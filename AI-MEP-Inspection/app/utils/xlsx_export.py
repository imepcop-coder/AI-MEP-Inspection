from __future__ import annotations

from datetime import datetime
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as ReportLabImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


COMPANY_NAME = "MEP Engineering Studio"
BRAND_PRIMARY = "0F172A"
BRAND_ACCENT = "1D4ED8"
BRAND_MUTED = "E2E8F0"


def _header_fill():
    return PatternFill("solid", fgColor=BRAND_ACCENT)


def _title_fill():
    return PatternFill("solid", fgColor="D9E1F2")


def _border():
    thin = Side(style="thin", color="000000")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_field_label(field_name: str, page: dict | None = None) -> str:
    if page and page.get("fields"):
        for field in page["fields"]:
            if field.get("name") == field_name:
                return field.get("label", field_name.replace("_", " ").title())
    return field_name.replace("_", " ").title()


def _format_values_ordered(values: dict, page: dict | None = None) -> list[tuple[str, str]]:
    """
    Format values while supporting:

    - Normal values
    - Nested dictionaries
    - Lists
    - Engineering summary
    - Engineering references
    """

    ordered = []
    seen = set()

    if page and page.get("fields"):

        for field in page["fields"]:

            name = field.get("name")

            if name not in values:
                continue

            value = values[name]

            label = field.get(
                "label",
                _format_field_label(name, page),
            )

            if isinstance(value, dict):

                ordered.append((label, ""))

                for k, v in value.items():

                    ordered.append(
                        (
                            f"   {k}",
                            str(v),
                        )
                    )

            elif isinstance(value, list):

                ordered.append(
                    (
                        label,
                        "\n".join(str(i) for i in value),
                    )
                )

            else:

                ordered.append(
                    (
                        label,
                        str(value),
                    )
                )

            seen.add(name)

    for key, value in values.items():

        if key in seen:
            continue

        label = key.replace("_", " ").title()

        if isinstance(value, dict):

            ordered.append((label, ""))

            for k, v in value.items():

                ordered.append(
                    (
                        f"   {k}",
                        str(v),
                    )
                )

        elif isinstance(value, list):

            ordered.append(
                (
                    label,
                    "\n".join(str(i) for i in value),
                )
            )

        else:

            ordered.append(
                (
                    label,
                    str(value),
                )
            )

    return ordered


