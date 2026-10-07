"""Dataset management, versioning, SHA-256 hashing, and CSV schema validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

REQUIRED_COLUMNS = [
    "temperature",
    "humidity",
    "wind_speed",
    "solar_radiation",
    "et",
]

OPTIONAL_COLUMNS = [
    "tmin",
    "tmax",
    "latitude",
    "elevation",
    "doy",
    "precipitation",
    "location_name",
    "provenance",
    "is_synthetic",
]

# Physical validation thresholds
PHYSICAL_BOUNDS = {
    "temperature": (-10.0, 50.0),
    "tmin": (-15.0, 45.0),
    "tmax": (-5.0, 55.0),
    "humidity": (0.0, 100.0),
    "wind_speed": (0.0, 30.0),
    "solar_radiation": (0.0, 35.0),
    "et": (0.0, 20.0),
    "latitude": (-90.0, 90.0),
    "elevation": (-400.0, 5000.0),
    "doy": (1, 366),
}


@dataclass
class DatasetMetadata:
    """Provenance and metadata card for a saved dataset version."""

    dataset_name: str
    version: str
    content_hash: str
    row_count: int
    column_count: int
    columns: List[str]
    created_at: str
    provenance: str
    is_synthetic: bool
    summary_stats: Dict[str, Dict[str, float]]


@dataclass
class ValidationReport:
    """Report from validating a user-uploaded CSV against AgriScope physical schema."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    row_count: int
    columns_found: List[str]
    missing_required: List[str]


def compute_dataframe_hash(df: pd.DataFrame) -> str:
    """Compute deterministic SHA-256 hash of a DataFrame's tabular content."""
    # Hash sorted column names and normalized row records
    sorted_df = df.reindex(sorted(df.columns), axis=1)
    csv_bytes = sorted_df.to_csv(index=False, float_format="%.4f").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def validate_user_csv(df: pd.DataFrame) -> ValidationReport:
    """Validate user-uploaded dataset against schema requirements and physical boundaries.

    Checks:
    1. Presence of required core columns: temperature, humidity, wind_speed, solar_radiation, et.
    2. Data types (must be numeric).
    3. Physical ranges (temperature -10..50°C, RH 0..100%, WS 0..30 m/s, Rs 0..35 MJ/m²/day, ET 0..20 mm/day).
    4. Row count > 0.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if df.empty:
        errors.append("Dataset contains 0 rows.")
        return ValidationReport(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            row_count=0,
            columns_found=list(df.columns),
            missing_required=REQUIRED_COLUMNS,
        )

    # Normalize column names to lowercase stripped
    cols = {c.lower().strip(): c for c in df.columns}
    missing = [c for c in REQUIRED_COLUMNS if c not in cols]

    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")

    # Check for NaN / null values in required columns
    for req_col in REQUIRED_COLUMNS:
        if req_col in cols:
            orig_col = cols[req_col]
            # Verify numeric conversion
            numeric_series = pd.to_numeric(df[orig_col], errors="coerce")
            nan_count = int(numeric_series.isna().sum())
            if nan_count > 0:
                warnings.append(
                    f"Column '{req_col}' contains {nan_count} missing or non-numeric values."
                )

            # Check physical boundaries
            bounds = PHYSICAL_BOUNDS.get(req_col)
            if bounds:
                min_b, max_b = bounds
                out_of_bounds = int(((numeric_series < min_b) | (numeric_series > max_b)).sum())
                if out_of_bounds > 0:
                    errors.append(
                        f"Column '{req_col}' has {out_of_bounds} values outside physical range [{min_b}, {max_b}]."
                    )

    return ValidationReport(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        row_count=len(df),
        columns_found=list(df.columns),
        missing_required=missing,
    )


def save_versioned_dataset(
    df: pd.DataFrame,
    output_dir: str | Path,
    dataset_name: str = "agriscope_et",
    version: str = "v1",
    provenance: str = "nasa_power",
    is_synthetic: bool = False,
) -> Tuple[Path, Path, DatasetMetadata]:
    """Save dataset as both Parquet and CSV alongside versioned metadata card."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    content_hash = compute_dataframe_hash(df)
    timestamp = datetime.now(timezone.utc).isoformat()

    # Calculate summary stats for numeric columns
    numeric_df = df.select_dtypes(include=["number"])
    stats: Dict[str, Dict[str, float]] = {}
    for col in numeric_df.columns:
        s = numeric_df[col]
        stats[col] = {
            "mean": round(float(s.mean()), 3),
            "std": round(float(s.std()), 3) if len(s) > 1 else 0.0,
            "min": round(float(s.min()), 3),
            "max": round(float(s.max()), 3),
        }

    meta = DatasetMetadata(
        dataset_name=dataset_name,
        version=version,
        content_hash=content_hash,
        row_count=len(df),
        column_count=len(df.columns),
        columns=list(df.columns),
        created_at=timestamp,
        provenance=provenance,
        is_synthetic=is_synthetic,
        summary_stats=stats,
    )

    parquet_file = out_path / f"{dataset_name}_{version}.parquet"
    csv_file = out_path / f"{dataset_name}_{version}.csv"
    meta_file = out_path / f"{dataset_name}_{version}_metadata.json"

    # Save outputs
    df.to_parquet(parquet_file, index=False)
    df.to_csv(csv_file, index=False)

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(asdict(meta), f, indent=2)

    return parquet_file, csv_file, meta
