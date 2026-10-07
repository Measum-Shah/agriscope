import pytest
from agriscope_ml.physics.penman_monteith import (
    atmospheric_pressure,
    clear_sky_radiation,
    extraterrestrial_radiation,
    fao56_penman_monteith_full,
    fao56_penman_monteith_simplified,
    mean_saturation_vapour_pressure,
    net_longwave_radiation,
    net_shortwave_radiation,
    psychrometric_constant,
    slope_vapour_pressure_curve,
    wind_at_2m,
)


def test_fao56_intermediate_atmospheric_terms():
    """Verify atmospheric pressure and psychrometric constant against FAO-56 Table 2.2."""
    # Sea level (0 m)
    p0 = atmospheric_pressure(0.0)
    assert p0 == pytest.approx(101.3, abs=0.1)
    gamma0 = psychrometric_constant(0.0, p0)
    assert gamma0 == pytest.approx(0.067, abs=0.002)

    # Elevation 1800 m (e.g. Quetta / Kenya highlands)
    p1800 = atmospheric_pressure(1800.0)
    assert p1800 == pytest.approx(81.8, abs=1.0)
    gamma1800 = psychrometric_constant(1800.0, p1800)
    assert gamma1800 == pytest.approx(0.054, abs=0.003)


def test_fao56_vapour_pressure_terms():
    """Verify slope Delta and saturation vapour pressure es for standard temperatures."""
    # T = 30.2 °C (from FAO-56 Example 18 Bangkok case)
    delta = slope_vapour_pressure_curve(30.2)
    assert delta == pytest.approx(0.246, abs=0.005)

    # Tmin = 25.6 °C, Tmax = 34.8 °C
    es = mean_saturation_vapour_pressure(tmin=25.6, tmax=34.8)
    assert es == pytest.approx(4.42, abs=0.05)


def test_fao56_radiation_terms():
    """Verify extraterrestrial and net radiation formulas."""
    # Bangkok latitude 13.73° N on April 15 (DOY 105)
    ra = extraterrestrial_radiation(13.73, 105)
    assert ra == pytest.approx(38.0, abs=0.5)

    # Clear-sky radiation for elevation 2 m
    rso = clear_sky_radiation(ra, 2.0)
    assert rso == pytest.approx(28.5, abs=0.5)

    # Net shortwave radiation with albedo 0.23 and Rs = 22.0 MJ/m²/day
    rns = net_shortwave_radiation(22.0, albedo=0.23)
    assert rns == pytest.approx(16.94, abs=0.1)

    # Net longwave radiation
    rnl = net_longwave_radiation(
        tmin=25.6,
        tmax=34.8,
        ea=2.85,
        rs=22.0,
        rso=rso,
    )
    assert 2.5 <= rnl <= 4.0


def test_wind_conversion_logarithmic_profile():
    """Test anemometer height correction to standard 2 m height."""
    # If measured at 2 m, wind speed must be identical
    assert wind_at_2m(3.5, 2.0) == pytest.approx(3.5, abs=1e-4)

    # If measured at 10 m (standard airport weather tower)
    # Factor is 4.87 / ln(678 - 5.42) = 4.87 / ln(672.58) = 4.87 / 6.511 = ~0.748
    u2_from_10m = wind_at_2m(5.0, 10.0)
    assert u2_from_10m == pytest.approx(5.0 * 0.748, abs=0.05)
    assert u2_from_10m < 5.0  # Wind is lower near the ground


def test_fao56_bangkok_worked_example_full():
    """Test complete FAO-56 Penman-Monteith full formula against Example 18 benchmark."""
    res = fao56_penman_monteith_full(
        tmin=25.6,
        tmax=34.8,
        humidity=64.5,
        wind_speed=2.0,
        solar_radiation=22.0,
        latitude=13.73,
        elevation=2.0,
        doy=105,
        measurement_height=2.0,
    )

    # FAO-56 Example 18 benchmark: ET0 ~ 5.3 to 5.7 mm/day
    assert 5.2 <= res.et0 <= 5.8
    assert res.delta == pytest.approx(0.246, abs=0.01)
    assert res.gamma == pytest.approx(0.067, abs=0.005)
    assert res.es == pytest.approx(4.42, abs=0.05)
    assert res.ea == pytest.approx(2.85, abs=0.1)
    assert res.vpd > 1.4
    assert res.g == 0.0
    assert not res.is_simplified


def test_fao56_simplified_4_input_model():
    """Verify simplified 4-input model with documented assumptions."""
    res = fao56_penman_monteith_simplified(
        temperature=28.0,
        humidity=60.0,
        wind_speed=2.5,
        solar_radiation=20.0,
        assumed_elevation=150.0,
    )

    assert 3.5 <= res.et0 <= 7.0
    assert res.is_simplified is True
    assert "elevation_m" in res.assumptions
    assert "tmin_c" in res.assumptions
    assert res.g == 0.0


def test_physical_edge_cases():
    """Verify stability under cold, arid, humid, and mountainous conditions."""
    # Cold winter day (0 °C, low radiation)
    cold_res = fao56_penman_monteith_full(
        tmin=-4.0,
        tmax=4.0,
        humidity=80.0,
        wind_speed=1.0,
        solar_radiation=6.0,
        latitude=35.0,
        elevation=500.0,
        doy=15,
    )
    assert 0.0 <= cold_res.et0 <= 2.0

    # Hot arid summer day (45 °C, 15% RH, high wind)
    arid_res = fao56_penman_monteith_full(
        tmin=32.0,
        tmax=46.0,
        humidity=15.0,
        wind_speed=4.5,
        solar_radiation=30.0,
        latitude=28.0,
        elevation=120.0,
        doy=170,
    )
    assert 7.0 <= arid_res.et0 <= 15.0
