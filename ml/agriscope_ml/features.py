"""Feature definitions, schemas, and cyclic transformations for AgriScope ML models."""

from __future__ import annotations

import math
from typing import Any, List, Tuple

import numpy as np
import pandas as pd

BASIC_FEATURE_NAMES: List[str] = [
    "temperature",
    "humidity",
    "wind_speed",
    "solar_radiation",
]

EXTENDED_FEATURE_NAMES: List[str] = [
    "temperature",
    "humidity",
    "wind_speed",
    "solar_radiation",
    "tmin",
    "tmax",
    "temp_range",
    "latitude",
    "elevation",
    "doy",
    "sin_doy",
    "cos_doy",
    "vpd",
]

TARGET_COLUMN: str = "et"


def encode_cyclic_doy(doy: pd.Series | np.ndarray | float | int) -> Tuple[Any, Any]:
    """Encode day of year (1-365) cyclically using sine and cosine components.

    sin_doy = sin(2 * pi * doy / 365.25)
    cos_doy = cos(2 * pi * doy / 365.25)
    """
    if isinstance(doy, (int, float)):
        angle = 2.0 * math.pi * float(doy) / 365.25
        return round(math.sin(angle), 5), round(math.cos(angle), 5)

    angle = 2.0 * np.pi * np.asarray(doy, dtype=float) / 365.25
    return np.sin(angle), np.cos(angle)


def extract_features(
    df: pd.DataFrame,
    schema: str = "basic",
) -> pd.DataFrame:
    """Extract and engineer model features according to specified schema.

    Args:
        df: Input DataFrame with meteorological columns.
        schema: "basic" (4 core features) or "extended" (geography + cyclic calendar + diurnal).

    Returns:
        Engineered feature DataFrame ready for Scikit-learn / XGBoost inference.
    """
    df_out = df.copy()

    if schema == "basic":
        for col in BASIC_FEATURE_NAMES:
            if col not in df_out.columns:
                raise ValueError(f"Required basic feature '{col}' missing from DataFrame.")
        return df_out[BASIC_FEATURE_NAMES].astype(float)

    if schema == "extended":
        # Ensure core 4 exist
        for col in BASIC_FEATURE_NAMES:
            if col not in df_out.columns:
                raise ValueError(f"Required feature '{col}' missing from DataFrame.")

        # Impute or compute derived columns if missing
        if "tmin" not in df_out.columns:
            df_out["tmin"] = df_out["temperature"] - 5.0
        if "tmax" not in df_out.columns:
            df_out["tmax"] = df_out["temperature"] + 5.0

        if "temp_range" not in df_out.columns:
            df_out["temp_range"] = (df_out["tmax"] - df_out["tmin"]).clip(lower=0.0)

        if "latitude" not in df_out.columns:
            df_out["latitude"] = 30.0  # Default subtropical agricultural belt

        if "elevation" not in df_out.columns:
            df_out["elevation"] = 100.0  # Standard agricultural plain

        if "doy" not in df_out.columns:
            df_out["doy"] = 180  # Default mid-year

        sin_d, cos_d = encode_cyclic_doy(df_out["doy"])
        df_out["sin_doy"] = sin_d
        df_out["cos_doy"] = cos_d

        if "vpd" not in df_out.columns:
            # Estimate VPD from mean temp and RH if absent
            t = df_out["temperature"]
            es = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
            ea = es * (df_out["humidity"].clip(0.0, 100.0) / 100.0)
            df_out["vpd"] = (es - ea).clip(lower=0.0)

        return df_out[EXTENDED_FEATURE_NAMES].astype(float)

    raise ValueError(f"Unknown feature schema '{schema}'. Choose 'basic' or 'extended'.")


def prepare_training_xy(
    df: pd.DataFrame,
    schema: str = "basic",
) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare feature matrix X and target vector y from dataset DataFrame."""
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in dataset.")

    x = extract_features(df, schema=schema)
    y = df[TARGET_COLUMN].astype(float)
    return x, y
