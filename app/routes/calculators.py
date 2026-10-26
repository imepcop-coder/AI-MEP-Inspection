from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import values
import logging
from pydantic import ValidationError

from app.services.duct_calculator import (
    calculate_rectangular_duct,
    calculate_round_duct,
    DuctCalculationError,
)

from app.services.heat_load import (
    calculate_heat_load,
    HeatLoadCalculationError,
)

from app.services.airflow import (
    calculate_airflow,
    AirFlowCalculationError,
)

from app.services.fresh_air import (
    calculate_fresh_air,
    FreshAirCalculationError,
)

from app.services.chilled_water import (
    calculate_chilled_water,
    ChilledWaterCalculationError,
)

from app.services.pump_head import (
    calculate_pump_head,
    PumpHeadCalculationError,
)

from app.services.static_pressure import (
    calculate_static_pressure,
    StaticPressureCalculationError,
)
from app.utils.xlsx_export import build_calculator_pdf, build_calculator_workbook
from app.routes.plumbing_page import PLUMBING_PAGES, PLUMBING_SCHEMAS, PLUMBING_HANDLERS

router = APIRouter()
logger = logging.getLogger("ai_mep")

HVAC_CALCULATORS = {
    "duct-sizing": {
        "title": "HVAC Duct Sizing Calculator",
        "description": "Estimate duct sizing based on required airflow and velocity.",
        "fields": [
            {"name": "duct_type", "label": "Duct Type", "type": "select"},
            {"name": "airflow", "label": "Air Flow (CFM)", "type": "number"},
            {"name": "velocity", "label": "Velocity (FPM)", "type": "number"},
        ],
        "formula": "A = Q / V where Q is airflow and V is velocity.",
        "reference": "Duct sizing formulas for air distribution systems.",
        "recommendation": "Verify calculated duct dimensions against acoustic and space constraints, and coordinate with grilles and diffusers.",
        "result_key": "area_sqft",
        "result_unit": "sq.ft",
    },
    "heat-load": {
        "title": "HVAC Heat Load Calculator",
        "description": "Estimate sensible cooling load for a conditioned space.",
        "fields": [
            {"name": "length", "label": "Room Length (m)", "type": "number"},
            {"name": "width", "label": "Room Width (m)", "type": "number"},
            {"name": "height", "label": "Room Height (m)", "type": "number"},
            {"name": "occupants", "label": "Occupants", "type": "number"},
            {"name": "lighting", "label": "Lighting Load (W)", "type": "number"},
            {"name": "equipment", "label": "Equipment Load (W)", "type": "number"},
        ],
        "formula": "Total Load = room sensible load + people load + lighting + equipment.",
        "reference": "Simplified cooling load estimation for engineering design.",
        "recommendation": "Validate results with building occupancy schedules and overheating factors before selecting equipment.",
        "result_key": "required_cfm",
        "result_unit": "CFM",
    },
    "airflow": {
        "title": "HVAC Air Flow Calculator",
        "description": "Calculate ventilation air flow based on room volume and air changes per hour.",
        "fields": [
            {"name": "length", "label": "Room Length (m)", "type": "number"},
            {"name": "width", "label": "Room Width (m)", "type": "number"},
            {"name": "height", "label": "Room Height (m)", "type": "number"},
            {"name": "air_changes", "label": "Air Changes Per Hour (ACH)", "type": "number"},
        ],
        "formula": "Q = Volume × ACH.",
        "reference": "Ventilation design using room volume and required air changes.",
        "recommendation": "Confirm air change requirements with occupancy and contamination control criteria.",
        "result_key": "airflow_cfm",
        "result_unit": "CFM",
    },
    "fresh-air": {
        "title": "HVAC Fresh Air Calculator",
        "description": "Estimate fresh air requirement from occupancy and floor area.",
        "fields": [
            {"name": "occupants", "label": "Occupants", "type": "number"},
            {"name": "area", "label": "Area (m²)", "type": "number"},
            {"name": "fresh_air_per_person", "label": "Fresh Air Per Person (CFM)", "type": "number"},
            {"name": "fresh_air_per_area", "label": "Fresh Air Per Area (CFM/m²)", "type": "number"},
        ],
        "formula": "Total fresh air = people air + area air.",
        "reference": "Mechanical ventilation fresh air requirements.",
        "recommendation": "Coordinate fresh air intake capacity with central air handling unit design.",
        "result_key": "total_cfm",
        "result_unit": "CFM",
    },
    "chilled-water": {
        "title": "HVAC Chilled Water Flow Calculator",
        "description": "Estimate chilled water flow and pipe size for cooling load.",
        "fields": [
            {"name": "cooling_load", "label": "Cooling Load (kW)", "type": "number"},
            {"name": "delta_t", "label": "Temperature Difference (°C)", "type": "number"},
            {"name": "velocity", "label": "Pipe Velocity (m/s)", "type": "number"},
        ],
        "formula": "Q = kW / (4.186 × ΔT)",
        "reference": "Chilled water flow rate calculation for hydronic systems.",
        "recommendation": "Review system operating temperatures and pipe material selection during design.",
        "result_key": "flow_lpm",
        "result_unit": "LPM",
    },
    "pump-head": {
        "title": "HVAC Pump Head Calculator",
        "description": "Estimate hydraulic power and pump head required for fluid transport.",
        "fields": [
            {"name": "flow_rate", "label": "Flow Rate (m³/hr)", "type": "number"},
            {"name": "static_head", "label": "Static Head (m)", "type": "number"},
            {"name": "friction_loss", "label": "Friction Loss (m)", "type": "number"},
            {"name": "efficiency", "label": "Efficiency (%)", "type": "number"},
        ],
        "formula": "Pump power = 9.81 × Q × H / η.",
        "reference": "Pump hydraulic power calculation for system selection.",
        "recommendation": "Confirm pump selection with safety factors and service margins.",
        "result_key": "shaft_power",
        "result_unit": "kW",
    },
    "static-pressure": {
        "title": "HVAC Static Pressure Calculator",
        "description": "Calculate static pressure for ductwork based on velocity and friction loss.",
        "fields": [
            {"name": "airflow", "label": "Air Flow (CFM)", "type": "number"},
            {"name": "velocity", "label": "Air Velocity (m/s)", "type": "number"},
            {"name": "duct_length", "label": "Duct Length (m)", "type": "number"},
            {"name": "friction_rate", "label": "Friction Rate (Pa/m)", "type": "number"},
        ],
        "formula": "Total static pressure = velocity pressure + friction loss.",
        "reference": "Static pressure calculation for duct system design.",
        "recommendation": "Check fan selection and ductwork layout with the computed pressure drop.",
        "result_key": "total_static_pressure",
        "result_unit": "Pa",
    },
}


