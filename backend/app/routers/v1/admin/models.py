"""Admin models router for model lifecycle management, training, approval, rollback, shadow mode, and drift monitoring."""

from __future__ import annotations

import uuid
from typing import List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.ml_model import (
    ApproveModelRequest,
    DriftCheckRequest,
    DriftReportResponse,
    MLModelResponse,
    ModelComparisonRequest,
    ModelComparisonResponse,
    RejectModelRequest,
    RollbackModelRequest,
    ShadowModeToggleRequest,
    ShadowReportResponse,
    TrainingJobProgress,
    TrainModelRequest,
    TrainModelResponse,
)
from app.services.audit import AuditService
from app.services.dataset_service import DatasetService
from app.services.model_service import ModelService
from app.workers.tasks.training import train_models_task

router = APIRouter(prefix="/admin/models", tags=["admin-models"])


@router.get("", response_model=List[MLModelResponse])
async def list_models(
    status: Optional[str] = Query(None, description="Filter by model status"),
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """List all ML models in registry with lifecycle status."""
    models = await ModelService.list_models(db, status=status)
    return [MLModelResponse.model_validate(m) for m in models]


@router.get("/active", response_model=Optional[MLModelResponse])
async def get_active_model(
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve currently active production model."""
    model = await ModelService.get_active_model(db)
    if not model:
        return None
    return MLModelResponse.model_validate(model)


@router.get("/{model_id}", response_model=MLModelResponse)
async def get_model_details(
    model_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed model card metadata and performance metrics."""
    model = await ModelService.get_model(db, model_id)
    return MLModelResponse.model_validate(model)


@router.post("/train", response_model=TrainModelResponse, status_code=status.HTTP_202_ACCEPTED)
async def train_model(
    payload: TrainModelRequest,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Trigger asynchronous training job on a validated dataset."""
    dataset = await DatasetService.get_dataset(db, payload.dataset_id)
    algos = payload.algorithms or [payload.algorithm]

    task = train_models_task.delay(
        dataset_id_str=str(dataset.id),
        algorithms=algos,
        feature_schema=payload.feature_schema,
        version=payload.version,
        tune=payload.tune_hyperparameters,
        params=payload.params,
        admin_email=current_admin.email,
    )

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.model.train_start",
        target=str(dataset.id),
        metadata_json={
            "task_id": task.id,
            "algorithms": algos,
            "feature_schema": payload.feature_schema,
            "tune": payload.tune_hyperparameters,
        },
    )

    return TrainModelResponse(
        task_id=task.id,
        message=f"Training job initiated for {len(algos)} algorithm(s).",
        status="training",
        dataset_id=payload.dataset_id,
        algorithms=algos,
    )


@router.get("/jobs/{task_id}", response_model=TrainingJobProgress)
async def get_training_job_status(
    task_id: str,
    current_admin: User = Depends(require_role(["admin"])),
):
    """Poll live progress and status for active training jobs."""
    res = AsyncResult(task_id)
    state = res.state
    meta = res.info if isinstance(res.info, dict) else {}

    progress = meta.get("progress", 100.0 if state == "SUCCESS" else 0.0)
    current_step = meta.get("step", "Processing" if state == "PROGRESS" else state)

    return TrainingJobProgress(
        task_id=task_id,
        state=state,
        progress=float(progress),
        current_step=str(current_step),
        result=res.result if state == "SUCCESS" and isinstance(res.result, dict) else None,
        error=str(res.result) if state == "FAILURE" else None,
    )


@router.post("/{model_id}/approve", response_model=MLModelResponse)
async def approve_model(
    model_id: uuid.UUID,
    payload: ApproveModelRequest,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Approve candidate model with zero-downtime hot swap and metric guard checks."""
    model = await ModelService.approve_model(
        db,
        model_id=model_id,
        admin_email=current_admin.email,
        force=payload.force,
    )

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.model.approve",
        target=str(model.id),
        metadata_json={
            "version": model.version,
            "algorithm": model.algorithm,
            "force_override": payload.force,
        },
    )
    return MLModelResponse.model_validate(model)


@router.post("/{model_id}/reject", response_model=MLModelResponse)
async def reject_model(
    model_id: uuid.UUID,
    payload: RejectModelRequest,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Reject candidate model with reason and transition status to rejected."""
    model = await ModelService.reject_model(
        db, model_id=model_id, admin_email=current_admin.email, reason=payload.reason
    )

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.model.reject",
        target=str(model.id),
        metadata_json={"reason": payload.reason, "version": model.version},
    )
    return MLModelResponse.model_validate(model)


@router.post("/rollback", response_model=MLModelResponse)
async def rollback_model(
    payload: RollbackModelRequest,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Rollback active production model to previous version with immediate hot swap."""
    model = await ModelService.rollback_model(
        db, admin_email=current_admin.email, target_model_id=payload.target_model_id
    )

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.model.rollback",
        target=str(model.id),
        metadata_json={"restored_version": model.version, "algorithm": model.algorithm},
    )
    return MLModelResponse.model_validate(model)


@router.post("/{model_id}/shadow", response_model=MLModelResponse)
async def toggle_shadow_mode(
    model_id: uuid.UUID,
    payload: ShadowModeToggleRequest,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Toggle silent shadow mode evaluation for candidate model."""
    model = await ModelService.toggle_shadow_mode(db, model_id, enabled=payload.enabled)

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.model.shadow_toggle",
        target=str(model.id),
        metadata_json={"shadow_mode": payload.enabled},
    )
    return MLModelResponse.model_validate(model)


@router.get("/{model_id}/shadow-report", response_model=ShadowReportResponse)
async def get_shadow_report(
    model_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Fetch champion vs challenger shadow comparison report."""
    report = await ModelService.get_shadow_report(db, model_id)
    return ShadowReportResponse(**report)


@router.post("/compare", response_model=ModelComparisonResponse)
async def compare_models(
    payload: ModelComparisonRequest,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Side-by-side metric comparison across multiple model versions."""
    res = await ModelService.compare_models(db, payload.model_ids)
    return ModelComparisonResponse(
        models=[MLModelResponse.model_validate(m) for m in res["models"]],
        metrics_matrix=res["metrics_matrix"],
        scatter_samples=res["scatter_samples"],
    )


@router.post("/drift-check", response_model=DriftReportResponse)
async def run_drift_check(
    payload: DriftCheckRequest = DriftCheckRequest(),
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Execute statistical data drift test (PSI and KS) on production inference window."""
    report = await ModelService.run_drift_check(
        db,
        window_days=payload.window_days,
        psi_threshold=payload.psi_threshold,
        ks_alpha=payload.ks_alpha,
    )

    await AuditService.log_event(
        db,
        actor=current_admin.email,
        action="admin.model.drift_check",
        target="inference_window",
        metadata_json={"drift_detected": report.get("drift_detected", False)},
    )
    return DriftReportResponse(**report)
