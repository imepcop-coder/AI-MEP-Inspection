"""
Engineering Calculation Logic
AI MEP Calculator - Plumbing Module
"""

from math import pi, sqrt


# ==========================================================
# Water Demand Calculator
# ==========================================================

LITERS_PER_PERSON = {
    "Residential": 135,
    "Apartment": 135,
    "Villa": 180,
    "Hotel": 250,
    "Hospital": 450,
    "Office": 45,
    "School": 45,
    "Restaurant": 70,
    "Mall": 25,
    "Industrial": 60,
}

PEAK_FACTOR = {
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


def water_demand(building_type, occupancy, fixture_units=0):
    lpp = LITERS_PER_PERSON.get(building_type, 135)
    demand_lpd = occupancy * lpp
    demand_lpm = demand_lpd / (24 * 60)
    peak = PEAK_FACTOR.get(building_type, 2.5)
    peak_lpm = demand_lpm * peak

    return {
        "building_type": building_type,
        "occupancy": occupancy,
        "fixture_units": fixture_units,
        "liters_per_person": round(lpp, 2),
        "demand_lpd": round(demand_lpd, 2),
        "demand_lpm": round(demand_lpm, 2),
        "peak_factor": peak,
        "peak_demand_lpm": round(peak_lpm, 2),
    }


# ==========================================================
# Fixture Unit Calculator
# ==========================================================

FIXTURE_UNITS = {
    "Water Closet": 4,
    "Wash Basin": 1,
    "Kitchen Sink": 2,
    "Urinal": 2,
    "Shower": 2,
    "Bathtub": 4,
    "Drinking Fountain": 0.5,
    "Service Sink": 3,
}


def fixture_units(fixture_type, quantity):
    fu = FIXTURE_UNITS.get(fixture_type, 1)
    total = fu * quantity

    return {
        "fixture_type": fixture_type,
        "quantity": quantity,
        "fixture_unit_per_item": fu,
        "total_fixture_units": round(total, 2),
    }


# ==========================================================
# Pipe Size Calculator
# ==========================================================

STANDARD_PIPE_SIZES = [
    15,
    20,
    25,
    32,
    40,
    50,
    65,
    80,
    100,
    125,
    150,
    200,
    250,
    300,
]


def pipe_size(flow_rate_lpm, velocity):
    q = flow_rate_lpm / 1000 / 60
    diameter = sqrt((4 * q) / (pi * velocity))
    diameter_mm = diameter * 1000

    recommended = STANDARD_PIPE_SIZES[-1]
    for size in STANDARD_PIPE_SIZES:
        if size >= diameter_mm:
            recommended = size
            break

    return {
        "flow_rate_lpm": flow_rate_lpm,
        "velocity_mps": velocity,
        "diameter_mm": round(diameter_mm, 2),
        "recommended_nominal_size": f"{recommended} mm",
    }


# ==========================================================
# Drainage Calculator
# ==========================================================

def drainage_pipe(fixture_units, slope_percent):
    flow = fixture_units * 0.03

    if fixture_units <= 20:
        size = 75
    elif fixture_units <= 160:
        size = 100
    elif fixture_units <= 360:
        size = 150
    else:
        size = 200

    return {
        "fixture_units": fixture_units,
        "slope_percent": slope_percent,
        "recommended_pipe_mm": size,
        "estimated_flow_lps": round(flow, 2),
    }


# ==========================================================
# Rainwater Calculator
# ==========================================================

def rainwater(area, rainfall, runoff=0.9):
    flow = (area * rainfall * runoff) / 3600

    return {
        "roof_area_m2": area,
        "rainfall_mm_hr": rainfall,
        "runoff_coefficient": runoff,
        "flow_lps": round(flow, 2),
    }


# ==========================================================
# Water Tank Calculator
# ==========================================================

def water_tank(occupancy, storage_days=1, liters_per_person=135):
    capacity = occupancy * liters_per_person * storage_days

    return {
        "occupancy": occupancy,
        "storage_days": storage_days,
        "liters_per_person": liters_per_person,
        "required_capacity_liters": round(capacity, 2),
        "required_capacity_m3": round(capacity / 1000, 2),
    }


# ==========================================================
# Underground Sump
# ==========================================================

def sump_capacity(daily_demand, storage_days=2):
    total = daily_demand * storage_days

    return {
        "daily_demand_liters": daily_demand,
        "storage_days": storage_days,
        "sump_capacity_liters": round(total, 2),
        "sump_capacity_m3": round(total / 1000, 2),
    }


# ==========================================================
# Pump Head & Power
# ==========================================================

def pump_power(flow_lps, total_head, efficiency):
    flow = flow_lps / 1000
    hydraulic = (1000 * 9.81 * flow * total_head) / 1000
    motor = hydraulic / (efficiency / 100)
    hp = motor * 1.34102

    return {
        "flow_lps": flow_lps,
        "total_head_m": total_head,
        "efficiency": efficiency,
        "hydraulic_power_kw": round(hydraulic, 2),
        "motor_power_kw": round(motor, 2),
        "motor_power_hp": round(hp, 2),
    }
