"""
Business Service Layer
AI MEP Calculator - Plumbing Module
"""

from .plumbing_calculators import (
    water_demand,
    fixture_units,
    pipe_size,
    calculate_pipe_velocity,
    calculate_pipe_friction_loss,
    drainage_pipe,
    rainwater,
    water_tank,
    sump_capacity,
    pump_power,
    calculate_booster_pump,
    calculate_transfer_pump,
    calculate_domestic_pump,
    calculate_hydrotest_pressure,
    calculate_expansion_tank,
)

from app.calculators.plumbing_models import (
    WaterDemandRequest,
    WaterDemandResponse,
    FixtureUnitRequest,
    FixtureUnitResponse,
    PipeSizeRequest,
    PipeSizeResponse,
    PipeVelocityRequest,
    PipeVelocityResponse,
    PipeFrictionRequest,
    PipeFrictionResponse,
    DrainageRequest,
    DrainageResponse,
    RainwaterRequest,
    RainwaterResponse,
    TankRequest,
    TankResponse,
    SumpRequest,
    SumpResponse,
    PumpRequest,
    PumpResponse,
    BoosterPumpRequest,
    BoosterPumpResponse,
    TransferPumpRequest,
    TransferPumpResponse,
    DomesticPumpRequest,
    DomesticPumpResponse,
    HydrotestRequest,
    HydrotestResponse,
    ExpansionTankRequest,
    ExpansionTankResponse,
)


class PlumbingService:
    """
    Business service for Plumbing calculations.
    """

    # =====================================================
    # Water Demand
    # =====================================================

    @staticmethod
    def calculate_water_demand(
        request: WaterDemandRequest,
    ) -> WaterDemandResponse:

        result = water_demand(
            building_type=request.building_type,
            occupancy=request.occupancy,
            fixture_units=request.fixture_units,
        )

        return WaterDemandResponse(**result)

    # =====================================================
    # Fixture Units
    # =====================================================

    @staticmethod
    def calculate_fixture_units(
        request: FixtureUnitRequest,
    ) -> FixtureUnitResponse:

        result = fixture_units(
            fixture_type=request.fixture_type,
            quantity=request.quantity,
        )

        return FixtureUnitResponse(**result)

    # =====================================================
    # Pipe Size
    # =====================================================

    @staticmethod
    def calculate_pipe_size(
        request: PipeSizeRequest,
    ) -> PipeSizeResponse:

        result = pipe_size(
            flow_rate_lpm=request.flow_rate_lpm,
            velocity=request.velocity_mps,
        )

        return PipeSizeResponse(**result)

    # =====================================================
    # Pipe Velocity
    # =====================================================

    @staticmethod
    def calculate_pipe_velocity(
        request: PipeVelocityRequest,
    ) -> PipeVelocityResponse:

        result = calculate_pipe_velocity(
            flow_rate_lpm=request.flow_rate_lpm,
            diameter_mm=request.diameter_mm,
        )

        return PipeVelocityResponse(**result)

    # =====================================================
    # Pipe Friction
    # =====================================================

    @staticmethod
    def calculate_pipe_friction(
        request: PipeFrictionRequest,
    ) -> PipeFrictionResponse:

        result = calculate_pipe_friction_loss(
            flow_rate_lpm=request.flow_rate_lpm,
            diameter_mm=request.diameter_mm,
            length_m=request.length_m,
            hazen_williams_c=request.hazen_williams_c,
        )

        return PipeFrictionResponse(**result)

    # =====================================================
    # Drainage
    # =====================================================

    @staticmethod
    def calculate_drainage(
        request: DrainageRequest,
    ) -> DrainageResponse:

        result = drainage_pipe(
            fixture_units=request.fixture_units,
            slope_percent=request.slope_percent,
        )

        return DrainageResponse(**result)

    # =====================================================
    # Rainwater
    # =====================================================

    @staticmethod
    def calculate_rainwater(
        request: RainwaterRequest,
    ) -> RainwaterResponse:

        result = rainwater(
            area=request.roof_area_m2,
            rainfall=request.rainfall_mm_hr,
            runoff=request.runoff_coefficient,
        )

        return RainwaterResponse(**result)

    # =====================================================
    # Water Tank
    # =====================================================

    @staticmethod
    def calculate_water_tank(
        request: TankRequest,
    ) -> TankResponse:

        result = water_tank(
            occupancy=request.occupancy,
            storage_days=request.storage_days,
            liters_per_person=request.liters_per_person,
        )

        return TankResponse(**result)

    # =====================================================
    # Underground Sump
    # =====================================================

    @staticmethod
    def calculate_sump(
        request: SumpRequest,
    ) -> SumpResponse:

        result = sump_capacity(
            daily_demand=request.daily_demand_liters,
            storage_days=request.storage_days,
        )

        return SumpResponse(**result)

    # =====================================================
    # Pump
    # =====================================================

    @staticmethod
    def calculate_pump(
        request: PumpRequest,
    ) -> PumpResponse:

        result = pump_power(
            flow_lps=request.flow_lps,
            total_head=request.total_head_m,
            efficiency=request.efficiency,
        )

        return PumpResponse(**result)

    # =====================================================
    # Booster Pump
    # =====================================================

    @staticmethod
    def calculate_booster_pump(
        request: BoosterPumpRequest,
    ) -> BoosterPumpResponse:

        result = calculate_booster_pump(
            flow_lps=request.flow_lps,
            required_pressure_kpa=request.required_pressure_kpa,
            inlet_pressure_kpa=request.inlet_pressure_kpa,
            efficiency_percent=request.efficiency,
        )

        return BoosterPumpResponse(**result)

    # =====================================================
    # Transfer Pump
    # =====================================================

    @staticmethod
    def calculate_transfer_pump(
        request: TransferPumpRequest,
    ) -> TransferPumpResponse:

        result = calculate_transfer_pump(
            flow_lps=request.flow_lps,
            lift_m=request.lift_m,
            friction_loss_m=request.friction_loss_m,
            efficiency_percent=request.efficiency,
        )

        return TransferPumpResponse(**result)

    # =====================================================
    # Domestic Pump
    # =====================================================

    @staticmethod
    def calculate_domestic_pump(
        request: DomesticPumpRequest,
    ) -> DomesticPumpResponse:

        result = calculate_domestic_pump(
            flow_lps=request.flow_lps,
            required_residual_pressure_kpa=request.required_residual_pressure_kpa,
            elevation_m=request.elevation_m,
            efficiency_percent=request.efficiency,
        )

        return DomesticPumpResponse(**result)

    # =====================================================
    # Hydrotest
    # =====================================================

    @staticmethod
    def calculate_hydrotest(
        request: HydrotestRequest,
    ) -> HydrotestResponse:

        result = calculate_hydrotest_pressure(
            operating_pressure_kpa=request.operating_pressure_kpa,
            test_factor=request.test_factor,
        )

        return HydrotestResponse(**result)

    # =====================================================
    # Expansion Tank
    # =====================================================

    @staticmethod
    def calculate_expansion_tank(
        request: ExpansionTankRequest,
    ) -> ExpansionTankResponse:

        result = calculate_expansion_tank(
            system_volume_l=request.system_volume_l,
            temp_rise_c=request.temp_rise_c,
            expansion_coefficient=request.expansion_coefficient,
            safety_factor=request.safety_factor,
            precharge_pressure_kpa=request.precharge_pressure_kpa,
        )

        return ExpansionTankResponse(**result)
