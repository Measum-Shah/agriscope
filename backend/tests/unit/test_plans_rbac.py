"""Tests for Entitlements, Quotas, Plans, and RBAC."""

from __future__ import annotations

import pytest

from app.core.deps import require_role
from app.core.exceptions import ForbiddenException
from app.core.plans import (
    QuotaService,
    get_plan_limits,
    require_plan_feature,
)
from app.models.user import User, UserPlan, UserRole


def test_plan_entitlements_matrix():
    """Verify exact limits and features across Free, Pro, and Admin tiers."""
    # Free
    free = get_plan_limits("free")
    assert free.max_predictions_per_day == 30
    assert free.history_limit == 50
    assert free.max_fields == 1
    assert free.batch_csv_enabled is False
    assert free.batch_max_rows == 0
    assert free.remote_sensing_enabled is False
    assert free.forecast_enabled is False
    assert free.model_comparison_enabled is False
    assert free.explainability_enabled is False
    assert free.export_enabled is False
    assert free.api_keys_enabled is False

    # Pro
    pro = get_plan_limits("pro")
    assert pro.max_predictions_per_day == 1000
    assert pro.history_limit is None  # unlimited
    assert pro.max_fields == 50
    assert pro.batch_csv_enabled is True
    assert pro.batch_max_rows == 10000
    assert pro.remote_sensing_enabled is True
    assert pro.forecast_enabled is True
    assert pro.model_comparison_enabled is True
    assert pro.explainability_enabled is True
    assert pro.export_enabled is True
    assert pro.api_keys_enabled is True

    # Admin
    admin = get_plan_limits("admin")
    assert admin.max_predictions_per_day >= 50000
    assert admin.max_fields >= 1000
    assert admin.export_enabled is True


@pytest.mark.asyncio
async def test_quota_service_increment_and_reset():
    """Verify daily prediction quota tracking and reset."""
    user_id = "user-12345"
    QuotaService.reset_memory_quota()

    # Initial usage
    used = await QuotaService.get_used_predictions_today(user_id)
    assert used == 0

    # Increment
    new_used = await QuotaService.increment_predictions_today(user_id, count=5)
    assert new_used == 5
    assert await QuotaService.get_used_predictions_today(user_id) == 5

    # Increment more
    await QuotaService.increment_predictions_today(user_id, count=25)
    assert await QuotaService.get_used_predictions_today(user_id) == 30

    # Reset
    QuotaService.reset_memory_quota()
    assert await QuotaService.get_used_predictions_today(user_id) == 0


@pytest.mark.asyncio
async def test_require_plan_feature_dependency():
    """Verify feature gate dependency for plans."""
    free_user = User(
        name="Free User", email="free@test.com", plan=UserPlan.FREE.value, role=UserRole.FREE.value
    )
    pro_user = User(
        name="Pro User", email="pro@test.com", plan=UserPlan.PRO.value, role=UserRole.PRO.value
    )

    batch_check = require_plan_feature("batch_csv_enabled")
    rs_check = require_plan_feature("remote_sensing_enabled")

    # Free user rejected
    with pytest.raises(ForbiddenException, match="requires an upgraded subscription"):
        await batch_check(free_user)
    with pytest.raises(ForbiddenException, match="requires an upgraded subscription"):
        await rs_check(free_user)

    # Pro user allowed
    assert await batch_check(pro_user) == pro_user
    assert await rs_check(pro_user) == pro_user


@pytest.mark.asyncio
async def test_require_role_rbac_dependency():
    """Verify role-based access control dependency."""
    free_user = User(name="Free User", email="free@test.com", role=UserRole.FREE.value)
    pro_user = User(name="Pro User", email="pro@test.com", role=UserRole.PRO.value)
    admin_user = User(name="Admin User", email="admin@test.com", role=UserRole.ADMIN.value)

    admin_guard = require_role(["admin"])
    pro_or_admin_guard = require_role(["pro", "admin"])

    # Test admin guard
    with pytest.raises(ForbiddenException, match="Insufficient permissions"):
        await admin_guard(free_user)
    with pytest.raises(ForbiddenException, match="Insufficient permissions"):
        await admin_guard(pro_user)
    assert await admin_guard(admin_user) == admin_user

    # Test pro or admin guard
    with pytest.raises(ForbiddenException):
        await pro_or_admin_guard(free_user)
    assert await pro_or_admin_guard(pro_user) == pro_user
    assert await pro_or_admin_guard(admin_user) == admin_user
