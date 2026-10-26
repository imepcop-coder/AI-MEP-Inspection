import math

from typing import Literal


class ElectricalCalculationError(Exception):
    pass


def validate_positive(value: float, name: str) -> float:
    if value is None or value <= 0:
        raise ElectricalCalculationError(f"{name} must be greater than zero.")
    return value


def validate_percentage(value: float, name: str) -> float:
    value = float(value)
    if value <= 0 or value > 100:
        raise ElectricalCalculationError(f"{name} must be between 0 and 100.")
    return value


def validate_power_factor(value: float) -> float:
    value = float(value)
    if value <= 0 or value > 1:
        raise ElectricalCalculationError("Power factor must be between 0 and 1.")
    return value


def normalize_voltage_drop_phase_factor(phase_type: Literal["Single-phase", "Three-phase"]) -> float:
    return 2.0 if phase_type == "Single-phase" else 1.732


def select_standard_conductor_size(required_area_mm2: float) -> float:
    standard_sizes = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
    return next((size for size in standard_sizes if size >= required_area_mm2), standard_sizes[-1])


def calculate_cable_size(current_a: float, ambient_temp_c: float = 30.0) -> dict:
    current_a = validate_positive(float(current_a), "Current")
    ambient_temp_c = float(ambient_temp_c)

    allowable_density = 4.0
    design_current = current_a * 1.25
    temperature_derating = 1.0
    if ambient_temp_c > 30.0:
        temperature_derating = max(0.7, 1.0 - 0.006 * (ambient_temp_c - 30.0))

    required_area_mm2 = design_current / (allowable_density * temperature_derating)
    recommended_area_mm2 = select_standard_conductor_size(required_area_mm2)

    return {
        "design_current_a": round(design_current, 2),
        "required_area_mm2": round(required_area_mm2, 2),
        "recommended_area_mm2": round(recommended_area_mm2, 2),
        "temperature_derating_factor": round(temperature_derating, 3),
    }


def calculate_voltage_drop(
    voltage_v: float,
    current_a: float,
    length_m: float,
    conductor_area_mm2: float,
    power_factor: float,
    phase_type: Literal["Single-phase", "Three-phase"] = "Single-phase",
) -> dict:
    voltage_v = validate_positive(float(voltage_v), "Voltage")
    current_a = validate_positive(float(current_a), "Current")
    length_m = validate_positive(float(length_m), "Length")
    conductor_area_mm2 = validate_positive(float(conductor_area_mm2), "Conductor area")
    power_factor = validate_power_factor(power_factor)

    resistivity = 0.01786
    resistance_ohm = resistivity * length_m / conductor_area_mm2
    reactance_ohm = 0.00008 * length_m
    cos_phi = power_factor
    sin_phi = math.sqrt(max(0.0, 1.0 - cos_phi**2))
    phase_factor = normalize_voltage_drop_phase_factor(phase_type)
    voltage_drop = phase_factor * current_a * (resistance_ohm * cos_phi + reactance_ohm * sin_phi)
    percent_drop = voltage_drop / voltage_v * 100.0

    return {
        "voltage_drop_v": round(voltage_drop, 3),
        "percent_drop": round(percent_drop, 3),
        "resistance_ohm": round(resistance_ohm, 5),
        "reactance_ohm": round(reactance_ohm, 5),
    }


def calculate_current(power_kw: float, voltage_v: float, power_factor: float, phase_type: Literal["Single-phase", "Three-phase"]) -> dict:
    power_kw = validate_positive(float(power_kw), "Power")
    voltage_v = validate_positive(float(voltage_v), "Voltage")
    power_factor = validate_power_factor(power_factor)

    apparent_power_kva = power_kw / power_factor
    if phase_type == "Single-phase":
        current_a = power_kw * 1000.0 / (voltage_v * power_factor)
    else:
        current_a = power_kw * 1000.0 / (1.732 * voltage_v * power_factor)

    return {
        "current_a": round(current_a, 2),
        "apparent_power_kva": round(apparent_power_kva, 2),
        "phase_type": phase_type,
    }


def calculate_transformer_sizing(load_kw: float, power_factor: float) -> dict:
    load_kw = validate_positive(float(load_kw), "Load")
    power_factor = validate_power_factor(power_factor)

    service_factor = 1.25
    base_kva = load_kw / power_factor
    required_kva = base_kva * service_factor

    return {
        "load_kw": round(load_kw, 2),
        "base_kva": round(base_kva, 2),
        "required_kva": round(required_kva, 2),
        "service_factor": service_factor,
    }


def calculate_generator_sizing(load_kw: float, power_factor: float, starting_load_factor: float) -> dict:
    load_kw = validate_positive(float(load_kw), "Load")
    power_factor = validate_power_factor(power_factor)
    starting_load_factor = validate_positive(float(starting_load_factor), "Starting load factor")

    base_kva = load_kw / power_factor
    required_kva = base_kva * starting_load_factor

    return {
        "load_kw": round(load_kw, 2),
        "base_kva": round(base_kva, 2),
        "required_kva": round(required_kva, 2),
        "starting_load_factor": round(starting_load_factor, 2),
    }


