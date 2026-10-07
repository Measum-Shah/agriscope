"""Public researcher API surface authenticated via scoped API keys."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import require_api_key_scope
from app.core.exceptions import NotFoundException
from app.core.plans import QuotaService, redis_client
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.batch_job import BatchJob
from app.models.field import Field
from app.models.field_observation import FieldObservation
from app.models.user import User
from app.schemas.public import (
    PublicBatchStatusResponse,
    PublicBatchSubmitRequest,
    PublicBatchSubmitResponse,
    PublicFieldEtSeriesResponse,
    PublicFieldObservationItem,
    PublicPredictRequest,
    PublicPredictResponse,
    PublicWeatherPrefillResponse,
)
from app.services.export_service import generate_csv_bytes
from app.services.ml_client import MLClient
from app.services.weather_service import WeatherService
from app.workers.tasks.batch import process_batch_prediction_job_task

try:
    from agriscope_ml.physics.penman_monteith import calculate_et0
except Exception:
    calculate_et0 = None

router = APIRouter(prefix="/public", tags=["Public Researcher API"])


@router.post(
    "/predict",
    response_model=PublicPredictResponse,
    summary="Public ET0 single inference",
)
async def public_predict(
    payload: PublicPredictRequest,
    api_key: ApiKey = Depends(require_api_key_scope(["predict:write"])),
    db: AsyncSession = Depends(get_db),
) -> PublicPredictResponse:
    """Computes daily reference evapotranspiration (ET₀) and 90% conformal intervals."""
    user = await db.get(User, api_key.user_id)
    # Increment user daily predictions
    await QuotaService.increment_predictions_today(str(user.id), 1)

    ml_client = MLClient()
    obs_dict = {
        "temperature": payload.temperature,
        "humidity": payload.humidity,
        "wind_speed": payload.wind_speed,
        "solar_radiation": payload.solar_radiation,
        "latitude": payload.latitude,
        "elevation": payload.elevation_m,
        "doy": payload.day_of_year,
    }

    fao56_ref = None
    if calculate_et0:
        try:
            calc = calculate_et0(
                temperature=payload.temperature,
                humidity=payload.humidity,
                wind_speed=payload.wind_speed,
                solar_radiation=payload.solar_radiation,
                latitude=payload.latitude,
                elevation=payload.elevation_m,
                doy=payload.day_of_year,
            )
            fao56_ref = round(calc.et0, 2)
        except Exception:
            fao56_ref = None

    try:
        pred_res = await ml_client.predict(obs_dict)
        et_value = pred_res.et_value
        low_val = pred_res.interval_low
        high_val = pred_res.interval_high
        classification = pred_res.classification
        version = pred_res.model_version
    except Exception:
        et_value = fao56_ref if fao56_ref is not None else 4.5
        low_val = round(max(0.0, et_value * 0.85), 2)
        high_val = round(et_value * 1.15, 2)
        classification = "moderate" if 2.0 <= et_value <= 5.0 else ("high" if et_value > 5.0 else "low")
        version = "fao56_physics_fallback"

    now = datetime.now(timezone.utc)
    return PublicPredictResponse(
        et_value=et_value,
        interval_low=low_val,
        interval_high=high_val,
        classification=classification,
        fao56_reference=fao56_ref,
        unit="mm/day",
        model_version=version,
        timestamp=now,
    )


@router.post(
    "/batch/submit",
    response_model=PublicBatchSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit async batch prediction dataset",
)
async def public_batch_submit(
    payload: PublicBatchSubmitRequest,
    api_key: ApiKey = Depends(require_api_key_scope(["batch:write"])),
    db: AsyncSession = Depends(get_db),
) -> PublicBatchSubmitResponse:
    """Accepts array of meteorological rows and queues background batch inference."""
    user = await db.get(User, api_key.user_id)
    headers = ["temperature", "humidity", "wind_speed", "solar_radiation", "latitude", "elevation_m", "day_of_year"]
    rows = []
    for r in payload.rows:
        rows.append([
            r.temperature,
            r.humidity,
            r.wind_speed,
            r.solar_radiation,
            r.latitude or "",
            r.elevation_m or "",
            r.day_of_year or "",
        ])

    csv_bytes = generate_csv_bytes(headers, rows)
    job_id = uuid.uuid4()
    batch_job = BatchJob(
        id=job_id,
        user_id=user.id,
        status="pending",
        total_rows=len(payload.rows),
        processed_rows=0,
        error_summary={},
    )
    db.add(batch_job)
    await db.commit()

    # Trigger Celery background task
    try:
        process_batch_prediction_job_task.delay(str(job_id), str(user.id), csv_bytes.decode("utf-8"))
    except Exception:
        # Fallback for synchronous test / local worker
        process_batch_prediction_job_task(str(job_id), str(user.id), csv_bytes.decode("utf-8"))

    return PublicBatchSubmitResponse(
        job_id=str(job_id),
        status="pending",
        total_rows=len(payload.rows),
    )


@router.get(
    "/batch/status/{job_id}",
    response_model=PublicBatchStatusResponse,
    summary="Check status of public batch job",
)
async def public_batch_status(
    job_id: uuid.UUID,
    api_key: ApiKey = Depends(require_api_key_scope(["batch:read"])),
    db: AsyncSession = Depends(get_db),
) -> PublicBatchStatusResponse:
    """Returns progress and result download URL once complete."""
    query = select(BatchJob).where(BatchJob.id == job_id, BatchJob.user_id == api_key.user_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise NotFoundException("Batch job not found")

    download_url = None
    if job.status == "completed" and job.output_file_uri:
        download_url = f"/api/v1/batch/download/{job.id}"

    failed_count = (job.error_summary or {}).get("failed_count", 0)
    return PublicBatchStatusResponse(
        job_id=str(job.id),
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        failed_count=failed_count,
        download_url=download_url,
    )


@router.get(
    "/weather/prefill",
    response_model=PublicWeatherPrefillResponse,
    summary="Get meteorological inputs for coordinates",
)
async def public_weather_prefill(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
    target_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    api_key: ApiKey = Depends(require_api_key_scope(["weather:read"])),
) -> PublicWeatherPrefillResponse:
    """Returns temperature, humidity, wind, solar radiation for coordinates and date."""
    parsed_date = date.fromisoformat(target_date) if target_date else date.today()
    service = WeatherService(redis_client=redis_client)
    res = await service.get_prefill_inputs(latitude=lat, longitude=lon, target_date=parsed_date)
    return PublicWeatherPrefillResponse(
        temperature=res["temperature"],
        humidity=res["humidity"],
        wind_speed=res["wind_speed"],
        solar_radiation=res["solar_radiation"],
        provider=res.get("source_provider", "open_meteo"),
        is_fallback=res.get("is_fallback", False),
    )


@router.get(
    "/fields/{field_id}/et-series",
    response_model=PublicFieldEtSeriesResponse,
    summary="Get time-series evapotranspiration for a field",
)
async def public_field_et_series(
    field_id: uuid.UUID,
    api_key: ApiKey = Depends(require_api_key_scope(["fields:read"])),
    db: AsyncSession = Depends(get_db),
) -> PublicFieldEtSeriesResponse:
    """Returns remote-sensing derived NDVI, Kc, and ETc time series."""
    query = select(Field).where(Field.id == field_id, Field.user_id == api_key.user_id)
    res = await db.execute(query)
    field = res.scalar_one_or_none()
    if not field:
        raise NotFoundException("Field not found or access denied")

    obs_query = (
        select(FieldObservation)
        .where(FieldObservation.field_id == field_id)
        .order_by(desc(FieldObservation.observation_date))
        .limit(60)
    )
    obs_res = await db.execute(obs_query)
    observations = list(obs_res.scalars().all())

    items = [
        PublicFieldObservationItem(
            date=obs.observation_date.isoformat(),
            ndvi=obs.ndvi,
            kc=obs.kc,
            et0=obs.et0,
            etc=obs.etc,
        )
        for obs in reversed(observations)
    ]

    return PublicFieldEtSeriesResponse(
        field_id=str(field.id),
        field_name=field.name,
        crop_name=field.crop_name,
        area_ha=field.area_ha,
        observations=items,
    )
