"""Endpoints for single inference, multi-model comparison, explainability, and samples."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.plans import require_plan_feature
from app.db.session import get_db
from app.models.user import User
from app.schemas.prediction import (
    ComparePredictResponse,
    ExplainPredictRequest,
    ExplainPredictResponse,
    PredictRequest,
    PredictResponse,
)
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/predict", tags=["Predictions"])
service = PredictionService()


@router.post("", response_model=PredictResponse)
async def predict_single(
    payload: PredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictResponse:
    """Execute single ET0 prediction with physical constraints, conformal bounds, and quota tracking."""
    return await service.predict(session=db, user=current_user, payload=payload)


@router.post(
    "/compare",
    response_model=ComparePredictResponse,
    dependencies=[Depends(require_plan_feature("model_comparison_enabled"))],
)
async def compare_models(
    payload: PredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComparePredictResponse:
    """Run side-by-side comparison across all model architectures and physics (Pro feature)."""
    return await service.compare(session=db, user=current_user, payload=payload)


@router.post(
    "/explain",
    response_model=ExplainPredictResponse,
    dependencies=[Depends(require_plan_feature("explainability_enabled"))],
)
async def explain_prediction(
    payload: ExplainPredictRequest,
    current_user: User = Depends(get_current_user),
) -> ExplainPredictResponse:
    """Calculate additive SHAP feature attributions and ranking (Pro feature)."""
    return await service.explain(user=current_user, payload=payload)


@router.get("/sample", response_model=Dict[str, Any])
async def get_sample_data(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Provide realistic agricultural meteorological observations for testing."""
    return service.get_sample_inputs()
