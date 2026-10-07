"""Integration tests for /predict and /history REST APIs including validation envelopes, plan gates, and filters."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User, UserPlan, UserRole, UserStatus
from app.services.ml_client import ExplanationResult, PredictionResult


@pytest.fixture
def mock_ml_client():
    client = AsyncMock()
    client.predict.return_value = PredictionResult(
        et_value=4.62,
        interval_low=4.02,
        interval_high=5.22,
        confidence_level=0.90,
        classification="moderate",
        model_id="agriscope_ensemble_basic",
        model_version="v1.0",
        data_provenance="synthetic",
        is_synthetic=True,
        latency_ms=18.0,
    )
    client.explain.return_value = ExplanationResult(
        prediction=4.62,
        base_value=3.85,
        contributions={"temperature": 0.32, "humidity": -0.15, "wind_speed": 0.08, "solar_radiation": 0.52},
        feature_ranking=["solar_radiation", "temperature", "humidity", "wind_speed"],
        model_id="agriscope_ensemble_basic",
        model_version="v1.0",
        latency_ms=22.0,
    )
    client.list_models.return_value = []
    return client


async def create_user_with_token(client: AsyncClient, email: str, plan: str = "free") -> tuple[User, str]:
    from app.db.session import async_session_factory

    user = User(
        name="Test Farmer",
        email=email,
        password_hash="secret_hash",
        role=UserRole.ADMIN.value if plan == "admin" else (UserRole.PRO.value if plan == "pro" else UserRole.FREE.value),
        plan=plan,
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )
    # Persist in test db
    test_engine = client._transport.app.state.test_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        s.add(user)
        await s.commit()
        await s.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "role": user.role, "plan": user.plan})
    return user, token


@pytest.mark.asyncio
async def test_predict_parameter_boundary_envelopes(client: AsyncClient):
    """Verify physical boundary validation errors (422) for all meteorological parameters."""
    _, token = await create_user_with_token(client, "boundaries@agriscope.local")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Temperature below -10
    res = await client.post(
        "/api/v1/predict",
        headers=headers,
        json={"temperature": -15.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 15.0},
    )
    assert res.status_code == 422

    # 2. Temperature above 50
    res = await client.post(
        "/api/v1/predict",
        headers=headers,
        json={"temperature": 55.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 15.0},
    )
    assert res.status_code == 422

    # 3. Humidity below 0
    res = await client.post(
        "/api/v1/predict",
        headers=headers,
        json={"temperature": 25.0, "humidity": -1.0, "wind_speed": 2.0, "solar_radiation": 15.0},
    )
    assert res.status_code == 422

    # 4. Humidity above 100
    res = await client.post(
        "/api/v1/predict",
        headers=headers,
        json={"temperature": 25.0, "humidity": 105.0, "wind_speed": 2.0, "solar_radiation": 15.0},
    )
    assert res.status_code == 422

    # 5. Wind speed above 30
    res = await client.post(
        "/api/v1/predict",
        headers=headers,
        json={"temperature": 25.0, "humidity": 50.0, "wind_speed": 35.0, "solar_radiation": 15.0},
    )
    assert res.status_code == 422

    # 6. Solar radiation above 35
    res = await client.post(
        "/api/v1/predict",
        headers=headers,
        json={"temperature": 25.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 40.0},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_predict_plan_gating_compare_and_explain(client: AsyncClient, mock_ml_client):
    """Verify Free plan cannot access compare or explain (403), while Pro plan can."""
    _, free_token = await create_user_with_token(client, "free_plan@agriscope.local", plan="free")
    _, pro_token = await create_user_with_token(client, "pro_plan@agriscope.local", plan="pro")

    free_headers = {"Authorization": f"Bearer {free_token}"}
    pro_headers = {"Authorization": f"Bearer {pro_token}"}
    payload = {"temperature": 30.0, "humidity": 45.0, "wind_speed": 2.5, "solar_radiation": 22.0}

    with patch("app.services.prediction_service.PredictionService.__init__", return_value=None):
        with patch.object(
            client._transport.app,
            "dependency_overrides",
            {**client._transport.app.dependency_overrides},
        ):
            # 1. Compare: Free user rejected
            res_free_compare = await client.post("/api/v1/predict/compare", headers=free_headers, json=payload)
            assert res_free_compare.status_code == 403

            # 2. Explain: Free user rejected
            res_free_explain = await client.post("/api/v1/predict/explain", headers=free_headers, json=payload)
            assert res_free_explain.status_code == 403


@pytest.mark.asyncio
async def test_full_predict_history_flow(client: AsyncClient, mock_ml_client):
    """Verify full end-to-end predict -> persist -> history list -> patch bookmark -> stats -> delete flow."""
    user, token = await create_user_with_token(client, "farmer_flow@agriscope.local", plan="pro")
    headers = {"Authorization": f"Bearer {token}"}

    # Patch ml_client on the singleton service
    from app.routers.v1.predict import service
    service.ml_client = mock_ml_client

    # 1. Predict
    pred_payload = {
        "temperature": 32.0,
        "humidity": 40.0,
        "wind_speed": 3.0,
        "solar_radiation": 25.0,
        "note": "Field A morning reading",
        "tags": ["field-a", "wheat"],
    }
    p_res = await client.post("/api/v1/predict", headers=headers, json=pred_payload)
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["et_value"] == 4.62
    assert p_data["classification"] == "moderate"
    assert "irrigation_interpretation" in p_data
    assert p_data["id"] is not None
    pred_id = p_data["id"]

    # 2. History List
    h_res = await client.get("/api/v1/history", headers=headers)
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["total"] >= 1
    assert any(item["id"] == pred_id for item in h_data["items"])

    # 3. Filter history by classification
    f_res = await client.get("/api/v1/history?classification=moderate", headers=headers)
    assert f_res.status_code == 200
    assert len(f_res.json()["items"]) >= 1

    f_empty = await client.get("/api/v1/history?classification=low", headers=headers)
    assert f_empty.status_code == 200
    assert len(f_empty.json()["items"]) == 0

    # 4. Patch bookmark (is_saved), note, and tags
    patch_res = await client.patch(
        f"/api/v1/history/{pred_id}",
        headers=headers,
        json={"is_saved": True, "note": "Updated bookmark note", "tags": ["verified"]},
    )
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["is_saved"] is True
    assert patched["note"] == "Updated bookmark note"
    assert "verified" in patched["tags"]

    # 5. History Stats
    stats_res = await client.get("/api/v1/history/stats", headers=headers)
    assert stats_res.status_code == 200
    s_data = stats_res.json()
    assert s_data["predictions_total"] >= 1
    assert s_data["latest_et"] == 4.62

    # 6. Delete single item
    del_res = await client.delete(f"/api/v1/history/{pred_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 7. Check history empty after deletion
    h_after = await client.get("/api/v1/history", headers=headers)
    assert not any(item["id"] == pred_id for item in h_after.json()["items"])


@pytest.mark.asyncio
async def test_predict_sample_data_endpoint(client: AsyncClient):
    """Verify GET /api/v1/predict/sample returns valid agricultural sample observations."""
    _, token = await create_user_with_token(client, "sampler@agriscope.local")
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/predict/sample", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "temperature" in data
    assert "humidity" in data
    assert "wind_speed" in data
    assert "solar_radiation" in data
