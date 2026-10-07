# Architecture Decision Records (ADRs)

This document tracks key architectural decisions, rationale, and context for the AgriScope platform.

---

## ADR Template

### ADR [Number]: [Title]

- **Status**: [Proposed | Accepted | Superseded | Deprecated]
- **Date**: [YYYY-MM-DD]
- **Deciders**: [List of participants]

#### Context
[Describe the context, problem statement, and forces at play.]

#### Decision
[State the chosen architectural decision and technical direction.]

#### Consequences
- **Positive**: [Benefits, simplifications, performance improvements]
- **Negative / Trade-offs**: [Drawbacks, complexity added, technical debt accepted]
- **Compliance / Notes**: [Testing considerations, documentation requirements]

---

## ADR 001: Repository Scaffold and Infrastructure Layout

- **Status**: Accepted
- **Date**: 2026-10-06
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope requires a production-grade, modular structure uniting FastAPI backend services, a standalone ML package (`agriscope_ml`), a separate ML FastAPI inference microservice, a Celery worker/beat pipeline, a React 18 TypeScript frontend, and observability infrastructure (Prometheus, Grafana, Mailpit, MinIO, PostgreSQL + PostGIS). The project must support fully offline development while adhering strictly to fixed architectural boundaries.

#### Decision
1. Implemented the authoritative directory structure defined in `PROJECT_CONTEXT.md` Section D without deviations.
2. Configured multi-container Docker Compose with distinct profiles for dev and prod, isolating networks and establishing healthcheck dependencies.
3. Created an isolated `agriscope_ml` package decoupled from database and web frameworks.
4. Enforced uniform error formatting `{detail, code, request_id}` via FastAPI exception handlers and correlation ID middleware (`RequestIDMiddleware`).
5. Standardized physical meteorological validation ranges in `src/utils/constants.ts` (temperature -10..50 °C, humidity 0..100 %, wind 0..30 m/s, solar radiation 0..35 MJ/m²/day).

#### Consequences
- **Positive**: Ensures strict layering (routers → services → models/providers), clean offline fallback mechanisms via provider mocks, and reproducible CI/CD verification.
- **Trade-offs**: Requires disciplined maintenance of schemas, provider interfaces, and multi-stage container definitions as domain models expand.

---

## ADR 002: Relational Data Model & PostGIS Geospatial Schema Design

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
The AgriScope platform requires a complete data model mapping all aspects of user authentication, RBAC, token rotation, field polygons, remote-sensing observations, FAO-56 crop stages, model governance, batch prediction jobs, and audit logs. The model must strictly enforce physical validation ranges via database check constraints, support spatial indexing for field geometries, provide composite indices for time-series queries, and support idempotent seeding of FAO-56 reference crops and system administrators.

#### Decision
1. Defined 20 SQLAlchemy 2.0 ORM models inheriting from `Base` and `TimestampMixin` with `__future__.annotations` and `TYPE_CHECKING` guards.
2. Implemented PostGIS geometry on `fields.geometry` (SRID 4326) with GIST indexing.
3. Created explicit database check constraints on `predictions` (temperature -10..50 °C, humidity 0..100 %, wind 0..30 m/s, solar radiation 0..35 MJ/m²/day) and `field_observations` (`cloud_cover_pct` 0..100 %).
4. Configured composite indexes for critical query paths:
   - `predictions(user_id, timestamp)`
   - `field_observations(field_id, observation_date)`
   - `audit_logs(actor, timestamp)`
   - `fields(user_id, name)`
5. Enforced cascading and nullification rules across all foreign keys (`CASCADE` for user/field-owned entities, `SET NULL` for reference entities like models and crops).
6. Authored initial Alembic migration `0001_initial.py` defining full DDL across all 20 tables and indexes.
7. Implemented idempotent seeding in `app/db/init_db.py` populating 20 reference FAO-56 crops with growth stage lengths and initializing the default administrator.

#### Consequences
- **Positive**: Strict data integrity at the database layer; high query efficiency via targeted composite and spatial indexes; full auditability and ML governance.
- **Trade-offs**: SQLite in-memory unit tests require selective metadata creation or dialect isolation for Postgres-specific types (e.g. `JSONB`, `ARRAY`, `Geometry`), while integration tests verify PostGIS in PostgreSQL.

---

## ADR 003: Authentication Core, Refresh Token Family Rotation & Lockout Defense

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
User authentication requires strict defense against credential stuffing, timing attacks, token replay, and unauthorized privilege escalation. It must conform to the 15-minute lockout requirement, constant-time responses, single-use password resets, and session audit trails.

#### Decision
1. **Refresh Token Family Rotation**: Refresh tokens are stored only in httpOnly, secure, SameSite cookies. Each rotation revokes the active token and issues a replacement in the same `token_family`. Presenting a previously revoked token invalidates the entire family immediately to neutralize token replay.
2. **Account Lockout & Auto-Unlock**: 5 consecutive login failures set `locked_until = now + 15 min`. Verification normalizes timezones and auto-unlocks after 15 minutes without human intervention.
3. **Enumeration Resistance**: Bad logins for non-existent users perform constant-time dummy password hashing with identical error messages to obscure account presence.
4. **Single-Use Password Reset**: Password reset tokens encode a hash snippet (`pwd_ver`) matching the user's password state when issued. Modifying the password immediately renders old reset tokens invalid and revokes all active sessions (`logout-all`).
5. **Auditing & Rate Limiting**: Every authentication attempt and lifecycle change logs an event to `audit_logs`. Endpoints are protected by Redis sliding-window limiters with memory fallback.

#### Consequences
- **Positive**: Hardened defense against session hijacking, brute force, and token leakage; zero plaintext token storage; thorough auditability.
- **Trade-offs**: Requires cookie-aware clients in web and API testing; Celery worker pipeline is integrated for async emails with synchronous direct-dispatch fallback in dev/test.

---

## ADR 004: Centralized Entitlements Matrix, Quota Service, and Multi-Factor Account Security

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope differentiates between Free, Pro, and Admin tiers across inference volume (e.g. 10/day vs unlimited), features (satellite indices, Sentinel-2 pipeline, custom Kc, GeoJSON/PDF exports, API access), and administrative controls. Furthermore, production security mandates RFC 6238 TOTP two-factor authentication, single-use recovery codes, GDPR-compliant account data exports, re-verified email changes, and comprehensive user-facing audit trails.

