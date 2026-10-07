"""Pydantic schemas for Batch Predictions, Reports, and Notifications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# Batch Schemas
class BatchJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    total_rows: int
    processed_rows: int
    error_summary: Dict[str, Any]
    output_file_uri: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchJobCreateResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    total_rows: int
    message: str


# Report Schemas
class ReportCreateRequest(BaseModel):
    title: str = Field(..., max_length=200)
    format: str = Field(default="pdf", description="Format: pdf, csv, xlsx, png")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ReportResponse(BaseModel):
    id: uuid.UUID
    title: str
    format: str
    file_size_bytes: int
    status: str
    download_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Notification Schemas
class NotificationResponse(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    type: str
    is_read: bool
    metadata_json: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceResponse(BaseModel):
    email_enabled: bool
    sms_enabled: bool
    in_app_enabled: bool
    irrigation_alerts: bool
    system_announcements: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    irrigation_alerts: Optional[bool] = None
    system_announcements: Optional[bool] = None
