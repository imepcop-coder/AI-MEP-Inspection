"""Production-grade fire fighting calculators for UAE / NFPA design workflows.

This module preserves the existing calculator entry points while returning a
consistent engineering response envelope across the application.
"""

import math
from typing import Any


GRAVITY_M_S2 = 9.81
BAR_TO_KPA = 100.0
BAR_TO_HEAD_M = 10.2
LPM_TO_GPM = 3.785411784
M_TO_FT = 3.280839895
KPA_TO_PSI = 0.1450377377
L_TO_GAL = 0.264172052
M3_TO_GAL = 264.172052

SPRINKLER_DENSITY_LPM_M2 = {
    "Light": 4.1,
    "Ordinary I": 6.1,
    "Ordinary II": 8.1,
    "Extra I": 10.2,
    "Extra II": 12.2,
}

SPRINKLER_DESIGN_AREA_M2 = {
    "Light": 139.0,
    "Ordinary I": 186.0,
    "Ordinary II": 279.0,
    "Extra I": 279.0,
    "Extra II": 372.0,
}

HAZARD_FLOW_DENSITY = {
    "Light": 0.1,
    "Ordinary": 0.15,
    "Extra": 0.2,
    "High": 0.25,
}

STANDARD_PIPE_SIZES = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300]


class FireCalculationError(Exception):
    """Base exception for fire-related calculator validation failures."""


class UAEFireCalcError(FireCalculationError):
    """Custom exception for UAE Fire & Life Safety Code based calculators."""


def _positive(value: Any, name: str) -> float:
    """Validate that a numeric input is strictly greater than zero."""
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise FireCalculationError(f"{name} must be numeric.") from exc
    if converted <= 0:
        raise FireCalculationError(f"{name} must be greater than zero.")
    return converted


def _non_negative(value: Any, name: str) -> float:
    """Validate that a numeric input is zero or greater."""
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise FireCalculationError(f"{name} must be numeric.") from exc
    if converted < 0:
        raise FireCalculationError(f"{name} must be greater than or equal to zero.")
    return converted


def _percentage(value: Any, name: str) -> float:
    """Validate that a percentage lies between 0 and 100 inclusive."""
    converted = _non_negative(value, name)
    if converted > 100.0:
        raise FireCalculationError(f"{name} must be between 0 and 100.")
    return converted


def _pressure(value: Any, name: str) -> float:
    """Validate that a pressure input is greater than zero."""
    return _positive(value, name)


def _flow(value: Any, name: str) -> float:
    """Validate that a flow input is greater than zero."""
    return _positive(value, name)


def validate_positive(value: Any, name: str) -> float:
    """Backward-compatible validator used by existing calculator entry points."""
    return _positive(value, name)


def _round_value(value: Any, digits: int = 2) -> Any:
    """Round numeric values consistently for engineering output."""
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def _convert_bar_to_head_m(pressure_bar: float) -> float:
    """Convert pressure in bar to equivalent water head in metres."""
    return pressure_bar * BAR_TO_HEAD_M