#### Decision
1. **Centralized Entitlement Matrix**: Implemented `backend/app/core/plans.py` mapping `PlanEntitlements` per tier. Features and daily quotas are explicitly typed and validated.
2. **QuotaService with Atomic Counters**: Implemented Redis-backed daily quota tracking with ISO date keys (`quota:{user_id}:{YYYY-MM-DD}`) and automatic 24-hour TTL expiry. Integrated an in-memory dictionary fallback with identical TTL logic for testing and offline execution.
3. **`require_plan_feature` Dependency**: Created FastAPI dependency factory enforcing feature entitlements and rejecting unauthorized requests with HTTP 403 `UPGRADE_REQUIRED`.
4. **RFC 6238 TOTP 2FA**:
   - Provisioning generates a base32 secret and standard `otpauth://` URI with QR code generated in PNG base64 format.
   - Enabling requires proof-of-possession via a 6-digit code.
   - Issues 8 cryptographically secure recovery codes stored as SHA-256 hashes (`totp_recovery_codes`), single-use upon consumption.
   - Login flow issues a temporary `2FA_REQUIRED:<temp_token>` challenge if TOTP is enabled and validates either standard 6-digit TOTP or a valid recovery code before issuing the access/refresh token pair.
5. **Account Self-Service**:
   - Profile update with validation.
   - Email change requiring current password and verification token sent to the target email address.
   - Password change invalidating all other active sessions while preserving current session.
   - Full GDPR JSON data export (`GET /api/v1/users/me/export`) aggregating user profile, sessions, audit logs, fields, and predictions.
   - Soft deletion setting status to `deleted`, scrubbing active sessions, and recording deletion audit events.
6. **Audit Trail Exposure**: Dedicated `/api/v1/users/me/audit` endpoint allowing users to inspect their own security and lifecycle events.

#### Consequences
- **Positive**: Declarative feature gating across all future prediction and satellite routes; robust defense-in-depth with multi-factor authentication; complete user self-service and compliance ready.
- **Trade-offs**: Recovery codes require SHA-256 lookup in a JSON list; hard account purges are deferred to scheduled background cleanup jobs.

---

## ADR 005: Frontend Foundation, Design System, and Accessible Account Screens

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope requires a responsive, high-contrast, accessible UI system aligned with agricultural and meteorological science. The frontend must handle silent cookie-based token refreshes without jarring interruptions, defend against concurrent refresh races, enforce route protection by role and subscription feature entitlement, support light/dark modes via CSS variables, and comply with WCAG 2.1 AA accessibility guidelines validated by axe-core.

#### Decision
1. **Design System & Palette**: Built 15 atomic UI primitives in `components/ui` (`Button`, `Input`, `Select`, `Checkbox`, `Modal`, `ConfirmDialog`, `Table`, `Card`, `Badge`, `Tabs`, `Toast`, `Skeleton`, `EmptyState`, `Spinner`, `Tooltip`) leveraging Radix UI primitives. Defined a deep-green palette (`#15803d` primary, `#052e16` background accents) using CSS variables with instant light/dark toggle and persistence.
2. **Resilient HTTP Client & Silent Refresh**: Implemented typed Axios instance with request UUID tracing (`X-Request-ID`), access token injection, and an interceptor queuing 401 requests during silent `/api/v1/auth/refresh` execution via httpOnly cookies. Dispatches `auth:unauthorized` on persistent token rejection.
3. **Authentication State & Route Guards**:
   - `AuthContext`: Hydrates user profile and entitlements on boot, handles standard logins as well as multi-factor challenges (`2FA_REQUIRED`).
   - `ProtectedRoute`: Shields dashboard routes and navigates to `/login` preserving intended destination.
   - `RoleRoute`: Verifies allowed roles and renders an access-restricted view for unauthorized roles.
   - `PlanRoute`: Checks feature entitlement flags and presents a clear upgrade prompt when a feature is locked to Free-tier accounts.
4. **Form Architecture & Physical Validation**: React Hook Form with `@hookform/resolvers/zod` referencing shared boundaries in `utils/constants.ts` (e.g. password rules: min 8, uppercase, digit; physical ranges: temp -10..50 °C, humidity 0..100%, wind 0..30 m/s, solar radiation 0..35 MJ/m²/day).
5. **Account Management Screens**: Complete suite covering Login (with 2FA challenge), Register, VerifyEmail (auto-detect query token + manual resend), ForgotPassword, ResetPassword, Profile updates, Email change re-verification, Password change, TOTP 2FA setup with QR code + 8 recovery codes, active session termination, security audit logging, GDPR JSON export, and double-confirmed account deletion.
6. **Accessibility Verification**: Built test suite with `axe-core` verifying zero automated WCAG violations across all public auth pages.

#### Consequences
- **Positive**: Strict decoupling of UI components; seamless silent session renewal; fully accessible forms; reusable upgrade and role gates; end-to-end verified across unit and accessibility tests.
- **Trade-offs**: Color contrast rule in axe-core is disabled in jsdom due to layout box simulation limitations; real browser contrast checks should be maintained during manual visual review.

---

## ADR 006: FAO-56 Penman-Monteith Physics, Crop Coefficients, and Agroclimatology Data Pipeline

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope estimates daily reference evapotranspiration ($ET_0$) and crop evapotranspiration ($ET_c$) through rigorous FAO-56 Penman-Monteith formulations and remote-sensing vegetation indices. Machine learning pipelines require reproducible, quality-controlled daily training datasets combining global observations (NASA POWER agroclimatology) with a labelled offline fallback generator that guarantees transparency.

#### Decision
1. **FAO-56 Penman-Monteith Formulation (`physics/penman_monteith.py`)**:
   - Implemented exact FAO-56 daily formulation computing all intermediate thermodynamic terms: psychrometric constant $\gamma(z)$, slope of saturation vapour pressure curve $\Delta(T)$, mean saturation vapour pressure $e_s$, actual vapour pressure $e_a$, vapour pressure deficit $(e_s - e_a)$, extraterrestrial radiation $R_a(\varphi, J)$, clear-sky solar radiation $R_{so}$, net shortwave radiation $R_{ns}$, net longwave radiation $R_{nl}$, net radiation $R_n$, and 2-meter wind speed profile adjustment $u_2(z_w)$.
   - Validated against FAO-56 worked examples (e.g. Bangkok Example 18 benchmark).
   - Created a documented simplified 4-input fallback $(T, RH, u_2, R_s)$ with explicit agricultural default assumptions ($z=100\text{ m}$, diurnal temperature swing $\Delta T = 10^\circ\text{C}$, clear-sky fraction $\approx 0.65$).
