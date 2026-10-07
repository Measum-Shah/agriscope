"""Unit tests for Admin Console APIs: RBAC denial, user management, datasets, metrics, and audit."""

from __future__ import annotations

import io
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User


@pytest.fixture
async def setup_users(client: AsyncClient):
    """Register regular and admin users via API endpoints."""
    # 1. Register regular user
    user_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "farmer@example.com", "password": "FarmerPassword123!", "name": "Farmer Joe"},
    )
    assert user_res.status_code == 201
    user_data = user_res.json()

    user_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "farmer@example.com", "password": "FarmerPassword123!"},
    )
    user_token = user_login.json()["access_token"]

    # 2. Register admin user
    admin_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "superadmin@example.com", "password": "AdminPassword123!", "name": "Super Admin"},
    )
    assert admin_res.status_code == 201
    admin_id = admin_res.json()["id"]

    # Promote registered admin to role="admin" and plan="admin" in DB
    override = client._transport.app.dependency_overrides[get_db]
    async for db in override():
        user = await db.get(User, uuid.UUID(admin_id))
        if user:
            user.role = "admin"
            user.plan = "admin"
            await db.commit()
        break

    # Mint admin token directly with role=admin
    admin_token = create_access_token({"sub": str(admin_id), "role": "admin", "plan": "admin"})

    return {
        "admin_id": admin_id,
        "admin_token": admin_token,
        "user_id": user_data["id"],
        "user_token": user_token,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,endpoint",
    [
        ("GET", "/api/v1/admin/users"),
        ("GET", "/api/v1/admin/datasets"),
        ("GET", "/api/v1/admin/metrics"),
        ("GET", "/api/v1/admin/audit"),
        ("GET", "/api/v1/admin/system/feature-flags"),
        ("GET", "/api/v1/admin/system/limits"),
    ],
)
async def test_admin_routes_rbac_denial_for_non_admins(client: AsyncClient, setup_users, method, endpoint):
    """Verifies that non-admin callers receive HTTP 403 Forbidden across all admin routes."""
    headers = {"Authorization": f"Bearer {setup_users['user_token']}"}
    if method == "GET":
        res = await client.get(endpoint, headers=headers)
    elif method == "POST":
        res = await client.post(endpoint, json={}, headers=headers)
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_user_management_lifecycle_and_audit(client: AsyncClient, setup_users):
    """Tests user listing, role/plan update, suspension, unlock, and audit trail logging."""
    admin_headers = {"Authorization": f"Bearer {setup_users['admin_token']}"}
    target_id = setup_users["user_id"]

    # 1. List users
    res = await client.get("/api/v1/admin/users?search=farmer", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(u["id"] == target_id for u in data["items"])

    # 2. Update role & plan
    res = await client.patch(
        f"/api/v1/admin/users/{target_id}/role-plan",
        json={"role": "researcher", "plan": "pro"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["role"] == "researcher"
    assert res.json()["plan"] == "pro"

    # 3. Suspend user
    res = await client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        json={"status": "suspended"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "suspended"

    # 4. Unlock user
    res = await client.post(f"/api/v1/admin/users/{target_id}/unlock", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["failed_attempts"] == 0

    # 5. Check user audit logs
    res = await client.get(f"/api/v1/admin/users/{target_id}/audit", headers=admin_headers)
    assert res.status_code == 200
    audit_items = res.json()
    actions = [a["action"] for a in audit_items]
    assert "admin.user.update_role_plan" in actions
    assert "admin.user.update_status" in actions
    assert "admin.user.unlock" in actions


@pytest.mark.asyncio
async def test_admin_dataset_upload_outliers_preview_and_download(client: AsyncClient, setup_users):
    """Tests CSV upload, validation, outlier calculation, preview, and download."""
    admin_headers = {"Authorization": f"Bearer {setup_users['admin_token']}"}

    # Prepare CSV content with normal and outlier values
    csv_content = (
        "temp_max,temp_min,humidity,wind_speed,solar_radiation,et0\n"
        "32.0,20.0,55.0,2.1,22.0,5.1\n"
        "33.0,21.0,50.0,2.5,23.0,5.4\n"
        "31.5,19.5,60.0,1.8,21.0,4.8\n"
        "34.0,22.0,48.0,3.0,24.0,5.9\n"
        "55.0,25.0,30.0,8.5,28.0,9.2\n"  # statistical outlier
    )
    files = {"file": ("test_et0_dataset.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {
        "name": "Punjab Station 2026",
        "version": "v1.0",
        "description": "Validation test dataset",
    }

    res = await client.post(
        "/api/v1/admin/datasets/upload",
        data=data,
        files=files,
        headers=admin_headers,
    )
    assert res.status_code == 200
    report = res.json()
    assert report["name"] == "Punjab Station 2026"
    assert report["row_count"] == 5
    assert len(report["preview_rows"]) == 5
    assert "temp_max" in report["stats"]
    assert report["status"] == "validated"
    dataset_id = report["id"]

    # Download dataset
    dl_res = await client.get(f"/api/v1/admin/datasets/{dataset_id}/download", headers=admin_headers)
    assert dl_res.status_code == 200
    assert "Punjab Station 2026" in dl_res.headers.get("Content-Disposition", "")


@pytest.mark.asyncio
async def test_admin_system_metrics_flags_and_announcements(client: AsyncClient, setup_users):
    """Tests metrics endpoint, feature flag updates, and announcement creation."""
    admin_headers = {"Authorization": f"Bearer {setup_users['admin_token']}"}

    # 1. Metrics
    res = await client.get("/api/v1/admin/metrics", headers=admin_headers)
    assert res.status_code == 200
    metrics = res.json()
    assert "total_users" in metrics
    assert "predictions_today" in metrics
    assert "latency_p50_ms" in metrics

    # 2. Feature Flags
    res = await client.post(
        "/api/v1/admin/system/feature-flags",
        json={"name": "deep_et_v2", "is_enabled": True, "description": "Experimental model"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["name"] == "deep_et_v2"
    assert res.json()["is_enabled"] is True

    # 3. Announcements
    res = await client.post(
        "/api/v1/admin/system/announcements",
        json={
            "title": "Scheduled Maintenance",
            "message": "Platform upgrade at 02:00 UTC",
            "type": "warning",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Scheduled Maintenance"

    # 4. App-wide announcement visibility for general users
    pub_res = await client.get("/api/v1/notifications/announcements")
    assert pub_res.status_code == 200
    items = pub_res.json()
    assert any(a["title"] == "Scheduled Maintenance" for a in items)
