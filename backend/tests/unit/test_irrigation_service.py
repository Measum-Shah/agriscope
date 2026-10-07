"""Unit tests for soil water balance, FAO-56 irrigation planning, and crop library."""

import uuid
from datetime import date, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.soil import get_soil_preset, SOIL_PRESETS
from app.models.crop import Crop, CropStage
from app.models.field import Field
from app.models.irrigation_event import IrrigationEvent
from app.models.user import User, UserRole, UserStatus
from app.schemas.irrigation import IrrigationEventCreate
from app.services.field_service import FieldService
from app.services.irrigation_service import (
    IrrigationService,
    calculate_effective_rainfall,
    get_dynamic_root_depth,
)
from agriscope_ml.physics.crop_coefficients import (
    CropStageKc,
    CropStageLengths,
    calculate_etc,
    interpolate_kc_stage,
)

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [74.30, 31.50],
            [74.31, 31.50],
            [74.31, 31.51],
            [74.30, 31.51],
            [74.30, 31.50],
        ]
    ],
}


def test_soil_preset_lookup():
    """Verify FAO-56 Table 19 soil parameters."""
    loam = get_soil_preset("loam")
    assert loam.taw_mm_per_m == 160.0
    assert loam.field_capacity == 0.28
    assert loam.wilting_point == 0.12

    sand = get_soil_preset("sand")
    assert sand.taw_mm_per_m == 80.0

    clay = get_soil_preset("clay")
    assert clay.taw_mm_per_m == 160.0


def test_calculate_effective_rainfall_usda_scs():
    """Verify USDA SCS effective rainfall calculation breakpoints."""
    # Small rain (evaporates/intercepts)
    assert calculate_effective_rainfall(5.0) == 0.0
    assert calculate_effective_rainfall(8.3) == 0.0

    # Moderate rain: Peff = 0.8 * P - 5.0
    # For P = 25 mm -> 0.8 * 25 - 5 = 15.0 mm
    assert calculate_effective_rainfall(25.0) == 15.0
    # For P = 50 mm -> 0.8 * 50 - 5 = 35.0 mm
    assert calculate_effective_rainfall(50.0) == 35.0

    # Heavy rain (> 75 mm): Peff = 0.6 * P + 10.0
    # For P = 100 mm -> 0.6 * 100 + 10 = 70.0 mm
    assert calculate_effective_rainfall(100.0) == 70.0


def test_dynamic_root_depth():
    """Verify root depth progression with crop development."""
    assert get_dynamic_root_depth(0, 120, zr_min=0.3, zr_max=1.2) == 0.3
    # Mid development (day 60 of 120) -> 0.3 + 0.9 * 0.5 = 0.75 m
    assert get_dynamic_root_depth(60, 120, zr_min=0.3, zr_max=1.2) == 0.75
    # Full maturity (day 120) -> 1.2 m
    assert get_dynamic_root_depth(120, 120, zr_min=0.3, zr_max=1.2) == 1.2
    # Post maturity clamping
    assert get_dynamic_root_depth(150, 120, zr_min=0.3, zr_max=1.2) == 1.2


@pytest.mark.asyncio
async def test_irrigation_plan_calculation_and_event_rebalance(client):
    """Test full daily water balance, depletion calculation, and event rebalancing."""
    test_engine = client._transport.app.state.test_engine
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    user = User(
        name="Irrigation Agronomist",
        email="agronomist@agriscope.local",
        password_hash="pw",
        role=UserRole.PRO.value,
        plan="pro",
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )

    crop = Crop(
        name="Test Maize",
        kc_ini=0.3,
        kc_mid=1.2,
        kc_end=0.35,
    )

    async with factory() as s:
        s.add(user)
        s.add(crop)
        await s.commit()
        await s.refresh(user)
        await s.refresh(crop)

        # Seed crop stages
        stages = [
            CropStage(crop_id=crop.id, stage_name="initial", duration_days=20),
            CropStage(crop_id=crop.id, stage_name="development", duration_days=30),
            CropStage(crop_id=crop.id, stage_name="mid", duration_days=40),
            CropStage(crop_id=crop.id, stage_name="late", duration_days=30),
        ]
        s.add_all(stages)

        field_service = FieldService(s)
        field = await field_service.create_field(
            user=user,
            name="Corn Plot Beta",
            geometry=SAMPLE_POLYGON,
            crop_id=crop.id,
            planting_date=date.today() - timedelta(days=20),
        )

        irrigation_service = IrrigationService(s)

        # 1. Initial Plan before irrigation events
        plan = await irrigation_service.calculate_field_irrigation_plan(
            field_id=field.id,
            user=user,
            soil_type="loam",
            mad_fraction=0.5,
            forecast_days=7,
        )

        assert plan.field_name == "Corn Plot Beta"
        assert plan.crop_name == "Test Maize"
        assert len(plan.daily_balance) > 0
        assert len(plan.schedule) == 8  # today + 7 days forecast
        assert plan.summary.total_etc_mm > 0

        initial_depletion = plan.summary.current_depletion_mm

        # 2. Log an applied irrigation event today
        event_payload = IrrigationEventCreate(
            event_date=date.today(),
            water_applied_mm=30.0,
            method="drip",
            notes="Morning drip cycle",
        )
        created_event = await irrigation_service.create_irrigation_event(
            field_id=field.id,
            user=user,
            payload=event_payload,
        )
        assert created_event.water_applied_mm == 30.0

        # 3. Recalculate plan and verify depletion reduced / re-balanced
        updated_plan = await irrigation_service.calculate_field_irrigation_plan(
            field_id=field.id,
            user=user,
            soil_type="loam",
            mad_fraction=0.5,
        )

        assert len(updated_plan.events) == 1
        assert updated_plan.summary.total_irrigation_applied_mm == 30.0
        # Depletion should be significantly less or zeroed out
        assert updated_plan.summary.current_depletion_mm <= initial_depletion
