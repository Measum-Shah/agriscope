"""Batch prediction API router handling CSV uploads, progress tracking, and results download."""

from __future__ import annotations

import io
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Header,
    Query,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.plans import require_plan_feature
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.session import get_db
from app.models.batch_job import BatchJob
from app.models.user import User
from app.providers.storage.minio import get_storage_provider
from app.schemas.jobs import BatchJobCreateResponse, BatchJobResponse
from app.workers.tasks.batch import process_batch_prediction_job_task

router = APIRouter(prefix="/batch", tags=["Batch Predictions"])


@router.get("/template")
async def download_csv_template():
    """Download standard CSV template for batch predictions."""
    template_content = (
        "temperature,humidity,wind_speed,solar_radiation\n"
        "28.5,45.0,2.1,22.4\n"
        "31.0,38.0,1.8,24.5\n"
        "24.2,60.0,3.2,18.0\n"
    )
    return {
        "filename": "agriscope_batch_template.csv",
        "content_type": "text/csv",
        "csv_content": template_content,
    }


@router.post(
    "/upload",
    response_model=BatchJobCreateResponse,
    dependencies=[Depends(require_plan_feature("export_csv"))],
)
async def upload_batch_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload CSV file (up to 10k rows) and queue asynchronous prediction job."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise BadRequestException(detail="Only CSV files are supported.")

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:  # 15 MB limit
        raise BadRequestException(detail="File size exceeds maximum 15 MB limit.")

    # Count rows roughly
    text_content = content.decode("utf-8-sig", errors="replace")
    lines = [l for l in text_content.splitlines() if l.strip()]
    if len(lines) <= 1:
        raise BadRequestException(detail="CSV file contains no data rows.")
    if len(lines) > 10001:
        raise BadRequestException(detail="CSV exceeds maximum allowable limit of 10,000 rows.")

    storage = get_storage_provider()
    input_filename = f"batch_input_{uuid.uuid4().hex}_{file.filename}"
    await storage.upload_bytes(content, input_filename, content_type="text/csv")

    job = BatchJob(
        user_id=current_user.id,
        status="pending",
        input_file_uri=input_filename,
        total_rows=len(lines) - 1,
        processed_rows=0,
        error_summary={},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch Celery background worker task
    try:
        process_batch_prediction_job_task.delay(str(job.id))
    except Exception:
        # Fallback to direct background task if Celery broker unavailable in testing
        background_tasks.add_task(process_batch_prediction_job_task, str(job.id))

    return BatchJobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_rows=job.total_rows,
        message="Batch prediction job submitted successfully.",
    )


@router.get("/status/{job_id}", response_model=BatchJobResponse)
async def get_batch_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query real-time status and progress of batch prediction job."""
    stmt = select(BatchJob).where(BatchJob.id == job_id, BatchJob.user_id == current_user.id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise NotFoundException(detail="Batch job not found.")
    return job


@router.get("/download/{job_id}")
async def download_batch_results(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtain presigned download URL for completed batch results."""
    stmt = select(BatchJob).where(BatchJob.id == job_id, BatchJob.user_id == current_user.id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job or not job.output_file_uri:
        raise NotFoundException(detail="Batch job results not found or still processing.")

    storage = get_storage_provider()
    url = await storage.get_presigned_download_url(job.output_file_uri, expires_in_seconds=3600)
    return {"download_url": url, "filename": job.output_file_uri}
