"""Tests for model pipeline definitions, supported algorithms, and determinism."""

from __future__ import annotations

import numpy as np
import pytest

from agriscope_ml.pipelines import SUPPORTED_ALGORITHMS, get_pipeline


def test_supported_algorithms():
    """Verify supported algorithms list."""
    expected = ["random_forest", "xgboost", "lightgbm", "svr", "mlp", "ensemble"]
    for algo in expected:
        assert algo in SUPPORTED_ALGORITHMS


@pytest.mark.parametrize("algo", ["random_forest", "xgboost", "lightgbm", "svr", "mlp"])
def test_pipeline_fit_predict(algo):
    """Verify each algorithm can be instantiated, fitted on dummy data, and predict."""
    np.random.seed(42)
    x = np.random.uniform(10, 40, size=(40, 4))
    y = 0.1 * x[:, 0] + 0.2 * x[:, 1] + 1.0

    pipe = get_pipeline(algo, seed=42)
    pipe.fit(x, y)
    preds = pipe.predict(x)

    assert len(preds) == len(y)
    assert not np.isnan(preds).any()


def test_seed_determinism():
    """Verify that training with the same random seed yields identical predictions."""
    np.random.seed(42)
    x = np.random.uniform(10, 40, size=(50, 4))
    y = 0.15 * x[:, 0] + 0.05 * x[:, 1] + np.random.normal(0, 0.1, size=50)

    pipe1 = get_pipeline("random_forest", params={"n_estimators": 25}, seed=123)
    pipe1.fit(x, y)
    preds1 = pipe1.predict(x)

    pipe2 = get_pipeline("random_forest", params={"n_estimators": 25}, seed=123)
    pipe2.fit(x, y)
    preds2 = pipe2.predict(x)

    assert np.allclose(
        preds1, preds2
    ), "Models trained with identical seed should produce identical outputs"
