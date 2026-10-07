"""Unit tests for ML model lifecycle management: training, quality guards, approval, rollback, shadow mode, and drift."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.ml_model import MLModel, ModelStatus
from app.models.training_dataset import TrainingDataset
from app.models.user import User


@pytest.fixture
async def setup_admin_and_dataset(client: AsyncClient):
    """Set up admin user and sample validated dataset."""
    admin_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "mladmin@example.com", "password": "AdminPassword123!", "name": "ML Admin"},
    )
    admin_id = admin_res.json()["id"]

    override = client._transport.app.dependency_overrides[get_db]
    dataset_id = uuid.uuid4()
    async for db in override():
        user = await db.get(User, uuid.UUID(admin_id))
        if user:
            user.role = "admin"
            user.plan = "admin"
        ds = TrainingDataset(
            id=dataset_id,
            name="Punjab Weather ET",
            version="v1.0",
            file_uri="datasets/test_et.csv",
            file_hash="dummyhash123",
            status="validated",
            data_provenance="real_derived",
            stats_json={"row_count": 100},
        )
        db.add(ds)
        await db.commit()
        break

    admin_token = create_access_token({"sub": str(admin_id), "role": "admin", "plan": "admin"})
    user_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "regular@example.com", "password": "UserPassword123!", "name": "Regular User"},
    )
    user_token = create_access_token({"sub": user_res.json()["id"], "role": "user", "plan": "free"})

    return {"admin_token": admin_token, "user_token": user_token, "dataset_id": str(dataset_id)}


@pytest.mark.asyncio
async def test_admin_models_rbac(client: AsyncClient, setup_admin_and_dataset):
    """Non-admin user requests to /admin/models must receive 403 Forbidden."""
    u_token = setup_admin_and_dataset["user_token"]
    res = await client.get("/api/v1/admin/models", headers={"Authorization": f"Bearer {u_token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_train_model_trigger_and_job_status(client: AsyncClient, setup_admin_and_dataset):
    """Admin can trigger training job and query task status."""
    a_token, ds_id = setup_admin_and_dataset["admin_token"], setup_admin_and_dataset["dataset_id"]

    with patch("app.routers.v1.admin.models.train_models_task.delay") as mock_delay:
        mock_task = MagicMock(id="mock-task-1234")
        mock_delay.return_value = mock_task

        res = await client.post(
            "/api/v1/admin/models/train",
            json={"dataset_id": ds_id, "algorithms": ["random_forest"], "feature_schema": "basic"},
            headers={"Authorization": f"Bearer {a_token}"},
        )
        assert res.status_code == 202
        assert res.json()["task_id"] == "mock-task-1234"

    with patch("app.routers.v1.admin.models.AsyncResult") as mock_async_result:
        mock_ar = MagicMock(state="PROGRESS", info={"progress": 45.0, "step": "Training RF"}, result=None)
        mock_async_result.return_value = mock_ar

        job_res = await client.get(
            "/api/v1/admin/models/jobs/mock-task-1234",
            headers={"Authorization": f"Bearer {a_token}"},
        )
        assert job_res.status_code == 200
        assert job_res.json()["state"] == "PROGRESS"


@pytest.mark.asyncio
async def test_model_approval_guards_and_hot_swap(client: AsyncClient, setup_admin_and_dataset):
    """Model approval enforces metric guards unless force=True; performs hot swap."""
    a_token = setup_admin_and_dataset["admin_token"]
    override = client._transport.app.dependency_overrides[get_db]

    m_low_id, m_high_id = uuid.uuid4(), uuid.uuid4()
    async for db in override():
        m_low = MLModel(
            id=m_low_id, name="agriscope_weak", algorithm="random_forest", version="v1.1-weak",
            metrics_json={"random_split": {"r2": 0.55, "rmse": 2.10, "mae": 1.50}},
            artifact_uri="ml/weak", status=ModelStatus.PENDING_APPROVAL.value, data_provenance="real_derived",
        )
        m_high = MLModel(
            id=m_high_id, name="agriscope_strong", algorithm="random_forest", version="v1.2-strong",
            metrics_json={"random_split": {"r2": 0.88, "rmse": 0.65, "mae": 0.45}},
            artifact_uri="ml/strong", status=ModelStatus.PENDING_APPROVAL.value, data_provenance="real_derived",
        )
        db.add_all([m_low, m_high])
        await db.commit()
        break

    with patch("app.services.model_service.MLClient.load_model") as mock_load:
        mock_load.return_value = {"status": "loaded"}

        # Low quality fails guard
        fail_res = await client.post(
            f"/api/v1/admin/models/{m_low_id}/approve", json={"force": False},
            headers={"Authorization": f"Bearer {a_token}"},
        )
        assert fail_res.status_code == 400
        assert "failed quality gate" in fail_res.json()["detail"].lower()

        # Low quality succeeds with force=True
        force_res = await client.post(
            f"/api/v1/admin/models/{m_low_id}/approve", json={"force": True},
            headers={"Authorization": f"Bearer {a_token}"},
        )
        assert force_res.status_code == 200
        assert force_res.json()["status"] == "active"

        # High quality succeeds normally and archives previous active
        high_res = await client.post(
            f"/api/v1/admin/models/{m_high_id}/approve", json={"force": False},
            headers={"Authorization": f"Bearer {a_token}"},
        )
        assert high_res.status_code == 200
        assert high_res.json()["status"] == "active"

    async for db in override():
        m_prev = await db.get(MLModel, m_low_id)
        assert m_prev.status == ModelStatus.ARCHIVED.value
        break


@pytest.mark.asyncio
async def test_reject_and_rollback_model(client: AsyncClient, setup_admin_and_dataset):
    """Admin can reject candidate model with reason and rollback to archived version."""
    a_token = setup_admin_and_dataset["admin_token"]
    override = client._transport.app.dependency_overrides[get_db]

    m_cand_id, m_act_id, m_arch_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async for db in override():
        cand = MLModel(
            id=m_cand_id, name="mlp_test", algorithm="mlp", version="v2.0-test",
            metrics_json={"random_split": {"r2": 0.75, "rmse": 0.90}}, artifact_uri="ml/mlp",
            status=ModelStatus.PENDING_APPROVAL.value, data_provenance="real_derived",
        )
        act = MLModel(
            id=m_act_id, name="rf_act", algorithm="random_forest", version="v1.0-act",
            metrics_json={"random_split": {"r2": 0.82, "rmse": 0.80}}, artifact_uri="ml/rf",
            status=ModelStatus.ACTIVE.value, data_provenance="real_derived",
        )
        arch = MLModel(
            id=m_arch_id, name="xgb_arch", algorithm="xgboost", version="v0.9-arch",
            metrics_json={"random_split": {"r2": 0.80, "rmse": 0.85}}, artifact_uri="ml/xgb",
            status=ModelStatus.ARCHIVED.value, data_provenance="real_derived",
        )
        db.add_all([cand, act, arch])
        await db.commit()
        break

    empty_rej = await client.post(
        f"/api/v1/admin/models/{m_cand_id}/reject", json={"reason": "  "},
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert empty_rej.status_code in (400, 422)

    rej_res = await client.post(
        f"/api/v1/admin/models/{m_cand_id}/reject",
        json={"reason": "High variance observed in arid test zones."},
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"

    with patch("app.services.model_service.MLClient.load_model") as mock_load:
        mock_load.return_value = {"status": "loaded"}
        roll_res = await client.post(
            "/api/v1/admin/models/rollback", json={},
            headers={"Authorization": f"Bearer {a_token}"},
        )
        assert roll_res.status_code == 200
        assert roll_res.json()["status"] == "active"
        assert roll_res.json()["id"] == str(m_arch_id)


@pytest.mark.asyncio
async def test_shadow_mode_and_reports(client: AsyncClient, setup_admin_and_dataset):
    """Toggle shadow mode for pending model and view champion/challenger report."""
    a_token = setup_admin_and_dataset["admin_token"]
    override = client._transport.app.dependency_overrides[get_db]

    cand_id = uuid.uuid4()
    async for db in override():
        cand = MLModel(
            id=cand_id, name="lgb_shadow", algorithm="lightgbm", version="v3.0-shadow",
            metrics_json={"random_split": {"r2": 0.86, "rmse": 0.70}}, artifact_uri="ml/lgb",
            status=ModelStatus.PENDING_APPROVAL.value, data_provenance="real_derived",
        )
        db.add(cand)
        await db.commit()
        break

    shad_res = await client.post(
        f"/api/v1/admin/models/{cand_id}/shadow", json={"enabled": True},
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert shad_res.status_code == 200
    assert shad_res.json()["metrics_json"]["shadow_mode"] is True

    rep_res = await client.get(
        f"/api/v1/admin/models/{cand_id}/shadow-report",
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert rep_res.status_code == 200
    assert rep_res.json()["candidate_model_id"] == str(cand_id)
    assert "mean_difference" in rep_res.json()


@pytest.mark.asyncio
async def test_compare_and_drift_check(client: AsyncClient, setup_admin_and_dataset):
    """Admin can compare models side-by-side and execute dataset drift check."""
    a_token = setup_admin_and_dataset["admin_token"]
    override = client._transport.app.dependency_overrides[get_db]

    m1_id, m2_id = uuid.uuid4(), uuid.uuid4()
    async for db in override():
        m1 = MLModel(
            id=m1_id, name="model_a", algorithm="random_forest", version="vA",
            metrics_json={"random_split": {"r2": 0.85, "rmse": 0.75, "mae": 0.50}},
            artifact_uri="ml/a", status=ModelStatus.ACTIVE.value, data_provenance="real_derived",
        )
        m2 = MLModel(
            id=m2_id, name="model_b", algorithm="xgboost", version="vB",
            metrics_json={"random_split": {"r2": 0.90, "rmse": 0.60, "mae": 0.40}},
            artifact_uri="ml/b", status=ModelStatus.PENDING_APPROVAL.value, data_provenance="real_derived",
        )
        db.add_all([m1, m2])
        await db.commit()
        break

    comp_res = await client.post(
        "/api/v1/admin/models/compare", json={"model_ids": [str(m1_id), str(m2_id)]},
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert comp_res.status_code == 200
    assert len(comp_res.json()["models"]) == 2
    assert "r2" in comp_res.json()["metrics_matrix"]

    drift_res = await client.post(
        "/api/v1/admin/models/drift-check",
        json={"window_days": 30, "psi_threshold": 0.20, "ks_alpha": 0.05},
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert drift_res.status_code == 200
    assert "drift_detected" in drift_res.json()
    assert "feature_results" in drift_res.json()
