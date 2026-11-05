from fastapi import APIRouter, Depends, HTTPException, Request
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
        context={
            "user": user,
            "notifications": notifications,
            "unread_count": sum(not notification.is_read for notification in notifications),
        }
    )


@router.post("/notifications/read/{notification_id}")
async def mark_notification_read(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_authenticated_user(request, db)
    notification = (
        apply_tenant_filter(db.query(Notification), user)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_authenticated_user(request, db)
    (
        apply_tenant_filter(db.query(Notification), user)
        .filter(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)
