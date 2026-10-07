"""Tests for SHAP explanations and additivity verification."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agriscope_ml.explain import ModelExplainer
from agriscope_ml.pipelines import create_rf_regressor


def test_shap_additivity_tree_model():
    """Verify SHAP additivity property: base_value + sum(contributions) == prediction."""
    np.random.seed(42)
    # Generate simple tabular dataset
    feature_cols = ["temperature", "humidity", "wind_speed", "solar_radiation"]
    x = pd.DataFrame(
        np.random.uniform(10, 40, size=(100, 4)),
        columns=feature_cols,
    )
    y = (
        0.15 * x["temperature"]
        - 0.05 * x["humidity"]
        + 0.3 * x["wind_speed"]
        + 0.2 * x["solar_radiation"]
    )

    pipeline = create_rf_regressor(params={"n_estimators": 20, "max_depth": 5}, seed=42)
    pipeline.fit(x, y)

    explainer = ModelExplainer(
        pipeline=pipeline,
        background_data=x.head(40),
        feature_names=feature_cols,
    )

    # Explain single test instance
    test_instance = x.iloc[0]
    explanation = explainer.explain_instance(test_instance)

    assert "prediction" in explanation
    assert "base_value" in explanation
    assert "contributions" in explanation
    assert len(explanation["contributions"]) == 4

    # Check additivity delta is within tight tolerance
    assert (
        explanation["additivity_delta"] < 1e-3
    ), f"SHAP additivity violated: delta = {explanation['additivity_delta']}"

    # Check global importance ranking
    importance = explainer.compute_global_importance(x.head(20))
    assert len(importance) == 4
    # Highest importance should be non-zero
    assert list(importance.values())[0] > 0.0
