"""Tests for model artifact registry round-trip and integrity verification."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from agriscope_ml.model_card import create_model_card
from agriscope_ml.registry import ModelBundle, ModelRegistry
from agriscope_ml.uncertainty import ConformalPredictor


def test_registry_filesystem_round_trip(tmp_path):
    """Verify saving a bundle and loading it back verifies integrity and preserves predictions."""
    x = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]])
    y = np.array([2.0, 4.0, 6.0, 8.0])

    pipe = Pipeline([("model", LinearRegression())])
    pipe.fit(x, y)

    cp = ConformalPredictor(base_pipeline=pipe, default_alpha=0.10)
    cp.calibrate(x, y)

    card = create_model_card(
        model_id="test_model",
        algorithm="linear",
        version="v1.0",
        feature_schema="basic",
        feature_names=["f1", "f2"],
        hyperparameters={"fit_intercept": True},
        dataset_id="test_ds",
        dataset_hash="test_hash_12345",
        provenance="synthetic",
        is_synthetic=True,
        metrics={"r2": 1.0},
        conformal={"coverage": 1.0},
        training_time_seconds=0.12,
    )

    bundle = ModelBundle(
        model_id="test_model",
        version="v1.0",
        pipeline=pipe,
        conformal_predictor=cp,
        model_card=card,
        background_data=pd.DataFrame(x, columns=["f1", "f2"]),
    )

    reg = ModelRegistry(root_dir=tmp_path)
    checksums = reg.register_model(bundle)

    assert "model.joblib" in checksums
    assert "conformal.joblib" in checksums
    assert "model_card.json" in checksums

    # Load back with integrity verification
    loaded = reg.get_model("test_model", "v1.0", verify=True)

    assert loaded.model_id == "test_model"
    assert loaded.model_card.algorithm == "linear"
    # Verify predictions match exactly
    orig_preds = pipe.predict(x)
    loaded_preds = loaded.pipeline.predict(x)
    assert np.allclose(orig_preds, loaded_preds)


def test_registry_tamper_detection(tmp_path):
    """Verify that tampering with an artifact triggers an integrity verification error."""
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    y = np.array([2.0, 4.0])
    pipe = Pipeline([("model", LinearRegression())])
    pipe.fit(x, y)
    cp = ConformalPredictor(base_pipeline=pipe)
    cp.calibrate(x, y)

    card = create_model_card(
        model_id="tamper_test",
        algorithm="linear",
        version="v1.0",
        feature_schema="basic",
        feature_names=["f1", "f2"],
        hyperparameters={},
        dataset_id="ds",
        dataset_hash="hash",
        provenance="synthetic",
        is_synthetic=True,
        metrics={},
        conformal={},
        training_time_seconds=0.05,
    )
    bundle = ModelBundle(
        model_id="tamper_test",
        version="v1.0",
        pipeline=pipe,
        conformal_predictor=cp,
        model_card=card,
    )

    reg = ModelRegistry(root_dir=tmp_path)
    reg.register_model(bundle)

    # Tamper with the model file
    model_file = tmp_path / "tamper_test" / "v1.0" / "model.joblib"
    with open(model_file, "ab") as f:
        f.write(b"corrupted_bytes")

    with pytest.raises(ValueError, match="Integrity check failed"):
        reg.get_model("tamper_test", "v1.0", verify=True)
