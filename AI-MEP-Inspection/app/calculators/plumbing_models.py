"""
Pydantic models for Plumbing Calculators

Author: AI MEP Calculator
"""

from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================
# Common Base Models
# ============================================================

class CalculatorResponse(BaseModel):
    success: bool = True
    message: str = "Calculation completed successfully."


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


# ============================================================
# Water Demand Calculator
# ============================================================

BuildingType = Literal[
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
]


class WaterDemandRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    building_type: BuildingType
    occupancy: int = Field(..., gt=0, le=100000)
    fixture_units: float = Field(..., ge=0)

    @field_validator("occupancy")
    @classmethod
    def validate_occupancy(cls, value: int):
        if value <= 0:
            raise ValueError("Occupancy must be greater than zero.")
        return value


class WaterDemandResponse(CalculatorResponse):
    building_type: str
    occupancy: int
    fixture_units: float

    liters_per_person: float
    demand_lpd: float
    demand_lpm: float
    peak_factor: float
    peak_demand_lpm: float


# ============================================================
# Fixture Unit Calculator
# ============================================================

FixtureType = Literal[
    "Water Closet",
    "Wash Basin",
    "Kitchen Sink",
    "Urinal",
    "Shower",
    "Bathtub",
    "Drinking Fountain",
    "Service Sink",
]


class FixtureUnitRequest(BaseModel):
    fixture_type: FixtureType
    quantity: int = Field(..., gt=0)


class FixtureUnitResponse(CalculatorResponse):
    fixture_type: str
    quantity: int
    fixture_unit_per_item: float
    total_fixture_units: float


# ============================================================
# Pipe Size Calculator
# ============================================================

PipeMaterial = Literal[
    "PVC",
    "HDPE",
    "Copper",
    "GI",
    "PPR",
]


class PipeSizeRequest(BaseModel):
    flow_rate_lpm: float = Field(..., gt=0)
    velocity_mps: float = Field(..., gt=0)
    material: PipeMaterial


class PipeSizeResponse(CalculatorResponse):
    flow_rate_lpm: float
    velocity_mps: float
    diameter_mm: float
    recommended_nominal_size: str


# ============================================================
# Drainage Calculator
# ============================================================

class DrainageRequest(BaseModel):
    fixture_units: float = Field(..., gt=0)
    slope_percent: float = Field(..., gt=0)


class DrainageResponse(CalculatorResponse):
    fixture_units: float
    slope_percent: float
    recommended_pipe_mm: float
    estimated_flow_lps: float


# ============================================================
# Rainwater Calculator
# ============================================================

class RainwaterRequest(BaseModel):
    roof_area_m2: float = Field(..., gt=0)
    rainfall_mm_hr: float = Field(..., gt=0)
    runoff_coefficient: float = Field(
        default=0.9,
        ge=0,
        le=1,
    )


class RainwaterResponse(CalculatorResponse):
    roof_area_m2: float
    rainfall_mm_hr: float
    runoff_coefficient: float
    flow_lps: float


# ============================================================
# Water Tank Calculator
# ============================================================

class TankRequest(BaseModel):
    occupancy: int = Field(..., gt=0)
    storage_days: float = Field(default=1.0, gt=0)
    liters_per_person: float = Field(default=135.0, gt=0)


class TankResponse(CalculatorResponse):
    occupancy: int
    storage_days: float
    liters_per_person: float
    required_capacity_liters: float
    required_capacity_m3: float


# ============================================================
# Underground Sump Calculator
# ============================================================

class SumpRequest(BaseModel):
    daily_demand_liters: float = Field(..., gt=0)
    storage_days: float = Field(default=2.0, gt=0)


class SumpResponse(CalculatorResponse):
    daily_demand_liters: float
    storage_days: float
    sump_capacity_liters: float
    sump_capacity_m3: float


# ============================================================
# Pump Calculator
# ============================================================

class PumpRequest(BaseModel):
    flow_lps: float = Field(..., gt=0)
    total_head_m: float = Field(..., gt=0)
    efficiency: float = Field(
        default=70,
        gt=0,
        le=100,
    )


