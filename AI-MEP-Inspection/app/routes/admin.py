from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.tenant import get_authenticated_user
from app.database.db import get_db
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def check_login(request: Request):
    return request.session.get("user")


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user_data = check_login(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    user = get_authenticated_user(request, db)
    if not user or user.role not in {"Admin", "Super Admin"}:
        return RedirectResponse(url="/dashboard", status_code=303)

    users = db.query(User).filter(User.company_id == user.company_id).order_by(User.created_at.desc()).limit(20).all()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"user": user, "users": users}
    )
