"""SHAP model explainability for AgriScope ET models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor


class ModelExplainer:
    """SHAP explainer utilizing TreeExplainer for tree models and KernelExplainer fallback."""

    def __init__(
        self,
        pipeline: Any,
        background_data: pd.DataFrame,
        feature_names: Optional[List[str]] = None,
    ):
        """Initialize SHAP explainer with pipeline and representative background data.

        Args:
            pipeline: Scikit-learn Pipeline with ('scaler', StandardScaler()) and ('model', estimator).
            background_data: DataFrame of representative samples for baseline estimation.
            feature_names: Explicit feature column names.
        """
        self.pipeline = pipeline
        self.feature_names = (
            feature_names
            if feature_names is not None
            else (list(background_data.columns) if hasattr(background_data, "columns") else [])
        )

        # Check if pipeline contains a tree-based estimator
        model = (
            pipeline.named_steps.get("model", pipeline)
            if hasattr(pipeline, "named_steps")
            else pipeline
        )
        self.is_tree_model = isinstance(model, (RandomForestRegressor, XGBRegressor, LGBMRegressor))

        self.scaler = (
            pipeline.named_steps.get("scaler") if hasattr(pipeline, "named_steps") else None
        )
        self.model = model

        if self.is_tree_model:
            # Transform background samples if scaler present
            x_bg_transformed = (
                self.scaler.transform(background_data)
                if self.scaler is not None
                else np.asarray(background_data)
            )
            self.explainer = shap.TreeExplainer(self.model, data=x_bg_transformed)
        else:
            # Sample background dataset to maintain fast interactive inference
            bg_sample = shap.sample(background_data, min(50, len(background_data)), random_state=42)

            # Use wrapper function to prevent SHAP from mutating Pipeline.feature_names_in_ property
            def predict_wrapper(data):
                return self.pipeline.predict(data)

            self.explainer = shap.KernelExplainer(predict_wrapper, bg_sample)

    def explain_instance(
        self,
        x_single: pd.DataFrame | pd.Series | np.ndarray,
    ) -> Dict[str, Any]:
        """Compute per-feature SHAP contributions for a single observation.

        Args:
            x_single: 1D or single-row 2D input feature vector.

        Returns:
            Dictionary with prediction, base_value, contributions, and additivity delta.
        """
        if isinstance(x_single, pd.Series):
            df_in = pd.DataFrame([x_single])
        elif isinstance(x_single, np.ndarray) and x_single.ndim == 1:
            df_in = pd.DataFrame([x_single], columns=self.feature_names or None)
        elif isinstance(x_single, pd.DataFrame):
            df_in = x_single.iloc[[0]]
        else:
            df_in = pd.DataFrame(x_single, columns=self.feature_names or None)

        pred = float(self.pipeline.predict(df_in)[0])

        if self.is_tree_model:
            x_tf = self.scaler.transform(df_in) if self.scaler is not None else np.asarray(df_in)
            shap_raw = self.explainer.shap_values(x_tf)
            expected_val = self.explainer.expected_value
        else:
            shap_raw = self.explainer.shap_values(df_in, nsamples=100, silent=True)
            expected_val = self.explainer.expected_value

        # Extract scalar base value
        if isinstance(expected_val, (list, np.ndarray)):
            base_val = float(expected_val[0])
        else:
            base_val = float(expected_val)

        # Extract 1D array of shap values
        if isinstance(shap_raw, list):
            sv = np.asarray(shap_raw[0]).flatten()
        else:
            sv = np.asarray(shap_raw).flatten()

        names = (
            self.feature_names
            if self.feature_names and len(self.feature_names) == len(sv)
            else [f"feature_{i}" for i in range(len(sv))]
        )

        contributions: Dict[str, float] = {
            name: round(float(val), 4) for name, val in zip(names, sv)
        }

        # Additivity sanity check: base_value + sum(contributions) == prediction
        sum_contribs = float(np.sum(sv))
        reconstructed = base_val + sum_contribs
        additivity_delta = abs(pred - reconstructed)

        # Ranked contributions
        ranking: List[Tuple[str, float]] = sorted(
            [(k, abs(v)) for k, v in contributions.items()],
            key=lambda item: item[1],
            reverse=True,
        )

        return {
            "prediction": round(pred, 4),
            "base_value": round(base_val, 4),
            "contributions": contributions,
            "additivity_delta": round(additivity_delta, 6),
            "ranking": [name for name, _ in ranking],
        }

    def compute_global_importance(
        self,
        x_sample: pd.DataFrame,
    ) -> Dict[str, float]:
        """Compute mean absolute SHAP values across a representative sample."""
        if self.is_tree_model:
            x_tf = (
                self.scaler.transform(x_sample) if self.scaler is not None else np.asarray(x_sample)
            )
            shap_raw = self.explainer.shap_values(x_tf)
        else:
            shap_raw = self.explainer.shap_values(x_sample, nsamples=50, silent=True)

        sv = np.asarray(shap_raw)
        if sv.ndim > 2:
            sv = sv[0]

        mean_abs = np.mean(np.abs(sv), axis=0)
        names = (
            self.feature_names
            if self.feature_names and len(self.feature_names) == len(mean_abs)
            else [f"feature_{i}" for i in range(len(mean_abs))]
        )

        importance = {name: round(float(score), 4) for name, score in zip(names, mean_abs)}
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
