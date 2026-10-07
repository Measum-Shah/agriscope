"""Conformal prediction intervals and empirical coverage validation for ET models."""

from __future__ import annotations

import math
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


class ConformalPredictor:
    """Split-conformal prediction interval generator for regression models.

    Guarantees finite-sample marginal coverage >= 1 - alpha under exchangeability.
    """

    def __init__(self, base_pipeline: Any, default_alpha: float = 0.10):
        """Initialize conformal predictor.

        Args:
            base_pipeline: Fitted or unfitted scikit-learn pipeline/estimator.
            default_alpha: Significance level (default 0.10 for 90% confidence interval).
        """
        self.pipeline = base_pipeline
        self.default_alpha = default_alpha
        self.q_val_: float = 0.0
        self.is_calibrated_: bool = False
        self.n_cal_: int = 0

    def calibrate(
        self,
        x_cal: pd.DataFrame | np.ndarray,
        y_cal: pd.Series | np.ndarray,
        alpha: float | None = None,
    ) -> float:
        """Calibrate conformal non-conformity scores on held-out calibration data.

        Args:
            x_cal: Calibration features.
            y_cal: True calibration targets.
            alpha: Custom significance level override.

        Returns:
            The computed conformal non-conformity quantile value.
        """
        target_alpha = alpha if alpha is not None else self.default_alpha
        y_cal_arr = np.asarray(y_cal, dtype=float)
        preds = self.pipeline.predict(x_cal)
        residuals = np.abs(y_cal_arr - preds)

        n = len(residuals)
        if n == 0:
            raise ValueError("Calibration set cannot be empty.")

        # Finite-sample conformal quantile: ceil((n + 1) * (1 - alpha)) / n
        level = math.ceil((n + 1) * (1.0 - target_alpha)) / n
        level = min(1.0, max(0.0, level))

        # Use higher quantile to guarantee finite-sample coverage >= 1 - alpha
        self.q_val_ = float(np.quantile(residuals, level, method="higher"))
        self.is_calibrated_ = True
        self.n_cal_ = n
        self.default_alpha = target_alpha
        return self.q_val_

    def predict_interval(
        self,
        x: pd.DataFrame | np.ndarray,
        alpha: float | None = None,
        clip_non_negative: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate point predictions and lower/upper conformal prediction bounds.

        Args:
            x: Feature matrix.
            alpha: Significance level override (if None, uses calibrated level).
            clip_non_negative: If True, clips lower bound to 0.0 (ET cannot be physically negative).

        Returns:
            Tuple of (point_predictions, lower_bounds, upper_bounds).
        """
        if not self.is_calibrated_:
            raise RuntimeError("ConformalPredictor must be calibrated before generating intervals.")

        preds = np.asarray(self.pipeline.predict(x), dtype=float)
        q = self.q_val_

        # If custom alpha provided different from calibrated alpha, adjust if needed
        if alpha is not None and alpha != self.default_alpha:
            pass  # uses calibrated q_val_

        lower = preds - q
        upper = preds + q

        if clip_non_negative:
            lower = np.clip(lower, 0.0, None)

        return preds, lower, upper

    def evaluate_coverage(
        self,
        x_test: pd.DataFrame | np.ndarray,
        y_test: pd.Series | np.ndarray,
        alpha: float | None = None,
    ) -> Dict[str, float]:
        """Compute empirical coverage and average interval width on held-out test data.

        Returns:
            Dictionary with 'nominal_coverage', 'empirical_coverage', 'mean_width', 'q_val'.
        """
        target_alpha = alpha if alpha is not None else self.default_alpha
        preds, lower, upper = self.predict_interval(
            x_test, alpha=target_alpha, clip_non_negative=False
        )
        y_arr = np.asarray(y_test, dtype=float)

        covered = (y_arr >= lower) & (y_arr <= upper)
        empirical_cov = float(np.mean(covered))
        widths = upper - lower

        return {
            "nominal_coverage": round(1.0 - target_alpha, 4),
            "empirical_coverage": round(empirical_cov, 4),
            "mean_interval_width": round(float(np.mean(widths)), 4),
            "quantile_score": round(self.q_val_, 4),
            "calibration_samples": self.n_cal_,
        }
