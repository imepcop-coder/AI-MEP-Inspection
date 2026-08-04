import os
from datetime import datetime

from PIL import Image
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.models.report_template import ReportTemplate


def _severity_fill(value):
    value = str(value).lower()

    if value == "critical":
        return PatternFill("solid", fgColor="C00000")

    if value == "high":
        return PatternFill("solid", fgColor="FF6666")

    if value == "medium":
        return PatternFill("solid", fgColor="FFD966")

    if value == "low":
        return PatternFill("solid", fgColor="A9D18E")

    return PatternFill("solid", fgColor="D9D9D9")


def _field_labels(field: str) -> str:
    labels = {
        "image": "Image",
        "project": "Project",
        "client": "Client",
        "contractor": "Contractor",
        "consultant": "Consultant",
        "location": "Location",
        "area": "Area",
        "floor": "Floor",
        "room": "Room",
        "equipment": "Equipment",
        "tag_number": "Tag Number",
        "discipline": "Discipline",
        "category": "Category",
        "sub_category": "Sub Category",
        "finding": "Finding",
        "snag_description": "Snag Description",
        "observation": "Observation",
        "recommendation": "Recommendation",
        "corrective_action": "Corrective Action",
        "root_cause": "Root Cause",
        "severity": "Severity",
        "priority": "Priority",
        "status": "Status",
        "inspector": "Inspector",
        "inspection_date": "Inspection Date",
        "standard_reference": "Standard Reference",
        "drawing_number": "Drawing Number",
        "specification": "Specification",
        "comments": "Comments",
        "attachments": "Attachments",
        "ai_summary": "AI Summary",
        "ai_confidence_score": "AI Confidence Score",
    }
    return labels.get(field, field.replace("_", " ").title())


def filter_analysis_payload(payload: dict, fields: list[str] | None = None) -> dict:
    selected_fields = fields or []
    if not selected_fields:
        return payload
    return {key: value for key, value in payload.items() if key in selected_fields}


def create_report(results, filename=None, template: ReportTemplate | None = None):

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/inspection_report_{timestamp}.xlsx"

    template_name = template.name if template else "Inspection Report"
    fields = template.get_field_list() if template else ["image", "snag_description", "recommendation"]

    wb = Workbook()
    ws = wb.active
    ws.title = template_name

    ws.merge_cells("A1:J1")

    title = ws["A1"]
    title.value = template_name.upper()
    title.font = Font(size=18, bold=True, color="FFFFFF")
    title.fill = PatternFill("solid", fgColor="1F4E78")
    title.alignment = Alignment(horizontal="center", vertical="center")

    headers = [_field_labels(field) for field in fields]

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, text in enumerate(headers, 1):
        cell = ws.cell(2, col)
        cell.value = text
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="D9EAD3")
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    widths = [25 if field == "image" else 20 for field in fields]

    from openpyxl.utils import get_column_letter
    for i,w in enumerate(widths,1):
        ws.column_dimensions[get_column_letter(i)].width = w

    os.makedirs("uploads/resized", exist_ok=True)

    row = 3

    for i,item in enumerate(results,1):

        ws.row_dimensions[row].height = 110

        filtered_item = filter_analysis_payload(item, fields)
        values = []
        for field in fields:
            values.append(filtered_item.get(field, ""))

        for c,v in enumerate(values,1):
            cell=ws.cell(row,c)
            cell.value=v
            cell.border=border
            cell.alignment=Alignment(vertical="center",wrap_text=True)

        if "severity" in fields:
            ws.cell(row, fields.index("severity") + 2).fill = _severity_fill(item.get("severity",""))

        if "image" in fields:
            image_name=item.get("image")

            if image_name:
                image_path=os.path.join("uploads",image_name)

                if os.path.exists(image_path):

                    img=Image.open(image_path)
                    img.thumbnail((180,120))

                    canvas=Image.new("RGB",(180,120),"white")
                    x=(180-img.width)//2
                    y=(120-img.height)//2
                    canvas.paste(img,(x,y))

                    resized=os.path.join(
                        "uploads",
                        "resized",
                        f"resized_{image_name}"
                    )

                    canvas.save(resized)

                    xl=XLImage(resized)
                    xl.width=180
                    xl.height=120
                    xl.anchor=f"B{row}"

                    ws.add_image(xl)

        row+=1

    ws.freeze_panes="A3"
    ws.sheet_view.showGridLines=False

    os.makedirs(os.path.dirname(filename) or "reports",exist_ok=True)

    wb.save(filename)

    return filename
