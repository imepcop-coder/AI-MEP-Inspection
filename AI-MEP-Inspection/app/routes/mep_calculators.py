from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from app.schemas.calculators import (
    BatteryRoomVentilationRequest,
    CableSizeRequest,
    CircuitBreakerRequest,
    ChillerCapacityRequest,
    ChillerEfficiencyRequest,
    CoolingLoadRequest,
    CurrentCalculatorRequest,
    DrainagePipeRequest,
    ExpansionTankRequest,
    FireFlowRequest,
    FirePumpHeadRequest,
    FireWaterTankRequest,
    JockeyPumpRequest,
    FirePipeSizingRequest,
    GeneratorRoomVentilationRequest,
    GeneratorSizingRequest,
    HeaterCapacityRequest,
    HydraulicCalculationRequest,
    HydrotestRequest,
    LightingLuxRequest,
    NozzlePressureRequest,
    HoseReelRequest,
    PipeSizeRequest,
    PressureDropRequest,
    PumpSelectionRequest,
    RainwaterPipeRequest,
    SprinklerSpacingRequest,
    StandpipeRequest,
    SumpTankRequest,
    TransformerSizingRequest,
    UPSSizingRequest,
    VoltageDropRequest,
    WaterDemandRequest,
    WaterTankRequest,
    FixtureUnitRequest,
)
from app.services.plumbing_calculators import (
    calculate_drainage_pipe,
    calculate_fixture_units,
    calculate_pipe_diameter,
    calculate_pump_power,
    calculate_rainwater_pipe,
    calculate_water_demand,
    calculate_water_tank_capacity,
    calculate_sump_size,
)
from app.services.electrical_calculators import (
    calculate_battery_sizing,
    calculate_cable_size,
    calculate_circuit_breaker,
    calculate_current,
    calculate_earthing_resistance,
    calculate_generator_sizing,
    calculate_lighting_lux,
    calculate_power_factor,
    calculate_transformer_sizing,
    calculate_ups_sizing,
    calculate_voltage_drop,
)
from app.services.fire_calculators import (
    calculate_fire_flow,
    calculate_fire_pump_head,
    calculate_fire_water_tank,
    calculate_fire_pipe_size,
    calculate_hose_reel_pressure,
    calculate_hydraulic_loss,
    calculate_jockey_pump,
    calculate_nozzle_pressure,
    calculate_sprinkler_spacing,
    calculate_standpipe_pressure,
)
from fastapi.templating import Jinja2Templates
from app.utils.xlsx_export import build_calculator_pdf, build_calculator_workbook

router = APIRouter()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")

CATEGORY_META = {
    "plumbing": "Plumbing",
    "electrical": "Electrical",
    "fire": "Fire Fighting",
}

