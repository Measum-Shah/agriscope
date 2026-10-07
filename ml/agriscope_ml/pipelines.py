"""Scikit-Learn pipeline definitions for AgriScope ET machine learning models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from xgboost import XGBRegressor

SUPPORTED_ALGORITHMS: List[str] = [
    "random_forest",
    "xgboost",
    "lightgbm",
    "svr",
    "mlp",
    "ensemble",
]


def create_rf_regressor(params: Optional[Dict[str, Any]] = None, seed: int = 42) -> Pipeline:
    """Create a Random Forest regressor pipeline with StandardScaler."""
    p = {
        "n_estimators": 100,
        "max_depth": 12,
        "min_samples_split": 4,
        "min_samples_leaf": 2,
        "random_state": seed,
        "n_jobs": -1,
    }
    if params:
        p.update(params)
    return Pipeline([("scaler", StandardScaler()), ("model", RandomForestRegressor(**p))])


def create_xgb_regressor(params: Optional[Dict[str, Any]] = None, seed: int = 42) -> Pipeline:
    """Create an XGBoost regressor pipeline with StandardScaler."""
    p = {
        "n_estimators": 150,
        "max_depth": 6,
        "learning_rate": 0.08,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "random_state": seed,
        "n_jobs": -1,
    }
    if params:
        p.update(params)
    return Pipeline([("scaler", StandardScaler()), ("model", XGBRegressor(**p))])


def create_lgbm_regressor(params: Optional[Dict[str, Any]] = None, seed: int = 42) -> Pipeline:
    """Create a LightGBM regressor pipeline with StandardScaler."""
    p = {
        "n_estimators": 150,
        "max_depth": 6,
        "learning_rate": 0.08,
        "num_leaves": 31,
        "random_state": seed,
        "verbose": -1,
        "n_jobs": -1,
    }
    if params:
        p.update(params)
    return Pipeline([("scaler", StandardScaler()), ("model", LGBMRegressor(**p))])


def create_svr_regressor(params: Optional[Dict[str, Any]] = None) -> Pipeline:
    """Create a Support Vector Regressor pipeline with StandardScaler."""
    p = {
        "C": 15.0,
        "epsilon": 0.1,
        "kernel": "rbf",
    }
    if params:
        p.update(params)
    return Pipeline([("scaler", StandardScaler()), ("model", SVR(**p))])


def create_mlp_regressor(params: Optional[Dict[str, Any]] = None, seed: int = 42) -> Pipeline:
    """Create a Multi-Layer Perceptron regressor pipeline with StandardScaler."""
    p = {
        "hidden_layer_sizes": (64, 32),
        "activation": "relu",
        "alpha": 0.01,
        "learning_rate_init": 0.01,
        "max_iter": 400,
        "random_state": seed,
        "early_stopping": True,
        "n_iter_no_change": 15,
    }
    if params:
        p.update(params)
    return Pipeline([("scaler", StandardScaler()), ("model", MLPRegressor(**p))])


def create_stacking_ensemble(
    estimators: Optional[List[tuple]] = None,
    params: Optional[Dict[str, Any]] = None,
    seed: int = 42,
) -> Pipeline:
    """Create a Stacking ensemble regressor pipeline combining base models."""
    if estimators is None:
        estimators = [
            (
                "rf",
                RandomForestRegressor(n_estimators=80, max_depth=10, random_state=seed, n_jobs=-1),
            ),
            (
                "xgb",
                XGBRegressor(
                    n_estimators=100, max_depth=5, learning_rate=0.08, random_state=seed, n_jobs=-1
                ),
            ),
            (
                "lgb",
                LGBMRegressor(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.08,
                    random_state=seed,
                    verbose=-1,
                    n_jobs=-1,
                ),
            ),
            ("svr", SVR(C=10.0, epsilon=0.1)),
        ]

    p = {
        "estimators": estimators,
        "final_estimator": RidgeCV(),
        "cv": 5,
        "n_jobs": -1,
    }
    if params:
        p.update(params)

    return Pipeline([("scaler", StandardScaler()), ("model", StackingRegressor(**p))])


def get_pipeline(
    algorithm: str,
    params: Optional[Dict[str, Any]] = None,
    seed: int = 42,
) -> Pipeline:
    """Factory creating an sklearn pipeline for the requested algorithm.

    Args:
        algorithm: One of 'random_forest', 'xgboost', 'lightgbm', 'svr', 'mlp', 'ensemble'.
        params: Custom hyperparameter overrides passed to model constructor.
        seed: Random state for deterministic model initialization.

    Returns:
        Configured sklearn.pipeline.Pipeline.
    """
    algo = algorithm.lower().strip()
    if algo in ("random_forest", "rf"):
        return create_rf_regressor(params=params, seed=seed)
    if algo in ("xgboost", "xgb"):
        return create_xgb_regressor(params=params, seed=seed)
    if algo in ("lightgbm", "lgb"):
        return create_lgbm_regressor(params=params, seed=seed)
    if algo == "svr":
        return create_svr_regressor(params=params)
    if algo == "mlp":
        return create_mlp_regressor(params=params, seed=seed)
    if algo in ("ensemble", "stacking"):
        return create_stacking_ensemble(params=params, seed=seed)

    raise ValueError(
        f"Unsupported algorithm '{algorithm}'. Choose from: {', '.join(SUPPORTED_ALGORITHMS)}"
    )
