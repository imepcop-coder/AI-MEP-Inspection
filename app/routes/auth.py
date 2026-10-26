import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime
from urllib.parse import urlencode

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import urlparse, unquote

from app.auth.security import hash_password, verify_password
from app.auth.tenant import SESSION_SECRET
from app.database.db import get_db
from app.models.user import User
from app.services.workspace_service import WorkspaceService

router = APIRouter()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
GOOGLE_SIGNUP_TTL_SECONDS = 600
_google_state_cipher = Fernet(
    base64.urlsafe_b64encode(hashlib.sha256(SESSION_SECRET.encode("utf-8")).digest())
)


def _google_configuration() -> tuple[str, str, str] | None:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        return None
    return client_id, client_secret, redirect_uri


def _google_login_error(code: str | None = None) -> str | None:
    messages = {
        "google_unavailable": "Google sign-in is not configured. Please use your email and password.",
        "google_failed": "Google sign-in could not be completed. Please try again.",
        "google_email": "Google must provide a verified email address to continue.",
        "google_disabled": "This account is disabled. Contact your administrator.",
    }
    return messages.get(code or "")


def _oauth_redirect(url: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=303)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _set_authenticated_session(request: Request, user: User, db: Session, action: str) -> None:
    workspace = WorkspaceService(db).create_default_workspace(user)
    user.company_id = workspace.company_id
    user.workspace_id = workspace.id
    user.last_login = datetime.utcnow()
    db.commit()
    request.session.clear()
    request.session["user"] = {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "company_id": user.company_id,
        "workspace_id": user.workspace_id,
    }
    WorkspaceService(db).log_action(user, action, "User authenticated with Google")


def _read_google_signup(request: Request) -> dict | None:
    token = request.session.get("google_signup")
    if not isinstance(token, str):
        return None
    try:
        payload = _google_state_cipher.decrypt(
            token.encode("ascii"),
            ttl=GOOGLE_SIGNUP_TTL_SECONDS,
        )
        profile = json.loads(payload)
    except (InvalidToken, UnicodeEncodeError, json.JSONDecodeError):
        request.session.pop("google_signup", None)
        request.session.pop("google_signup_csrf", None)
        return None
    if not isinstance(profile, dict) or not profile.get("email") or not profile.get("sub"):
        request.session.pop("google_signup", None)
        request.session.pop("google_signup_csrf", None)
        return None
    return profile


# ---------------------------------------------------------
# Login Page
# ---------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already authenticated, redirect to dashboard
    if getattr(request.state, "current_user", None):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": _google_login_error(request.query_params.get("error"))}
    )


