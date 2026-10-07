"""Dataset management service for uploading, validating, and inspecting ML training datasets."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.logging import logger
from app.models.training_dataset import TrainingDataset
from app.providers.storage.minio import get_storage_provider


REQUIRED_COLUMNS = ["temp_max", "temp_min", "humidity", "wind_speed"]

VALID_RANGES = {
    "temp_max": (-20.0, 60.0),
    "temp_min": (-30.0, 50.0),
    "humidity": (0.0, 100.0),
    "wind_speed": (0.0, 50.0),
    "solar_radiation": (0.0, 50.0),
    "et0": (0.0, 30.0),
}


class DatasetService:
    @staticmethod
    def _validate_content(df: pd.DataFrame) -> Tuple[List[str], Dict[str, Any], Dict[str, Any]]:
        errors: List[str] = []
        stats: Dict[str, Any] = {}
        outlier_report: Dict[str, Any] = {}

        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                errors.append(f"Missing mandatory column: '{col}'")

        if errors:
            return errors, stats, outlier_report

        # Compute summary statistics and check ranges
        for col in df.select_dtypes(include=["number"]).columns:
            series = df[col].dropna()
            if series.empty:
                continue

            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr = q75 - q25
            lower_bound = q25 - (1.5 * iqr)
            upper_bound = q75 + (1.5 * iqr)
            outliers = series[(series < lower_bound) | (series > upper_bound)]

            stats[col] = {
                "mean": round(float(series.mean()), 3),
                "std": round(float(series.std()), 3) if len(series) > 1 else 0.0,
                "min": round(float(series.min()), 3),
                "max": round(float(series.max()), 3),
                "null_count": int(df[col].isna().sum()),
            }

            outlier_report[col] = {
                "outlier_count": int(len(outliers)),
                "iqr_lower": round(lower_bound, 3),
                "iqr_upper": round(upper_bound, 3),
            }

            if col in VALID_RANGES:
                r_min, r_max = VALID_RANGES[col]
                violators = series[(series < r_min) | (series > r_max)]
                if len(violators) > 0:
                    errors.append(
                        f"Column '{col}' has {len(violators)} values outside physical boundaries [{r_min}, {r_max}]."
                    )

        return errors, stats, outlier_report

    @classmethod
    async def upload_dataset(
        cls,
        db: AsyncSession,
        name: str,
        version: str,
        content_bytes: bytes,
        filename: str,
        description: Optional[str] = None,
    ) -> Tuple[TrainingDataset, Dict[str, Any]]:
        if len(content_bytes) > 25 * 1024 * 1024:
            raise BadRequestException("Dataset exceeds max size of 25MB.")

        # Compute SHA-256
        sha256 = hashlib.sha256(content_bytes).hexdigest()

        try:
            df = pd.read_csv(io.BytesIO(content_bytes))
        except Exception as e:
            raise BadRequestException(f"Invalid CSV format: {str(e)}")

        if df.empty or len(df) == 0:
            raise BadRequestException("Uploaded CSV is empty.")

        errors, stats, outlier_report = cls._validate_content(df)
        status = "rejected" if errors else "validated"

        storage = get_storage_provider()
        object_name = f"datasets/{uuid.uuid4()}_{filename}"
        file_uri = await storage.upload_bytes(content_bytes, object_name, content_type="text/csv")

        dataset = TrainingDataset(
            name=name,
            version=version,
            file_uri=file_uri,
            file_hash=sha256,
            status=status,
            data_provenance="user_uploaded",
            stats_json={
                "row_count": len(df),
                "columns": list(df.columns),
                "summary": stats,
                "outliers": outlier_report,
                "errors": errors,
            },
            description=description,
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)

        report = {
            "id": dataset.id,
            "name": dataset.name,
            "version": dataset.version,
            "status": dataset.status,
            "row_count": len(df),
            "columns": list(df.columns),
            "stats": stats,
            "outlier_report": outlier_report,
            "preview_rows": df.head(10).fillna("").to_dict(orient="records"),
            "validation_errors": errors,
            "message": "Dataset uploaded and validated successfully."
            if not errors
            else "Dataset uploaded with validation warnings/errors.",
        }
        return dataset, report

    @classmethod
    async def list_datasets(cls, db: AsyncSession) -> List[TrainingDataset]:
        result = await db.execute(select(TrainingDataset).order_by(TrainingDataset.created_at.desc()))
        return list(result.scalars().all())

    @classmethod
    async def get_dataset(cls, db: AsyncSession, dataset_id: uuid.UUID) -> TrainingDataset:
        dataset = await db.get(TrainingDataset, dataset_id)
        if not dataset:
            raise NotFoundException("Dataset not found.")
        return dataset

    @classmethod
    async def delete_dataset(cls, db: AsyncSession, dataset_id: uuid.UUID) -> None:
        dataset = await cls.get_dataset(db, dataset_id)
        await db.delete(dataset)
        await db.commit()
