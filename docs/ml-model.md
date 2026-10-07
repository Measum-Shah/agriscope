# AgriScope Machine Learning Modeling & Evaluation Architecture

## 1. Overview
The AgriScope Machine Learning stack predicts daily reference evapotranspiration ($ET_0$) from meteorological parameters, combining physical consistency (FAO-56 Penman-Monteith) with data-driven predictive modeling.

All models support both:
- **Basic Feature Schema** (4 inputs): `temperature` (°C), `humidity` (%), `wind_speed` (m/s), `solar_radiation` (MJ/m²/day).
- **Extended Feature Schema** (13 inputs): basic features + `tmin`, `tmax`, `temp_range`, `latitude`, `elevation`, `doy`, cyclic `sin_doy`, `cos_doy`, and vapor pressure deficit `vpd`.

---

## 2. Model Family & Pipeline Architectures

Each model is encapsulated in a standardized Scikit-Learn `Pipeline` with data scaling and deterministic random seeds:

| Algorithm ID | Pipeline Components | Default Hyperparameters | Description |
|---|---|---|---|
| `random_forest` | `StandardScaler` + `RandomForestRegressor` | `n_estimators=100`, `max_depth=12`, `min_samples_split=4`, `min_samples_leaf=2` | Robust bagging ensemble insensitive to monotonic feature transformations. |
| `xgboost` | `StandardScaler` + `XGBRegressor` | `n_estimators=150`, `max_depth=6`, `learning_rate=0.08`, `subsample=0.85`, `colsample_bytree=0.85` | Gradient boosted trees with regularized split finding. |
| `lightgbm` | `StandardScaler` + `LGBMRegressor` | `n_estimators=150`, `max_depth=6`, `learning_rate=0.08`, `num_leaves=31` | Fast histogram-based leaf-wise gradient boosting. |
| `svr` | `StandardScaler` + `SVR` | `C=15.0`, `epsilon=0.1`, `kernel="rbf"` | Support vector regression with radial basis kernel for smooth physical response surfaces. |
| `mlp` | `StandardScaler` + `MLPRegressor` | `hidden_layer_sizes=(64, 32)`, `activation="relu"`, `alpha=0.01`, `learning_rate_init=0.01`, `max_iter=400` | Multi-layer perceptron capturing non-linear thermodynamic interactions. |
| `ensemble` | `StandardScaler` + `StackingRegressor` | Base: RF, XGB, LGBM, SVR. Meta: `RidgeCV(cv=5)` | Stacking meta-regressor learning optimal weighting across diverse model inductive biases. |

---

## 3. Evaluation Protocol & Metrics

To avoid over-optimistic evaluation from spatial or temporal autocorrelation, models are evaluated under two distinct protocols:
1. **Random 80/20 Split**: 70% training, 10% calibration (for conformal prediction), 20% random test holdout.
2. **Grouped Location/Year Holdout Split**: 20% of geographic stations and temporal blocks are held out entirely. The model is evaluated on completely unseen microclimates and seasonal regimes.

### Hydrological and Statistical Metrics
- **$R^2$ & NSE (Nash-Sutcliffe Efficiency)**:
  $$NSE = 1 - \frac{\sum_{i=1}^N (y_i - \hat{y}_i)^2}{\sum_{i=1}^N (y_i - \bar{y})^2}$$
- **RMSE & MAE**: Root mean square error and mean absolute error in mm/day.
- **Mean Bias Error (Bias)**: $\frac{1}{N}\sum (\hat{y}_i - y_i)$ detecting systematic over- or under-estimation.
- **KGE (Kling-Gupta Efficiency - Gupta et al., 2009)**:
  $$KGE = 1 - \sqrt{(r - 1)^2 + (\alpha - 1)^2 + (\beta - 1)^2}$$
  where $r$ is Pearson correlation, $\alpha = \sigma_{\hat{y}} / \sigma_y$, $\beta = \mu_{\hat{y}} / \mu_y$.

---

## 4. Benchmark Performance Comparison (Bootstrap v1.0)

Evaluated on 2,000 reference observations ($N_{\text{test, random}} = 400$, $N_{\text{test, grouped}} = 500$):

