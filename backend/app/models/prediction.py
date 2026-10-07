"""Prediction SQLAlchemy model with ET inputs, check constraints, and composite indexes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.models.batch_job import BatchJob
    from app.models.field import Field
    from app.models.ml_model import MLModel
    from app.models.user import User

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PredictionSource(str, Enum):
    MANUAL = "manual"
    LOCATION = "location"
    BATCH = "batch"
    API = "api"


class ETClassification(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Prediction(Base, TimestampMixin):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    field_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batch_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(50), default=PredictionSource.MANUAL.value, nullable=False
    )

    # Core meteorological inputs with check constraints
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed: Mapped[float] = mapped_column(Float, nullable=False)
    solar_radiation: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional physical / geographical inputs
    tmin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tmax: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    day_of_year: Mapped[Optional[int]] = mapped_column(Float, nullable=True)

    # ET outputs
    et_value: Mapped[float] = mapped_column(Float, nullable=False)
    interval_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    interval_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    classification: Mapped[str] = mapped_column(
        String(50), default=ETClassification.MODERATE.value, nullable=False
    )

    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    feature_contributions: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="predictions")
    model: Mapped[Optional[MLModel]] = relationship("MLModel", back_populates="predictions")
    field: Mapped[Optional[Field]] = relationship("Field", back_populates="predictions")
    batch_job: Mapped[Optional[BatchJob]] = relationship("BatchJob", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_user_timestamp", "user_id", "timestamp"),
        Index("ix_predictions_user_saved", "user_id", "is_saved"),
        Index("ix_predictions_user_classification", "user_id", "classification"),
        CheckConstraint("temperature >= -10 AND temperature <= 50", name="chk_pred_temp_range"),
        CheckConstraint("humidity >= 0 AND humidity <= 100", name="chk_pred_humidity_range"),
        CheckConstraint("wind_speed >= 0 AND wind_speed <= 30", name="chk_pred_wind_range"),
        CheckConstraint(
            "solar_radiation >= 0 AND solar_radiation <= 35", name="chk_pred_solar_range"
        ),
    )