def _build_summary_rows(page: dict | None = None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if page is None:
        return rows
    if page.get("description"):
        rows.append(("Description", page["description"]))
    if page.get("formula"):
        rows.append(("Formula", page["formula"]))
    if page.get("reference"):
        rows.append(("Reference", page["reference"]))
    if page.get("recommendation"):
        rows.append(("Recommendation", page["recommendation"]))
    return rows


def _build_recommendations(page: dict | None = None) -> list[str]:
    if page and page.get("recommendation"):
        return [page["recommendation"]]
    return [
        "Verify the output against the project design criteria and local engineering standards.",
        "Review equipment and construction constraints before finalizing the design.",
    ]


def _build_calculation_diagram(values: dict, results: dict, page: dict | None = None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    ordered_inputs = _format_values_ordered(values, page)
    if ordered_inputs:
        rows.append(("Input Parameter", "Value"))
        rows.extend((label, str(value)) for label, value in ordered_inputs)
    ordered_results = _format_values_ordered(results, page)
    if ordered_results:
        if ordered_inputs:
            rows.append(("", ""))
        rows.append(("Result Parameter", "Value"))
        rows.extend((label, str(value)) for label, value in ordered_results)
    return rows


def _infer_standard(title: str, page: dict | None = None) -> list[str]:
    text = f"{title} {' '.join([str(item.get('title', '')) for item in (page.get('categories', []) if isinstance(page, dict) else [])])}".lower()
    if "duct" in text or "airflow" in text or "ventilation" in text:
        return ["ASHRAE 62.1", "ASHRAE 90.1", "SMACNA Duct Design"]
    if "pump" in text or "pipe" in text or "water" in text:
        return ["IPC", "ASHRAE Handbook", "NFPA 13 / 14"]
    if "fire" in text:
        return ["NFPA 13", "NFPA 20", "NFPA 24"]
    if "cable" in text or "voltage" in text or "transformer" in text or "breaker" in text:
        return ["IEC 60364", "NEC / IEC", "IEEE 141"]
    if "network" in text or "rack" in text or "cable" in text:
        return ["TIA-568", "IEC 11801", "BICSI"]
    return ["ASHRAE", "IPC", "NFPA", "IEC"]


def _equipment_recommendations(title: str, page: dict | None = None) -> list[str]:
    lower = (title or "").lower()
    if "pump" in lower or "water" in lower or "pipe" in lower:
        return ["Recommended Pump", "Recommended Tank", "Recommended Pipe", "Recommended Control Valve"]
    if "fire" in lower or "hydrant" in lower:
        return ["Recommended Fire Pump", "Recommended Tank", "Recommended Pipe", "Recommended Hydrant Layout"]
    if "cable" in lower or "breaker" in lower or "transformer" in lower:
        return ["Recommended Cable", "Recommended Breaker", "Recommended Transformer", "Recommended Panelboard"]
    if "duct" in lower or "air" in lower or "load" in lower or "chilled" in lower:
        return ["Recommended AHU", "Recommended Chiller", "Recommended Pump", "Recommended Pipe"]
    return ["Recommended Equipment Set", "Recommended Control Strategy", "Recommended Service Margin"]


def _build_chart_config(title: str, inputs: dict, results: dict) -> dict:
    lower = (title or "").lower()
    result_items = _format_values_ordered(results)

    if not result_items:
        if not inputs:
            return {"chart_type": "bar", "labels": ["Design Input"], "values": [1], "title": title}
        data = _format_values_ordered(inputs)
        labels = [item[0][:14] for item in data[:6]]
        values = [float(item[1]) if _safe_float(item[1]) is not None else 1 for item in data[:6]]
        return {"chart_type": "bar", "labels": labels, "values": values, "title": f"{title} Input Profile"}

    labels = [item[0][:20] for item in result_items[:6]]
    values = []
    for _, value in result_items[:6]:
        numeric = _safe_float(value)
        values.append(numeric if numeric is not None else 1)

    if "load" in lower or "demand" in lower or "flow" in lower:
        chart_type = "pie"
    elif "pump" in lower or "head" in lower or "pressure" in lower or "loss" in lower:
        chart_type = "line"
    else:
        chart_type = "bar"

    return {"chart_type": chart_type, "labels": labels, "values": values, "title": f"{title} Performance"}


def _generate_chart_image(title: str, inputs: dict, results: dict) -> BytesIO:
    config = _build_chart_config(title, inputs, results)
    labels = config["labels"]
    values = config["values"]
    fig, ax = plt.subplots(figsize=(7, 4.2))

    if config["chart_type"] == "pie":
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title(config["title"], fontsize=11)
    elif config["chart_type"] == "line":
        ax.plot(range(len(labels)), values, marker="o", linewidth=2.5, color="#2563eb")
        ax.set_title(config["title"], fontsize=11)
        ax.set_xticks(list(range(len(labels))))
        ax.set_xticklabels(labels, rotation=35, ha="right")
        ax.grid(True, linestyle="--", alpha=0.3)
    else:
        ax.bar(labels, values, color="#2563eb", edgecolor="#0f172a", alpha=0.8)
        ax.set_title(config["title"], fontsize=11)
        ax.tick_params(axis="x", rotation=30)
        ax.grid(True, axis="y", linestyle="--", alpha=0.2)

    fig.tight_layout()
    output = BytesIO()
    fig.savefig(output, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    output.seek(0)
    return output


def _build_step_by_step(formula: str | None, inputs: dict, results: dict) -> list[str]:
    steps: list[str] = []
    input_items = _format_values_ordered(inputs)
    result_items = _format_values_ordered(results)
    if input_items:
        steps.append(f"1. Input data established from project conditions: {', '.join(f'{label}={value}' for label, value in input_items[:3])}.")
    if formula:
        steps.append(f"2. Apply the engineering equation: {formula}.")
    if result_items:
        steps.append(f"3. Calculate the governing parameters and confirm the final output: {', '.join(f'{label}={value}' for label, value in result_items[:3])}.")
    steps.append("4. Verify serviceability, operational margin, and compliance with the applicable engineering standards before final release.")
    return steps


def _draw_header(canvas, doc, title: str, project_name: str | None, client_name: str | None, engineer_name: str | None):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(colors.HexColor("#0F172A"))
    canvas.rect(doc.leftMargin, height - doc.topMargin + 20, width - doc.leftMargin - doc.rightMargin, 0.8 * inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(doc.leftMargin + 0.18 * inch, height - doc.topMargin + 42, COMPANY_NAME)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin + 0.18 * inch, height - doc.topMargin + 28, f"Project: {project_name or 'Untitled Project'}")
    canvas.drawString(doc.leftMargin + 0.18 * inch, height - doc.topMargin + 16, f"Client: {client_name or 'Client TBD'}   Engineer: {engineer_name or 'Engineer TBD'}")
    canvas.restoreState()


def _draw_footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(doc.leftMargin, 0.52 * inch, "MEP Engineering Studio | Consultant Report")
    canvas.drawRightString(width - doc.rightMargin, 0.52 * inch, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _on_page(canvas, doc, title: str, project_name: str | None, client_name: str | None, engineer_name: str | None):
    _draw_header(canvas, doc, title, project_name, client_name, engineer_name)
    _draw_footer(canvas, doc)


def build_calculator_pdf(
    title: str,
    inputs: dict,
    results: dict,
    page: dict | None = None,
    project_name: str | None = None,
    client_name: str | None = None,
    engineer_name: str | None = None,
):
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch * 1.1,
        bottomMargin=inch * 0.9,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        alignment=1,
        fontSize=19,
        leading=22,
        spaceAfter=10,
        textColor=colors.HexColor("#0F172A"),
    )
    heading_style = ParagraphStyle(
        "Heading2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=14,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#0F172A"),
    )
    normal_style = styles["BodyText"]
    normal_style.spaceAfter = 5

    story = [Paragraph(f"{title} Engineering Report", title_style)]
    generated_date = datetime.now().strftime("%Y-%m-%d")

    meta_rows = [
        ["Company", COMPANY_NAME, "Project", project_name or "Untitled Project"],
        ["Client", client_name or "Client TBD", "Engineer", engineer_name or "Engineer TBD"],
        ["Date", generated_date, "Calculator", title],
    ]
    meta_table = Table(meta_rows, colWidths=[1.2 * inch, 2 * inch, 1.2 * inch, 2 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 12))

    if page and page.get("formula"):
        story.append(Paragraph("Engineering Formula", heading_style))
        story.append(Paragraph(page["formula"], normal_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Input Table", heading_style))
    input_rows = [[label, str(value)] for label, value in _format_values_ordered(inputs, page)]
    input_table = Table([["Parameter", "Value"]] + input_rows, colWidths=[2.5 * inch, 4.0 * inch])
    input_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(input_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Step-by-Step Calculations", heading_style))
    for step in _build_step_by_step(page.get("formula") if page else None, inputs, results):
        story.append(Paragraph(step, normal_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Final Results", heading_style))
    result_rows = [[label, str(value)] for label, value in _format_values_ordered(results, page)]
    result_table = Table([["Result", "Value"]] + result_rows, colWidths=[2.5 * inch, 4.0 * inch])
    result_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(result_table)
    story.append(Spacer(1, 12))

    chart_buffer = _generate_chart_image(title, inputs, results)
    story.append(Paragraph("Engineering Diagram", heading_style))
    chart_image = ReportLabImage(chart_buffer, width=5.8 * inch, height=3.2 * inch)
    story.append(chart_image)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommendations", heading_style))
    for item in _build_recommendations(page):
        story.append(Paragraph(f"• {item}", normal_style))

    story.append(Paragraph("Applicable Standards", heading_style))
    for standard in _infer_standard(title, page):
        story.append(Paragraph(f"• {standard}", normal_style))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Equipment Selection", heading_style))
    for item in _equipment_recommendations(title, page):
        story.append(Paragraph(f"• {item}", normal_style))

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: _on_page(canvas, doc, title, project_name, client_name, engineer_name),
        onLaterPages=lambda canvas, doc: _on_page(canvas, doc, title, project_name, client_name, engineer_name),
    )
    output.seek(0)
    return output


def build_calculator_workbook(
    title: str,
    inputs: dict,
    results: dict,
    page: dict | None = None,
    project_name: str | None = None,
    client_name: str | None = None,
    engineer_name: str | None = None,
):
    wb = Workbook()
    summary_ws = wb.active
    summary_ws.title = "Summary"

    trend_fill = PatternFill("solid", fgColor="0F172A")
    head_fill = PatternFill("solid", fgColor="D9E1F2")

    summary_ws.merge_cells("A1:F1")
    summary_ws["A1"] = f"{title} Engineering Workbook"
    summary_ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    summary_ws["A1"].fill = trend_fill
    summary_ws["A1"].alignment = Alignment(horizontal="center")

    generated_date = datetime.now().strftime("%Y-%m-%d")
    summary_rows = [
        ["Company", COMPANY_NAME, "Project", project_name or "Untitled Project", "Date", generated_date],
        ["Client", client_name or "Client TBD", "Engineer", engineer_name or "Engineer TBD", "Calculator", title],
    ]
    for row_idx, row in enumerate(summary_rows, start=2):
        for col_idx, value in enumerate(row, start=1):
            cell = summary_ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = _border()
            cell.font = Font(bold=True if col_idx % 2 == 1 else False)
            cell.fill = head_fill if col_idx % 2 == 1 else PatternFill("solid", fgColor="F8FAFC")
            cell.alignment = Alignment(horizontal="left")

    inputs_ws = wb.create_sheet("Inputs")
    inputs_rows = [["Parameter", "Value"]] + [[label, str(value)] for label, value in _format_values_ordered(inputs, page)]
    for row_idx, row in enumerate(inputs_rows, start=1):
        for col_idx, value in enumerate(row, start=1):
            cell = inputs_ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = _border()
            if row_idx == 1:
                cell.fill = _header_fill()
                cell.font = Font(bold=True, color="FFFFFF")
            else:
                cell.fill = PatternFill("solid", fgColor="F8FAFC") if (row_idx % 2 == 0) else PatternFill("solid", fgColor="FFFFFF")

    calc_ws = wb.create_sheet("Engineering Calculations")
    calc_ws["A1"] = "Formula"
    calc_ws["A1"].font = Font(bold=True)
    calc_ws["A2"] = page.get("formula") if page and page.get("formula") else "Engineering equation applied to the project inputs"
    calc_ws["A2"].alignment = Alignment(wrap_text=True)
    calc_ws["A5"] = "Step-by-Step Calculation"
    calc_ws["A5"].font = Font(bold=True)
    for index, step in enumerate(_build_step_by_step(page.get("formula") if page else None, inputs, results), start=7):
        calc_ws[f"A{index}"] = step
        calc_ws[f"A{index}"].alignment = Alignment(wrap_text=True)

    results_ws = wb.create_sheet("Results")
    results_rows = [["Result", "Value"]] + [[label, str(value)] for label, value in _format_values_ordered(results, page)]
    for row_idx, row in enumerate(results_rows, start=1):
        for col_idx, value in enumerate(row, start=1):
            cell = results_ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = _border()
            if row_idx == 1:
                cell.fill = _header_fill()
                cell.font = Font(bold=True, color="FFFFFF")
            else:
                cell.fill = PatternFill("solid", fgColor="F8FAFC") if row_idx % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")

    charts_ws = wb.create_sheet("Charts")
    chart_buffer = _generate_chart_image(title, inputs, results)
    chart_image = Image(chart_buffer)
    chart_image.width = 760
    chart_image.height = 420
    charts_ws.add_image(chart_image, "A1")
    charts_ws["A1"].value = "Dynamic Engineering Diagram"
    charts_ws["A1"].font = Font(bold=True)

    equipment_ws = wb.create_sheet("Equipment Selection")
    equipment_ws["A1"] = "Recommended Equipment"
    equipment_ws["A1"].font = Font(bold=True, size=12)
    for index, item in enumerate(_equipment_recommendations(title, page), start=2):
        equipment_ws[f"A{index}"] = item
        equipment_ws[f"A{index}"].border = _border()

    notes_ws = wb.create_sheet("Design Notes")
    notes_ws["A1"] = "Recommendations"
    notes_ws["A1"].font = Font(bold=True)
    for index, item in enumerate(_build_recommendations(page), start=2):
        notes_ws[f"A{index}"] = item
        notes_ws[f"A{index}"].alignment = Alignment(wrap_text=True)
        notes_ws[f"A{index}"].border = _border()
    notes_ws["A10"] = "Applicable Standards"
    notes_ws["A10"].font = Font(bold=True)
    for index, item in enumerate(_infer_standard(title, page), start=11):
        notes_ws[f"A{index}"] = item
        notes_ws[f"A{index}"].border = _border()

    for variant in [summary_ws, inputs_ws, calc_ws, results_ws, charts_ws, equipment_ws, notes_ws]:
        for column_cells in variant.columns:
            cells = [cell for cell in column_cells if getattr(cell, "value", None) is not None]
            if not cells:
                continue
            max_width = max(len(str(cell.value)) for cell in cells)
            variant.column_dimensions[cells[0].column_letter].width = max(max_width + 2, 18)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
