"""Main FastAPI Application factory for AgriScope API."""

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.exceptions import AgriScopeException
from app.core.logging import logger, setup_logging
from app.db.session import engine
from app.schemas.common import HealthResponse, ReadinessResponse

# Prometheus metrics
REQUEST_COUNT = Counter(
    "agriscope_http_requests_total",
    "Total HTTP requests handled by AgriScope backend",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "agriscope_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns unique X-Request-ID to every request and injects into state."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.time()
        endpoint = request.url.path

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).inc()
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)
        except Exception:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=500,
            ).inc()
            raise

        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all API responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Remove server info if present
        if "server" in response.headers:
            del response.headers["server"]
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    setup_logging(settings.LOG_LEVEL)
    logger.info("AgriScope API starting up...")
    yield
    logger.info("AgriScope API shutting down. Disposing engine connections...")
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory for AgriScope FastAPI backend."""
    app = FastAPI(
        title="AgriScope API",
        version="0.1.0",
        description="Production-grade AI Evapotranspiration Platform API",
        lifespan=lifespan,
    )

    # Routers
    from app.routers.v1.api_keys import router as api_keys_router
    from app.routers.v1.auth import router as auth_router
    from app.routers.v1.batch import router as batch_router
    from app.routers.v1.billing import router as billing_router
    from app.routers.v1.crops import router as crops_router
    from app.routers.v1.fields import router as fields_router
    from app.routers.v1.history import router as history_router
    from app.routers.v1.irrigation import router as irrigation_router
    from app.routers.v1.notifications import router as notifications_router
    from app.routers.v1.predict import router as predict_router
    from app.routers.v1.public import router as public_router
    from app.routers.v1.remote_sensing import router as remote_sensing_router
    from app.routers.v1.reports import router as reports_router
    from app.routers.v1.users import router as users_router
    from app.routers.v1.weather import router as weather_router

    from app.routers.v1.admin.audit import router as admin_audit_router
    from app.routers.v1.admin.datasets import router as admin_datasets_router
    from app.routers.v1.admin.metrics import router as admin_metrics_router
    from app.routers.v1.admin.models import router as admin_models_router
    from app.routers.v1.admin.system import router as admin_system_router
    from app.routers.v1.admin.users import router as admin_users_router

    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(users_router, prefix=settings.API_V1_PREFIX)
    app.include_router(api_keys_router, prefix=settings.API_V1_PREFIX)
    app.include_router(public_router, prefix=settings.API_V1_PREFIX)
    app.include_router(billing_router, prefix=settings.API_V1_PREFIX)
    app.include_router(predict_router, prefix=settings.API_V1_PREFIX)
    app.include_router(history_router, prefix=settings.API_V1_PREFIX)
    app.include_router(weather_router, prefix=settings.API_V1_PREFIX)
    app.include_router(fields_router, prefix=settings.API_V1_PREFIX)
    app.include_router(remote_sensing_router, prefix=settings.API_V1_PREFIX)
    app.include_router(crops_router, prefix=settings.API_V1_PREFIX)
    app.include_router(irrigation_router, prefix=settings.API_V1_PREFIX)
    app.include_router(batch_router, prefix=settings.API_V1_PREFIX)
    app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
    app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_users_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_datasets_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_metrics_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_models_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_audit_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_system_router, prefix=settings.API_V1_PREFIX)


    # Middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers conforming strictly to {detail, code, request_id}
    @app.exception_handler(AgriScopeException)
    async def agriscope_exception_handler(request: Request, exc: AgriScopeException):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(f"AgriScopeException [{exc.code}]: {exc.detail} (req: {request_id})")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": exc.code,
                "request_id": request_id,
            },
            headers=exc.headers if getattr(exc, "headers", None) else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": str(exc),
                "code": "VALIDATION_ERROR",
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(f"Unhandled internal server error: {exc} (req: {request_id})")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred.",
                "code": "INTERNAL_SERVER_ERROR",
                "request_id": request_id,
            },
        )

    # Health & Readiness Endpoints
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.APP_NAME,
            version="0.1.0",
        )

    @app.get("/ready", response_model=ReadinessResponse, tags=["Health"])
    async def ready() -> ReadinessResponse:
        # Check DB
        db_ok = False
        try:
            from sqlalchemy import text

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as e:
            logger.warning(f"Readiness DB check failed: {e}")
            db_ok = False

        # Check Redis
        redis_ok = False
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.REDIS_URL)
            await r.ping()
            await r.close()
            redis_ok = True
        except Exception as e:
            logger.warning(f"Readiness Redis check failed: {e}")
            redis_ok = False

        # Check Storage (MinIO or mock)
        storage_ok = True  # Always ok for mock provider
        if settings.STORAGE_PROVIDER == "minio":
            try:
                from minio import Minio

                client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ROOT_USER,
                    secret_key=settings.MINIO_ROOT_PASSWORD,
                    secure=settings.MINIO_USE_SSL,
                )
                client.bucket_exists(settings.MINIO_DEFAULT_BUCKET)
                storage_ok = True
            except Exception as e:
                logger.warning(f"Readiness MinIO check failed: {e}")
                storage_ok = False

        all_ready = db_ok and redis_ok and storage_ok
        return ReadinessResponse(
            status="ready" if all_ready else "not_ready",
            database=db_ok,
            redis=redis_ok,
            storage=storage_ok,
        )

    @app.get("/metrics", tags=["Observability"])
    async def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
