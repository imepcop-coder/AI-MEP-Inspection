"""
Pydantic models for Plumbing Calculators

Author: AI MEP Calculator
"""

from typing import Literal, Optional

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


DrainagePipeRequest = DrainageRequest


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


RainwaterPipeRequest = RainwaterRequest


class RainwaterResponse(CalculatorResponse):
    roof_area_m2: float
    rainfall_mm_hr: float
    runoff_coefficient: float
    flow_lps: float


# ============================================================
# Water Tank Calculator
# ============================================================

class WaterTankRequest(BaseModel):
    occupancy: int = Field(..., gt=0)
    storage_days: float = Field(default=1.0, gt=0)
    liters_per_person: float = Field(default=135.0, gt=0)


class WaterTankResponse(CalculatorResponse):
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


SumpTankRequest = SumpRequest


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


PumpSelectionRequest = PumpRequest


class PumpResponse(CalculatorResponse):
    flow_lps: float
    total_head_m: float
    efficiency: float

    hydraulic_power_kw: float
    motor_power_kw: float
    motor_power_hp: float


# ============================================================
# Generic API Response
# ============================================================

class HealthResponse(BaseModel):
    status: str = "ok"
    module: str = "Plumbing Calculator"
    version: str = "1.0.0"


# ============================================================
# Electrical Calculators
# ============================================================

class CableSizeRequest(BaseModel):
    current: float = Field(..., gt=0)
    ambient_temperature: float = Field(..., gt=0)


class VoltageDropRequest(BaseModel):
    voltage: float = Field(..., gt=0)
    current: float = Field(..., gt=0)
    length: float = Field(..., gt=0)
    conductor_area: float = Field(..., gt=0)
    power_factor: float = Field(..., gt=0, le=1)
    phase_type: Literal["Single-phase", "Three-phase"]


class CurrentCalculatorRequest(BaseModel):
    power: float = Field(..., gt=0)
    voltage: float = Field(..., gt=0)
    power_factor: float = Field(..., gt=0, le=1)
    phase_type: Literal["Single-phase", "Three-phase"]


class TransformerSizingRequest(BaseModel):
    load: float = Field(..., gt=0)
    power_factor: float = Field(..., gt=0, le=1)


class GeneratorSizingRequest(BaseModel):
    load: float = Field(..., gt=0)
    power_factor: float = Field(..., gt=0, le=1)
    starting_load_factor: float = Field(..., gt=0)


class UPSSizingRequest(BaseModel):
    load: float = Field(..., gt=0)
    autonomy_minutes: float = Field(..., gt=0)
    efficiency: float = Field(..., gt=0, le=100)


class LightingLuxRequest(BaseModel):
    area: float = Field(..., gt=0)
    target_lux: float = Field(..., gt=0)
    lumens_per_watt: float = Field(..., gt=0)


class CircuitBreakerRequest(BaseModel):
    current: float = Field(..., gt=0)
    breaker_type: Literal["Thermal Magnetic", "Electronic", "Molded Case"]


class BatterySizingRequest(BaseModel):
    load: float = Field(..., gt=0)
    autonomy_hours: float = Field(..., gt=0)
    battery_voltage: float = Field(default=48.0, gt=0)
    efficiency: float = Field(default=90.0, gt=0, le=100)


class EarthingRequest(BaseModel):
    soil_resistivity: float = Field(..., gt=0)
    electrode_length: float = Field(..., gt=0)
    electrode_diameter: float = Field(..., gt=0)
    electrode_count: int = Field(default=1, gt=0)


class PowerFactorRequest(BaseModel):
    real_power: float = Field(..., gt=0)
    apparent_power: float = Field(..., gt=0)
    target_power_factor: float | None = Field(default=None, gt=0, le=1)


# ============================================================
# Fire Calculators
# ============================================================

class FirePumpHeadRequest(BaseModel):
    flow: float = Field(..., gt=0)
    system_pressure: float = Field(..., gt=0)
    elevation: float = Field(...)


class FireFlowRequest(BaseModel):
    area: float = Field(..., gt=0)
    hazard_class: Literal["Light", "Ordinary", "Extra", "High"]


class FireWaterTankRequest(BaseModel):
    demand: float = Field(..., gt=0)
    duration: float = Field(..., gt=0)