CALCULATOR_PAGES = {
    "water-demand": {
        "category": "plumbing",
        "title": "Water Demand Calculator",
        "description": "Estimate domestic and process water demand in liters per minute.",
        "fields": [
            {
                "name": "building_type",
                "label": "Building Type",
                "type": "select",
                "options": ["Residential", "Commercial", "Industrial", "Institutional", "Mixed-use"],
                "required": True,
            },
            {"name": "occupancy", "label": "Occupancy", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "fixture_units", "label": "Fixture Units", "type": "number", "min": "0.1", "step": "0.1", "required": True},
        ],
        "function": calculate_water_demand,
        "schema": WaterDemandRequest,
        "result_label": "Water Demand",
        "result_key": "water_demand_lpm",
        "result_unit": "LPM",
        "formula": "Demand = max(occupancy × 0.12, fixture units × 1.1) × building type factor",
        "reference": "Adapted from domestic water demand design practices.",
    },
    "pipe-sizing": {
        "category": "plumbing",
        "title": "Pipe Size Calculator",
        "description": "Calculate the minimum pipe diameter for a target flow and velocity.",
        "fields": [
            {"name": "flow_rate", "label": "Flow Rate (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "velocity", "label": "Velocity (m/s)", "type": "number", "min": "0.1", "step": "0.01", "required": True},
        ],
        "function": calculate_pipe_diameter,
        "schema": PipeSizeRequest,
        "result_label": "Recommended Pipe Diameter",
        "result_key": "pipe_diameter_mm",
        "result_unit": "mm",
        "formula": "d = sqrt(4Q / (π v)) where Q is flow in m³/s.",
        "reference": "Standard hydraulics for pipe sizing using continuity equation.",
    },
    "drainage-pipe": {
        "category": "plumbing",
        "title": "Drainage Pipe Calculator",
        "description": "Recommend drainage pipe size based on fixture load and slope.",
        "fields": [
            {"name": "fixture_units", "label": "Fixture Units", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "slope_percent", "label": "Slope (%)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
        ],
        "function": calculate_drainage_pipe,
        "schema": DrainagePipeRequest,
        "result_label": "Recommended Pipe Diameter",
        "result_key": "pipe_diameter_mm",
        "result_unit": "mm",
        "formula": "Select diameter from fixture units and minimum slope; ensure adequate self-cleansing velocity.",
        "reference": "Drainage design tables and slope guidelines.",
    },
    "rainwater-pipe": {
        "category": "plumbing",
        "title": "Rainwater Pipe Calculator",
        "description": "Compute a rainwater drain diameter based on roof area and intensity.",
        "fields": [
            {"name": "roof_area", "label": "Roof Area (m²)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "rainfall_intensity", "label": "Rainfall Intensity (mm/h)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
        ],
        "function": calculate_rainwater_pipe,
        "schema": RainwaterPipeRequest,
        "result_label": "Rainwater Pipe Diameter",
        "result_key": "pipe_diameter_mm",
        "result_unit": "mm",
        "formula": "D = sqrt(4Q/πv) with Q = roof area × intensity / 3600.",
        "reference": "Rainwater drainage sizing using hydraulic continuity.",
    },
    "water-tank": {
        "category": "plumbing",
        "title": "Water Tank Calculator",
        "description": "Determine storage capacity for a given daily water demand.",
        "fields": [
            {"name": "daily_demand", "label": "Daily Demand (L)", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "storage_hours", "label": "Storage Hours", "type": "number", "min": "1", "step": "0.1", "required": True},
        ],
        "function": calculate_water_tank_capacity,
        "schema": WaterTankRequest,
        "result_label": "Tank Capacity",
        "result_key": "tank_capacity_l",
        "result_unit": "L",
        "formula": "Capacity = daily demand × storage hours / 24.",
        "reference": "Potable water storage sizing for service continuity.",
    },
    "sump-tank": {
        "category": "plumbing",
        "title": "Sump Tank Calculator",
        "description": "Estimate sump volume needed for pump cycling and daily flow.",
        "fields": [
            {"name": "daily_demand", "label": "Daily Demand (L)", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "pump_cycles", "label": "Pump Cycles per Day", "type": "number", "min": "1", "step": "1", "required": True},
        ],
        "function": calculate_sump_size,
        "schema": SumpTankRequest,
        "result_label": "Sump Volume",
        "result_key": "sump_volume_l",
        "result_unit": "L",
        "formula": "Volume = daily demand / pump cycles × 1.2.",
        "reference": "Sump sizing for pump repeat cycles and safety overflow." ,
    },
    "pump-selection": {
        "category": "plumbing",
        "title": "Pump Selection Calculator",
        "description": "Size pump power for required flow, head, and efficiency.",
        "fields": [
            {"name": "flow", "label": "Flow (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "head", "label": "Head (m)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "efficiency", "label": "Efficiency (%)", "type": "number", "min": "1", "max": "100", "step": "0.1", "required": True},
        ],
        "function": calculate_pump_power,
        "schema": PumpSelectionRequest,
        "result_label": "Pump Power",
        "result_key": "pump_power_kw",
        "result_unit": "kW",
        "formula": "Power = 9.81 × Q × H / η with Q in m³/s.",
        "reference": "Pump hydraulic power formula for centrifugal pump selection.",
    },
    "fixture-unit": {
        "category": "plumbing",
        "title": "Fixture Unit Calculator",
        "description": "Sum fixture units for plumbing load calculations.",
        "fields": [
            {"name": "fixture_type", "label": "Fixture Type", "type": "select", "options": ["WC", "Urinal", "Sink", "Shower", "Bathtub", "Kitchen Sink", "Laundry", "Dishwasher"], "required": True},
            {"name": "quantity", "label": "Quantity", "type": "number", "min": "1", "step": "1", "required": True},
        ],
        "function": calculate_fixture_units,
        "schema": FixtureUnitRequest,
        "result_label": "Total Fixture Units",
        "result_key": "total_fixture_units",
        "result_unit": "FU",
        "formula": "Total fixture units = quantity × fixture unit factor.",
        "reference": "Domestic fixture unit load calculation.",
    },
    "cable-sizing": {
        "category": "electrical",
        "title": "Cable Size Calculator",
        "description": "Estimate conductor area from current demand and derating.",
        "fields": [
            {"name": "current", "label": "Current (A)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "ambient_temperature", "label": "Ambient Temperature (°C)", "type": "number", "min": "0", "step": "0.1", "required": True},
        ],
        "function": calculate_cable_size,
        "schema": CableSizeRequest,
        "result_label": "Conductor Area",
        "result_key": "conductor_area_mm2",
        "result_unit": "mm²",
        "formula": "Area = 1.25 × current / allowable current density.",
        "reference": "IEC cable derating and conductor sizing practice.",
    },
    "voltage-drop": {
        "category": "electrical",
        "title": "Voltage Drop Calculator",
        "description": "Calculate conductor voltage drop for feeders and branches.",
        "fields": [
            {"name": "voltage", "label": "Voltage (V)", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "current", "label": "Current (A)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "length", "label": "Length (m)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "conductor_area", "label": "Conductor Area (mm²)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "power_factor", "label": "Power Factor", "type": "number", "min": "0.1", "max": "1", "step": "0.01", "required": True},
            {"name": "phase_type", "label": "Phase Type", "type": "select", "options": ["Single-phase", "Three-phase"], "required": True},
        ],
        "function": calculate_voltage_drop,
        "schema": VoltageDropRequest,
        "result_label": "Voltage Drop",
        "result_key": "percent_drop",
        "result_unit": "%",
        "formula": "Vd = k × I × L / A with phase factor for single/three-phase.",
        "reference": "Voltage drop calculation for electrical circuits.",
    },
    "current": {
        "category": "electrical",
        "title": "Current Calculator",
        "description": "Calculate current from power, voltage and power factor.",
        "fields": [
            {"name": "power", "label": "Power (kW)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "voltage", "label": "Voltage (V)", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "power_factor", "label": "Power Factor", "type": "number", "min": "0.1", "max": "1", "step": "0.01", "required": True},
            {"name": "phase_type", "label": "Phase Type", "type": "select", "options": ["Single-phase", "Three-phase"], "required": True},
        ],
        "function": calculate_current,
        "schema": CurrentCalculatorRequest,
        "result_label": "Current",
        "result_key": "current_a",
        "result_unit": "A",
        "formula": "I = (kW × 1000) / (V × pf) or I = (kW × 1000) / (1.732 × V × pf).",
        "reference": "Electrical current calculation for load sizing.",
    },
    "transformer-sizing": {
        "category": "electrical",
        "title": "Transformer Sizing Calculator",
        "description": "Estimate transformer kVA rating from load and power factor.",
        "fields": [
            {"name": "load", "label": "Load (kW)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "power_factor", "label": "Power Factor", "type": "number", "min": "0.1", "max": "1", "step": "0.01", "required": True},
        ],
        "function": calculate_transformer_sizing,
        "schema": TransformerSizingRequest,
        "result_label": "Required Transformer Rating",
        "result_key": "required_kva",
        "result_unit": "kVA",
        "formula": "kVA = kW / (pf × 0.8) with service factor.",
        "reference": "Transformer sizing using load and power factor.",
    },
    "generator-sizing": {
        "category": "electrical",
        "title": "Generator Sizing Calculator",
        "description": "Estimate backup generator capacity for electrical loads.",
        "fields": [
            {"name": "load", "label": "Load (kW)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "power_factor", "label": "Power Factor", "type": "number", "min": "0.1", "max": "1", "step": "0.01", "required": True},
            {"name": "starting_load_factor", "label": "Starting Load Factor", "type": "number", "min": "1", "step": "0.1", "required": True},
        ],
        "function": calculate_generator_sizing,
        "schema": GeneratorSizingRequest,
        "result_label": "Required Generator Rating",
        "result_key": "required_kva",
        "result_unit": "kVA",
        "formula": "kVA = kW / (pf × 0.8) × starting factor.",
        "reference": "Generator sizing with starting load allowance.",
    },
    "ups-sizing": {
        "category": "electrical",
        "title": "UPS Sizing Calculator",
        "description": "Calculate UPS rating and battery needs for backup autonomy.",
        "fields": [
            {"name": "load", "label": "Load (kW)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "autonomy_minutes", "label": "Autonomy (minutes)", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "efficiency", "label": "Efficiency (%)", "type": "number", "min": "1", "max": "100", "step": "0.1", "required": True},
        ],
        "function": calculate_ups_sizing,
        "schema": UPSSizingRequest,
        "result_label": "UPS Rating",
        "result_key": "required_kva",
        "result_unit": "kVA",
        "formula": "UPS kVA = load / (0.8 × η).",
        "reference": "UPS capacity and battery energy sizing.",
    },
    "lighting-lux": {
        "category": "electrical",
        "title": "Lighting Lux Calculator",
        "description": "Estimate lighting power required to meet target illuminance.",
        "fields": [
            {"name": "area", "label": "Area (m²)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "target_lux", "label": "Target Lux", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "lumens_per_watt", "label": "Lumens per Watt", "type": "number", "min": "1", "step": "1", "required": True},
        ],
        "function": calculate_lighting_lux,
        "schema": LightingLuxRequest,
        "result_label": "Required Lighting Power",
        "result_key": "required_power_w",
        "result_unit": "W",
        "formula": "Power = area × lux / (lm/W × UF × MF).",
        "reference": "Lighting design using utilization and maintenance factors.",
    },
    "circuit-breaker": {
        "category": "electrical",
        "title": "Circuit Breaker Calculator",
        "description": "Recommend breaker rating based on design current.",
        "fields": [
            {"name": "current", "label": "Current (A)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "breaker_type", "label": "Breaker Type", "type": "select", "options": ["Thermal Magnetic", "Electronic", "Molded Case"], "required": True},
        ],
        "function": calculate_circuit_breaker,
        "schema": CircuitBreakerRequest,
        "result_label": "Recommended Breaker Rating",
        "result_key": "recommended_rating_a",
        "result_unit": "A",
        "formula": "Rating = design current = current × 1.25.",
        "reference": "Circuit breaker selection using industry design margin.",
    },
    "fire-pump-head": {
        "category": "fire",
        "title": "Fire Pump Head Calculator",
        "description": "Calculate required pump head from system pressure and elevation.",
        "fields": [
            {"name": "flow", "label": "Flow (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "system_pressure", "label": "System Pressure (kPa)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "elevation", "label": "Elevation (m)", "type": "number", "min": "0", "step": "0.1", "required": True},
        ],
        "function": calculate_fire_pump_head,
        "schema": FirePumpHeadRequest,
        "result_label": "Total Pump Head",
        "result_key": "total_head_m",
        "result_unit": "m",
        "formula": "H = elevation + pressure/9.81 + safety allowance.",
        "reference": "Fire pump head calculation for system design.",
    },
    "fire-flow": {
        "category": "fire",
        "title": "Fire Water Demand Calculator",
        "description": "Calculate fire water demand from hazard classification.",
        "fields": [
            {"name": "area", "label": "Area (m²)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "hazard_class", "label": "Hazard Class", "type": "select", "options": ["Light", "Ordinary", "Extra", "High"], "required": True},
        ],
        "function": calculate_fire_flow,
        "schema": FireFlowRequest,
        "result_label": "Fire Water Demand",
        "result_key": "fire_flow_lpm",
        "result_unit": "LPM",
        "formula": "Flow = area × density based on hazard class.",
        "reference": "Fire flow estimation using hazard flow densities.",
    },
    "jockey-pump": {
        "category": "fire",
        "title": "Jockey Pump Calculator",
        "description": "Estimate jockey pump pressure setpoint and power requirements.",
        "fields": [
            {"name": "pump_flow_lpm", "label": "Pump Flow (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "system_pressure_kpa", "label": "System Pressure (kPa)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "pressure_margin_kpa", "label": "Pressure Margin (kPa)", "type": "number", "min": "0.1", "step": "0.1", "required": True, "value": 10.0},
            {"name": "efficiency_percent", "label": "Efficiency (%)", "type": "number", "min": "1", "max": "100", "step": "0.1", "required": True, "value": 70.0},
        ],
        "function": calculate_jockey_pump,
        "schema": JockeyPumpRequest,
        "result_label": "Operating Pressure",
        "result_key": "operating_pressure_kpa",
        "result_unit": "kPa",
        "formula": "Pset = system pressure + margin; Head = Pset / 9.81; Power = ρ g Q H / η.",
        "reference": "Jockey pump sizing for fire protection pressure control.",
    },
    "fire-water-tank": {
        "category": "fire",
        "title": "Fire Water Tank Calculator",
        "description": "Estimate fire water storage capacity for a duration.",
        "fields": [
            {"name": "demand", "label": "Demand (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "duration", "label": "Duration (hours)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
        ],
        "function": calculate_fire_water_tank,
        "schema": FireWaterTankRequest,
        "result_label": "Tank Capacity",
        "result_key": "tank_capacity_l",
        "result_unit": "L",
        "formula": "Capacity = demand × duration × 60.",
        "reference": "Fire water storage for required operating duration.",
    },
    "sprinkler-spacing": {
        "category": "fire",
        "title": "Sprinkler Spacing Calculator",
        "description": "Estimate maximum sprinkler spacing for a given area.",
        "fields": [
            {"name": "area", "label": "Area (m²)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "efficiency", "label": "Efficiency (%)", "type": "number", "min": "1", "max": "100", "step": "1", "required": True},
        ],
        "function": calculate_sprinkler_spacing,
        "schema": SprinklerSpacingRequest,
        "result_label": "Sprinkler Spacing",
        "result_key": "sprinkler_spacing_m",
        "result_unit": "m",
        "formula": "Spacing = sqrt(area × efficiency fraction).",
        "reference": "Sprinkler coverage calculation for layout planning.",
    },
    "fire-pipe-sizing": {
        "category": "fire",
        "title": "Fire Pipe Sizing Calculator",
        "description": "Calculate the minimum fire service pipe diameter for a target flow and velocity.",
        "fields": [
            {"name": "flow_rate_lpm", "label": "Flow Rate (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "velocity_m_s", "label": "Velocity (m/s)", "type": "number", "min": "0.1", "step": "0.01", "required": True},
        ],
        "function": calculate_fire_pipe_size,
        "schema": FirePipeSizingRequest,
        "result_label": "Recommended Pipe Diameter",
        "result_key": "pipe_diameter_mm",
        "result_unit": "mm",
        "formula": "d = sqrt(4Q / (π v)) with Q in m³/s.",
        "reference": "Fire service pipe sizing using continuity equation.",
    },
    "standpipe": {
        "category": "fire",
        "title": "Standpipe Pressure Calculator",
        "description": "Estimate standpipe pressure required at a hose outlet.",
        "fields": [
            {"name": "height", "label": "Height (m)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "hose_length", "label": "Hose Length (m)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "friction_loss", "label": "Friction Loss (kPa/m)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
        ],
        "function": calculate_standpipe_pressure,
        "schema": StandpipeRequest,
        "result_label": "Required Standpipe Pressure",
        "result_key": "required_pressure_kpa",
        "result_unit": "kPa",
        "formula": "P = elevation × 9.81 + hose loss + margin.",
        "reference": "Standpipe pressure demand calculation.",
    },
    "hose-reel-pressure": {
        "category": "fire",
        "title": "Hose Reel Pressure Calculator",
        "description": "Estimate pressure needed for a hose reel system.",
        "fields": [
            {"name": "flow", "label": "Flow (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "hose_length", "label": "Hose Length (m)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "nozzle_pressure", "label": "Nozzle Pressure (kPa)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
        ],
        "function": calculate_hose_reel_pressure,
        "schema": HoseReelRequest,
        "result_label": "Total Hose Reel Pressure",
        "result_key": "total_pressure_kpa",
        "result_unit": "kPa",
        "formula": "Total pressure = hose loss + nozzle pressure.",
        "reference": "Hose reel pressure requirements for fire service.",
    },
    "nozzle-pressure": {
        "category": "fire",
        "title": "Nozzle Pressure Calculator",
        "description": "Estimate nozzle outlet pressure for a given flow.",
        "fields": [
            {"name": "flow", "label": "Flow (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "nozzle_coefficient", "label": "Nozzle Coefficient", "type": "number", "min": "0.1", "step": "0.01", "required": True},
        ],
        "function": calculate_nozzle_pressure,
        "schema": NozzlePressureRequest,
        "result_label": "Required Nozzle Pressure",
        "result_key": "required_pressure_kpa",
        "result_unit": "kPa",
        "formula": "P = (Q / coefficient)² × constant.",
        "reference": "Nozzle pressure from discharge coefficient.",
    },
    "hydraulic-calculation": {
        "category": "fire",
        "title": "Hydraulic Calculation",
        "description": "Estimate friction head loss for a pipe run.",
        "fields": [
            {"name": "flow", "label": "Flow (LPM)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "diameter", "label": "Diameter (mm)", "type": "number", "min": "1", "step": "1", "required": True},
            {"name": "length", "label": "Length (m)", "type": "number", "min": "0.1", "step": "0.1", "required": True},
            {"name": "roughness", "label": "Roughness (mm)", "type": "number", "min": "0.01", "step": "0.01", "required": True},
        ],
        "function": calculate_hydraulic_loss,
        "schema": HydraulicCalculationRequest,
        "result_label": "Head Loss",
        "result_key": "head_loss_m",
        "result_unit": "m",
        "formula": "Use Darcy-Weisbach friction factor with Reynolds number and roughness.",
        "reference": "Hydraulic friction loss using velocity, diameter and roughness.",
    },
}


def _strip_project_name(form_data: dict) -> tuple[dict, str | None]:
    values = dict(form_data)
    project_name = values.pop("project_name", None)
    return values, project_name


def get_calculator(category: str, slug: str):
    page = CALCULATOR_PAGES.get(slug)
    if not page or page["category"] != category:
        raise HTTPException(status_code=404, detail="Calculator not found.")
    return page


@router.get("/calculators/{category}/{slug}")
async def get_calculator_page(request: Request, category: str, slug: str):
    page = get_calculator(category, slug)
    return templates.TemplateResponse(
        request,
        "calculators/calculator_page.html",
        {
            "page": page,
            "values": {},
            "result": None,
            "error": None,
        },
    )


@router.post("/calculators/{category}/{slug}")
async def post_calculator_page(request: Request, category: str, slug: str):
    page = get_calculator(category, slug)
    form_data = await request.form()
    values, _ = _strip_project_name(dict(form_data))
    result = None
    error = None

    try:
        validated = page["schema"].parse_obj(values)
        result = page["function"](**validated.dict())
    except ValidationError as ex:
        # Log details to application logger and return a friendly message to the user
        import logging
        logging.getLogger('ai_mep').info('Validation error in HVAC calculator: %s', str(ex))
        error = "Please check the highlighted fields and try again."
    except Exception as ex:
        import logging
        logging.getLogger('ai_mep').exception('Error running HVAC calculator: %s', str(ex))
        # Friendly generic message for calculation failures
        error = "Calculation could not be completed. Please verify your inputs and try again."

    return templates.TemplateResponse(
        request,
        "calculators/calculator_page.html",
        {
            "page": page,
            "values": values,
            "result": result,
            "error": error,
        },
    )


@router.post("/calculators/{category}/{slug}/export_excel")
async def export_calculator_excel(request: Request, category: str, slug: str):
    page = get_calculator(category, slug)
    form_data = await request.form()
    values, project_name = _strip_project_name(dict(form_data))

    try:
        validated = page["schema"].parse_obj(values)
        result = page["function"](**validated.dict())
    except ValidationError as ex:
        raise HTTPException(status_code=400, detail="; ".join([f"{err['loc'][0]}: {err['msg']}" for err in ex.errors()]))
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    stream = build_calculator_workbook(
        page["title"],
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
    response.headers["Content-Disposition"] = f"attachment; filename={slug}.xlsx"
    return response


@router.post("/calculators/{category}/{slug}/export_pdf")
async def export_calculator_pdf(request: Request, category: str, slug: str):
    page = get_calculator(category, slug)
    form_data = await request.form()
    values, project_name = _strip_project_name(dict(form_data))

    try:
        validated = page["schema"].parse_obj(values)
        result = page["function"](**validated.dict())
    except ValidationError as ex:
        raise HTTPException(status_code=400, detail="; ".join([f"{err['loc'][0]}: {err['msg']}" for err in ex.errors()]))
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    stream = build_calculator_pdf(
        page["title"],
        values,
        result,
        page=page,
        project_name=project_name,
    )
    stream.seek(0)

    response = StreamingResponse(stream, media_type="application/pdf")
    response.headers["Content-Disposition"] = f"attachment; filename={slug}.pdf"
    return response


@router.post("/api/calculators/{category}/{slug}")
async def api_calculate(category: str, slug: str, request: Request):
    page = get_calculator(category, slug)
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON payload."})

    try:
        validated = page["schema"].parse_obj(payload)
    except ValidationError as ex:
        return JSONResponse(
            status_code=422,
            content={"error": "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in ex.errors()])},
        )

    try:
        result = page["function"](**validated.dict())
    except Exception as ex:
        return JSONResponse(status_code=400, content={"error": str(ex)})

    return JSONResponse(content={"result": result})
