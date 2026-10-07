"""ShadowResult SQLAlchemy model evaluating candidate model predictions against champion."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.ml_model import MLModel
    from app.models.prediction import Prediction

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ShadowResult(Base, TimestampMixin):
    __tablename__ = "shadow_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_et_value: Mapped[float] = mapped_column(Float, nullable=False)
    difference_from_active: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    prediction: Mapped[Prediction] = relationship("Prediction")
    model: Mapped[MLModel] = relationship("MLModel", back_populates="shadow_results")
