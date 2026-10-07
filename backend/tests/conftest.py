"""Pytest fixtures and configuration."""

import os
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure development environment during testing
os.environ["ENVIRONMENT"] = "testing"
os.environ["STORAGE_PROVIDER"] = "mock"

from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402

# When using standard SQLite in-memory without SpatiaLite, geoalchemy2's DDL listeners fail on RecoverGeometryColumn
# and type compilation generates invalid syntax "geometry(GEOMETRY, 4326)" instead of simple "GEOMETRY".
import geoalchemy2.admin.dialects.sqlite as _geo_sqlite
from geoalchemy2.types import Geometry as _Geometry
from shapely import wkb as _wkb, wkt as _wkt
from sqlalchemy import event as _sa_event
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
from sqlalchemy.ext.compiler import compiles as _compiles

_geo_sqlite.before_create = lambda *args, **kwargs: None
_geo_sqlite.after_create = lambda *args, **kwargs: None
_Geometry.get_col_spec = lambda self, **kw: "GEOMETRY"


@_compiles(_PG_JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"



@pytest.fixture
def app():
    """Create test application instance with sqlite-backed in-memory database."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @_sa_event.listens_for(test_engine.sync_engine, "connect")
    def _sqlite_geo_funcs(dbapi_conn, _rec):
        def _geom_from_ewkt(val):
            if not val:
                return None
            wkt_part = val.split(";")[-1] if ";" in val else val
            return _wkb.dumps(_wkt.loads(wkt_part), hex=True)

        dbapi_conn.create_function("GeomFromEWKT", 1, _geom_from_ewkt)
        dbapi_conn.create_function("GeomFromEWKB", 1, lambda val: val)
        dbapi_conn.create_function("ST_AsEWKB", 1, lambda val: val)
        dbapi_conn.create_function("AsEWKB", 1, lambda val: val)
        dbapi_conn.create_function("ST_AsBinary", 1, lambda val: val)
        dbapi_conn.create_function("RecoverGeometryColumn", 5, lambda *a: 1)

    test_session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    application = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.state.test_engine = test_engine
    return application


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async test HTTP client."""
    test_engine = app.state.test_engine
    # Initialize required tables for test run
    async with test_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Base.metadata.tables["users"],
                    Base.metadata.tables["sessions"],
                    Base.metadata.tables["audit_logs"],
                    Base.metadata.tables["crops"],
                    Base.metadata.tables["crop_stages"],
                    Base.metadata.tables["ml_models"],
                    Base.metadata.tables["predictions"],
                    Base.metadata.tables["fields"],
                    Base.metadata.tables["field_observations"],
                    Base.metadata.tables["irrigation_events"],
                    Base.metadata.tables["batch_jobs"],
                    Base.metadata.tables["reports"],
                    Base.metadata.tables["notifications"],
                    Base.metadata.tables["notification_preferences"],
                    Base.metadata.tables["api_keys"],
                    Base.metadata.tables["subscriptions"],
                    Base.metadata.tables["training_datasets"],
                    Base.metadata.tables["shadow_results"],
                    Base.metadata.tables["feature_flags"],
                    Base.metadata.tables["announcements"],
                ],
            )
        )

    # Mock Celery delay calls
    from app.workers.tasks.emails import (
        send_password_reset_email_task,
        send_verification_email_task,
    )

    send_verification_email_task.delay = send_verification_email_task
    # Reset in-memory rate limiter between tests
    from app.core.rate_limit import RateLimiter
    RateLimiter.reset_memory()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    await test_engine.dispose()
