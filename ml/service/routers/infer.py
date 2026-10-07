"""Inference and explainability endpoints for AgriScope ML service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..manager import ModelManager
from ..schemas.inference import (
    BatchInferenceRequest,
    BatchInferenceResponse,
    ExplainRequest,
    ExplainResponse,
    InferenceResponse,
    MeteorologicalInput,
)

router = APIRouter(tags=["Inference"])


def get_manager(request: Request) -> ModelManager:
    manager = getattr(request.app.state, "model_manager", None)
    if manager is None:
        manager = ModelManager()
        manager.warm_up()
        request.app.state.model_manager = manager
    return manager


@router.post("/infer", response_model=InferenceResponse)
async def infer_single(
    payload: MeteorologicalInput,
    manager=Depends(get_manager),
) -> InferenceResponse:
    """Predict reference evapotranspiration (ET0) with 90% conformal prediction interval."""
    try:
        return manager.predict_single(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


@router.post("/infer/batch", response_model=BatchInferenceResponse)
async def infer_batch(
    payload: BatchInferenceRequest,
    manager=Depends(get_manager),
) -> BatchInferenceResponse:
    """Batch predict ET0 and conformal intervals for up to 10,000 observations."""
    try:
        return manager.predict_batch(payload.observations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch inference failed: {str(e)}")


@router.post("/explain", response_model=ExplainResponse)
async def explain_instance(
    payload: ExplainRequest,
    manager=Depends(get_manager),
) -> ExplainResponse:
    """Compute additive SHAP feature contributions for a single observation."""
    try:
        return manager.explain(payload.observation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")
