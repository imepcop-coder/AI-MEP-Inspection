import math


class StaticPressureCalculationError(ValueError):
    """Custom exception for Static Pressure Calculator."""
    pass


def _validate_numeric_field(name, value, allow_zero=False, minimum=None, maximum=None):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise StaticPressureCalculationError(f"{name} must be numeric.")

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise StaticPressureCalculationError(f"{name} must be a finite number.")

    if minimum is not None and numeric_value < minimum:
        raise StaticPressureCalculationError(f"{name} must be greater than or equal to {minimum}.")

    if maximum is not None and numeric_value > maximum:
        raise StaticPressureCalculationError(f"{name} must be less than or equal to {maximum}.")

    if allow_zero:
        if numeric_value < 0:
            raise StaticPressureCalculationError(f"{name} cannot be negative.")
    elif numeric_value <= 0:
        raise StaticPressureCalculationError(f"{name} must be greater than zero.")

    return numeric_value


def _validate(
    airflow_cfm,
    duct_length_ft,
    friction_rate_inwg_per_100ft,
    velocity_fpm,
    fitting_loss_inwg=0.0,
    coil_loss_inwg=0.0,
    filter_loss_inwg=0.0,
    diffuser_loss_inwg=0.0,
    safety_factor_percent=20.0,
):
    values = {
        "Airflow CFM": airflow_cfm,
        "Duct Length ft": duct_length_ft,
        "Friction Rate in.wg/100ft": friction_rate_inwg_per_100ft,
        "Velocity FPM": velocity_fpm,
        "Fitting Loss in.wg": fitting_loss_inwg,
        "Coil Loss in.wg": coil_loss_inwg,
        "Filter Loss in.wg": filter_loss_inwg,
        "Diffuser Loss in.wg": diffuser_loss_inwg,
        "Safety Factor %": safety_factor_percent,
    }

    converted = {}
    for key, value in values.items():
        if key in {"Fitting Loss in.wg", "Coil Loss in.wg", "Filter Loss in.wg", "Diffuser Loss in.wg"}:
            converted[key] = _validate_numeric_field(key, value, allow_zero=True, minimum=0)
        elif key == "Safety Factor %":
            converted[key] = _validate_numeric_field(key, value, allow_zero=True, minimum=0, maximum=100)
        else:
            converted[key] = _validate_numeric_field(key, value, allow_zero=False, minimum=0.0001)

    if converted["Safety Factor %"] < 5:
        raise StaticPressureCalculationError("Safety Factor % should normally be between 10% and 30%.")

    return converted