2. **Crop Coefficients & Satellite Scaling (`physics/crop_coefficients.py`)**:
   - FAO-56 piecewise 4-stage linear interpolation ($L_{\text{ini}}, L_{\text{dev}}, L_{\text{mid}}, L_{\text{late}}$) with stage classification.
   - Remote-sensing NDVI to $K_c$ transformation using dense canopy fraction scaling bounded strictly by physical limits ($0.15 \le K_c \le 1.35$).
   - Standard crop evapotranspiration calculation: $ET_c = K_c \times ET_0$.
3. **NASA POWER Agroclimatology Client (`data/nasa_power.py`)**:
   - Curated list of 50 diverse agricultural stations across Pakistan (Faisalabad, Multan, Lahore, Hyderabad, Quetta, Peshawar, Nawabshah, Sukkur, etc.), South Asia, Mediterranean, the Americas, Africa, and Oceania.
   - Local JSON caching, exponential backoff retries, polite rate limiting, QC range clipping (excluding -999 fill values), and FAO-56 $ET_0$ calculation.
4. **Offline Synthetic Generator (`data/synthetic.py`)**:
   - Generates physically consistent meteorological variables with FAO-56 target calculation plus ~3% observation noise.
   - Stamped unequivocally with `provenance="synthetic"` and `is_synthetic=True`. Never presented as real data.
5. **Versioned Dataset Storage & Validation (`data/datasets.py`)**:
   - Parquet and CSV export with deterministic SHA-256 content hashing and JSON metadata cards.
   - User CSV schema validation ensuring required columns and physical validity bounds.
6. **Feature Engineering & CLI (`features.py`, `cli.py`)**:
   - Basic 4-feature and extended feature schemas (cyclic $\sin/\cos$ day-of-year encodings, diurnal temperature range, vapour pressure deficit).
   - CLI executable `agriscope-ml build-dataset --source nasa|synthetic` with automated offline fallback warning.

#### Consequences
- **Positive**: Strict adherence to FAO-56 physical standards; zero black-box physics; reproducible datasets with content-hashed auditability; clear provenance labeling preventing synthetic data confusion.
- **Trade-offs**: NASA POWER API queries require live internet connectivity; offline environments automatically and transparently fall back to the synthetic generator.

---

## ADR 007: Machine Learning Model Training, Dual-Split Evaluation, Uncertainty, and Registry Architecture

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope requires automated training, evaluation, uncertainty estimation, explainability, distribution drift detection, and versioned storage for machine learning ET prediction models. The training pipeline must assess generalizability not only on random splits but also across unseen locations and years to prevent optimistic bias from spatial/temporal autocorrelation.

#### Decision
1. **Model Pipelines (`pipelines.py`)**:
   - Implemented standardized scikit-learn pipelines with `StandardScaler` for `RandomForest`, `XGBoost`, `LightGBM`, `SVR`, `MLP`, and a `StackingRegressor` (combining RF, XGBoost, LightGBM, SVR with `RidgeCV` meta-estimator).
   - Configurable hyperparameters with seed determinism.
2. **Dual-Split Evaluation Protocol (`train.py`, `evaluate.py`)**:
   - Evaluated models under both (a) random 80/20 train/test split and (b) grouped split holding out 20% of entire locations/years.
   - Reported comprehensive hydrological and statistical metrics: $R^2$, RMSE, MAE, Mean Bias Error (bias), Nash-Sutcliffe Efficiency (NSE), Kling-Gupta Efficiency (KGE), and 7-point residual distributions (mean, std, median, min, max, p25, p75).
3. **Hyperparameter Tuning (`tuning.py`)**:
   - Integrated Optuna Bayesian optimization with TPE sampling, cross-validated objective minimizing RMSE, timeout and trial caps, and progress callbacks.
4. **Split Conformal Prediction Intervals (`uncertainty.py`)**:
   - Split conformal prediction on calibration holdouts providing finite-sample marginal coverage guarantees at nominal 90% confidence ($\alpha=0.10$).
   - Clipped lower bounds to $0.0$ mm/day to enforce physical non-negativity.
   - Evaluated empirical coverage on test holdouts with tolerance checks ($\ge \text{nominal} - 0.05$).
5. **SHAP Explainability (`explain.py`)**:
   - `TreeExplainer` for tree models (RF, XGBoost, LightGBM) and sampled `KernelExplainer` fallback for kernel/neural/ensemble models.
   - Enforced strict additivity verification: $|\hat{y} - (\text{base\_value} + \sum \phi_j)| < 10^{-4}$.
6. **Distribution Drift Monitoring (`drift.py`)**:
   - Population Stability Index (PSI) using quantile binning ($PSI < 0.10$ stable, $0.10 \le PSI < 0.20$ moderate, $PSI \ge 0.20$ drifted).
   - Two-sample Kolmogorov-Smirnov test ($\alpha=0.05$).
7. **Model Registry & SHA-256 Integrity Verification (`registry.py`, `model_card.py`)**:
   - Persistent filesystem and S3/MinIO artifact bundles (`model.joblib`, `conformal.joblib`, `background.parquet`, `model_card.json`, `checksums.json`).
   - Recomputes SHA-256 hashes upon artifact retrieval, rejecting tampered or corrupt models.
8. **CLI & Makefile Integration**:
   - `agriscope-ml train --algorithm all --schema basic --version v1.0` produces and registers bootstrap models.
   - `make train` added to root Makefile.

#### Consequences
- **Positive**: Guaranteed coverage calibration, explainability out-of-the-box, dual-split reporting highlights real-world generalization, tamper-resistant artifact registry.
- **Trade-offs**: Stacking and kernel explainers require sampled backgrounds (e.g. 50-100 instances) to maintain interactive sub-second SHAP latency.

---

