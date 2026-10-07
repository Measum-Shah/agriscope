"""Export formatting engine with CSV formula injection sanitization, XLSX, and PNG chart generation."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional


def sanitize_csv_cell(value: Any) -> str:
    """Sanitize CSV cells against CSV / Spreadsheet Formula Injection (CWE-1236).

    If a formula prefix (=, +, -, @, \t, \r) is present, prepend a single quote (') to force text parsing.
    """
    if value is None:
        return ""
    str_val = str(value)
    if not str_val:
        return ""

    if str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{str_val}"
    return str_val.strip()


def generate_csv_bytes(headers: List[str], rows: List[List[Any]]) -> bytes:
    """Serialize structured tabular data to sanitized CSV bytes."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Sanitize and write headers
    writer.writerow([sanitize_csv_cell(h) for h in headers])

    # Sanitize and write rows
    for row in rows:
        writer.writerow([sanitize_csv_cell(col) for col in row])

    return output.getvalue().encode("utf-8")


def generate_xlsx_bytes(
    sheet_title: str,
    headers: List[str],
    rows: List[List[Any]],
) -> bytes:
    """Serialize tabular data to styled XLSX workbook bytes."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]

    # Header styling (AgriScope deep green)
    header_fill = PatternFill(start_color="166534", end_color="166534", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center")

    # Write Headers
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align

    # Write Rows with sanitization
    for row_idx, row in enumerate(rows, start=2):
        cleaned_row = []
        for val in row:
            if isinstance(val, (int, float)):
                cleaned_row.append(val)
            else:
                cleaned_row.append(sanitize_csv_cell(val))
        ws.append(cleaned_row)

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def generate_png_chart(
    dates: List[str],
    ml_et0: List[float],
    fao_et0: Optional[List[float]] = None,
    title: str = "Evapotranspiration Trend",
) -> bytes:
    """Render a standalone server-side PNG visualization using Matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.plot(dates, ml_et0, marker="o", color="#16a34a", linewidth=2.5, label="ML ET₀ Estimate")
    if fao_et0 and len(fao_et0) == len(dates):
        ax.plot(dates, fao_et0, linestyle="--", color="#64748b", linewidth=1.8, label="FAO-56 Benchmark")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    ax.set_ylabel("ET₀ (mm/day)", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", frameon=True)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.tight_layout()

    bio = io.BytesIO()
    plt.savefig(bio, format="png", bbox_inches="tight")
    plt.close(fig)
    return bio.getvalue()
