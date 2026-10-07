"""Tests for PSI and Kolmogorov-Smirnov distribution drift detection."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agriscope_ml.drift import calculate_psi, detect_dataset_drift


def test_psi_and_ks_unshifted_data():
    """Verify that samples drawn from identical distributions show no drift."""
    np.random.seed(42)
    ref = np.random.normal(25.0, 5.0, size=500)
    curr = np.random.normal(25.0, 5.0, size=500)

    psi_val = calculate_psi(ref, curr)
    assert psi_val < 0.10  # Standard threshold for no drift

    df_ref = pd.DataFrame({"temp": ref, "wind": np.random.uniform(0, 10, 500)})
    df_curr = pd.DataFrame({"temp": curr, "wind": np.random.uniform(0, 10, 500)})

    report = detect_dataset_drift(df_ref, df_curr, psi_threshold=0.20, ks_alpha=0.01)
    assert not report.drift_detected
    assert len(report.drifted_features) == 0


def test_psi_and_ks_shifted_data():
    """Verify that significantly shifted distributions trigger drift detection."""
    np.random.seed(42)
    ref = np.random.normal(20.0, 3.0, size=500)
    # Severe shift: mean moves from 20 to 35
    curr = np.random.normal(35.0, 3.0, size=500)

    psi_val = calculate_psi(ref, curr)
    assert psi_val >= 0.20  # Significant shift

    df_ref = pd.DataFrame({"temp": ref})
    df_curr = pd.DataFrame({"temp": curr})

    report = detect_dataset_drift(df_ref, df_curr, psi_threshold=0.20, ks_alpha=0.05)
    assert report.drift_detected
    assert "temp" in report.drifted_features
    assert report.feature_results["temp"].psi_drift
    assert report.feature_results["temp"].ks_drift
