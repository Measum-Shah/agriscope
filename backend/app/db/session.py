"""Async SQLAlchemy session manager and engine."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy import event
from app.core.config import settings

db_url = str(settings.DATABASE_URL)
is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    import geoalchemy2.admin.dialects.sqlite as _geo_sqlite
    from geoalchemy2.types import Geometry as _Geometry
    from shapely import wkb as _wkb, wkt as _wkt
    from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
    from sqlalchemy.ext.compiler import compiles as _compiles

    _geo_sqlite.before_create = lambda *args, **kwargs: None
    _geo_sqlite.after_create = lambda *args, **kwargs: None
    _Geometry.get_col_spec = lambda self, **kw: "GEOMETRY"

    @_compiles(_PG_JSONB, "sqlite")
    def _compile_jsonb_sqlite(type_, compiler, **kw):
        return "JSON"

    engine = create_async_engine(db_url, echo=False, future=True)

    @event.listens_for(engine.sync_engine, "connect")
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
else:
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency providing an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
