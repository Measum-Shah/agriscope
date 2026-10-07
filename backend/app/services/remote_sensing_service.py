"""Remote sensing domain service executing multi-temporal satellite analyses and storing observations."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.crop import Crop, CropStage
from app.models.field import Field
from app.models.field_observation import FieldObservation
from app.models.user import User
from app.providers.satellite.base import SatelliteObservation, SatelliteProvider
from app.providers.satellite.mock import MockSatelliteProvider
from app.providers.satellite.stac_sentinel import StacSentinelProvider
from app.providers.weather.mock import MockWeatherProvider
from app.providers.weather.open_meteo import OpenMeteoProvider
from agriscope_ml.physics.crop_coefficients import CropStageKc, CropStageLengths, interpolate_kc_stage, ndvi_to_kc, calculate_etc


class RemoteSensingService:
    """Manages satellite scene retrieval, cloud filtering, Kc calculations, and observation storage."""

    def __init__(
        self,
        session: AsyncSession,
        satellite_provider: Optional[SatelliteProvider] = None,
    ):
        self.session = session
        self.provider = satellite_provider or StacSentinelProvider()
        self.mock_provider = MockSatelliteProvider()
        self.weather_provider = OpenMeteoProvider()
        self.mock_weather = MockWeatherProvider()

    async def analyze_field(
        self,
        user: User,
        field_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        cloud_cover_max: float = 30.0,
    ) -> Dict[str, Any]:
        """Fetch satellite imagery for field polygon, derive NDVI/EVI/NDWI, compute Kc and ETc, and persist."""
        stmt = (
            select(Field)
            .where(Field.id == field_id, Field.user_id == user.id)
        )
        res = await self.session.execute(stmt)
        field_obj = res.scalar_one_or_none()
        if not field_obj:
            raise NotFoundException(detail="Field not found.")

        # Default analysis window: last 60 days
        end_d = end_date or date.today()
        start_d = start_date or (end_d - timedelta(days=60))

        # Convert PostGIS geometry to GeoJSON dict
        shapely_geom = to_shape(field_obj.geometry)
        geom_dict = mapping(shapely_geom)
        centroid = shapely_geom.centroid

        # 1. Fetch satellite observations
        is_fallback = False
        try:
            observations = await self.provider.get_time_series(
                geometry=geom_dict,
                start_date=start_d,
                end_date=end_d,
                cloud_cover_max=cloud_cover_max,
            )
            if not observations:
                raise ValueError("No cloud-free STAC scenes found")
        except Exception as e:
            logger.warning(f"STAC satellite retrieval failed ({e}), using mock satellite provider.")
            observations = await self.mock_provider.get_time_series(
                geometry=geom_dict,
                start_date=start_d,
                end_date=end_d,
                cloud_cover_max=cloud_cover_max,
            )
            is_fallback = True

        # 2. Query weather ET0 for each observation date to compute ETc
        results = []
        for obs in observations:
            obs_d = date.fromisoformat(obs.observation_date)

            # Weather ET0
            try:
                weather = await self.weather_provider.get_daily_inputs(centroid.y, centroid.x, obs_d)
                et0 = weather.et0_provider or 4.0
            except Exception:
                weather = await self.mock_weather.get_daily_inputs(centroid.y, centroid.x, obs_d)
                et0 = weather.et0_provider or 4.0

            # Derive Kc from satellite NDVI
            kc_ndvi = ndvi_to_kc(obs.ndvi)
            etc = calculate_etc(et0=et0, kc=kc_ndvi)

            # Persist observation in field_observations table
            # Check if observation for this date already exists
            existing_stmt = select(FieldObservation).where(
                FieldObservation.field_id == field_obj.id,
                FieldObservation.observation_date == obs_d,
            )
            res_exist = await self.session.execute(existing_stmt)
            existing_obs = res_exist.scalar_one_or_none()

            if existing_obs:
                existing_obs.ndvi = obs.ndvi
                existing_obs.evi = obs.evi
                existing_obs.ndwi = obs.ndwi
                existing_obs.cloud_cover_pct = obs.cloud_cover_pct
                existing_obs.et0 = round(et0, 2)
                existing_obs.kc = round(kc_ndvi, 2)
                existing_obs.etc = round(etc, 2)
                existing_obs.rain_mm = 0.0
            else:
                new_obs = FieldObservation(
                    field_id=field_obj.id,
                    observation_date=obs_d,
                    ndvi=obs.ndvi,
                    evi=obs.evi,
                    ndwi=obs.ndwi,
                    cloud_cover_pct=obs.cloud_cover_pct,
                    et0=round(et0, 2),
                    kc=round(kc_ndvi, 2),
                    etc=round(etc, 2),
                    rain_mm=0.0,
                )
                self.session.add(new_obs)

            results.append(
                {
                    "date": obs.observation_date,
                    "ndvi": obs.ndvi,
                    "evi": obs.evi,
                    "ndwi": obs.ndwi,
                    "cloud_cover_pct": obs.cloud_cover_pct,
                    "kc": round(kc_ndvi, 2),
                    "et0": round(et0, 2),
                    "etc": round(etc, 2),
                    "satellite": obs.satellite,
                    "scene_id": obs.scene_id,
                    "modis_et_mm": obs.modis_et_mm,
                }
            )

        await self.session.commit()

        return {
            "field_id": str(field_obj.id),
            "field_name": field_obj.name,
            "observations_count": len(results),
            "provider": self.mock_provider.provider_id if is_fallback else self.provider.provider_id,
            "is_fallback": is_fallback,
            "series": sorted(results, key=lambda x: x["date"]),
        }

    async def get_field_observations(
        self,
        user: User,
        field_id: uuid.UUID,
    ) -> List[FieldObservation]:
        """Query historical observation series stored in the database for a field."""
        stmt = (
            select(FieldObservation)
            .join(Field, FieldObservation.field_id == Field.id)
            .where(Field.id == field_id, Field.user_id == user.id)
            .order_by(FieldObservation.observation_date.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