def _build_response(
    *,
    inputs: dict[str, Any],
    results: dict[str, Any],
    summary: dict[str, Any],
    remarks: list[str] | None = None,
    standards: list[str] | None = None,
    calculation_steps: dict[str, str] | None = None,
    legacy_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the common response envelope used throughout the service."""
    response: dict[str, Any] = {
        "inputs": inputs,
        "results": results,
        "summary": summary,
        "remarks": remarks or [],
        "standards": standards or [],
        "calculation_steps": calculation_steps or {},
    }
    if legacy_results:
        response.update(legacy_results)
    return response


def _build_remarks(*conditions: tuple[bool, str]) -> list[str]:
    """Create a dynamic remark list from condition/value pairs."""
    return [remark for condition, remark in conditions if condition]


# ----------------------------------------------------------------------
# 1. Sprinkler design (NFPA 13 / UAE Civil Defence style)
# ----------------------------------------------------------------------

def uae_sprinkler_demand(hazard_class: str, k_factor_lpm_bar: float = 80.0, min_pressure_bar: float = 1.4) -> dict[str, Any]:
    """Calculate sprinkler demand using UAE / NFPA style design assumptions."""
    if hazard_class not in SPRINKLER_DENSITY_LPM_M2:
        raise UAEFireCalcError("Unsupported hazard class for sprinklers.")

    # Step 1: Select the hazard-specific density and design area from the design table.
    density_lpm_m2 = SPRINKLER_DENSITY_LPM_M2[hazard_class]
    area_m2 = SPRINKLER_DESIGN_AREA_M2[hazard_class]

    # Step 2: Compute the total sprinkler flow using density × design area.
    total_flow_lpm = density_lpm_m2 * area_m2

    # Step 3: Convert the minimum operating pressure to water head.
    min_pressure_bar = _pressure(min_pressure_bar, "Minimum pressure")
    k_factor_lpm_bar = _positive(k_factor_lpm_bar, "K-factor")
    head_m = _convert_bar_to_head_m(min_pressure_bar)

    # Step 4: Estimate the number of sprinklers based on an approximate 12 m² per sprinkler.
    sprinklers = math.ceil(area_m2 / 12.0)

    # Step 5: Convert the key values to imperial units for reporting.
    total_flow_gpm = total_flow_lpm / LPM_TO_GPM
    head_ft = head_m / M_TO_FT
    pressure_psi = min_pressure_bar * 14.5037738

    inputs = {
        "hazard_class": hazard_class,
        "k_factor_lpm_bar": _round_value(k_factor_lpm_bar, 1),
        "min_pressure_bar": _round_value(min_pressure_bar, 2),
    }
    results = {
        "design_area_m2": _round_value(area_m2, 2),
        "design_area_ft2": _round_value(area_m2 * 10.7639104, 2),
        "density_lpm_m2": _round_value(density_lpm_m2, 2),
        "density_gpm_ft2": _round_value(density_lpm_m2 / 40.746, 3),
        "total_flow_lpm": _round_value(total_flow_lpm, 2),
        "total_flow_gpm": _round_value(total_flow_gpm, 2),
        "min_sprinkler_pressure_bar": _round_value(min_pressure_bar, 2),
        "min_sprinkler_pressure_psi": _round_value(pressure_psi, 2),
        "min_sprinkler_head_m": _round_value(head_m, 2),
        "min_sprinkler_head_ft": _round_value(head_ft, 2),
        "approx_sprinkler_count": sprinklers,
        "k_factor_lpm_bar": _round_value(k_factor_lpm_bar, 1),
    }
    summary = {
        "Required Sprinkler Flow": _round_value(total_flow_lpm, 2),
        "Minimum Sprinkler Head": _round_value(head_m, 2),
        "Approximate Sprinkler Count": sprinklers,
    }
    remarks = _build_remarks(
        (hazard_class in {"Extra I", "Extra II"}, "High hazard occupancy; verify sprinkler hazard classification with the authority."),
        (total_flow_lpm > 3000.0, "Sprinkler flow requirement is high; confirm demand with the fire protection consultant."),
    )
    standards = [
        "NFPA 13",
        "UAE Fire & Life Safety Code",
        "Dubai Civil Defence",
        "Abu Dhabi Civil Defence",
    ]
    calculation_steps = {
        "Sprinkler Flow": "Density × Design Area",
        "Sprinkler Head": "Pressure × 10.2 m/bar",
        "Sprinkler Count": "Design Area ÷ 12 m² per sprinkler",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 2. Hose reel demand (UAE Civil Defence typical)
# ----------------------------------------------------------------------

def uae_hose_reel_demand(number_of_reels: int, flow_per_reel_lpm: float = 100.0, min_pressure_bar: float = 6.0) -> dict[str, Any]:
    """Calculate hose reel demand using a simplified UAE Civil Defence design basis."""
    # Step 1: Validate the number of hose reels and individual flow demand.
    reels = int(_positive(number_of_reels, "Number of hose reels"))
    flow_per_reel_lpm = _flow(flow_per_reel_lpm, "Flow per reel")
    min_pressure_bar = _pressure(min_pressure_bar, "Minimum pressure")

    # Step 2: Compute the aggregate hose reel flow.
    total_flow_lpm = reels * flow_per_reel_lpm

    # Step 3: Convert the minimum hose reel pressure to equivalent water head.
    head_m = _convert_bar_to_head_m(min_pressure_bar)

    # Step 4: Convert the key values to imperial units for reporting.
    total_flow_gpm = total_flow_lpm / LPM_TO_GPM
    head_ft = head_m / M_TO_FT
    pressure_psi = min_pressure_bar * 14.5037738

    inputs = {
        "number_of_reels": reels,
        "flow_per_reel_lpm": _round_value(flow_per_reel_lpm, 2),
        "min_pressure_bar": _round_value(min_pressure_bar, 2),
    }
    results = {
        "total_flow_lpm": _round_value(total_flow_lpm, 2),
        "total_flow_gpm": _round_value(total_flow_gpm, 2),
        "min_pressure_bar": _round_value(min_pressure_bar, 2),
        "min_pressure_psi": _round_value(pressure_psi, 2),
        "min_head_m": _round_value(head_m, 2),
        "min_head_ft": _round_value(head_ft, 2),
    }
    summary = {
        "Required Hose Reel Flow": _round_value(total_flow_lpm, 2),
        "Minimum Hose Reel Pressure": _round_value(min_pressure_bar, 2),
    }
    remarks = _build_remarks(
        (total_flow_lpm > 1000.0, "Hose reel demand is significant; verify whether concurrent operation is expected."),
        (min_pressure_bar > 6.0, "Operating pressure exceeds the common baseline; confirm with the authority and layout losses."),
    )
    standards = [
        "NFPA 14",
        "UAE Fire & Life Safety Code",
        "Dubai Civil Defence",
        "Abu Dhabi Civil Defence",
    ]
    calculation_steps = {
        "Hose Reel Flow": "Number of Reels × Flow per Reel",
        "Hose Reel Head": "Pressure × 10.2 m/bar",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 3. Hydrant demand (NFPA 24 / UAE Civil Defence typical)
# ----------------------------------------------------------------------

def uae_hydrant_demand(number_of_hydrants: int, flow_per_hydrant_lpm: float = 1900.0, min_pressure_bar: float = 7.0) -> dict[str, Any]:
    """Calculate hydrant demand using a simplified NFPA 24 / UAE Civil Defence basis."""
    # Step 1: Validate the number of hydrants and the design flow per hydrant.
    hydrants = int(_positive(number_of_hydrants, "Number of hydrants"))
    flow_per_hydrant_lpm = _flow(flow_per_hydrant_lpm, "Flow per hydrant")
    min_pressure_bar = _pressure(min_pressure_bar, "Minimum pressure")

    # Step 2: Compute the aggregate hydrant flow demand.
    total_flow_lpm = hydrants * flow_per_hydrant_lpm

    # Step 3: Convert the minimum operating pressure to water head.
    head_m = _convert_bar_to_head_m(min_pressure_bar)

    # Step 4: Convert the key values to imperial units for reporting.
    total_flow_gpm = total_flow_lpm / LPM_TO_GPM
    head_ft = head_m / M_TO_FT
    pressure_psi = min_pressure_bar * 14.5037738

    inputs = {
        "number_of_hydrants": hydrants,
        "flow_per_hydrant_lpm": _round_value(flow_per_hydrant_lpm, 2),
        "min_pressure_bar": _round_value(min_pressure_bar, 2),
    }
    results = {
        "total_flow_lpm": _round_value(total_flow_lpm, 2),
        "total_flow_gpm": _round_value(total_flow_gpm, 2),
        "min_pressure_bar": _round_value(min_pressure_bar, 2),
        "min_pressure_psi": _round_value(pressure_psi, 2),
        "min_head_m": _round_value(head_m, 2),
        "min_head_ft": _round_value(head_ft, 2),
    }
    summary = {
        "Required Hydrant Flow": _round_value(total_flow_lpm, 2),
        "Minimum Hydrant Pressure": _round_value(min_pressure_bar, 2),
    }
    remarks = _build_remarks(
        (total_flow_lpm > 5000.0, "Hydrant demand is high; confirm local authority requirements and network capability."),
        (min_pressure_bar > 7.0, "Hydrant pressure exceeds the baseline; verify pressure zoning and supply availability."),
    )
    standards = [
        "NFPA 24",
        "UAE Fire & Life Safety Code",
        "Dubai Civil Defence",
        "Abu Dhabi Civil Defence",
    ]
    calculation_steps = {
        "Hydrant Flow": "Number of Hydrants × Flow per Hydrant",
        "Hydrant Head": "Pressure × 10.2 m/bar",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 4. Fire pump sizing (NFPA 20 / UAE Civil Defence style)
# ----------------------------------------------------------------------

def uae_fire_pump_sizing(
    sprinkler_flow_lpm: float,
    hose_reel_flow_lpm: float,
    hydrant_flow_lpm: float,
    elevation_m: float,
    residual_pressure_bar: float = 3.5,
    pump_discharge_pressure_bar: float = 7.0,
) -> dict[str, Any]:
    """Size a fire pump using a simplified NFPA 20 / UAE Civil Defence basis."""
    # Step 1: Validate flow and pressure inputs.
    sprinkler_flow_lpm = _flow(sprinkler_flow_lpm, "Sprinkler flow")
    hose_reel_flow_lpm = _flow(hose_reel_flow_lpm, "Hose reel flow")
    hydrant_flow_lpm = _flow(hydrant_flow_lpm, "Hydrant flow")
    elevation_m = _non_negative(elevation_m, "Elevation")
    residual_pressure_bar = _pressure(residual_pressure_bar, "Residual pressure")
    pump_discharge_pressure_bar = _pressure(pump_discharge_pressure_bar, "Pump discharge pressure")

    # Step 2: Sum the dominant fire protection demand flows.
    total_flow_lpm = sprinkler_flow_lpm + hose_reel_flow_lpm + hydrant_flow_lpm

    # Step 3: Convert the residual and discharge pressures to equivalent water heads.
    discharge_head_m = _convert_bar_to_head_m(pump_discharge_pressure_bar)
    residual_head_m = _convert_bar_to_head_m(residual_pressure_bar)

    # Step 4: Add the elevation head to the residual pressure head at the remote point.
    total_head_m = elevation_m + residual_head_m

    # Step 5: Add a friction allowance to account for pipe and fitting losses.
    friction_allowance_m = 20.0
    total_head_with_friction_m = total_head_m + friction_allowance_m

    # Step 6: Derive the NFPA 20 check-point flow and pressure for pump curve review.
    flow_150_lpm = total_flow_lpm * 1.5
    pressure_65_bar = pump_discharge_pressure_bar * 0.65
    pressure_65_head_m = _convert_bar_to_head_m(pressure_65_bar)

    # Step 7: Convert the key values to imperial units for reporting.
    total_flow_gpm = total_flow_lpm / LPM_TO_GPM
    total_head_ft = total_head_with_friction_m / M_TO_FT
    discharge_pressure_psi = pump_discharge_pressure_bar * 14.5037738
    residual_pressure_psi = residual_pressure_bar * 14.5037738

    inputs = {
        "sprinkler_flow_lpm": _round_value(sprinkler_flow_lpm, 2),
        "hose_reel_flow_lpm": _round_value(hose_reel_flow_lpm, 2),
        "hydrant_flow_lpm": _round_value(hydrant_flow_lpm, 2),
        "elevation_m": _round_value(elevation_m, 2),
        "residual_pressure_bar": _round_value(residual_pressure_bar, 2),
        "pump_discharge_pressure_bar": _round_value(pump_discharge_pressure_bar, 2),
    }
    results = {
        "total_flow_lpm": _round_value(total_flow_lpm, 2),
        "total_flow_gpm": _round_value(total_flow_gpm, 2),
        "elevation_m": _round_value(elevation_m, 2),
        "elevation_ft": _round_value(elevation_m * M_TO_FT, 2),
        "residual_pressure_bar": _round_value(residual_pressure_bar, 2),
        "residual_pressure_psi": _round_value(residual_pressure_psi, 2),
        "pump_discharge_pressure_bar": _round_value(pump_discharge_pressure_bar, 2),
        "pump_discharge_pressure_psi": _round_value(discharge_pressure_psi, 2),
        "residual_head_m": _round_value(residual_head_m, 2),
        "discharge_head_m": _round_value(discharge_head_m, 2),
        "friction_allowance_m": _round_value(friction_allowance_m, 2),
        "total_head_with_friction_m": _round_value(total_head_with_friction_m, 2),
        "total_head_with_friction_ft": _round_value(total_head_ft, 2),
        "nfpa20_check_flow_lpm": _round_value(flow_150_lpm, 2),
        "nfpa20_check_pressure_bar": _round_value(pressure_65_bar, 2),
        "nfpa20_check_head_m": _round_value(pressure_65_head_m, 2),
    }
    summary = {
        "Required Pump Flow": _round_value(total_flow_lpm, 2),
        "Required Pump Head": _round_value(total_head_with_friction_m, 2),
    }
    remarks = _build_remarks(
        (total_head_with_friction_m > 120.0, "Pump head exceeds normal building requirements; verify pressure zoning and driver sizing."),
        (pump_discharge_pressure_bar > 7.0, "Discharge pressure is elevated; review the pump curve and downstream equipment limits."),
        (elevation_m > 30.0, "Building elevation is significant; check booster requirements at the upper levels."),
    )
    standards = [
        "NFPA 20",
        "NFPA 13",
        "UAE Fire & Life Safety Code",
        "Dubai Civil Defence",
        "Abu Dhabi Civil Defence",
    ]
    calculation_steps = {
        "Pump Flow": "Sprinkler Flow + Hose Reel Flow + Hydrant Flow",
        "Pump Head": "Elevation + Residual Pressure + Friction Loss",
        "NFPA 20 Check": "150% Flow at 65% Pressure",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 5. Fire water tank sizing (NFPA 22 / UAE Civil Defence style)
# ----------------------------------------------------------------------

def uae_fire_tank_sizing(
    sprinkler_flow_lpm: float,
    sprinkler_duration_min: float,
    hose_reel_flow_lpm: float,
    hose_reel_duration_min: float,
    hydrant_flow_lpm: float,
    hydrant_duration_min: float,
) -> dict[str, Any]:
    """Size a fire water tank using a simplified NFPA 22 / UAE Civil Defence basis."""
    # Step 1: Validate the flow and duration inputs for each demand component.
    sprinkler_flow_lpm = _flow(sprinkler_flow_lpm, "Sprinkler flow")
    sprinkler_duration_min = _positive(sprinkler_duration_min, "Sprinkler duration")
    hose_reel_flow_lpm = _flow(hose_reel_flow_lpm, "Hose reel flow")
    hose_reel_duration_min = _positive(hose_reel_duration_min, "Hose reel duration")
    hydrant_flow_lpm = _flow(hydrant_flow_lpm, "Hydrant flow")
    hydrant_duration_min = _positive(hydrant_duration_min, "Hydrant duration")

    # Step 2: Compute the required water volume for each demand component.
    sprinkler_volume_l = sprinkler_flow_lpm * sprinkler_duration_min
    hose_reel_volume_l = hose_reel_flow_lpm * hose_reel_duration_min
    hydrant_volume_l = hydrant_flow_lpm * hydrant_duration_min

    # Step 3: Sum the component volumes to obtain the total tank capacity.
    total_volume_l = sprinkler_volume_l + hose_reel_volume_l + hydrant_volume_l
    total_volume_m3 = total_volume_l / 1000.0

    # Step 4: Convert the tank volume to imperial units for reporting.
    total_volume_gal = total_volume_l * L_TO_GAL

    inputs = {
        "sprinkler_flow_lpm": _round_value(sprinkler_flow_lpm, 2),
        "sprinkler_duration_min": _round_value(sprinkler_duration_min, 2),
        "hose_reel_flow_lpm": _round_value(hose_reel_flow_lpm, 2),
        "hose_reel_duration_min": _round_value(hose_reel_duration_min, 2),
        "hydrant_flow_lpm": _round_value(hydrant_flow_lpm, 2),
        "hydrant_duration_min": _round_value(hydrant_duration_min, 2),
    }
    results = {
        "sprinkler_volume_l": _round_value(sprinkler_volume_l, 2),
        "sprinkler_volume_gal": _round_value(sprinkler_volume_l * L_TO_GAL, 2),
        "hose_reel_volume_l": _round_value(hose_reel_volume_l, 2),
        "hose_reel_volume_gal": _round_value(hose_reel_volume_l * L_TO_GAL, 2),
        "hydrant_volume_l": _round_value(hydrant_volume_l, 2),
        "hydrant_volume_gal": _round_value(hydrant_volume_l * L_TO_GAL, 2),
        "total_tank_volume_l": _round_value(total_volume_l, 2),
        "total_tank_volume_m3": _round_value(total_volume_m3, 3),
        "total_tank_volume_gal": _round_value(total_volume_gal, 2),
    }
    summary = {
        "Required Tank Capacity": _round_value(total_volume_m3, 3),
        "Required Tank Capacity (L)": _round_value(total_volume_l, 2),
    }
    remarks = _build_remarks(
        (total_volume_m3 > 500.0, "Required tank capacity is large; verify storage footprint and site constraints."),
        (sprinkler_duration_min > 60.0 or hose_reel_duration_min > 60.0 or hydrant_duration_min > 60.0, "Extended duration has a significant effect on tank size; confirm the design basis with the authority."),
    )
    standards = [
        "NFPA 22",
        "UAE Fire & Life Safety Code",
        "Dubai Civil Defence",
        "Abu Dhabi Civil Defence",
    ]
    calculation_steps = {
        "Tank Volume": "Flow × Duration",
        "Total Tank Capacity": "Sprinkler Volume + Hose Reel Volume + Hydrant Volume",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# 6. Standpipe pressure (NFPA 14 / UAE Civil Defence style)
# ----------------------------------------------------------------------

def uae_standpipe_pressure(
    building_height_m: float,
    friction_loss_kpa: float,
    min_landing_valve_pressure_bar: float = 3.5,
) -> dict[str, Any]:
    """Calculate standpipe pressure demand for a building riser system."""
    # Step 1: Validate the building height and friction loss inputs.
    building_height_m = _non_negative(building_height_m, "Building height")
    friction_loss_kpa = _non_negative(friction_loss_kpa, "Friction loss")
    min_landing_valve_pressure_bar = _pressure(min_landing_valve_pressure_bar, "Landing valve pressure")

    # Step 2: Convert the building elevation into equivalent pressure at the base of the riser.
    elevation_pressure_kpa = building_height_m * GRAVITY_M_S2

    # Step 3: Convert the landing valve pressure requirement to kPa.
    landing_valve_pressure_kpa = min_landing_valve_pressure_bar * BAR_TO_KPA

    # Step 4: Add the elevation pressure, overall friction loss, and landing valve requirement.
    required_pressure_kpa = elevation_pressure_kpa + friction_loss_kpa + landing_valve_pressure_kpa
    required_pressure_bar = required_pressure_kpa / BAR_TO_KPA

    # Step 5: Convert the key values to imperial units for reporting.
    required_pressure_psi = required_pressure_kpa * KPA_TO_PSI
    elevation_pressure_psi = elevation_pressure_kpa * KPA_TO_PSI

    inputs = {
        "building_height_m": _round_value(building_height_m, 2),
        "friction_loss_kpa": _round_value(friction_loss_kpa, 2),
        "min_landing_valve_pressure_bar": _round_value(min_landing_valve_pressure_bar, 2),
    }
    results = {
        "building_height_m": _round_value(building_height_m, 2),
        "building_height_ft": _round_value(building_height_m * M_TO_FT, 2),
        "elevation_pressure_kpa": _round_value(elevation_pressure_kpa, 2),
        "elevation_pressure_psi": _round_value(elevation_pressure_psi, 2),
        "friction_loss_kpa": _round_value(friction_loss_kpa, 2),
        "landing_valve_pressure_kpa": _round_value(landing_valve_pressure_kpa, 2),
        "landing_valve_pressure_bar": _round_value(min_landing_valve_pressure_bar, 2),
        "required_pressure_kpa": _round_value(required_pressure_kpa, 2),
        "required_pressure_bar": _round_value(required_pressure_bar, 2),
        "required_pressure_psi": _round_value(required_pressure_psi, 2),
    }
    summary = {
        "Required Standpipe Pressure": _round_value(required_pressure_bar, 2),
        "Required Standpipe Pressure (kPa)": _round_value(required_pressure_kpa, 2),
    }
    remarks = _build_remarks(
        (required_pressure_bar > 10.0, "Standpipe pressure is elevated; confirm zoning, valve selections, and pressure limiting devices."),
        (building_height_m > 50.0, "The building is tall; confirm standpipe pressure management for the upper levels."),
    )
    standards = [
        "NFPA 14",
        "UAE Fire & Life Safety Code",
        "Dubai Civil Defence",
        "Abu Dhabi Civil Defence",
    ]
    calculation_steps = {
        "Elevation Pressure": "Building Height × 9.81 kPa/m",
        "Required Pressure": "Elevation Pressure + Friction Loss + Landing Valve Pressure",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
    )


# ----------------------------------------------------------------------
# Existing fire calculators retained for backward compatibility
# ----------------------------------------------------------------------

def calculate_fire_pump_head(flow_lpm: float, system_pressure_kpa: float, elevation_m: float) -> dict[str, Any]:
    """Calculate a fire pump total head using pressure and elevation components."""
    # Step 1: Validate the flow, pressure, and elevation inputs.
    flow_lpm = _flow(flow_lpm, "Flow")
    system_pressure_kpa = _pressure(system_pressure_kpa, "System pressure")
    elevation_m = _non_negative(elevation_m, "Elevation")

    # Step 2: Convert the system pressure to an equivalent water head.
    head_from_pressure_m = system_pressure_kpa / GRAVITY_M_S2

    # Step 3: Add the elevation and a practical design allowance for losses.
    total_head_m = elevation_m + head_from_pressure_m + 10.0

    inputs = {
        "flow_lpm": _round_value(flow_lpm, 2),
        "system_pressure_kpa": _round_value(system_pressure_kpa, 2),
        "elevation_m": _round_value(elevation_m, 2),
    }
    results = {
        "flow_lpm": _round_value(flow_lpm, 2),
        "flow_gpm": _round_value(flow_lpm / LPM_TO_GPM, 2),
        "system_pressure_kpa": _round_value(system_pressure_kpa, 2),
        "system_pressure_psi": _round_value(system_pressure_kpa * KPA_TO_PSI, 2),
        "elevation_m": _round_value(elevation_m, 2),
        "head_from_pressure_m": _round_value(head_from_pressure_m, 2),
        "head_from_pressure_ft": _round_value(head_from_pressure_m * M_TO_FT, 2),
        "total_head_m": _round_value(total_head_m, 2),
        "total_head_ft": _round_value(total_head_m * M_TO_FT, 2),
    }
    summary = {
        "Required Pump Head": _round_value(total_head_m, 2),
    }
    remarks = _build_remarks(
        (total_head_m > 100.0, "Pump head is high; review pressure zoning and pump selection."),
    )
    standards = ["NFPA 20", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Pump Head": "Elevation + Pressure Head + Design Allowance",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "flow_lpm": _round_value(flow_lpm, 2),
            "system_pressure_kpa": _round_value(system_pressure_kpa, 2),
            "elevation_m": _round_value(elevation_m, 2),
            "head_from_pressure_m": _round_value(head_from_pressure_m, 2),
            "total_head_m": _round_value(total_head_m, 2),
        },
    )


def calculate_fire_flow(area_m2: float, hazard_class: str) -> dict[str, Any]:
    """Calculate fire flow demand from a design area and hazard classification."""
    # Step 1: Validate the design area and confirm the hazard class is supported.
    area_m2 = _flow(area_m2, "Area")
    if hazard_class not in HAZARD_FLOW_DENSITY:
        raise FireCalculationError("Unsupported hazard classification selected.")

    # Step 2: Compute the required fire flow from density × area.
    density_lpm_per_m2 = HAZARD_FLOW_DENSITY[hazard_class]
    total_flow_lpm = area_m2 * density_lpm_per_m2

    inputs = {
        "area_m2": _round_value(area_m2, 2),
        "hazard_class": hazard_class,
    }
    results = {
        "area_m2": _round_value(area_m2, 2),
        "area_ft2": _round_value(area_m2 * 10.7639104, 2),
        "hazard_class": hazard_class,
        "fire_flow_lpm": _round_value(total_flow_lpm, 2),
        "fire_flow_gpm": _round_value(total_flow_lpm / LPM_TO_GPM, 2),
        "density_lpm_per_m2": _round_value(density_lpm_per_m2, 3),
    }
    summary = {
        "Required Fire Flow": _round_value(total_flow_lpm, 2),
    }
    remarks = _build_remarks(
        (total_flow_lpm > 3000.0, "High fire flow requirement; verify the design basis with the authority."),
    )
    standards = ["NFPA 13", "NFPA 24", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Fire Flow": "Density × Design Area",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "area_m2": _round_value(area_m2, 2),
            "hazard_class": hazard_class,
            "fire_flow_lpm": _round_value(total_flow_lpm, 2),
            "density_lpm_per_m2": _round_value(density_lpm_per_m2, 3),
        },
    )


def calculate_fire_water_tank(demand_lpm: float, duration_hours: float) -> dict[str, Any]:
    """Calculate fire water tank storage from demand and duration."""
    # Step 1: Validate the demand and duration values.
    demand_lpm = _flow(demand_lpm, "Demand")
    duration_hours = _positive(duration_hours, "Duration")

    # Step 2: Convert the storage duration to litres using 60 minutes per hour.
    capacity_l = demand_lpm * duration_hours * 60.0

    inputs = {
        "demand_lpm": _round_value(demand_lpm, 2),
        "duration_hours": _round_value(duration_hours, 2),
    }
    results = {
        "demand_lpm": _round_value(demand_lpm, 2),
        "duration_hours": _round_value(duration_hours, 2),
        "tank_capacity_l": _round_value(capacity_l, 2),
        "tank_capacity_m3": _round_value(capacity_l / 1000.0, 3),
        "tank_capacity_gal": _round_value(capacity_l * L_TO_GAL, 2),
    }
    summary = {
        "Required Tank Capacity": _round_value(capacity_l / 1000.0, 3),
    }
    remarks = _build_remarks(
        (capacity_l > 100000.0, "Tank capacity is large; confirm site footprint and construction constraints."),
    )
    standards = ["NFPA 22", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Tank Capacity": "Demand × Duration × 60",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "demand_lpm": _round_value(demand_lpm, 2),
            "duration_hours": _round_value(duration_hours, 2),
            "tank_capacity_l": _round_value(capacity_l, 2),
            "tank_capacity_m3": _round_value(capacity_l / 1000.0, 3),
        },
    )


def calculate_jockey_pump(
    pump_flow_lpm: float,
    system_pressure_kpa: float,
    pressure_margin_kpa: float = 10.0,
    efficiency_percent: float = 70.0,
) -> dict[str, Any]:
    """Estimate a jockey pump duty point from flow, pressure, and efficiency."""
    # Step 1: Validate the pump flow, system pressure, margin, and efficiency inputs.
    pump_flow_lpm = _flow(pump_flow_lpm, "Pump flow")
    system_pressure_kpa = _pressure(system_pressure_kpa, "System pressure")
    pressure_margin_kpa = _pressure(pressure_margin_kpa, "Pressure margin")
    efficiency_percent = _percentage(efficiency_percent, "Efficiency")

    # Step 2: Determine the operating pressure and equivalent head.
    operating_pressure_kpa = system_pressure_kpa + pressure_margin_kpa
    head_m = operating_pressure_kpa / GRAVITY_M_S2

    # Step 3: Convert flow to m³/s and compute hydraulic and motor power.
    flow_m3_s = pump_flow_lpm / 60000.0
    hydraulic_power_kw = (1000.0 * GRAVITY_M_S2 * flow_m3_s * head_m) / 1000.0
    motor_power_kw = hydraulic_power_kw / (efficiency_percent / 100.0)

    inputs = {
        "pump_flow_lpm": _round_value(pump_flow_lpm, 2),
        "system_pressure_kpa": _round_value(system_pressure_kpa, 2),
        "pressure_margin_kpa": _round_value(pressure_margin_kpa, 2),
        "efficiency_percent": _round_value(efficiency_percent, 2),
    }
    results = {
        "pump_flow_lpm": _round_value(pump_flow_lpm, 2),
        "system_pressure_kpa": _round_value(system_pressure_kpa, 2),
        "pressure_margin_kpa": _round_value(pressure_margin_kpa, 2),
        "operating_pressure_kpa": _round_value(operating_pressure_kpa, 2),
        "head_m": _round_value(head_m, 2),
        "hydraulic_power_kw": _round_value(hydraulic_power_kw, 3),
        "motor_power_kw": _round_value(motor_power_kw, 3),
        "efficiency_percent": _round_value(efficiency_percent, 2),
    }
    summary = {
        "Required Pump Power": _round_value(motor_power_kw, 3),
    }
    remarks = _build_remarks(
        (efficiency_percent < 70.0, "Pump efficiency is below the typical design target; review the equipment selection."),
    )
    standards = ["NFPA 20", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Jockey Pump Head": "System Pressure + Pressure Margin",
        "Hydraulic Power": "ρ × g × Q × H",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "pump_flow_lpm": _round_value(pump_flow_lpm, 2),
            "system_pressure_kpa": _round_value(system_pressure_kpa, 2),
            "pressure_margin_kpa": _round_value(pressure_margin_kpa, 2),
            "operating_pressure_kpa": _round_value(operating_pressure_kpa, 2),
            "head_m": _round_value(head_m, 2),
            "hydraulic_power_kw": _round_value(hydraulic_power_kw, 3),
            "motor_power_kw": _round_value(motor_power_kw, 3),
            "efficiency_percent": _round_value(efficiency_percent, 2),
        },
    )


def calculate_fire_pipe_size(flow_rate_lpm: float, velocity_m_s: float) -> dict[str, Any]:
    """Estimate the nominal pipe size for a target flow and velocity."""
    # Step 1: Validate the flow rate and velocity inputs.
    flow_rate_lpm = _flow(flow_rate_lpm, "Flow rate")
    velocity_m_s = _positive(velocity_m_s, "Velocity")

    # Step 2: Convert the flow to m³/s and solve the continuity equation for diameter.
    flow_m3_s = flow_rate_lpm / 60000.0
    diameter_m = math.sqrt((4.0 * flow_m3_s) / (math.pi * velocity_m_s))
    diameter_mm = diameter_m * 1000.0

    # Step 3: Select the next standard pipe size that satisfies the required diameter.
    recommended_size = STANDARD_PIPE_SIZES[-1]
    for size in STANDARD_PIPE_SIZES:
        if size >= diameter_mm:
            recommended_size = size
            break

    inputs = {
        "flow_rate_lpm": _round_value(flow_rate_lpm, 2),
        "velocity_m_s": _round_value(velocity_m_s, 3),
    }
    results = {
        "flow_rate_lpm": _round_value(flow_rate_lpm, 2),
        "flow_rate_gpm": _round_value(flow_rate_lpm / LPM_TO_GPM, 2),
        "velocity_m_s": _round_value(velocity_m_s, 3),
        "pipe_diameter_mm": _round_value(diameter_mm, 2),
        "pipe_diameter_in": _round_value(diameter_mm / 25.4, 2),
        "recommended_nominal_size": f"{recommended_size} mm",
    }
    summary = {
        "Recommended Pipe Size": f"{recommended_size} mm",
    }
    remarks = _build_remarks(
        (velocity_m_s > 4.0, "Velocity is high; verify pressure losses and noise concerns."),
    )
    standards = ["NFPA 13", "NFPA 20", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Pipe Diameter": "sqrt(4Q / πv)",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "flow_rate_lpm": _round_value(flow_rate_lpm, 2),
            "velocity_m_s": _round_value(velocity_m_s, 3),
            "pipe_diameter_mm": _round_value(diameter_mm, 2),
            "recommended_nominal_size": f"{recommended_size} mm",
        },
    )


def calculate_sprinkler_spacing(area_m2: float, efficiency_percent: float) -> dict[str, Any]:
    """Estimate a representative sprinkler spacing from an effective coverage area."""
    # Step 1: Validate the coverage area and sprinkler efficiency percentage.
    area_m2 = _flow(area_m2, "Area")
    efficiency_percent = _percentage(efficiency_percent, "Efficiency")
    if efficiency_percent < 1.0:
        efficiency_percent = 1.0

    # Step 2: Compute the spacing from the square-root relationship between area and spacing.
    spacing_m = math.sqrt(area_m2 * (efficiency_percent / 100.0))

    inputs = {
        "area_m2": _round_value(area_m2, 2),
        "efficiency_percent": _round_value(efficiency_percent, 2),
    }
    results = {
        "sprinkler_spacing_m": _round_value(spacing_m, 2),
        "sprinkler_spacing_ft": _round_value(spacing_m * M_TO_FT, 2),
        "efficiency_percent": _round_value(efficiency_percent, 2),
    }
    summary = {
        "Sprinkler Spacing": _round_value(spacing_m, 2),
    }
    remarks = _build_remarks(
        (efficiency_percent < 70.0, "Coverage efficiency is low; review the sprinkler layout assumptions."),
    )
    standards = ["NFPA 13", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Sprinkler Spacing": "sqrt(Area × Efficiency)",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "sprinkler_spacing_m": _round_value(spacing_m, 2),
            "efficiency_percent": _round_value(efficiency_percent, 2),
        },
    )


def calculate_standpipe_pressure(height_m: float, hose_length_m: float, friction_loss_kpa_per_m: float) -> dict[str, Any]:
    """Calculate a standpipe pressure based on elevation and friction loss."""
    # Step 1: Validate the height, hose length, and friction-loss input.
    height_m = _non_negative(height_m, "Height")
    hose_length_m = _non_negative(hose_length_m, "Hose length")
    friction_loss_kpa_per_m = _positive(friction_loss_kpa_per_m, "Friction loss")

    # Step 2: Convert the building height into equivalent pressure.
    elevation_pressure_kpa = height_m * GRAVITY_M_S2

    # Step 3: Add the hose friction loss and a design allowance.
    hose_loss_kpa = hose_length_m * friction_loss_kpa_per_m
    required_pressure_kpa = elevation_pressure_kpa + hose_loss_kpa + 50.0

    inputs = {
        "height_m": _round_value(height_m, 2),
        "hose_length_m": _round_value(hose_length_m, 2),
        "friction_loss_kpa_per_m": _round_value(friction_loss_kpa_per_m, 2),
    }
    results = {
        "required_pressure_kpa": _round_value(required_pressure_kpa, 2),
        "required_pressure_bar": _round_value(required_pressure_kpa / BAR_TO_KPA, 2),
        "required_pressure_psi": _round_value(required_pressure_kpa * KPA_TO_PSI, 2),
        "elevation_pressure_kpa": _round_value(elevation_pressure_kpa, 2),
        "hose_loss_kpa": _round_value(hose_loss_kpa, 2),
    }
    summary = {
        "Required Pressure": _round_value(required_pressure_kpa, 2),
    }
    remarks = _build_remarks(
        (required_pressure_kpa > 500.0, "Standpipe pressure demand is elevated; review the pressure-control strategy."),
    )
    standards = ["NFPA 14", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Standpipe Pressure": "Elevation Pressure + Hose Loss + Design Allowance",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "required_pressure_kpa": _round_value(required_pressure_kpa, 2),
            "elevation_pressure_kpa": _round_value(elevation_pressure_kpa, 2),
        },
    )


def calculate_hose_reel_pressure(flow_lpm: float, hose_length_m: float, nozzle_pressure_kpa: float) -> dict[str, Any]:
    """Estimate hose reel pressure loss for a given flow and hose length."""
    # Step 1: Validate the flow, hose length, and nozzle pressure inputs.
    flow_lpm = _flow(flow_lpm, "Flow")
    hose_length_m = _non_negative(hose_length_m, "Hose length")
    nozzle_pressure_kpa = _pressure(nozzle_pressure_kpa, "Nozzle pressure")

    # Step 2: Estimate the friction loss and total pressure demand.
    pressure_loss_kpa = (flow_lpm / 100.0) ** 2 * 0.5 + hose_length_m * 0.2
    total_pressure_kpa = pressure_loss_kpa + nozzle_pressure_kpa

    inputs = {
        "flow_lpm": _round_value(flow_lpm, 2),
        "hose_length_m": _round_value(hose_length_m, 2),
        "nozzle_pressure_kpa": _round_value(nozzle_pressure_kpa, 2),
    }
    results = {
        "total_pressure_kpa": _round_value(total_pressure_kpa, 2),
        "total_pressure_bar": _round_value(total_pressure_kpa / BAR_TO_KPA, 2),
        "pressure_loss_kpa": _round_value(pressure_loss_kpa, 2),
    }
    summary = {
        "Required Pressure": _round_value(total_pressure_kpa, 2),
    }
    remarks = _build_remarks(
        (total_pressure_kpa > 600.0, "Pressure demand is high; review hose diameter and pump capability."),
    )
    standards = ["NFPA 14", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Hose Reel Pressure": "Pressure Loss + Nozzle Pressure",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "total_pressure_kpa": _round_value(total_pressure_kpa, 2),
            "pressure_loss_kpa": _round_value(pressure_loss_kpa, 2),
        },
    )


def calculate_nozzle_pressure(flow_lpm: float, nozzle_coefficient: float) -> dict[str, Any]:
    """Estimate nozzle pressure from flow and nozzle discharge coefficient."""
    # Step 1: Validate the flow and nozzle coefficient inputs.
    flow_lpm = _flow(flow_lpm, "Flow")
    nozzle_coefficient = _positive(nozzle_coefficient, "Nozzle coefficient")

    # Step 2: Convert the flow to litres per second and apply the nozzle pressure relation.
    flow_l_s = flow_lpm / 60.0
    required_pressure_kpa = (flow_l_s / nozzle_coefficient) ** 2 * 1000.0

    inputs = {
        "flow_lpm": _round_value(flow_lpm, 2),
        "nozzle_coefficient": _round_value(nozzle_coefficient, 3),
    }
    results = {
        "required_pressure_kpa": _round_value(required_pressure_kpa, 2),
        "required_pressure_bar": _round_value(required_pressure_kpa / BAR_TO_KPA, 2),
        "flow_l_s": _round_value(flow_l_s, 3),
    }
    summary = {
        "Required Pressure": _round_value(required_pressure_kpa, 2),
    }
    remarks = _build_remarks(
        (required_pressure_kpa > 500.0, "Nozzle pressure is high; verify the selected nozzle and upstream supply."),
    )
    standards = ["NFPA 14", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Nozzle Pressure": "(Q / K)² × 1000",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "required_pressure_kpa": _round_value(required_pressure_kpa, 2),
            "flow_l_s": _round_value(flow_l_s, 3),
        },
    )


def calculate_hydraulic_loss(flow_lpm: float, diameter_mm: float, length_m: float, roughness_mm: float) -> dict[str, Any]:
    """Estimate hydraulic pressure loss in a pipe using a Darcy-Weisbach style approach."""
    # Step 1: Validate the hydraulic inputs.
    flow_lpm = _flow(flow_lpm, "Flow")
    diameter_mm = _positive(diameter_mm, "Diameter")
    length_m = _positive(length_m, "Length")
    roughness_mm = _positive(roughness_mm, "Roughness")

    # Step 2: Convert the flow to m³/s and compute the flow velocity.
    q_m3_s = flow_lpm / 60000.0
    d_m = diameter_mm / 1000.0
    area_m2 = math.pi * d_m ** 2 / 4.0
    velocity_m_s = q_m3_s / area_m2

    # Step 3: Estimate the Reynolds number and friction factor.
    reynolds_number = velocity_m_s * d_m / 1e-6
    if reynolds_number < 2000:
        friction_factor = 64.0 / reynolds_number
    else:
        relative_roughness = roughness_mm / 1000.0 / d_m
        friction_factor = 0.25 / (math.log10(relative_roughness / 3.7 + 5.74 / reynolds_number ** 0.9) ** 2)

    # Step 4: Compute the head and pressure losses.
    head_loss_m = friction_factor * (length_m / d_m) * velocity_m_s ** 2 / (2.0 * GRAVITY_M_S2)
    pressure_loss_kpa = head_loss_m * GRAVITY_M_S2

    inputs = {
        "flow_lpm": _round_value(flow_lpm, 2),
        "diameter_mm": _round_value(diameter_mm, 2),
        "length_m": _round_value(length_m, 2),
        "roughness_mm": _round_value(roughness_mm, 2),
    }
    results = {
        "head_loss_m": _round_value(head_loss_m, 3),
        "head_loss_ft": _round_value(head_loss_m * M_TO_FT, 3),
        "pressure_loss_kpa": _round_value(pressure_loss_kpa, 2),
        "pressure_loss_bar": _round_value(pressure_loss_kpa / BAR_TO_KPA, 2),
        "velocity_m_s": _round_value(velocity_m_s, 3),
    }
    summary = {
        "Pressure Loss": _round_value(pressure_loss_kpa, 2),
    }
    remarks = _build_remarks(
        (pressure_loss_kpa > 100.0, "Hydraulic loss is significant; verify pipe sizing and pressure management."),
    )
    standards = ["NFPA 13", "NFPA 20", "UAE Fire & Life Safety Code", "Dubai Civil Defence", "Abu Dhabi Civil Defence"]
    calculation_steps = {
        "Pressure Loss": "Friction Factor × (L/D) × (v² / 2g)",
    }
    return _build_response(
        inputs=inputs,
        results=results,
        summary=summary,
        remarks=remarks,
        standards=standards,
        calculation_steps=calculation_steps,
        legacy_results={
            "head_loss_m": _round_value(head_loss_m, 3),
            "pressure_loss_kpa": _round_value(pressure_loss_kpa, 2),
            "velocity_m_s": _round_value(velocity_m_s, 3),
        },
    )
