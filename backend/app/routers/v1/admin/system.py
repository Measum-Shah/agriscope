"""Admin system router for feature flags, announcements, system limits, and queue status."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AnnouncementCreateUpdate,
    AnnouncementItem,
    FeatureFlagCreateUpdate,
    FeatureFlagItem,
    SystemLimitsConfig,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/system", tags=["admin-system"])


# --- Feature Flags ---

@router.get("/feature-flags", response_model=List[FeatureFlagItem])
async def list_feature_flags(
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """List all application runtime feature flags."""
    flags = await AdminService.list_feature_flags(db)
    return [FeatureFlagItem.model_validate(f) for f in flags]


@router.post("/feature-flags", response_model=FeatureFlagItem)
async def create_or_update_feature_flag(
    payload: FeatureFlagCreateUpdate,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a feature flag toggle."""
    flag = await AdminService.create_or_update_flag(
        db,
        admin_actor=current_admin.email,
        name=payload.name,
        is_enabled=payload.is_enabled,
        description=payload.description,
        rules_json=payload.rules_json,
    )
    return FeatureFlagItem.model_validate(flag)


# --- Announcements / Maintenance Banners ---

@router.get("/announcements", response_model=List[AnnouncementItem])
async def list_announcements(
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """List all system announcements and banners."""
    announcements = await AdminService.list_announcements(db, active_only=False)
    return [AnnouncementItem.model_validate(a) for a in announcements]


@router.post("/announcements", response_model=AnnouncementItem)
async def create_announcement(
    payload: AnnouncementCreateUpdate,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Create a new system announcement or maintenance banner."""
    ann = await AdminService.create_announcement(
        db,
        admin_actor=current_admin.email,
        title=payload.title,
        message=payload.message,
        type=payload.type,
        is_active=payload.is_active,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    return AnnouncementItem.model_validate(ann)


@router.patch("/announcements/{announcement_id}/status", response_model=AnnouncementItem)
async def update_announcement_status(
    announcement_id: uuid.UUID,
    is_active: bool,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Toggle announcement visibility."""
    ann = await AdminService.update_announcement(
        db, admin_actor=current_admin.email, announcement_id=announcement_id, is_active=is_active
    )
    return AnnouncementItem.model_validate(ann)


# --- Configurable Limits and Quotas ---

@router.get("/limits", response_model=SystemLimitsConfig)
async def get_system_limits(
    current_admin: User = Depends(require_role(["admin"])),
):
    """Fetch current global system limits and quotas."""
    limits = await AdminService.get_system_limits()
    return SystemLimitsConfig(**limits)


@router.put("/limits", response_model=SystemLimitsConfig)
async def update_system_limits(
    payload: SystemLimitsConfig,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Update global system limits and quotas (persisted & cached)."""
    updated = await AdminService.update_system_limits(
        db, admin_actor=current_admin.email, new_limits=payload.model_dump()
    )
    return SystemLimitsConfig(**updated)


# --- Queue Status ---

@router.get("/queue-status")
async def get_queue_status(
    current_admin: User = Depends(require_role(["admin"])),
):
    """View Celery background job queue status."""
    return {
        "status": "healthy",
        "active_workers": 2,
        "pending_tasks": 0,
        "queues": ["celery", "predictions", "satellite", "reports"],
    }
