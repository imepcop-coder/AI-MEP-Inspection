import csv
import io
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.tenant import apply_tenant_filter, ensure_tenant_access, get_authenticated_user
from app.database.db import get_db
from app.models.document import Document
from app.models.inspection import Inspection
from app.models.report_template import ReportTemplate
from app.models.user import User
from app.excel.report_generator import _field_labels

router = APIRouter()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")

REPORT_FOLDER = Path("reports")
REPORT_FOLDER.mkdir(exist_ok=True)


def _csv_safe_value(value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def _inspection_export_value(inspection: Inspection, field: str) -> str:
    if field == "project":
        return inspection.project.project_name if inspection.project else ""
    if field == "project_code":
        return inspection.project.project_code if inspection.project else ""
    if field == "client":
        return inspection.project.client_name if inspection.project else ""
    if field in {"snag_description", "finding", "observation"}:
        return inspection.description or ""
    return getattr(inspection, field, "") or ""


def _is_admin_user(user: User) -> bool:
    return getattr(user, "role", "") in {"Admin", "Super Admin", "Company Admin"}


@router.get("/reports")
async def reports(request: Request, db: Session = Depends(get_db)):
    current_user = get_authenticated_user(request, db)

    report_query = db.query(Document).filter(Document.user_id == current_user.id)
    if current_user.company_id is not None:
        report_query = report_query.filter(Document.company_id == current_user.company_id)
    if current_user.workspace_id is not None:
        report_query = report_query.filter(Document.workspace_id == current_user.workspace_id)

    documents = report_query.order_by(Document.uploaded_at.desc()).all()
    report_list = []
    for document in documents:
        file_path = REPORT_FOLDER / document.filename
        if not file_path.exists():
            continue

        modified = document.uploaded_at or datetime.utcnow()
        report_list.append({
            "name": document.filename,
            "size": round(file_path.stat().st_size / 1024, 2),
            "date": modified.strftime("%d-%m-%Y"),
            "time": modified.strftime("%I:%M %p"),
        })

    templates_db = apply_tenant_filter(db.query(ReportTemplate), current_user).order_by(ReportTemplate.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "request": request,
            "reports": report_list,
            "report_templates": templates_db,
        },
    )


@router.get("/reports/export.csv")
async def export_inspections_csv(
    request: Request,
    template_id: str | None = None,
    db: Session = Depends(get_db),
):
    current_user = get_authenticated_user(request, db)
    fields = [
        "inspection_no",
        "project",
        "location",
        "discipline",
        "status",
        "inspection_date",
        "inspector",
        "description",
    ]
    if template_id:
        try:
            parsed_template_id = int(template_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid report template") from exc
        template = (
            apply_tenant_filter(db.query(ReportTemplate), current_user)
            .filter(ReportTemplate.id == parsed_template_id)
            .first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Report template not found")
        fields = template.get_field_list()

    inspections = (
        apply_tenant_filter(db.query(Inspection), current_user)
        .order_by(Inspection.created_at.desc())
        .all()
    )
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([_csv_safe_value(_field_labels(field)) for field in fields])
    for inspection in inspections:
        writer.writerow(
            [
                _csv_safe_value(_inspection_export_value(inspection, field))
                for field in fields
            ]
        )
    csv_content = output.getvalue()
    output.close()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inspection-export.csv"'},
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
    document = db.query(Document).filter(Document.filename == filename).first()

    if not document:
        raise HTTPException(status_code=404, detail="Report not found.")

    if not _is_admin_user(current_user):
        if document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to download this report.")
        if current_user.company_id is not None and document.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="You do not have permission to download this report.")
        if current_user.workspace_id is not None and document.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="You do not have permission to download this report.")

    file_path = REPORT_FOLDER / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file is unavailable.")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )