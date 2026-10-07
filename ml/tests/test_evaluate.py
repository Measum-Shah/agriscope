"""Tests for evaluation metrics: R2, RMSE, MAE, bias, NSE, KGE, and CV."""

from __future__ import annotations

import numpy as np
import pytest

from agriscope_ml.evaluate import (
    calculate_kge,
    calculate_nse,
    compute_metrics,
    cross_validate_pipeline,
)
from agriscope_ml.pipelines import create_rf_regressor


def test_metrics_perfect_predictions():
    """Verify metrics return ideal values when predictions match ground truth exactly."""
    y = np.array([1.5, 2.5, 3.5, 4.5, 5.5])
    m = compute_metrics(y, y)

    assert m.r2 == 1.0
    assert m.nse == 1.0
    assert m.rmse == 0.0
    assert m.mae == 0.0
    assert m.bias == 0.0
    assert pytest.approx(m.kge, abs=1e-3) == 1.0
    assert m.sample_count == 5
    assert m.residuals.mean == 0.0


def test_metrics_known_constant_bias():
    """Verify bias, MAE, and RMSE behavior under known constant offset."""
    y_true = np.array([2.0, 4.0, 6.0, 8.0])
    y_pred = y_true + 1.0  # Constant positive bias of 1.0

    m = compute_metrics(y_true, y_pred)
    assert m.bias == 1.0
    assert m.mae == 1.0
    assert m.rmse == 1.0
    assert m.residuals.mean == -1.0  # y_true - y_pred = -1.0


def test_nse_formula_properties():
    """Verify NSE formula on known hydrological scenarios."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_mean = np.full_like(y_true, fill_value=np.mean(y_true))

    # Predicting the mean gives NSE = 0
    assert pytest.approx(calculate_nse(y_true, y_mean), abs=1e-4) == 0.0

    # Predictions worse than mean give NSE < 0
    y_bad = np.array([100.0, 200.0, 300.0, 400.0])
    assert calculate_nse(y_true, y_bad) < 0.0


def test_kge_formula_properties():
    """Verify KGE behaves as expected when scaled."""
    y_true = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
    # Scaled by 1.2 -> beta = 1.2, alpha = 1.2, r = 1.0
    y_scaled = y_true * 1.2
    kge = calculate_kge(y_true, y_scaled)
    assert kge < 1.0
    assert kge > 0.6  # High correlation but slight variability/mean discrepancy


def test_cross_validation_kfold():
    """Verify cross_validate_pipeline runs 3 folds and returns valid summary statistics."""
    np.random.seed(42)
    x = np.random.uniform(10, 40, size=(60, 4))
    y = 0.1 * x[:, 0] + 0.2 * x[:, 1] + 1.0

    pipe = create_rf_regressor(params={"n_estimators": 10}, seed=42)
    cv_res = cross_validate_pipeline(pipe, x, y, cv=3, seed=42)

    assert cv_res["cv_splits"] == 3
    assert len(cv_res["folds"]) == 3
    assert "r2" in cv_res["summary"]
    assert "rmse" in cv_res["summary"]
    assert cv_res["summary"]["rmse"]["mean"] >= 0.0