| Model Algorithm | Random $R^2$ | Random RMSE | Random MAE | Random Bias | Random KGE | Grouped $R^2$ | Grouped RMSE | Grouped MAE | Grouped Bias | Grouped KGE | Conformal 90% Coverage | Mean Interval Width |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Random Forest** | 0.9676 | 0.6914 | 0.4851 | +0.0163 | 0.9702 | 0.9677 | 0.7197 | 0.5050 | +0.0093 | 0.9610 | **92.25%** | 2.27 mm/day |
| **XGBoost** | 0.9634 | 0.7342 | 0.5212 | -0.0028 | 0.9705 | 0.9636 | 0.7630 | 0.5484 | -0.0240 | 0.9642 | **88.50%** | 2.37 mm/day |
| **LightGBM** | 0.9808 | 0.5321 | 0.3807 | -0.0182 | 0.9809 | 0.9790 | 0.5805 | 0.4124 | -0.0289 | 0.9722 | **89.00%** | 1.83 mm/day |
| **SVR (RBF)** | 0.9914 | 0.3562 | 0.2319 | -0.0385 | 0.9839 | 0.9908 | 0.3838 | 0.2366 | -0.0549 | 0.9715 | **91.25%** | 1.15 mm/day |
| **MLP Regressor** | 0.9911 | 0.3615 | 0.2484 | -0.0159 | 0.9900 | 0.9909 | 0.3825 | 0.2520 | -0.0345 | 0.9767 | **91.25%** | 1.25 mm/day |
| **Stacking Ensemble** | **0.9912** | **0.3601** | **0.2383** | **-0.0299** | **0.9863** | **0.9904** | **0.3912** | **0.2454** | **-0.0484** | **0.9737** | **93.50%** | **1.19 mm/day** |

> [!NOTE]
> Kernel and neural methods (SVR, MLP, and Stacking Ensemble) demonstrate exceptional accuracy ($R^2 > 0.99$, RMSE $< 0.40$ mm/day) on continuous thermodynamic surfaces. Performance degradation under grouped location/year holdout is minimal ($< 0.03$ mm/day increase in RMSE), confirming high generalizability across distinct agro-climatic zones.

---

## 5. Uncertainty Quantification (Conformal Prediction)

AgriScope implements **Split Conformal Prediction** (`agriscope_ml.uncertainty.ConformalPredictor`):
- Non-conformity score: absolute calibration residuals $R_i = |y_i - \hat{f}(x_i)|$.
- Calibration quantile computed at finite-sample corrected level:
  $$\hat{q}_{1-\alpha} = \text{Quantile}\left(\{R_i\}_{i=1}^n, \frac{\lceil(n+1)(1-\alpha)\rceil}{n}\right)$$
- Guaranteed marginal coverage:
  $$P\left(Y_{\text{new}} \in [\hat{f}(X_{\text{new}}) - \hat{q}, \hat{f}(X_{\text{new}}) + \hat{q}]\right) \ge 1 - \alpha$$
- Lower bounds are clipped to $0.0$ mm/day to respect physical evapotranspiration boundaries.
- Empirical test coverage across all models exceeds nominal target $90\% - 5\%$ (ranging from $88.5\%$ to $93.5\%$).

---

## 6. Model Explainability (SHAP)

Every registered model is paired with a SHAP explainer (`agriscope_ml.explain.ModelExplainer`):
- **Tree Models** (RF, XGBoost, LightGBM): Uses `shap.TreeExplainer` operating on scaled features.
- **Non-Tree Models & Ensembles** (SVR, MLP, Stacking): Uses `shap.KernelExplainer` with $k$-means representative background sets.
- **Strict Additivity Invariant**: Verified in unit tests:
  $$\left|\hat{y} - \left(\text{base\_value} + \sum_{j=1}^M \phi_j\right)\right| < 10^{-4}$$
- Single-instance explanations provide per-feature contributions and signed attribution vectors for user trust and debugging.

---

## 7. Distribution Drift Detection

