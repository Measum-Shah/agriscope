"""Notifications API router with in-app center, preferences, and real-time SSE streaming."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.jobs import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
)
from app.services.notification_service import NotificationService, SSEConnectionManager

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notification history for the authenticated user."""
    service = NotificationService(db)
    return await service.list_notifications(current_user, unread_only=unread_only, limit=limit)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a specific notification as read."""
    service = NotificationService(db)
    return await service.mark_as_read(notification_id, current_user)


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user)
    return {"ok": True, "marked_count": count}


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve notification delivery preferences."""
    service = NotificationService(db)
    return await service.get_preferences(current_user)


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification delivery preferences."""
    service = NotificationService(db)
    return await service.update_preferences(current_user, payload.model_dump(exclude_unset=True))


@router.get("/announcements", response_model=List[dict])
async def get_active_announcements(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve active system announcements and maintenance banners for all users."""
    from app.services.admin_service import AdminService
    announcements = await AdminService.list_announcements(db, active_only=True)
    return [
        {
            "id": str(a.id),
            "title": a.title,
            "message": a.message,
            "type": a.type,
            "is_active": a.is_active,
        }
        for a in announcements
    ]


@router.get("/stream")
async def stream_notifications(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Server-Sent Events (SSE) live event stream for user."""
    return StreamingResponse(
        SSEConnectionManager.subscribe(current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

