"""History domain service handling pagination, multi-criteria filtering, bookmarks, and aggregations."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.plans import QuotaService, get_plan_limits
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import (
    HistoryListResponse,
    HistoryStatsResponse,
    HistoryUpdate,
    PredictionRead,
)


class HistoryService:
    """Manages prediction history, server-side filtering, bookmarking, and dashboard metrics."""

    @staticmethod
    async def get_history(
        session: AsyncSession,
        user: User,
        page: int = 1,
        page_size: int = 20,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        classification: Optional[str] = None,
        model_id: Optional[uuid.UUID] = None,
        field_id: Optional[uuid.UUID] = None,
        is_saved: Optional[bool] = None,
        query: Optional[str] = None,
    ) -> HistoryListResponse:
        """Query user predictions with multi-criteria filters and tier boundary caps."""
        conditions = [Prediction.user_id == user.id]

        if date_from:
            conditions.append(Prediction.timestamp >= date_from)
        if date_to:
            conditions.append(Prediction.timestamp <= date_to)
        if classification:
            conditions.append(Prediction.classification == classification.lower())
        if model_id:
            conditions.append(Prediction.model_id == model_id)
        if field_id:
            conditions.append(Prediction.field_id == field_id)
        if is_saved is not None:
            conditions.append(Prediction.is_saved == is_saved)
        if query:
            q_pattern = f"%{query}%"
            conditions.append(
                or_(
                    Prediction.note.ilike(q_pattern),
                    Prediction.source.ilike(q_pattern),
                )
            )

        filter_clause = and_(*conditions)

        # Count total matches
        count_stmt = select(func.count(Prediction.id)).where(filter_clause)
        count_res = await session.execute(count_stmt)
        total_count = int(count_res.scalar() or 0)

        # Enforce Free plan history limit (last 50 items)
        plan_limits = get_plan_limits(user.plan)
        is_capped = False
        effective_total = total_count

        if plan_limits.history_limit is not None and total_count > plan_limits.history_limit:
            effective_total = plan_limits.history_limit
            is_capped = True

        # Pagination
        offset = (page - 1) * page_size
        limit = min(page_size, max(0, effective_total - offset)) if is_capped else page_size

        if offset >= effective_total:
            items = []
        else:
            query_stmt = (
                select(Prediction)
                .where(filter_clause)
                .order_by(desc(Prediction.timestamp))
                .offset(offset)
                .limit(limit)
            )
            res = await session.execute(query_stmt)
            records = res.scalars().all()
            items = [PredictionRead.model_validate(r) for r in records]

        total_pages = max(1, math.ceil(effective_total / page_size)) if effective_total > 0 else 1

        return HistoryListResponse(
            items=items,
            total=effective_total,
            page=page,
            page_size=page_size,
            pages=total_pages,
            is_capped=is_capped,
        )

    @staticmethod
    async def update_prediction(
        session: AsyncSession,
        user: User,
        prediction_id: uuid.UUID,
        payload: HistoryUpdate,
    ) -> Optional[PredictionRead]:
        """Update is_saved bookmark, tags, or notes on a prediction."""
        stmt = select(Prediction).where(
            Prediction.id == prediction_id, Prediction.user_id == user.id
        )
        res = await session.execute(stmt)
        pred = res.scalar_one_or_none()
        if not pred:
            return None

        if payload.is_saved is not None:
            pred.is_saved = payload.is_saved
        if payload.tags is not None:
            pred.tags = payload.tags
        if payload.note is not None:
            pred.note = payload.note

        await session.commit()
        await session.refresh(pred)
        return PredictionRead.model_validate(pred)

    @staticmethod
    async def delete_prediction(
        session: AsyncSession,
        user: User,
        prediction_id: uuid.UUID,
    ) -> bool:
        """Delete a single prediction record belonging to user."""
        stmt = delete(Prediction).where(
            Prediction.id == prediction_id, Prediction.user_id == user.id
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount > 0

    @staticmethod
    async def bulk_delete_predictions(
        session: AsyncSession,
        user: User,
        ids: List[uuid.UUID],
    ) -> int:
        """Bulk delete multiple prediction records."""
        stmt = delete(Prediction).where(
            Prediction.id.in_(ids), Prediction.user_id == user.id
        )
        res = await session.execute(stmt)
        await session.commit()
        return int(res.rowcount)

    @staticmethod
    async def get_dashboard_stats(
        session: AsyncSession,
        user: User,
    ) -> HistoryStatsResponse:
        """Assemble summary statistics, quota, and 7-day trend for dashboard view."""
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        plan_limits = get_plan_limits(user.plan)

        # 1. Quota
        used_today = await QuotaService.get_used_predictions_today(str(user.id))
        quota_remaining = max(0, plan_limits.max_predictions_per_day - used_today)

        # 2. Total predictions count
        total_stmt = select(func.count(Prediction.id)).where(Prediction.user_id == user.id)
        total_res = await session.execute(total_stmt)
        predictions_total = int(total_res.scalar() or 0)

        # 3. Predictions today in DB
        today_stmt = select(func.count(Prediction.id)).where(
            Prediction.user_id == user.id, Prediction.timestamp >= today_start
        )
        today_res = await session.execute(today_stmt)
        predictions_today = int(today_res.scalar() or 0)

        # 4. Latest prediction
        latest_stmt = (
            select(Prediction)
            .where(Prediction.user_id == user.id)
            .order_by(desc(Prediction.timestamp))
            .limit(1)
        )
        latest_res = await session.execute(latest_stmt)
        latest_pred = latest_res.scalar_one_or_none()
        latest_et = latest_pred.et_value if latest_pred else None

        # 5. Recent activity (last 5)
        recent_stmt = (
            select(Prediction)
            .where(Prediction.user_id == user.id)
            .order_by(desc(Prediction.timestamp))
            .limit(5)
        )
        recent_res = await session.execute(recent_stmt)
        recent_records = recent_res.scalars().all()
        recent_activity = [PredictionRead.model_validate(r) for r in recent_records]

        # 6. Trend past 7 days
        seven_days_ago = today_start - timedelta(days=6)
        trend_stmt = (
            select(
                func.date(Prediction.timestamp).label("pred_date"),
                func.avg(Prediction.et_value).label("avg_et"),
                func.count(Prediction.id).label("count"),
            )
            .where(Prediction.user_id == user.id, Prediction.timestamp >= seven_days_ago)
            .group_by(func.date(Prediction.timestamp))
            .order_by(func.date(Prediction.timestamp))
        )
        trend_res = await session.execute(trend_stmt)
        trend_7d: List[Dict[str, Any]] = [
            {"date": str(row.pred_date), "avg_et": round(float(row.avg_et), 2), "count": int(row.count)}
            for row in trend_res
        ]

        return HistoryStatsResponse(
            predictions_today=predictions_today,
            predictions_total=predictions_total,
            latest_et=latest_et,
            quota_remaining=quota_remaining,
            recent_activity=recent_activity,
            trend_7d=trend_7d,
        )