## ADR 008: ML Microservice Architecture, Hot-Swapping, and Resilient Backend Client Integration

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope requires real-time, low-latency evapotranspiration prediction, batch estimation, and additive explainability decoupled from the primary database-backed backend. The inference microservice must support atomic zero-downtime model rollouts and hot-swaps without interrupting in-flight requests, and the backend client must be resilient to ML service outages, preventing cascading thread or connection exhaustion.

#### Decision
1. **Dedicated FastAPI Microservice (`ml/service`)**:
   - Implemented `ModelManager` with startup lifespan warm-loading that pre-compiles Scikit-Learn / numpy caches and initializes SHAP explainers.
   - Endpoints: `POST /infer`, `POST /infer/batch`, `POST /explain`, `GET /models`, `POST /models/load`, and `GET /health`.
   - Enforced physical boundary validation across all meteorological inputs (-10..50°C, 0..100% RH, 0..30 m/s WS, 0..35 MJ/m²/day Rs).
2. **Zero-Downtime Hot-Swapping**:
   - Model bundles and background samples are pre-loaded and pre-warmed prior to acquiring an internal synchronization lock and atomically updating active model pointers.
   - Verified that concurrent inference requests succeed continuously without dropped connections during reload.
3. **Resilient Backend ML Client (`backend/app/services/ml_client.py`)**:
   - Asynchronous client using `httpx.AsyncClient` with strict timeouts (connect=2.0s, read=5.0s).
   - Exponential backoff retries ($0.05 \times 2^k$) on transient connection failures.
   - Three-state `CircuitBreaker` (`CLOSED`, `OPEN`, `HALF_OPEN`): trips to `OPEN` upon 3 consecutive failures; fast-fails subsequent requests without making network calls; transitions to `HALF_OPEN` after 5.0s recovery timeout and heals to `CLOSED` upon 2 successful trials.
4. **Database Registry Sync & Redis Caching (`backend/app/services/model_registry_sync.py`)**:
   - Idempotent synchronization of on-disk artifact bundles into PostgreSQL `ml_models` table; registers bootstrap ensemble model as `ACTIVE`.
   - Caches active model metadata in Redis (`agriscope:active_model_metadata`, TTL 300s); automatically invalidates cache on model promotion.
5. **Latency Validation**:
   - Benchmarked warm single inference at $p_{95} = 36.34\text{ ms}$ (comfortably within the $< 150\text{ ms}$ budget).
   - Batch inference at $0.444\text{ ms/row}$.

#### Consequences
- **Positive**: Sub-50ms inference response times; complete isolation of ML workloads from the main API; cascading failure protection via circuit breaker; seamless hot-reload for model deployments.
- **Trade-offs**: SHAP KernelExplainer for non-tree ensembles operates on sampled background distributions (50-100 rows) to ensure explanation latency remains under 200 ms.

---

## ADR 009: Evapotranspiration Predictions, History Audit, Quotas, and Interactive Visualizations

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope users require interactive tools to calculate daily reference evapotranspiration ($ET_0$), compare model predictions, evaluate local feature contributions (SHAP), experiment with parameter sensitivity in real time without polluting audit history ("what-if" sandbox), and track historical evapotranspiration trends. At the same time, Free and Pro plan entitlements, daily inference quotas (30/day vs 1000/day), and history retrieval caps (last 50 items vs unlimited) must be enforced server-side.

#### Decision
1. **Prediction & Quota Orchestration (`backend/app/services/prediction_service.py`)**:
   - `POST /predict`: Validates input meteorological parameters against fixed envelopes (-10..50°C, 0..100%, 0..30 m/s, 0..35 MJ/m²/d); checks and increments daily quota in Redis (`agriscope:quota:{user_id}:{date}`); executes inference via `MLClient`; calculates concurrent FAO-56 Penman-Monteith physics reference via `agriscope_ml.physics.penman_monteith.calculate_et0`; classifies demand (`low` <2, `moderate` 2–5, `high` >5 mm/day); generates agronomic irrigation interpretation; persists to `predictions` table if `persist=True`.
   - Sandbox Mode: Passing `persist=False` bypasses database write and daily quota consumption, enabling real-time UI sliders ("What-If sandbox") to debounce-call predictions live.
   - Pro Feature Gating: `POST /predict/compare` (side-by-side active-family models + ensemble) and `POST /predict/explain` (additive SHAP attributions) are gated behind `require_plan("model_comparison_enabled")` and `require_plan("explainability_enabled")`.
   - `GET /predict/sample`: Returns realistic agricultural meteorological observations.
2. **History Management & Dashboard Aggregates (`backend/app/services/history_service.py`)**:
   - `GET /history`: Server-side pagination, text search over notes and tags, filtering by date range, classification, and bookmark state. Free tier is capped at the last 50 records.
   - `PATCH /history/{id}`: Toggle bookmark (`is_saved`), edit tags, and add observation notes.
   - `DELETE /history/{id}` and `POST /history/bulk-delete`: Authorized deletion of prediction audit logs.
   - `GET /history/stats`: Returns daily quota status, total inferences, mean/latest ET, classification distribution, and 7-day daily mean trend.
3. **Frontend Visualizations & Interactive Workspaces**:
   - `PredictPage`: Left column parameter form with Zod physical boundary validation, quick sample data loader, and collapsible advanced coordinates. Right column responsive tabs for inference result panel, live debounced What-If sandbox sliders, SHAP attribution bar chart (`ShapBarChart`), and multi-model comparison matrix (`ModelComparisonChart`) with Pro upgrade banners.
   - `HistoryPage`: Paginated audit table with multi-select bulk delete, inline bookmarking, note editing dialog, demand classification filters, and 7-day ET trend line chart (`EtHistoryLineChart`) with FAO-56 colored background zones.
   - `DashboardPage`: Live KPI cards for daily quota, latest $ET_0$, total inferences, and 7-day trend chart.

#### Consequences
- **Positive**: Strict tier separation and quota enforcement; sub-50ms interactive what-if feedback; clear visual distinction between machine-learned estimates and physics benchmarks; zero database bloat from slider experiments.
- **Trade-offs**: Free-tier capping is applied after sorting descending by creation timestamp to ensure users see their most recent 50 predictions.

---

