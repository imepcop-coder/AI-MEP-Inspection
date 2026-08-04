import math
from typing import Any, Dict, Optional


class UAEPlumbingError(Exception):
    """Engineering exception for UAE plumbing calculations."""


def _coerce_float(value: Any, name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise UAEPlumbingError(f"{name} must be numeric.") from exc

    if not math.isfinite(numeric_value):
        raise UAEPlumbingError(f"{name} must be a finite number.")

    return numeric_value


def _positive(value: Any, name: str) -> float:
    numeric_value = _coerce_float(value, name)
    if numeric_value <= 0.0:
        raise UAEPlumbingError(f"{name} must be greater than zero.")
    return numeric_value


def _non_negative(value: Any, name: str) -> float:
    numeric_value = _coerce_float(value, name)
    if numeric_value < 0.0:
        raise UAEPlumbingError(f"{name} must be greater than or equal to zero.")
    return numeric_value


def _percentage(value: Any, name: str) -> float:
    numeric_value = _coerce_float(value, name)
    if not 0.0 <= numeric_value <= 100.0:
        raise UAEPlumbingError(f"{name} must be between 0 and 100 percent.")
    return numeric_value


def _velocity(value: Any, name: str, service: str = "Cold") -> float:
    numeric_value = _positive(value, name)
    service_key = (service or "Cold").strip().lower()
    if service_key == "hot":
        if numeric_value > MAX_HOT_WATER_VELOCITY:
            raise UAEPlumbingError("Velocity exceeds UAE recommended limit for hot water.")
    elif service_key == "cold":
        if numeric_value > MAX_COLD_WATER_VELOCITY:
            raise UAEPlumbingError("Velocity exceeds UAE recommended limit for cold water.")
    return numeric_value


def _flow(value: Any, name: str) -> float:
    return _positive(value, name)


def _pressure(value: Any, name: str) -> float:
    return _positive(value, name)


def _pipe_size(value: Any, name: str) -> float:
    return _positive(value, name)


def _build_response(
    inputs: Dict[str, Any],
    results: Dict[str, Any],
    summary: Dict[str, Any],
    remarks: Optional[list[str]] = None,
    calculation_steps: Optional[Dict[str, str]] = None,
    standards: Optional[list[str]] = None,
) -> Dict[str, Any]:
    return {
        "inputs": inputs,
        "results": results,
        "summary": summary,
        "remarks": remarks or [],
        "standards": standards or UAE_STANDARDS,
        "calculation_steps": calculation_steps or {},
    }


def _format_flow_lps(lpm: float) -> float:
    return round(lpm / 60.0, 3)


def _format_gpm(lpm: float) -> float:
    return round(lpm / 3.78541, 3)


def _format_m3_hr(lpm: float) -> float:
    return round(lpm / 1000.0 * 60.0, 3)


def _next_standard_pipe_size(diameter_mm: float) -> int:
    for size in STANDARD_PIPE_SIZES_MM:
        if size >= diameter_mm:
            return size
    return STANDARD_PIPE_SIZES_MM[-1]


def _pipe_velocity_from_flow(flow_lpm: float, diameter_mm: float) -> float:
    flow_m3_s = flow_lpm / 1000.0 / 60.0
    diameter_m = diameter_mm / 1000.0
    area_m2 = math.pi * diameter_m**2 / 4.0
    return flow_m3_s / area_m2 if area_m2 > 0 else 0.0


def _hazen_williams_head_loss_m(flow_lpm: float, diameter_mm: float, length_m: float, c_factor: float = 120.0) -> float:
    flow_m3_s = flow_lpm / 1000.0 / 60.0
    diameter_m = diameter_mm / 1000.0
    return (
        10.67
        * length_m
        * flow_m3_s**1.852
        / (c_factor**1.852 * diameter_m**4.8704)
        if c_factor > 0.0
        else 0.0
    )


# ----------------------------------------------------------------------
# 1. Domestic water demand (IPC/UPC + UAE practice)
# ----------------------------------------------------------------------

LITERS_PER_PERSON_UAE = {
    "Residential": 135.0,
    "Apartment": 135.0,
    "Villa": 180.0,
    "Hotel": 250.0,
    "Hospital": 450.0,
    "Office": 45.0,
    "School": 45.0,
    "Restaurant": 70.0,
    "Mall": 25.0,
    "Industrial": 60.0,
}

PEAK_FACTOR_UAE = {
    "Residential": 2.5,
    "Apartment": 2.5,
    "Villa": 2.2,
    "Hotel": 2.0,
    "Hospital": 1.8,
    "Office": 2.0,
    "School": 2.0,
    "Restaurant": 2.5,
    "Mall": 2.0,
    "Industrial": 1.8,
}

UAE_STANDARDS = [
    "IPC",
    "UPC",
    "ASPE Plumbing Engineering Design Handbook",
    "Dubai Municipality",
    "Abu Dhabi DMT",
    "DEWA",
    "UAE Plumbing Code",
]

GRAVITY_M_S2 = 9.81
DEFAULT_PUMP_EFFICIENCY = 70.0
MAX_COLD_WATER_VELOCITY = 2.0
MAX_HOT_WATER_VELOCITY = 1.5
STANDARD_PIPE_SIZES_MM = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300]


