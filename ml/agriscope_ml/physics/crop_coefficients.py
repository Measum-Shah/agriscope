"""FAO-56 Crop coefficient (Kc) calculations and remote-sensing NDVI conversion.

References:
    - FAO-56 Chapter 6: Calculation of the crop coefficient (Kc).
    - Choudhury, B. J., et al. (1994). Relations between evaporation coefficients
      and vegetation indices. Remote Sensing of Environment.
    - Allen, R. G., et al. (2007). Satellite-based energy balance for mapping
      evapotranspiration with internalized calibration (METRIC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class CropStageLengths:
    """Lengths of the four FAO-56 growth stages in days."""

    initial: int  # L_ini
    development: int  # L_dev
    mid_season: int  # L_mid
    late_season: int  # L_late

    @property
    def total_growing_days(self) -> int:
        return self.initial + self.development + self.mid_season + self.late_season


@dataclass
class CropStageKc:
    """FAO-56 tabulated crop coefficients for growth stages."""

    kc_ini: float  # Kc at initial stage
    kc_mid: float  # Kc at peak mid-season stage
    kc_end: float  # Kc at harvest/end of season


def interpolate_kc_stage(
    days_after_planting: int,
    stage_lengths: CropStageLengths,
    stage_kc: CropStageKc,
) -> Tuple[float, str]:
    """Calculate the FAO-56 piecewise linear crop coefficient Kc for a given day in the season.

    Four Growth Stages:
    1. Initial Stage (0 <= t <= L_ini):
       Kc(t) = Kc_ini
    2. Crop Development Stage (L_ini < t <= L_ini + L_dev):
       Linear increase from Kc_ini to Kc_mid:
       Kc(t) = Kc_ini + ((t - L_ini) / L_dev) * (Kc_mid - Kc_ini)
    3. Mid-Season Stage (L_ini + L_dev < t <= L_ini + L_dev + L_mid):
       Kc(t) = Kc_mid
    4. Late Season Stage (L_ini + L_dev + L_mid < t <= total_days):
       Linear decrease from Kc_mid to Kc_end:
       Kc(t) = Kc_mid + ((t - (L_ini + L_dev + L_mid)) / L_late) * (Kc_end - Kc_mid)

    Args:
        days_after_planting: Number of days elapsed since planting date (>= 0).
        stage_lengths: Stage durations in days.
        stage_kc: Standard stage Kc values.

    Returns:
        Tuple of (interpolated_kc, current_stage_name).
    """
    t = max(0, days_after_planting)
    l_ini = stage_lengths.initial
    l_dev = stage_lengths.development
    l_mid = stage_lengths.mid_season
    l_late = stage_lengths.late_season

    t1 = l_ini
    t2 = l_ini + l_dev
    t3 = l_ini + l_dev + l_mid
    t4 = stage_lengths.total_growing_days

    if t <= t1:
        return stage_kc.kc_ini, "initial"

    if t <= t2:
        if l_dev > 0:
            fraction = (t - t1) / float(l_dev)
            kc = stage_kc.kc_ini + fraction * (stage_kc.kc_mid - stage_kc.kc_ini)
        else:
            kc = stage_kc.kc_mid
        return round(kc, 3), "development"

    if t <= t3:
        return stage_kc.kc_mid, "mid_season"

    if t <= t4:
        if l_late > 0:
            fraction = (t - t3) / float(l_late)
            kc = stage_kc.kc_mid + fraction * (stage_kc.kc_end - stage_kc.kc_mid)
        else:
            kc = stage_kc.kc_end
        return round(kc, 3), "late_season"

    # Post harvest
    return stage_kc.kc_end, "post_harvest"


def ndvi_to_kc(
    ndvi: float,
    kc_min: float = 0.15,
    kc_max: float = 1.25,
    ndvi_min: float = 0.15,
    ndvi_max: float = 0.85,
) -> float:
    """Derive crop coefficient Kc from satellite-derived NDVI.

    Formulation:
    Standard satellite vegetation index scaling based on dense canopy fractional cover:
        Kc = Kc_min + (Kc_max - Kc_min) * ((NDVI - NDVI_min) / (NDVI_max - NDVI_min))

    Physical boundaries:
    - Minimum base soil evaporation limit = 0.15
    - Maximum transpiration potential limit = 1.35
    - Clamped to [kc_min, kc_max] range.

    Args:
        ndvi: Normalized Difference Vegetation Index value (-1.0 to 1.0).
        kc_min: Baseline bare-soil crop coefficient (default 0.15).
        kc_max: Full canopy cover crop coefficient (default 1.25).
        ndvi_min: NDVI value representing bare soil (default 0.15).
        ndvi_max: NDVI value representing full dense canopy (default 0.85).

    Returns:
        Estimated crop coefficient Kc clamped within physical boundaries.
    """
    if ndvi <= ndvi_min:
        return kc_min

    if ndvi >= ndvi_max:
        return min(kc_max, 1.35)

    scale = (ndvi - ndvi_min) / (ndvi_max - ndvi_min)
    kc_val = kc_min + scale * (kc_max - kc_min)
    return round(max(0.15, min(1.35, kc_val)), 3)


def calculate_etc(et0: float, kc: float) -> float:
    """Calculate crop evapotranspiration under standard conditions ETc [mm / day].

    FAO-56 Eq. 58:
        ETc = Kc * ET0

    Args:
        et0: Reference evapotranspiration [mm/day].
        kc: Crop coefficient.

    Returns:
        Crop evapotranspiration [mm/day].
    """
    return round(max(0.0, et0 * kc), 3)
