"""Admin users router for user administration, role/plan updates, lockout release, and session termination."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminUserAuditItem,
    AdminUserItem,
    AdminUserStatusUpdate,
    AdminUserUpdateRolePlan,
)
from app.schemas.common import PaginatedResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=PaginatedResponse[AdminUserItem])
async def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Search, filter, and paginate all platform users."""
    users, total = await AdminService.list_users(
        db, search=search, role=role, plan=plan, status=status_filter, page=page, size=size
    )
    pages = (total + size - 1) // size if total > 0 else 1
    return PaginatedResponse(
        items=[AdminUserItem.model_validate(u) for u in users],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=AdminUserItem)
async def get_user_detail(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed user account."""
    user = await AdminService.get_user(db, user_id)
    return AdminUserItem.model_validate(user)


@router.patch("/{user_id}/role-plan", response_model=AdminUserItem)
async def update_role_plan(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRolePlan,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role and/or subscription plan."""
    user = await AdminService.update_user_role_plan(
        db,
        admin_actor=current_admin.email,
        user_id=user_id,
        role=payload.role,
        plan=payload.plan,
    )
    return AdminUserItem.model_validate(user)


@router.patch("/{user_id}/status", response_model=AdminUserItem)
async def update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdate,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Suspend or activate a user account."""
    user = await AdminService.update_user_status(
        db,
        admin_actor=current_admin.email,
        user_id=user_id,
        status=payload.status,
    )
    return AdminUserItem.model_validate(user)


@router.post("/{user_id}/unlock", response_model=AdminUserItem)
async def unlock_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Manually clear failed login attempts and lockout timestamp."""
    user = await AdminService.unlock_user(
        db, admin_actor=current_admin.email, user_id=user_id
    )
    return AdminUserItem.model_validate(user)


@router.post("/{user_id}/force-logout")
async def force_logout_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Terminate all active authentication sessions for the target user."""
    revoked_count = await AdminService.force_logout_user(
        db, admin_actor=current_admin.email, user_id=user_id
    )
    return {"success": True, "revoked_sessions": revoked_count}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a user account and associated credentials."""
    await AdminService.delete_user(db, admin_actor=current_admin.email, user_id=user_id)


@router.get("/{user_id}/audit", response_model=List[AdminUserAuditItem])
async def get_user_audit(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """View user-specific security and operational audit trail."""
    user = await AdminService.get_user(db, user_id)
    logs = await AdminService.get_user_audit(db, user_identifier=str(user.id), user_email=user.email)
    return [AdminUserAuditItem.model_validate(log) for log in logs]