def uae_water_demand(building_type: str, occupancy: int, fixture_units: float = 0.0) -> Dict[str, Any]:
    """Calculate UAE domestic water demand with an engineering-ready envelope."""
    if building_type not in LITERS_PER_PERSON_UAE:
        raise UAEPlumbingError("Unsupported building type for UAE water demand.")

    occupancy_value = int(_positive(occupancy, "Occupancy"))
    fixture_units_value = _non_negative(fixture_units, "Fixture units")
    lpp = LITERS_PER_PERSON_UAE[building_type]
    peak_factor = PEAK_FACTOR_UAE[building_type]

    daily_water_demand_lpd = occupancy_value * lpp
    average_flow_lpm = daily_water_demand_lpd / (24.0 * 60.0)
    peak_flow_lpm = average_flow_lpm * peak_factor
    peak_flow_lps = _format_flow_lps(peak_flow_lpm)
    peak_flow_gpm = _format_gpm(peak_flow_lpm)
    peak_flow_m3_hr = _format_m3_hr(peak_flow_lpm)

    fixture_demand_lpm = fixture_units_value * 0.2 if fixture_units_value > 0.0 else 0.0
    design_flow_lpm = max(peak_flow_lpm, fixture_demand_lpm)
    design_flow_lps = _format_flow_lps(design_flow_lpm)
    design_flow_gpm = _format_gpm(design_flow_lpm)

    results = {
        "building_type": building_type,
        "occupancy": occupancy_value,
        "fixture_units": round(fixture_units_value, 2),
        "liters_per_person_per_day": round(lpp, 2),
        "daily_water_demand_l_per_day": round(daily_water_demand_lpd, 2),
        "average_flow_lpm": round(average_flow_lpm, 3),
        "average_flow_lps": round(average_flow_lpm / 60.0, 3),
        "average_flow_gpm": round(average_flow_lpm / 3.78541, 3),
        "average_flow_m3_hr": round(average_flow_lpm / 1000.0 * 60.0, 3),
        "peak_factor": round(peak_factor, 2),
        "peak_flow_lpm": round(peak_flow_lpm, 3),
        "peak_flow_lps": round(peak_flow_lps, 3),
        "peak_flow_gpm": round(peak_flow_gpm, 3),
        "peak_flow_m3_hr": round(peak_flow_m3_hr, 3),
        "design_flow_lpm": round(design_flow_lpm, 3),
        "design_flow_lps": round(design_flow_lps, 3),
        "design_flow_gpm": round(design_flow_gpm, 3),
        "design_flow_m3_hr": round(design_flow_lpm / 1000.0 * 60.0, 3),
    }

    summary = {
        "Daily Water Demand (L/day)": round(daily_water_demand_lpd, 2),
        "Peak Water Demand (LPM)": round(peak_flow_lpm, 3),
        "Design Flow (LPS)": round(design_flow_lps, 3),
    }

    remarks = []
    if peak_factor > 2.0:
        remarks.append("Peak demand factor is elevated; verify simultaneous use assumptions.")
    if building_type in {"Hotel", "Hospital", "Restaurant"}:
        remarks.append("High-use occupancy profile; confirm local authority demand criteria.")

    calculation_steps = {
        "Daily Water Demand": "Occupancy × Liters Per Person per Day",
        "Average Demand": "Daily Water Demand ÷ 24 ÷ 60",
        "Peak Demand": "Average Demand × Peak Factor",
        "Design Flow": "Maximum of Peak Demand and Fixture-based demand",
    }

    return _build_response(
        inputs={"building_type": building_type, "occupancy": occupancy_value, "fixture_units": round(fixture_units_value, 2)},
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 2. Fixture units (IPC/UPC style)
# ----------------------------------------------------------------------

FIXTURE_UNITS_UAE = {
    "Water Closet": 4.0,
    "Wash Basin": 1.0,
    "Kitchen Sink": 2.0,
    "Urinal": 2.0,
    "Shower": 2.0,
    "Bathtub": 4.0,
    "Drinking Fountain": 0.5,
    "Service Sink": 3.0,
}


def uae_fixture_units(fixture_type: str, quantity: int) -> Dict[str, Any]:
    """Calculate fixture unit loading with engineering guidance."""
    if fixture_type not in FIXTURE_UNITS_UAE:
        raise UAEPlumbingError("Unsupported fixture type for UAE fixture units.")

    quantity_value = int(_positive(quantity, "Quantity"))
    fixture_unit_value = FIXTURE_UNITS_UAE[fixture_type]
    total_fixture_units = fixture_unit_value * quantity_value

    results = {
        "fixture_type": fixture_type,
        "quantity": quantity_value,
        "fixture_unit_per_item": round(fixture_unit_value, 2),
        "total_fixture_units": round(total_fixture_units, 2),
        "equivalent_water_demand_lpm": round(total_fixture_units * 0.2, 3),
    }

    summary = {
        "Total Fixture Units": round(total_fixture_units, 2),
        "Equivalent Design Flow (LPS)": round(total_fixture_units * 0.2 / 60.0, 3),
    }

    remarks = []
    if total_fixture_units >= 100.0:
        remarks.append("Fixture loading is high; verify branch and stack sizing with the local authority design criteria.")

    calculation_steps = {
        "Fixture Units": "Fixture Unit per Item × Quantity",
        "Equivalent Design Flow": "Fixture Units × 0.2 LPM per FU",
    }

    return _build_response(
        inputs={"fixture_type": fixture_type, "quantity": quantity_value},
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 3. Pipe sizing by velocity (UAE limits)
# ----------------------------------------------------------------------


def uae_pipe_size(flow_rate_lpm: float, velocity_m_s: float, service: str = "Cold", pipe_material: str = "PVC") -> Dict[str, Any]:
    """Size a pipe using the velocity method and include friction-loss check."""
    flow_rate_value = _flow(flow_rate_lpm, "Flow rate")
    velocity_value = _velocity(velocity_m_s, "Velocity", service=service)
    pipe_material_value = (pipe_material or "PVC").strip() or "PVC"

    flow_m3_s = flow_rate_value / 1000.0 / 60.0
    diameter_m = math.sqrt((4.0 * flow_m3_s) / (math.pi * velocity_value))
    diameter_mm = diameter_m * 1000.0
    recommended_size_mm = _next_standard_pipe_size(diameter_mm)
    selected_velocity_m_s = _pipe_velocity_from_flow(flow_rate_value, recommended_size_mm)
    friction_loss_m_per_100m = _hazen_williams_head_loss_m(flow_rate_value, recommended_size_mm, 100.0, 120.0)
    friction_loss_kpa_per_100m = friction_loss_m_per_100m * 9.81

    results = {
        "pipe_material": pipe_material_value,
        "service": service,
        "flow_rate_lpm": round(flow_rate_value, 3),
        "flow_rate_lps": round(flow_rate_value / 60.0, 3),
        "flow_rate_gpm": round(flow_rate_value / 3.78541, 3),
        "velocity_m_s": round(velocity_value, 3),
        "required_diameter_mm": round(diameter_mm, 2),
        "required_diameter_inch": round(diameter_mm / 25.4, 3),
        "recommended_nominal_size_mm": recommended_size_mm,
        "recommended_nominal_size_inch": round(recommended_size_mm / 25.4, 3),
        "selected_velocity_m_s": round(selected_velocity_m_s, 3),
        "hazen_williams_head_loss_m_per_100m": round(friction_loss_m_per_100m, 3),
        "hazen_williams_pressure_loss_kpa_per_100m": round(friction_loss_kpa_per_100m, 2),
    }

    summary = {
        "Recommended Pipe Size (mm)": recommended_size_mm,
        "Velocity Check": round(selected_velocity_m_s, 3),
        "Pressure Loss (kPa/100m)": round(friction_loss_kpa_per_100m, 2),
    }

    remarks = []
    if selected_velocity_m_s > MAX_COLD_WATER_VELOCITY and service.lower() != "hot":
        remarks.append("Selected pipe size produces a velocity above the recommended cold-water limit.")
    elif selected_velocity_m_s > MAX_HOT_WATER_VELOCITY and service.lower() == "hot":
        remarks.append("Selected pipe size produces a velocity above the recommended hot-water limit.")
    else:
        remarks.append("Pipe velocity is within the UAE design recommendation for the selected service.")

    if friction_loss_kpa_per_100m > 150.0:
        remarks.append("Friction loss is significant; verify pipe sizing and pressure availability.")

    calculation_steps = {
        "Flow Rate Conversion": "Q = flow_rate_lpm ÷ 1000 ÷ 60",
        "Pipe Diameter": "D = √(4Q / πV)",
        "Nominal Size Selection": "Select next standard pipe size above the calculated diameter",
        "Friction Loss": "Hazen-Williams head loss over 100 m",
    }

    return _build_response(
        inputs={"flow_rate_lpm": round(flow_rate_value, 3), "velocity_m_s": round(velocity_value, 3), "service": service, "pipe_material": pipe_material_value},
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 4. Domestic booster pump sizing (UAE practice)
# ----------------------------------------------------------------------


def uae_domestic_booster_pump(
    peak_flow_lps: float,
    building_height_m: float,
    residual_pressure_bar: float = 2.5,
    efficiency_percent: float = DEFAULT_PUMP_EFFICIENCY,
    friction_loss_m: float = 0.0,
) -> Dict[str, Any]:
    """Calculate domestic booster pump requirements with engineering-ready output."""
    peak_flow_value = _flow(peak_flow_lps, "Peak flow")
    building_height_value = _positive(building_height_m, "Building height")
    residual_pressure_value = _pressure(residual_pressure_bar, "Residual pressure")
    efficiency_value = _percentage(efficiency_percent, "Efficiency")
    friction_loss_value = _non_negative(friction_loss_m, "Friction loss")

    elevation_head_m = building_height_value
    residual_head_m = residual_pressure_value * 10.0
    total_head_m = elevation_head_m + residual_head_m + friction_loss_value
    flow_m3_s = peak_flow_value / 1000.0
    hydraulic_power_kw = GRAVITY_M_S2 * flow_m3_s * total_head_m
    motor_power_kw = hydraulic_power_kw / (efficiency_value / 100.0)
    motor_power_hp = motor_power_kw * 1.34102

    results = {
        "peak_flow_lps": round(peak_flow_value, 3),
        "peak_flow_lpm": round(peak_flow_value * 60.0, 3),
        "building_height_m": round(building_height_value, 2),
        "residual_pressure_bar": round(residual_pressure_value, 2),
        "friction_loss_m": round(friction_loss_value, 2),
        "total_head_m": round(total_head_m, 2),
        "hydraulic_power_kw": round(hydraulic_power_kw, 3),
        "motor_power_kw": round(motor_power_kw, 3),
        "motor_power_hp": round(motor_power_hp, 3),
        "efficiency_percent": round(efficiency_value, 1),
    }

    summary = {
        "Required Pump Head (m)": round(total_head_m, 2),
        "Motor Power (kW)": round(motor_power_kw, 3),
        "Motor Power (HP)": round(motor_power_hp, 3),
    }

    remarks = []
    if total_head_m > 60.0:
        remarks.append("Booster pump head is high; consider pressure zoning or intermediate boosting.")
    if efficiency_value < 70.0:
        remarks.append("Pump efficiency is below typical UAE practice; verify driver sizing and pump selection.")

    calculation_steps = {
        "Elevation Head": "Building height above inlet",
        "Residual Pressure Head": "Residual pressure × 10",
        "Total Pump Head": "Elevation head + Residual pressure head + Friction loss",
        "Pump Power": "ρgQH / η",
    }

    return _build_response(
        inputs={
            "peak_flow_lps": round(peak_flow_value, 3),
            "building_height_m": round(building_height_value, 2),
            "residual_pressure_bar": round(residual_pressure_value, 2),
            "efficiency_percent": round(efficiency_value, 1),
            "friction_loss_m": round(friction_loss_value, 2),
        },
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 5. Water tank sizing (UAE practice)
# ----------------------------------------------------------------------


def uae_water_tank_capacity(occupancy: int, building_type: str, storage_days: float = 1.0, reserve_factor: float = 1.0) -> Dict[str, Any]:
    """Calculate potable water storage capacity with reserve allowance."""
    if building_type not in LITERS_PER_PERSON_UAE:
        raise UAEPlumbingError("Unsupported building type for UAE tank sizing.")

    occupancy_value = int(_positive(occupancy, "Occupancy"))
    storage_days_value = _positive(storage_days, "Storage days")
    reserve_factor_value = _positive(reserve_factor, "Reserve factor")
    lpp = LITERS_PER_PERSON_UAE[building_type]

    required_capacity_liters = occupancy_value * lpp * storage_days_value
    reserve_capacity_liters = required_capacity_liters * reserve_factor_value
    reserve_capacity_m3 = reserve_capacity_liters / 1000.0

    results = {
        "building_type": building_type,
        "occupancy": occupancy_value,
        "storage_days": round(storage_days_value, 2),
        "reserve_factor": round(reserve_factor_value, 2),
        "liters_per_person_per_day": round(lpp, 2),
        "required_capacity_liters": round(required_capacity_liters, 2),
        "required_capacity_m3": round(required_capacity_liters / 1000.0, 3),
        "reserve_capacity_liters": round(reserve_capacity_liters, 2),
        "reserve_capacity_m3": round(reserve_capacity_m3, 3),
        "reserve_capacity_gallons": round(reserve_capacity_liters / 3.78541, 2),
    }

    summary = {
        "Tank Capacity (L)": round(reserve_capacity_liters, 2),
        "Tank Capacity (m³)": round(reserve_capacity_m3, 3),
    }

    remarks = []
    if storage_days_value > 1.0:
        remarks.append("Water storage exceeds one day; confirm tank sizing with the client and authority requirements.")
    if reserve_factor_value > 1.0:
        remarks.append("Reserve factor increases storage volume; verify overflow and maintenance access.")

    calculation_steps = {
        "Daily Demand": "Occupancy × Liters Per Person per Day",
        "Storage Requirement": "Daily Demand × Storage Days",
        "Reserve Capacity": "Storage Requirement × Reserve Factor",
    }

    return _build_response(
        inputs={"occupancy": occupancy_value, "building_type": building_type, "storage_days": round(storage_days_value, 2), "reserve_factor": round(reserve_factor_value, 2)},
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 6. Drainage pipe sizing (IPC/UPC style, simplified)
# ----------------------------------------------------------------------


def uae_drainage_pipe(fixture_units: float, slope_percent: float) -> Dict[str, Any]:
    """Size drainage piping with a practical design logic and guidance."""
    fixture_units_value = _positive(fixture_units, "Fixture units")
    slope_percent_value = _non_negative(slope_percent, "Slope")
    if slope_percent_value <= 0.0:
        raise UAEPlumbingError("Slope percent must be greater than zero.")

    if fixture_units_value <= 20.0:
        size_mm = 75
    elif fixture_units_value <= 160.0:
        size_mm = 100
    elif fixture_units_value <= 360.0:
        size_mm = 150
    else:
        size_mm = 200

    if slope_percent_value < 1.0 and size_mm < 100:
        size_mm = 100

    estimated_flow_lps = fixture_units_value * 0.03
    results = {
        "fixture_units": round(fixture_units_value, 2),
        "slope_percent": round(slope_percent_value, 2),
        "recommended_pipe_mm": size_mm,
        "recommended_pipe_inch": round(size_mm / 25.4, 3),
        "estimated_flow_lps": round(estimated_flow_lps, 3),
        "estimated_flow_lpm": round(estimated_flow_lps * 60.0, 3),
    }

    summary = {
        "Recommended Pipe Size (mm)": size_mm,
        "Estimated Flow (LPS)": round(estimated_flow_lps, 3),
    }

    remarks = []
    if slope_percent_value < 1.0:
        remarks.append("The selected slope is shallow; verify drainage capacity and support the larger diameter recommendation.")
    if fixture_units_value > 160.0:
        remarks.append("The drainage load is significant; verify stack and vent sizing.")

    calculation_steps = {
        "Drainage Load": "Fixture Units",
        "Pipe Selection": "Choose pipe size from fixture-unit and slope ranges",
        "Estimated Flow": "Fixture Units × 0.03 LPS",
    }

    return _build_response(
        inputs={"fixture_units": round(fixture_units_value, 2), "slope_percent": round(slope_percent_value, 2)},
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 7. Rainwater pipe sizing (UAE rainfall + IPC logic, simplified)
# ----------------------------------------------------------------------


def uae_rainwater_pipe(roof_area_m2: float, rainfall_intensity_mm_h: float, runoff_coeff: float = 0.9) -> Dict[str, Any]:
    """Size rainwater piping using runoff and rainfall intensity."""
    roof_area_value = _positive(roof_area_m2, "Roof area")
    rainfall_intensity_value = _positive(rainfall_intensity_mm_h, "Rainfall intensity")
    runoff_coeff_value = _non_negative(runoff_coeff, "Runoff coefficient")
    if runoff_coeff_value > 1.0:
        raise UAEPlumbingError("Runoff coefficient must be between 0 and 1.")

    discharge_l_s = roof_area_value * rainfall_intensity_value * runoff_coeff_value / 3600.0
    velocity_m_s = 1.2
    diameter_m = math.sqrt((4.0 * discharge_l_s / 1000.0) / (math.pi * velocity_m_s))
    diameter_mm = diameter_m * 1000.0
    recommended_size_mm = _next_standard_pipe_size(diameter_mm)

    results = {
        "roof_area_m2": round(roof_area_value, 2),
        "rainfall_intensity_mm_h": round(rainfall_intensity_value, 2),
        "runoff_coefficient": round(runoff_coeff_value, 2),
        "discharge_l_s": round(discharge_l_s, 3),
        "discharge_lpm": round(discharge_l_s * 60.0, 3),
        "diameter_mm": round(diameter_mm, 2),
        "diameter_inch": round(diameter_mm / 25.4, 3),
        "recommended_nominal_size_mm": recommended_size_mm,
        "recommended_nominal_size_inch": round(recommended_size_mm / 25.4, 3),
    }

    summary = {
        "Recommended Pipe Size (mm)": recommended_size_mm,
        "Design Discharge (L/s)": round(discharge_l_s, 3),
    }

    remarks = []
    if rainfall_intensity_value > 100.0:
        remarks.append("Rainfall intensity is high; verify roof drain and gutter capacity with the authority requirements.")
    if runoff_coeff_value < 0.8:
        remarks.append("Runoff coefficient is low; verify the roof drainage catchment assumptions.")

    calculation_steps = {
        "Runoff Discharge": "Roof Area × Rainfall Intensity × Runoff Coefficient ÷ 3600",
        "Pipe Diameter": "D = √(4Q / πV)",
    }

    return _build_response(
        inputs={"roof_area_m2": round(roof_area_value, 2), "rainfall_intensity_mm_h": round(rainfall_intensity_value, 2), "runoff_coefficient": round(runoff_coeff_value, 2)},
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 8. Pump power (generic, UAE-style)
# ----------------------------------------------------------------------


def uae_pump_power(flow_lps: float, total_head_m: float, efficiency_percent: float) -> Dict[str, Any]:
    """Calculate hydraulic and motor power for a pump."""
    flow_value = _flow(flow_lps, "Flow")
    head_value = _positive(total_head_m, "Total head")
    efficiency_value = _percentage(efficiency_percent, "Efficiency")

    flow_m3_s = flow_value / 1000.0
    hydraulic_kw = GRAVITY_M_S2 * flow_m3_s * head_value
    motor_kw = hydraulic_kw / (efficiency_value / 100.0)
    motor_hp = motor_kw * 1.34102

    results = {
        "flow_lps": round(flow_value, 3),
        "flow_lpm": round(flow_value * 60.0, 3),
        "flow_gpm": round(flow_value * 60.0 / 3.78541, 3),
        "total_head_m": round(head_value, 2),
        "efficiency_percent": round(efficiency_value, 1),
        "hydraulic_power_kw": round(hydraulic_kw, 3),
        "motor_power_kw": round(motor_kw, 3),
        "motor_power_hp": round(motor_hp, 3),
    }

    summary = {
        "Hydraulic Power (kW)": round(hydraulic_kw, 3),
        "Motor Power (kW)": round(motor_kw, 3),
        "Motor Power (HP)": round(motor_hp, 3),
    }

    remarks = []
    if efficiency_value < 70.0:
        remarks.append("Pump efficiency is below common UAE practice; verify motor and pump selection.")
    if head_value > 60.0:
        remarks.append("Pump head is high; consider staged pumping or pressure zoning.")

    calculation_steps = {
        "Hydraulic Power": "P = ρgQH",
        "Motor Power": "P_motor = P_hydraulic ÷ η",
    }

    return _build_response(
        inputs={"flow_lps": round(flow_value, 3), "total_head_m": round(head_value, 2), "efficiency_percent": round(efficiency_value, 1)},
        results=results,
        summary=summary,
        remarks=remarks,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# Legacy compat wrappers for existing routes and service layer
# ----------------------------------------------------------------------

# Retained for compatibility with the existing FastAPI plumbing routes.

def validate_positive(value: Any, name: str) -> float:
    return _positive(value, name)


def water_demand(building_type: str, occupancy: int, fixture_units: float = 0.0) -> Dict[str, Any]:
    result = uae_water_demand(building_type=building_type, occupancy=occupancy, fixture_units=fixture_units)
    return {
        "building_type": building_type,
        "occupancy": int(_positive(occupancy, "Occupancy")),
        "fixture_units": round(_non_negative(fixture_units, "Fixture units"), 2),
        "liter_person_day": round(result["results"]["liters_per_person_per_day"], 2),
        "demand_lpd": round(result["results"]["daily_water_demand_l_per_day"], 2),
        "demand_lpm": round(result["results"]["average_flow_lpm"], 2),
        "peak_factor": round(result["results"]["peak_factor"], 2),
        "peak_demand_lpm": round(result["results"]["peak_flow_lpm"], 2),
    }


def fixture_units(fixture_type: str, quantity: int) -> Dict[str, Any]:
    result = uae_fixture_units(fixture_type=fixture_type, quantity=quantity)
    return {
        "fixture_type": fixture_type,
        "quantity": int(_positive(quantity, "Quantity")),
        "fixture_unit_per_item": round(result["results"]["fixture_unit_per_item"], 2),
        "total_fixture_units": round(result["results"]["total_fixture_units"], 2),
    }


def pipe_size(flow_rate_lpm: float, velocity: float, service: str = "Cold", pipe_material: str = "PVC") -> Dict[str, Any]:
    result = uae_pipe_size(flow_rate_lpm=flow_rate_lpm, velocity_m_s=velocity, service=service, pipe_material=pipe_material)
    return {
        "flow_rate_lpm": round(result["results"]["flow_rate_lpm"], 3),
        "velocity_mps": round(result["results"]["velocity_m_s"], 3),
        "diameter_mm": round(result["results"]["required_diameter_mm"], 2),
        "recommended_nominal_size": f"{result['results']['recommended_nominal_size_mm']} mm",
    }


def calculate_pipe_velocity(flow_rate_lpm: float, diameter_mm: float) -> Dict[str, Any]:
    flow_rate_value = _flow(flow_rate_lpm, "Flow rate")
    diameter_value = _pipe_size(diameter_mm, "Diameter")
    velocity = _pipe_velocity_from_flow(flow_rate_value, diameter_value)
    return {
        "flow_rate_lpm": round(flow_rate_value, 2),
        "diameter_mm": round(diameter_value, 2),
        "velocity_m_s": round(velocity, 3),
    }


def calculate_pipe_friction_loss(flow_rate_lpm: float, diameter_mm: float, length_m: float, hazen_williams_c: float = 120.0) -> Dict[str, Any]:
    flow_rate_value = _flow(flow_rate_lpm, "Flow rate")
    diameter_value = _pipe_size(diameter_mm, "Diameter")
    length_value = _positive(length_m, "Length")
    c_value = _positive(hazen_williams_c, "Hazen-Williams C")
    head_loss_m = _hazen_williams_head_loss_m(flow_rate_value, diameter_value, length_value, c_value)
    pressure_loss_kpa = head_loss_m * 9.81
    return {
        "flow_rate_lpm": round(flow_rate_value, 2),
        "diameter_mm": round(diameter_value, 2),
        "length_m": round(length_value, 2),
        "hazen_williams_c": round(c_value, 2),
        "head_loss_m": round(head_loss_m, 3),
        "pressure_loss_kpa": round(pressure_loss_kpa, 2),
    }


def drainage_pipe(fixture_units: float, slope_percent: float) -> Dict[str, Any]:
    result = uae_drainage_pipe(fixture_units=fixture_units, slope_percent=slope_percent)
    return {
        "fixture_units": round(result["results"]["fixture_units"], 2),
        "slope_percent": round(result["results"]["slope_percent"], 2),
        "recommended_pipe_mm": result["results"]["recommended_pipe_mm"],
        "estimated_flow_lps": round(result["results"]["estimated_flow_lps"], 2),
    }


def rainwater(area: float, rainfall: float, runoff: float = 0.9) -> Dict[str, Any]:
    result = uae_rainwater_pipe(roof_area_m2=area, rainfall_intensity_mm_h=rainfall, runoff_coeff=runoff)
    return {
        "roof_area_m2": round(result["results"]["roof_area_m2"], 2),
        "rainfall_mm_hr": round(result["results"]["rainfall_intensity_mm_h"], 2),
        "runoff_coefficient": round(result["results"]["runoff_coefficient"], 2),
        "flow_lps": round(result["results"]["discharge_l_s"], 3),
    }


def water_tank(occupancy: int, storage_days: float = 1.0, liters_per_person: float = 135.0) -> Dict[str, Any]:
    if liters_per_person <= 0.0:
        raise UAEPlumbingError("Liters per person must be greater than zero.")
    occupancy_value = int(_positive(occupancy, "Occupancy"))
    storage_days_value = _positive(storage_days, "Storage days")
    liters_per_person_value = _positive(liters_per_person, "Liters per person")
    capacity_liters = occupancy_value * liters_per_person_value * storage_days_value
    return {
        "occupancy": occupancy_value,
        "storage_days": round(storage_days_value, 2),
        "liters_per_person": round(liters_per_person_value, 2),
        "required_capacity_liters": round(capacity_liters, 2),
        "required_capacity_m3": round(capacity_liters / 1000.0, 2),
    }


def sump_capacity(daily_demand: float, storage_days: float = 2.0) -> Dict[str, Any]:
    daily_demand_value = _positive(daily_demand, "Daily demand")
    storage_days_value = _positive(storage_days, "Storage days")
    total = daily_demand_value * storage_days_value
    return {
        "daily_demand_liters": round(daily_demand_value, 2),
        "storage_days": round(storage_days_value, 2),
        "sump_capacity_liters": round(total, 2),
        "sump_capacity_m3": round(total / 1000.0, 2),
    }


def pump_power(flow_lps: float, total_head: float, efficiency: float) -> Dict[str, Any]:
    result = uae_pump_power(flow_lps=flow_lps, total_head_m=total_head, efficiency_percent=efficiency)
    return {
        "flow_lps": round(result["results"]["flow_lps"], 3),
        "total_head_m": round(result["results"]["total_head_m"], 2),
        "efficiency": round(result["results"]["efficiency_percent"], 1),
        "hydraulic_power_kw": round(result["results"]["hydraulic_power_kw"], 3),
        "motor_power_kw": round(result["results"]["motor_power_kw"], 3),
        "motor_power_hp": round(result["results"]["motor_power_hp"], 3),
    }


def calculate_booster_pump(flow_lps: float, required_pressure_kpa: float, inlet_pressure_kpa: float = 200.0, efficiency_percent: float = DEFAULT_PUMP_EFFICIENCY) -> Dict[str, Any]:
    flow_value = _flow(flow_lps, "Flow")
    required_pressure_value = _pressure(required_pressure_kpa, "Required pressure")
    inlet_pressure_value = _pressure(inlet_pressure_kpa, "Inlet pressure")
    efficiency_value = _percentage(efficiency_percent, "Efficiency")
    pressure_gain_kpa = max(required_pressure_value - inlet_pressure_value, 0.0)
    total_head_m = pressure_gain_kpa / 9.81
    flow_m3_s = flow_value / 1000.0
    hydraulic_kw = 9.81 * flow_m3_s * total_head_m
    motor_kw = hydraulic_kw / (efficiency_value / 100.0)
    return {
        "flow_lps": round(flow_value, 3),
        "required_pressure_kpa": round(required_pressure_value, 2),
        "inlet_pressure_kpa": round(inlet_pressure_value, 2),
        "pressure_gain_kpa": round(pressure_gain_kpa, 2),
        "total_head_m": round(total_head_m, 3),
        "efficiency": round(efficiency_value, 2),
        "hydraulic_power_kw": round(hydraulic_kw, 3),
        "motor_power_kw": round(motor_kw, 3),
    }


def calculate_transfer_pump(flow_lps: float, lift_m: float, friction_loss_m: float = 2.0, efficiency_percent: float = DEFAULT_PUMP_EFFICIENCY) -> Dict[str, Any]:
    flow_value = _flow(flow_lps, "Flow")
    lift_value = _positive(lift_m, "Lift")
    friction_loss_value = _non_negative(friction_loss_m, "Friction loss")
    efficiency_value = _percentage(efficiency_percent, "Efficiency")
    total_head_m = lift_value + friction_loss_value
    flow_m3_s = flow_value / 1000.0
    hydraulic_kw = 9.81 * flow_m3_s * total_head_m
    motor_kw = hydraulic_kw / (efficiency_value / 100.0)
    return {
        "flow_lps": round(flow_value, 3),
        "lift_m": round(lift_value, 2),
        "friction_loss_m": round(friction_loss_value, 2),
        "total_head_m": round(total_head_m, 3),
        "efficiency": round(efficiency_value, 2),
        "hydraulic_power_kw": round(hydraulic_kw, 3),
        "motor_power_kw": round(motor_kw, 3),
    }


def calculate_domestic_pump(flow_lps: float, required_residual_pressure_kpa: float, elevation_m: float = 10.0, efficiency_percent: float = DEFAULT_PUMP_EFFICIENCY) -> Dict[str, Any]:
    flow_value = _flow(flow_lps, "Flow")
    required_residual_pressure_value = _pressure(required_residual_pressure_kpa, "Residual pressure")
    elevation_value = _positive(elevation_m, "Elevation")
    efficiency_value = _percentage(efficiency_percent, "Efficiency")
    pressure_head_m = required_residual_pressure_value / 9.81
    total_head_m = pressure_head_m + elevation_value
    flow_m3_s = flow_value / 1000.0
    hydraulic_kw = 9.81 * flow_m3_s * total_head_m
    motor_kw = hydraulic_kw / (efficiency_value / 100.0)
    return {
        "flow_lps": round(flow_value, 3),
        "required_residual_pressure_kpa": round(required_residual_pressure_value, 2),
        "elevation_m": round(elevation_value, 2),
        "total_head_m": round(total_head_m, 3),
        "efficiency": round(efficiency_value, 2),
        "hydraulic_power_kw": round(hydraulic_kw, 3),
        "motor_power_kw": round(motor_kw, 3),
    }


def calculate_hydrotest_pressure(operating_pressure_kpa: float, test_factor: float = 1.5) -> Dict[str, Any]:
    operating_pressure_value = _pressure(operating_pressure_kpa, "Operating pressure")
    test_factor_value = _positive(test_factor, "Test factor")
    test_pressure_kpa = operating_pressure_value * test_factor_value
    test_head_m = test_pressure_kpa / 9.81
    return {
        "operating_pressure_kpa": round(operating_pressure_value, 2),
        "test_factor": round(test_factor_value, 2),
        "test_pressure_kpa": round(test_pressure_kpa, 2),
        "test_head_m": round(test_head_m, 3),
    }


def calculate_expansion_tank(
    system_volume_l: float,
    temp_rise_c: float,
    expansion_coefficient: float = 0.000214,
    safety_factor: float = 1.2,
    precharge_pressure_kpa: float = 200.0,
) -> Dict[str, Any]:
    system_volume_value = _positive(system_volume_l, "System volume")
    temp_rise_value = _positive(temp_rise_c, "Temperature rise")
    expansion_coefficient_value = _positive(expansion_coefficient, "Expansion coefficient")
    safety_factor_value = _positive(safety_factor, "Safety factor")
    precharge_pressure_value = _positive(precharge_pressure_kpa, "Precharge pressure")

    expansion_volume_l = (
        system_volume_value
        * expansion_coefficient_value
        * temp_rise_value
    )

    required_tank_volume_l = (
        expansion_volume_l
        * safety_factor_value
    )

    return {
        "system_volume_l": round(system_volume_value, 2),
        "temp_rise_c": round(temp_rise_value, 2),
        "expansion_coefficient": round(expansion_coefficient_value, 6),
        "safety_factor": round(safety_factor_value, 2),
        "precharge_pressure_kpa": round(precharge_pressure_value, 2),
        "expansion_volume_l": round(expansion_volume_l, 3),
        "required_tank_volume_l": round(required_tank_volume_l, 3),
    }


# ==========================================================
# Backward Compatibility Aliases
# ==========================================================

try:
    calculate_water_demand = water_demand
except NameError:
    pass

try:
    calculate_fixture_units = fixture_units
except NameError:
    pass

try:
    calculate_pipe_size = pipe_size
except NameError:
    pass

try:
    calculate_drainage_pipe = drainage_pipe
except NameError:
    pass

try:
    calculate_rainwater_pipe = rainwater
except NameError:
    pass

try:
    calculate_water_tank_capacity = water_tank
except NameError:
    pass

try:
    calculate_pump_power = pump_power
except NameError:
    pass
calculate_pipe_diameter = pipe_size

try:
    calculate_pipe_diameter = pipe_size
except NameError:
    pass

try:
    calculate_sump_size = sump_capacity
except NameError:
    pass