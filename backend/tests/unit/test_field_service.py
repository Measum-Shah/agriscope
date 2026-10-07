"""Unit tests for Field CRUD, geodesic area calculation, and plan entitlement limits."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException
from app.models.user import User, UserRole, UserStatus
from app.services.field_service import FieldService, calculate_polygon_area_ha

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [74.3000, 31.5000],
            [74.3100, 31.5000],
            [74.3100, 31.5100],
            [74.3000, 31.5100],
            [74.3000, 31.5000],
        ]
    ],
}


def test_calculate_polygon_area_ha():
    """Verify geodesic polygon area in hectares."""
    area_ha = calculate_polygon_area_ha(SAMPLE_POLYGON)
    # A ~0.01 x 0.01 degree box at lat 31.5 is roughly 100-120 ha
    assert 80.0 <= area_ha <= 150.0


@pytest.mark.asyncio
async def test_field_entitlement_enforcement_free_user(client):
    """Verify Free plan user cannot create more than 1 field."""
    from app.core.security import create_access_token

    test_engine = client._transport.app.state.test_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    user = User(
        name="Single Field Farmer",
        email="single_field@agriscope.local",
        password_hash="pw",
        role=UserRole.FREE.value,
        plan="free",
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )
    async with factory() as s:
        s.add(user)
        await s.commit()
        await s.refresh(user)

        service = FieldService(s)

        # 1. First field should succeed
        f1 = await service.create_field(user, "Field Alpha", SAMPLE_POLYGON)
        assert f1.name == "Field Alpha"
        assert f1.area_ha > 0

        # 2. Second field creation on Free plan should raise ForbiddenException
        with pytest.raises(ForbiddenException):
            await service.create_field(user, "Field Beta", SAMPLE_POLYGON)
