"""Common schema definitions for responses and error payloads."""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standardized error format as specified in PROJECT_CONTEXT section E."""

    detail: str = Field(..., description="Human-readable error description")
    code: str = Field(..., description="Machine-readable error code")
    request_id: str = Field(..., description="Unique correlation request ID")


class StatusResponse(BaseModel):
    """Generic status reply."""

    status: str
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Liveness check response."""

    status: str
    app: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness probe checking DB, Redis, and storage dependencies."""

    status: str
    database: bool
    redis: bool
    storage: bool
    details: Optional[dict] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated container."""

    items: List[T]
    total: int
    page: int
    size: int
    pages: int
