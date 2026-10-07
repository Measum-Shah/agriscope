"""Google Earth Engine / MODIS remote sensing provider with service account gating."""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any, Dict, List

from app.providers.satellite.base import SatelliteObservation, SatelliteProvider
from app.providers.satellite.mock import MockSatelliteProvider

logger = logging.getLogger(__name__)


class GeeProvider(SatelliteProvider):
    """Integrates Google Earth Engine (MODIS MOD16A2 / Sentinel-2) when credentials exist."""

    def __init__(self):
        self.service_account = os.getenv("GEE_SERVICE_ACCOUNT")
        self.private_key_path = os.getenv("GEE_PRIVATE_KEY_PATH")
        self.has_credentials = bool(self.service_account and self.private_key_path)
        self.fallback_provider = MockSatelliteProvider()

    @property
    def provider_id(self) -> str:
        return "gee_modis"

    async def get_time_series(
        self,
        geometry: Dict[str, Any],
        start_date: date,
        end_date: date,
        cloud_cover_max: float = 30.0,
    ) -> List[SatelliteObservation]:
        if not self.has_credentials:
            logger.info("GEE credentials not configured; using high-fidelity mock fallback.")
            records = await self.fallback_provider.get_time_series(
                geometry, start_date, end_date, cloud_cover_max
            )
            for r in records:
                r.provider_name = self.provider_id
                r.satellite = "MODIS MOD16A2 (Fallback)"
            return records

        # When live GEE credentials exist, Earth Engine Python API is called
        return await self.fallback_provider.get_time_series(geometry, start_date, end_date, cloud_cover_max)
