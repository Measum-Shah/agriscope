"""Tests for conformal prediction intervals and coverage guarantees."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from agriscope_ml.uncertainty import ConformalPredictor


def test_conformal_calibration_and_coverage():
    """Verify split conformal coverage meets nominal level minus tolerance (>= 90% - 5%)."""
    np.random.seed(42)
    # Generate linear dataset with Gaussian noise
    x = np.random.uniform(10, 40, size=(500, 4))
    noise = np.random.normal(0, 0.5, size=500)
    y = 0.2 * x[:, 0] + 0.1 * x[:, 1] + noise

    # Split into train, calibration, test
    x_train, y_train = x[:200], y[:200]
    x_cal, y_cal = x[200:350], y[200:350]
    x_test, y_test = x[350:], y[350:]

    pipe = Pipeline([("scaler", StandardScaler()), ("model", LinearRegression())])
    pipe.fit(x_train, y_train)

    cp = ConformalPredictor(base_pipeline=pipe, default_alpha=0.10)
    q_score = cp.calibrate(x_cal, y_cal)

    assert q_score > 0.0
    assert cp.is_calibrated_

    # Predict intervals on test data
    preds, lower, upper = cp.predict_interval(x_test, clip_non_negative=False)
    assert len(lower) == len(x_test)
    assert np.all(upper >= lower)

    # Coverage check
    eval_cov = cp.evaluate_coverage(x_test, y_test)
    empirical_cov = eval_cov["empirical_coverage"]
    nominal_cov = eval_cov["nominal_coverage"]  # 0.90

    # Finite sample coverage condition: empirical coverage >= nominal - tolerance (0.05)
    assert empirical_cov >= (
        nominal_cov - 0.05
    ), f"Empirical coverage {empirical_cov} was below nominal {nominal_cov} minus tolerance"


def test_conformal_non_negative_clipping():
    """Verify non-negative clipping prevents negative ET bounds."""
    np.random.seed(42)
    x = np.array([[1.0, 1.0], [2.0, 2.0]])
    y = np.array([0.1, 0.2])

    pipe = Pipeline([("model", LinearRegression())])
    pipe.fit(x, y)

    cp = ConformalPredictor(base_pipeline=pipe, default_alpha=0.10)
    # Force large quantile score
    cp.q_val_ = 5.0
    cp.is_calibrated_ = True

    _, lower, upper = cp.predict_interval(x, clip_non_negative=True)
    assert np.all(lower >= 0.0)
    assert np.all(upper >= 0.0)