class JockeyPumpRequest(BaseModel):
    pump_flow_lpm: float = Field(..., gt=0)
    system_pressure_kpa: float = Field(..., gt=0)
    pressure_margin_kpa: float = Field(default=10.0, gt=0)
    efficiency_percent: float = Field(default=70.0, gt=0, le=100)


class FirePipeSizingRequest(BaseModel):
    flow_rate_lpm: float = Field(..., gt=0)
    velocity_m_s: float = Field(..., gt=0)


class SprinklerSpacingRequest(BaseModel):
    area: float = Field(..., gt=0)
    efficiency: float = Field(..., gt=0, le=100)


class StandpipeRequest(BaseModel):
    height: float = Field(..., gt=0)
    hose_length: float = Field(..., gt=0)
    friction_loss: float = Field(..., gt=0)


class HoseReelRequest(BaseModel):
    flow: float = Field(..., gt=0)
    hose_length: float = Field(..., gt=0)
    nozzle_pressure: float = Field(..., gt=0)


class NozzlePressureRequest(BaseModel):
    flow: float = Field(..., gt=0)
    nozzle_coefficient: float = Field(..., gt=0)


class CoolingLoadRequest(BaseModel):
    length: float = Field(..., gt=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    outdoor_temp: float = Field(...)
    indoor_temp: float = Field(...)
    wall_area: float = Field(..., gt=0)
    wall_u_value: float = Field(..., gt=0)
    roof_area: float = Field(..., gt=0)
    roof_u_value: float = Field(..., gt=0)
    glass_area: float = Field(..., gt=0)
    glass_u_value: float = Field(..., gt=0)
    glass_shgc: float = Field(..., ge=0, le=1)
    occupants: int = Field(..., ge=0)
    lighting_load: float = Field(..., ge=0)
    equipment_load: float = Field(..., ge=0)
    fresh_air_cfm: float = Field(..., ge=0)


class ChillerCapacityRequest(BaseModel):
    load_kw: float = Field(..., gt=0)
    safety_factor: float = Field(default=15.0, gt=0)
    cop: float = Field(..., gt=0)


class ChillerEfficiencyRequest(BaseModel):
    cooling_capacity_kw: float = Field(..., gt=0)
    input_power_kw: float = Field(..., gt=0)
    eer_25: float = Field(..., gt=0)
    eer_50: float = Field(..., gt=0)
    eer_75: float = Field(..., gt=0)
    eer_100: float = Field(..., gt=0)


class PressureDropRequest(BaseModel):
    method: Literal["Darcy-Weisbach", "Hazen-Williams"]
    flow_lpm: float = Field(..., gt=0)
    diameter_mm: float = Field(..., gt=0)
    length_m: float = Field(..., gt=0)
    roughness_mm: float = Field(default=0.15, gt=0)
    hazen_williams_c: float = Field(default=130.0, gt=0)


class ExpansionTankRequest(BaseModel):
    system_volume_m3: float = Field(..., gt=0)
    temperature_rise_c: float = Field(..., gt=0)
    precharge_pressure_bar: float = Field(..., gt=0)
    system_pressure_bar: float = Field(..., gt=0)


class HydrotestRequest(BaseModel):
    system_volume_l: float = Field(..., gt=0)
    leak_allowance_percent: float = Field(default=10.0, ge=0)


class GeneratorRoomVentilationRequest(BaseModel):
    heat_rejection_kw: float = Field(..., gt=0)
    temp_rise_c: float = Field(..., gt=0)


class BatteryRoomVentilationRequest(BaseModel):
    number_batteries: int = Field(..., gt=0)
    heat_per_battery_kw: float = Field(..., gt=0)
    temp_rise_c: float = Field(..., gt=0)


class HeaterCapacityRequest(BaseModel):
    area_m2: float = Field(..., gt=0)
    u_value_w_m2k: float = Field(..., gt=0)
    temp_difference_c: float = Field(..., gt=0)
    efficiency_percent: float = Field(default=90.0, gt=0, le=100)


class HydraulicCalculationRequest(BaseModel):
    flow: float = Field(..., gt=0)
    diameter: float = Field(..., gt=0)
    length: float = Field(..., gt=0)
    roughness: float = Field(..., gt=0)


class CalculationResponse(BaseModel):
    result: dict
    error: Optional[str] = None
