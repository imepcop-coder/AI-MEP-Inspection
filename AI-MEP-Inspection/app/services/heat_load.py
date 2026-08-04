import math
from datetime import datetime


class HeatLoadCalculationError(ValueError):
    """Custom exception for Heat Load Calculator."""
    pass


# ============================================================
# UAE / GCC DEFAULT DESIGN VALUES
# ============================================================

DEFAULT_OUTDOOR_DB = 46.0
DEFAULT_INDOOR_DB = 24.0

DEFAULT_WALL_U = 0.60
DEFAULT_ROOF_U = 0.40

DEFAULT_GLASS_U = 2.80
DEFAULT_SHGC = 0.35

DEFAULT_SOLAR = 750.0

DEFAULT_PEOPLE_SENSIBLE = 75.0
DEFAULT_PEOPLE_LATENT = 55.0

DEFAULT_FRESH_AIR_FACTOR = 1.23

AIR_DENSITY = 1.20
AIR_CP = 1.005


# ============================================================
# Validation
# ============================================================

def _validate(
    length,
    width,
    height,
    occupants,
    lighting,
    equipment,
    outdoor_db,
    indoor_db,
    wall_u,
    roof_u,
    glass_area,
    glass_u,
    glass_shgc,
    solar,
    fresh_air_cfm,
):
    values = {
    "Room Length": length,
    "Room Width": width,
    "Room Height": height,
    "Occupants": occupants,
    "Lighting Load": lighting,
    "Equipment Load": equipment,
    "Outdoor Temperature": outdoor_db,
    "Indoor Temperature": indoor_db,
    "Wall U Value": wall_u,
    "Roof U Value": roof_u,
    "Glass Area": glass_area,
    "Glass U Value": glass_u,
    "Glass SHGC": glass_shgc,
    "Solar Irradiance": solar,
    "Fresh Air CFM": fresh_air_cfm,
}

    converted = {}

    for key, value in values.items():

        try:
            value = float(value)

        except (TypeError, ValueError):

            raise HeatLoadCalculationError(
                f"{key} must be numeric."
            )

        if math.isnan(value) or math.isinf(value):

            raise HeatLoadCalculationError(
                f"{key} must be a valid number."
            )

        converted[key] = value

    if converted["Room Length"] <= 0:
        raise HeatLoadCalculationError(
            "Room Length must be greater than zero."
        )

    if converted["Room Width"] <= 0:
        raise HeatLoadCalculationError(
            "Room Width must be greater than zero."
        )

    if converted["Room Height"] <= 0:
        raise HeatLoadCalculationError(
            "Room Height must be greater than zero."
        )

    if converted["Occupants"] < 0:
        raise HeatLoadCalculationError(
            "Occupants cannot be negative."
        )

    if converted["Lighting Load"] < 0:
        raise HeatLoadCalculationError(
            "Lighting Load cannot be negative."
        )

    if converted["Equipment Load"] < 0:
        raise HeatLoadCalculationError(
            "Equipment Load cannot be negative."
        )

    return converted


# ============================================================
# Professional Heat Load Calculator
# ============================================================

