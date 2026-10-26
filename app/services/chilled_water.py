import math


class ChilledWaterCalculationError(ValueError):
    """Custom exception for UAE chilled water calculator."""
    pass


def _validate_numeric_field(name, value, minimum=None, maximum=None):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise ChilledWaterCalculationError(f"{name} must be numeric.")

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise ChilledWaterCalculationError(f"{name} must be a finite number.")

    if minimum is not None and numeric_value < minimum:
        raise ChilledWaterCalculationError(f"{name} must be greater than or equal to {minimum}.")

    if maximum is not None and numeric_value > maximum:
        raise ChilledWaterCalculationError(f"{name} must be less than or equal to {maximum}.")

    return numeric_value


def _validate(cooling_load_kw, delta_t_c, velocity_m_s):
    values = {
        "Cooling Load kW": cooling_load_kw,
        "Delta T °C": delta_t_c,
        "Pipe Velocity m/s": velocity_m_s,
    }

    converted = {}
    for key, value in values.items():
        if key == "Pipe Velocity m/s":
            converted[key] = _validate_numeric_field(key, value, minimum=0.9, maximum=2.4)
        else:
            converted[key] = _validate_numeric_field(key, value, minimum=0.0001)

    if converted["Cooling Load kW"] <= 0:
        raise ChilledWaterCalculationError("Cooling Load kW must be greater than zero.")

    if converted["Delta T °C"] <= 0:
        raise ChilledWaterCalculationError("Delta T °C must be greater than zero.")

    return converted


def calculate_chilled_water_uae(cooling_load_kw, delta_t_c, velocity_m_s):
    """UAE / ASHRAE chilled water flow and pipe sizing calculator."""
    data = _validate(cooling_load_kw, delta_t_c, velocity_m_s)

    cooling_load_kw = data["Cooling Load kW"]
    delta_t_c = data["Delta T °C"]
    velocity_m_s = data["Pipe Velocity m/s"]

    # Flow rate based on sensible cooling equation
    flow_lps = cooling_load_kw / (4.186 * delta_t_c)
    flow_lpm = flow_lps * 60.0
    flow_m3hr = flow_lps * 3.6
    flow_gpm = flow_lpm / 3.785

    # Pipe sizing from continuity equation Q = V × A
    flow_m3s = flow_lps / 1000.0
    pipe_area_m2 = flow_m3s / velocity_m_s
    diameter_m = math.sqrt((4 * pipe_area_m2) / math.pi)
    diameter_mm = diameter_m * 1000.0

    standard_sizes_mm = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300, 350, 400]
    recommended_pipe_mm = standard_sizes_mm[-1]
    for size_mm in standard_sizes_mm:
        if diameter_mm <= size_mm:
            recommended_pipe_mm = size_mm
            break

    velocity_ok = 0.9 <= velocity_m_s <= 2.4

    remarks = []
    if velocity_ok:
        remarks.append("Pipe velocity is within the recommended UAE chilled water range of 0.9 to 2.4 m/s.")
    else:
        remarks.append("Pipe velocity is outside the preferred UAE chilled water design band; review the pipe sizing and system layout.")

    if diameter_mm > 150:
        remarks.append("The pipe sizing is large; confirm the distribution layout and available service space for the selected diameter.")
    else:
        remarks.append("Pipe diameter is suitable for a typical commercial chilled water distribution design.")

    result = {
        "inputs": {
            "Cooling Load kW": round(cooling_load_kw, 2),
            "Delta T °C": round(delta_t_c, 2),
            "Pipe Velocity m/s": round(velocity_m_s, 2),
        },
        "results": {
            "Flow Rate (L/s)": round(flow_lps, 2),
            "Flow Rate (L/min)": round(flow_lpm, 2),
            "Flow Rate (m³/hr)": round(flow_m3hr, 2),
            "Flow Rate (GPM)": round(flow_gpm, 2),
            "Pipe Area (m²)": round(pipe_area_m2, 6),
            "Calculated Pipe Diameter (mm)": round(diameter_mm, 2),
            "Recommended Pipe Size (mm)": recommended_pipe_mm,
            "Velocity Within UAE Limits": velocity_ok,
        },
        "summary": {
            "Cooling Load": round(cooling_load_kw, 2),
            "Flow Rate": round(flow_lps, 2),
            "Pipe Diameter": round(diameter_mm, 2),
        },
        "remarks": remarks,
        "standards": [
            "ASHRAE Handbook",
            "ASHRAE 90.1",
            "UAE / Abu Dhabi Standards",
            "SMACNA",
        ],
        "calculation_steps": {
            "Flow Rate": "Cooling Load ÷ (4.186 × ΔT)",
            "Pipe Area": "Flow ÷ Velocity",
            "Pipe Diameter": "√((4 × Area) ÷ π)",
            "Recommended Pipe": "Nearest standard pipe size", 
        },
        "cooling_load_kw": round(cooling_load_kw, 2),
        "delta_t_c": round(delta_t_c, 2),
        "velocity_m_s": round(velocity_m_s, 2),
        "flow_lps": round(flow_lps, 2),
        "flow_lpm": round(flow_lpm, 2),
        "flow_m3hr": round(flow_m3hr, 2),
        "flow_gpm": round(flow_gpm, 2),
        "pipe_area_m2": round(pipe_area_m2, 6),
        "pipe_diameter_mm": round(diameter_mm, 2),
        "recommended_pipe_mm": recommended_pipe_mm,
        "velocity_within_uae_limits": velocity_ok,
        "cooling_load": round(cooling_load_kw, 2),
        "delta_t": round(delta_t_c, 2),
        "velocity": round(velocity_m_s, 2),
        "recommended_pipe": recommended_pipe_mm,
    }
    return result


def calculate_chilled_water(cooling_load, delta_t, velocity):
    """Backward-compatible wrapper for the route contract."""
    return calculate_chilled_water_uae(
        cooling_load_kw=cooling_load,
        delta_t_c=delta_t,
        velocity_m_s=velocity,
    )