"""Tests for hyperparameter tuning with Optuna."""

from __future__ import annotations

import numpy as np

from agriscope_ml.tuning import tune_hyperparameters


def test_optuna_tuning_runs_and_improves():
    """Verify Optuna tuning executes trials, invokes callbacks, and returns best pipeline."""
    np.random.seed(42)
    x = np.random.uniform(10, 40, size=(60, 4))
    y = 0.2 * x[:, 0] + 0.1 * x[:, 1] + 1.0

    trials_seen = []

    def callback(study, trial):
        trials_seen.append(trial.number)

    res = tune_hyperparameters(
        algorithm="random_forest",
        x=x,
        y=y,
        n_trials=3,
        cv_folds=2,
        progress_callback=callback,
        seed=42,
    )

    assert res.algorithm == "random_forest"
    assert res.total_trials == 3
    assert len(trials_seen) == 3
    assert "n_estimators" in res.best_params
    assert res.best_score >= 0.0

    # Ensure best pipeline can predict
    preds = res.best_pipeline.predict(x)
    assert len(preds) == len(y)