def _strip_project_name(form_data: dict) -> tuple[dict, str | None]:
    values = dict(form_data)
    project_name = values.pop("project_name", None)
    return values, project_name


def _run_hvac_calculation(slug: str, values: dict):
    if slug == "duct-sizing":
        if values.get("duct_type") == "Rectangular":
            return calculate_rectangular_duct(
                airflow=values.get("airflow"),
                velocity=values.get("velocity"),
            )
        return calculate_round_duct(
            airflow=values.get("airflow"),
            velocity=values.get("velocity"),
        )
    if slug == "heat-load":
        return calculate_heat_load(
            length=values.get("length"),
            width=values.get("width"),
            height=values.get("height"),
            occupants=values.get("occupants"),
            lighting=values.get("lighting"),
            equipment=values.get("equipment"),
        )
    if slug == "airflow":
        return calculate_airflow(
            length=values.get("length"),
            width=values.get("width"),
            height=values.get("height"),
            air_changes=values.get("air_changes"),
        )
    elif slug == "fire-flow":
        return calculate_fire_flow(
                                
        area_m2=values.get("area"),
        hazard_class=values.get("hazard_class"),
        )
    if slug == "chilled-water":
        return calculate_chilled_water(
            cooling_load=values.get("cooling_load"),
            delta_t=values.get("delta_t"),
            velocity=values.get("velocity"),
        )
    if slug == "pump-head":
        return calculate_pump_head(
            flow_rate=values.get("flow_rate"),
            static_head=values.get("static_head"),
            friction_loss=values.get("friction_loss"),
            efficiency=values.get("efficiency"),
        )
    if slug == "static-pressure":
        return calculate_static_pressure(
            airflow=values.get("airflow"),
            velocity=values.get("velocity"),
            duct_length=values.get("duct_length"),
            friction_rate=values.get("friction_rate"),
        )
    raise HTTPException(status_code=404, detail="Calculator not found.")


