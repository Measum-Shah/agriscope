"""Notification domain service managing in-app, email alerts, and Server-Sent Events."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.notification import Notification, NotificationPreference
from app.models.user import User


class SSEConnectionManager:
    """Manages active Server-Sent Event subscriber queues."""

    _subscribers: Dict[uuid.UUID, List[asyncio.Queue]] = {}

    @classmethod
    async def subscribe(cls, user_id: uuid.UUID) -> AsyncGenerator[str, None]:
        """Subscribe user connection to receive live SSE events."""
        queue: asyncio.Queue = asyncio.Queue()
        if user_id not in cls._subscribers:
            cls._subscribers[user_id] = []
        cls._subscribers[user_id].append(queue)
        logger.info("SSE client connected", user_id=str(user_id))

        try:
            # Send initial keepalive
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            if user_id in cls._subscribers and queue in cls._subscribers[user_id]:
                cls._subscribers[user_id].remove(queue)
                if not cls._subscribers[user_id]:
                    del cls._subscribers[user_id]
            logger.info("SSE client disconnected", user_id=str(user_id))

    @classmethod
    async def broadcast_to_user(
        cls, user_id: uuid.UUID, event_type: str, payload: Dict[str, Any]
    ) -> None:
        """Push an SSE notification event to all active sessions for a user."""
        if user_id not in cls._subscribers:
            return

        sse_message = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        for queue in cls._subscribers[user_id]:
            await queue.put(sse_message)


class NotificationService:
    """Manages notification storage, read state, user preferences, and real-time dispatch."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_notifications(
        self, user: User, unread_only: bool = False, limit: int = 50
    ) -> List[Notification]:
        """Fetch notification history for a user."""
        stmt = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_read(
        self, notification_id: uuid.UUID, user: User
    ) -> Notification:
        """Mark single notification as read."""
        stmt = select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
        res = await self.session.execute(stmt)
        notif = res.scalar_one_or_none()
        if not notif:
            raise NotFoundException(detail="Notification not found.")
        notif.is_read = True
        await self.session.commit()
        await self.session.refresh(notif)
        return notif

    async def mark_all_as_read(self, user: User) -> int:
        """Mark all notifications as read for a user."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user.id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount

    async def create_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        type_: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Persist notification and broadcast via SSE."""
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type_,
            metadata_json=metadata or {},
        )
        self.session.add(notif)
        await self.session.commit()
        await self.session.refresh(notif)

        # Broadcast live to connected browser clients
        await SSEConnectionManager.broadcast_to_user(
            user_id=user_id,
            event_type="notification",
            payload={
                "id": str(notif.id),
                "title": notif.title,
                "message": notif.message,
                "type": notif.type,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
                "metadata": notif.metadata_json,
            },
        )
        return notif

    async def get_preferences(self, user: User) -> NotificationPreference:
        """Retrieve user notification preferences or initialize default."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user.id
        )
        res = await self.session.execute(stmt)
        pref = res.scalar_one_or_none()
        if not pref:
            pref = NotificationPreference(
                user_id=user.id,
                email_enabled=True,
                sms_enabled=False,
                in_app_enabled=True,
                irrigation_alerts=True,
                system_announcements=True,
            )
            self.session.add(pref)
            await self.session.commit()
            await self.session.refresh(pref)
        return pref

    async def update_preferences(
        self, user: User, updates: Dict[str, Any]
    ) -> NotificationPreference:
        """Update notification delivery preferences."""
        pref = await self.get_preferences(user)
        for field, val in updates.items():
            if hasattr(pref, field) and val is not None:
                setattr(pref, field, val)
        await self.session.commit()
        await self.session.refresh(pref)
        return pref