@router.get("/auth/google")
async def google_login(request: Request):
    if getattr(request.state, "current_user", None):
        return RedirectResponse(url="/dashboard", status_code=303)
    configuration = _google_configuration()
    if configuration is None:
        return RedirectResponse(url="/login?error=google_unavailable", status_code=303)

    client_id, _, redirect_uri = configuration
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    oauth_state = {
        "state": state,
        "nonce": nonce,
        "verifier": verifier,
    }
    request.session.clear()
    request.session["google_oauth"] = _google_state_cipher.encrypt(
        json.dumps(oauth_state).encode("utf-8")
    ).decode("ascii")

    parameters = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return RedirectResponse(f"{GOOGLE_AUTHORIZE_URL}?{urlencode(parameters)}", status_code=302)


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    configuration = _google_configuration()
    encrypted_state = request.session.pop("google_oauth", None)
    if configuration is None or not isinstance(encrypted_state, str):
        request.session.clear()
        return _oauth_redirect("/login?error=google_failed")

    try:
        state_payload = _google_state_cipher.decrypt(
            encrypted_state.encode("ascii"),
            ttl=600,
        )
        oauth_state = json.loads(state_payload)
    except (InvalidToken, UnicodeEncodeError, json.JSONDecodeError):
        request.session.clear()
        return _oauth_redirect("/login?error=google_failed")

    callback_state = request.query_params.get("state", "")
    authorization_code = request.query_params.get("code")
    if (
        not callback_state
        or not hmac.compare_digest(callback_state, str(oauth_state.get("state", "")))
        or not authorization_code
        or request.query_params.get("error")
    ):
        request.session.clear()
        return _oauth_redirect("/login?error=google_failed")

    client_id, client_secret, redirect_uri = configuration
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": authorization_code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": oauth_state["verifier"],
                },
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            identity_token = token_payload.get("id_token")
            if not isinstance(identity_token, str):
                raise ValueError("Google response did not include an identity token.")

            jwks_response = await client.get(GOOGLE_JWKS_URL)
            jwks_response.raise_for_status()
            jwks = jwt.PyJWKSet.from_dict(jwks_response.json())

        header = jwt.get_unverified_header(identity_token)
        signing_key = next(
            (key for key in jwks.keys if key.key_id == header.get("kid")),
            None,
        )
        if signing_key is None or header.get("alg") != "RS256":
            raise jwt.InvalidTokenError("Unrecognized Google signing key.")
        claims = jwt.decode(
            identity_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=GOOGLE_ISSUERS,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "nonce"]},
        )
        if not hmac.compare_digest(str(claims.get("nonce", "")), str(oauth_state["nonce"])):
            raise jwt.InvalidTokenError("Google nonce validation failed.")
        if claims.get("email_verified") is not True:
            request.session.clear()
            return _oauth_redirect("/login?error=google_email")
        email = str(claims.get("email", "")).strip().lower()
        full_name = str(claims.get("name") or claims.get("given_name") or "").strip()
        subject = str(claims.get("sub", ""))
        if not email or not subject:
            request.session.clear()
            return _oauth_redirect("/login?error=google_email")
    except (httpx.HTTPError, ValueError, KeyError, jwt.PyJWTError):
        request.session.clear()
        return _oauth_redirect("/login?error=google_failed")

    user = db.query(User).filter(User.email == email).first()
    if user:
        if not user.is_active:
            request.session.clear()
            return _oauth_redirect("/login?error=google_disabled")
        user.is_verified = True
        if full_name and not user.full_name:
            user.full_name = full_name[:100]
        _set_authenticated_session(request, user, db, "google_login")
        return _oauth_redirect("/dashboard")

    encrypted_profile = _google_state_cipher.encrypt(
        json.dumps(
            {
                "sub": subject,
                "email": email,
                "full_name": full_name[:100],
            }
        ).encode("utf-8")
    )
    request.session.clear()
    request.session["google_signup"] = encrypted_profile.decode("ascii")
    request.session["google_signup_csrf"] = secrets.token_urlsafe(32)
    return _oauth_redirect("/auth/google/complete")


@router.get("/auth/google/complete", response_class=HTMLResponse)
async def google_signup_complete_page(request: Request):
    profile = _read_google_signup(request)
    csrf_token = request.session.get("google_signup_csrf")
    if not profile or not isinstance(csrf_token, str):
        request.session.clear()
        return RedirectResponse(url="/login?error=google_failed", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="google_signup_complete.html",
        context={"profile": profile, "csrf_token": csrf_token},
    )


@router.post("/auth/google/complete")
async def complete_google_signup(
    request: Request,
    phone: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    profile = _read_google_signup(request)
    expected_csrf = request.session.get("google_signup_csrf")
    if (
        not profile
        or not isinstance(expected_csrf, str)
        or not hmac.compare_digest(csrf_token, expected_csrf)
    ):
        request.session.clear()
        return RedirectResponse(url="/login?error=google_failed", status_code=303)

    phone = phone.strip()
    if not phone or len(phone) > 20:
        refreshed_csrf = secrets.token_urlsafe(32)
        request.session["google_signup_csrf"] = refreshed_csrf
        return templates.TemplateResponse(
            request=request,
            name="google_signup_complete.html",
            context={
                "profile": profile,
                "csrf_token": refreshed_csrf,
                "error": "Enter a phone number of 1 to 20 characters.",
            },
            status_code=422,
        )
    if db.query(User.id).filter(User.phone == phone).first():
        refreshed_csrf = secrets.token_urlsafe(32)
        request.session["google_signup_csrf"] = refreshed_csrf
        return templates.TemplateResponse(
            request=request,
            name="google_signup_complete.html",
            context={
                "profile": profile,
                "csrf_token": refreshed_csrf,
                "error": "That phone number is already associated with an account.",
            },
            status_code=409,
        )

    request.session.pop("google_signup_csrf", None)
    request.session.pop("google_signup", None)
    existing_user = db.query(User).filter(User.email == profile["email"]).first()
    if existing_user:
        if not existing_user.is_active:
            request.session.clear()
            return _oauth_redirect("/login?error=google_disabled")
        existing_user.is_verified = True
        _set_authenticated_session(request, existing_user, db, "google_login")
        return _oauth_redirect("/dashboard")

    user = User(
        full_name=(profile.get("full_name") or profile["email"].split("@", 1)[0])[:100],
        email=profile["email"],
        phone=phone,
        password=hash_password(secrets.token_urlsafe(48)),
        role="Engineer",
        is_active=True,
        is_verified=True,
        subscription_plan="Free",
        ai_usage_count=0,
    )
    db.add(user)
    try:
        db.flush()
        _set_authenticated_session(request, user, db, "google_signup")
    except Exception:
        db.rollback()
        raise
    return _oauth_redirect("/dashboard")


# ---------------------------------------------------------
# Register Page
# ---------------------------------------------------------
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    # If already authenticated, redirect to dashboard
    if getattr(request.state, "current_user", None):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={}
    )


