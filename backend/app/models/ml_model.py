"""MLModel SQLAlchemy model with full lifecycle states and data provenance."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.models.prediction import Prediction
    from app.models.shadow_result import ShadowResult
    from app.models.training_dataset import TrainingDataset

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ModelStatus(str, Enum):
    TRAINING = "training"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class DataProvenance(str, Enum):
    REAL_DERIVED = "real_derived"
    SYNTHETIC = "synthetic"
    USER_UPLOADED = "user_uploaded"


class MLModel(Base, TimestampMixin):
    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feature_schema: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=ModelStatus.PENDING_APPROVAL.value, nullable=False, index=True
    )
    trained_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data_provenance: Mapped[str] = mapped_column(
        String(50), default=DataProvenance.REAL_DERIVED.value, nullable=False
    )

    dataset: Mapped[Optional[TrainingDataset]] = relationship(
        "TrainingDataset", back_populates="models"
    )
    predictions: Mapped[List[Prediction]] = relationship("Prediction", back_populates="model")
    shadow_results: Mapped[List[ShadowResult]] = relationship(
        "ShadowResult", back_populates="model"
    )

    __table_args__ = (UniqueConstraint("name", "version", name="uq_ml_models_name_version"),)
