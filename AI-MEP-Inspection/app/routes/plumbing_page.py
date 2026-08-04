"""
Plumbing UI Routes
AI MEP Calculator
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.calculators.plumbing_models import (
    FixtureUnitRequest,
    PipeSizeRequest,
    PumpRequest,
    RainwaterRequest,
    SumpRequest,
    TankRequest,
    WaterDemandRequest,
    DrainageRequest,
)
from app.services.plumbing_service import PlumbingService

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

PLUMBING_SCHEMAS = {
    "water-demand-page": WaterDemandRequest,
    "fixture-units-page": FixtureUnitRequest,
    "pipe-size-page": PipeSizeRequest,
    "drainage-page": DrainageRequest,
    "rainwater-page": RainwaterRequest,
    "tank-page": TankRequest,
    "sump-page": SumpRequest,
    "pump-page": PumpRequest,
}

PLUMBING_HANDLERS = {
    "water-demand-page": PlumbingService.calculate_water_demand,
    "fixture-units-page": PlumbingService.calculate_fixture_units,
    "pipe-size-page": PlumbingService.calculate_pipe_size,
    "drainage-page": PlumbingService.calculate_drainage,
    "rainwater-page": PlumbingService.calculate_rainwater,
    "tank-page": PlumbingService.calculate_water_tank,
    "sump-page": PlumbingService.calculate_sump,
    "pump-page": PlumbingService.calculate_pump,
}

PLUMBING_PAGES = {
    "water-demand-page": {
        "title": "Water Demand Calculator",
        "description": "Estimate daily and peak water demand.",
        "api_path": "/plumbing/water-demand",
        "fields": [
            {
                "name": "building_type",
                "label": "Building Type",
                "type": "select",
                "options": [
                    "Residential",
                    "Apartment",
                    "Villa",
                    "Hotel",
                    "Hospital",
                    "Office",
                    "School",
                    "Restaurant",
                    "Mall",
                    "Industrial",
                ],
                "required": True,
            },
            {"name": "occupancy", "label": "Occupancy", "type": "number", "min": "1", "step": "1", "required": True, "default": "100"},
            {"name": "fixture_units", "label": "Fixture Units", "type": "number", "min": "0", "step": "0.01", "required": True, "default": "50"},
        ],
        "result_rows": [
            {"key": "building_type", "label": "Building Type"},
            {"key": "occupancy", "label": "Occupancy"},
            {"key": "liter_person_day", "label": "Liters per Person / Day"},
            {"key": "demand_lpd", "label": "Daily Demand (LPD)"},
            {"key": "demand_lpm", "label": "Demand (LPM)"},
            {"key": "peak_factor", "label": "Peak Factor"},
            {"key": "peak_demand_lpm", "label": "Peak Demand (LPM)"},
        ],
        "formula": "Demand = max(occupancy × 0.12, fixture units × 1.1) × building type factor",
        "reference": "Adapted from domestic water demand design practices.",
    },
    "fixture-units-page": {
        "title": "Fixture Unit Calculator",
        "description": "Calculate total fixture loading.",
        "api_path": "/plumbing/fixture-units",
        "fields": [
            {"name": "fixture_type", "label": "Fixture Type", "type": "select", "options": ["Water Closet", "Wash Basin", "Kitchen Sink", "Urinal", "Shower", "Bathtub", "Drinking Fountain", "Service Sink"], "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "min": "1", "step": "1", "required": True, "default": "1"},
        ],
        "result_rows": [
            {"key": "fixture_type", "label": "Fixture Type"},
            {"key": "quantity", "label": "Quantity"},
            {"key": "fixture_unit_per_item", "label": "Fixture Unit Per Item"},
            {"key": "total_fixture_units", "label": "Total Fixture Units"},
        ],
        "formula": "Total fixture units = fixture unit factor × quantity.",
        "reference": "Fixture unit load calculation for plumbing design.",
    },
    "pipe-size-page": {
        "title": "Pipe Size Calculator",
        "description": "Pipe diameter calculation from flow and velocity.",
        "api_path": "/plumbing/pipe-size",
        "fields": [
            {"name": "flow_rate_lpm", "label": "Flow Rate (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "100"},
            {"name": "velocity_mps", "label": "Velocity (m/s)", "type": "number", "min": "0.1", "step": "0.01", "required": True, "default": "1"},
            {"name": "material", "label": "Pipe Material", "type": "select", "options": ["PVC", "HDPE", "Copper", "GI", "PPR"], "required": True, "default": "PVC"},
        ],
        "result_rows": [
            {"key": "material", "label": "Pipe Material"},
            {"key": "flow_rate_lpm", "label": "Flow Rate (LPM)"},
            {"key": "velocity_mps", "label": "Velocity (m/s)"},
            {"key": "diameter_mm", "label": "Diameter (mm)"},
            {"key": "recommended_nominal_size", "label": "Recommended Nominal Size"},
        ],
        "formula": "d = sqrt(4Q / (π v)) where Q is flow in m³/s.",
        "reference": "Hydraulic continuity equation for pipe sizing.",
    },
    "drainage-page": {
        "title": "Drainage Calculator",
        "description": "Drainage pipe sizing based on fixture units and slope.",
        "api_path": "/plumbing/drainage",
        "fields": [
            {"name": "fixture_units", "label": "Fixture Units", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "20"},
            {"name": "slope_percent", "label": "Slope (%)", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "1"},
        ],
        "result_rows": [
            {"key": "fixture_units", "label": "Fixture Units"},
            {"key": "slope_percent", "label": "Slope (%)"},
            {"key": "recommended_pipe_mm", "label": "Recommended Pipe (mm)"},
            {"key": "estimated_flow_lps", "label": "Estimated Flow (LPS)"},
        ],
        "formula": "Use fixture unit load and slope to select drainage diameter.",
        "reference": "Drainage pipe sizing guidelines for plumbing systems.",
    },
    "rainwater-page": {
        "title": "Rainwater Calculator",
        "description": "Roof rainwater calculations.",
        "api_path": "/plumbing/rainwater",
        "fields": [
            {"name": "roof_area_m2", "label": "Roof Area (m²)", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "100"},
            {"name": "rainfall_mm_hr", "label": "Rainfall (mm/h)", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "25"},
            {"name": "runoff_coefficient", "label": "Runoff Coefficient", "type": "number", "min": "0.1", "max": "1", "step": "0.01", "required": True, "default": "0.9"},
        ],
        "result_rows": [
            {"key": "roof_area_m2", "label": "Roof Area (m²)"},
            {"key": "rainfall_mm_hr", "label": "Rainfall (mm/h)"},
            {"key": "runoff_coefficient", "label": "Runoff Coefficient"},
            {"key": "flow_lps", "label": "Flow (LPS)"},
        ],
        "formula": "Flow = roof area × rainfall × runoff coefficient / 3600.",
        "reference": "Rainwater drainage sizing using runoff and intensity.",
    },
    "tank-page": {
        "title": "Water Tank Calculator",
        "description": "Tank capacity calculator.",
        "api_path": "/plumbing/tank",
        "fields": [
            {"name": "occupancy", "label": "Occupancy", "type": "number", "min": "1", "step": "1", "required": True, "default": "50"},
            {"name": "storage_days", "label": "Storage Days", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "1"},
            {"name": "liters_per_person", "label": "Liters Per Person", "type": "number", "min": "1", "step": "1", "required": True, "default": "135"},
        ],
        "result_rows": [
            {"key": "occupancy", "label": "Occupancy"},
            {"key": "storage_days", "label": "Storage Days"},
            {"key": "liters_per_person", "label": "Liters Per Person"},
            {"key": "required_capacity_liters", "label": "Required Capacity (L)"},
            {"key": "required_capacity_m3", "label": "Required Capacity (m³)"},
        ],
        "formula": "Capacity = occupancy × liters per person × storage days.",
        "reference": "Potable water storage sizing based on daily demand.",
    },
    "sump-page": {
        "title": "Underground Sump Calculator",
        "description": "Sump capacity calculator.",
        "api_path": "/plumbing/sump",
        "fields": [
            {"name": "daily_demand_liters", "label": "Daily Demand (L)", "type": "number", "min": "1", "step": "1", "required": True, "default": "1000"},
            {"name": "storage_days", "label": "Storage Days", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "2"},
        ],
        "result_rows": [
            {"key": "daily_demand_liters", "label": "Daily Demand (L)"},
            {"key": "storage_days", "label": "Storage Days"},
            {"key": "sump_capacity_liters", "label": "Sump Capacity (L)"},
            {"key": "sump_capacity_m3", "label": "Sump Capacity (m³)"},
        ],
        "formula": "Sump capacity = daily demand × storage days.",
        "reference": "Sump storage sizing for pump cycling and overflow safety.",
    },
    "pump-page": {
        "title": "Pump Head & Power Calculator",
        "description": "Pump selection calculator.",
        "api_path": "/plumbing/pump",
        "fields": [
            {"name": "flow_lps", "label": "Flow (LPS)", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "10"},
            {"name": "total_head_m", "label": "Total Head (m)", "type": "number", "min": "0.1", "step": "0.1", "required": True, "default": "20"},
            {"name": "efficiency", "label": "Efficiency (%)", "type": "number", "min": "1", "max": "100", "step": "0.1", "required": True, "default": "70"},
        ],
        "result_rows": [
            {"key": "flow_lps", "label": "Flow (LPS)"},
            {"key": "total_head_m", "label": "Total Head (m)"},
            {"key": "efficiency", "label": "Efficiency (%)"},
            {"key": "hydraulic_power_kw", "label": "Hydraulic Power (kW)"},
            {"key": "motor_power_kw", "label": "Motor Power (kW)"},
            {"key": "motor_power_hp", "label": "Motor Power (HP)"},
        ],
        "formula": "Power = 9.81 × Q × H / η, with Q in m³/s.",
        "reference": "Pump hydraulic power formula for centrifugal pump selection.",
    },
}


@router.get("/plumbing")
async def plumbing_dashboard(request: Request):
    return templates.TemplateResponse(request, "plumbing.html", {"request": request})


@router.get("/plumbing/{page_slug}")
async def plumbing_calculator_page(request: Request, page_slug: str):
    page = PLUMBING_PAGES.get(page_slug)
    if not page:
        raise HTTPException(status_code=404, detail="Calculator page not found.")
    return templates.TemplateResponse(
        request,
        "plumbing_calculator_page.html",
        {
            "request": request,
            "page": page,
            "values": {field["name"]: field.get("default", "") for field in page["fields"]},
            "result": None,
            "error": None,
        },
    )


@router.post("/plumbing/{page_slug}")
async def plumbing_calculator_page_submit(request: Request, page_slug: str):
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
        error = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in ex.errors()])
    except Exception as ex:
        error = str(ex)

    return templates.TemplateResponse(
        request,
        "plumbing_calculator_page.html",
        {
            "request": request,
            "page": page,
            "values": values,
            "result": result,
            "error": error,
        },
    )