# ---------------------------------------------------------
# Register User
# ---------------------------------------------------------
@router.post("/register")
async def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form("Engineer"),
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Passwords do not match."})

    if role not in ["Engineer", "Inspector", "Admin"]:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Invalid role selected."})

    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Email already registered."})

    existing_phone = db.query(User).filter(User.phone == phone).first()
    if existing_phone:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Phone number already registered."})

    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password=hash_password(password),
        role=role,
        is_active=True,
        is_verified=False,
        verification_token=None,
        subscription_plan="Free",
        ai_usage_count=0,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    workspace = WorkspaceService(db)
    workspace.create_default_workspace(user)
    workspace.log_action(user, "account_created", "User registered a new account")

    return templates.TemplateResponse(request=request, name="login.html", context={"success": "Registration successful. Please login."})


# ---------------------------------------------------------
# Login User
# ---------------------------------------------------------
@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    import logging
    logger = logging.getLogger("ai_mep.auth")
    logger.info("Login attempt for email=%s", email)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.info("Login failed: user not found for email=%s", email)
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid email or password."})

    # log a short prefix of the stored hash for debugging (do not leak full hash in logs)
    try:
        logger.debug("Found user id=%s hash_prefix=%s", user.id, (user.password or "")[0:40])
    except Exception:
        pass

    valid = verify_password(password, user.password)
    logger.info("Password verification for email=%s: %s", email, valid)

    if not valid:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid email or password."})

    if not user.is_active:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Your account is disabled."})

    workspace = WorkspaceService(db).create_default_workspace(user)
    user.company_id = workspace.company_id
    user.workspace_id = workspace.id
    db.commit()

    request.session["user"] = {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "company_id": user.company_id,
        "workspace_id": user.workspace_id,
    }

    user.last_login = datetime.utcnow()
    db.commit()

    workspace = WorkspaceService(db)
    workspace.log_action(user, "login", "User logged in")

    # Determine where to redirect after login
    next_url = request.query_params.get("next") or request.session.pop("next", None)
    # Validate next_url to prevent open redirects: only allow relative paths
    if next_url and isinstance(next_url, str):
        parsed = urlparse(next_url)
        if parsed.scheme or parsed.netloc or not next_url.startswith("/"):
            next_url = None
    if not next_url:
        next_url = "/dashboard"

    # Prefer rendering the dashboard immediately after login so the user sees the UI
    # even if the client's cookie handling or middleware ordering is flaky in development.
    # Redirect behavior is still supported via next_url when things are healthy.
    try:
        # Render dashboard context directly
        workspace_service = WorkspaceService(db)
        workspace_service.create_default_workspace(user)
        context = workspace_service.get_dashboard_context(user)
        return templates.TemplateResponse(request=request, name="dashboard.html", context=context)
    except Exception:
        # Fallback to redirect
        return RedirectResponse(url=next_url, status_code=303)


# ---------------------------------------------------------
# Forgot Password Page
# ---------------------------------------------------------
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={}
    )


# ---------------------------------------------------------
# Reset Password
# ---------------------------------------------------------
@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="forgot_password.html",
            context={
                "error": "Email not found."
            }
        )

    user.password = hash_password(new_password)

    db.commit()

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# ---------------------------------------------------------
# Logout
# ---------------------------------------------------------
@router.get("/logout")
async def logout(request: Request):
    # Clear server-side session data
    try:
        request.session.clear()
    except Exception:
        pass
    # Return redirect and delete the session cookie to ensure the browser discards it
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    return response