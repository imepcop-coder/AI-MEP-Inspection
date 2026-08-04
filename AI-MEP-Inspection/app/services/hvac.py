import math


class HVACCalculationError(ValueError):
    """Custom exception for HVAC calculation errors."""
    pass


def _validate_positive(fields: dict):
    validated = {}
    for name, value in fields.items():
        try:
            validated[name] = float(value)
        except (TypeError, ValueError):
            raise HVACCalculationError(f"{name.replace('_', ' ').title()} must be numeric.")

        if math.isnan(validated[name]) or math.isinf(validated[name]):
            raise HVACCalculationError(f"{name.replace('_', ' ').title()} must be a finite number.")

    return validated


def calculate_cooling_load(
    length,
    width,
    height,
    outdoor_temp,
    indoor_temp,
    wall_area,
    wall_u_value,
    roof_area,
    roof_u_value,
    glass_area,
    glass_u_value,
    glass_shgc,
    occupants,
    lighting_load,
    equipment_load,
    fresh_air_cfm,
):
    """Estimate room cooling load from envelope, internal gains and ventilation."""
    fields = {
        "length": length,
        "width": width,
        "height": height,
        "outdoor_temp": outdoor_temp,
        "indoor_temp": indoor_temp,
        "wall_area": wall_area,
        "wall_u_value": wall_u_value,
        "roof_area": roof_area,
        "roof_u_value": roof_u_value,
        "glass_area": glass_area,
        "glass_u_value": glass_u_value,
        "glass_shgc": glass_shgc,
        "occupants": occupants,
        "lighting_load": lighting_load,
        "equipment_load": equipment_load,
        "fresh_air_cfm": fresh_air_cfm,
    }

    data = _validate_positive(fields)

    delta_t = max(data["outdoor_temp"] - data["indoor_temp"], 0)
    total_floor_area = data["length"] * data["width"]
    wall_area_estimated = data["wall_area"]
    roof_area_estimated = data["roof_area"]
    glass_area = min(data["glass_area"], wall_area_estimated + roof_area_estimated)

    wall_gain = data["wall_u_value"] * wall_area_estimated * delta_t
    roof_gain = data["roof_u_value"] * roof_area_estimated * delta_t
    glass_conduction = data["glass_u_value"] * glass_area * delta_t
    solar_irradiance = 500.0
    glass_solar_gain = glass_area * data["glass_shgc"] * solar_irradiance
    people_sensible = data["occupants"] * 120.0
    people_latent = data["occupants"] * 70.0
    lighting_gain = data["lighting_load"]
    equipment_gain = data["equipment_load"]
    fresh_air_gain = 0.57 * data["fresh_air_cfm"] * delta_t

    total_watts = (
        wall_gain
        + roof_gain
        + glass_conduction
        + glass_solar_gain
        + people_sensible
        + people_latent
        + lighting_gain
        + equipment_gain
        + fresh_air_gain
    )

    total_kw = total_watts / 1000.0
    total_btuh = total_watts * 3.412142
    total_ton = total_btuh / 12000.0
    required_cfm = total_btuh / (1.08 * max(delta_t, 1))

    return {
        "room_length": round(data["length"], 2),
        "room_width": round(data["width"], 2),
        "room_height": round(data["height"], 2),
        "floor_area": round(total_floor_area, 2),
        "wall_area": round(wall_area_estimated, 2),
        "roof_area": round(roof_area_estimated, 2),
        "glass_area": round(glass_area, 2),
        "outdoor_temp": round(data["outdoor_temp"], 1),
        "indoor_temp": round(data["indoor_temp"], 1),
        "delta_t": round(delta_t, 1),
        "wall_heat_gain": round(wall_gain, 2),
        "roof_heat_gain": round(roof_gain, 2),
        "glass_conduction_gain": round(glass_conduction, 2),
        "glass_solar_gain": round(glass_solar_gain, 2),
        "occupancy_sensible_load": round(people_sensible, 2),
        "occupancy_latent_load": round(people_latent, 2),
        "lighting_load": round(lighting_gain, 2),
        "equipment_load": round(equipment_gain, 2),
        "fresh_air_load": round(fresh_air_gain, 2),
        "total_watts": round(total_watts, 2),
        "total_kw": round(total_kw, 2),
        "total_btuh": round(total_btuh, 2),
        "tons_of_refrigeration": round(total_ton, 2),
        "required_cfm": round(required_cfm, 2),
        "recommended_ac": max(1, math.ceil(total_ton)),
    }


