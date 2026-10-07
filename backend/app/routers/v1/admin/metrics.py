"""Admin metrics router for system health, user counts, prediction throughput, and latency."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import SystemMetricsResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/metrics", tags=["admin-metrics"])


@router.get("", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_admin: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve operational metrics including active users, predictions, error rate, and latencies."""
    metrics_data = await AdminService.get_system_metrics(db)
    return SystemMetricsResponse(**metrics_data)