def calculate_ups_sizing(load_kw: float, autonomy_minutes: float, efficiency_percent: float) -> dict:
    load_kw = validate_positive(float(load_kw), "Load")
    autonomy_minutes = validate_positive(float(autonomy_minutes), "Autonomy")
    efficiency = validate_percentage(float(efficiency_percent), "Efficiency") / 100.0
    ups_power_factor = 0.9

    required_kva = load_kw / (ups_power_factor * efficiency)
    battery_capacity_kwh = load_kw * (autonomy_minutes / 60.0) / efficiency

    return {
        "required_kva": round(required_kva, 2),
        "battery_capacity_kwh": round(battery_capacity_kwh, 2),
        "assumed_power_factor": ups_power_factor,
        "efficiency_percent": round(efficiency * 100.0, 1),
    }


def calculate_lighting_lux(area_m2: float, target_lux: float, lumens_per_watt: float) -> dict:
    area_m2 = validate_positive(float(area_m2), "Area")
    target_lux = validate_positive(float(target_lux), "Target lux")
    lumens_per_watt = validate_positive(float(lumens_per_watt), "Lumens per watt")

    utilization_factor = 0.6
    maintenance_factor = 0.8
    total_lumens = area_m2 * target_lux
    watts_required = total_lumens / (lumens_per_watt * utilization_factor * maintenance_factor)
    fixture_count = math.ceil(watts_required / 40.0)

    return {
        "required_power_w": round(watts_required, 2),
        "fixture_count": fixture_count,
        "power_density_w_m2": round(watts_required / area_m2, 2),
    }


def calculate_circuit_breaker(current_a: float, breaker_type: str) -> dict:
    current_a = validate_positive(float(current_a), "Current")

    design_current = current_a * 1.25
    standard_ratings = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400]
    recommended_rating = next((rating for rating in standard_ratings if rating >= design_current), standard_ratings[-1])

    return {
        "breaker_type": breaker_type,
        "design_current_a": round(design_current, 2),
        "recommended_rating_a": recommended_rating,
    }


def calculate_battery_sizing(
    load_kw: float,
    autonomy_hours: float,
    battery_voltage_v: float = 48.0,
    efficiency_percent: float = 90.0,
) -> dict:
    load_kw = validate_positive(float(load_kw), "Load")
    autonomy_hours = validate_positive(float(autonomy_hours), "Autonomy")
    battery_voltage_v = validate_positive(float(battery_voltage_v), "Battery voltage")
    efficiency = validate_percentage(float(efficiency_percent), "Efficiency") / 100.0

    required_energy_kwh = load_kw * autonomy_hours / efficiency
    battery_capacity_ah = required_energy_kwh * 1000.0 / battery_voltage_v

    return {
        "required_energy_kwh": round(required_energy_kwh, 2),
        "battery_capacity_ah": round(battery_capacity_ah, 2),
        "battery_voltage_v": round(battery_voltage_v, 1),
        "efficiency_percent": round(efficiency * 100.0, 1),
    }


def calculate_earthing_resistance(
    soil_resistivity_ohm_m: float,
    electrode_length_m: float,
    electrode_diameter_mm: float,
    electrode_count: int = 1,
) -> dict:
    soil_resistivity_ohm_m = validate_positive(float(soil_resistivity_ohm_m), "Soil resistivity")
    electrode_length_m = validate_positive(float(electrode_length_m), "Electrode length")
    electrode_diameter_mm = validate_positive(float(electrode_diameter_mm), "Electrode diameter")
    electrode_count = int(validate_positive(float(electrode_count), "Electrode count"))

    electrode_diameter_m = electrode_diameter_mm / 1000.0
    single_rod_resistance = (
        soil_resistivity_ohm_m
        / (2.0 * math.pi * electrode_length_m)
        * (math.log(4.0 * electrode_length_m / electrode_diameter_m) - 1.0)
    )
    combined_resistance = single_rod_resistance / electrode_count
    spacing_m = electrode_length_m * 1.5

    return {
        "single_rod_resistance_ohm": round(single_rod_resistance, 3),
        "combined_resistance_ohm": round(combined_resistance, 3),
        "electrode_count": electrode_count,
        "recommended_spacing_m": round(spacing_m, 2),
    }


def calculate_power_factor(
    real_power_kw: float,
    apparent_power_kva: float,
    target_power_factor: float | None = None,
) -> dict:
    real_power_kw = validate_positive(float(real_power_kw), "Real power")
    apparent_power_kva = validate_positive(float(apparent_power_kva), "Apparent power")
    power_factor = real_power_kw / apparent_power_kva
    if power_factor <= 0 or power_factor > 1:
        raise ElectricalCalculationError("Computed power factor must be between 0 and 1.")

    reactive_power_kvar = math.sqrt(max(0.0, apparent_power_kva**2 - real_power_kw**2))
    result = {
        "power_factor": round(power_factor, 3),
        "reactive_power_kvar": round(reactive_power_kvar, 2),
        "real_power_kw": round(real_power_kw, 2),
        "apparent_power_kva": round(apparent_power_kva, 2),
    }

    if target_power_factor is not None:
        target_power_factor = validate_power_factor(float(target_power_factor))
        if target_power_factor < power_factor:
            raise ElectricalCalculationError("Target power factor must be greater than or equal to current power factor.")
        if target_power_factor > 0 and target_power_factor <= 1.0:
            current_angle = math.acos(power_factor)
            target_angle = math.acos(target_power_factor)
            capacitor_kvar = real_power_kw * (math.tan(current_angle) - math.tan(target_angle))
            result["target_power_factor"] = round(target_power_factor, 3)
            result["correction_capacitor_kvar"] = round(max(0.0, capacitor_kvar), 2)

    return result
