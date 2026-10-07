"""Soil physics types and FAO-56 standard soil texture presets.

Reference:
    - FAO-56 Table 19: Available soil water capacity (TAW) for various soil textures.
    - FAO-56 Table 22: Average maximum rooting depths (Zr) and depletion fractions (p).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SoilPreset:
    """Soil physical characteristics according to FAO-56 guidelines."""

    name: str
    description: str
    field_capacity: float  # theta_FC (m3/m3)
    wilting_point: float   # theta_WP (m3/m3)
    taw_mm_per_m: float    # Total Available Water: 1000 * (FC - WP) [mm/m]


# FAO-56 Table 19 Standard Soil Water Characteristics
SOIL_PRESETS: Dict[str, SoilPreset] = {
    "sand": SoilPreset(
        name="Sand",
        description="Coarse textured, very low water holding capacity",
        field_capacity=0.12,
        wilting_point=0.04,
        taw_mm_per_m=80.0,
    ),
    "loamy_sand": SoilPreset(
        name="Loamy Sand",
        description="Coarse-medium textured, low water holding capacity",
        field_capacity=0.16,
        wilting_point=0.06,
        taw_mm_per_m=100.0,
    ),
    "sandy_loam": SoilPreset(
        name="Sandy Loam",
        description="Moderately coarse, medium water holding capacity",
        field_capacity=0.22,
        wilting_point=0.09,
        taw_mm_per_m=130.0,
    ),
    "loam": SoilPreset(
        name="Loam",
        description="Medium textured, optimal water holding capacity",
        field_capacity=0.28,
        wilting_point=0.12,
        taw_mm_per_m=160.0,
    ),
    "silt_loam": SoilPreset(
        name="Silt Loam",
        description="Fine-medium textured, high water holding capacity",
        field_capacity=0.32,
        wilting_point=0.14,
        taw_mm_per_m=180.0,
    ),
    "clay_loam": SoilPreset(
        name="Clay Loam",
        description="Fine textured, good water holding capacity",
        field_capacity=0.34,
        wilting_point=0.17,
        taw_mm_per_m=170.0,
    ),
    "clay": SoilPreset(
        name="Clay",
        description="Very fine textured, high retention but slow infiltration",
        field_capacity=0.38,
        wilting_point=0.22,
        taw_mm_per_m=160.0,
    ),
}


def get_soil_preset(soil_type: str) -> SoilPreset:
    """Get soil preset by key, defaulting to medium loam if unknown."""
    normalized = soil_type.lower().strip().replace(" ", "_").replace("-", "_")
    return SOIL_PRESETS.get(normalized, SOIL_PRESETS["loam"])
