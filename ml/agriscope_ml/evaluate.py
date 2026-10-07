"""Evaluation metrics and cross-validation for AgriScope ET models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, KFold


@dataclass
class ResidualSummary:
    """Statistical summary of model prediction residuals (y_true - y_pred)."""

    mean: float
    std: float
    median: float
    min: float
    max: float
    p25: float
    p75: float


@dataclass
class EvaluationMetrics:
    """Standard evaluation metrics for ET hydrological/meteorological regression."""

    r2: float
    rmse: float
    mae: float
    bias: float
    nse: float
    kge: float
    sample_count: int
    residuals: ResidualSummary


def calculate_nse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Nash-Sutcliffe Efficiency (NSE).

    NSE = 1 - [sum((y_true - y_pred)^2) / sum((y_true - mean(y_true))^2)]
    Ranges from -inf to 1.0 (1.0 = perfect match).
    """
    denominator = np.sum((y_true - np.mean(y_true)) ** 2)
    if denominator == 0.0:
        return 1.0 if np.allclose(y_true, y_pred) else 0.0
    numerator = np.sum((y_true - y_pred) ** 2)
    return float(1.0 - (numerator / denominator))


def calculate_kge(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Kling-Gupta Efficiency (KGE, Gupta et al. 2009).

    KGE = 1 - sqrt((r - 1)^2 + (alpha - 1)^2 + (beta - 1)^2)
    where:
        r = Pearson correlation coefficient
        alpha = std(y_pred) / std(y_true)  (relative variability)
        beta = mean(y_pred) / mean(y_true) (bias ratio)
    """
    std_true = np.std(y_true)
    std_pred = np.std(y_pred)
    mean_true = np.mean(y_true)
    mean_pred = np.mean(y_pred)

    # Correlation
    if std_true > 1e-8 and std_pred > 1e-8:
        cov = np.cov(y_true, y_pred)[0, 1]
        r = cov / (std_true * std_pred)
        r = float(np.clip(r, -1.0, 1.0))
    else:
        r = 1.0 if np.allclose(y_true, y_pred) else 0.0

    # Variability ratio alpha
    alpha = float(std_pred / std_true) if std_true > 1e-8 else (1.0 if std_pred == 0.0 else 2.0)

    # Bias ratio beta
    beta = (
        float(mean_pred / mean_true)
        if abs(mean_true) > 1e-8
        else (1.0 if abs(mean_pred) < 1e-8 else 2.0)
    )

    kge_val = 1.0 - np.sqrt((r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2)
    return float(kge_val)


def compute_metrics(
    y_true: np.ndarray | pd.Series | List[float],
    y_pred: np.ndarray | pd.Series | List[float],
) -> EvaluationMetrics:
    """Compute R², RMSE, MAE, bias, NSE, KGE, and residual summary statistics."""
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    if len(yt) != len(yp):
        raise ValueError(f"Length mismatch: y_true ({len(yt)}) vs y_pred ({len(yp)})")
    if len(yt) == 0:
        raise ValueError("Cannot evaluate metrics on empty arrays.")

    residuals = yt - yp

    # R2 / NSE
    nse = calculate_nse(yt, yp)
    kge = calculate_kge(yt, yp)

    # RMSE & MAE
    rmse = float(np.sqrt(np.mean(residuals**2)))
    mae = float(np.mean(np.abs(residuals)))

    # Bias (Mean Error = mean(y_pred - y_true))
    bias = float(np.mean(yp - yt))

    # Sklearn-compatible R2 (same as NSE on test set)
    r2 = nse

    res_summary = ResidualSummary(
        mean=round(float(np.mean(residuals)), 4),
        std=round(float(np.std(residuals)), 4),
        median=round(float(np.median(residuals)), 4),
        min=round(float(np.min(residuals)), 4),
        max=round(float(np.max(residuals)), 4),
        p25=round(float(np.percentile(residuals, 25)), 4),
        p75=round(float(np.percentile(residuals, 75)), 4),
    )

    return EvaluationMetrics(
        r2=round(r2, 4),
        rmse=round(rmse, 4),
        mae=round(mae, 4),
        bias=round(bias, 4),
        nse=round(nse, 4),
        kge=round(kge, 4),
        sample_count=len(yt),
        residuals=res_summary,
    )


def cross_validate_pipeline(
    pipeline: Any,
    x: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    cv: int = 5,
    groups: Optional[pd.Series | np.ndarray] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """Perform k-fold or group k-fold cross-validation, computing mean and std metrics."""
    x_arr = np.asarray(x)
    y_arr = np.asarray(y)

    if groups is not None:
        splitter = GroupKFold(n_splits=cv)
        split_gen = splitter.split(x_arr, y_arr, groups=np.asarray(groups))
    else:
        splitter = KFold(n_splits=cv, shuffle=True, random_state=seed)
        split_gen = splitter.split(x_arr, y_arr)

    fold_metrics: List[Dict[str, float]] = []

    for train_idx, val_idx in split_gen:
        x_tr, y_tr = x_arr[train_idx], y_arr[train_idx]
        x_va, y_va = x_arr[val_idx], y_arr[val_idx]

        pipeline.fit(x_tr, y_tr)
        preds = pipeline.predict(x_va)
        metrics = compute_metrics(y_va, preds)
        fold_metrics.append(
            {
                "r2": metrics.r2,
                "rmse": metrics.rmse,
                "mae": metrics.mae,
                "bias": metrics.bias,
                "nse": metrics.nse,
                "kge": metrics.kge,
            }
        )

    # Compute mean and std for each metric
    summary: Dict[str, Dict[str, float]] = {}
    for key in ["r2", "rmse", "mae", "bias", "nse", "kge"]:
        vals = [f[key] for f in fold_metrics]
        summary[key] = {
            "mean": round(float(np.mean(vals)), 4),
            "std": round(float(np.std(vals)), 4),
        }

    return {
        "folds": fold_metrics,
        "summary": summary,
        "cv_splits": cv,
    }


def metrics_to_dict(metrics: EvaluationMetrics) -> Dict[str, Any]:
    """Convert EvaluationMetrics dataclass to JSON-serializable dictionary."""
    return asdict(metrics)
