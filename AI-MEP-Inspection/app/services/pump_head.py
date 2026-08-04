import math


class PumpHeadCalculationError(ValueError):
    """Custom exception for UAE pump head calculator."""
    pass


def _validate_numeric_field(name, value, minimum=None, maximum=None):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise PumpHeadCalculationError(f"{name} must be numeric.")

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise PumpHeadCalculationError(f"{name} must be a finite number.")

    if minimum is not None and numeric_value < minimum:
        raise PumpHeadCalculationError(f"{name} must be greater than or equal to {minimum}.")

    if maximum is not None and numeric_value > maximum:
        raise PumpHeadCalculationError(f"{name} must be less than or equal to {maximum}.")

    return numeric_value


def _validate(flow_rate, static_head, friction_loss, efficiency):
    fields = {
        "Flow Rate": flow_rate,
        "Static Head": static_head,
        "Friction Loss": friction_loss,
        "Pump Efficiency": efficiency,
    }

    values = {}
    for key, value in fields.items():
        if key == "Pump Efficiency":
            values[key] = _validate_numeric_field(key, value, minimum=1, maximum=100)
        elif key in {"Static Head", "Friction Loss"}:
            values[key] = _validate_numeric_field(key, value, minimum=0)
        else:
            values[key] = _validate_numeric_field(key, value, minimum=0.0001)

    if values["Flow Rate"] <= 0:
        raise PumpHeadCalculationError("Flow Rate must be greater than zero.")

    if values["Static Head"] < 0:
        raise PumpHeadCalculationError("Static Head cannot be negative.")

    if values["Friction Loss"] < 0:
        raise PumpHeadCalculationError("Friction Loss cannot be negative.")

    return values


def calculate_pump_head_uae(flow_rate, static_head, friction_loss, efficiency):
    """UAE / GCC pump head calculation using total dynamic head and hydraulic power method."""
    data = _validate(flow_rate, static_head, friction_loss, efficiency)

    flow_rate = data["Flow Rate"]
    static_head = data["Static Head"]
    friction_loss = data["Friction Loss"]
    efficiency = data["Pump Efficiency"]

    total_head = static_head + friction_loss
    flow_m3s = flow_rate / 3600.0
    hydraulic_power_kw = (1000 * 9.81 * flow_m3s * total_head) / 1000.0
    shaft_power_kw = hydraulic_power_kw / (efficiency / 100.0)
    bhp = shaft_power_kw * 1.341
    recommended_rating_kw = math.ceil(shaft_power_kw)

    remarks = []
    if total_head > 30:
        remarks.append("Total dynamic head is high; verify pump selection against the final hydraulic curve and local authority standards.")
    elif total_head > 15:
        remarks.append("Total dynamic head is moderate; good practice is to confirm duty points and NPSH margin during pump selection.")
    else:
        remarks.append("Total dynamic head is within a normal range for a standard commercial chilled water or water transfer system.")

    result = {
        "inputs": {
            "Flow Rate (m³/hr)": round(flow_rate, 2),
            "Static Head (m)": round(static_head, 2),
            "Friction Loss (m)": round(friction_loss, 2),
            "Pump Efficiency (%)": round(efficiency, 2),
        },
        "results": {
            "Total Dynamic Head (m)": round(total_head, 2),
            "Hydraulic Power (kW)": round(hydraulic_power_kw, 2),
            "Shaft Power (kW)": round(shaft_power_kw, 2),
            "Brake Horsepower (HP)": round(bhp, 2),
            "Recommended Pump Rating (kW)": recommended_rating_kw,
        },
        "summary": {
            "Flow Rate": round(flow_rate, 2),
            "Total Dynamic Head": round(total_head, 2),
            "Recommended Pump Rating": recommended_rating_kw,
        },
        "remarks": remarks,
        "standards": [
            "ASHRAE HVAC Systems and Equipment",
            "ASHRAE Applications Handbook",
            "SMACNA Design Guidance",
            "UAE / GCC Pump Selection Practice",
            "Local Authority Review",
        ],
        "calculation_steps": {
            "Total Dynamic Head": "Static Head + Friction Loss",
            "Hydraulic Power": "ρ × g × Q × H",
            "Pump Shaft Power": "Hydraulic Power ÷ Efficiency",
        },
        "flow_rate": round(flow_rate, 2),
        "static_head": round(static_head, 2),
        "friction_loss": round(friction_loss, 2),
        "total_dynamic_head": round(total_head, 2),
        "hydraulic_power": round(hydraulic_power_kw, 2),
        "shaft_power": round(shaft_power_kw, 2),
        "bhp": round(bhp, 2),
        "efficiency": round(efficiency, 2),
        "recommended_pump_rating": recommended_rating_kw,
    }

    return result


def calculate_pump_head(flow_rate, static_head, friction_loss, efficiency):
    """Backward-compatible wrapper for the route contract."""
    return calculate_pump_head_uae(
        flow_rate=flow_rate,
        static_head=static_head,
        friction_loss=friction_loss,
        efficiency=efficiency,
    )