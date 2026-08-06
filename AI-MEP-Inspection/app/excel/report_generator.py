import os
import math
from datetime import datetime

from PIL import Image
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.models.report_template import ReportTemplate


# Styling constants
TITLE_BANNER_COLOR = "1D4ED8"  # Blue banner for title
HEADER_FILL_COLOR = "0F172A"  # Dark blue header
HEADER_FONT_COLOR = "FFFFFF"
ALT_ROW_FILL = "F8FAFC"
DEFAULT_FONT_NAME = "Calibri"
DEFAULT_FONT_SIZE = 11


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
    """
    Create a professional Excel inspection report using only the fields selected in the template.
    Images are embedded (no filenames), sized proportionally (approx 120-150px), centered in their cell,
    rows are auto-sized for image and wrapped text, columns use suggested defaults, headers are styled,
    and print settings are applied for a professional output.
    """

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/inspection_report_{timestamp}.xlsx"

    template_name = template.name if template else "Inspection Report"
    fields = template.get_field_list() if template else ["image", "snag_description", "recommendation"]

    wb = Workbook()
    ws = wb.active
    ws.title = template_name

    # Determine last column for merges
    last_col_letter = get_column_letter(max(1, len(fields)))

    # Title banner (professional fixed title)
    ws.merge_cells(f"A1:{last_col_letter}1")
    title = ws["A1"]
    title.value = "AI MEP INSPECTION REPORT"
    title.font = Font(size=16, bold=True, color=HEADER_FONT_COLOR, name=DEFAULT_FONT_NAME)
    title.fill = PatternFill("solid", fgColor=TITLE_BANNER_COLOR)
    title.alignment = Alignment(horizontal="center", vertical="center")

    # Metadata rows below title
    generated_date = datetime.now().strftime("%Y-%m-%d")
    report_number = f"REP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    project_val = (results[0].get("project") if results and isinstance(results, (list, tuple)) and results[0] else "")
    inspection_date = (results[0].get("inspection_date") if results and isinstance(results, (list, tuple)) and results[0] else "")

    # Row 2: Report Number / Project
    ws.cell(row=2, column=1, value="Report Number")
    ws.cell(row=2, column=2, value=report_number)
    ws.cell(row=2, column=3, value="Project")
    ws.cell(row=2, column=4, value=project_val)

    # Row 3: Inspection Date / Generated Date
    ws.cell(row=3, column=1, value="Inspection Date")
    ws.cell(row=3, column=2, value=inspection_date)
    ws.cell(row=3, column=3, value="Generated Date")
    ws.cell(row=3, column=4, value=generated_date)

    # Header row index (leave a blank row at 4 for spacing)
    header_row = 5

    # Build headers using selected fields only
    headers = [_field_labels(field) for field in fields]

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    header_fill = PatternFill("solid", fgColor=HEADER_FILL_COLOR)
    alt_fill = PatternFill("solid", fgColor=ALT_ROW_FILL)

    # Suggested default widths
    width_map = {
        "image": 28,
        "snag_description": 60,
        "recommendation": 60,
        "category": 20,
        "severity": 15,
        "discipline": 20,
        "location": 25,
        "equipment": 25,
    }

    widths = [width_map.get(field, 20) for field in fields]

    # Apply column widths
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Create header cells
    for col_idx, text in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=text)
        cell.font = Font(bold=True, color=HEADER_FONT_COLOR, name=DEFAULT_FONT_NAME, size=DEFAULT_FONT_SIZE)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    # Ensure upload resize folder exists
    os.makedirs("uploads/resized", exist_ok=True)

    # Data rows start after header
    row = header_row + 1

    for i, item in enumerate(results, start=1):
        filtered_item = filter_analysis_payload(item, fields)

        # Determine if this row should use alternate fill
        row_fill = alt_fill if (row % 2 == 0) else PatternFill("solid", fgColor="FFFFFF")

        # Image column index (if present)
        image_col_index = fields.index("image") + 1 if "image" in fields else None
        image_present = False
        image_pixel_box = (140, 140)  # width, height in pixels (approx 120-150)

        # First write non-image cell values, style them and estimate text height
        max_text_height_pts = 0
        for col_idx, field in enumerate(fields, start=1):
            value = filtered_item.get(field, "")
            cell = ws.cell(row=row, column=col_idx)

            # Do not write the filename into the Image cell
            if field == "image":
                cell.value = None
            else:
                # Convert to string and write
                cell_value = "" if value is None else str(value)
                cell.value = cell_value

                # Estimate wrapped text height for this cell
                col_width_chars = widths[col_idx - 1]
                # approximate characters per line (tuned for Calibri 11)
                chars_per_line = max(20, int(col_width_chars * 1.2))
                lines = math.ceil(len(cell_value) / chars_per_line) if cell_value else 1
                # line height approx 14 points for Calibri 11
                text_height = lines * (DEFAULT_FONT_SIZE + 3)
                if text_height > max_text_height_pts:
                    max_text_height_pts = text_height

            # Style cell
            cell.border = border
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            cell.font = Font(name=DEFAULT_FONT_NAME, size=DEFAULT_FONT_SIZE)
            cell.fill = row_fill

        # Severity cell coloured background if present
        if "severity" in fields:
            sev_idx = fields.index("severity") + 1
            ws.cell(row, sev_idx).fill = _severity_fill(item.get("severity", ""))

        # Handle image insertion after text cells so we can compute row height
        if image_col_index:
            image_name = item.get("image")
            if image_name:
                image_path = os.path.join("uploads", image_name)
                if os.path.exists(image_path):
                    try:
                        # Read original image
                        orig = Image.open(image_path).convert("RGB")
                        orig_w, orig_h = orig.size

                        # Column metrics: width in characters -> approximate pixels
                        col_idx = image_col_index
                        col_letter = get_column_letter(col_idx)
                        col_width_chars = ws.column_dimensions[col_letter].width or widths[col_idx - 1]
                        cell_width_px = int(col_width_chars * 7)
 
                        # Target row height for image rows (about 120 points)
                        min_row_height_pts = 120
                        min_row_height_px = int(min_row_height_pts * 1.3333)
 
                        # Padding inside cell (pixels)
                        padding_px = 8
 
                        # Current text-estimated row height in points -> pixels
                        current_row_height_pts = ws.row_dimensions[row].height or int(max_text_height_pts or 18)
                        current_row_height_px = int(current_row_height_pts * 1.3333)
                        row_height_px = max(min_row_height_px, current_row_height_px)
                        available_h = max(1, row_height_px - 2 * padding_px)
 
                        # Compute available box for image inside the cell, capped to 140x140 px
                        max_box_px = 140
                        box_w = min(max(1, cell_width_px - 2 * padding_px), max_box_px)
                        box_h = min(available_h, max_box_px)
 
                        # Compute scale factor, preserve aspect ratio
                        scale = min(box_w / orig_w, box_h / orig_h, 1.0)
                        target_w = max(1, int(orig_w * scale))
                        target_h = max(1, int(orig_h * scale))
 
                        # Resize image before inserting
                        resized_img = orig.resize((target_w, target_h), Image.LANCZOS)
 
                        # Create canvas sized to the full cell width and desired row height to center image
                        canvas_w = cell_width_px
                        canvas_h = row_height_px
                        canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
                        paste_x = max(0, (canvas_w - target_w) // 2)
                        paste_y = max(0, (canvas_h - target_h) // 2)
                        canvas.paste(resized_img, (paste_x, paste_y))

                        resized_name = f"resized_{i}_{os.path.basename(image_name)}"
                        resized_path = os.path.join("uploads", "resized", resized_name)
                        canvas.save(resized_path, format="JPEG", quality=90)

                        xl = XLImage(resized_path)
 
                        # Use the canvas dimensions so the image occupies the full cell area and is centered inside it
                        xl.width = canvas_w
                        xl.height = canvas_h
 
                        anchor_cell = f"{col_letter}{row}"

                        # Try to set the anchor to span the cell so it moves and resizes with the cell
                        try:
                            if hasattr(xl, 'anchor') and hasattr(xl.anchor, '_from'):
                                xl.anchor._from.col = col_idx - 1
                                xl.anchor._from.row = row - 1
                                if hasattr(xl.anchor, '_to'):
                                    xl.anchor._to.col = col_idx
                                    xl.anchor._to.row = row
                                    xl.anchor._from.colOff = 0
                                    xl.anchor._from.rowOff = 0
                                    xl.anchor._to.colOff = 0
                                    xl.anchor._to.rowOff = 0
                        except Exception:
                            pass

                        # Add the image (canvas contains the centered photo with padding)
                        ws.add_image(xl, anchor_cell)

                        # Set the row height to fit the canvas (1 px ~= 0.75 points)
                        final_row_height_px = canvas_h
                        new_row_height_pts = max(current_row_height_pts, int(final_row_height_px * 0.75) + 2)
                        ws.row_dimensions[row].height = new_row_height_pts

                        image_present = True
                        image_height_points = int(target_h * 0.75)
                    except Exception:
                        image_present = False
                        image_height_points = 0
                else:
                    image_present = False
                    image_height_points = 0
            else:
                image_present = False
                image_height_points = 0
        else:
            image_height_points = 0

        # Determine final row height in points
        if image_present:
            final_height_pts = max(120, max_text_height_pts or 0, int(image_height_points or 0))
        else:
            final_height_pts = max(18, max_text_height_pts or 0)
        ws.row_dimensions[row].height = final_height_pts

        row += 1

    # Freeze panes so header is always visible
    ws.freeze_panes = f"A{header_row + 1}"

    # Apply print settings
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = False
    ws.print_title_rows = f"{header_row}:{header_row}"
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.75
    ws.page_margins.bottom = 0.75
    try:
        ws.oddFooter.center.text = "Generated by AI MEP Inspection Platform"
    except Exception:
        # Older openpyxl versions may have different footer API — ignore safely
        pass

    # Ensure directory exists and save
    os.makedirs(os.path.dirname(filename) or "reports", exist_ok=True)
    wb.save(filename)

    return filename
