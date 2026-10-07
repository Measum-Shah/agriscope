"""User and Account Self-Service API router."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.plans import QuotaService, get_plan_limits
from app.core.rate_limit import create_rate_limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.account import (
    AuditLogRead,
    ChangeEmailRequest,
    ChangePasswordRequest,
    EntitlementsResponse,
    TOTPDisableRequest,
    TOTPEnableResponse,
    TOTPSetupResponse,
    TOTPVerifyEnableRequest,
    UpdateProfileRequest,
    UserDataExportResponse,
)
from app.schemas.common import StatusResponse
from app.schemas.user import UserRead
from app.services.account import AccountService

router = APIRouter(prefix="/users", tags=["Users & Account"])

strict_limiter = create_rate_limiter(requests_per_minute=10, prefix="rl_account")


@router.get("/me/entitlements", response_model=EntitlementsResponse)
async def get_my_entitlements(
    current_user: User = Depends(get_current_user),
) -> EntitlementsResponse:
    limits = get_plan_limits(current_user.plan)
    used_today = await QuotaService.get_used_predictions_today(str(current_user.id))
    remaining = max(0, limits.max_predictions_per_day - used_today)

    return EntitlementsResponse(
        plan=current_user.plan,
        max_predictions_per_day=limits.max_predictions_per_day,
        used_predictions_today=used_today,
        remaining_predictions_today=remaining,
        history_limit=limits.history_limit,
        max_fields=limits.max_fields,
        batch_csv_enabled=limits.batch_csv_enabled,
        batch_max_rows=limits.batch_max_rows,
        remote_sensing_enabled=limits.remote_sensing_enabled,
        forecast_enabled=limits.forecast_enabled,
        model_comparison_enabled=limits.model_comparison_enabled,
        explainability_enabled=limits.explainability_enabled,
        export_enabled=limits.export_enabled,
        api_keys_enabled=limits.api_keys_enabled,
    )


@router.get("/me", response_model=UserRead)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Return the authenticated user profile."""
    return UserRead.model_validate(current_user)


@router.patch("/me/profile", response_model=UserRead)
async def update_profile(
    data: UpdateProfileRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AccountService(db)
    updated = await service.update_profile(
        user=current_user, name=data.name, client_ip=client_ip, user_agent=user_agent
    )
    return UserRead.model_validate(updated)


@router.post(
    "/me/change-email", response_model=StatusResponse, dependencies=[Depends(strict_limiter)]
)
async def change_email(
    data: ChangeEmailRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AccountService(db)
    await service.request_email_change(
        user=current_user,
        new_email=data.new_email,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return StatusResponse(
        status="ok", message="Verification link dispatched to your new email address."
    )


@router.post("/me/confirm-email-change", response_model=UserRead)
async def confirm_email_change(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AccountService(db)
    user = await service.confirm_email_change(
        token=token, client_ip=client_ip, user_agent=user_agent
    )
    return UserRead.model_validate(user)


@router.post(
    "/me/change-password",
    response_model=StatusResponse,
    dependencies=[Depends(strict_limiter)],
)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AccountService(db)
    await service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return StatusResponse(status="ok", message="Password updated. Other sessions revoked.")


# --- 2FA Endpoints ---


@router.post("/me/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TOTPSetupResponse:
    service = AccountService(db)
    secret, uri, qr_b64 = await service.setup_totp(current_user)
    return TOTPSetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_code_base64=qr_b64,
    )


@router.post("/me/2fa/verify", response_model=TOTPEnableResponse)
async def verify_2fa(
    data: TOTPVerifyEnableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TOTPEnableResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AccountService(db)
    recovery_codes = await service.verify_and_enable_totp(
        user=current_user,
        code=data.code,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return TOTPEnableResponse(
        status="ok",
        message="2FA enabled successfully. Store these recovery codes securely.",
        recovery_codes=recovery_codes,
    )


@router.post("/me/2fa/disable", response_model=StatusResponse)
async def disable_2fa(
    data: TOTPDisableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AccountService(db)
    await service.disable_totp(
        user=current_user,
        code=data.code,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return StatusResponse(status="ok", message="Two-factor authentication disabled.")


# --- Self-service Export, Audit, and Deletion ---


@router.get("/me/export", response_model=UserDataExportResponse)
async def export_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserDataExportResponse:
    service = AccountService(db)
    data = await service.export_user_data(current_user)
    return UserDataExportResponse(
        user=UserRead.model_validate(data["user"]),
        sessions=[s for s in data["sessions"]],
        audit_events=[a for a in data["audit_events"]],
        exported_at=data["exported_at"],
    )


@router.delete("/me", response_model=StatusResponse)
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = AccountService(db)
    await service.delete_account(user=current_user, client_ip=client_ip, user_agent=user_agent)
    return StatusResponse(status="ok", message="Account deactivated and scheduled for purge.")


@router.get("/me/audit", response_model=List[AuditLogRead])
async def get_my_audit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AuditLogRead]:
    service = AccountService(db)
    logs = await service.list_user_audit_logs(current_user.id)
    return [AuditLogRead.model_validate(log_entry) for log_entry in logs]
