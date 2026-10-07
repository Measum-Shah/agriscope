"""Pydantic schemas for ML model lifecycle, training, comparison, shadow mode, and drift."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.ml_model import DataProvenance, ModelStatus


class TrainModelRequest(BaseModel):
    """Payload to initiate model training job from a validated dataset."""

    dataset_id: uuid.UUID = Field(..., description="ID of validated training dataset")
    algorithm: str = Field(
        default="random_forest",
        description="Algorithm: random_forest, xgboost, lightgbm, svr, mlp, ensemble/stacking",
    )
    algorithms: Optional[List[str]] = Field(
        default=None,
        description="Optional list of algorithms to train simultaneously in a suite",
    )
    feature_schema: str = Field(default="basic", description="'basic' or 'extended'")
    version: Optional[str] = Field(default=None, description="Semantic version string, e.g. v2.1")
    tune_hyperparameters: bool = Field(default=False, description="Run Optuna hyperparameter optimization")
    cv_folds: int = Field(default=5, ge=2, le=10, description="Cross-validation fold count")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Explicit hyperparameters")


class TrainModelResponse(BaseModel):
    """Asynchronous job initialization response."""

    task_id: str
    message: str
    status: str = "training"
    dataset_id: uuid.UUID
    algorithms: List[str]


class TrainingJobProgress(BaseModel):
    """Live status and step progress for active training jobs."""

    task_id: str
    state: str = "PENDING"
    progress: float = 0.0
    current_step: str = "Initiating"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ApproveModelRequest(BaseModel):
    """Payload to approve a candidate model into production."""

    force: bool = Field(
        default=False,
        description="Force approval overriding quality threshold guards (logs audit warning)",
    )


class RejectModelRequest(BaseModel):
    """Payload to reject a candidate model with required reasoning."""

    reason: str = Field(..., min_length=3, max_length=500, description="Reason for rejection")


class RollbackModelRequest(BaseModel):
    """Payload to rollback production active model to a previous version."""

    target_model_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Target model ID to restore (if null, most recently archived active model)",
    )


class ShadowModeToggleRequest(BaseModel):
    """Payload to toggle shadow mode evaluation for a pending candidate model."""

    enabled: bool = Field(..., description="Enable or disable shadow mode execution")


class MLModelResponse(BaseModel):
    """Schema representing an MLModel record in the registry."""

    id: uuid.UUID
    name: str
    algorithm: str
    version: str
    dataset_id: Optional[uuid.UUID] = None
    feature_schema: Dict[str, Any]
    metrics_json: Dict[str, Any]
    artifact_uri: str
    status: str
    trained_by: Optional[str] = None
    data_provenance: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelComparisonRequest(BaseModel):
    """Request payload to compare multiple models side-by-side."""

    model_ids: List[uuid.UUID] = Field(..., min_length=2, max_length=10)


class ValidationScatterPoint(BaseModel):
    """Sample validation scatter point comparing true vs predicted values."""

    index: int
    y_true: float
    predictions: Dict[str, float]  # model_id/version -> y_pred


class ModelComparisonResponse(BaseModel):
    """Comparative evaluation across multiple model versions or architectures."""

    models: List[MLModelResponse]
    metrics_matrix: Dict[str, Dict[str, Any]]
    scatter_samples: List[ValidationScatterPoint] = Field(default_factory=list)


class ShadowResultItem(BaseModel):
    """Single inference shadow evaluation record."""

    id: uuid.UUID
    prediction_id: uuid.UUID
    candidate_et_value: float
    difference_from_active: float
    latency_ms: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShadowReportResponse(BaseModel):
    """Aggregated champion vs challenger shadow performance analysis."""

    candidate_model_id: uuid.UUID
    candidate_version: str
    candidate_algorithm: str
    active_model_id: Optional[uuid.UUID] = None
    active_version: Optional[str] = None
    sample_count: int
    mean_difference: float
    rmse_vs_active: float
    mae_vs_active: float
    max_difference: float
    fao56_correlation: Optional[float] = None
    recent_samples: List[ShadowResultItem] = Field(default_factory=list)


class DriftCheckRequest(BaseModel):
    """Payload for executing a statistical data drift check."""

    window_days: int = Field(default=30, ge=1, le=180)
    psi_threshold: float = Field(default=0.20, ge=0.05, le=1.0)
    ks_alpha: float = Field(default=0.05, ge=0.001, le=0.20)


class FeatureDriftItem(BaseModel):
    """Drift metrics for a specific numerical meteorological feature."""

    feature: str
    psi: float
    psi_drift: bool
    psi_severity: str
    ks_statistic: float
    ks_pvalue: float
    ks_drift: bool
    is_drifted: bool


class DriftReportResponse(BaseModel):
    """Full PSI and KS dataset drift detection report."""

    drift_detected: bool
    drifted_features: List[str]
    feature_results: Dict[str, FeatureDriftItem]
    reference_sample_count: int
    current_sample_count: int
    psi_threshold: float
    ks_alpha: float
    evaluated_at: datetime
