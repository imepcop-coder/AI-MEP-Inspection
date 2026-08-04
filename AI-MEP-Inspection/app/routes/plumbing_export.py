from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.services.plumbing_service import PlumbingService
from app.calculators.plumbing_models import (
    DrainageRequest,
    FixtureUnitRequest,
    PipeSizeRequest,
    PumpRequest,
    RainwaterRequest,
    SumpRequest,
    TankRequest,
    WaterDemandRequest,
)
from app.routes.plumbing_page import PLUMBING_PAGES
from app.utils.xlsx_export import build_calculator_pdf, build_calculator_workbook

router = APIRouter()

SCHEMA_MAP = {
    "water-demand-page": WaterDemandRequest,
    "fixture-units-page": FixtureUnitRequest,
    "pipe-size-page": PipeSizeRequest,
    "drainage-page": DrainageRequest,
    "rainwater-page": RainwaterRequest,
    "tank-page": TankRequest,
    "sump-page": SumpRequest,
    "pump-page": PumpRequest,
}

HANDLER_MAP = {
    "water-demand-page": PlumbingService.calculate_water_demand,
    "fixture-units-page": PlumbingService.calculate_fixture_units,
    "pipe-size-page": PlumbingService.calculate_pipe_size,
    "drainage-page": PlumbingService.calculate_drainage,
    "rainwater-page": PlumbingService.calculate_rainwater,
    "tank-page": PlumbingService.calculate_water_tank,
    "sump-page": PlumbingService.calculate_sump,
    "pump-page": PlumbingService.calculate_pump,
}


@router.post("/plumbing/{page_slug}/export_excel")
async def export_plumbing_excel(request: Request, page_slug: str):
    schema = SCHEMA_MAP.get(page_slug)
    handler = HANDLER_MAP.get(page_slug)
    if schema is None or handler is None:
        raise HTTPException(status_code=404, detail="Excel export not supported for this calculator.")

    form_data = await request.form()
    values = dict(form_data)
    project_name = values.pop("project_name", None)

    try:
        validated = schema.parse_obj(values)
        result_obj = handler(validated)
        result = result_obj.dict() if hasattr(result_obj, "dict") else result_obj
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

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


@router.post("/plumbing/{page_slug}/export_pdf")
async def export_plumbing_pdf(request: Request, page_slug: str):
    schema = SCHEMA_MAP.get(page_slug)
    handler = HANDLER_MAP.get(page_slug)
    if schema is None or handler is None:
        raise HTTPException(status_code=404, detail="PDF export not supported for this calculator.")

    form_data = await request.form()
    values = dict(form_data)
    project_name = values.pop("project_name", None)

    try:
        validated = schema.parse_obj(values)
        result_obj = handler(validated)
        result = result_obj.dict() if hasattr(result_obj, "dict") else result_obj
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

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
