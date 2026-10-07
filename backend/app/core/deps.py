"""Core FastAPI dependencies: DB sessions, auth tokens, user loading, and RBAC."""

from __future__ import annotations

import uuid
from typing import Callable, List, Optional

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


async def get_request_id(request: Request) -> str:
    """Extracts request_id attached by middleware."""
    return getattr(request.state, "request_id", "unknown")


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> uuid.UUID:
    """Extracts user UUID from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException(detail="Missing or invalid Authorization header.")

    token = authorization.split(" ")[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException(detail="Invalid token type.")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException(detail="Token missing subject.")
        return uuid.UUID(user_id_str)
    except UnauthorizedException:
        raise
    except Exception as err:
        raise UnauthorizedException(detail="Could not validate credentials.") from err


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Loads full User model for authenticated caller."""
    user = await db.get(User, user_id)
    if not user:
        raise UnauthorizedException(detail="User does not exist.")
    if user.status != "active":
        raise ForbiddenException(detail="Account is suspended or inactive.")
    return user


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency verifying the caller possesses at least one of the specified roles."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException(detail="Insufficient permissions for this action.")
        return current_user

    return role_checker
