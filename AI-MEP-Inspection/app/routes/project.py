from datetime import datetime

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.tenant import apply_tenant_filter, ensure_tenant_access, get_authenticated_user
from app.database.db import get_db
from app.models.project import Project

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


# =========================================================
# Helper
# =========================================================

def check_login(request: Request):
    return request.session.get("user")


# =========================================================
# Project List
# =========================================================

@router.get("/projects", response_class=HTMLResponse)
async def project_list(
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
    projects = (
        apply_tenant_filter(db.query(Project), current_user)
        .order_by(Project.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="projects/project_list.html",
        context={
            "user": user,
            "projects": projects
        }
    )


# =========================================================
# Add Project Page
# =========================================================

@router.get("/projects/new", response_class=HTMLResponse)
async def add_project_page(request: Request):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/add_project.html",
        context={
            "user": user
        }
    )


# =========================================================
# Save Project
# =========================================================

@router.post("/projects/new")
async def save_project(
    request: Request,
    project_code: str = Form(...),
    project_name: str = Form(...),
    client_name: str = Form(...),
    consultant_name: str = Form(None),
    contractor_name: str = Form(None),
    location: str = Form(...),
    discipline: str = Form(...),
    start_date: str = Form(None),
    end_date: str = Form(None),
    status: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    existing = (
        db.query(Project)
        .filter(Project.project_code == project_code)
        .first()
    )

    if existing:

        return templates.TemplateResponse(
            request=request,
            name="projects/add_project.html",
            context={
                "user": user,
                "error": "Project Code already exists."
            }
        )

    current_user = get_authenticated_user(request, db)
    project = Project(
        project_code=project_code,
        project_name=project_name,
        client_name=client_name,
        consultant_name=consultant_name,
        contractor_name=contractor_name,
        location=location,
        discipline=discipline,
        start_date=datetime.strptime(start_date, "%Y-%m-%d").date()
        if start_date else None,
        end_date=datetime.strptime(end_date, "%Y-%m-%d").date()
        if end_date else None,
        status=status,
        description=description,
        company_id=current_user.company_id,
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return RedirectResponse(
        url="/projects",
        status_code=303
    )

# =========================================================
# END OF PART 1
# =========================================================
# =========================================================
# View Project
# =========================================================

@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def view_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        return RedirectResponse(
            url="/projects",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/view_project.html",
        context={
            "user": user,
            "project": project
        }
    )


# =========================================================
# Edit Project Page
# =========================================================

@router.get("/projects/edit/{project_id}", response_class=HTMLResponse)
async def edit_project_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        return RedirectResponse(
            url="/projects",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/edit_project.html",
        context={
            "user": user,
            "project": project
        }
    )


# =========================================================
# Update Project
# =========================================================

@router.post("/projects/edit/{project_id}")
async def update_project(
    project_id: int,
    request: Request,
    project_code: str = Form(...),
    project_name: str = Form(...),
    client_name: str = Form(...),
    consultant_name: str = Form(None),
    contractor_name: str = Form(None),
    location: str = Form(...),
    discipline: str = Form(...),
    start_date: str = Form(None),
    end_date: str = Form(None),
    status: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        return RedirectResponse(
            url="/projects",
            status_code=303
        )

    current_user = get_authenticated_user(request, db)
    duplicate = (
        apply_tenant_filter(db.query(Project), current_user)
        .filter(
            Project.project_code == project_code,
            Project.id != project_id
        )
        .first()
    )

    if duplicate:
        return templates.TemplateResponse(
        request=request,
        name="projects/edit_project.html",
        context={
            "user": user,
            "project": project,
            "error": "Project Code already exists."
        }
    )

    project.project_code = project_code
    project.project_name = project_name
    project.client_name = client_name
    project.consultant_name = consultant_name
    project.contractor_name = contractor_name
    project.location = location
    project.discipline = discipline
    project.status = status
    project.description = description

    project.start_date = (
        datetime.strptime(start_date, "%Y-%m-%d").date()
        if start_date else None
    )

    project.end_date = (
        datetime.strptime(end_date, "%Y-%m-%d").date()
        if end_date else None
    )

    db.commit()
    db.refresh(project)

    return RedirectResponse(
        url="/projects",
        status_code=303
    )


# =========================================================
# Delete Project
# =========================================================

@router.get("/projects/delete/{project_id}")
async def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = check_login(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    project = db.query(Project).filter(Project.id == project_id).first()

    if project:
        db.delete(project)
        db.commit()

    return RedirectResponse(
        url="/projects",
        status_code=303
    )

# =========================================================
# END OF PROJECT ROUTES
# =========================================================