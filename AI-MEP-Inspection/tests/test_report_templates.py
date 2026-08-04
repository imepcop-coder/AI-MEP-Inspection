from pathlib import Path

from openpyxl import load_workbook

from app.excel.report_generator import create_report, filter_analysis_payload
from app.models.report_template import ReportTemplate


def test_template_payload_filtering_and_excel_generation(tmp_path):
    template = ReportTemplate(
        name="Simple Snag Report",
        description="Basic report",
        fields=["image", "snag_description", "recommendation"],
        is_default=False,
    )

    payload = {
        "image": "sample.png",
        "snag_description": "Loose cable on the access walkway.",
        "recommendation": "Replace the cable and inspect the route.",
        "severity": "High",
        "discipline": "Electrical",
    }

    filtered = filter_analysis_payload(payload, template.fields)
    assert set(filtered.keys()) == {"image", "snag_description", "recommendation"}
    assert "severity" not in filtered

    output_path = tmp_path / "template_report.xlsx"
    report_path = create_report(
        [{"image": "sample.png", "snag_description": "Loose cable", "recommendation": "Secure it"}],
        filename=str(output_path),
        template=template,
    )

    assert Path(report_path).exists()
    workbook = load_workbook(report_path)
    sheet = workbook.active
    assert sheet.title == "Simple Snag Report"
    assert sheet["A2"].value == "Image"
    assert sheet["B2"].value == "Snag Description"
    assert sheet["C2"].value == "Recommendation"
