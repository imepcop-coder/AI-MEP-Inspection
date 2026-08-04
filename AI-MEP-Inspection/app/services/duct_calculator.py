import math


class DuctCalculationError(ValueError):
    """Custom exception for duct calculation errors."""
    pass


def _validate_numeric_field(name, value, minimum=0.0):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise DuctCalculationError(f"{name} must be numeric.")

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise DuctCalculationError(f"{name} must be a finite number.")

    if numeric_value <= minimum:
        raise DuctCalculationError(f"{name} must be greater than zero.")

    return numeric_value


def _validate_inputs(airflow: float, velocity: float):
    """Validate user inputs before performing calculations."""
    airflow = _validate_numeric_field("Airflow", airflow)
    velocity = _validate_numeric_field("Velocity", velocity)

    if airflow > 500000:
        raise DuctCalculationError("Airflow value is unrealistically high.")

    if velocity > 10000:
        raise DuctCalculationError("Velocity value is unrealistically high.")

    return airflow, velocity


def calculate_rectangular_duct(airflow: float, velocity: float):
    """Rectangular duct sizing for UAE / GCC ASHRAE / SMACNA practice."""
    airflow, velocity = _validate_inputs(airflow, velocity)

    area_sqft = airflow / velocity
    area_sqin = area_sqft * 144

    side = math.sqrt(area_sqin)
    width = round(side)
    height = round(area_sqin / width)
    hydraulic_diameter = round((2 * width * height) / (width + height), 2)

    remarks = []
    if velocity > 2500:
        remarks.append("Velocity is elevated; review duct sizing and acoustics in line with SMACNA guidance.")
    elif velocity > 1800:
        remarks.append("Velocity is moderately high; a duct layout review is recommended for comfort and acoustic control.")
    else:
        remarks.append("Velocity is within a normal commercial HVAC range for duct sizing.")

    result = {
        "type": "Rectangular",
        "airflow": airflow,
        "velocity": velocity,
        "area_sqft": round(area_sqft, 3),
        "area_sqin": round(area_sqin, 2),
        "width": width,
        "height": height,
        "hydraulic_diameter": hydraulic_diameter,
        "unit": "inch",
        "inputs": {
            "Air Flow (CFM)": round(airflow, 2),
            "Velocity (FPM)": round(velocity, 1),
        },
        "results": {
            "Duct Area (ft²)": round(area_sqft, 3),
            "Hydraulic Diameter (in)": round(hydraulic_diameter, 2),
            "Width (in)": width,
            "Height (in)": height,
        },
        "summary": {
            "Airflow": round(airflow, 2),
            "Velocity": round(velocity, 1),
            "Duct Area": round(area_sqft, 3),
        },
        "remarks": remarks,
        "standards": [
            "ASHRAE Fundamentals",
            "SMACNA HVAC Duct Design",
            "UAE / GCC Code Practice",
            "Local Authority Design Review",
        ],
        "calculation_steps": {
            "Duct Area": "Airflow ÷ Velocity",
            "Rectangular Duct": "Area converted to equivalent square dimensions",
            "Hydraulic Diameter": "2WH ÷ (W + H)",
        },
    }
    return result


def calculate_round_duct(airflow: float, velocity: float):
    """Round duct sizing for UAE / GCC ASHRAE / SMACNA practice."""
    airflow, velocity = _validate_inputs(airflow, velocity)

    area_sqft = airflow / velocity
    if area_sqft <= 0:
        raise DuctCalculationError("Calculated duct area is invalid.")

    diameter_ft = math.sqrt((4 * area_sqft) / math.pi)
    diameter_in = diameter_ft * 12
    circumference = math.pi * diameter_in

    remarks = []
    if velocity > 2500:
        remarks.append("Velocity is elevated; review duct sizing and acoustics in line with SMACNA guidance.")
    elif velocity > 1800:
        remarks.append("Velocity is moderately high; a duct layout review is recommended for comfort and acoustic control.")
    else:
        remarks.append("Velocity is within a normal commercial HVAC range for duct sizing.")

    result = {
        "type": "Round",
        "airflow": airflow,
        "velocity": velocity,
        "area_sqft": round(area_sqft, 3),
        "diameter": round(diameter_in, 1),
        "circumference": round(circumference, 2),
        "unit": "inch",
        "inputs": {
            "Air Flow (CFM)": round(airflow, 2),
            "Velocity (FPM)": round(velocity, 1),
        },
        "results": {
            "Duct Area (ft²)": round(area_sqft, 3),
            "Diameter (in)": round(diameter_in, 1),
            "Circumference (in)": round(circumference, 2),
        },
        "summary": {
            "Airflow": round(airflow, 2),
            "Velocity": round(velocity, 1),
            "Diameter": round(diameter_in, 1),
        },
        "remarks": remarks,
        "standards": [
            "ASHRAE Fundamentals",
            "SMACNA HVAC Duct Design",
            "UAE / GCC Code Practice",
            "Local Authority Design Review",
        ],
        "calculation_steps": {
            "Duct Area": "Airflow ÷ Velocity",
            "Round Duct Diameter": "√((4 × Area) ÷ π)",
            "Circumference": "π × Diameter",
        },
    }
    return result