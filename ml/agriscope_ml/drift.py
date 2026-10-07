"""Data drift detection using Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class FeatureDriftResult:
    """Drift evaluation result for a single numerical feature."""

    feature: str
    psi: float
    psi_drift: bool
    psi_severity: str  # "none", "moderate", "significant"
    ks_statistic: float
    ks_pvalue: float
    ks_drift: bool
    is_drifted: bool


@dataclass
class DriftReport:
    """Comprehensive dataset drift report comparing reference vs current distributions."""

    drift_detected: bool
    drifted_features: List[str]
    feature_results: Dict[str, FeatureDriftResult]
    reference_sample_count: int
    current_sample_count: int
    psi_threshold: float
    ks_alpha: float


def calculate_psi(
    reference: np.ndarray | pd.Series,
    current: np.ndarray | pd.Series,
    num_bins: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """Calculate Population Stability Index (PSI) between reference and current samples.

    PSI = sum((P_i - Q_i) * ln(P_i / Q_i))
    where P_i is reference probability and Q_i is current probability.
    """
    ref = np.asarray(reference, dtype=float)
    curr = np.asarray(current, dtype=float)

    ref = ref[~np.isnan(ref)]
    curr = curr[~np.isnan(curr)]

    if len(ref) == 0 or len(curr) == 0:
        return 0.0

    # Create quantile bin edges based on reference distribution
    quantiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(ref, quantiles)
    # Ensure strictly increasing edges to prevent duplicate bin errors
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return 0.0

    # Broaden outer bounds slightly to enclose min and max
    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    ref_counts, _ = np.histogram(ref, bins=bin_edges)
    curr_counts, _ = np.histogram(curr, bins=bin_edges)

    # Fractions with epsilon smoothing
    ref_fractions = (ref_counts + epsilon) / (len(ref) + epsilon * len(ref_counts))
    curr_fractions = (curr_counts + epsilon) / (len(curr) + epsilon * len(curr_counts))

    psi_val = np.sum((ref_fractions - curr_fractions) * np.log(ref_fractions / curr_fractions))
    return float(max(0.0, psi_val))


def evaluate_feature_drift(
    feature_name: str,
    reference: np.ndarray | pd.Series,
    current: np.ndarray | pd.Series,
    psi_threshold: float = 0.20,
    ks_alpha: float = 0.05,
) -> FeatureDriftResult:
    """Evaluate drift on a single feature using both PSI and KS 2-sample test."""
    psi_val = calculate_psi(reference, current)

    if psi_val < 0.10:
        severity = "none"
        psi_drift = False
    elif psi_val < psi_threshold:
        severity = "moderate"
        psi_drift = False
    else:
        severity = "significant"
        psi_drift = True

    # 2-sample Kolmogorov-Smirnov test
    ref_clean = np.asarray(reference, dtype=float)
    ref_clean = ref_clean[~np.isnan(ref_clean)]
    curr_clean = np.asarray(current, dtype=float)
    curr_clean = curr_clean[~np.isnan(curr_clean)]

    if len(ref_clean) > 0 and len(curr_clean) > 0:
        ks_res = stats.ks_2samp(ref_clean, curr_clean)
        ks_stat = float(ks_res.statistic)
        ks_pval = float(ks_res.pvalue)
        ks_drift = ks_pval < ks_alpha
    else:
        ks_stat = 0.0
        ks_pval = 1.0
        ks_drift = False

    is_drifted = psi_drift or ks_drift

    return FeatureDriftResult(
        feature=feature_name,
        psi=round(psi_val, 4),
        psi_drift=psi_drift,
        psi_severity=severity,
        ks_statistic=round(ks_stat, 4),
        ks_pvalue=round(ks_pval, 6),
        ks_drift=ks_drift,
        is_drifted=is_drifted,
    )


def detect_dataset_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_names: Optional[List[str]] = None,
    psi_threshold: float = 0.20,
    ks_alpha: float = 0.05,
) -> DriftReport:
    """Detect distribution drift across all features comparing current data to reference."""
    cols = (
        feature_names
        if feature_names is not None
        else [
            col
            for col in reference_df.columns
            if col in current_df.columns and pd.api.types.is_numeric_dtype(reference_df[col])
        ]
    )

    feature_results: Dict[str, FeatureDriftResult] = {}
    drifted: List[str] = []

    for col in cols:
        res = evaluate_feature_drift(
            feature_name=col,
            reference=reference_df[col],
            current=current_df[col],
            psi_threshold=psi_threshold,
            ks_alpha=ks_alpha,
        )
        feature_results[col] = res
        if res.is_drifted:
            drifted.append(col)

    return DriftReport(
        drift_detected=len(drifted) > 0,
        drifted_features=drifted,
        feature_results=feature_results,
        reference_sample_count=len(reference_df),
        current_sample_count=len(current_df),
        psi_threshold=psi_threshold,
        ks_alpha=ks_alpha,
    )


def drift_report_to_dict(report: DriftReport) -> Dict[str, Any]:
    """Convert DriftReport to serializable dictionary."""
    return asdict(report)
