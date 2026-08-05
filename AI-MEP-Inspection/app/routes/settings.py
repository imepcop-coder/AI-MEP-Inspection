from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

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
    user_data = check_login(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(User).filter(User.id == user_data["id"]).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"user": user}
    )


@router.post("/settings")
async def update_settings(
    request: Request,
    full_name: str = Form(None),
    phone: str = Form(None),
    company_name: str = Form(None),
    db: Session = Depends(get_db),
):
    user_data = check_login(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(User).filter(User.id == user_data["id"]).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    if full_name:
        user.full_name = full_name
    if phone:
        user.phone = phone
    if company_name:
        user.company_name = company_name

    db.commit()
    return RedirectResponse(url="/settings", status_code=303)