## ADR 010: Location-Based Meteorological Ingestion, Multi-Provider Architecture, and 7-Day ET₀ Forecasting

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
Field managers and agricultural researchers require location-driven evapotranspiration estimates without manually transcribing weather parameters. The platform needs to query historical and forecast weather by geospatial coordinates, convert meteorological measurements into model-ready features, cross-check estimates against physical benchmarks, and degrade gracefully when third-party meteorological APIs (NASA POWER, Open-Meteo) experience transient outages or rate limits.

#### Decision
1. **WeatherProvider Interface & Concrete Providers (`app/providers/weather`)**:
   - `WeatherProvider`: Base abstract contract defining `get_historical`, `get_forecast`, and `get_daily_inputs`.
   - `NasaPowerProvider`: Historical daily agroclimatology provider backed by NASA POWER point API with parameter mapping and QC filtering.
   - `OpenMeteoProvider`: High-resolution forecast, archive, and Open-Meteo Geocoding provider. Performs 10m to 2m wind conversion using the FAO-56 logarithmic profile ($u_2 \approx u_{10} \times 0.75$) and extracts provider-calculated FAO-56 Penman-Monteith $ET_0$ for independent verification.
   - `MockWeatherProvider`: Deterministic, physics-consistent synthetic provider using latitude, longitude, and day-of-year seasonal curves for offline local development and guaranteed fallback.
2. **Weather Domain Service (`app/services/weather_service.py`)**:
   - Multi-tier resolution: Checks Redis cache (TTL 7d for historical, 3h for forecast) -> queries primary provider -> falls back to alternative provider or `MockWeatherProvider`.
   - Explicit degradation flags: Returns `is_fallback: True` and `provider_name` so the UI and audit logs clearly distinguish between real meteorological ingestion and synthetic fallbacks.
   - 7-Day ET₀ Forecasting: Loops over weather forecast days, feeds parameters into `MLClient.predict`, and yields daily predictions alongside 90% conformal intervals and Open-Meteo reference values.
3. **Frontend Map & Forecast Workspaces**:
   - `PointPickerMap`: Leaflet-based map with draggable point marker, click-to-pick coordinates, and live place search via `/weather/geocode`.
   - `LocationModeSelector`: Map and date picker that queries `/weather/prefill` and populates the prediction form with `source=location`.
   - `ForecastChart`: Composed Recharts visualization rendering the ML forecast line, 90% conformal prediction interval area band, and Open-Meteo FAO-56 dashed line.
   - `HistoricalAggregationChart`: Monthly bar chart summarizing historical $ET_0$ seasonal trends.

#### Consequences
- **Positive**: Complete offline testability; seamless degradation when remote weather APIs fail; visual cross-checking builds agronomist trust by comparing ML models directly against provider-calculated FAO-56 values.
- **Trade-offs**: Wind speed from Open-Meteo at 10m is approximated to 2m via standard FAO-56 logarithmic profile assuming neutral atmospheric stability and standard roughness.

---

## ADR 011: Field Boundary Management, Satellite Remote Sensing, and Multi-Temporal Kc/ETc Analytics

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
Precision irrigation management requires spatial field boundaries (parcels), crop stage modeling, multi-spectral vegetation indexing (NDVI, EVI, NDWI) from Earth observation satellites (Copernicus Sentinel-2 L2A), scene cloud screening, and dynamic crop evapotranspiration ($ET_c = K_c \times ET_0$) calculations. The system must enforce plan quotas (Free tier = 1 field; Pro tier = unlimited fields and remote sensing pipeline), operate seamlessly offline with deterministic synthetic curves, and support open STAC APIs with Scene Classification Layer (SCL) cloud masking.

#### Decision
1. **Geospatial & Field Model (`backend/app/models/field.py`, `field_observation.py`, `services/field_service.py`)**:
   - Fields store PostGIS spatial geometry (WGS84 SRID 4326) with automated surface area calculation in hectares via spherical polygon integration.
   - Plan limit enforcement: Free users are restricted to 1 field (`max_fields=1`), raising HTTP 403 Forbidden with upgrade instructions when exceeded.
2. **Satellite Providers & Remote Sensing Pipeline (`app/providers/satellite`, `app/services/remote_sensing_service.py`)**:
   - `SatelliteProvider`: Base abstract contract defining multi-spectral observation retrieval (`SatelliteObservation`) over polygon geometries and date ranges.
   - `StacSentinelProvider`: Open STAC API client (Earth Search / Planetary Computer) querying Sentinel-2 L2A collections. Computes NDVI ($(B08 - B04)/(B08 + B04)$), EVI, and NDWI; performs SCL-based cloud screening (filtering cloud high/medium probability, cirrus, snow/ice, and shadows); and computes parcel-averaged indices.
   - `GeeProvider`: Service-account gated Google Earth Engine client with graceful fallback for MODIS MOD16 evapotranspiration comparison.
   - `MockSatelliteProvider`: Physics-consistent, deterministic seasonal NDVI/EVI/NDWI curves for offline local testing and CI/CD pipelines.
   - `RemoteSensingService`: Ingests satellite scenes, derives crop coefficient $K_c$ (using both FAO-56 stage interpolation and empirical NDVI relation $K_c = 1.25 \times \text{NDVI} + 0.1$), retrieves daily weather $ET_0$, computes crop water demand $ET_c = K_c \times ET_0$, and persists time series records to `field_observations`.
   - Celery Beat Task (`app/workers/tasks/satellite.py`): Weekly background batch job refreshing active fields and generating notifications.
3. **Frontend Workspaces & Visualizations (`pages/fields`, `pages/remote-sensing`, `components/maps`, `components/charts`)**:
   - `FieldPolygonMap`: Interactive Leaflet map with click-to-draw polygon vertices, undo/clear controls, and polygon boundary visualization.
   - `FieldsPage`: Parcel management dashboard with area calculation, crop assignment, creation dialog, deletion actions, and Free plan limit notices.
   - `RemoteSensingPage`: Multi-temporal satellite analysis dashboard featuring KPI cards (latest NDVI, derived $K_c$, daily $ET_c$, cloud mask status), `VegetationIndicesChart` (NDVI, EVI, NDWI curves), `EvapotranspirationComparisonChart` ($ET_0$ vs $ET_c$ vs rainfall), field boundary viewer, and scene observation audit table.

