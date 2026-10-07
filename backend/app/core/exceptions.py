"""Custom application exceptions with standardized error codes."""

from typing import Any, Dict, Optional


class AgriScopeException(Exception):
    """Base application exception with error code and optional status."""

    def __init__(
        self,
        detail: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        extra: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code
        self.extra = extra or {}
        self.headers = headers or {}


class NotFoundException(AgriScopeException):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(detail=detail, code=code, status_code=404)


class BadRequestException(AgriScopeException):
    def __init__(self, detail: str = "Bad request", code: str = "BAD_REQUEST"):
        super().__init__(detail=detail, code=code, status_code=400)


class UnauthorizedException(AgriScopeException):
    def __init__(self, detail: str = "Authentication required", code: str = "UNAUTHORIZED"):
        super().__init__(detail=detail, code=code, status_code=401)


class ForbiddenException(AgriScopeException):
    def __init__(self, detail: str = "Access forbidden", code: str = "FORBIDDEN"):
        super().__init__(detail=detail, code=code, status_code=403)


class QuotaExceededException(AgriScopeException):
    def __init__(
        self,
        detail: str = "Plan quota exceeded",
        code: str = "QUOTA_EXCEEDED",
        retry_after: int = 86400,
    ):
        super().__init__(
            detail=detail,
            code=code,
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )


class RateLimitExceededException(AgriScopeException):
    def __init__(
        self,
        detail: str = "Rate limit exceeded. Please wait before retrying.",
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: int = 60,
    ):
        super().__init__(
            detail=detail,
            code=code,
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
