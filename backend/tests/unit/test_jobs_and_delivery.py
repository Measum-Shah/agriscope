"""Unit tests for CSV formula injection sanitization, export formats, PDF generation, and notifications."""

import csv
import io
import uuid
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User, UserRole, UserStatus
from app.services.export_service import generate_csv_bytes, generate_xlsx_bytes, sanitize_csv_cell, generate_png_chart
from app.services.notification_service import NotificationService, SSEConnectionManager
from app.services.report_service import generate_prediction_summary_pdf


def test_sanitize_csv_cell_formula_injection():
    """Verify formula injection prefixes are neutralized with prepended single quote."""
    # Malicious injection payloads (CWE-1236)
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-2+3+cmd|' /C calc'!A0") == "'-2+3+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitize_csv_cell("\tDDE") == "'\tDDE"

    # Benign normal cells
    assert sanitize_csv_cell("Wheat Field 1") == "Wheat Field 1"
    assert sanitize_csv_cell(28.5) == "28.5"
    assert sanitize_csv_cell("") == ""
    assert sanitize_csv_cell(None) == ""


def test_generate_csv_and_xlsx_bytes():
    """Verify tabular serialization to CSV and openpyxl XLSX."""
    headers = ["Parcel", "ET0", "Status"]
    rows = [
        ["Plot A", 4.25, "=SUM(A1:B1)"],
        ["Plot B", 5.10, "Normal"],
    ]

    # CSV
    csv_bytes = generate_csv_bytes(headers, rows)
    assert isinstance(csv_bytes, bytes)
    assert b"'=SUM(A1:B1)" in csv_bytes

    # XLSX
    xlsx_bytes = generate_xlsx_bytes("Test Sheet", headers, rows)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 100


def test_generate_prediction_summary_pdf():
    """Verify PDF report generation with ReportLab and embedded chart."""
    sample_preds = [
        {
            "created_at": "2026-10-01",
            "temperature": 28.0,
            "humidity": 45.0,
            "wind_speed": 2.5,
            "solar_radiation": 22.0,
            "predicted_et0": 4.85,
            "fao56_reference_et0": 4.90,
            "classification": "moderate",
        },
        {
            "created_at": "2026-10-02",
            "temperature": 32.0,
            "humidity": 35.0,
            "wind_speed": 3.0,
            "solar_radiation": 25.0,
            "predicted_et0": 5.60,
            "fao56_reference_et0": 5.55,
            "classification": "high",
        },
    ]

    pdf_bytes = generate_prediction_summary_pdf("Test Farmer", sample_preds)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


@pytest.mark.asyncio
async def test_notification_service_and_preferences(client):
    """Test notification creation, preference updating, and read status."""
    test_engine = client._transport.app.state.test_engine
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    user = User(
        name="Notifier User",
        email="notify@agriscope.local",
        password_hash="pw",
        role=UserRole.PRO.value,
        plan="pro",
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )

    async with factory() as s:
        s.add(user)
        await s.commit()
        await s.refresh(user)

        notif_service = NotificationService(s)

        # 1. Create notification
        notif = await notif_service.create_notification(
            user_id=user.id,
            title="Batch Job Ready",
            message="Your bulk inference job with 500 rows is complete.",
            type_="info",
            metadata={"job_id": "123"},
        )
        assert notif.id is not None
        assert not notif.is_read

        # 2. List notifications
        list_items = await notif_service.list_notifications(user)
        assert len(list_items) == 1

        # 3. Mark as read
        read_notif = await notif_service.mark_as_read(notif.id, user)
        assert read_notif.is_read

        # 4. Update preferences
        pref = await notif_service.get_preferences(user)
        assert pref.email_enabled
        updated_pref = await notif_service.update_preferences(user, {"email_enabled": False})
        assert not updated_pref.email_enabled
