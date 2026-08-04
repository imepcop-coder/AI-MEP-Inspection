from app.excel.report_generator import create_report

data = [
    {
        "image": "HVAC.jpg",
        "discipline": "Electrical",
        "location": "Ceiling",
        "observation": "Exposed wiring and cables without proper insulation or protection",
        "severity": "High"
    }
]

file = create_report(data)

print(file)