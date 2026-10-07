"""Admin datasets router for dataset upload, validation, outlier analysis, download, and deletion."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.providers.storage.minio import get_storage_provider
from app.schemas.admin import DatasetItem, DatasetUploadReport
from app.services.audit import AuditService
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/admin/datasets", tags=["admin-datasets"])


@router.get("", response_model=List[DatasetItem])
async def list_datasets(
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """List all registered ML training datasets."""
    datasets = await DatasetService.list_datasets(db)
    return [DatasetItem.model_validate(d) for d in datasets]


@router.post("/upload", response_model=DatasetUploadReport)
async def upload_dataset(
    name: str = Form(...),
    version: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Upload CSV dataset, validate physical ranges and schemas, calculate stats, and generate outlier report."""
    content_bytes = await file.read()
    dataset, report_dict = await DatasetService.upload_dataset(
        db,
        name=name,
        version=version,
        content_bytes=content_bytes,
        filename=file.filename or "dataset.csv",
        description=description,
    )

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.dataset.upload",
        target=str(dataset.id),
        metadata_json={
            "name": name,
            "version": version,
            "status": dataset.status,
            "row_count": report_dict["row_count"],
        },
    )
    return DatasetUploadReport(**report_dict)


@router.get("/{dataset_id}", response_model=DatasetItem)
async def get_dataset(
    dataset_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Get metadata for a specific dataset."""
    dataset = await DatasetService.get_dataset(db, dataset_id)
    return DatasetItem.model_validate(dataset)


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Download the raw CSV file of the training dataset."""
    dataset = await DatasetService.get_dataset(db, dataset_id)
    storage = get_storage_provider()
    # file_uri format: s3://bucket/object_name or mock key
    obj_name = dataset.file_uri.split("/")[-1]
    if "datasets/" not in obj_name:
        obj_name = f"datasets/{obj_name}"

    try:
        csv_bytes = await storage.download_bytes(obj_name)
    except Exception:
        # Fallback empty CSV with header
        csv_bytes = b"temp_max,temp_min,humidity,wind_speed\n"

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.dataset.download",
        target=str(dataset.id),
        metadata_json={"dataset_name": dataset.name},
    )

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset.name}_{dataset.version}.csv"'},
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a training dataset record."""
    dataset = await DatasetService.get_dataset(db, dataset_id)
    await DatasetService.delete_dataset(db, dataset_id)

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.dataset.delete",
        target=str(dataset_id),
        metadata_json={"dataset_name": dataset.name},
    )