def calculate_heat_load(
    length,
    width,
    height,
    occupants,
    lighting,
    equipment,
    outdoor_db=46.0,
    indoor_db=24.0,
    wall_u=0.60,
    roof_u=0.40,
    glass_area=0.0,
    glass_u=2.80,
    glass_shgc=0.35,
    solar=750.0,
    fresh_air_cfm=0.0,
):
    """
    Professional UAE / GCC Heat Load Calculator
    """

    data = _validate(
        length,
        width,
        height,
        occupants,
        lighting,
        equipment,
        outdoor_db,
        indoor_db,
        wall_u,
        roof_u,
        glass_area,
        glass_u,
        glass_shgc,
        solar,
        fresh_air_cfm,
    )
    length = data["Room Length"]
    width = data["Room Width"]
    height = data["Room Height"]
    occupants = data["Occupants"]
    lighting = data["Lighting Load"]
    equipment = data["Equipment Load"]

    # ----------------------------------------------------
    # UAE DESIGN CONDITIONS
    # ----------------------------------------------------

    outdoor_db = data["Outdoor Temperature"]
    indoor_db = data["Indoor Temperature"]

    wall_u = data["Wall U Value"]
    roof_u = data["Roof U Value"]

    glass_area = data["Glass Area"]
    glass_u = data["Glass U Value"]
    glass_shgc = data["Glass SHGC"]

    solar = data["Solar Irradiance"]

    fresh_air_cfm = data["Fresh Air CFM"]

    # ----------------------------------------------------
    # Room Geometry
    # ----------------------------------------------------

    floor_area = length * width
    volume = floor_area * height

    wall_area = max(
    (2 * (length + width) * height) - glass_area,
    0.0,
     )
    roof_area = floor_area

    delta_t = max(
        outdoor_db - indoor_db,
        0,
    )

    # ----------------------------------------------------
    # Envelope Heat Gain
    # ----------------------------------------------------

    wall_heat_gain = (
        wall_u
        * wall_area
        * delta_t
    )

    roof_heat_gain = (
        roof_u
        * roof_area
        * delta_t
    )

    glass_conduction_gain = (
        glass_u
        * glass_area
        * delta_t
    )

    glass_solar_gain = (
        glass_area
        * glass_shgc
        * solar
    )

      # ----------------------------------------------------
    # Internal Loads
    # ----------------------------------------------------

    people_sensible = occupants * DEFAULT_PEOPLE_SENSIBLE
    people_latent = occupants * DEFAULT_PEOPLE_LATENT

    lighting_load = lighting
    equipment_load = equipment

    fresh_air_load = (
        DEFAULT_FRESH_AIR_FACTOR
        * fresh_air_cfm
        * delta_t
    )

    # ----------------------------------------------------
    # Total Cooling Load
    # ----------------------------------------------------

    total_watts = (
        wall_heat_gain
        + roof_heat_gain
        + glass_conduction_gain
        + glass_solar_gain
        + people_sensible
        + people_latent
        + lighting_load
        + equipment_load
        + fresh_air_load
    )

    total_kw = total_watts / 1000.0
    total_btuh = total_watts * 3.412142
    total_tr = total_btuh / 12000.0

    # ----------------------------------------------------
    # Air Flow
    # ----------------------------------------------------

    if delta_t > 0:

        mass_flow = (
            total_watts /
            (AIR_CP * 1000 * delta_t)
        )

        volume_flow = (
            mass_flow /
            AIR_DENSITY
        )

        required_cfm = (
            volume_flow *
            2118.88
        )

    else:

        required_cfm = 0.0

    airflow_lps = required_cfm * 0.4719

    recommended_ac = max(
        1,
        math.ceil(max(total_tr, 0.1))
    )

    envelope_load = (
        wall_heat_gain
        + roof_heat_gain
        + glass_conduction_gain
        + glass_solar_gain
    )

    internal_load = (
        people_sensible
        + people_latent
        + lighting_load
        + equipment_load
    )

    # ----------------------------------------------------
    # Return Results
    # ----------------------------------------------------

    return {

        # Existing Outputs

        "room_area": round(floor_area, 2),
        "room_volume": round(volume, 2),

        "room_load": round(envelope_load, 2),
        "people_load": round(
            people_sensible + people_latent,
            2,
        ),

        "lighting_load": round(
            lighting_load,
            2,
        ),

        "equipment_load": round(
            equipment_load,
            2,
        ),

        "total_watts": round(
            total_watts,
            2,
        ),

        "total_kw": round(
            total_kw,
            2,
        ),

        "total_btuh": round(
            total_btuh,
            2,
        ),

        "tons_of_refrigeration": round(
            total_tr,
            2,
        ),

        "required_cfm": round(
            required_cfm,
            2,
        ),

        "recommended_ac": recommended_ac,

        # Geometry

        "floor_area": round(
            floor_area,
            2,
        ),

        "wall_area": round(
            wall_area,
            2,
        ),

        "roof_area": round(
            roof_area,
            2,
        ),

        # Design Conditions

        "outdoor_temperature": outdoor_db,
        "indoor_temperature": indoor_db,
        "temperature_difference": round(
            delta_t,
            2,
        ),

        # Detailed Loads

        "wall_heat_gain": round(
            wall_heat_gain,
            2,
        ),

        "roof_heat_gain": round(
            roof_heat_gain,
            2,
        ),

        "glass_conduction_gain": round(
            glass_conduction_gain,
            2,
        ),

        "glass_solar_gain": round(
            glass_solar_gain,
            2,
        ),

        "people_sensible": round(
            people_sensible,
            2,
        ),

        "people_latent": round(
            people_latent,
            2,
        ),

        "fresh_air_load": round(
            fresh_air_load,
            2,
        ),

        "airflow_lps": round(
            airflow_lps,
            2,
        ),

        # Summary

        "summary": {

            "Envelope Load": round(
                envelope_load,
                2,
            ),

            "Internal Load": round(
                internal_load,
                2,
            ),

            "Ventilation Load": round(
                fresh_air_load,
                2,
            ),

            "Grand Total": round(
                total_watts,
                2,
            ),
        },

        # Engineering Information

        "calculation_standard":
            "ASHRAE Fundamentals / ASHRAE 62.1 / UAE GCC",

        "engineering_reference": [
            "ASHRAE Handbook - Fundamentals",
            "ASHRAE Standard 62.1",
            "SMACNA HVAC Duct Design",
            "UAE Abu Dhabi Cooling Load Manual",
        ],

        "generated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    }