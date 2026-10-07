"""IrrigationEvent SQLAlchemy model recording applied water and method."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.field import Field

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class IrrigationEvent(Base, TimestampMixin):
    __tablename__ = "irrigation_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    water_applied_mm: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(
        String(50), default="drip", nullable=False
    )  # drip, sprinkler, flood, furrow
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    field: Mapped[Field] = relationship("Field", back_populates="irrigation_events")
