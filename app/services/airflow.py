import math


class AirFlowCalculationError(ValueError):
    """Custom exception for Air Flow Calculator."""
    pass


def _validate_numeric_field(name, value, allow_zero=False, minimum=None, maximum=None):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise AirFlowCalculationError(f"{name} must be numeric.")

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise AirFlowCalculationError(f"{name} must be a finite number.")

    if minimum is not None and numeric_value < minimum:
        raise AirFlowCalculationError(f"{name} must be greater than or equal to {minimum}.")

    if maximum is not None and numeric_value > maximum:
        raise AirFlowCalculationError(f"{name} must be less than or equal to {maximum}.")

    if allow_zero:
        if numeric_value < 0:
            raise AirFlowCalculationError(f"{name} cannot be negative.")
    elif numeric_value <= 0:
        raise AirFlowCalculationError(f"{name} must be greater than zero.")

    return numeric_value


def _validate(length_m, width_m, height_m, air_changes_per_hour, min_fresh_air_cfm=0.0, diffuser_capacity_cfm=400.0):
    fields = {
        "Room Length": length_m,
        "Room Width": width_m,
        "Room Height": height_m,
        "Air Changes per Hour": air_changes_per_hour,
        "Minimum Fresh Air CFM": min_fresh_air_cfm,
        "Diffuser Capacity CFM": diffuser_capacity_cfm,
    }

    converted = {}
    for key, value in fields.items():
        if key in {"Minimum Fresh Air CFM", "Diffuser Capacity CFM"}:
            converted[key] = _validate_numeric_field(key, value, allow_zero=True, minimum=0)
        else:
            converted[key] = _validate_numeric_field(key, value, allow_zero=False, minimum=0.0001)

    if converted["Air Changes per Hour"] > 30:
        raise AirFlowCalculationError("Air Changes per Hour is unusually high for a standard comfort ventilation design.")

    if converted["Diffuser Capacity CFM"] <= 0:
        raise AirFlowCalculationError("Diffuser Capacity CFM must be greater than zero.")

    return converted


def calculate_airflow_uae(
    length_m,
    width_m,
    height_m,
    air_changes_per_hour,
    min_fresh_air_cfm=0.0,
    diffuser_capacity_cfm=400.0,
):
    """UAE / ASHRAE 62.1 compliant airflow calculator."""
    data = _validate(
        length_m,
        width_m,
        height_m,
        air_changes_per_hour,
        min_fresh_air_cfm,
        diffuser_capacity_cfm,
    )

    length_m = data["Room Length"]
    width_m = data["Room Width"]
    height_m = data["Room Height"]
    ach = data["Air Changes per Hour"]
    min_fresh_air = data["Minimum Fresh Air CFM"]
    diffuser_capacity = data["Diffuser Capacity CFM"]

    # Step 1: Room geometry
    room_area_m2 = length_m * width_m
    room_volume_m3 = room_area_m2 * height_m

    # Step 2: Ventilation airflow based on ACH
    airflow_cmh = room_volume_m3 * ach
    airflow_cms = airflow_cmh / 3600.0
    airflow_cfm = airflow_cmh * 0.58858
    airflow_lps = airflow_cms * 1000.0

    # Step 3: Minimum fresh air override
    airflow_cfm_final = max(airflow_cfm, min_fresh_air)

    # Step 4: Recommended diffuser count
    recommended_diffusers = math.ceil(airflow_cfm_final / diffuser_capacity) if diffuser_capacity > 0 else 0

    remarks = []
    if ach > 12:
        remarks.append("Air change rate is high; verify the ventilation strategy against the design occupant load and space use.")
    elif ach < 4:
        remarks.append("Air change rate is low; confirm this meets minimum ventilation and comfort requirements.")
    else:
        remarks.append("Air change rate is within a normal comfort ventilation range for standard HVAC design.")

    if min_fresh_air > airflow_cfm:
        remarks.append("Minimum fresh air requirement governs the final design airflow.")
    else:
        remarks.append("Room ACH airflow governs the final ventilation requirement.")

    if recommended_diffusers > 4:
        remarks.append("Multiple diffusers are required; review grille layout and airflow balancing.")
    else:
        remarks.append("The diffuser count is reasonable for the selected room size and ventilation rate.")

    result = {
        "inputs": {
            "Room Length (m)": round(length_m, 2),
            "Room Width (m)": round(width_m, 2),
            "Room Height (m)": round(height_m, 2),
            "Air Changes per Hour (ACH)": round(ach, 2),
            "Minimum Fresh Air CFM": round(min_fresh_air, 2),
            "Diffuser Capacity CFM": round(diffuser_capacity, 2),
        },
        "results": {
            "Room Area (m²)": round(room_area_m2, 2),
            "Room Volume (m³)": round(room_volume_m3, 2),
            "Airflow (CMH)": round(airflow_cmh, 2),
            "Airflow (CMS)": round(airflow_cms, 3),
            "Airflow (CFM)": round(airflow_cfm, 2),
            "Airflow (L/s)": round(airflow_lps, 2),
            "Final Required Airflow (CFM)": round(airflow_cfm_final, 2),
            "Recommended Diffusers": recommended_diffusers,
        },
        "summary": {
            "Room Area": round(room_area_m2, 2),
            "Room Volume": round(room_volume_m3, 2),
            "Required Airflow": round(airflow_cfm_final, 2),
        },
        "remarks": remarks,
        "standards": [
            "ASHRAE Fundamentals",
            "ASHRAE 62.1",
            "SMACNA",
            "UAE Fire Code",
            "Abu Dhabi Code",
        ],
        "calculation_steps": {
            "Room Area": "Length × Width",
            "Room Volume": "Area × Height",
            "Airflow (CMH)": "Volume × ACH",
            "Airflow (CFM)": "CMH × 0.58858",
            "Recommended Diffusers": "Required Airflow ÷ Diffuser Capacity",
        },
        "room_area": round(room_area_m2, 2),
        "room_volume": round(room_volume_m3, 2),
        "air_changes": round(ach, 2),
        "airflow_cmh": round(airflow_cmh, 2),
        "airflow_cms": round(airflow_cms, 3),
        "airflow_cfm": round(airflow_cfm, 2),
        "airflow_lps": round(airflow_lps, 2),
        "recommended_diffusers": recommended_diffusers,
        "minimum_fresh_air_cfm": round(min_fresh_air, 2),
        "diffuser_capacity_cfm": round(diffuser_capacity, 2),
    }

    return result


def calculate_airflow(
    length,
    width,
    height,
    air_changes,
    min_fresh_air_cfm=0.0,
    diffuser_capacity_cfm=400.0,
):
    """Backward-compatible wrapper for the existing route contract."""
    return calculate_airflow_uae(
        length_m=length,
        width_m=width,
        height_m=height,
        air_changes_per_hour=air_changes,
        min_fresh_air_cfm=min_fresh_air_cfm,
        diffuser_capacity_cfm=diffuser_capacity_cfm,
    )