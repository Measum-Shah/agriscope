"""Authentication API router with registration, token rotation, sessions, and recovery."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import UnauthorizedException
from app.core.rate_limit import create_rate_limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionRead,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import StatusResponse
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Rate limiters
auth_limiter = create_rate_limiter(requests_per_minute=20, prefix="rl_auth")
strict_limiter = create_rate_limiter(requests_per_minute=5, prefix="rl_strict")


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Sets secure httpOnly cookie with refresh token."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/api/v1/auth",
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_limiter)],
)
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AuthService(db)
    user = await service.register_user(
        name=data.name,
        email=data.email,
        password=data.password,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(auth_limiter)],
)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AuthService(db)
    user, access_token, raw_refresh = await service.authenticate_user(
        email=data.email,
        password=data.password,
        totp_code=data.totp_code,
        recovery_code=data.recovery_code,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        plan=user.plan,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(auth_limiter)],
)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise UnauthorizedException(detail="Refresh token cookie missing.")

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AuthService(db)
    user, new_access_token, new_refresh = await service.rotate_refresh_token(
        raw_refresh_token=refresh_token,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    set_refresh_cookie(response, new_refresh)
    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        plan=user.plan,
    )


@router.post("/logout", response_model=StatusResponse)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    if refresh_token:
        service = AuthService(db)
        await service.logout(refresh_token)
    clear_refresh_cookie(response)
    return StatusResponse(status="ok", message="Logged out successfully.")


@router.post("/logout-all", response_model=StatusResponse)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    service = AuthService(db)
    await service.logout_all(current_user.id)
    clear_refresh_cookie(response)
    return StatusResponse(status="ok", message="All sessions revoked.")


@router.get("/sessions", response_model=List[SessionRead])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SessionRead]:
    service = AuthService(db)
    sessions = await service.list_sessions(current_user.id)
    return [SessionRead.model_validate(s) for s in sessions]


@router.delete("/sessions/{session_id}", response_model=StatusResponse)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    service = AuthService(db)
    await service.revoke_session_by_id(current_user.id, session_id)
    return StatusResponse(status="ok", message="Session revoked.")


@router.post("/verify-email", response_model=StatusResponse)
async def verify_email(
    data: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AuthService(db)
    await service.verify_email(data.token, client_ip=client_ip, user_agent=user_agent)
    return StatusResponse(status="ok", message="Email verified successfully.")


@router.post(
    "/resend-verification",
    response_model=StatusResponse,
    dependencies=[Depends(strict_limiter)],
)
async def resend_verification(
    data: ResendVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AuthService(db)
    await service.resend_verification(data.email, client_ip=client_ip, user_agent=user_agent)
    return StatusResponse(
        status="ok", message="If this email is registered and unverified, a link was sent."
    )


@router.post(
    "/forgot-password",
    response_model=StatusResponse,
    dependencies=[Depends(strict_limiter)],
)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AuthService(db)
    await service.request_password_reset(data.email, client_ip=client_ip, user_agent=user_agent)
    return StatusResponse(
        status="ok", message="If the email exists, a password reset link has been dispatched."
    )


@router.post(
    "/reset-password",
    response_model=StatusResponse,
    dependencies=[Depends(strict_limiter)],
)
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AuthService(db)
    await service.reset_password(
        token=data.token,
        new_password=data.new_password,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return StatusResponse(status="ok", message="Password has been reset successfully.")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
