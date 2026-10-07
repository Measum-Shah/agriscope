"""FastAPI microservice for ML inference, batch estimation, explainability, and hot-reload."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .manager import ModelManager
from .routers.infer import router as infer_router
from .routers.models import router as models_router
from .schemas.inference import MLHealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup lifespan: initialize ModelManager, warm-load active model, and cache structures."""
    manager = ModelManager()
    manager.warm_up()
    app.state.model_manager = manager
    yield


app = FastAPI(
    title="AgriScope ML Inference Service",
    version="0.1.0",
    description="Dedicated microservice for ET estimation, conformal prediction, and explainability",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(infer_router)
app.include_router(models_router)


@app.get("/health", response_model=MLHealthResponse, tags=["Health"])
async def health(request: Request) -> MLHealthResponse:
    """Service health and loaded active model status."""
    manager: ModelManager = getattr(request.app.state, "model_manager", None)
    if manager is None:
        manager = ModelManager()
        manager.warm_up()
        request.app.state.model_manager = manager
    active_id = manager.active_bundle.model_id if manager and manager._active_bundle else "none"
    active_ver = manager.active_bundle.version if manager and manager._active_bundle else "none"
    uptime = time.time() - manager.start_time if manager else 0.0
    loaded = list(manager._loaded_models.keys()) if manager else []

    return MLHealthResponse(
        status="ok",
        service="agriscope-ml-service",
        version="0.1.0",
        active_model_id=active_id,
        active_model_version=active_ver,
        uptime_seconds=round(uptime, 2),
        loaded_models=loaded,
    )
