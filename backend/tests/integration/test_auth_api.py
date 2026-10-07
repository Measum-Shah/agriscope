"""Integration tests for Auth API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.providers.email.smtp import MockEmailProvider


@pytest.fixture(autouse=True)
def clean_emails():
    MockEmailProvider.clear()
    yield
    MockEmailProvider.clear()


@pytest.mark.asyncio
async def test_auth_router_full_http_flow(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "name": "Integration Tester",
        "email": "integration@test.com",
        "password": "IntegrationPassword2026!",
    }
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["email"] == "integration@test.com"

    # 2. Login
    login_payload = {
        "email": "integration@test.com",
        "password": "IntegrationPassword2026!",
    }
    res = await client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    access_token = token_data["access_token"]
    assert "refresh_token" in res.cookies

    # 3. Access protected /me
    headers = {"Authorization": f"Bearer {access_token}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "integration@test.com"

    # 4. Refresh token
    res = await client.post("/api/v1/auth/refresh", cookies=res.cookies)
    assert res.status_code == 200
    new_token_data = res.json()
    assert "access_token" in new_token_data

    # 5. List sessions
    res = await client.get("/api/v1/auth/sessions", headers=headers)
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) >= 1

    # 6. Logout
    res = await client.post("/api/v1/auth/logout", cookies=res.cookies)
    assert res.status_code == 200
