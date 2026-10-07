"""Model management and hot-swap endpoints for AgriScope ML service."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from ..manager import ModelManager
from ..schemas.inference import LoadModelRequest, LoadModelResponse, ModelSummaryResponse

router = APIRouter(prefix="/models", tags=["Models"])


def get_manager(request: Request) -> ModelManager:
    manager = getattr(request.app.state, "model_manager", None)
    if manager is None:
        manager = ModelManager()
        manager.warm_up()
        request.app.state.model_manager = manager
    return manager


@router.get("", response_model=List[ModelSummaryResponse])
async def list_models(manager=Depends(get_manager)) -> List[ModelSummaryResponse]:
    """List all registered and loaded models with metrics and data provenance."""
    try:
        return manager.list_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/load", response_model=LoadModelResponse)
async def load_model(
    payload: LoadModelRequest,
    manager=Depends(get_manager),
) -> LoadModelResponse:
    """Hot-swap the active model bundle without dropping in-flight inference requests."""
    try:
        manager.load_model(payload.model_id, payload.version)
        active = manager.active_bundle
        return LoadModelResponse(
            success=True,
            message=f"Model '{payload.model_id}:{payload.version}' loaded successfully.",
            active_model_id=active.model_id,
            active_model_version=active.version,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to hot-swap model: {str(e)}")
