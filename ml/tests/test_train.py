"""Tests for training workflows, grouped holdouts, and model cards."""

from __future__ import annotations

import pandas as pd

from agriscope_ml.data.synthetic import generate_synthetic_et_dataset
from agriscope_ml.registry import ModelRegistry
from agriscope_ml.train import (
    prepare_group_identifiers,
    train_single_model,
)


def test_prepare_group_identifiers():
    """Verify group identifier creation from location or synthetic partitions."""
    df_loc = pd.DataFrame({"location_name": ["Lahore", "Faisalabad"], "year": [2021, 2022]})
    groups = prepare_group_identifiers(df_loc)
    assert groups.iloc[0] == "Lahore_2021"

    df_synth = pd.DataFrame({"temperature": [20, 25, 30]})
    groups_synth = prepare_group_identifiers(df_synth)
    assert len(groups_synth) == 3


def test_train_single_model_dual_eval(tmp_path):
    """Verify train_single_model trains, evaluates random and grouped splits, and registers."""
    df = generate_synthetic_et_dataset(num_samples=150, seed=42)
    reg = ModelRegistry(root_dir=tmp_path)

    res = train_single_model(
        df=df,
        algorithm="random_forest",
        version="v1.0",
        feature_schema="basic",
        params={"n_estimators": 10, "max_depth": 4},
        registry=reg,
        seed=42,
    )

    assert res.algorithm == "random_forest"
    assert "r2" in res.random_metrics
    assert "r2" in res.grouped_metrics
    assert "empirical_coverage" in res.conformal_metrics

    # Verify registered in tmp_path
    loaded = reg.get_model("agriscope_random_forest_basic", "v1.0")
    assert loaded.model_card.algorithm == "random_forest"
    assert loaded.model_card.metrics["random_split"]["r2"] == res.random_metrics["r2"]