#### Consequences
- **Positive**: Complete offline-first execution with automated fallback to deterministic mock satellite data; accurate polygon surface area calculation without heavy external GIS binaries; deep integration with FAO-56 crop coefficients and machine learning $ET_0$ pipelines.
- **Trade-offs**: Large cloud-covered scenes are excluded based on the configurable `max_cloud_cover` threshold; optical satellite revisit times range from 5–10 days, requiring linear interpolation of $K_c$ between cloud-free acquisitions.

---

## ADR 012: FAO-56 Daily Soil Water Balance, Root-Zone Depletion, and Irrigation Scheduling

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
Precision agricultural management requires daily accounting of soil water dynamics to prevent crop water stress while avoiding over-irrigation. The platform must compute daily root-zone depletion ($D_r$), incorporate dynamic root depth ($Z_r$), account for USDA-SCS effective precipitation ($P_{\text{eff}}$), enforce soil texture presets (TAW, RAW, FC, WP), generate 7-to-14 day forecast schedules, and provide irrigation event logging with real-time balance re-calculation.

#### Decision
1. **Soil Water Balance Engine (`backend/app/services/irrigation_service.py`, `core/soil.py`)**:
   - Implemented standard FAO-56 Table 19 soil texture presets (`sand`, `loamy_sand`, `sandy_loam`, `loam`, `silt_loam`, `clay_loam`, `clay`) with physical Field Capacity ($\theta_{\text{FC}}$), Wilting Point ($\theta_{\text{WP}}$), and Total Available Water ($\text{TAW} = 1000 \times (\theta_{\text{FC}} - \theta_{\text{WP}})$ mm/m).
   - Dynamic root depth $Z_r(t)$: Grows from $Z_{r,\min}$ (0.3m) to $Z_{r,\max}$ (1.2m) scaled by days after planting relative to total growing season days.
   - Readily Available Water: $\text{RAW} = p \times \text{TAW} \times Z_r$, where $p$ is the Management Allowed Depletion (MAD, default 0.50).
   - Daily soil water balance: $D_{r,i} = D_{r,i-1} + ET_{c,i} - P_{\text{eff},i} - I_i$, clamped to $0 \le D_r \le \text{TAW}$.
   - USDA SCS effective rainfall calculation: $P_{\text{eff}} = 0$ for $P \le 8.3\text{ mm}$, $0.8 P - 5.0$ for $P \le 75\text{ mm}$, and $0.6 P + 10.0$ for $P > 75\text{ mm}$.
2. **Irrigation APIs & Event Logging (`backend/app/routers/v1/crops.py`, `irrigation.py`)**:
   - `GET /crops`: FAO-56 crop library with growth stages and coefficient values.
   - `GET /irrigation/plan/{field_id}`: Full seasonal water balance, 7-day schedule with recommended application depth (mm), volume ($m^3/\text{ha}$ and total $m^3$), and status indicators.
   - `POST /irrigation/events/{field_id}`: Logs applied irrigation events and dynamically updates root-zone depletion.
   - `DELETE /irrigation/events/{field_id}/{event_id}`: Removes applied events and triggers re-balancing.
3. **Frontend Irrigation Dashboard (`pages/irrigation`, `components/charts/SoilWaterDepletionChart.tsx`)**:
   - Soil texture and MAD slider controls.
   - Season summary KPI cards (Moisture status, Net Irrigation Requirement, total applied water, effective rainfall).
   - Interactive Recharts `SoilWaterDepletionChart` displaying root-zone depletion $D_r$ against red dashed RAW stress thresholds and TAW limits.
   - Forecast-aware 7-day schedule table with volumetric recommendations and event logging dialog.

#### Consequences
- **Positive**: Direct agronomic guidance actionable by farm operators; full offline deterministic evaluation; immediate moisture recovery feedback upon logging irrigation events.
- **Trade-offs**: Capillary rise and runoff are simplified under standard FAO-56 daily water balance assumptions with effective rainfall filtering.

---

## ADR 013: Asynchronous Batch Processing, Document Delivery & Real-Time SSE Notifications

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope requires high-throughput batch prediction processing for large meteorological datasets (up to 10,000 CSV rows), server-side generation of branded PDF and Excel (XLSX) reports, defense against CSV formula injection attacks (CWE-1236), object storage in MinIO with expiring presigned download URLs, and real-time user notifications delivered via Server-Sent Events (SSE) and in-app dropdowns.

#### Decision
1. **Asynchronous Batch Execution Pipeline (`backend/app/workers/tasks/batch.py`, `routers/v1/batch.py`)**:
   - Implemented `process_batch_prediction_job_task` Celery worker task parsing CSV inputs up to 10,000 rows.
   - Computes model inferences, conformal 90% uncertainty bounds, and FAO-56 reference values per row with per-row error capture.
   - Uploads annotated result CSV files to MinIO / storage provider and updates database records with progress metrics.
   - Enforces idempotent job creation via `Idempotency-Key` headers.
2. **Document & Export Services (`backend/app/services/export_service.py`, `report_service.py`, `routers/v1/reports.py`)**:
   - **Formula Injection Defense**: Applied strict sanitization (`sanitize_csv_cell`) prefixing formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with single quotes (`'`) to neutralize Excel DDE/formula execution.
   - **Multi-Format Exports**: Implemented CSV, XLSX (`openpyxl` with styled headers and column widths), PNG (`matplotlib` chart renders), and branded PDF reports (`reportlab` with metadata tables, metrics summaries, and embedded Matplotlib visual snapshots).
   - Generated artifacts are stored in MinIO storage with expiring signed download tokens (1 hour TTL).
3. **Real-Time Notification Infrastructure (`backend/app/services/notification_service.py`, `routers/v1/notifications.py`)**:
   - Implemented `SSEConnectionManager` using `asyncio.Queue` per client connection for event broadcasting over `GET /notifications/stream`.
   - In-app notification center persistence in `notifications` table with user preferences (`notification_preferences`).
4. **Frontend Integration (`pages/batch`, `pages/reports`, `components/ui/NotificationCenter.tsx`)**:
   - `BatchPage`: CSV dataset uploader, template downloader, polling progress indicator, per-row validation error viewer, and result file downloader.
   - `ReportsPage`: Export generation modal (PDF, XLSX, CSV, PNG) and document inventory list.
   - `NotificationCenter`: Bell dropdown in topbar with live unread counter badge, real-time SSE listener, and mark-as-read controls.

