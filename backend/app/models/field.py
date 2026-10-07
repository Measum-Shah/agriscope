"""Field SQLAlchemy model with PostGIS geometry and spatial indexing."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from app.models.crop import Crop
    from app.models.field_observation import FieldObservation
    from app.models.irrigation_event import IrrigationEvent
    from app.models.prediction import Prediction
    from app.models.user import User

from geoalchemy2 import Geometry
from sqlalchemy import Date, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Field(Base, TimestampMixin):
    __tablename__ = "fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    crop_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crops.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    planting_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    area_ha: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Polygon or MultiPolygon geometry in WGS84 (SRID 4326)
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="fields")
    crop: Mapped[Optional[Crop]] = relationship("Crop", back_populates="fields")
    observations: Mapped[List[FieldObservation]] = relationship(
        "FieldObservation", back_populates="field", cascade="all, delete-orphan"
    )
    irrigation_events: Mapped[List[IrrigationEvent]] = relationship(
        "IrrigationEvent", back_populates="field", cascade="all, delete-orphan"
    )
    predictions: Mapped[List[Prediction]] = relationship("Prediction", back_populates="field")

    __table_args__ = (Index("ix_fields_user_name", "user_id", "name"),)
