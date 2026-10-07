"""Admin audit log viewer router with filtering and pagination."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.admin import AdminUserAuditItem
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


@router.get("", response_model=PaginatedResponse[AdminUserAuditItem])
async def list_audit_logs(
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    target: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Query and filter immutable platform security and operational audit records."""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if actor:
        stmt = stmt.where(AuditLog.actor.ilike(f"%{actor}%"))
        count_stmt = count_stmt.where(AuditLog.actor.ilike(f"%{actor}%"))
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
        count_stmt = count_stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if target:
        stmt = stmt.where(AuditLog.target.ilike(f"%{target}%"))
        count_stmt = count_stmt.where(AuditLog.target.ilike(f"%{target}%"))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset((page - 1) * size).limit(size)
    logs = (await db.execute(stmt)).scalars().all()

    pages = (total + size - 1) // size if total > 0 else 1
    return PaginatedResponse(
        items=[AdminUserAuditItem.model_validate(l) for l in logs],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
