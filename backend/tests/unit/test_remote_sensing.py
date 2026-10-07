"""Unit and integration tests for remote sensing analysis, NDVI/EVI/NDWI formulas, and Kc/ETc."""

from __future__ import annotations

from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field import Field
from app.models.user import User, UserRole, UserStatus
from app.providers.satellite.mock import MockSatelliteProvider
from app.providers.satellite.stac_sentinel import compute_indices_from_bands
from app.services.field_service import FieldService
from app.services.remote_sensing_service import RemoteSensingService
from agriscope_ml.physics.crop_coefficients import ndvi_to_kc, calculate_etc

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [74.3000, 31.5000],
            [74.3100, 31.5000],
            [74.3100, 31.5100],
            [74.3000, 31.5100],
            [74.3000, 31.5000],
        ]
    ],
}


def test_compute_indices_from_bands():
    """Verify spectral index math: NDVI, EVI, NDWI."""
    # Healthy green canopy: low red (0.05), high NIR (0.45), low blue (0.03), medium SWIR (0.15)
    ndvi, evi, ndwi = compute_indices_from_bands(b04_red=0.05, b08_nir=0.45, b02_blue=0.03, b11_swir=0.15)
    # NDVI = (0.45 - 0.05) / (0.45 + 0.05) = 0.40 / 0.50 = 0.80
    assert 0.78 <= ndvi <= 0.82
    assert evi > 0.50
    assert ndwi > 0.40


def test_ndvi_to_kc_and_etc_calculation():
    """Verify NDVI to Kc translation and ETc = Kc * ET0."""
    # Dense canopy NDVI 0.85 -> Kc ~ 1.25
    kc_full = ndvi_to_kc(0.85)
    assert 1.20 <= kc_full <= 1.30

    # Bare soil NDVI 0.15 -> Kc ~ 0.15
    kc_bare = ndvi_to_kc(0.15)
    assert kc_bare == 0.15

    # ETc calculation
    etc = calculate_etc(et0=4.0, kc=kc_full)
    assert round(etc, 2) == round(4.0 * kc_full, 2)


@pytest.mark.asyncio
async def test_mock_satellite_provider_determinism():
    """Verify MockSatelliteProvider generates multi-temporal series."""
    provider = MockSatelliteProvider()
    records = await provider.get_time_series(
        geometry=SAMPLE_POLYGON,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 7, 15),
    )
    assert len(records) >= 5
    for r in records:
        assert 0.15 <= r.ndvi <= 0.90
        assert r.cloud_cover_pct <= 30.0
        assert r.provider_name == "mock"


@pytest.mark.asyncio
async def test_remote_sensing_analysis_pipeline(client):
    """Verify RemoteSensingService analyzes field, populates observations, and computes ETc."""
    test_engine = client._transport.app.state.test_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    user = User(
        name="RS Farmer",
        email="rs_farmer@agriscope.local",
        password_hash="pw",
        role=UserRole.PRO.value,
        plan="pro",
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )
    async with factory() as s:
        s.add(user)
        await s.commit()
        await s.refresh(user)

        field_service = FieldService(s)
        field_obj = await field_service.create_field(user, "Wheat Parcel A", SAMPLE_POLYGON)

        rs_service = RemoteSensingService(s, satellite_provider=MockSatelliteProvider())
        analysis = await rs_service.analyze_field(
            user=user,
            field_id=field_obj.id,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
        )

        assert analysis["field_name"] == "Wheat Parcel A"
        assert analysis["observations_count"] > 0
        assert len(analysis["series"]) > 0

        # Verify observation fields
        first_obs = analysis["series"][0]
        assert "ndvi" in first_obs
        assert "kc" in first_obs
        assert "etc" in first_obs
        assert first_obs["etc"] > 0.0

        # Query DB to ensure observations persisted
        stored_obs = await rs_service.get_field_observations(user, field_obj.id)
        assert len(stored_obs) == analysis["observations_count"]
