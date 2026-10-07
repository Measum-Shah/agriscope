"""Model training workflow with random and grouped-split evaluations and artifact registry."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from .data.datasets import compute_dataframe_hash
from .evaluate import compute_metrics, metrics_to_dict
from .features import BASIC_FEATURE_NAMES, EXTENDED_FEATURE_NAMES, extract_features
from .model_card import create_model_card
from .pipelines import SUPPORTED_ALGORITHMS, get_pipeline
from .registry import ModelBundle, ModelRegistry
from .uncertainty import ConformalPredictor


@dataclass
class TrainingResult:
    """Outcome of model training run including dual split metrics and bundle."""

    model_id: str
    algorithm: str
    version: str
    random_metrics: Dict[str, Any]
    grouped_metrics: Dict[str, Any]
    conformal_metrics: Dict[str, Any]
    training_time_seconds: float
    bundle: ModelBundle


def prepare_group_identifiers(df: pd.DataFrame) -> pd.Series:
    """Extract or synthesize grouping identifiers for location/year holdout splits."""
    if "location_name" in df.columns and "year" in df.columns:
        return df["location_name"].astype(str) + "_" + df["year"].astype(str)
    if "location_name" in df.columns:
        return df["location_name"].astype(str)
    if "latitude" in df.columns and "elevation" in df.columns:
        # Cluster geographic coordinates into grid cells
        lat_bin = (df["latitude"] // 5).astype(str)
        elev_bin = (df["elevation"] // 200).astype(str)
        return "geo_" + lat_bin + "_" + elev_bin

    # Deterministic fallback partitioning into 5 distinct groups
    n = len(df)
    indices = np.arange(n)
    return pd.Series((indices % 5).astype(str), index=df.index)


def split_data(
    df: pd.DataFrame,
    feature_schema: str = "basic",
    seed: int = 42,
) -> Tuple[
    Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series],
    Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series],
]:
    """Perform both (a) random 80/20 (+ calib) and (b) grouped location/year holdout split."""
    x = extract_features(df, schema=feature_schema)
    y = df["et"].astype(float)
    groups = prepare_group_identifiers(df)

    # 1. Random split: 70% train, 10% calib, 20% test
    x_tr_full, x_te_rand, y_tr_full, y_te_rand = train_test_split(
        x, y, test_size=0.20, random_state=seed
    )
    x_train_rand, x_cal_rand, y_train_rand, y_cal_rand = train_test_split(
        x_tr_full, y_tr_full, test_size=0.125, random_state=seed  # 0.125 * 0.8 = 0.10
    )

    # 2. Grouped split: 20% groups held out entirely for testing
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
    tr_idx, te_idx = next(gss.split(x, y, groups=groups))

    x_train_grp, y_train_grp = x.iloc[tr_idx], y.iloc[tr_idx]
    x_test_grp, y_test_grp = x.iloc[te_idx], y.iloc[te_idx]

    return (
        (x_train_rand, y_train_rand, x_cal_rand, y_cal_rand, x_te_rand, y_te_rand),
        (x_train_grp, y_train_grp, x_test_grp, y_test_grp),
    )


def train_single_model(
    df: pd.DataFrame,
    algorithm: str,
    version: str = "v1.0",
    feature_schema: str = "basic",
    params: Optional[Dict[str, Any]] = None,
    registry: Optional[ModelRegistry] = None,
    seed: int = 42,
) -> TrainingResult:
    """Train a single model architecture with dual evaluation and conformal calibration."""
    start_time = time.time()
    algo = algorithm.lower().strip()
    model_id = f"agriscope_{algo}_{feature_schema}"

    # Extract splits
    (
        (x_train, y_train, x_cal, y_cal, x_test_rand, y_test_rand),
        (x_train_grp, y_train_grp, x_test_grp, y_test_grp),
    ) = split_data(df, feature_schema=feature_schema, seed=seed)

    feature_cols = BASIC_FEATURE_NAMES if feature_schema == "basic" else EXTENDED_FEATURE_NAMES

    # 1. Train pipeline on random train split
    pipeline = get_pipeline(algo, params=params, seed=seed)
    pipeline.fit(x_train, y_train)

    # 2. Conformal calibration on held-out calibration split
    conformal = ConformalPredictor(base_pipeline=pipeline, default_alpha=0.10)
    conformal.calibrate(x_cal, y_cal)

    # 3. Evaluate random split
    rand_preds = pipeline.predict(x_test_rand)
    rand_eval = compute_metrics(y_test_rand, rand_preds)

    # 4. Evaluate grouped holdout split (model trained on non-held-out groups)
    grp_pipeline = get_pipeline(algo, params=params, seed=seed)
    grp_pipeline.fit(x_train_grp, y_train_grp)
    grp_preds = grp_pipeline.predict(x_test_grp)
    grp_eval = compute_metrics(y_test_grp, grp_preds)

    # 5. Evaluate conformal coverage
    conf_coverage = conformal.evaluate_coverage(x_test_rand, y_test_rand)

    elapsed = time.time() - start_time

    # Determine metadata
    provenance = str(df["provenance"].iloc[0]) if "provenance" in df.columns else "nasa_power"
    is_synth = bool(df["is_synthetic"].iloc[0]) if "is_synthetic" in df.columns else False
    data_hash = compute_dataframe_hash(df)

    card = create_model_card(
        model_id=model_id,
        algorithm=algo,
        version=version,
        feature_schema=feature_schema,
        feature_names=feature_cols,
        hyperparameters=params or {},
        dataset_id=f"dataset_{data_hash[:10]}",
        dataset_hash=data_hash,
        provenance=provenance,
        is_synthetic=is_synth,
        metrics={
            "random_split": metrics_to_dict(rand_eval),
            "grouped_split": metrics_to_dict(grp_eval),
        },
        conformal=conf_coverage,
        training_time_seconds=elapsed,
        description=f"AgriScope {algo.upper()} ET model ({feature_schema} schema).",
    )

    bundle = ModelBundle(
        model_id=model_id,
        version=version,
        pipeline=pipeline,
        conformal_predictor=conformal,
        model_card=card,
        background_data=x_train.head(100),
    )

    if registry:
        registry.register_model(bundle)

    return TrainingResult(
        model_id=model_id,
        algorithm=algo,
        version=version,
        random_metrics=metrics_to_dict(rand_eval),
        grouped_metrics=metrics_to_dict(grp_eval),
        conformal_metrics=conf_coverage,
        training_time_seconds=elapsed,
        bundle=bundle,
    )


def train_all_models(
    df: pd.DataFrame,
    version: str = "v1.0",
    feature_schema: str = "basic",
    registry: Optional[ModelRegistry] = None,
    seed: int = 42,
) -> Dict[str, TrainingResult]:
    """Train all supported model architectures plus Stacking Ensemble."""
    results: Dict[str, TrainingResult] = {}
    for algo in SUPPORTED_ALGORITHMS:
        res = train_single_model(
            df=df,
            algorithm=algo,
            version=version,
            feature_schema=feature_schema,
            registry=registry,
            seed=seed,
        )
        results[algo] = res
    return results


def load_dataset_from_source(dataset_path: str | Path) -> pd.DataFrame:
    """Load dataset from parquet or csv file path."""
    p = Path(dataset_path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset file '{p}' not found.")
    if p.suffix in (".parquet", ".pq"):
        return pd.read_parquet(p)
    return pd.read_csv(p)