#### Consequences
- **Positive**: High-throughput non-blocking inference for enterprise users; CWE-1236 immune CSV exports; instant real-time UI feedback via SSE without polling overhead.
- **Trade-offs**: Requires persistent worker threads and background storage connectivity; MinIO signed URLs expire after 1 hour requiring re-query for active links.

---

## ADR 014: Researcher API Keys, Rate Limiting, and Subscription Billing Engine

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
AgriScope requires programmatic access for research institutions and agronomists, complete with granular scopes, SHA-256 hashed secret keys, per-key rate limits (returning standard `429 Too Many Requests` and `Retry-After` headers), and usage telemetry. Additionally, access to these capabilities is gated behind subscription tiers managed through a provider-abstracted billing engine supporting Stripe (test checkout, customer portal, webhook signature verification, and idempotent event processing) and a deterministic Mock provider for local development.

#### Decision
1. **API Key Lifecycle & Security (`backend/app/models/api_key.py`, `app/services/api_key_service.py`, `app/core/api_key_auth.py`)**:
   - Plaintext keys (`agri_live_<hex>`) are displayed strictly once upon creation.
   - Keys are hashed at rest via SHA-256 (`key_hash`). The first 14 characters (`agri_live_xxxx`) are preserved as a public prefix for auditing and identification.
   - Fine-grained scopes (`predict:read`, `batch:write`, `weather:read`, `fields:read`) enforced via `require_api_key_scope` dependency.
   - Integrated with user authentication via `get_api_key_or_user` dependency, allowing unified endpoints.
2. **Rate Limiting & Telemetry (`backend/app/core/rate_limit.py`, `app/core/exceptions.py`)**:
   - Slotted sliding-window rate limiting backed by Redis with in-memory class-level dictionary fallback.
   - Raises `RateLimitExceededException` (HTTP 429) injecting `Retry-After: 60` response headers.
   - Per-key daily quota enforcement with `Retry-After: 86400` headers.
   - Real-time usage tracking recording endpoint hits and HTTP status codes.
3. **Public Researcher Surface (`backend/app/routers/v1/public.py`, `app/schemas/public.py`)**:
   - Exposed stable endpoints under `/api/v1/public/*`: `predict`, `batch/submit`, `batch/status/{job_id}`, `weather/prefill`, and `fields/{field_id}/et-series`.
   - Single prediction gracefully falls back to FAO-56 Penman-Monteith physics calculation when the ML microservice is unreachable in local or test environments.
4. **Billing Provider Abstraction & State Machine (`backend/app/providers/billing/`, `app/services/subscription_service.py`, `app/routers/v1/billing.py`)**:
   - Abstract `BillingProvider` interface with `StripeProvider` and `MockBillingProvider` implementations.
   - Stripe webhook verification with signature validation and duplicate event deduplication (`event_id` tracking).
   - Subscription lifecycle state machine (`free` → `pro` → `past_due` → `canceled`) that updates `User.plan` and entitlements immediately, records audit trail entries, and broadcasts SSE updates to active frontend clients.
5. **Frontend Management Interfaces (`frontend/src/pages/settings/ApiKeysTab.tsx`, `BillingTab.tsx`, `SettingsPage.tsx`)**:
   - `ApiKeysTab`: Key generation modal, copy-once secret modal, scope checkboxes, revocation with confirmation, and usage statistics modal.
   - `BillingTab`: Subscription status overview, plan feature matrix (Free vs Pro Researcher), Stripe checkout/portal redirection, and mock upgrade/downgrade controls.

#### Consequences
- **Positive**: Full separation of concerns for third-party billing engines; secure API key issuance immune to plaintext database exposure; instant entitlement synchronization on subscription change.
- **Trade-offs**: Mock provider is active by default in development until `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` environment variables are supplied.

---

## ADR 015: Administrative Governance, ML Dataset Ingestion, and System Control

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
Platform administrators require complete operational control over user accounts, training datasets, runtime feature toggles, system-wide maintenance banners, global resource limits, and audit histories. All administrative mutations must strictly enforce RBAC (`role="admin"`), log immutable audit events, and validate training data against physical meteorological boundaries and statistical outlier envelopes.

#### Decision
1. **Administrative Access Control & Security (`backend/app/routers/v1/admin/`, `app/core/deps.py`)**:
   - Every administrative endpoint under `/api/v1/admin/*` enforces `require_role(["admin"])`, responding with HTTP 403 Forbidden to non-admin callers.
   - All mutations (role/plan adjustment, status updates, lockout release, force logout, dataset upload/deletion, flag toggles, banner publishes) write immutable audit records via `AuditService.log_event`.
2. **User Administration Lifecycle (`backend/app/routers/v1/admin/users.py`, `app/services/admin_service.py`)**:
   - Supports search by name/email, filtering by role, plan, and status, and server-side pagination.
   - Immediate privilege modification (role/plan), account suspension/activation, manual failed attempt reset/unlock, and session revocation.
   - User-specific audit trail inspection matching both user ID and email.
3. **ML Dataset Validation Engine (`backend/app/routers/v1/admin/datasets.py`, `app/services/dataset_service.py`)**:
   - Multipart CSV upload with schema checking (`temp_max`, `temp_min`, `humidity`, `wind_speed`).
   - Statistical distribution calculation (mean, std, IQR outlier fences: $Q_1 - 1.5 \times \text{IQR}$, $Q_3 + 1.5 \times \text{IQR}$) and physical boundary validation.
   - Classifies dataset status as `validated` or `rejected`, generates 10-row preview, uploads raw artifact to MinIO storage, and enables direct raw CSV download.
4. **System Governance, Banners & Metrics (`backend/app/routers/v1/admin/system.py`, `admin/metrics.py`, `notifications.py`)**:
   - Feature flags CRUD for dynamic runtime capability gating.
   - Announcements / maintenance banner publishing with app-wide visibility rendered in `DashboardLayout.tsx`.
   - Global quotas and limits adjustment (daily predictions, batch size, rate limits).
   - Real-time operational metrics reporting active users, prediction volume, active ML engine, queue depth, and latencies.
