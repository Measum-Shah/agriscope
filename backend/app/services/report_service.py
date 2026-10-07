"""PDF Report generator creating branded prediction and field season reports."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.export_service import generate_png_chart


def generate_prediction_summary_pdf(
    user_name: str,
    predictions: List[Dict[str, Any]],
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Generate professional PDF report summarizing model predictions."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#166534"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=12,
    )
    cell_style = ParagraphStyle(
        "ReportCell", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#1f2937")
    )
    header_cell_style = ParagraphStyle(
        "ReportHeaderCell",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    elements = []

    # Header section
    elements.append(Paragraph("AgriScope • Evapotranspiration Summary Report", title_style))
    ts_str = (generated_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC")
    elements.append(
        Paragraph(
            f"Prepared for: <b>{user_name}</b> | Generated at: {ts_str} | Data Provenance: Physics-ML Ensemble",
            subtitle_style,
        )
    )
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#166534"), spaceAfter=14))

    # Summary table
    table_data = [
        [
            Paragraph("Date", header_cell_style),
            Paragraph("Temp (°C)", header_cell_style),
            Paragraph("RH (%)", header_cell_style),
            Paragraph("Wind (m/s)", header_cell_style),
            Paragraph("Rad (MJ)", header_cell_style),
            Paragraph("ML ET₀ (mm)", header_cell_style),
            Paragraph("FAO-56 (mm)", header_cell_style),
            Paragraph("Demand", header_cell_style),
        ]
    ]

    dates_for_chart = []
    ml_vals_for_chart = []
    fao_vals_for_chart = []

    for pred in predictions[:20]:
        date_str = str(pred.get("created_at") or pred.get("date") or "N/A")[:10]
        ml_et = float(pred.get("predicted_et0") or pred.get("et0_ml") or 0.0)
        fao_et = float(pred.get("fao56_reference_et0") or pred.get("et0_provider") or ml_et)

        dates_for_chart.append(date_str)
        ml_vals_for_chart.append(ml_et)
        fao_vals_for_chart.append(fao_et)

        table_data.append(
            [
                Paragraph(date_str, cell_style),
                Paragraph(f"{pred.get('temperature', 0):.1f}", cell_style),
                Paragraph(f"{pred.get('humidity', 0):.0f}", cell_style),
                Paragraph(f"{pred.get('wind_speed', 0):.1f}", cell_style),
                Paragraph(f"{pred.get('solar_radiation', 0):.1f}", cell_style),
                Paragraph(f"<b>{ml_et:.2f}</b>", cell_style),
                Paragraph(f"{fao_et:.2f}", cell_style),
                Paragraph(str(pred.get("classification") or "optimal").upper(), cell_style),
            ]
        )

    t = Table(table_data, colWidths=[65, 55, 45, 55, 50, 75, 75, 60])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#166534")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 14))

    # Embedded Chart Snapshot
    if len(dates_for_chart) >= 2:
        chart_png = generate_png_chart(
            dates=dates_for_chart[:14],
            ml_et0=ml_vals_for_chart[:14],
            fao_et0=fao_vals_for_chart[:14],
            title="Evapotranspiration Trend (ML vs FAO-56 Reference)",
        )
        img_buffer = io.BytesIO(chart_png)
        img = Image(img_buffer, width=480, height=220)
        elements.append(img)

    # Footer note
    elements.append(Spacer(1, 14))
    footer_text = (
        "<b>AgriScope Platform Notice:</b> Predictions are generated using trained gradient boosting / stacking "
        "pipelines calibrated on NASA POWER and FAO-56 Penman-Monteith physical models."
    )
    elements.append(Paragraph(footer_text, subtitle_style))

    doc.build(elements)
    return buffer.getvalue()
