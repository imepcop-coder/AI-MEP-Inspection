from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.database.db import get_db
from app.models.user import User
from app.services.workspace_service import WorkspaceService

router = APIRouter()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ---------------------------------------------------------
# Login Page
# ---------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


# ---------------------------------------------------------
# Register Page
# ---------------------------------------------------------
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
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
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password):
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

    return RedirectResponse(url="/dashboard", status_code=303)


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
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)