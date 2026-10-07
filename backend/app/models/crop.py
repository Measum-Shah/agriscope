"""Crop and CropStage SQLAlchemy models with FAO-56 coefficients."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.models.field import Field

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Crop(Base, TimestampMixin):
    __tablename__ = "crops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    scientific_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    kc_ini: Mapped[float] = mapped_column(Float, nullable=False)
    kc_mid: Mapped[float] = mapped_column(Float, nullable=False)
    kc_end: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    stages: Mapped[List["CropStage"]] = relationship(
        "CropStage", back_populates="crop", cascade="all, delete-orphan"
    )
    fields: Mapped[List["Field"]] = relationship("Field", back_populates="crop")


class CropStage(Base):
    __tablename__ = "crop_stages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # initial, development, mid, late
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)

    crop: Mapped["Crop"] = relationship("Crop", back_populates="stages")
