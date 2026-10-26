import math


class FreshAirCalculationError(ValueError):
    """Custom exception for UAE fresh air calculator."""
    pass


def _validate_numeric_field(name, value, minimum=None):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise FreshAirCalculationError(f"{name} must be numeric.")

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise FreshAirCalculationError(f"{name} must be a finite number.")

    if minimum is not None and numeric_value < minimum:
        raise FreshAirCalculationError(f"{name} cannot be less than {minimum}.")

    return numeric_value


def _validate(occupants, area, fresh_air_per_person, fresh_air_per_area):
    fields = {
        "Occupants": occupants,
        "Room Area": area,
        "Fresh Air Per Person": fresh_air_per_person,
        "Fresh Air Per Area": fresh_air_per_area,
    }

    values = {}
    for key, value in fields.items():
        if key == "Occupants":
            values[key] = _validate_numeric_field(key, value, minimum=0)
        else:
            values[key] = _validate_numeric_field(key, value, minimum=0)

    if values["Occupants"] < 0:
        raise FreshAirCalculationError("Occupants cannot be negative.")

    if values["Room Area"] <= 0:
        raise FreshAirCalculationError("Room Area must be greater than zero.")

    if values["Fresh Air Per Person"] < 0:
        raise FreshAirCalculationError("Fresh Air Per Person cannot be negative.")

    if values["Fresh Air Per Area"] < 0:
        raise FreshAirCalculationError("Fresh Air Per Area cannot be negative.")

    return values


def calculate_fresh_air_uae(occupants, area, fresh_air_per_person, fresh_air_per_area):
    """UAE / GCC ASHRAE ventilation calculator for occupancy and area-based outside air."""
    data = _validate(occupants, area, fresh_air_per_person, fresh_air_per_area)

    occupants = data["Occupants"]
    area = data["Room Area"]
    fresh_air_per_person = data["Fresh Air Per Person"]
    fresh_air_per_area = data["Fresh Air Per Area"]

    people_air = occupants * fresh_air_per_person
    area_air = area * fresh_air_per_area
    total_cfm = people_air + area_air
    total_lps = total_cfm * 0.4719
    total_cmh = total_cfm * 1.699
    total_cms = total_cmh / 3600

    remarks = []
    if total_cfm < 50:
        remarks.append("Fresh air quantity is modest; confirm the selected design values with the project ventilation schedule.")
    elif total_cfm > 2000:
        remarks.append("Fresh air quantity is significant; verify air handling unit sizing against the final design load and local authority review.")
    else:
        remarks.append("Fresh air provision is within a normal range for commercial comfort ventilation design.")

    result = {
        "inputs": {
            "Occupants": int(occupants),
            "Room Area (m²)": round(area, 2),
            "Fresh Air Per Person (CFM/person)": round(fresh_air_per_person, 2),
            "Fresh Air Per Area (CFM/m²)": round(fresh_air_per_area, 2),
        },
        "results": {
            "Occupancy Fresh Air (CFM)": round(people_air, 2),
            "Area Fresh Air (CFM)": round(area_air, 2),
            "Total Fresh Air (CFM)": round(total_cfm, 2),
            "Total Fresh Air (L/s)": round(total_lps, 2),
            "Total Fresh Air (CMH)": round(total_cmh, 2),
            "Total Fresh Air (CMS)": round(total_cms, 3),
            "Recommended FA Unit": math.ceil(total_cfm / 2000),
        },
        "summary": {
            "Occupants": int(occupants),
            "Room Area": round(area, 2),
            "Total Fresh Air": round(total_cfm, 2),
        },
        "remarks": remarks,
        "standards": [
            "ASHRAE 62.1",
            "ASHRAE Fundamentals",
            "SMACNA HVAC Design Guide",
            "UAE / GCC Ventilation Practice",
            "Local Authority Review",
        ],
        "calculation_steps": {
            "Occupancy Air": "Occupants × Fresh Air Per Person",
            "Area Air": "Area × Fresh Air Per Area",
            "Total Fresh Air": "Occupancy Air + Area Air",
        },
        "occupants": int(occupants),
        "room_area": round(area, 2),
        "people_air": round(people_air, 2),
        "area_air": round(area_air, 2),
        "total_cfm": round(total_cfm, 2),
        "total_lps": round(total_lps, 2),
        "total_cmh": round(total_cmh, 2),
        "total_cms": round(total_cms, 3),
        "recommended_fa_unit": math.ceil(total_cfm / 2000),
    }

    return result


def calculate_fresh_air(occupants, area, fresh_air_per_person, fresh_air_per_area):
    """Backward-compatible wrapper for the route contract."""
    return calculate_fresh_air_uae(
        occupants=occupants,
        area=area,
        fresh_air_per_person=fresh_air_per_person,
        fresh_air_per_area=fresh_air_per_area,
    )