5. **Frontend Administration Console (`frontend/src/pages/admin/`)**:
   - `AdminOverviewPage`: Stat cards (users, predictions, model, storage) and Recharts 7-day throughput/latency area chart.
   - `AdminUsersPage`: User table with inline role/plan selectors, lockout status badges, force logout, audit modal, and double-confirm dialogs for destructive actions.
   - `AdminDatasetsPage`: Inventory table, CSV upload modal with statistical validation report, and raw download.
   - `AdminSystemPage`: Tabbed governance interface for feature flags, announcements, limits, and system audit logs.
   - App-wide `AnnouncementBanner` banner component visible to all authenticated users.

#### Consequences
- **Positive**: Complete administrative autonomy without direct database access; strict audit accountability for compliance; validation and outlier filtering of training datasets before model ingestion.
- **Trade-offs**: Admin role promotion is strictly guarded; initial bootstrap admin is seeded via database initialization.

---


## ADR 016: ML Model Lifecycle, Approval Gates, Shadow Traffic, and Automated Drift Monitoring

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
The AgriScope platform requires a governed, auditable ML model lifecycle beyond simple registry storage. Administrators need to train new models from validated datasets, evaluate them against quality gates, run shadow traffic tests alongside the active production model, approve zero-downtime hot swaps, rollback to previous versions, and continuously monitor for feature distribution drift.

#### Decision
1. **Status State Machine**: `training → pending_approval → active → archived | rejected`. Only one model may hold `active` status at a time; approval atomically archives the previous active model.
2. **Quality Approval Gates (`model_service.py`)**: R² ≥ 0.70 and RMSE ≤ 1.50 enforced before approval. `force=True` flag bypasses with mandatory audit log entry. Rejection requires a written reason.
3. **Zero-Downtime Hot Swap**: `ModelService.approve_model` calls `MLClient.load_model(name, version)` on the ML microservice, then atomically promotes the candidate and invalidates the Redis active model cache (`agriscope:active_model_metadata`).
4. **Shadow Mode**: Pending models with `metrics_json.shadow_mode=True` receive silent shadow evaluations on every live prediction via `record_shadow_evaluation` in `prediction_service.py`. Results stored in `shadow_results` table.
5. **Champion/Challenger Report**: `ModelDriftService.get_shadow_report` computes bias, RMSE, and MAE deltas between shadow candidates and the active model using live `ShadowResult` records.
6. **Distribution Drift Detection**: Scheduled weekly Celery beat task (`run_drift_check_task`, 604800s) computes PSI + KS statistics on live prediction features vs reference distributions using `agriscope_ml.drift.detect_dataset_drift`. Notifies admins on significant drift (PSI ≥ 0.20).
7. **Training Pipeline**: Celery task `train_models_task` (queue=training) downloads dataset from MinIO, calls `agriscope_ml.train.train_single_model`, optionally runs Optuna tuning, performs cross-validation, and creates `MLModel` records with `status=pending_approval`. Supports algorithms: RF, XGBoost, LightGBM, SVR, MLP, ensemble.
8. **Rollback**: `rollback_model` promotes the most-recently-archived model back to active and archives the current active model.

#### Consequences
- **Positive**: Full auditability of all model promotions; zero-downtime deployments; automated quality enforcement; real-world shadow validation before live traffic; continuous drift alerting.
- **Trade-offs**: Only one active model at a time limits A/B testing to shadow mode; PSI/KS drift detection requires at least 10 live predictions for meaningful comparison.

---

## ADR 017: Platform Hardening, Accessibility, PWA, Security Headers, and Observability

- **Status**: Accepted
- **Date**: 2026-10-07
- **Deciders**: Principal Full-Stack & ML Engineer

#### Context
With all functional domains implemented (Tasks 1–16), AgriScope requires comprehensive platform hardening, internationalization, accessibility compliance, offline capabilities, security controls, query optimization, and production-grade observability.

#### Decision
1. **i18n & RTL Layout**: Complete English and Urdu translation catalogs with 13 functional namespaces (`common`, `nav`, `auth`, `settings`, `dashboard`, `predict`, `history`, `fields`, `irrigation`, `batch`, `notifications`, `admin`, `errors`). Added `LanguageSwitcher` persisting to `localStorage.agriscope_locale`, dynamically switching `document.documentElement.dir` (`rtl` for Urdu) and `lang`. RTL logical styling integrated via CSS variables and directional utilities in `styles/index.css`.
2. **Accessibility (WCAG 2.1 AA)**: Skip-to-main content links on layouts; reduced-motion CSS media query overrides (`prefers-reduced-motion: reduce`); accessible loading states via `Skeleton`, `SkeletonCard`, and `SkeletonTable`; standard `EmptyState` and `ErrorState` components with ARIA landmarks. Automated `axe-core` accessibility audits running across auth and core dashboard views in CI.
3. **Progressive Web App (PWA)**: Configured `vite-plugin-pwa` with Workbox offline caching. Static assets cached with `CacheFirst`, OpenStreetMap tiles cached under `map-tiles-v1`, and API/auth endpoints strictly excluded with `NetworkOnly`. Offline fallback served via `public/offline.html`.
4. **Performance & Query Optimization**: Composite indexes added on hot paths: `(user_id, timestamp)`, `(user_id, is_saved)`, and `(user_id, classification)` on `predictions`. Bundler code-splitting configured with dedicated vendor chunks (`vendor`, `charts`, `maps`, `i18n`) under a 600KB budget. Provided `infra/scripts/seed_predictions.py` for 1M-row batch seeding.
5. **Security Hardening**: Hardened Nginx reverse proxy with global security headers (`CSP`, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`). Internal metric/health endpoint access restrictions configured. Backend `SecurityHeadersMiddleware` strips `server` info and enforces strict browser policies. CI scanning updated with `bandit`, `pip-audit`, and `npm audit`. Mapped threat model and controls against OWASP ASVS in `docs/security.md`.
6. **Observability**: Prometheus alerting rules (`alert_rules.yml`) configured for high error rates (>5%), p95 latency degradations (>2s), and ML service latency degradation (>500ms). Expanded Grafana dashboard (`overview.json`) providing latency percentiles (p50/p95/p99), error rate %, and live service health.

#### Consequences
- **Positive**: Full bilingual support with seamless Urdu RTL ergonomics; WCAG 2.1 AA compliance verified by automated audits; offline resilience; enterprise-grade security posture and production telemetry.
- **Trade-offs**: Color-contrast checks in JSDOM are disabled during automated axe runs due to lack of layout computation; manual contrast validation applies to custom themes.
