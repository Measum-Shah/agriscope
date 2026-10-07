"""Irrigation domain service managing daily soil water balance and scheduling."""

from __future__ import annotations

import math
import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.logging import logger
from app.core.soil import SoilPreset, get_soil_preset
from app.models.crop import Crop, CropStage
from app.models.field import Field
from app.models.field_observation import FieldObservation
from app.models.irrigation_event import IrrigationEvent
from app.models.user import User
from app.providers.weather.base import WeatherProvider
from app.providers.weather.mock import MockWeatherProvider
from app.providers.weather.open_meteo import OpenMeteoProvider
from app.schemas.irrigation import (
    FieldIrrigationPlanResponse,
    IrrigationEventCreate,
    IrrigationEventResponse,
    IrrigationScheduleDay,
    SeasonSummary,
    SoilBalanceDay,
)
from agriscope_ml.physics.crop_coefficients import (
    CropStageKc,
    CropStageLengths,
    calculate_etc,
    interpolate_kc_stage,
)


def calculate_effective_rainfall(rain_mm: float) -> float:
    """Calculate effective rainfall Peff according to USDA Soil Conservation Service method.

    Peff represents the portion of total precipitation stored in the root zone without runoff or deep percolation.
    Formula:
        If Rain <= 8.3 mm: Peff = 0 (interception and surface evaporation losses)
        If Rain <= 75 mm: Peff = 0.8 * Rain - 5.0
        If Rain > 75 mm: Peff = 0.6 * Rain + 10.0
    """
    if rain_mm <= 8.3:
        return 0.0
    if rain_mm <= 75.0:
        return round(max(0.0, 0.8 * rain_mm - 5.0), 2)
    return round(0.6 * rain_mm + 10.0, 2)


def get_dynamic_root_depth(
    days_after_planting: int,
    total_season_days: int,
    zr_min: float = 0.3,
    zr_max: float = 1.2,
) -> float:
    """Calculate effective root zone depth Zr(t) [m] as a function of growth progression."""
    if total_season_days <= 0 or days_after_planting <= 0:
        return zr_min
    fraction = min(1.0, days_after_planting / float(total_season_days))
    # Borg-Grimes root growth model approximation: Zr(t) = Zr_min + (Zr_max - Zr_min) * (0.5 + 0.5 * sin(pi * fraction - pi/2))
    # Or linear progression during development:
    zr = zr_min + (zr_max - zr_min) * fraction
    return round(min(zr_max, max(zr_min, zr)), 2)


