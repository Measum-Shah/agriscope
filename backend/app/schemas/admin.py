"""Admin schemas for user management, dataset inspection, metrics, audit and system settings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


# --- Admin User Management Schemas ---

class AdminUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: str
    plan: str
    status: str
    email_verified: bool
    totp_enabled: bool
    failed_attempts: int
    locked_until: Optional[datetime] = None
    registration_date: datetime
    last_login: Optional[datetime] = None


class AdminUserUpdateRolePlan(BaseModel):
    role: Optional[str] = Field(None, description="free | pro | admin")
    plan: Optional[str] = Field(None, description="free | pro | admin")


class AdminUserStatusUpdate(BaseModel):
    status: str = Field(..., description="active | suspended | pending_verification")


class AdminUserAuditItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor: str
    action: str
    target: Optional[str]
    metadata_json: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime


# --- Admin Dataset Schemas ---

class DatasetItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: str
    file_uri: str
    file_hash: str
    status: str  # validated | rejected | in_use | ready
    data_provenance: str
    stats_json: Dict[str, Any]
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime



class DatasetUploadReport(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    status: str
    row_count: int
    columns: List[str]
    stats: Dict[str, Any]
    outlier_report: Dict[str, Any]
    preview_rows: List[Dict[str, Any]]
    validation_errors: List[str]
    message: str


# --- Admin Metrics Schemas ---

class SystemMetricsResponse(BaseModel):
    total_users: int
    active_users: int
    suspended_users: int
    predictions_today: int
    total_predictions: int
    queue_depth: int
    active_model: Optional[str]
    error_rate_pct: float
    latency_p50_ms: float
    latency_p95_ms: float
    storage_usage_bytes: int
    uptime_seconds: float


# --- Admin System & Audit Schemas ---

class FeatureFlagItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_enabled: bool
    rules_json: Dict[str, Any] = Field(default_factory=dict)


class FeatureFlagCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    is_enabled: bool = False
    rules_json: Dict[str, Any] = Field(default_factory=dict)


class AnnouncementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message: str
    type: str  # info | warning | maintenance
    is_active: bool
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None



class AnnouncementCreateUpdate(BaseModel):
    title: str
    message: str
    type: str = "info"
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class SystemLimitsConfig(BaseModel):
    free_daily_prediction_limit: int = 30
    pro_daily_prediction_limit: int = 1000
    free_max_fields: int = 1
    pro_max_fields: int = 50
    batch_max_rows: int = 10000
    rate_limit_per_min_default: int = 60
    maintenance_mode: bool = False
