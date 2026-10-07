"""FAO-56 Penman-Monteith reference evapotranspiration (ET0) formulation.

References:
    Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998).
    Crop evapotranspiration - Guidelines for computing crop water requirements -
    FAO Irrigation and drainage paper 56. Food and Agriculture Organization of the
    United Nations, Rome.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PenmanMonteithResult:
    """Detailed intermediate and final results of FAO-56 Penman-Monteith ET0 calculation."""

    et0: float  # mm / day
    delta: float  # kPa / °C (slope of saturation vapour pressure curve)
    gamma: float  # kPa / °C (psychrometric constant)
    pressure: float  # kPa (atmospheric pressure)
    es: float  # kPa (saturation vapour pressure)
    ea: float  # kPa (actual vapour pressure)
    vpd: float  # kPa (vapour pressure deficit = es - ea)
    rn: float  # MJ / m² / day (net radiation)
    rns: float  # MJ / m² / day (net shortwave radiation)
    rnl: float  # MJ / m² / day (net longwave radiation)
    ra: float  # MJ / m² / day (extraterrestrial radiation)
    rso: float  # MJ / m² / day (clear-sky solar radiation)
    g: float = 0.0  # MJ / m² / day (soil heat flux = 0 for daily)
    u2: float = 2.0  # m / s (wind speed at 2 m)
    radiation_term: float = 0.0  # mm / day (thermal radiative contribution)
    wind_term: float = 0.0  # mm / day (aerodynamic contribution)
    is_simplified: bool = False
    assumptions: Dict[str, Any] = field(default_factory=dict)


def slope_vapour_pressure_curve(temperature: float) -> float:
    """Calculate slope of saturation vapour pressure curve Delta [kPa / °C].

    FAO-56 Eq. 13:
        Delta = 4098 * [0.6108 * exp((17.27 * T) / (T + 237.3))] / (T + 237.3)^2
    """
    t = temperature
    es_t = 0.6108 * math.exp((17.27 * t) / (t + 237.3))
    return (4098.0 * es_t) / ((t + 237.3) ** 2)


def atmospheric_pressure(elevation: float) -> float:
    """Calculate atmospheric pressure P [kPa] at given elevation z [m].

    FAO-56 Eq. 7:
        P = 101.3 * ((293 - 0.0065 * z) / 293)^5.26
    """
    return 101.3 * (((293.0 - 0.0065 * elevation) / 293.0) ** 5.26)


def psychrometric_constant(elevation: float, pressure: Optional[float] = None) -> float:
    """Calculate psychrometric constant gamma [kPa / °C].

    FAO-56 Eq. 8:
        gamma = 0.000665 * P
    """
    p = pressure if pressure is not None else atmospheric_pressure(elevation)
    return 0.000665 * p


def saturation_vapour_pressure_single(temperature: float) -> float:
    """Calculate saturation vapour pressure e°(T) [kPa] at temperature T [°C].

    FAO-56 Eq. 11:
        e°(T) = 0.6108 * exp((17.27 * T) / (T + 237.3))
    """
    return 0.6108 * math.exp((17.27 * temperature) / (temperature + 237.3))


def mean_saturation_vapour_pressure(
    tmin: Optional[float] = None,
    tmax: Optional[float] = None,
    tmean: Optional[float] = None,
) -> float:
    """Calculate mean saturation vapour pressure es [kPa].

    FAO-56 Eq. 12:
        es = (e°(Tmax) + e°(Tmin)) / 2
    If only tmean is available, falls back to e°(tmean).
    """
    if tmin is not None and tmax is not None:
        return (
            saturation_vapour_pressure_single(tmax) + saturation_vapour_pressure_single(tmin)
        ) / 2.0
    if tmean is not None:
        return saturation_vapour_pressure_single(tmean)
    raise ValueError("Either (tmin, tmax) or tmean must be provided.")


def actual_vapour_pressure(
    es: float,
    humidity: float,
    tmin: Optional[float] = None,
    tmax: Optional[float] = None,
    rh_min: Optional[float] = None,
    rh_max: Optional[float] = None,
) -> float:
    """Calculate actual vapour pressure ea [kPa].

    If rh_min and rh_max with tmin and tmax are provided, uses FAO-56 Eq. 17:
        ea = (e°(Tmin) * RHmax/100 + e°(Tmax) * RHmin/100) / 2
    Otherwise uses mean humidity (FAO-56 Eq. 19):
        ea = es * (humidity / 100)
    """
    if rh_min is not None and rh_max is not None and tmin is not None and tmax is not None:
        e_min = saturation_vapour_pressure_single(tmin)
        e_max = saturation_vapour_pressure_single(tmax)
        ea = (e_min * (rh_max / 100.0) + e_max * (rh_min / 100.0)) / 2.0
        return max(0.01, min(ea, es))

    ea = es * (max(0.0, min(100.0, humidity)) / 100.0)
    return max(0.01, min(ea, es))


def wind_at_2m(wind_speed: float, measurement_height: float = 2.0) -> float:
    """Convert wind speed measured at height z [m] to equivalent at 2 m height u2 [m/s].

    FAO-56 Eq. 47:
        u2 = u_z * 4.87 / ln(67.8 * z - 5.42)
    """
    if abs(measurement_height - 2.0) < 1e-4:
        return max(0.0, wind_speed)
    factor = 4.87 / math.log(67.8 * measurement_height - 5.42)
    return max(0.0, wind_speed * factor)


def extraterrestrial_radiation(latitude_deg: float, doy: int) -> float:
    """Calculate daily extraterrestrial radiation Ra [MJ / m² / day].

    FAO-56 Eqs. 21-25:
        Ra = (24 * 60 / pi) * Gsc * dr * [omega_s * sin(phi) * sin(delta) + cos(phi) * cos(delta) * sin(omega_s)]
    where:
        Gsc = 0.0820 MJ / m² / min
        dr = 1 + 0.033 * cos(2 * pi * doy / 365)
        delta = 0.409 * sin(2 * pi * doy / 365 - 1.39)
        omega_s = arccos(-tan(phi) * tan(delta))
    """
    phi = math.radians(latitude_deg)
    dr = 1.0 + 0.033 * math.cos((2.0 * math.pi / 365.0) * doy)
    delta = 0.409 * math.sin(((2.0 * math.pi / 365.0) * doy) - 1.39)

    tan_phi_delta = -math.tan(phi) * math.tan(delta)
    # Sunset hour angle bounded for polar day/night
    if tan_phi_delta > 1.0:
        omega_s = 0.0
    elif tan_phi_delta < -1.0:
        omega_s = math.pi
    else:
        omega_s = math.acos(tan_phi_delta)

    gsc = 0.0820
    term1 = omega_s * math.sin(phi) * math.sin(delta)
    term2 = math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    ra = (24.0 * 60.0 / math.pi) * gsc * dr * (term1 + term2)
    return max(0.0, ra)


def clear_sky_radiation(ra: float, elevation: float) -> float:
    """Calculate clear-sky solar radiation Rso [MJ / m² / day].

    FAO-56 Eq. 37:
        Rso = (0.75 + 2e-5 * z) * Ra
    """
    return (0.75 + 2e-5 * elevation) * ra


def net_shortwave_radiation(solar_radiation: float, albedo: float = 0.23) -> float:
    """Calculate net solar (shortwave) radiation Rns [MJ / m² / day].

    FAO-56 Eq. 38:
        Rns = (1 - albedo) * Rs
    Default albedo for grass reference crop = 0.23.
    """
    return (1.0 - albedo) * max(0.0, solar_radiation)


def net_longwave_radiation(
    tmin: float,
    tmax: float,
    ea: float,
    rs: float,
    rso: float,
) -> float:
    """Calculate net outgoing longwave radiation Rnl [MJ / m² / day].

    FAO-56 Eq. 39:
        Rnl = sigma * [(Tmax_K^4 + Tmin_K^4) / 2] * (0.34 - 0.14 * sqrt(ea)) * (1.35 * (Rs / Rso) - 0.35)
    Stefan-Boltzmann constant sigma = 4.903e-9 MJ / K⁴ / m² / day.
    """
    sigma = 4.903e-9
    tmax_k = tmax + 273.16
    tmin_k = tmin + 273.16
    temp_term = (tmax_k**4 + tmin_k**4) / 2.0

    ea_term = 0.34 - 0.14 * math.sqrt(max(0.0, ea))

    ratio = rs / rso if rso > 0.0 else 0.8
    # Cloudiness fraction clamped between 0.05 and 1.0 (FAO-56 limits)
    cloud_term = max(0.05, min(1.0, 1.35 * min(1.0, max(0.3, ratio)) - 0.35))

    return max(0.0, sigma * temp_term * ea_term * cloud_term)


def fao56_penman_monteith_full(
    tmin: float,
    tmax: float,
    humidity: float,
    wind_speed: float,
    solar_radiation: float,
    latitude: float,
    elevation: float,
    doy: int,
    measurement_height: float = 2.0,
    rh_min: Optional[float] = None,
    rh_max: Optional[float] = None,
) -> PenmanMonteithResult:
    """Full FAO-56 Penman-Monteith ET0 calculation.

    Args:
        tmin: Daily minimum temperature [°C].
        tmax: Daily maximum temperature [°C].
        humidity: Mean relative humidity [%].
        wind_speed: Measured wind speed [m/s].
        solar_radiation: Incoming solar radiation Rs [MJ/m²/day].
        latitude: Station latitude in degrees (-90 to 90).
        elevation: Station elevation above sea level [m].
        doy: Day of year (1-366).
        measurement_height: Anemometer measurement height [m] (default 2.0).
        rh_min: Optional minimum relative humidity [%].
        rh_max: Optional maximum relative humidity [%].

    Returns:
        PenmanMonteithResult dataclass with final et0 and all intermediate terms.
    """
    tmean = (tmax + tmin) / 2.0
    u2 = wind_at_2m(wind_speed, measurement_height)
    delta = slope_vapour_pressure_curve(tmean)
    press = atmospheric_pressure(elevation)
    gamma = psychrometric_constant(elevation, press)

    es = mean_saturation_vapour_pressure(tmin=tmin, tmax=tmax)
    ea = actual_vapour_pressure(es, humidity, tmin=tmin, tmax=tmax, rh_min=rh_min, rh_max=rh_max)
    vpd = max(0.0, es - ea)

    ra = extraterrestrial_radiation(latitude, doy)
    rso = clear_sky_radiation(ra, elevation)
    rns = net_shortwave_radiation(solar_radiation)
    rnl = net_longwave_radiation(tmin, tmax, ea, solar_radiation, rso)
    rn = rns - rnl
    g = 0.0  # Daily soil heat flux is zero

    # FAO-56 Eq. 6
    num_rad = 0.408 * delta * (rn - g)
    num_wind = gamma * (900.0 / (tmean + 273.0)) * u2 * vpd
    denom = delta + gamma * (1.0 + 0.34 * u2)

    et0 = (num_rad + num_wind) / denom
    et0_val = max(0.0, round(et0, 3))

    rad_term = max(0.0, num_rad / denom)
    wind_term = max(0.0, num_wind / denom)

    return PenmanMonteithResult(
        et0=et0_val,
        delta=round(delta, 5),
        gamma=round(gamma, 5),
        pressure=round(press, 2),
        es=round(es, 4),
        ea=round(ea, 4),
        vpd=round(vpd, 4),
        rn=round(rn, 3),
        rns=round(rns, 3),
        rnl=round(rnl, 3),
        ra=round(ra, 3),
        rso=round(rso, 3),
        g=0.0,
        u2=round(u2, 2),
        radiation_term=round(rad_term, 3),
        wind_term=round(wind_term, 3),
        is_simplified=False,
    )


def fao56_penman_monteith_simplified(
    temperature: float,
    humidity: float,
    wind_speed: float,
    solar_radiation: float,
    assumed_elevation: float = 100.0,
    assumed_temp_range: float = 10.0,
) -> PenmanMonteithResult:
    """Simplified 4-input FAO-56 Penman-Monteith calculation.

    Documented Assumptions for Missing Latitude / Elevation / DOY / Tmin / Tmax:
    1. Daily diurnal temperature swing: Tmin = T - 5.0 °C, Tmax = T + 5.0 °C.
    2. Atmospheric pressure evaluated at assumed standard agricultural elevation = 100 m.
    3. Net shortwave radiation: Rns = (1 - 0.23) * Rs = 0.77 * Rs.
    4. Net longwave radiation estimated via FAO-56 Eq. 39 using typical cloudiness
       fraction (Rs / Rso approx 0.75), yielding Rnl approximation based on saturation
       deficit and mean Stefan-Boltzmann blackbody radiation.
    5. Daily soil heat flux G = 0.0.

    Args:
        temperature: Mean air temperature [°C].
        humidity: Mean relative humidity [%].
        wind_speed: Wind speed at 2 m [m/s].
        solar_radiation: Solar radiation Rs [MJ/m²/day].
        assumed_elevation: Elevation fallback [m] (default 100 m).
        assumed_temp_range: Diurnal range fallback [°C] (default 10 °C).

    Returns:
        PenmanMonteithResult with intermediate terms and assumption audit stamps.
    """
    half_range = assumed_temp_range / 2.0
    tmin = temperature - half_range
    tmax = temperature + half_range
    u2 = max(0.0, wind_speed)

    delta = slope_vapour_pressure_curve(temperature)
    press = atmospheric_pressure(assumed_elevation)
    gamma = psychrometric_constant(assumed_elevation, press)

    es = mean_saturation_vapour_pressure(tmin=tmin, tmax=tmax)
    ea = actual_vapour_pressure(es, humidity)
    vpd = max(0.0, es - ea)

    rns = net_shortwave_radiation(solar_radiation)

    # Simplified net longwave radiation using mean temperature & assumed clear sky
    sigma = 4.903e-9
    tmean_k = temperature + 273.16
    temp_term = tmean_k**4
    ea_term = max(0.05, 0.34 - 0.14 * math.sqrt(max(0.0, ea)))
    cloud_term = 0.65  # Typical agricultural mean clear-sky fraction
    rnl = sigma * temp_term * ea_term * cloud_term

    rn = max(0.0, rns - rnl)
    g = 0.0

    num_rad = 0.408 * delta * (rn - g)
    num_wind = gamma * (900.0 / (temperature + 273.0)) * u2 * vpd
    denom = delta + gamma * (1.0 + 0.34 * u2)

    et0 = max(0.0, round((num_rad + num_wind) / denom, 3))
    rad_term = max(0.0, num_rad / denom)
    wind_term = max(0.0, num_wind / denom)

    assumptions = {
        "elevation_m": assumed_elevation,
        "tmin_c": tmin,
        "tmax_c": tmax,
        "assumed_cloudiness_fraction": cloud_term,
        "soil_heat_flux_g": 0.0,
    }

    return PenmanMonteithResult(
        et0=et0,
        delta=round(delta, 5),
        gamma=round(gamma, 5),
        pressure=round(press, 2),
        es=round(es, 4),
        ea=round(ea, 4),
        vpd=round(vpd, 4),
        rn=round(rn, 3),
        rns=round(rns, 3),
        rnl=round(rnl, 3),
        ra=0.0,
        rso=0.0,
        g=0.0,
        u2=round(u2, 2),
        radiation_term=round(rad_term, 3),
        wind_term=round(wind_term, 3),
        is_simplified=True,
        assumptions=assumptions,
    )


def calculate_et0(
    temperature: float,
    humidity: float,
    wind_speed: float,
    solar_radiation: float,
    tmin: Optional[float] = None,
    tmax: Optional[float] = None,
    latitude: Optional[float] = None,
    elevation: Optional[float] = None,
    doy: Optional[int] = None,
    measurement_height: float = 2.0,
    rh_min: Optional[float] = None,
    rh_max: Optional[float] = None,
) -> PenmanMonteithResult:
    """Unified entrypoint for FAO-56 Penman-Monteith ET0.

    Automatically dispatches to full or simplified formula depending on availability
    of geographic coordinates (latitude, elevation, doy).
    """
    if latitude is not None and elevation is not None and doy is not None:
        eff_tmin = tmin if tmin is not None else temperature - 5.0
        eff_tmax = tmax if tmax is not None else temperature + 5.0
        return fao56_penman_monteith_full(
            tmin=eff_tmin,
            tmax=eff_tmax,
            humidity=humidity,
            wind_speed=wind_speed,
            solar_radiation=solar_radiation,
            latitude=latitude,
            elevation=elevation,
            doy=doy,
            measurement_height=measurement_height,
            rh_min=rh_min,
            rh_max=rh_max,
        )
    return fao56_penman_monteith_simplified(
        temperature=temperature,
        humidity=humidity,
        wind_speed=wind_speed,
        solar_radiation=solar_radiation,
        assumed_elevation=elevation if elevation is not None else 100.0,
    )