def calculate_chiller_capacity(load_kw, safety_factor, cop):
    fields = _validate_positive(
        {
            "load_kw": load_kw,
            "safety_factor": safety_factor,
            "cop": cop,
        }
    )

    design_capacity_kw = fields["load_kw"] * (1 + fields["safety_factor"] / 100)
    design_capacity_tr = design_capacity_kw / 3.517
    power_input_kw = design_capacity_kw / fields["cop"] if fields["cop"] > 0 else 0.0

    return {
        "design_capacity_kw": round(design_capacity_kw, 2),
        "design_capacity_tr": round(design_capacity_tr, 2),
        "power_input_kw": round(power_input_kw, 2),
        "cop": round(fields["cop"], 2),
        "safety_factor": round(fields["safety_factor"], 2),
    }


def calculate_chiller_efficiency(
    cooling_capacity_kw,
    input_power_kw,
    eer_25,
    eer_50,
    eer_75,
    eer_100,
):
    fields = _validate_positive(
        {
            "cooling_capacity_kw": cooling_capacity_kw,
            "input_power_kw": input_power_kw,
            "eer_25": eer_25,
            "eer_50": eer_50,
            "eer_75": eer_75,
            "eer_100": eer_100,
        }
    )

    cop = fields["cooling_capacity_kw"] / fields["input_power_kw"] if fields["input_power_kw"] > 0 else 0.0
    ip_lv = (
        0.01 * fields["eer_100"]
        + 0.42 * fields["eer_75"]
        + 0.45 * fields["eer_50"]
        + 0.12 * fields["eer_25"]
    )
    np_lv = ip_lv

    return {
        "cooling_capacity_kw": round(fields["cooling_capacity_kw"], 2),
        "input_power_kw": round(fields["input_power_kw"], 2),
        "cop": round(cop, 2),
        "eer_25": round(fields["eer_25"], 2),
        "eer_50": round(fields["eer_50"], 2),
        "eer_75": round(fields["eer_75"], 2),
        "eer_100": round(fields["eer_100"], 2),
        "iplv": round(ip_lv, 2),
        "nplv": round(np_lv, 2),
    }


def calculate_pressure_drop(
    method,
    flow_lpm,
    diameter_mm,
    length_m,
    roughness_mm,
    hazen_williams_c,
):
    if method not in {"Darcy-Weisbach", "Hazen-Williams"}:
        raise HVACCalculationError("Method must be Darcy-Weisbach or Hazen-Williams.")

    fields = _validate_positive(
        {
            "flow_lpm": flow_lpm,
            "diameter_mm": diameter_mm,
            "length_m": length_m,
            "roughness_mm": roughness_mm,
            "hazen_williams_c": hazen_williams_c,
        }
    )

    q_m3s = fields["flow_lpm"] / 1000.0 / 60.0
    diameter_m = fields["diameter_mm"] / 1000.0
    area = math.pi * diameter_m ** 2 / 4.0
    if area <= 0:
        raise HVACCalculationError("Pipe diameter must be greater than zero.")

    velocity = q_m3s / area
    rho = 998.2
    mu = 0.001
    re = rho * velocity * diameter_m / mu
    if re <= 0:
        raise HVACCalculationError("Reynolds number could not be calculated.")

    if re < 2300:
        friction_factor = 64.0 / re
    else:
        friction_factor = 0.3164 / re ** 0.25

    darcy_head_loss = friction_factor * (fields["length_m"] / diameter_m) * (velocity ** 2) / (2 * 9.81)
    darcy_pressure_pa = rho * 9.81 * darcy_head_loss

    q_m3s_hw = q_m3s
    c = fields["hazen_williams_c"]
    hw_head_loss = (
        10.67
        * fields["length_m"]
        * q_m3s_hw ** 1.852
        / (c ** 1.852 * diameter_m ** 4.8704)
        if c > 0
        else 0.0
    )
    hw_pressure_pa = rho * 9.81 * hw_head_loss

    result = {
        "flow_lpm": round(fields["flow_lpm"], 2),
        "diameter_mm": round(fields["diameter_mm"], 2),
        "length_m": round(fields["length_m"], 2),
        "velocity_m_s": round(velocity, 2),
        "reynolds_number": round(re, 0),
        "darcy_head_loss_m": round(darcy_head_loss, 3),
        "darcy_pressure_pa": round(darcy_pressure_pa, 2),
        "hazen_williams_head_loss_m": round(hw_head_loss, 3),
        "hazen_williams_pressure_pa": round(hw_pressure_pa, 2),
        "method": method,
    }

    if method == "Darcy-Weisbach":
        result["selected_head_loss_m"] = result["darcy_head_loss_m"]
        result["selected_pressure_pa"] = result["darcy_pressure_pa"]
    else:
        result["selected_head_loss_m"] = result["hazen_williams_head_loss_m"]
        result["selected_pressure_pa"] = result["hazen_williams_pressure_pa"]

    return result


