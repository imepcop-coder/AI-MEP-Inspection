from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.tenant import apply_tenant_filter, ensure_tenant_access, get_authenticated_user
from app.database.db import get_db
from app.models.inspection import Inspection
from app.models.project import Project

router = APIRouter()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# =========================================================
# Helper
# =========================================================

def check_login(request: Request):
    return request.session.get("user")


# =========================================================
# Inspection List
# =========================================================

@router.get("/inspections", response_class=HTMLResponse)
async def inspection_list(
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    current_user = get_authenticated_user(request, db)
    inspections = (
        apply_tenant_filter(db.query(Inspection), current_user)
        .order_by(Inspection.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="inspections/inspection_list.html",
        context={
            "user": user,
            "inspections": inspections
        }
    )


# =========================================================
# Add Inspection Page
# =========================================================

@router.get("/inspections/new", response_class=HTMLResponse)
async def add_inspection_page(
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    projects = db.query(Project).all()

    print("Projects Found:", len(projects))

    for p in projects:
        print(p.id, p.project_name)

    return templates.TemplateResponse(
        request=request,
        name="inspections/add_inspection.html",
        context={
            "user": user,
            "projects": projects
        }
    )

# =========================================================
# Save Inspection
# =========================================================

@router.post("/inspections/new")
async def save_inspection(
    request: Request,

    inspection_no: str = Form(...),
    project_id: int = Form(...),
    discipline: str = Form(...),
    inspection_date: str = Form(...),
    inspector: str = Form(...),
    location: str = Form(...),
    inspection_type: str = Form(...),
    drawing_no: str = Form(None),
    specification: str = Form(None),
    description: str = Form(None),
    status: str = Form(...),

    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    current_user = get_authenticated_user(request, db)
    existing = (
        apply_tenant_filter(db.query(Inspection), current_user)
        .filter(
            Inspection.inspection_no == inspection_no
        )
        .first()
    )

    if existing:

        projects = db.query(Project).all()

        return templates.TemplateResponse(
            request=request,
            name="inspections/add_inspection.html",
            context={
                "user": user,
                "projects": projects,
                "error": "Inspection Number already exists."
            }
        )

    inspection = Inspection(
        inspection_no=inspection_no,
        project_id=project_id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        workspace_id=current_user.workspace_id,
        discipline=discipline,
        inspection_date=datetime.strptime(
            inspection_date,
            "%Y-%m-%d"
        ).date(),
        inspector=inspector,
        location=location,
        inspection_type=inspection_type,
        drawing_no=drawing_no,
        specification=specification,
        description=description,
        status=status,
    )

    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    return RedirectResponse(
        url="/inspections",
        status_code=303
    )

# =========================================================
# END OF PART 1
# =========================================================
# =========================================================
# View Inspection
# =========================================================

@router.get("/inspections/{inspection_id}", response_class=HTMLResponse)
async def view_inspection(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    inspection = (
        db.query(Inspection)
        .filter(Inspection.id == inspection_id, Inspection.user_id == user["id"])
        .first()
    )

    if not inspection:
        return RedirectResponse(url="/inspections", status_code=303)

    project = (
        apply_tenant_filter(db.query(Project), current_user)
        .filter(Project.id == inspection.project_id)
        .first()
    )

    return templates.TemplateResponse(
        request=request,
        name="inspections/view_inspection.html",
        context={
            "user": user,
            "inspection": inspection,
            "project": project
        }
    )


# =========================================================
# Edit Inspection Page
# =========================================================

@router.get("/inspections/edit/{inspection_id}", response_class=HTMLResponse)
async def edit_inspection_page(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    inspection = (
        db.query(Inspection)
        .filter(Inspection.id == inspection_id, Inspection.user_id == user["id"])
        .first()
    )

    if not inspection:
        return RedirectResponse(url="/inspections", status_code=303)

    projects = (
        apply_tenant_filter(db.query(Project), current_user)
        .order_by(Project.project_name)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="inspections/edit_inspection.html",
        context={
            "user": user,
            "inspection": inspection,
            "projects": projects
        }
    )


# =========================================================
# Update Inspection
# =========================================================

@router.post("/inspections/edit/{inspection_id}")
async def update_inspection(
    inspection_id: int,
    request: Request,

    inspection_no: str = Form(...),
    project_id: int = Form(...),
    discipline: str = Form(...),
    inspection_date: str = Form(...),
    inspector: str = Form(...),
    location: str = Form(...),
    inspection_type: str = Form(...),
    drawing_no: str = Form(None),
    specification: str = Form(None),
    description: str = Form(None),
    status: str = Form(...),

    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    inspection = (
        db.query(Inspection)
        .filter(Inspection.id == inspection_id, Inspection.user_id == user["id"])
        .first()
    )

    if not inspection:
        return RedirectResponse(url="/inspections", status_code=303)

    duplicate = (
        apply_tenant_filter(db.query(Inspection), current_user)
        .filter(
            Inspection.inspection_no == inspection_no,
            Inspection.id != inspection_id
        )
        .first()
    )

    if duplicate:

        projects = db.query(Project).all()

        return templates.TemplateResponse(
            request=request,
            name="inspections/edit_inspection.html",
            context={
                "user": user,
                "inspection": inspection,
                "projects": projects,
                "error": "Inspection Number already exists."
            }
        )

    inspection.inspection_no = inspection_no
    inspection.project_id = project_id
    inspection.discipline = discipline
    inspection.inspection_date = datetime.strptime(
        inspection_date,
        "%Y-%m-%d"
    ).date()

    inspection.inspector = inspector
    inspection.location = location
    inspection.inspection_type = inspection_type
    inspection.drawing_no = drawing_no
    inspection.specification = specification
    inspection.description = description
    inspection.status = status

    db.commit()
    db.refresh(inspection)

    return RedirectResponse(
        url="/inspections",
        status_code=303
    )


# =========================================================
# Delete Inspection
# =========================================================

@router.get("/inspections/delete/{inspection_id}")
async def delete_inspection(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    inspection = (
        db.query(Inspection)
        .filter(Inspection.id == inspection_id, Inspection.user_id == user["id"])
        .first()
    )

    if inspection:
        db.delete(inspection)
        db.commit()

    return RedirectResponse(
        url="/inspections",
        status_code=303)


# =========================================================
# END OF INSPECTION ROUTES
# =========================================================