def _get_hvac_page(slug: str):
    page = HVAC_CALCULATORS.get(slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Calculator not found.")
    return page

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ==========================================================
# Calculator Dashboard
# ==========================================================

@router.get("/calculators")
async def calculators_dashboard(request: Request, category: str = None):

    calculators = [
        {
            "category": "HVAC",
            "items": [
                {
                    "name": "HVAC Duct Sizing",
                    "icon": "bi-wind",
                    "url": "/calculators/duct-sizing",
                    "description": "Size rectangular and circular ducts based on airflow and velocity.",
                },
                {
                    "name": "Heat Load",
                    "icon": "bi-thermometer-half",
                    "url": "/calculators/heat-load",
                    "description": "Estimate room cooling load and expected refrigeration demand.",
                },
                {
                    "name": "Air Flow",
                    "icon": "bi-fan",
                    "url": "/calculators/airflow",
                    "description": "Calculate ventilation airflow requirements for occupied spaces.",
                },
                {
                    "name": "Fresh Air",
                    "icon": "bi-cloud",
                    "url": "/calculators/fresh-air",
                    "description": "Determine outdoor air requirements and system intake rates.",
                },
                {
                    "name": "Chilled Water Flow",
                    "icon": "bi-droplet-half",
                    "url": "/calculators/chilled-water",
                    "description": "Size chilled water circuits for HVAC cooling systems.",
                },
                {
                    "name": "Pump Head",
                    "icon": "bi-water",
                    "url": "/calculators/pump-head",
                    "description": "Calculate pump head and power for hydronic systems.",
                },
                {
                    "name": "Static Pressure",
                    "icon": "bi-speedometer2",
                    "url": "/calculators/static-pressure",
                    "description": "Analyze pressure drop for ductwork and system performance.",
                },
            ],
        },
        {
            "category": "Plumbing",
            "items": [
                {
                    "name": "Water Demand",
                    "icon": "bi-droplet",
                    "url": "/calculators/plumbing/water-demand",
                    "description": "Estimate daily and peak water requirements for buildings.",
                },
                {
                    "name": "Fixture Units",
                    "icon": "bi-grid-3x3-gap",
                    "url": "/calculators/plumbing/fixture-unit",
                    "description": "Calculate load from sanitary fixtures and plumbing appliances.",
                },
                {
                    "name": "Pipe Sizing",
                    "icon": "bi-bezier2",
                    "url": "/calculators/plumbing/pipe-sizing",
                    "description": "Select pipe diameter using flow, velocity and standards.",
                },
                {
                    "name": "Drainage",
                    "icon": "bi-cloud-drizzle",
                    "url": "/calculators/plumbing/drainage-pipe",
                    "description": "Size wastewater stacks and drain piping for building drainage.",
                },
                {
                    "name": "Rainwater",
                    "icon": "bi-cloud-rain",
                    "url": "/calculators/plumbing/rainwater-pipe",
                    "description": "Compute roof rainwater pipe sizing and downpipe capacity.",
                },
                {
                    "name": "Water Tank",
                    "icon": "bi-tank-water",
                    "url": "/calculators/plumbing/water-tank",
                    "description": "Estimate storage capacity for service and emergency supply.",
                },
                {
                    "name": "Underground Sump",
                    "icon": "bi-funnel",
                    "url": "/calculators/plumbing/sump-tank",
                    "description": "Size sump storage to support pump duty cycles and relief.",
                },
                {
                    "name": "Pump Selection",
                    "icon": "bi-arrow-repeat",
                    "url": "/calculators/plumbing/pump-selection",
                    "description": "Match pump performance to flow, head and efficiency requirements.",
                },
            ],
        },
        {
            "category": "Fire Fighting",
            "items": [
                {
                    "name": "Fire Flow",
                    "icon": "bi-fire",
                    "url": "/calculators/fire/fire-flow",
                    "description": "Determine fire water demand from building hazard classification.",
                },
                {
                    "name": "Fire Pump Head",
                    "icon": "bi-tachometer",
                    "url": "/calculators/fire/fire-pump-head",
                    "description": "Calculate pump head requirements for fire suppression systems.",
                },
                {
                    "name": "Sprinkler Spacing",
                    "icon": "bi-droplet-half",
                    "url": "/calculators/fire/sprinkler-spacing",
                    "description": "Estimate sprinkler coverage and maximum allowable spacing.",
                },
                {
                    "name": "Standpipe Pressure",
                    "icon": "bi-water",
                    "url": "/calculators/fire/standpipe",
                    "description": "Compute standpipe pressure requirements for outlet service.",
                },
                {
                    "name": "Hose Reel Pressure",
                    "icon": "bi-funnel",
                    "url": "/calculators/fire/hose-reel-pressure",
                    "description": "Estimate nozzle and hose pressure for reel systems.",
                },
                {
                    "name": "Fire Water Tank",
                    "icon": "bi-tank-water",
                    "url": "/calculators/fire/fire-water-tank",
                    "description": "Calculate fire water storage based on duration and demand.",
                },
                {
                    "name": "Hydraulic Calculation",
                    "icon": "bi-speedometer2",
                    "url": "/calculators/fire/hydraulic-calculation",
                    "description": "Analyze friction loss and pressure drop for fire mains.",
                },
                {
                    "name": "Nozzle Pressure",
                    "icon": "bi-funnel",
                    "url": "/calculators/fire/nozzle-pressure",
                    "description": "Determine required outlet pressure for fire nozzles.",
                },
            ],
        },
        {
            "category": "Electrical",
            "items": [
                {
                    "name": "Cable Sizing",
                    "icon": "bi-plug",
                    "url": "/calculators/electrical/cable-sizing",
                    "description": "Size conductors for load, voltage drop and derating factors.",
                },
                {
                    "name": "Voltage Drop",
                    "icon": "bi-lightning-charge",
                    "url": "/calculators/electrical/voltage-drop",
                    "description": "Calculate voltage drop along feeders and branch circuits.",
                },
                {
                    "name": "Transformer Sizing",
                    "icon": "bi-building",
                    "url": "/calculators/electrical/transformer-sizing",
                    "description": "Estimate transformer kVA for load and power factor requirements.",
                },
                {
                    "name": "Generator Sizing",
                    "icon": "bi-battery-charging",
                    "url": "/calculators/electrical/generator-sizing",
                    "description": "Match generator capacity to connected load and starting demand.",
                },
                {
                    "name": "UPS Sizing",
                    "icon": "bi-battery-half",
                    "url": "/calculators/electrical/ups-sizing",
                    "description": "Calculate UPS rating and battery autonomy for critical loads.",
                },
            ],
        },
        {
            "category": "ELV",
            "items": [
                {
                    "name": "Lighting Lux",
                    "icon": "bi-lightbulb",
                    "url": "/calculators/electrical/lighting-lux",
                    "description": "Estimate lighting power for design illuminance levels.",
                },
                {
                    "name": "Circuit Breaker",
                    "icon": "bi-shield-lock",
                    "url": "/calculators/electrical/circuit-breaker",
                    "description": "Recommend breaker size using design current and safety margins.",
                },
                {
                    "name": "UPS Sizing",
                    "icon": "bi-battery-half",
                    "url": "/calculators/electrical/ups-sizing",
                    "description": "Plan backup power for low-voltage ELV and control systems.",
                },
            ],
        },
        {
            "category": "Inspection",
            "items": [
                {
                    "name": "Inspection Records",
                    "icon": "bi-journal-text",
                    "url": "/inspections",
                    "description": "Review recent inspection reports and project status.",
                },
                {
                    "name": "AI Assistant",
                    "icon": "bi-robot",
                    "url": "/assistant",
                    "description": "Use the AI assistant to generate inspection summaries and notes.",
                },
                {
                    "name": "Report Builder",
                    "icon": "bi-file-earmark-text",
                    "url": "/reports",
                    "description": "Generate professional QA/QC reports from inspection data.",
                },
                {
                    "name": "Project Workspace",
                    "icon": "bi-layout-text-window",
                    "url": "/dashboard",
                    "description": "Access your project dashboard and inspection workflow.",
                },
            ],
        },
    ]

    total_calculators = sum(len(category["items"]) for category in calculators)
    total_categories = len(calculators)
    selected_category = (category or "all").lower().replace(' ', '-')

    return templates.TemplateResponse(
        request=request,
        name="calculators/index.html",
        context={
            "request": request,
            "calculators": calculators,
            "total_calculators": total_calculators,
            "total_categories": total_categories,
            "selected_category": selected_category,
        },
    )


@router.get("/calculators/plumbing")
async def plumbing_suite(request: Request):
    return templates.TemplateResponse(request=request, name="calculators/plumbing.html", context={"request": request})


@router.get("/calculators/plumbing/{page_slug}")
async def plumbing_calculator(request: Request, page_slug: str):
    page = PLUMBING_PAGES.get(page_slug)
    if not page:
        raise HTTPException(status_code=404, detail="Calculator page not found.")
    values = {field["name"]: field.get("default", "") for field in page["fields"]}
    return templates.TemplateResponse(request=request, name="calculators/calculator_page.html", context={"request": request, "page": page, "values": values, "result": None, "error": None})


@router.post("/calculators/plumbing/{page_slug}")
async def plumbing_calculator_submit(request: Request, page_slug: str):
    page = PLUMBING_PAGES.get(page_slug)
    if not page:
        raise HTTPException(status_code=404, detail="Calculator page not found.")

    schema = PLUMBING_SCHEMAS.get(page_slug)
    handler = PLUMBING_HANDLERS.get(page_slug)
    form_data = dict((await request.form()).items())
    project_name = form_data.pop("project_name", None)
    values = {k: v for k, v in form_data.items()}
    result = None
    error = None

    try:
        validated = schema.parse_obj(values)
        calculation = handler(validated)
        result = calculation.dict() if hasattr(calculation, "dict") else calculation
    except ValidationError as ex:
        logger.warning("Validation error in plumbing calculation for %s: %s", page_slug, ex)
        try:
            from app.utils.validation import map_pydantic_errors
            field_errors = map_pydantic_errors(page, ex.errors())
        except Exception:
            field_errors = { (err.get('loc')[-1] if err.get('loc') else 'field'): err.get('msg') for err in ex.errors() }
        error = "Please check the highlighted fields and try again."
        return templates.TemplateResponse(request=request, name="calculators/calculator_page.html", context={"request": request, "page": page, "values": values, "result": None, "error": error, "field_errors": field_errors})
    except Exception as ex:
        logger.exception("Error running plumbing calculation for %s: %s", page_slug, ex)
        error = "Calculation could not be completed. Please verify your inputs and try again."

    return templates.TemplateResponse(request=request, name="calculators/calculator_page.html", context={"request": request, "page": page, "values": values, "result": result, "error": error})


@router.get("/calculators/plumbing/{page_slug}/print")
async def plumbing_calculator_print(request: Request, page_slug: str):
    page = PLUMBING_PAGES.get(page_slug)
    if not page:
        raise HTTPException(status_code=404, detail="Calculator page not found.")
    values = {field["name"]: field.get("default", "") for field in page["fields"]}
    return templates.TemplateResponse(request=request, name="calculators/calculator_page.html", context={"request": request, "page": page, "values": values, "result": None, "error": None})


@router.post("/calculators/plumbing/{page_slug}/export_excel")
async def calculators_plumbing_export_excel(request: Request, page_slug: str):
    schema = PLUMBING_SCHEMAS.get(page_slug)
    handler = PLUMBING_HANDLERS.get(page_slug)
    if schema is None or handler is None:
        raise HTTPException(status_code=404, detail="Excel export not supported for this calculator.")

    form_data = await request.form()
    values = dict(form_data)
    project_name = values.pop("project_name", None)

    try:
        validated = schema.parse_obj(values)
        result_obj = handler(validated)
        result = result_obj.dict() if hasattr(result_obj, "dict") else result_obj
    except ValidationError as ex:
        logger.warning("Validation error during Excel export for %s: %s", page_slug, ex)
        try:
            from app.utils.validation import map_pydantic_errors
            field_errors = map_pydantic_errors(page, ex.errors())
        except Exception:
            field_errors = { (err.get('loc')[-1] if err.get('loc') else 'field'): err.get('msg') for err in ex.errors() }
        raise HTTPException(status_code=400, detail={"errors": field_errors})
    except Exception as ex:
        logger.exception("Error during Excel export for %s: %s", page_slug, ex)
        raise HTTPException(status_code=400, detail="Calculation could not be completed. Please try again later.")

    page = PLUMBING_PAGES.get(page_slug)
    stream = build_calculator_workbook(
        page["title"] if page else page_slug,
        values,
        result,
        page=page,
        project_name=project_name,
    )
    stream.seek(0)

    response = StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response.headers["Content-Disposition"] = f"attachment; filename={page_slug}.xlsx"
    return response


@router.post("/calculators/plumbing/{page_slug}/export_pdf")
async def calculators_plumbing_export_pdf(request: Request, page_slug: str):
    schema = PLUMBING_SCHEMAS.get(page_slug)
    handler = PLUMBING_HANDLERS.get(page_slug)
    if schema is None or handler is None:
        raise HTTPException(status_code=404, detail="PDF export not supported for this calculator.")

    form_data = await request.form()
    values = dict(form_data)
    project_name = values.pop("project_name", None)

    try:
        validated = schema.parse_obj(values)
        result_obj = handler(validated)
        result = result_obj.dict() if hasattr(result_obj, "dict") else result_obj
    except ValidationError as ex:
        logger.warning("Validation error during PDF export for %s: %s", page_slug, ex)
        try:
            from app.utils.validation import map_pydantic_errors
            field_errors = map_pydantic_errors(page, ex.errors())
        except Exception:
            field_errors = { (err.get('loc')[-1] if err.get('loc') else 'field'): err.get('msg') for err in ex.errors() }
        raise HTTPException(status_code=400, detail={"errors": field_errors})
    except Exception as ex:
        logger.exception("Error during PDF export for %s: %s", page_slug, ex)
        raise HTTPException(status_code=400, detail="Calculation could not be completed. Please try again later.")

    page = PLUMBING_PAGES.get(page_slug)
    stream = build_calculator_pdf(
        page["title"] if page else page_slug,
        values,
        result,
        page=page,
        project_name=project_name,
    )
    stream.seek(0)

    response = StreamingResponse(
        stream,
        media_type="application/pdf",
    )
    response.headers["Content-Disposition"] = f"attachment; filename={page_slug}.pdf"
    return response


@router.get("/calculators/electrical")
async def electrical_suite(request: Request):
    return templates.TemplateResponse(request=request, name="calculators/electrical.html", context={"request": request})


@router.get("/calculators/fire-fighting")
async def fire_fighting_suite(request: Request):
    return templates.TemplateResponse(request=request, name="calculators/fire_fighting.html", context={"request": request})


# ==========================================================
# HVAC Duct Sizing
# ==========================================================

@router.get("/calculators/duct-sizing")
async def duct_sizing(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="calculators/duct_sizing.html",
        context={
            "request": request,
            "result": None,
            "error": None,
        },
    )


@router.post("/calculators/duct-sizing")
async def duct_sizing_calculate(
    request: Request,
    duct_type: str = Form(...),
    airflow: float = Form(...),
    velocity: float = Form(...),
):

    page_slug = 'duct-sizing'
    page = HVAC_CALCULATORS.get(page_slug)
    values = {"duct_type": duct_type, "airflow": airflow, "velocity": velocity}

    # Wrap the HVAC runner so run_calculation can call it with **inputs
    def _handler(**inputs):
        return _run_hvac_calculation(page_slug, inputs)

    from app.utils.calc_runner import run_calculation
    calc_resp = run_calculation(page.get('title', page_slug), page, _handler, values)

    if not calc_resp['success']:
        logger.error('Calculation failed for %s: %s', page_slug, calc_resp['error'])
        error = "Calculation could not be completed. Please verify your inputs and try again."
        return templates.TemplateResponse(
            request=request,
            name="calculators/calculator_page.html",
            context={
                "request": request,
                "page": page,
                "values": values,
                "result": None,
                "error": error,
                "field_errors": {"__internal": "Calculation failed. Check server logs for details."},
            },
        )

    result = calc_resp['result']
    return templates.TemplateResponse(
        request=request,
        name="calculators/calculator_page.html",
        context={
            "request": request,
            "page": page,
            "values": values,
            "result": result,
            "error": None,
        },
    )
# ==========================================================
# HVAC Heat Load
# ==========================================================
@router.get("/calculators/heat-load")
async def heat_load(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="calculators/heat_load.html",
        context={
            "request": request,
            "result": None,
            "error": None,
        },
    )
@router.post("/calculators/heat-load")
async def heat_load_calculate(
    request: Request,
    length: float = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    occupants: int = Form(...),
    lighting: float = Form(...),
    equipment: float = Form(...),

    outdoor_db: float = Form(...),
    indoor_db: float = Form(...),

    wall_u: float = Form(...),
    roof_u: float = Form(...),

    glass_area: float = Form(0),
    glass_u: float = Form(...),
    glass_shgc: float = Form(...),

    solar: float = Form(...),

    fresh_air_cfm: float = Form(0),
):

    page_slug = 'heat-load'
    page = HVAC_CALCULATORS.get(page_slug)
    values = {
        "length": length,
        "width": width,
        "height": height,
        "occupants": occupants,
        "lighting": lighting,
        "equipment": equipment,
        "outdoor_db": outdoor_db,
        "indoor_db": indoor_db,
        "wall_u": wall_u,
        "roof_u": roof_u,
        "glass_area": glass_area,
        "glass_u": glass_u,
        "glass_shgc": glass_shgc,
        "solar": solar,
        "fresh_air_cfm": fresh_air_cfm,
    }

    def _handler(**inputs):
        return _run_hvac_calculation(page_slug, inputs)

    from app.utils.calc_runner import run_calculation
    calc_resp = run_calculation(page.get('title', page_slug), page, _handler, values)
    if not calc_resp['success']:
        logger.error('Calculation failed for %s: %s', page_slug, calc_resp['error'])
        error = "Calculation could not be completed. Please verify your inputs and try again."
        return templates.TemplateResponse(
            request=request,
            name="calculators/calculator_page.html",
            context={
                "request": request,
                "page": page,
                "values": values,
                "result": None,
                "error": error,
                "field_errors": {"__internal": "Calculation failed. Check server logs for details."},
            },
        )

    result = calc_resp['result']
    return templates.TemplateResponse(
        request=request,
        name="calculators/calculator_page.html",
        context={
            "request": request,
            "page": page,
            "values": values,
            "result": result,
            "error": None,
        },
    )
# ==========================================================
# HVAC Air Flow
# ==========================================================

@router.get("/calculators/airflow")
async def airflow(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="calculators/airflow.html",
        context={
            "request": request,
            "result": None,
            "error": None,
        },
    )


@router.post("/calculators/airflow")
async def airflow_calculate(
    request: Request,
    length: float = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    air_changes: float = Form(...),
):

    page_slug = 'airflow'
    page = HVAC_CALCULATORS.get(page_slug)
    values = {"length": length, "width": width, "height": height, "air_changes": air_changes}

    def _handler(**inputs):
        return _run_hvac_calculation(page_slug, inputs)

    from app.utils.calc_runner import run_calculation
    calc_resp = run_calculation(page.get('title', page_slug), page, _handler, values)
    if not calc_resp['success']:
        logger.error('Calculation failed for %s: %s', page_slug, calc_resp['error'])
        error = "Calculation could not be completed. Please verify your inputs and try again."
        return templates.TemplateResponse(
            request=request,
            name="calculators/airflow.html",
            context={
                "request": request,
                "length": length,
                "width": width,
                "height": height,
                "air_changes": air_changes,
                "result": None,
                "error": error,
                "field_errors": {"__internal": "Calculation failed. Check server logs for details."},
            },
        )

    result = calc_resp['result']
    return templates.TemplateResponse(
        request=request,
        name="calculators/airflow.html",
        context={
            "request": request,
            "length": length,
            "width": width,
            "height": height,
            "air_changes": air_changes,
            "result": result,
            "error": None,
        },
    )
# ==========================================================
# HVAC Fresh Air
# ==========================================================

@router.get("/calculators/fresh-air")
async def fresh_air(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="calculators/fresh_air.html",
        context={
            "request": request,
            "result": None,
            "error": None,
        },
    )


@router.post("/calculators/fresh-air")
async def fresh_air_calculate(
    request: Request,
    occupants: int = Form(...),
    area: float = Form(...),
    fresh_air_per_person: float = Form(...),
    fresh_air_per_area: float = Form(...),
):

    page_slug = 'fresh-air'
    page = HVAC_CALCULATORS.get(page_slug)
    values = {"occupants": occupants, "area": area, "fresh_air_per_person": fresh_air_per_person, "fresh_air_per_area": fresh_air_per_area}

    def _handler(**inputs):
        return _run_hvac_calculation(page_slug, inputs)

    from app.utils.calc_runner import run_calculation
    calc_resp = run_calculation(page.get('title', page_slug), page, _handler, values)
    if not calc_resp['success']:
        logger.error('Calculation failed for %s: %s', page_slug, calc_resp['error'])
        error = "Calculation could not be completed. Please verify your inputs and try again."
        return templates.TemplateResponse(
            request=request,
            name="calculators/fresh_air.html",
            context={
                "request": request,
                "result": None,
                "error": error,
                "field_errors": {"__internal": "Calculation failed. Check server logs for details."},
            },
        )

    result = calc_resp['result']
    return templates.TemplateResponse(
        request=request,
        name="calculators/fresh_air.html",
        context={
            "request": request,
            "result": result,
            "error": None,
        },
    )


# ==========================================================
# HVAC Chilled Water
# ==========================================================

@router.get("/calculators/chilled-water")
async def chilled_water(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="calculators/chilled_water.html",
        context={
            "request": request,
            "result": None,
            "error": None,
        },
    )


@router.post("/calculators/chilled-water")
async def chilled_water_calculate(
    request: Request,
    cooling_load: float = Form(...),
    delta_t: float = Form(...),
    velocity: float = Form(...),
):

    page_slug = 'chilled-water'
    page = HVAC_CALCULATORS.get(page_slug)
    values = {"cooling_load": cooling_load, "delta_t": delta_t, "velocity": velocity}

    def _handler(**inputs):
        return _run_hvac_calculation(page_slug, inputs)

    from app.utils.calc_runner import run_calculation
    calc_resp = run_calculation(page.get('title', page_slug), page, _handler, values)
    if not calc_resp['success']:
        logger.error('Calculation failed for %s: %s', page_slug, calc_resp['error'])
        error = "Calculation could not be completed. Please verify your inputs and try again."
        return templates.TemplateResponse(
            request=request,
            name="calculators/chilled_water.html",
            context={
                "request": request,
                "cooling_load": cooling_load,
                "delta_t": delta_t,
                "velocity": velocity,
                "result": None,
                "error": error,
                "field_errors": {"__internal": "Calculation failed. Check server logs for details."},
            },
        )

    result = calc_resp['result']
    return templates.TemplateResponse(
        request=request,
        name="calculators/chilled_water.html",
        context={
            "request": request,
            "cooling_load": cooling_load,
            "delta_t": delta_t,
            "velocity": velocity,
            "result": result,
            "error": None,
        },
    )
# ==========================================================
# HVAC Pump Head
# ==========================================================

@router.get("/calculators/pump-head")
async def pump_head(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="calculators/pump_head.html",
        context={
            "request": request,
            "result": None,
            "error": None,
        },
    )


@router.post("/calculators/pump-head")
async def pump_head_calculate(
    request: Request,
    flow_rate: float = Form(...),
    static_head: float = Form(...),
    friction_loss: float = Form(...),
    efficiency: float = Form(...),
):

    page_slug = 'pump-head'
    page = HVAC_CALCULATORS.get(page_slug)
    values = {"flow_rate": flow_rate, "static_head": static_head, "friction_loss": friction_loss, "efficiency": efficiency}

    def _handler(**inputs):
        return _run_hvac_calculation(page_slug, inputs)

    from app.utils.calc_runner import run_calculation
    calc_resp = run_calculation(page.get('title', page_slug), page, _handler, values)
    if not calc_resp['success']:
        logger.error('Calculation failed for %s: %s', page_slug, calc_resp['error'])
        error = "Calculation could not be completed. Please verify your inputs and try again."
        return templates.TemplateResponse(
            request=request,
            name="calculators/pump_head.html",
            context={
                "request": request,
                "flow_rate": flow_rate,
                "static_head": static_head,
                "friction_loss": friction_loss,
                "efficiency": efficiency,
                "result": None,
                "error": error,
                "field_errors": {"__internal": "Calculation failed. Check server logs for details."},
            },
        )

    result = calc_resp['result']
    return templates.TemplateResponse(
        request=request,
        name="calculators/pump_head.html",
        context={
            "request": request,
            "flow_rate": flow_rate,
            "static_head": static_head,
            "friction_loss": friction_loss,
            "efficiency": efficiency,
            "result": result,
            "error": None,
        },
    )


# ==========================================================
# HVAC Static Pressure
# ==========================================================

@router.get("/calculators/static-pressure")
async def static_pressure(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="calculators/static_pressure.html",
        context={
            "request": request,
            "result": None,
            "error": None,
        },
    )


@router.post("/calculators/static-pressure")
async def static_pressure_calculate(
    request: Request,
    airflow: float = Form(...),
    velocity: float = Form(...),
    duct_length: float = Form(...),
    friction_rate: float = Form(...),
):

    page_slug = 'static-pressure'
    page = HVAC_CALCULATORS.get(page_slug)
    values = {"airflow": airflow, "velocity": velocity, "duct_length": duct_length, "friction_rate": friction_rate}

    def _handler(**inputs):
        return _run_hvac_calculation(page_slug, inputs)

    from app.utils.calc_runner import run_calculation
    calc_resp = run_calculation(page.get('title', page_slug), page, _handler, values)
    if not calc_resp['success']:
        logger.error('Calculation failed for %s: %s', page_slug, calc_resp['error'])
        error = "Calculation could not be completed. Please verify your inputs and try again."
        return templates.TemplateResponse(
            request=request,
            name="calculators/calculator_page.html",
            context={
                "request": request,
                "page": page,
                "values": values,
                "result": None,
                "error": error,
                "field_errors": {"__internal": "Calculation failed. Check server logs for details."},
            },
        )

    result = calc_resp['result']
    return templates.TemplateResponse(
        request=request,
        name="calculators/calculator_page.html",
        context={
            "request": request,
            "page": page,
            "values": values,
            "result": result,
            "error": None,
        },
    )