def calculate_static_pressure_uae(
    airflow_cfm,
    duct_length_ft,
    friction_rate_inwg_per_100ft,
    velocity_fpm,
    fitting_loss_inwg=0.0,
    coil_loss_inwg=0.0,
    filter_loss_inwg=0.0,
    diffuser_loss_inwg=0.0,
    safety_factor_percent=20.0,
):
    """UAE / ASHRAE / SMACNA static pressure calculator."""
    data = _validate(
        airflow_cfm,
        duct_length_ft,
        friction_rate_inwg_per_100ft,
        velocity_fpm,
        fitting_loss_inwg,
        coil_loss_inwg,
        filter_loss_inwg,
        diffuser_loss_inwg,
        safety_factor_percent,
    )

    airflow_cfm = data["Airflow CFM"]
    duct_length_ft = data["Duct Length ft"]
    friction_rate = data["Friction Rate in.wg/100ft"]
    velocity_fpm = data["Velocity FPM"]
    fitting_loss = data["Fitting Loss in.wg"]
    coil_loss = data["Coil Loss in.wg"]
    filter_loss = data["Filter Loss in.wg"]
    diffuser_loss = data["Diffuser Loss in.wg"]
    safety_factor_percent = data["Safety Factor %"]

    # Step 1: Velocity pressure
    # VP (in.wg) = (V / 4005)^2
    velocity_pressure_inwg = (velocity_fpm / 4005.0) ** 2

    # Step 2: Straight duct friction loss
    # FL = (L / 100) × Friction Rate
    friction_loss_inwg = (duct_length_ft / 100.0) * friction_rate

    # Step 3: Total static pressure
    # TSP = FL + VP + Σ(fittings) + Coil + Filter + Diffuser
    total_static_pressure_inwg = (
        friction_loss_inwg
        + velocity_pressure_inwg
        + fitting_loss
        + coil_loss
        + filter_loss
        + diffuser_loss
    )

    # Step 4: Recommended fan pressure
    # Fan pressure includes design safety margin normally 10–30%
    recommended_fan_pressure_inwg = total_static_pressure_inwg * (1.0 + safety_factor_percent / 100.0)

    remarks = []
    if velocity_fpm > 2500:
        remarks.append("Velocity exceeds the conventional SMACNA recommendation for main ductwork.")
    elif velocity_fpm > 1800:
        remarks.append("Velocity is moderately high; duct sizing should be reviewed for noise and balancing.")
    else:
        remarks.append("Velocity is within a reasonable design range for a standard HVAC duct system.")

    if filter_loss_inwg > 0.5:
        remarks.append("Filter pressure drop is high and may warrant a larger filter section or lower face velocity.")
    elif filter_loss_inwg > 0:
        remarks.append("Filter pressure drop is acceptable within normal operating limits.")

    if recommended_fan_pressure_inwg > 2.0:
        remarks.append("Recommended fan pressure is elevated; check the fan selection and static regain strategy.")
    else:
        remarks.append("Recommended fan pressure is acceptable for a normal commercial HVAC system.")

    if friction_loss_inwg > 0.8:
        remarks.append("Friction loss is high for the selected duct run and may require additional duct resizing.")

    result = {
        "inputs": {
            "Airflow CFM": round(airflow_cfm, 2),
            "Duct Length ft": round(duct_length_ft, 2),
            "Friction Rate in.wg/100ft": round(friction_rate, 3),
            "Velocity FPM": round(velocity_fpm, 1),
            "Fitting Loss in.wg": round(fitting_loss, 3),
            "Coil Loss in.wg": round(coil_loss, 3),
            "Filter Loss in.wg": round(filter_loss, 3),
            "Diffuser Loss in.wg": round(diffuser_loss, 3),
            "Safety Factor %": round(safety_factor_percent, 1),
        },
        "results": {
            "Velocity Pressure (in.wg)": round(velocity_pressure_inwg, 3),
            "Friction Loss (in.wg)": round(friction_loss_inwg, 3),
            "Total Static Pressure (in.wg)": round(total_static_pressure_inwg, 3),
            "Recommended Fan Pressure (in.wg)": round(recommended_fan_pressure_inwg, 3),
            "Velocity Pressure (Pa)": round(velocity_pressure_inwg * 249.09, 2),
            "Friction Loss (Pa)": round(friction_loss_inwg * 249.09, 2),
            "Total Static Pressure (Pa)": round(total_static_pressure_inwg * 249.09, 2),
            "Recommended Fan Pressure (Pa)": round(recommended_fan_pressure_inwg * 249.09, 2),
        },
        "summary": {
            "Velocity Pressure": round(velocity_pressure_inwg, 3),
            "Friction Loss": round(friction_loss_inwg, 3),
            "Total Static Pressure": round(total_static_pressure_inwg, 3),
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
            "Velocity Pressure": "(V / 4005)^2",
            "Straight Duct Friction Loss": "(Length / 100) × Friction Rate",
            "Total Static Pressure": "FL + VP + Σ(fittings) + Coil + Filter + Diffuser",
            "Recommended Fan Pressure": "TSP × (1 + Safety Factor)",
        },
        "airflow_cfm": round(airflow_cfm, 2),
        "velocity_fpm": round(velocity_fpm, 1),
        "velocity_pressure_inwg": round(velocity_pressure_inwg, 3),
        "duct_length_ft": round(duct_length_ft, 2),
        "friction_rate_inwg_per_100ft": round(friction_rate, 3),
        "friction_loss_inwg": round(friction_loss_inwg, 3),
        "fitting_loss_inwg": round(fitting_loss, 3),
        "coil_loss_inwg": round(coil_loss, 3),
        "filter_loss_inwg": round(filter_loss, 3),
        "diffuser_loss_inwg": round(diffuser_loss, 3),
        "total_static_pressure_inwg": round(total_static_pressure_inwg, 3),
        "safety_factor_percent": round(safety_factor_percent, 1),
        "recommended_fan_pressure_inwg": round(recommended_fan_pressure_inwg, 3),
    }

    return result


def calculate_static_pressure(
    airflow,
    velocity,
    duct_length,
    friction_rate,
    fitting_loss_inwg=0.0,
    coil_loss_inwg=0.0,
    filter_loss_inwg=0.0,
    diffuser_loss_inwg=0.0,
    safety_factor_percent=20.0,
):
    """Backward-compatible wrapper for the existing route contract."""
    return calculate_static_pressure_uae(
        airflow_cfm=airflow,
        duct_length_ft=duct_length,
        friction_rate_inwg_per_100ft=friction_rate,
        velocity_fpm=velocity,
        fitting_loss_inwg=fitting_loss_inwg,
        coil_loss_inwg=coil_loss_inwg,
        filter_loss_inwg=filter_loss_inwg,
        diffuser_loss_inwg=diffuser_loss_inwg,
        safety_factor_percent=safety_factor_percent,
    )