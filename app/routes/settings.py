from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.auth.tenant import apply_tenant_filter, get_authenticated_user
from app.database.db import get_db
from app.models.user import User

router = APIRouter()
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def check_login(request: Request):
    return request.session.get("user")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_authenticated_user(request, db)
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "request": request,
            "user": user,
            "success": None,
            "error": None,
            "active_tab": "profile",
        },
    )


@router.post("/settings")
async def update_settings(
    request: Request,
    full_name: str = Form(None),
    phone: str = Form(None),
    company_name: str = Form(None),
    db: Session = Depends(get_db),
):
    current_user = get_authenticated_user(request, db)
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    if full_name:
        user.full_name = full_name.strip()
    if phone:
        user.phone = phone.strip()
    if company_name:
        user.company_name = company_name.strip()

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
    return RedirectResponse(url="/settings?tab=profile", status_code=303)


@router.post("/settings/security")
async def update_security_settings(
    request: Request,
    current_password: str = Form(None),
    new_password: str = Form(None),
    confirm_password: str = Form(None),
    db: Session = Depends(get_db),
):
    current_user = get_authenticated_user(request, db)
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    if not current_password or not new_password or not confirm_password:
        return RedirectResponse(url="/settings?tab=security&error=Please+complete+all+security+fields", status_code=303)

    if not verify_password(current_password, user.password):
        return RedirectResponse(url="/settings?tab=security&error=Current+password+is+incorrect", status_code=303)

    if new_password != confirm_password:
        return RedirectResponse(url="/settings?tab=security&error=Passwords+do+not+match", status_code=303)

    if len(new_password) < 8:
        return RedirectResponse(url="/settings?tab=security&error=Password+must+be+at+least+8+characters", status_code=303)

    user.password = hash_password(new_password)
    db.commit()
    return RedirectResponse(url="/settings?tab=security&success=Password+updated+successfully", status_code=303)


@router.post("/settings/notifications")
async def update_notification_settings(
    request: Request,
    email_notifications: str = Form("off"),
    inspection_notifications: str = Form("off"),
    report_notifications: str = Form("off"),
    ai_notifications: str = Form("off"),
    db: Session = Depends(get_db),
):
    current_user = get_authenticated_user(request, db)
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    user.email_notifications = email_notifications == "on"
    user.inspection_notifications = inspection_notifications == "on"
    user.report_notifications = report_notifications == "on"
    user.ai_notifications = ai_notifications == "on"
    db.commit()
    return RedirectResponse(url="/settings?tab=notifications&success=Notification+preferences+saved", status_code=303)


@router.get("/settings")
async def settings_page_with_params(request: Request, db: Session = Depends(get_db)):
    current_user = get_authenticated_user(request, db)
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    active_tab = request.query_params.get("tab") or "profile"
    success = request.query_params.get("success")
    error = request.query_params.get("error")

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "request": request,
            "user": user,
            "success": success,
            "error": error,
            "active_tab": active_tab,
        },
    )
