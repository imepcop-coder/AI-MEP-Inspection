"""
FastAPI Routes
AI MEP Calculator - Plumbing Module
"""

from fastapi import APIRouter, HTTPException

from app.calculators.plumbing_models import (
    HealthResponse,
    WaterDemandRequest,
    WaterDemandResponse,
    FixtureUnitRequest,
    FixtureUnitResponse,
    PipeSizeRequest,
    PipeSizeResponse,
    DrainageRequest,
    DrainageResponse,
    RainwaterRequest,
    RainwaterResponse,
    TankRequest,
    TankResponse,
    SumpRequest,
    SumpResponse,
    PumpRequest,
    PumpResponse,
)

from app.services.plumbing_service import PlumbingService


router = APIRouter(
    prefix="/plumbing",
    tags=["Plumbing Calculators"],
)


# ==========================================================
# Health Check
# ==========================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
)
async def health():
    return HealthResponse()


# ==========================================================
# Water Demand Calculator
# ==========================================================

@router.post(
    "/water-demand",
    response_model=WaterDemandResponse,
)
async def calculate_water_demand(
    request: WaterDemandRequest,
):
    try:
        return PlumbingService.calculate_water_demand(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# Fixture Unit Calculator
# ==========================================================

@router.post(
    "/fixture-units",
    response_model=FixtureUnitResponse,
)
async def calculate_fixture_units(
    request: FixtureUnitRequest,
):
    try:
        return PlumbingService.calculate_fixture_units(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# Pipe Size Calculator
# ==========================================================

@router.post(
    "/pipe-size",
    response_model=PipeSizeResponse,
)
async def calculate_pipe_size(
    request: PipeSizeRequest,
):
    try:
        return PlumbingService.calculate_pipe_size(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# Drainage Calculator
# ==========================================================

@router.post(
    "/drainage",
    response_model=DrainageResponse,
)
async def calculate_drainage(
    request: DrainageRequest,
):
    try:
        return PlumbingService.calculate_drainage(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# Rainwater Calculator
# ==========================================================

@router.post(
    "/rainwater",
    response_model=RainwaterResponse,
)
async def calculate_rainwater(
    request: RainwaterRequest,
):
    try:
        return PlumbingService.calculate_rainwater(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# Water Tank Calculator
# ==========================================================

@router.post(
    "/tank",
    response_model=TankResponse,
)
async def calculate_tank(
    request: TankRequest,
):
    try:
        return PlumbingService.calculate_water_tank(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# Underground Sump Calculator
# ==========================================================

@router.post(
    "/sump",
    response_model=SumpResponse,
)
async def calculate_sump(
    request: SumpRequest,
):
    try:
        return PlumbingService.calculate_sump(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# Pump Head & Power Calculator
# ==========================================================

@router.post(
    "/pump",
    response_model=PumpResponse,
)
async def calculate_pump(
    request: PumpRequest,
):
    try:
        return PlumbingService.calculate_pump(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
