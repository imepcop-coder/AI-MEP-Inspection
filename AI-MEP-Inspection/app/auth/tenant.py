from __future__ import annotations

import base64
import json
import os
import secrets
from typing import Any

from fastapi import Request, Depends
from itsdangerous import BadSignature, TimestampSigner
from sqlalchemy.orm import Query, Session
from app.database.db import get_db

from app.models.user import User

# Ensure a persistent session secret so reloading the app doesn't invalidate existing session cookies.
_env_secret = os.getenv("SESSION_SECRET")
if _env_secret:
    SESSION_SECRET = _env_secret
else:
    # Use a file in the project root to persist the secret between restarts in development
    from pathlib import Path

    _project_root = Path(__file__).resolve().parents[1].parents[0]
    _secret_file = _project_root / "session_secret.txt"
    try:
        if _secret_file.exists():
            SESSION_SECRET = _secret_file.read_text(encoding="utf-8").strip()
        else:
            SESSION_SECRET = secrets.token_hex(32)
            try:
                _secret_file.write_text(SESSION_SECRET, encoding="utf-8")
            except Exception:
                # If writing fails, fall back to in-memory secret (less ideal)
                pass
    except Exception:
        SESSION_SECRET = secrets.token_hex(32)

SESSION_SIGNER = TimestampSigner(SESSION_SECRET)
SESSION_MAX_AGE = 1209600  # Match SessionMiddleware default (14 days)


class TenantContextError(PermissionError):
    pass


def get_tenant_context(user: User | dict[str, Any] | None) -> tuple[int | None, int | None]:
    if isinstance(user, dict):
        company_id = user.get("company_id")
        workspace_id = user.get("workspace_id")
        return company_id, workspace_id
    if user is None:
        return None, None
    return getattr(user, "company_id", None), getattr(user, "workspace_id", None)


def apply_tenant_filter(query: Query, user: User | dict[str, Any] | None, *, model: type | None = None):
    company_id, workspace_id = get_tenant_context(user)
    if company_id is None:
        return query

    if model is None:
        entity = query.column_descriptions[0]["entity"]
        if entity is None:
            return query
        model = getattr(entity, "class_", entity)

    if hasattr(model, "company_id"):
        query = query.filter(model.company_id == company_id)
    if hasattr(model, "workspace_id") and workspace_id is not None:
        query = query.filter(model.workspace_id == workspace_id)
    return query


def ensure_tenant_access(record: Any, user: User | dict[str, Any] | None) -> None:
    company_id, workspace_id = get_tenant_context(user)
    if company_id is None:
        return

    record_company_id = getattr(record, "company_id", None)
    if record_company_id is not None and record_company_id != company_id:
        raise TenantContextError("You do not have access to this tenant resource")

    record_workspace_id = getattr(record, "workspace_id", None)
    if workspace_id is not None and record_workspace_id is not None and record_workspace_id != workspace_id:
        raise TenantContextError("You do not have access to this tenant resource")


def get_session_payload(request: Request) -> dict[str, Any] | None:
    session_data = request.scope.get("session") if hasattr(request, "scope") else None
    if not session_data:
        try:
            session_data = request.session
        except AssertionError:
            session_data = None

    if session_data:
        user_data = session_data.get("user")
        if isinstance(user_data, dict):
            return user_data

    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return None

    try:
        signed_data = SESSION_SIGNER.unsign(session_cookie.encode("utf-8"), max_age=SESSION_MAX_AGE)
        decoded_json = json.loads(base64.b64decode(signed_data))
    except (BadSignature, ValueError, TypeError, json.JSONDecodeError):
        return None

    if not isinstance(decoded_json, dict):
        return None

    user_data = decoded_json.get("user")
    if not isinstance(user_data, dict):
        return None
    return user_data


def get_session_user(request: Request, db: Session) -> User | dict[str, Any] | None:
    user_data = get_session_payload(request)
    if not user_data:
        return None

    user = db.query(User).filter(User.id == user_data["id"]).first()
    if not user:
        return user_data

    if not getattr(user, "company_id", None):
        from app.services.workspace_service import WorkspaceService

        workspace = WorkspaceService(db).create_default_workspace(user)
        user.company_id = workspace.company_id
        user.workspace_id = workspace.id
        db.commit()

    return user


def get_authenticated_user(request, db: Session) -> User:
    from fastapi import HTTPException

    user = get_session_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return get_authenticated_user(request, db)
