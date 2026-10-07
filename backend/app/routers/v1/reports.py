"""Reports and export API router providing PDF, CSV, XLSX, and PNG file generation."""

from __future__ import annotations

import io
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.plans import require_plan_feature
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.session import get_db
from app.models.prediction import Prediction
from app.models.report import Report
from app.models.user import User
from app.providers.storage.minio import get_storage_provider
from app.schemas.jobs import ReportCreateRequest, ReportResponse
from app.services.export_service import generate_csv_bytes, generate_xlsx_bytes, generate_png_chart
from app.services.report_service import generate_prediction_summary_pdf

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])


@router.post(
    "/generate",
    response_model=ReportResponse,
    dependencies=[Depends(require_plan_feature("pdf_report"))],
)
async def generate_report(
    payload: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate professional PDF, CSV, XLSX, or PNG report and store in MinIO."""
    storage = get_storage_provider()

    # Query recent predictions for the user
    pred_stmt = (
        select(Prediction)
        .where(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(100)
    )
    pred_res = await db.execute(pred_stmt)
    predictions = list(pred_res.scalars().all())

    pred_dicts = [
        {
            "created_at": p.created_at.isoformat() if p.created_at else "",
            "temperature": p.temperature,
            "humidity": p.humidity,
            "wind_speed": p.wind_speed,
            "solar_radiation": p.solar_radiation,
            "predicted_et0": p.predicted_et0,
            "fao56_reference_et0": p.fao56_reference_et0,
            "classification": p.classification,
        }
        for p in predictions
    ]

    fmt = payload.format.lower().strip()
    data_bytes: bytes = b""
    content_type = "application/octet-stream"
    filename = f"report_{uuid.uuid4().hex[:8]}.{fmt}"

    if fmt == "pdf":
        data_bytes = generate_prediction_summary_pdf(
            user_name=current_user.name,
            predictions=pred_dicts,
            generated_at=datetime.utcnow(),
        )
        content_type = "application/pdf"
    elif fmt == "csv":
        headers = ["Date", "Temperature", "Humidity", "Wind_Speed", "Solar_Radiation", "Predicted_ET0", "FAO56_ET0", "Classification"]
        rows = [
            [d["created_at"][:10], d["temperature"], d["humidity"], d["wind_speed"], d["solar_radiation"], d["predicted_et0"], d["fao56_reference_et0"], d["classification"]]
            for d in pred_dicts
        ]
        data_bytes = generate_csv_bytes(headers, rows)
        content_type = "text/csv"
    elif fmt == "xlsx":
        headers = ["Date", "Temperature", "Humidity", "Wind Speed", "Solar Rad", "ML ET0 (mm)", "FAO-56 (mm)", "Classification"]
        rows = [
            [d["created_at"][:10], d["temperature"], d["humidity"], d["wind_speed"], d["solar_radiation"], d["predicted_et0"], d["fao56_reference_et0"], d["classification"]]
            for d in pred_dicts
        ]
        data_bytes = generate_xlsx_bytes("AgriScope ET0 Summary", headers, rows)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "png":
        dates = [d["created_at"][:10] for d in pred_dicts[:14]]
        ml_vals = [float(d["predicted_et0"]) for d in pred_dicts[:14]]
        fao_vals = [float(d["fao56_reference_et0"] or d["predicted_et0"]) for d in pred_dicts[:14]]
        data_bytes = generate_png_chart(dates, ml_vals, fao_vals)
        content_type = "image/png"
    else:
        raise BadRequestException(detail=f"Unsupported format '{fmt}'. Must be pdf, csv, xlsx, or png.")

    # Upload to storage
    out_uri = await storage.upload_bytes(data_bytes, filename, content_type=content_type)
    download_url = await storage.get_presigned_download_url(filename, expires_in_seconds=3600)

    report = Report(
        user_id=current_user.id,
        title=payload.title,
        format=fmt,
        file_uri=filename,
        file_size_bytes=len(data_bytes),
        parameters=payload.parameters,
        status="completed",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    resp = ReportResponse.model_validate(report)
    resp.download_url = download_url
    return resp


@router.get("/list", response_model=List[ReportResponse])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List historical reports generated for user."""
    storage = get_storage_provider()
    stmt = (
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)
    reports = list(res.scalars().all())

    results = []
    for r in reports:
        item = ReportResponse.model_validate(r)
        item.download_url = await storage.get_presigned_download_url(r.file_uri, expires_in_seconds=3600)
        results.append(item)
    return results


@router.get("/download/{object_name}")
async def stream_download_report(
    object_name: str,
    token: Optional[str] = Query(None),
):
    """Direct stream download for generated report files."""
    storage = get_storage_provider()
    try:
        data = await storage.download_bytes(object_name)
    except Exception:
        raise NotFoundException(detail="Report file not found.")

    media_type = "application/octet-stream"
    if object_name.endswith(".pdf"):
        media_type = "application/pdf"
    elif object_name.endswith(".csv"):
        media_type = "text/csv"
    elif object_name.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif object_name.endswith(".png"):
        media_type = "image/png"

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{object_name}"'},
    )
