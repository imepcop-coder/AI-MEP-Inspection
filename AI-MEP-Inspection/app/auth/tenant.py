from __future__ import annotations

from typing import Any

from fastapi import Request, Depends
from sqlalchemy.orm import Query, Session
from app.database.db import get_db

from app.models.user import User


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


def get_authenticated_user(request, db: Session) -> User:
    from fastapi import HTTPException

    user_data = request.session.get("user")
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.id == user_data["id"]).first()
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not getattr(user, "company_id", None):
        from app.services.workspace_service import WorkspaceService

        workspace = WorkspaceService(db).create_default_workspace(user)
        user.company_id = workspace.company_id
        user.workspace_id = workspace.id
        db.commit()

    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return get_authenticated_user(request, db)
