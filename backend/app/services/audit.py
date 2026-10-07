"""Audit logging service for tracking system and security events."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        actor: str,
        action: str,
        target: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Records an audit log entry."""
        audit_entry = AuditLog(
            actor=actor,
            action=action,
            target=target,
            metadata_json=metadata_json or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_entry)
        await db.commit()
        logger.info(f"[Audit] actor={actor} action={action} target={target}")
        return audit_entry
