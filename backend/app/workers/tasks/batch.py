"""Celery worker tasks for asynchronous batch prediction processing, reports, and delivery."""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any, Dict, List

from celery import shared_task
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.db.session import async_session_factory
from app.models.batch_job import BatchJob
from app.models.prediction import Prediction
from app.providers.storage.minio import get_storage_provider
from app.services.export_service import generate_csv_bytes, sanitize_csv_cell
from app.services.notification_service import SSEConnectionManager
from app.services.ml_client import MLClient


@shared_task(name="app.workers.tasks.batch.process_batch_prediction_job")
def process_batch_prediction_job_task(job_id_str: str) -> Dict[str, Any]:
    """Execute asynchronous batch prediction over uploaded CSV file."""
    import asyncio

    return asyncio.run(_async_process_batch_job(job_id_str))


async def _async_process_batch_job(job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    storage = get_storage_provider()
    ml_client = MLClient()

    async with async_session_factory() as session:
        stmt = select(BatchJob).where(BatchJob.id == job_id)
        res = await session.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return {"error": "Batch job not found"}

        job.status = "processing"
        await session.commit()

        # Download input CSV
        try:
            csv_bytes = await storage.download_bytes(job.input_file_uri)
            text_stream = io.StringIO(csv_bytes.decode("utf-8-sig"))
            reader = csv.DictReader(text_stream)
        except Exception as e:
            job.status = "failed"
            job.error_summary = {"fatal_error": f"Failed to read CSV: {str(e)}"}
            await session.commit()
            return {"error": str(e)}

        rows = list(reader)
        total_rows = len(rows)
        job.total_rows = total_rows

        output_rows: List[List[Any]] = []
        errors: List[Dict[str, Any]] = []
        processed = 0

        output_headers = [
            "row_index",
            "temperature",
            "humidity",
            "wind_speed",
            "solar_radiation",
            "predicted_et0_mm",
            "interval_low_mm",
            "interval_high_mm",
            "status",
            "error",
        ]

        for idx, row in enumerate(rows, start=1):
            try:
                temp = float(row.get("temperature", row.get("T2M", 0)))
                hum = float(row.get("humidity", row.get("RH2M", 0)))
                wind = float(row.get("wind_speed", row.get("WS2M", 0)))
                rad = float(row.get("solar_radiation", row.get("ALLSKY_SFC_SW_DWN", 0)))

                # Physical range validation
                if not (-10.0 <= temp <= 50.0):
                    raise ValueError(f"Temperature {temp}°C outside range [-10, 50]")
                if not (0.0 <= hum <= 100.0):
                    raise ValueError(f"Humidity {hum}% outside range [0, 100]")
                if not (0.0 <= wind <= 30.0):
                    raise ValueError(f"Wind speed {wind} m/s outside range [0, 30]")
                if not (0.0 <= rad <= 35.0):
                    raise ValueError(f"Solar radiation {rad} MJ outside range [0, 35]")

                # Inference via ML Client
                infer_res = await ml_client.predict(
                    temperature=temp,
                    humidity=hum,
                    wind_speed=wind,
                    solar_radiation=rad,
                )

                output_rows.append(
                    [
                        idx,
                        temp,
                        hum,
                        wind,
                        rad,
                        infer_res.predicted_et0,
                        infer_res.conformal_interval[0],
                        infer_res.conformal_interval[1],
                        "SUCCESS",
                        "",
                    ]
                )
            except Exception as row_err:
                errors.append({"row": idx, "error": str(row_err)})
                output_rows.append(
                    [
                        idx,
                        row.get("temperature", ""),
                        row.get("humidity", ""),
                        row.get("wind_speed", ""),
                        row.get("solar_radiation", ""),
                        "",
                        "",
                        "",
                        "FAILED",
                        str(row_err),
                    ]
                )

            processed += 1
            if processed % 100 == 0:
                job.processed_rows = processed
                await session.commit()

        # Generate Result CSV and upload
        result_csv_bytes = generate_csv_bytes(output_headers, output_rows)
        output_filename = f"batch_results_{job.id}.csv"
        out_uri = await storage.upload_bytes(
            result_csv_bytes,
            output_filename,
            content_type="text/csv",
        )

        job.processed_rows = processed
        job.output_file_uri = output_filename
        job.status = "completed" if len(errors) < total_rows else "failed"
        job.error_summary = {
            "total_processed": processed,
            "failed_count": len(errors),
            "errors_sample": errors[:25],
        }
        await session.commit()

        # Broadcast SSE event to user
        await SSEConnectionManager.broadcast_to_user(
            user_id=job.user_id,
            event_type="batch_completed",
            payload={
                "job_id": str(job.id),
                "status": job.status,
                "total_rows": total_rows,
                "failed_count": len(errors),
            },
        )

        return {
            "job_id": str(job.id),
            "status": job.status,
            "total_rows": total_rows,
            "failed_rows": len(errors),
        }