class IrrigationService:
    """Manages crop water requirement calculations, soil balance, and irrigation scheduling."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_crop_library(self) -> List[Crop]:
        """Fetch all crops with associated FAO-56 stage lengths."""
        stmt = select(Crop).options(selectinload(Crop.stages)).order_by(Crop.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_crop_detail(self, crop_id: uuid.UUID) -> Crop:
        """Fetch detailed crop metadata and growth stages."""
        stmt = (
            select(Crop)
            .options(selectinload(Crop.stages))
            .where(Crop.id == crop_id)
        )
        result = await self.session.execute(stmt)
        crop = result.scalar_one_or_none()
        if not crop:
            raise NotFoundException(detail="Crop not found.")
        return crop

    async def get_field_events(
        self, field_id: uuid.UUID, user: User
    ) -> List[IrrigationEvent]:
        """Fetch all irrigation events logged for a specific field."""
        await self._get_authorized_field(field_id, user)
        stmt = (
            select(IrrigationEvent)
            .where(IrrigationEvent.field_id == field_id)
            .order_by(IrrigationEvent.event_date.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_irrigation_event(
        self, field_id: uuid.UUID, user: User, payload: IrrigationEventCreate
    ) -> IrrigationEvent:
        """Record an applied irrigation event and commit."""
        field = await self._get_authorized_field(field_id, user)
        event = IrrigationEvent(
            field_id=field.id,
            event_date=payload.event_date,
            water_applied_mm=payload.water_applied_mm,
            method=payload.method,
            notes=payload.notes,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        logger.info(
            "Logged irrigation event",
            field_id=str(field.id),
            date=str(payload.event_date),
            amount_mm=payload.water_applied_mm,
        )
        return event

    async def delete_irrigation_event(
        self, field_id: uuid.UUID, event_id: uuid.UUID, user: User
    ) -> None:
        """Delete an existing irrigation event."""
        await self._get_authorized_field(field_id, user)
        stmt = select(IrrigationEvent).where(
            IrrigationEvent.id == event_id, IrrigationEvent.field_id == field_id
        )
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise NotFoundException(detail="Irrigation event not found.")
        await self.session.delete(event)
        await self.session.commit()

    async def calculate_field_irrigation_plan(
        self,
        field_id: uuid.UUID,
        user: User,
        soil_type: str = "loam",
        mad_fraction: float = 0.5,
        forecast_days: int = 7,
    ) -> FieldIrrigationPlanResponse:
        """Run complete historical and forecast FAO-56 daily root zone soil water balance."""
        field = await self._get_authorized_field(field_id, user)
        soil = get_soil_preset(soil_type)

        # Retrieve events
        events_stmt = (
            select(IrrigationEvent)
            .where(IrrigationEvent.field_id == field.id)
            .order_by(IrrigationEvent.event_date.asc())
        )
        events_res = await self.session.execute(events_stmt)
        events = list(events_res.scalars().all())
        events_by_date: Dict[date, float] = {}
        for ev in events:
            events_by_date[ev.event_date] = (
                events_by_date.get(ev.event_date, 0.0) + ev.water_applied_mm
            )

        # Retrieve existing observations
        obs_stmt = (
            select(FieldObservation)
            .where(FieldObservation.field_id == field.id)
            .order_by(FieldObservation.observation_date.asc())
        )
        obs_res = await self.session.execute(obs_stmt)
        observations = list(obs_res.scalars().all())

        # Determine start date
        today = date.today()
        start_date = field.planting_date or (today - timedelta(days=30))
        total_season_days = 120
        stage_lengths = CropStageLengths(20, 30, 40, 30)
        stage_kc = CropStageKc(0.35, 1.15, 0.40)

        crop_name = None
        if field.crop:
            crop_name = field.crop.name
            stage_kc = CropStageKc(
                field.crop.kc_ini, field.crop.kc_mid, field.crop.kc_end
            )
            if field.crop.stages and len(field.crop.stages) >= 4:
                stage_map = {s.stage_name.lower(): s.duration_days for s in field.crop.stages}
                stage_lengths = CropStageLengths(
                    stage_map.get("initial", 20),
                    stage_map.get("development", 30),
                    stage_map.get("mid", 40),
                    stage_map.get("late", 30),
                )
                total_season_days = stage_lengths.total_growing_days

        # Setup Weather Provider for forecast & missing days
        weather_provider: WeatherProvider = MockWeatherProvider()

        # Run Soil Water Balance: D_r,i = D_r,i-1 - (P_eff - ETc - RO - CR + I)
        daily_balance_list: List[SoilBalanceDay] = []
        depletion = 0.0  # Assumes field capacity (D_r = 0) at planting / start
        total_etc = 0.0
        total_rain = 0.0
        total_peff = 0.0
        total_applied = 0.0

        current_day = start_date
        end_date = today + timedelta(days=forecast_days)

        while current_day <= end_date:
            dap = (current_day - start_date).days
            root_depth = get_dynamic_root_depth(dap, total_season_days)
            taw = round(soil.taw_mm_per_m * root_depth, 2)
            raw = round(taw * mad_fraction, 2)

            # Resolve ET0 and Rain
            day_et0 = 4.0
            day_rain = 0.0

            # Match from observations if historical
            matching_obs = next(
                (o for o in observations if o.observation_date == current_day), None
            )
            if matching_obs:
                day_et0 = matching_obs.et0 or 4.0
                day_rain = matching_obs.rain_mm or 0.0
            else:
                # Use weather provider
                try:
                    w_rec = await weather_provider.get_daily_inputs(31.5, 74.3, current_day)
                    day_et0 = w_rec.et0_provider or 4.0
                    day_rain = w_rec.precipitation_mm or 0.0
                except Exception:
                    pass

            kc_val, _ = interpolate_kc_stage(dap, stage_lengths, stage_kc)
            etc_val = calculate_etc(day_et0, kc_val)
            peff_val = calculate_effective_rainfall(day_rain)
            applied_irrigation = events_by_date.get(current_day, 0.0)

            # Depletion update
            # Depletion increases with ETc, decreases with Effective Rain and Applied Irrigation
            depletion = depletion + etc_val - peff_val - applied_irrigation
            # Drainage / over-irrigation clamp: Depletion cannot be negative (D_r >= 0)
            if depletion < 0.0:
                depletion = 0.0
            # Maximum depletion cannot exceed TAW
            if depletion > taw:
                depletion = taw

            is_stress = depletion > raw
            recommended_depth = 0.0
            if current_day >= today and is_stress:
                recommended_depth = round(depletion, 1)

            balance_entry = SoilBalanceDay(
                date=current_day,
                et0_mm=round(day_et0, 2),
                kc=round(kc_val, 2),
                etc_mm=round(etc_val, 2),
                rain_mm=round(day_rain, 2),
                effective_rain_mm=peff_val,
                irrigation_applied_mm=applied_irrigation,
                root_depth_m=root_depth,
                taw_mm=taw,
                raw_mm=raw,
                depletion_mm=round(depletion, 2),
                is_stress=is_stress,
                irrigation_recommended_mm=recommended_depth,
            )
            daily_balance_list.append(balance_entry)

            if current_day <= today:
                total_etc += etc_val
                total_rain += day_rain
                total_peff += peff_val
                total_applied += applied_irrigation

            current_day += timedelta(days=1)

        # Build 7-14 Day Schedule
        schedule: List[IrrigationScheduleDay] = []
        forecast_slice = [d for d in daily_balance_list if d.date >= today]
        for f_day in forecast_slice:
            due = f_day.depletion_mm >= f_day.raw_mm
            depth_mm = round(f_day.depletion_mm, 1) if due else 0.0
            # Volume: 1 mm over 1 ha = 10 m3
            vol_per_ha = round(depth_mm * 10.0, 1)
            vol_total = round(vol_per_ha * field.area_ha, 1)

            reason = "Optimal soil moisture (depletion within RAW)"
            if due:
                reason = f"Soil moisture depleted below RAW threshold ({f_day.depletion_mm:.1f} mm >= {f_day.raw_mm:.1f} mm)"

            schedule.append(
                IrrigationScheduleDay(
                    date=f_day.date,
                    day_name=f_day.date.strftime("%a"),
                    depletion_mm=f_day.depletion_mm,
                    raw_threshold_mm=f_day.raw_mm,
                    is_irrigation_due=due,
                    recommended_depth_mm=depth_mm,
                    recommended_volume_m3_per_ha=vol_per_ha,
                    recommended_volume_m3_total=vol_total,
                    reason=reason,
                )
            )

        # Current Status Summary
        current_balance = next(
            (b for b in daily_balance_list if b.date == today), daily_balance_list[-1]
        )
        status = "optimal"
        if current_balance.depletion_mm == 0.0:
            status = "saturated"
        elif current_balance.depletion_mm > current_balance.raw_mm:
            status = "stress"
        elif current_balance.depletion_mm > (current_balance.raw_mm * 0.8):
            status = "caution"

        net_irrigation_req = max(0.0, total_etc - total_peff)

        summary = SeasonSummary(
            total_etc_mm=round(total_etc, 1),
            total_rainfall_mm=round(total_rain, 1),
            total_effective_rain_mm=round(total_peff, 1),
            total_irrigation_applied_mm=round(total_applied, 1),
            net_irrigation_requirement_mm=round(net_irrigation_req, 1),
            current_depletion_mm=current_balance.depletion_mm,
            raw_mm=current_balance.raw_mm,
            taw_mm=current_balance.taw_mm,
            status=status,
        )

        return FieldIrrigationPlanResponse(
            field_id=field.id,
            field_name=field.name,
            crop_name=crop_name,
            area_ha=field.area_ha,
            soil_type=soil.name,
            planting_date=field.planting_date,
            mad_fraction=mad_fraction,
            summary=summary,
            schedule=schedule,
            daily_balance=daily_balance_list,
            events=[IrrigationEventResponse.model_validate(e) for e in events],
        )

    async def _get_authorized_field(self, field_id: uuid.UUID, user: User) -> Field:
        """Ensure field exists and belongs to requesting user or user is admin."""
        stmt = (
            select(Field)
            .options(selectinload(Field.crop).selectinload(Crop.stages))
            .where(Field.id == field_id)
        )
        result = await self.session.execute(stmt)
        field = result.scalar_one_or_none()
        if not field:
            raise NotFoundException(detail="Field not found.")
        if field.user_id != user.id and user.role != "admin":
            raise NotFoundException(detail="Field not found.")
        return field
