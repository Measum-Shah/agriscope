"""Deterministic synthetic dataset generator for offline fallback and stress testing.

Adheres strictly to AgriScope rule:
All synthetic records are stamped with `provenance="synthetic"` and `is_synthetic=True`.
Never present synthetic data as real.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from ..physics.penman_monteith import fao56_penman_monteith_full


def generate_synthetic_et_dataset(
    num_samples: int = 5000,
    seed: int = 42,
    noise_std: float = 0.03,  # ~3% Gaussian observation noise
    location_names: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Generate physically-consistent meteorological samples with FAO-56 Penman-Monteith targets.

    Args:
        num_samples: Number of rows to generate.
        seed: Random seed for exact reproducibility.
        noise_std: Fractional standard deviation of observation noise (e.g. 0.03 = 3%).
        location_names: Optional list of location labels to cycle.

    Returns:
        DataFrame with physical features, FAO-56 ET target, and provenance flags.
    """
    rng = np.random.default_rng(seed)

    # 1. Sample physical coordinates & calendar
    # Latitudes focused in agricultural zones (-45° to +50°)
    latitudes = rng.uniform(-45.0, 50.0, size=num_samples)
    # Longitudes (-180° to +180°)
    longitudes = rng.uniform(-180.0, 180.0, size=num_samples)
    # Agricultural elevations (0 to 1800 m)
    elevations = rng.uniform(5.0, 1500.0, size=num_samples)
    # Day of year (1 to 365)
    doys = rng.integers(1, 366, size=num_samples)

    # 2. Sample physical meteorological ranges:
    # Mean temperature (-5 to 45 °C)
    temperatures = rng.uniform(-5.0, 42.0, size=num_samples)
    # Diurnal temperature swing (3 to 14 °C)
    diurnal_half = rng.uniform(2.5, 7.5, size=num_samples)
    tmins = temperatures - diurnal_half
    tmaxs = temperatures + diurnal_half

    # Relative humidity (10% to 95%)
    humidities = rng.uniform(12.0, 95.0, size=num_samples)
    # Wind speed at 2 m (0.2 to 15.0 m/s)
    wind_speeds = rng.uniform(0.3, 12.0, size=num_samples)
    # Solar radiation (3.0 to 32.0 MJ/m²/day)
    solar_radiations = rng.uniform(3.5, 32.0, size=num_samples)

    # Optional precipitation (0 to 60 mm) with ~70% dry days
    precip_prob = rng.random(size=num_samples)
    precipitations = np.where(
        precip_prob > 0.70,
        rng.exponential(scale=12.0, size=num_samples),
        0.0,
    )

    default_locations = [
        "Synthetic_Indus_Basin",
        "Synthetic_Punjab_Plains",
        "Synthetic_Sindh_Canal",
        "Synthetic_Deccan_Plateau",
        "Synthetic_Mekong_Delta",
        "Synthetic_Nile_Valley",
        "Synthetic_California_Valley",
        "Synthetic_Po_Valley",
    ]
    loc_pool = location_names or default_locations

    rows = []
    for i in range(num_samples):
        lat = float(latitudes[i])
        elev = float(elevations[i])
        doy = int(doys[i])
        t_mean = float(temperatures[i])
        t_min = float(tmins[i])
        t_max = float(tmaxs[i])
        rh = float(humidities[i])
        ws = float(wind_speeds[i])
        rs = float(solar_radiations[i])
        pr = float(precipitations[i])

        # Compute exact FAO-56 Penman-Monteith physics
        pm = fao56_penman_monteith_full(
            tmin=t_min,
            tmax=t_max,
            humidity=rh,
            wind_speed=ws,
            solar_radiation=rs,
            latitude=lat,
            elevation=elev,
            doy=doy,
        )

        # Apply ~3% observational noise
        noise_factor = 1.0 + rng.normal(0.0, noise_std)
        noisy_et = max(0.05, round(pm.et0 * noise_factor, 3))

        loc_label = loc_pool[i % len(loc_pool)]

        rows.append(
            {
                "location_name": loc_label,
                "latitude": round(lat, 4),
                "longitude": round(float(longitudes[i]), 4),
                "elevation": round(elev, 1),
                "doy": doy,
                "temperature": round(t_mean, 2),
                "tmin": round(t_min, 2),
                "tmax": round(t_max, 2),
                "humidity": round(rh, 2),
                "wind_speed": round(ws, 2),
                "solar_radiation": round(rs, 2),
                "precipitation": round(pr, 2),
                "et": noisy_et,
                "et_ground_truth_physics": pm.et0,
                "vpd": pm.vpd,
                "net_radiation": pm.rn,
                "provenance": "synthetic",
                "is_synthetic": True,
            }
        )

    return pd.DataFrame(rows)