class PumpResponse(CalculatorResponse):
    flow_lps: float
    total_head_m: float
    efficiency: float

    hydraulic_power_kw: float
    motor_power_kw: float
    motor_power_hp: float


# ============================================================
# Pipe Velocity Calculator
# ============================================================


class PipeVelocityRequest(BaseModel):
    flow_rate_lpm: float = Field(..., gt=0)
    diameter_mm: float = Field(..., gt=0)


class PipeVelocityResponse(CalculatorResponse):
    flow_rate_lpm: float
    diameter_mm: float
    velocity_m_s: float


# ============================================================
# Pipe Friction Calculator
# ============================================================


class PipeFrictionRequest(BaseModel):
    flow_rate_lpm: float = Field(..., gt=0)
    diameter_mm: float = Field(..., gt=0)
    length_m: float = Field(..., gt=0)
    hazen_williams_c: float = Field(default=120.0, gt=0)


class PipeFrictionResponse(CalculatorResponse):
    flow_rate_lpm: float
    diameter_mm: float
    length_m: float
    hazen_williams_c: float
    head_loss_m: float
    pressure_loss_kpa: float


# ============================================================
# Booster Pump Calculator
# ============================================================


class BoosterPumpRequest(BaseModel):
    flow_lps: float = Field(..., gt=0)
    required_pressure_kpa: float = Field(..., gt=0)
    inlet_pressure_kpa: float = Field(default=200.0, gt=0)
    efficiency: float = Field(default=70.0, gt=0, le=100)


class BoosterPumpResponse(CalculatorResponse):
    flow_lps: float
    required_pressure_kpa: float
    inlet_pressure_kpa: float
    pressure_gain_kpa: float
    total_head_m: float
    efficiency: float
    hydraulic_power_kw: float
    motor_power_kw: float


# ============================================================
# Transfer Pump Calculator
# ============================================================


class TransferPumpRequest(BaseModel):
    flow_lps: float = Field(..., gt=0)
    lift_m: float = Field(..., gt=0)
    friction_loss_m: float = Field(default=2.0, gt=0)
    efficiency: float = Field(default=70.0, gt=0, le=100)


class TransferPumpResponse(CalculatorResponse):
    flow_lps: float
    lift_m: float
    friction_loss_m: float
    total_head_m: float
    efficiency: float
    hydraulic_power_kw: float
    motor_power_kw: float


# ============================================================
# Domestic Pump Calculator
# ============================================================


class DomesticPumpRequest(BaseModel):
    flow_lps: float = Field(..., gt=0)
    required_residual_pressure_kpa: float = Field(..., gt=0)
    elevation_m: float = Field(default=10.0, gt=0)
    efficiency: float = Field(default=70.0, gt=0, le=100)


class DomesticPumpResponse(CalculatorResponse):
    flow_lps: float
    required_residual_pressure_kpa: float
    elevation_m: float
    total_head_m: float
    efficiency: float
    hydraulic_power_kw: float
    motor_power_kw: float


# ============================================================
# Hydrotest Calculator
# ============================================================


class HydrotestRequest(BaseModel):
    operating_pressure_kpa: float = Field(..., gt=0)
    test_factor: float = Field(default=1.5, gt=0)


class HydrotestResponse(CalculatorResponse):
    operating_pressure_kpa: float
    test_factor: float
    test_pressure_kpa: float
    test_head_m: float


# ============================================================
# Expansion Tank Calculator
# ============================================================


class ExpansionTankRequest(BaseModel):
    system_volume_l: float = Field(..., gt=0)
    temp_rise_c: float = Field(..., gt=0)
    expansion_coefficient: float = Field(default=0.000214, gt=0)
    safety_factor: float = Field(default=1.2, gt=0)
    precharge_pressure_kpa: float = Field(default=200.0, gt=0)


class ExpansionTankResponse(CalculatorResponse):
    system_volume_l: float
    temp_rise_c: float
    expansion_coefficient: float
    safety_factor: float
    precharge_pressure_kpa: float
    expansion_volume_l: float
    required_tank_volume_l: float


# ============================================================
# Generic API Response
# ============================================================

class HealthResponse(BaseModel):
    status: str = "ok"
    module: str = "Plumbing Calculator"
    version: str = "1.0.0"