def calculate_expansion_tank(
    system_volume_m3,
    temperature_rise_c,
    precharge_pressure_bar,
    system_pressure_bar,
):
    fields = _validate_positive(
        {
            "system_volume_m3": system_volume_m3,
            "temperature_rise_c": temperature_rise_c,
            "precharge_pressure_bar": precharge_pressure_bar,
            "system_pressure_bar": system_pressure_bar,
        }
    )

    if fields["precharge_pressure_bar"] >= fields["system_pressure_bar"]:
        raise HVACCalculationError("Precharge pressure should be lower than system pressure.")

    alpha = 0.000214
    expansion_volume_m3 = fields["system_volume_m3"] * alpha * fields["temperature_rise_c"]
    acceptance_factor = 0.20
    required_tank_m3 = expansion_volume_m3 / acceptance_factor

    return {
        "system_volume_m3": round(fields["system_volume_m3"], 3),
        "temperature_rise_c": round(fields["temperature_rise_c"], 2),
        "precharge_pressure_bar": round(fields["precharge_pressure_bar"], 2),
        "system_pressure_bar": round(fields["system_pressure_bar"], 2),
        "expansion_volume_m3": round(expansion_volume_m3, 4),
        "required_tank_m3": round(required_tank_m3, 4),
        "recommended_tank_l": round(required_tank_m3 * 1000.0, 2),
    }


def calculate_hydrotest_water(system_volume_l, leak_allowance_percent):
    fields = _validate_positive(
        {
            "system_volume_l": system_volume_l,
            "leak_allowance_percent": leak_allowance_percent,
        }
    )

    required_liters = fields["system_volume_l"] * (1 + fields["leak_allowance_percent"] / 100.0)

    return {
        "system_volume_l": round(fields["system_volume_l"], 2),
        "leak_allowance_percent": round(fields["leak_allowance_percent"], 2),
        "required_water_l": round(required_liters, 2),
        "required_water_m3": round(required_liters / 1000.0, 3),
    }


def calculate_generator_room_ventilation(heat_rejection_kw, temp_rise_c):
    fields = _validate_positive(
        {
            "heat_rejection_kw": heat_rejection_kw,
            "temp_rise_c": temp_rise_c,
        }
    )

    if fields["temp_rise_c"] <= 0:
        raise HVACCalculationError("Temperature rise must be greater than zero.")

    specific_heat = 1005.0
    density = 1.2
    airflow_m3_s = fields["heat_rejection_kw"] * 1000.0 / (density * specific_heat * fields["temp_rise_c"])
    airflow_l_s = airflow_m3_s * 1000.0
    airflow_cfm = airflow_m3_s * 2118.88

    return {
        "heat_rejection_kw": round(fields["heat_rejection_kw"], 2),
        "temp_rise_c": round(fields["temp_rise_c"], 2),
        "airflow_m3_s": round(airflow_m3_s, 3),
        "airflow_l_s": round(airflow_l_s, 2),
        "airflow_cfm": round(airflow_cfm, 2),
        "airflow_cmh": round(airflow_m3_s * 3600.0, 2),
    }


def calculate_battery_room_ventilation(number_batteries, heat_per_battery_kw, temp_rise_c):
    fields = _validate_positive(
        {
            "number_batteries": number_batteries,
            "heat_per_battery_kw": heat_per_battery_kw,
            "temp_rise_c": temp_rise_c,
        }
    )

    total_heat_kw = fields["number_batteries"] * fields["heat_per_battery_kw"]
    ventilation = calculate_generator_room_ventilation(total_heat_kw, fields["temp_rise_c"])
    ventilation["number_batteries"] = int(fields["number_batteries"])
    ventilation["heat_per_battery_kw"] = round(fields["heat_per_battery_kw"], 2)
    ventilation["total_heat_kw"] = round(total_heat_kw, 2)
    return ventilation


def calculate_heater_capacity(area_m2, u_value_w_m2k, temp_difference_c, efficiency_percent):
    fields = _validate_positive(
        {
            "area_m2": area_m2,
            "u_value_w_m2k": u_value_w_m2k,
            "temp_difference_c": temp_difference_c,
            "efficiency_percent": efficiency_percent,
        }
    )

    if fields["efficiency_percent"] <= 0 or fields["efficiency_percent"] > 100:
        raise HVACCalculationError("Efficiency must be between 0 and 100 percent.")

    heat_load_kw = (fields["area_m2"] * fields["u_value_w_m2k"] * fields["temp_difference_c"]) / 1000.0
    required_heater_kw = heat_load_kw / (fields["efficiency_percent"] / 100.0)

    return {
        "area_m2": round(fields["area_m2"], 2),
        "u_value_w_m2k": round(fields["u_value_w_m2k"], 2),
        "temp_difference_c": round(fields["temp_difference_c"], 2),
        "efficiency_percent": round(fields["efficiency_percent"], 2),
        "heat_load_kw": round(heat_load_kw, 3),
        "required_heater_kw": round(required_heater_kw, 3),
    }
