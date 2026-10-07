"""TrainingDataset SQLAlchemy model with provenance, hash, and status tracking."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.models.ml_model import MLModel

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TrainingDataset(Base, TimestampMixin):
    __tablename__ = "training_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    file_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    status: Mapped[str] = mapped_column(String(50), default="ready", nullable=False)
    data_provenance: Mapped[str] = mapped_column(
        String(50), default="real_derived", nullable=False
    )  # real_derived | synthetic | user_uploaded
    stats_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    models: Mapped[List[MLModel]] = relationship("MLModel", back_populates="dataset")
