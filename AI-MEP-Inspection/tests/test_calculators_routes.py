from fastapi.testclient import TestClient

from app.main import app


def test_calculator_category_pages_load():
    client = TestClient(app)
    for path in ["/calculators", "/calculators/plumbing", "/calculators/electrical", "/calculators/fire-fighting"]:
        response = client.get(path)
        assert response.status_code == 200


def test_shared_calculator_template_keeps_inputs_before_results():
    client = TestClient(app)
    response = client.get(
        "/calculators/fire/fire-flow",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/fire/fire-flow"},
    )
    assert response.status_code == 200
    html = response.text
    assert 'Inputs' in html
    assert 'Results' in html
    assert html.index('Inputs') < html.index('Results')
    assert 'order-lg-1' in html and 'order-lg-2' in html


def test_heat_load_template_has_single_standardized_layout():
    client = TestClient(app)
    response = client.get(
        "/calculators/heat-load",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/heat-load"},
    )
    assert response.status_code == 200
    html = response.text
    assert html.count('<form method="POST"') == 1
    assert html.count('Engineering Summary') == 1
    assert 'Professional HVAC Heat Load Calculator' in html


def test_static_pressure_template_has_single_standardized_layout():
    client = TestClient(app)
    response = client.get(
        "/calculators/static-pressure",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/static-pressure"},
    )
    assert response.status_code == 200
    html = response.text
    assert html.count('<form method="POST"') == 1
    assert html.count('Engineering Summary') == 1
    assert 'Professional HVAC Static Pressure Calculator' in html


def test_airflow_template_has_single_standardized_layout():
    client = TestClient(app)
    response = client.get(
        "/calculators/airflow",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/airflow"},
    )
    assert response.status_code == 200
    html = response.text
    assert html.count('<form method="POST"') == 1
    assert html.count('Engineering Summary') == 1
    assert 'Professional HVAC Air Flow Calculator' in html


def test_chilled_water_template_has_single_standardized_layout():
    client = TestClient(app)
    response = client.get(
        "/calculators/chilled-water",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/chilled-water"},
    )
    assert response.status_code == 200
    html = response.text
    assert html.count('<form method="POST"') == 1
    assert html.count('Engineering Summary') == 1
    assert 'Professional HVAC Chilled Water Calculator' in html


def test_duct_sizing_template_has_single_standardized_layout():
    client = TestClient(app)
    response = client.get(
        "/calculators/duct-sizing",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/duct-sizing"},
    )
    assert response.status_code == 200
    html = response.text
    assert html.count('<form method="POST"') == 1
    assert html.count('Engineering Summary') == 1
    assert 'Professional HVAC Duct Sizing Calculator' in html


def test_fresh_air_template_has_single_standardized_layout():
    client = TestClient(app)
    response = client.get(
        "/calculators/fresh-air",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/fresh-air"},
    )
    assert response.status_code == 200
    html = response.text
    assert html.count('<form method="POST"') == 1
    assert html.count('Engineering Summary') == 1
    assert 'Professional HVAC Fresh Air Calculator' in html


def test_pump_head_template_has_single_standardized_layout():
    client = TestClient(app)
    response = client.get(
        "/calculators/pump-head",
        headers={"origin": "http://testserver", "referer": "http://testserver/calculators/pump-head"},
    )
    assert response.status_code == 200
    html = response.text
    assert html.count('<form method="POST"') == 1
    assert html.count('Engineering Summary') == 1
    assert 'Professional HVAC Pump Head Calculator' in html
