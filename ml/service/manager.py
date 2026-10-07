"""Thread-safe model manager supporting warm startup, hot-swapping, and fast inference."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from agriscope_ml.data.synthetic import generate_synthetic_et_dataset
from agriscope_ml.explain import ModelExplainer
from agriscope_ml.features import extract_features
from agriscope_ml.registry import ModelBundle, ModelRegistry
from agriscope_ml.train import train_single_model

from .schemas.inference import (
    BatchInferenceResponse,
    ExplainResponse,
    InferenceResponse,
    MeteorologicalInput,
    ModelSummaryResponse,
    classify_et,
)


class ModelManager:
    """Manages active ML models with zero-downtime hot swapping and pre-warmed pipelines."""

    def __init__(self, artifacts_dir: Optional[str | Path] = None):
        artifacts_path = artifacts_dir or os.getenv("ARTIFACTS_DIR", "./artifacts")
        self.registry = ModelRegistry(root_dir=artifacts_path)
        self._active_bundle: Optional[ModelBundle] = None
        self._active_explainer: Optional[ModelExplainer] = None
        self._lock = threading.Lock()
        self._loaded_models: Dict[str, ModelBundle] = {}
        self.start_time = time.time()

    @property
    def active_bundle(self) -> ModelBundle:
        if self._active_bundle is None:
            raise RuntimeError("No model is currently loaded in the ML service.")
        return self._active_bundle

    def warm_up(
        self,
        default_model: str = "agriscope_ensemble_basic",
        default_version: str = "v1.0",
    ) -> None:
        """Warm-load the active model at startup, bootstrapping if necessary."""
        models = self.registry.list_models()
        target_model = default_model
        target_version = default_version

        # Check if default model exists in registry
        found = any(
            m["model_id"] == target_model and m["version"] == target_version for m in models
        )

        if not found and models:
            # Fall back to first available registered model
            target_model = models[0]["model_id"]
            target_version = models[0]["version"]
            found = True

        if not found:
            # Bootstrap a default model if registry is empty
            df_boot = generate_synthetic_et_dataset(num_samples=500, seed=42)
            train_single_model(
                df=df_boot,
                algorithm="random_forest",
                version=default_version,
                feature_schema="basic",
                registry=self.registry,
                seed=42,
            )
            target_model = "agriscope_random_forest_basic"
            target_version = default_version

        # Load and warm model
        self.load_model(target_model, target_version)

    def load_model(self, model_id: str, version: str) -> None:
        """Hot-swap the active model bundle without dropping in-flight requests."""
        # Load new bundle from registry
        new_bundle = self.registry.get_model(model_id, version, verify=True)

        # Pre-warm SHAP explainer
        bg_data = (
            new_bundle.background_data
            if new_bundle.background_data is not None
            else pd.DataFrame(
                [[25.0, 50.0, 2.0, 18.0]],
                columns=new_bundle.model_card.feature_names,
            )
        )
        new_explainer = ModelExplainer(
            pipeline=new_bundle.pipeline,
            background_data=bg_data,
            feature_names=new_bundle.model_card.feature_names,
        )

        # Pre-warm prediction pipeline to compile caches
        dummy_df = pd.DataFrame(
            [
                {
                    "temperature": 25.0,
                    "humidity": 50.0,
                    "wind_speed": 2.0,
                    "solar_radiation": 18.0,
                }
            ]
        )
        feat = extract_features(dummy_df, schema=new_bundle.model_card.feature_schema)
        _ = new_bundle.pipeline.predict(feat)
        if new_bundle.conformal_predictor is not None:
            _ = new_bundle.conformal_predictor.predict_interval(feat)

        # Atomic pointer swap under lock
        with self._lock:
            self._active_bundle = new_bundle
            self._active_explainer = new_explainer
            key = f"{model_id}:{version}"
            self._loaded_models[key] = new_bundle

    def predict_single(self, obs: MeteorologicalInput) -> InferenceResponse:
        """Execute single inference observation with conformal interval and latency tracking."""
        t0 = time.perf_counter()
        bundle = self.active_bundle

        # Convert to DataFrame
        row = obs.model_dump(exclude_none=True)
        df_in = pd.DataFrame([row])
        features = extract_features(df_in, schema=bundle.model_card.feature_schema)

        # Predict
        y_pred, y_low, y_high = bundle.conformal_predictor.predict_interval(
            features, clip_non_negative=True
        )

        val = float(y_pred[0])
        low = float(y_low[0])
        high = float(y_high[0])
        classification = classify_et(val)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return InferenceResponse(
            et_value=round(val, 3),
            interval_low=round(low, 3),
            interval_high=round(high, 3),
            confidence_level=0.90,
            classification=classification,
            model_id=bundle.model_id,
            model_version=bundle.version,
            data_provenance=bundle.model_card.provenance,
            is_synthetic=bundle.model_card.is_synthetic,
            latency_ms=round(latency_ms, 2),
        )

    def predict_batch(self, observations: List[MeteorologicalInput]) -> BatchInferenceResponse:
        """Execute batch inference across an array of observations."""
        t0 = time.perf_counter()
        bundle = self.active_bundle

        records = [obs.model_dump(exclude_none=True) for obs in observations]
        df_in = pd.DataFrame(records)
        features = extract_features(df_in, schema=bundle.model_card.feature_schema)

        preds, lows, highs = bundle.conformal_predictor.predict_interval(
            features, clip_non_negative=True
        )

        total_latency_ms = (time.perf_counter() - t0) * 1000.0
        per_item_latency = round(total_latency_ms / max(1, len(records)), 3)

        results: List[InferenceResponse] = []
        for p, low_bound, high_bound in zip(preds, lows, highs):
            val = float(p)
            results.append(
                InferenceResponse(
                    et_value=round(val, 3),
                    interval_low=round(float(low_bound), 3),
                    interval_high=round(float(high_bound), 3),
                    confidence_level=0.90,
                    classification=classify_et(val),
                    model_id=bundle.model_id,
                    model_version=bundle.version,
                    data_provenance=bundle.model_card.provenance,
                    is_synthetic=bundle.model_card.is_synthetic,
                    latency_ms=per_item_latency,
                )
            )

        return BatchInferenceResponse(
            predictions=results,
            count=len(results),
            total_latency_ms=round(total_latency_ms, 2),
        )

    def explain(self, obs: MeteorologicalInput) -> ExplainResponse:
        """Compute SHAP feature attributions for an observation."""
        t0 = time.perf_counter()
        bundle = self.active_bundle
        explainer = self._active_explainer

        if explainer is None:
            raise RuntimeError("Model explainer is not available for the active model.")

        row = obs.model_dump(exclude_none=True)
        df_in = pd.DataFrame([row])
        features = extract_features(df_in, schema=bundle.model_card.feature_schema)

        exp = explainer.explain_instance(features)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return ExplainResponse(
            prediction=exp["prediction"],
            base_value=exp["base_value"],
            contributions=exp["contributions"],
            feature_ranking=exp["ranking"],
            model_id=bundle.model_id,
            model_version=bundle.version,
            latency_ms=round(latency_ms, 2),
        )

    def list_models(self) -> List[ModelSummaryResponse]:
        """List all models registered on disk/storage."""
        summaries: List[ModelSummaryResponse] = []
        reg_models = self.registry.list_models()
        active_id = self._active_bundle.model_id if self._active_bundle else ""
        active_ver = self._active_bundle.version if self._active_bundle else ""

        for m in reg_models:
            is_act = m["model_id"] == active_id and m["version"] == active_ver
            card = self.registry.get_model(m["model_id"], m["version"]).model_card
            summaries.append(
                ModelSummaryResponse(
                    model_id=m["model_id"],
                    version=m["version"],
                    algorithm=m["algorithm"],
                    is_active=is_act,
                    data_provenance=card.provenance,
                    is_synthetic=card.is_synthetic,
                    metrics=card.metrics,
                )
            )
        return summaries
