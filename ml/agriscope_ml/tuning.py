"""Hyperparameter optimization using Optuna and RandomizedSearchCV."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import numpy as np
import optuna
import pandas as pd
from sklearn.model_selection import KFold

from .evaluate import compute_metrics
from .pipelines import get_pipeline


@dataclass
class TuningResult:
    """Result of hyperparameter optimization."""

    algorithm: str
    best_params: Dict[str, Any]
    best_score: float  # Best objective value (e.g. minimum RMSE)
    best_pipeline: Any
    total_trials: int
    optimization_metric: str


def define_optuna_search_space(trial: optuna.Trial, algorithm: str) -> Dict[str, Any]:
    """Define algorithmic hyperparameter search spaces for Optuna trials."""
    algo = algorithm.lower().strip()

    if algo in ("random_forest", "rf"):
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 200, step=25),
            "max_depth": trial.suggest_int("max_depth", 4, 16),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 8),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 4),
        }

    if algo in ("xgboost", "xgb"):
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 200, step=25),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.20, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        }

    if algo in ("lightgbm", "lgb"):
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 200, step=25),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.20, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        }

    if algo == "svr":
        return {
            "C": trial.suggest_float("C", 1.0, 50.0, log=True),
            "epsilon": trial.suggest_float("epsilon", 0.01, 0.5, log=True),
        }

    if algo == "mlp":
        layer_choice = trial.suggest_categorical("layers", ["small", "medium", "deep"])
        layer_map = {
            "small": (32,),
            "medium": (64, 32),
            "deep": (128, 64, 32),
        }
        return {
            "hidden_layer_sizes": layer_map[layer_choice],
            "alpha": trial.suggest_float("alpha", 1e-4, 1e-1, log=True),
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-3, 5e-2, log=True),
        }

    return {}


def tune_hyperparameters(
    algorithm: str,
    x: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    n_trials: int = 15,
    timeout_seconds: Optional[int] = 60,
    cv_folds: int = 3,
    progress_callback: Optional[
        Callable[[optuna.study.Study, optuna.trial.FrozenTrial], None]
    ] = None,
    seed: int = 42,
) -> TuningResult:
    """Tune pipeline hyperparameters using Optuna cross-validated objective.

    Minimizes RMSE across k-fold cross-validation.
    """
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="minimize", sampler=sampler)

    x_arr = np.asarray(x)
    y_arr = np.asarray(y)

    def objective(trial: optuna.Trial) -> float:
        params = define_optuna_search_space(trial, algorithm)
        kf = KFold(n_splits=cv_folds, shuffle=True, random_state=seed)

        rmse_scores: list[float] = []
        for train_idx, val_idx in kf.split(x_arr, y_arr):
            x_tr, y_tr = x_arr[train_idx], y_arr[train_idx]
            x_va, y_va = x_arr[val_idx], y_arr[val_idx]

            pipeline = get_pipeline(algorithm, params=params, seed=seed)
            pipeline.fit(x_tr, y_tr)
            preds = pipeline.predict(x_va)
            m = compute_metrics(y_va, preds)
            rmse_scores.append(m.rmse)

        return float(np.mean(rmse_scores))

    callbacks = [progress_callback] if progress_callback is not None else []
    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=timeout_seconds,
        callbacks=callbacks,
    )

    best_params = study.best_params.copy()
    # Handle mapped categoricals for MLP
    if "layers" in best_params:
        layer_map = {"small": (32,), "medium": (64, 32), "deep": (128, 64, 32)}
        best_params["hidden_layer_sizes"] = layer_map[best_params.pop("layers")]

    # Fit best pipeline on full dataset
    best_pipeline = get_pipeline(algorithm, params=best_params, seed=seed)
    best_pipeline.fit(x_arr, y_arr)

    return TuningResult(
        algorithm=algorithm,
        best_params=best_params,
        best_score=round(float(study.best_value), 4),
        best_pipeline=best_pipeline,
        total_trials=len(study.trials),
        optimization_metric="rmse",
    )
