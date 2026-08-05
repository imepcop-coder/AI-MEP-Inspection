from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.tenant import apply_tenant_filter, get_authenticated_user
from app.database.db import get_db
from app.models.notification import Notification
from app.models.user import User

router = APIRouter()
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def check_login(request: Request):
    return request.session.get("user")


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, db: Session = Depends(get_db)):
    user_data = check_login(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    user = get_authenticated_user(request, db)
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    notifications = apply_tenant_filter(db.query(Notification), user).filter(Notification.user_id == user.id).order_by(Notification.id.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="notifications.html",
        context={"user": user, "notifications": notifications}
    )
