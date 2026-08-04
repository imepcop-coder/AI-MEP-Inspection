from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.tenant import apply_tenant_filter, ensure_tenant_access, get_authenticated_user
from app.database.db import get_db
from app.models.report_template import ReportTemplate

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

REPORT_FOLDER = Path("reports")
REPORT_FOLDER.mkdir(exist_ok=True)


@router.get("/reports")
async def reports(request: Request, db: Session = Depends(get_db)):

    report_list = []

    latest_reports = sorted(
        REPORT_FOLDER.glob("*.xlsx"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )[:5]

    for file in latest_reports:

        modified = datetime.fromtimestamp(file.stat().st_mtime)

        report_list.append({
            "name": file.name,
            "size": round(file.stat().st_size / 1024, 2),
            "date": modified.strftime("%d-%m-%Y"),
            "time": modified.strftime("%I:%M %p")
        })

    templates_db = db.query(ReportTemplate).order_by(ReportTemplate.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "request": request,
            "reports": report_list,
            "report_templates": templates_db,
        }
    )


@router.get("/reports/templates")
async def manage_templates(request: Request, db: Session = Depends(get_db)):
    edit_id = request.query_params.get("edit_id")
    selected_template = None
    if edit_id:
        current_user = get_authenticated_user(request, db)
        selected_template = apply_tenant_filter(db.query(ReportTemplate), current_user).filter(ReportTemplate.id == int(edit_id)).first()

    templates_db = db.query(ReportTemplate).order_by(ReportTemplate.created_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "request": request,
            "reports": [],
            "report_templates": templates_db,
            "manage_templates": True,
            "selected_template": selected_template,
        },
    )


@router.post("/reports/templates")
async def save_template(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    template_id = form.get("template_id")
    name = (form.get("name") or "").strip()
    description = (form.get("description") or "").strip()
    fields = [field for field in (form.getlist("fields") or []) if field]
    is_default = form.get("is_default") == "on"

    if not name:
        raise ValueError("Template name is required")

    current_user = get_authenticated_user(request, db)
    if template_id:
        template = apply_tenant_filter(db.query(ReportTemplate), current_user).filter(ReportTemplate.id == int(template_id)).first()
        if not template:
            raise ValueError("Template not found")
    else:
        template = ReportTemplate(name=name, description=description, is_default=False, company_id=current_user.company_id, workspace_id=current_user.workspace_id)
        db.add(template)

    template.name = name
    template.description = description
    template.set_field_list(fields or ["image", "snag_description", "recommendation"])

    if is_default:
        apply_tenant_filter(db.query(ReportTemplate), current_user).filter(ReportTemplate.id != template.id).update({"is_default": False})
        template.is_default = True
    else:
        template.is_default = False

    db.commit()
    return RedirectResponse(url="/reports/templates", status_code=303)


@router.post("/reports/templates/delete/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    current_user = get_authenticated_user(request, db)
    template = apply_tenant_filter(db.query(ReportTemplate), current_user).filter(ReportTemplate.id == template_id).first()
    if template:
        db.delete(template)
        db.commit()
    return RedirectResponse(url="/reports/templates", status_code=303)


@router.post("/reports/templates/duplicate/{template_id}")
async def duplicate_template(template_id: int, db: Session = Depends(get_db)):
    current_user = get_authenticated_user(request, db)
    source = apply_tenant_filter(db.query(ReportTemplate), current_user).filter(ReportTemplate.id == template_id).first()
    if source:
        duplicate = ReportTemplate(
            name=f"{source.name} Copy",
            description=source.description,
            fields=source.get_field_list(),
            is_default=False,
            company_id=current_user.company_id,
            workspace_id=current_user.workspace_id,
        )
        db.add(duplicate)
        db.commit()
    return RedirectResponse(url="/reports/templates", status_code=303)


@router.get("/reports/download/{filename}")
async def download_report(filename: str, request: Request, db: Session = Depends(get_db)):

    current_user = get_authenticated_user(request, db)
    file_path = REPORT_FOLDER / filename
    if not file_path.exists():
        raise FileResponse(path=file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )