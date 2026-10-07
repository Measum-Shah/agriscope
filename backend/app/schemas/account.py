"""Pydantic schemas for User self-service, TOTP 2FA, and Entitlements."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.auth import SessionRead
from app.schemas.user import UserRead


class EntitlementsResponse(BaseModel):
    plan: str
    max_predictions_per_day: int
    used_predictions_today: int
    remaining_predictions_today: int
    history_limit: Optional[int]
    max_fields: int
    batch_csv_enabled: bool
    batch_max_rows: int
    remote_sensing_enabled: bool
    forecast_enabled: bool
    model_comparison_enabled: bool
    explainability_enabled: bool
    export_enabled: bool
    api_keys_enabled: bool


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str


class TOTPVerifyEnableRequest(BaseModel):
    code: str


class TOTPEnableResponse(BaseModel):
    status: str
    message: str
    recovery_codes: List[str]


class TOTPDisableRequest(BaseModel):
    code: str


class TOTPLoginChallengeRequest(BaseModel):
    temp_token: str
    code: Optional[str] = None
    recovery_code: Optional[str] = None


class AuditLogRead(BaseModel):
    id: uuid.UUID
    actor: str
    action: str
    target: Optional[str] = None
    metadata_json: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDataExportResponse(BaseModel):
    user: UserRead
    sessions: List[SessionRead]
    audit_events: List[AuditLogRead]
    exported_at: datetime
