"""FieldObservation SQLAlchemy model with remote-sensing indices and composite index."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.field import Field

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class FieldObservation(Base, TimestampMixin):
    __tablename__ = "field_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    ndvi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ndwi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    et0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    etc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rain_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    field: Mapped[Field] = relationship("Field", back_populates="observations")

    __table_args__ = (
        Index("ix_field_observations_field_date", "field_id", "observation_date"),
        CheckConstraint(
            "cloud_cover_pct >= 0 AND cloud_cover_pct <= 100", name="chk_obs_cloud_pct"
        ),
    )
