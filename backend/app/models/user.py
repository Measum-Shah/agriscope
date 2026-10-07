"""User SQLAlchemy model with authentication, plan entitlements, and lockout controls."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.models.api_key import ApiKey
    from app.models.batch_job import BatchJob
    from app.models.field import Field
    from app.models.notification import Notification
    from app.models.prediction import Prediction
    from app.models.report import Report
    from app.models.session import Session
    from app.models.subscription import Subscription

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin


class UserRole(str, Enum):
    FREE = "free"
    PRO = "pro"
    ADMIN = "admin"


class UserPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.FREE.value, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default=UserPlan.FREE.value, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=UserStatus.ACTIVE.value, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_recovery_codes: Mapped[List[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions: Mapped[List[Session]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    predictions: Mapped[List[Prediction]] = relationship(
        "Prediction", back_populates="user", cascade="all, delete-orphan"
    )
    fields: Mapped[List[Field]] = relationship(
        "Field", back_populates="user", cascade="all, delete-orphan"
    )
    batch_jobs: Mapped[List[BatchJob]] = relationship(
        "BatchJob", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List[ApiKey]] = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[List[Report]] = relationship(
        "Report", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List[Subscription]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List[Notification]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