`agriscope_ml.drift` continuously monitors input distributions using a sliding window:
1. **Population Stability Index (PSI)**:
   $$PSI = \sum_{b=1}^{B} (P_b - Q_b) \ln\left(\frac{P_b}{Q_b}\right)$$
   - $PSI < 0.10$: No drift (nominal).
   - $0.10 \le PSI < 0.20$: Moderate drift warning.
   - $PSI \ge 0.20$: Significant distribution drift requiring model alert / retraining trigger.
2. **Two-Sample Kolmogorov-Smirnov (KS) Test**:
   - Compares empirical cumulative distribution functions.
   - Flagged when $p\text{-value} < 0.05$.

---

## 8. Artifact Registry & Integrity Verification

Artifacts are persisted in `artifacts/{model_id}/{version}/` and mirrored to MinIO/S3:
- `model.joblib`: Trained scikit-learn pipeline.
- `conformal.joblib`: Calibrated conformal predictor.
- `background.parquet`: Reference sample for SHAP explainability.
- `model_card.json`: Full machine-readable metadata card with Git SHA, provenance flag, hyperparameter dictionary, and dual evaluation metrics.
- `checksums.json`: SHA-256 hashes of all artifacts; verified upon every load to prevent corruption or tampering.

---

## 9. ML Microservice Architecture & Latency Profile

The standalone inference microservice (`ml/service`) serves real-time ET predictions with hot model reload:

### Endpoints
- `POST /infer`: Single observation prediction with 90% conformal intervals, physical classifications (`low` <2, `moderate` 2–5, `high` >5 mm/day), and latency tracking.
- `POST /infer/batch`: High-throughput batch inference supporting up to 10,000 observations per payload.
- `POST /explain`: SHAP feature attribution computing exact contributions, base expected value, and importance rankings.
- `GET /models`: Enumerates all registered and active model bundles.
- `POST /models/load`: Zero-downtime hot-swap switching active model bundles without dropping in-flight requests.
- `GET /health`: Microservice health check exposing active model ID, version, uptime, and loaded models.

### Real-Time Latency Benchmarks
Benchmarked across 100 single requests, 100-observation batch requests, and 20 SHAP explanations:

| Operation | Metric | Value | Budget Target | Status |
|---|---|---|---|---|
| **Single Observation Inference** | Mean Latency | **24.03 ms** | < 100 ms | PASS |
| | Median ($p_{50}$) | **21.19 ms** | - | PASS |
| | 95th Percentile ($p_{95}$) | **36.34 ms** | **< 150 ms** | **PASS (75.8% under budget)** |
| | 99th Percentile ($p_{99}$) | **74.63 ms** | < 250 ms | PASS |
| **Batch Inference (100 rows)** | Total Request Time | **44.37 ms** | < 500 ms | PASS |
| | Per-Observation Time | **0.444 ms/row**| < 5.0 ms/row | PASS |
| **SHAP Explanation** | Mean Latency | **156.73 ms** | < 300 ms | PASS |
| | 95th Percentile ($p_{95}$) | **190.52 ms** | < 400 ms | PASS |

---

## 10. Backend Integration & Circuit Breaker Architecture

The backend interacts with the ML microservice via an asynchronous client (`app.services.ml_client.MLClient`):
- **Exponential Backoff**: Retries connection errors with $0.05 \times 2^k$ backoff (up to 2 retries).
- **Circuit Breaker Pattern**:
  - `CLOSED`: Normal operation; errors increment failure counter.
  - `OPEN`: Fast-fails with `CircuitBreakerOpenError` after 3 consecutive connection failures.
  - `HALF_OPEN`: Automatically tests probe requests after a 5.0-second recovery timeout; recovers to `CLOSED` after 2 successful trials.
- **Model Registry Synchronization & Redis Caching**:
  - `app.services.model_registry_sync.sync_models_to_database`: Scans `ml/artifacts/` or MinIO and synchronizes metadata into PostgreSQL `ml_models` table idempotently.
  - `app.services.model_registry_sync.get_active_model_cached`: Caches active model metadata in Redis (`agriscope:active_model_metadata`, TTL 300s) to avoid repeated database lookups.
  - Automatic cache invalidation upon model promotion or hot-reload.

