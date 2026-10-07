"""Abstract base interfaces and data structures for satellite remote sensing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class SatelliteObservation:
    """Standardized vegetation index and scene observation from satellite imagery."""

    observation_date: str  # YYYY-MM-DD
    ndvi: float  # Normalized Difference Vegetation Index (-1 to 1)
    evi: float  # Enhanced Vegetation Index (-1 to 1)
    ndwi: float  # Normalized Difference Water Index (-1 to 1)
    cloud_cover_pct: float  # Percentage of cloud cover over scene/polygon (0 to 100)
    provider_name: str = "mock"
    scene_id: Optional[str] = None
    satellite: str = "Sentinel-2"
    modis_et_mm: Optional[float] = None  # MODIS MOD16A2 validation ET if available
    is_cloud_masked: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class SatelliteProvider(ABC):
    """Abstract contract for satellite scene retrieval, cloud masking, and index computation."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this satellite provider."""
        pass

    @abstractmethod
    async def get_time_series(
        self,
        geometry: Dict[str, Any],
        start_date: date,
        end_date: date,
        cloud_cover_max: float = 30.0,
    ) -> List[SatelliteObservation]:
        """Retrieve multi-temporal vegetation indices over polygon geometry."""
        pass
