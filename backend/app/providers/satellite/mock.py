"""Deterministic mock satellite provider simulating seasonal canopy dynamics."""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Dict, List

from app.providers.satellite.base import SatelliteObservation, SatelliteProvider


class MockSatelliteProvider(SatelliteProvider):
    """Generates realistic seasonal curves for NDVI, EVI, and NDWI."""

    @property
    def provider_id(self) -> str:
        return "mock"

    def _compute_point_centroid(self, geometry: Dict[str, Any]) -> tuple[float, float]:
        """Extract approximate centroid from GeoJSON coordinates."""
        coords = geometry.get("coordinates", [])
        if not coords:
            return 31.5, 74.3
        ring = coords[0] if isinstance(coords[0], list) and isinstance(coords[0][0], list) else coords
        if ring and isinstance(ring[0], list):
            lons = [p[0] for p in ring if len(p) >= 2]
            lats = [p[1] for p in ring if len(p) >= 2]
            return sum(lats) / len(lats), sum(lons) / len(lons)
        return 31.5, 74.3

    def _generate_observation(self, lat: float, lon: float, d: date) -> SatelliteObservation:
        doy = d.timetuple().tm_yday

        # Gaussian or bell curve simulating vegetative growth cycle peaking around summer/autumn
        # Standard double-sigmoid or bell curve
        peak_doy = 210  # Late July
        width = 65.0
        exponent = -((doy - peak_doy) ** 2) / (2 * (width ** 2))
        bell = math.exp(exponent)

        # Baseline bare soil NDVI = 0.18, peak canopy = 0.82
        ndvi = round(0.18 + 0.64 * bell, 3)

        # EVI follows NDVI with slightly lower magnitude and higher dynamic range in dense canopy
        evi = round(max(0.10, min(0.70, 0.12 + 0.50 * bell)), 3)

        # NDWI (Gao 1996: (NIR - SWIR)/(NIR + SWIR)): canopy water content correlates with greenness
        ndwi = round(max(-0.20, min(0.45, -0.15 + 0.55 * bell)), 3)

        # Simulated cloud cover fluctuation
        cloud = round(5.0 + 15.0 * abs(math.sin(doy * 0.1)), 1)

        # MODIS MOD16 ET benchmark (approximate 8-day mean converted to daily mm)
        modis_et = round(max(1.2, 5.2 * bell + 0.8), 2)

        return SatelliteObservation(
            observation_date=d.isoformat(),
            ndvi=ndvi,
            evi=evi,
            ndwi=ndwi,
            cloud_cover_pct=cloud,
            provider_name=self.provider_id,
            scene_id=f"S2A_MSIL2A_{d.strftime('%Y%m%d')}_T42R_MOCK",
            satellite="Sentinel-2 L2A (Synthetic)",
            modis_et_mm=modis_et,
            is_cloud_masked=True,
            metadata={"cloud_filtered": True, "source": "deterministic_synthetic"},
        )

    async def get_time_series(
        self,
        geometry: Dict[str, Any],
        start_date: date,
        end_date: date,
        cloud_cover_max: float = 30.0,
    ) -> List[SatelliteObservation]:
        lat, lon = self._compute_point_centroid(geometry)
        curr = start_date
        records: List[SatelliteObservation] = []
        # Sentinel-2 revisit period ~ 5 days
        step_days = 5
        while curr <= end_date:
            obs = self._generate_observation(lat, lon, curr)
            if obs.cloud_cover_pct <= cloud_cover_max:
                records.append(obs)
            curr += timedelta(days=step_days)

        if not records and start_date <= end_date:
            # Always ensure at least one observation is yielded
            records.append(self._generate_observation(lat, lon, end_date))

        return records
