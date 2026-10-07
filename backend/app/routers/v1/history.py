"""Endpoints for user prediction history, server-side filtering, bookmarking, and deletion."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.prediction import (
    BulkDeleteRequest,
    HistoryListResponse,
    HistoryStatsResponse,
    HistoryUpdate,
    PredictionRead,
)
from app.services.history_service import HistoryService

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    classification: Optional[str] = Query(None, description="ET classification: low, moderate, high"),
    model_id: Optional[uuid.UUID] = Query(None, description="Target model UUID"),
    field_id: Optional[uuid.UUID] = Query(None, description="Target field UUID"),
    is_saved: Optional[bool] = Query(None, description="Bookmark filter"),
    query: Optional[str] = Query(None, description="Keyword search in note or source"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HistoryListResponse:
    """Retrieve server-paginated prediction history with multi-criteria filters."""
    return await HistoryService.get_history(
        session=db,
        user=current_user,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        classification=classification,
        model_id=model_id,
        field_id=field_id,
        is_saved=is_saved,
        query=query,
    )


@router.get("/stats", response_model=HistoryStatsResponse)
async def get_history_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HistoryStatsResponse:
    """Retrieve summary counts, remaining quota, latest ET, and 7-day trend for dashboard view."""
    return await HistoryService.get_dashboard_stats(session=db, user=current_user)


@router.patch("/{prediction_id}", response_model=PredictionRead)
async def update_history_item(
    prediction_id: uuid.UUID,
    payload: HistoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictionRead:
    """Update bookmark status, tags, or notes on a prediction record."""
    item = await HistoryService.update_prediction(
        session=db,
        user=current_user,
        prediction_id=prediction_id,
        payload=payload,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return item


@router.delete("/{prediction_id}")
async def delete_history_item(
    prediction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a single prediction record."""
    success = await HistoryService.delete_prediction(
        session=db, user=current_user, prediction_id=prediction_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"success": True, "deleted_id": str(prediction_id)}


@router.post("/bulk-delete")
async def bulk_delete_history_items(
    payload: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Bulk delete multiple prediction records."""
    count = await HistoryService.bulk_delete_predictions(
        session=db, user=current_user, ids=payload.ids
    )
    return {"success": True, "deleted_count": count}
