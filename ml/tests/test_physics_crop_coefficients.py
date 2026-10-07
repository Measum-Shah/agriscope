import pytest
from agriscope_ml.physics.crop_coefficients import (
    CropStageKc,
    CropStageLengths,
    calculate_etc,
    interpolate_kc_stage,
    ndvi_to_kc,
)


def test_kc_piecewise_linear_stage_interpolation():
    """Verify FAO-56 4-stage piecewise curve interpolation."""
    # Wheat in semiarid South Asia (140-day cycle: 20-30-60-30 days)
    lengths = CropStageLengths(
        initial=20,
        development=30,
        mid_season=60,
        late_season=30,
    )
    kc_values = CropStageKc(
        kc_ini=0.35,
        kc_mid=1.15,
        kc_end=0.25,
    )

    # Day 10 (Initial stage)
    kc_10, stage_10 = interpolate_kc_stage(10, lengths, kc_values)
    assert kc_10 == 0.35
    assert stage_10 == "initial"

    # Day 35 (Development stage halfway through L_dev = 20 + 15 = 35)
    # Expected: 0.35 + (15/30) * (1.15 - 0.35) = 0.35 + 0.40 = 0.75
    kc_35, stage_35 = interpolate_kc_stage(35, lengths, kc_values)
    assert kc_35 == pytest.approx(0.75, abs=0.01)
    assert stage_35 == "development"

    # Day 80 (Mid-season stage: 50 to 110 days)
    kc_80, stage_80 = interpolate_kc_stage(80, lengths, kc_values)
    assert kc_80 == 1.15
    assert stage_80 == "mid_season"

    # Day 125 (Late season halfway through: 110 + 15 = 125)
    # Expected: 1.15 + (15/30) * (0.25 - 1.15) = 1.15 - 0.45 = 0.70
    kc_125, stage_125 = interpolate_kc_stage(125, lengths, kc_values)
    assert kc_125 == pytest.approx(0.70, abs=0.01)
    assert stage_125 == "late_season"

    # Day 160 (Post-harvest)
    kc_post, stage_post = interpolate_kc_stage(160, lengths, kc_values)
    assert kc_post == 0.25
    assert stage_post == "post_harvest"


def test_ndvi_to_kc_relations_and_physical_caps():
    """Verify satellite NDVI to Kc conversion and boundaries."""
    # Bare soil (NDVI <= 0.15) -> min Kc baseline (0.15)
    assert ndvi_to_kc(0.10) == 0.15
    assert ndvi_to_kc(0.15) == 0.15

    # Full dense canopy (NDVI >= 0.85) -> peak Kc (1.25)
    assert ndvi_to_kc(0.85) == 1.25
    assert ndvi_to_kc(0.95) == 1.25

    # Intermediate canopy cover (NDVI = 0.50)
    # Scale = (0.50 - 0.15) / (0.85 - 0.15) = 0.35 / 0.70 = 0.5
    # Kc = 0.15 + 0.5 * (1.25 - 0.15) = 0.15 + 0.55 = 0.70
    assert ndvi_to_kc(0.50) == pytest.approx(0.70, abs=0.01)

    # Physical clamping bounds
    assert ndvi_to_kc(-0.5) >= 0.15
    assert ndvi_to_kc(1.5) <= 1.35


def test_calculate_etc():
    """Verify crop ET calculation ETc = Kc * ET0."""
    etc = calculate_etc(et0=5.0, kc=1.15)
    assert etc == pytest.approx(5.75, abs=0.01)

    # Zero ET0 edge case
    assert calculate_etc(et0=0.0, kc=1.2) == 0.0
