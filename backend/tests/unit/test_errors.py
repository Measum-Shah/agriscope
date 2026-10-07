"""Tests for error handlers and request ID middleware."""

import pytest
from httpx import AsyncClient

from app.core.exceptions import AgriScopeException


@pytest.mark.asyncio
async def test_custom_exception_response_format(app, client: AsyncClient):
    @app.get("/test-error")
    async def trigger_error():
        raise AgriScopeException(
            detail="Test custom error",
            code="TEST_ERROR",
            status_code=400,
        )

    response = await client.get("/test-error")
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Test custom error"
    assert data["code"] == "TEST_ERROR"
    assert "request_id" in data
    assert data["request_id"] != ""
