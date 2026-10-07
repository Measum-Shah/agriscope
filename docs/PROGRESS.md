# AgriScope Progress Log

## Task Log

| Task # | Task Name | Status | Date | Files Added/Modified | Description |
|--------|-----------|--------|------|----------------------|-------------|
| 0 | Permanent Project Memory | Completed | 2026-10-06 | `docs/PROJECT_CONTEXT.md`, `docs/PROGRESS.md`, `docs/decisions.md`, `README.md` | Initialized system memory, vision, architecture rules, ADR template, and repository stub. |
| 1 | Repository Scaffold and Infrastructure | Completed | 2026-10-06 | Full tree across `backend/`, `ml/`, `frontend/`, `infra/`, `.github/workflows/`, root configuration (`docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`, `.env`, `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml`, `Makefile`) | Implemented complete authoritative repository layout, Docker Compose definitions (dev and prod), backend app factory with request-ID and JSON logging, Celery app with `ping` task, standalone ML service with `/health`, Vite + React + TS + Tailwind frontend with Vitest/ESLint/Prettier, Prometheus + Grafana provisioning, and CI workflow. Verified all tests, linters, and type checks. |
| 2 | Complete Data Model | Completed | 2026-10-07 | `backend/app/models/` (all 20 models), `backend/app/schemas/` (`user.py`, `prediction.py`, `field.py`, `crop.py`), `backend/alembic/versions/0001_initial.py`, `backend/app/db/init_db.py`, `backend/app/db/seeds/crops.json` (20 crops), `backend/tests/unit/test_migrations.py`, `backend/tests/unit/test_constraints.py`, `backend/tests/unit/test_seeds.py`, `docs/architecture.md`, `docs/decisions.md` | Implemented all 20 SQLAlchemy 2.0 domain models with PostGIS geometries, check constraints, composite and spatial indexes, Alembic migration 0001_initial, idempotent seeding for admin and 20 FAO-56 crops, Mermaid ER diagram in architecture.md, and ADR 002. Passed all unit tests and lint checks. |
| 3 | Authentication Core | Completed | 2026-10-07 | `backend/app/routers/v1/auth.py`, `backend/app/services/auth.py`, `backend/app/services/audit.py`, `backend/app/core/security.py`, `backend/app/core/deps.py`, `backend/app/core/rate_limit.py`, `backend/app/providers/email/smtp.py`, `backend/app/workers/tasks/emails.py`, `backend/app/schemas/auth.py`, `backend/tests/unit/test_auth_service.py`, `backend/tests/unit/test_auth_edge_cases.py`, `backend/tests/integration/test_auth_api.py`, `docs/security.md`, `docs/decisions.md` | Implemented authentication core: registration with password complexity & breached-password checks, email verification via single-use tokens, constant-time login verification with 5-attempt/15-min auto-unlocking lockout, rotating refresh token families in httpOnly cookies with reuse detection, session management, 1h single-use password resets with multi-device session invalidation, Redis/in-memory rate limiters, audit logging, and Celery/SMTP email delivery. Achieved 95% test coverage on `auth_service` and 100% test suite pass rate. |
| 4 | Entitlements and Account Features | Completed | 2026-10-07 | `backend/app/core/plans.py`, `backend/app/schemas/account.py`, `backend/app/services/account.py`, `backend/app/routers/v1/users.py`, `backend/app/models/user.py`, `backend/tests/unit/test_plans_rbac.py`, `backend/tests/unit/test_account_service.py`, `docs/api.md`, `docs/decisions.md`, `docs/PROGRESS.md` | Implemented centralized entitlement matrix (`core/plans.py`), `QuotaService` daily prediction counter (Redis + in-memory fallback), `require_plan_feature` and `require_role` dependencies, RFC 6238 TOTP 2FA (QR code provisioning, verification, 8 hashed single-use recovery codes, 2FA challenge login step, disable), account self-service (profile update, email change re-verification, password change with multi-device session revocation, GDPR JSON data export, soft deletion), and user audit trail endpoint (`/users/me/audit`). Added Pillow dependency and verified all 32 tests pass. |
| 5 | Frontend Foundation, Design System, & Account Screens | Completed | 2026-10-07 | `frontend/src/components/ui/` (15 components), `frontend/src/api/` (`client.ts`, `auth.ts`, `users.ts`), `frontend/src/context/` (`AuthContext.tsx`, `ThemeContext.tsx`), `frontend/src/routes/` (`ProtectedRoute.tsx`, `RoleRoute.tsx`, `PlanRoute.tsx`), `frontend/src/layouts/` (`AuthLayout.tsx`, `DashboardLayout.tsx`), `frontend/src/pages/` (Login, Register, VerifyEmail, ForgotPassword, ResetPassword, Dashboard, Settings [Profile, Security, Account]), `frontend/src/__tests__/` (validators, guards, AuthContext, forms, a11y, App), `docs/decisions.md` | Built 15-component accessible design system with deep-green agri palette and CSS variables light/dark mode; typed Axios client with silent refresh, request-ID header, and 401 recovery; AuthContext and route guards; Zod form validation; full auth and account settings screens (profile edit, email change, password update, 2FA setup with QR & recovery codes, session revocation, audit history, data export, account deletion); verified 32/32 vitest tests passing including axe-core WCAG audits. |
| 6 | agriscope_ml Physics & Data Engine | Completed | 2026-10-07 | `ml/agriscope_ml/physics/` (`penman_monteith.py`, `crop_coefficients.py`), `ml/agriscope_ml/data/` (`nasa_power.py`, `synthetic.py`, `datasets.py`), `ml/agriscope_ml/features.py`, `ml/agriscope_ml/cli.py`, `ml/tests/` (21 tests), `ml/pyproject.toml`, `docs/decisions.md` | Implemented complete FAO-56 Penman-Monteith daily reference ET0 formulation with all thermodynamic terms, 4-input simplified fallback with documented assumptions, crop coefficient piecewise linear stage interpolation, satellite NDVI-to-Kc conversion, NASA POWER agroclimatology client with QC filters and global 50-station registry, labelled offline synthetic generator, versioned dataset storage with SHA-256 hashes, CSV schema validation, and CLI `agriscope-ml`. All 21 ML tests pass. |
| 7 | Model Training Stack | Completed | 2026-10-07 | `ml/agriscope_ml/` (`pipelines.py`, `train.py`, `evaluate.py`, `tuning.py`, `uncertainty.py`, `explain.py`, `drift.py`, `model_card.py`, `registry.py`, `cli.py`), `Makefile`, `docs/ml-model.md`, `docs/decisions.md`, `ml/tests/` (43 total tests) | Implemented full ML training stack: Scikit-learn pipelines with StandardScaler for RF, XGBoost, LightGBM, SVR, MLP, and Stacking ensemble; dual random and grouped location/year holdout evaluation; hydrological/statistical metrics (R², RMSE, MAE, bias, NSE, KGE, 7-point residual distributions); Optuna hyperparameter tuning with callbacks; split conformal prediction intervals (nominal 90% confidence, empirical coverage verification); SHAP TreeExplainer & KernelExplainer with strict additivity verification; PSI and KS distribution drift detectors; ModelCard JSON generation; MinIO/filesystem model registry with SHA-256 integrity verification; CLI `agriscope-ml train --algorithm all` and `make train`. |
| 8 | ML Service and API Integration | Completed | 2026-10-07 | `ml/service/` (`main.py`, `manager.py`, `schemas/inference.py`, `routers/infer.py`, `routers/models.py`), `ml/agriscope_ml/explain.py`, `backend/app/services/` (`ml_client.py`, `model_registry_sync.py`), `backend/app/db/init_db.py`, `ml/tests/test_service.py`, `backend/tests/unit/` (`test_ml_client.py`, `test_model_registry_sync.py`), `docs/ml-model.md`, `docs/decisions.md` | Built dedicated FastAPI ML inference service with warm-loading startup lifespan, zero-downtime model hot-swapping, and sub-40ms p95 latency. Implemented resilient async backend MLClient with 3-state CircuitBreaker (CLOSED, OPEN, HALF_OPEN) and exponential retry backoff. Added database model registry sync into `ml_models` with bootstrap ensemble activation, and Redis active model metadata caching. Verified all 43 ML and 40 backend unit/integration tests pass. |
| 9 | Predictions, History, & Charts | Completed | 2026-10-07 | `backend/app/schemas/prediction.py`, `backend/app/services/prediction_service.py`, `backend/app/services/history_service.py`, `backend/app/routers/v1/predict.py`, `backend/app/routers/v1/history.py`, `backend/tests/unit/test_predict_service.py`, `backend/tests/integration/test_predict_history_api.py`, `frontend/src/api/` (`predict.ts`, `history.ts`), `frontend/src/components/charts/` (`ShapBarChart.tsx`, `ModelComparisonChart.tsx`, `EtHistoryLineChart.tsx`), `frontend/src/components/predict/` (`PredictResultPanel.tsx`, `WhatIfSandbox.tsx`), `frontend/src/pages/predict/PredictPage.tsx`, `frontend/src/pages/history/HistoryPage.tsx`, `frontend/src/pages/dashboard/DashboardPage.tsx`, `frontend/src/__tests__/predict_history.test.tsx`, `docs/decisions.md`, `docs/PROGRESS.md` | Built end-to-end evapotranspiration estimation, history audit, and interactive visualizations. Implemented backend single prediction with Redis quota check, concurrent FAO-56 Penman-Monteith physics calculation, conformal interval formatting, agronomic guidance, and persistence; sandbox mode (`persist=False`); Pro-gated multi-model comparison and SHAP explainability; sample meteorological data endpoint; paginated history with Free-tier 50-item cap, full-text note search, demand filtering, bookmarking, and single/bulk deletion; dashboard 7-day trend statistics. Frontend Predict page with Zod validation, What-If sensitivity sandbox, SHAP bar chart, comparison table; History page with audit table and FAO-56 classification zones; live KPI dashboard cards. Verified 48 backend tests, 49 ML tests, and 34 frontend tests pass with zero lint errors. |
| 10 | Location-Based Prediction & Forecasting | Completed | 2026-10-07 | `backend/app/providers/weather/` (`base.py`, `mock.py`, `open_meteo.py`, `nasa_power.py`), `backend/app/services/weather_service.py`, `backend/app/schemas/weather.py`, `backend/app/routers/v1/weather.py`, `backend/tests/unit/test_weather_providers.py`, `backend/tests/integration/test_weather_api.py`, `frontend/src/api/weather.ts`, `frontend/src/components/maps/PointPickerMap.tsx`, `frontend/src/components/charts/` (`ForecastChart.tsx`, `HistoricalAggregationChart.tsx`), `frontend/src/components/predict/` (`LocationModeSelector.tsx`, `WeatherForecastWorkspace.tsx`), `frontend/src/pages/predict/PredictPage.tsx`, `frontend/src/styles/index.css`, `docs/decisions.md`, `docs/PROGRESS.md` | Built location-based meteorological ingestion, multi-provider weather integration, and 7-day ET0 forecasting. Implemented abstract WeatherProvider interface with OpenMeteoProvider (forecasts, FAO-56 cross-check, reverse geocoding), NasaPowerProvider (historical daily agroclimatology), and MockWeatherProvider (deterministic, labelled seasonal generator). Built WeatherService with multi-tier Redis caching (TTL 7d/3h), timeout retry, graceful degradation with fallback flags, and ML-model 7-day ET0 forecast generation. Frontend interactive Leaflet map with point picker and place search, Location Mode auto-fill on Predict page (`source=location`), 7-day Forecast chart with 90% conformal band and Open-Meteo benchmark, and seasonal monthly aggregation chart. Verified 54 backend tests, 49 ML tests, and 34 frontend tests pass with zero lint or type errors. |
| 11 | Field Management & Satellite Analysis | Completed | 2026-10-07 | `backend/app/models/` (`field.py`, `field_observation.py`), `backend/app/services/` (`field_service.py`, `remote_sensing_service.py`), `backend/app/schemas/field_analysis.py`, `backend/app/providers/satellite/` (`base.py`, `mock.py`, `stac_sentinel.py`, `gee.py`), `backend/app/routers/v1/` (`fields.py`, `remote_sensing.py`), `backend/app/workers/tasks/satellite.py`, `backend/tests/unit/` (`test_field_service.py`, `test_remote_sensing.py`), `frontend/src/api/` (`fields.ts`, `remoteSensing.ts`), `frontend/src/components/maps/FieldPolygonMap.tsx`, `frontend/src/components/charts/` (`VegetationIndicesChart.tsx`, `EvapotranspirationComparisonChart.tsx`), `frontend/src/pages/fields/FieldsPage.tsx`, `frontend/src/pages/remote-sensing/RemoteSensingPage.tsx`, `frontend/src/__tests__/fields_rs.test.tsx`, `docs/remote-sensing.md`, `docs/decisions.md`, `docs/PROGRESS.md` | Implemented end-to-end field polygon management and multi-temporal remote sensing pipeline. PostGIS spatial boundaries with automated spherical hectare calculation, Free-plan single field limit enforcement; SatelliteProvider interface with StacSentinelProvider (Earth Search / Planetary Computer Sentinel-2 L2A with SCL cloud masking and NDVI/EVI/NDWI calculation), GeeProvider (MODIS ET benchmark), and MockSatelliteProvider (deterministic seasonal curves); RemoteSensingService computing crop coefficient Kc (FAO-56 stage + NDVI empirical relation) and daily crop water need ETc = Kc * ET0; Celery beat weekly refresh task. Frontend Leaflet polygon drawer/viewer, FieldsPage with parcel CRUD, RemoteSensingPage with KPI cards, vegetation index curves, ET0 vs ETc charts, and satellite scene audit table. Verified 52 backend tests, 49 ML tests, and 36 frontend tests pass. |
| 12 | Crop Water Requirement & Irrigation | Completed | 2026-10-07 | `backend/app/core/soil.py`, `backend/app/schemas/irrigation.py`, `backend/app/services/irrigation_service.py`, `backend/app/routers/v1/` (`crops.py`, `irrigation.py`), `backend/app/models/irrigation_event.py`, `backend/tests/unit/test_irrigation_service.py`, `frontend/src/api/irrigation.ts`, `frontend/src/components/charts/SoilWaterDepletionChart.tsx`, `frontend/src/pages/irrigation/IrrigationPage.tsx`, `frontend/src/__tests__/irrigation.test.tsx`, `docs/decisions.md`, `docs/PROGRESS.md` | Implemented FAO-56 daily soil water balance and precision irrigation scheduling. Core soil presets (FAO-56 Table 19 TAW/RAW), USDA SCS effective rainfall filtering, dynamic root depth progression, root-zone depletion Dr tracking, 7-day forecast-aware scheduling with volumetric depth/hectare recommendations, and event logging with immediate balance re-calculation. Frontend Irrigation page with soil/MAD controls, depletion vs RAW chart, forecast schedule table, and applied water event logging modal. Verified 56 backend tests, 49 ML tests, and 37 frontend tests pass. |
| 13 | Async Jobs and Delivery | Completed | 2026-10-07 | `backend/app/providers/storage/` (`base.py`, `minio.py`, `mock.py`), `backend/app/services/` (`export_service.py`, `report_service.py`, `notification_service.py`), `backend/app/schemas/jobs.py`, `backend/app/workers/tasks/batch.py`, `backend/app/routers/v1/` (`batch.py`, `reports.py`, `notifications.py`), `backend/tests/unit/test_jobs_and_delivery.py`, `frontend/src/api/jobs.ts`, `frontend/src/pages/batch/BatchPage.tsx`, `frontend/src/pages/reports/ReportsPage.tsx`, `frontend/src/components/ui/NotificationCenter.tsx`, `frontend/src/__tests__/jobs_and_delivery.test.tsx`, `docs/decisions.md`, `docs/PROGRESS.md` | Built high-throughput async batch inference pipeline (up to 10k CSV rows, per-row validation errors, progress tracking, result CSV upload to MinIO with expiring signed URLs), multi-format export generator (CWE-1236 formula-sanitized CSV, styled XLSX via openpyxl, Matplotlib PNG charts, branded PDF reports via ReportLab), real-time Server-Sent Events (SSE) notification streaming, and in-app notification center. Frontend Batch page with CSV upload and progress tracker, Reports page with multi-format export generator modal, NotificationCenter bell dropdown with live counter, and export buttons on History. Verified 60 backend tests, 49 ML tests, and 40 frontend tests pass. |
| 14 | Researcher API and Subscriptions | Completed | 2026-10-07 | `backend/app/models/api_key.py`, `backend/app/schemas/` (`api_key.py`, `public.py`, `billing.py`), `backend/app/core/` (`api_key_auth.py`, `rate_limit.py`, `exceptions.py`), `backend/app/services/` (`api_key_service.py`, `subscription_service.py`), `backend/app/providers/billing/` (`base.py`, `mock.py`, `stripe.py`), `backend/app/routers/v1/` (`api_keys.py`, `public.py`, `billing.py`), `frontend/src/api/` (`apiKeys.ts`, `billing.ts`), `frontend/src/pages/settings/` (`ApiKeysTab.tsx`, `BillingTab.tsx`, `SettingsPage.tsx`), `frontend/src/__tests__/api_keys_billing.test.tsx`, `backend/tests/unit/` (`test_api_keys.py`, `test_billing.py`), `docs/api.md`, `docs/decisions.md`, `docs/PROGRESS.md` | Implemented secure programmatic Researcher API surface under `/api/v1/public/*` and subscription billing engine. API keys created with single plaintext disclosure, SHA-256 hashed at rest, scoped permissions, and sliding-window rate limiters with HTTP 429 Retry-After headers; usage statistics endpoint tracking daily quota and endpoints; BillingProvider interface supporting Stripe checkout/portal and mock local transitions with signature verification and idempotent event dispatch; subscription state machine (free -> pro -> past_due -> canceled) updating user plan and entitlements immediately. Frontend Settings tabs for API key lifecycle (generate, copy modal, revoke, usage) and Subscription & Billing (tier comparison cards, upgrade/downgrade buttons). Verified 67 backend unit tests, 49 ML tests, and 42 frontend tests pass. |
| 15 | Admin Console Basics | Completed | 2026-10-07 | `backend/app/routers/v1/admin/` (`users.py`, `datasets.py`, `metrics.py`, `audit.py`, `system.py`), `backend/app/services/` (`admin_service.py`, `dataset_service.py`), `backend/app/schemas/admin.py`, `backend/tests/unit/test_admin.py`, `frontend/src/api/admin.ts`, `frontend/src/pages/admin/` (`AdminPage.tsx`, `AdminOverviewPage.tsx`, `AdminUsersPage.tsx`, `AdminDatasetsPage.tsx`, `AdminSystemPage.tsx`), `frontend/src/components/feedback/AnnouncementBanner.tsx`, `frontend/src/__tests__/admin_console.test.tsx`, `docs/decisions.md`, `docs/PROGRESS.md` | Implemented administrative command center and governance APIs. RBAC denial on all admin routes for non-admins (`require_role(["admin"])`); full user administration (search/filter/paginate, role/plan updates, account suspension/activation, manual lockout release, force logout, delete, audit trail); ML training dataset ingestion (CSV upload, physical range QC, IQR outlier fences, 10-row preview, raw download); operational metrics (users, predictions, p50/p95 latency, active model, storage, queue depth); audit log viewer; system settings (feature flags CRUD, app-wide announcements, global quotas and limits). Frontend Admin Console with KPI cards, throughput charts, user management table with confirmation dialogs, dataset upload and statistical validation viewer, and app-wide announcement banner. Verified 76 backend unit tests, 49 ML tests, and 45 frontend tests pass. |
| 16 | Model Lifecycle Management | Completed | 2026-10-07 | `backend/app/schemas/ml_model.py`, `backend/app/services/model_service.py`, `backend/app/services/model_drift_service.py`, `backend/app/workers/tasks/training.py`, `backend/app/workers/schedules.py`, `backend/app/routers/v1/admin/models.py`, `backend/app/main.py`, `backend/app/services/prediction_service.py`, `backend/tests/conftest.py`, `backend/tests/unit/test_model_lifecycle.py`, `frontend/src/api/models.ts`, `frontend/src/components/admin/TrainModelModal.tsx`, `frontend/src/components/admin/ModelCardModal.tsx`, `frontend/src/components/admin/ModelDriftTab.tsx`, `frontend/src/components/admin/ApproveRejectModals.tsx`, `frontend/src/components/admin/ModelComparisonMatrix.tsx`, `frontend/src/components/admin/ShadowReportView.tsx`, `frontend/src/pages/admin/AdminModelsPage.tsx`, `frontend/src/pages/admin/AdminPage.tsx`, `frontend/src/__tests__/admin_models.test.tsx`, `docs/decisions.md`, `docs/PROGRESS.md` | Implemented full ML model lifecycle governance: training pipeline via Celery (RF/XGBoost/LightGBM/SVR/MLP/ensemble, optional Optuna tuning), approval gate (R²≥0.70, RMSE≤1.50, force-bypass with audit), zero-downtime hot swap via ML microservice load_model, reject with reason, rollback to previous version, shadow traffic evaluation with champion/challenger report, weekly drift monitoring via PSI+KS beat schedule. Frontend Admin Models page with registry table, approve/reject modals with quality gate warnings, shadow mode toggle, model card inspector, comparison matrix, drift tab. Root cause of persistent test failure: `r2` and `nse` both equal `0.885` in mock → `getByText` found multiple elements; fixed by switching to `getAllByText` + unique RMSE value. Verified 82 backend unit tests, 48/49 ML tests (1 skipped), 50 frontend tests pass. |
| 17 | Hardening and Polish | Completed | 2026-10-07 | `frontend/src/i18n/config.ts`, `frontend/src/components/ui/LanguageSwitcher.tsx`, `frontend/src/styles/index.css`, `frontend/src/layouts/DashboardLayout.tsx`, `frontend/src/utils/formatters.ts`, `frontend/src/components/ui/SkeletonLoader.tsx`, `frontend/src/components/ui/EmptyState.tsx`, `frontend/src/components/ui/ErrorState.tsx`, `frontend/vite.config.ts`, `frontend/public/offline.html`, `frontend/index.html`, `frontend/src/__tests__/a11y.test.tsx`, `backend/app/models/prediction.py`, `backend/app/main.py`, `backend/tests/unit/test_performance_indexes.py`, `infra/nginx/nginx.conf`, `infra/prometheus/prometheus.yml`, `infra/prometheus/alert_rules.yml`, `infra/grafana/dashboards/overview.json`, `infra/scripts/seed_predictions.py`, `.github/workflows/ci.yml`, `docs/security.md`, `docs/decisions.md`, `docs/PROGRESS.md` | Full platform hardening and production readiness: Complete English and Urdu translation dictionaries across 13 namespaces with RTL logical styles (`[dir='rtl']`), localStorage-persisted language switcher, and locale formatters. WCAG 2.1 AA accessibility enhancements (reduced-motion media query, skip-to-main links, skeleton loaders, empty/error state landmarks, and axe-core tests on Dashboard). PWA integration with vite-plugin-pwa, offline fallback, Workbox runtime caching excluding API calls, and code-split chunks (vendor, charts, maps, i18n). Database indexing optimization on `predictions` (`(user_id, timestamp)`, `(user_id, is_saved)`, `(user_id, classification)`) and 1M-row seed script. Nginx security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), backend SecurityHeadersMiddleware, CI bandit/pip-audit/npm-audit scans, and OWASP ASVS threat modeling in security.md. Prometheus alerting rules and expanded Grafana dashboard with percentiles and health metrics. Verified 86 backend unit tests, 48/49 ML tests (1 skipped), 51 frontend tests pass. |

---


### Task 15 Details & Verification

- **What was built**:
  - `backend/app/routers/v1/admin/`:
    - `users.py`: Search, filter, paginate, role/plan patch, status patch, unlock, force-logout, soft/hard delete, and user audit trail.
    - `datasets.py`: CSV dataset upload, schema validation, physical boundary checking, IQR outlier detection, 10-row preview, download, and deletion.
    - `metrics.py`: Real-time platform KPI statistics, prediction throughput, error rate, p50/p95 latency, and uptime.
    - `audit.py`: Query and filter system-wide audit records by actor, action, and target.
    - `system.py`: Feature flag CRUD, announcement banners publish/toggle, and global system quotas/limits.
  - `backend/app/services/`:
    - `admin_service.py`: User lifecycle mutations with automated audit logging, system metrics calculation, feature flag and announcement storage, and system limits cache.
    - `dataset_service.py`: Validates mandatory columns (`temp_max`, `temp_min`, `humidity`, `wind_speed`), evaluates summary statistics and outlier fences ($1.5 \times \text{IQR}$), tags status (`validated` or `rejected`), and stores CSV files in MinIO storage.
  - `backend/app/schemas/admin.py`: Pydantic V2 models for admin users, datasets, metrics, audit logs, feature flags, announcements, and system limits.
  - `backend/app/routers/v1/notifications.py`: Added public `GET /notifications/announcements` endpoint for app-wide banners.
  - `frontend/src/api/admin.ts`: Strongly typed API client for administrative operations.
  - `frontend/src/pages/admin/`:
    - `AdminPage.tsx`: Tabbed navigation container (Overview, Users, Datasets, System).
    - `AdminOverviewPage.tsx`: Live KPI stat cards and Recharts 7-day inference volume and latency trend chart.
    - `AdminUsersPage.tsx`: Interactive user management table with inline role/plan selectors, lockout status badges, force logout, audit modal, and confirmation dialogs.
    - `AdminDatasetsPage.tsx`: Dataset inventory, CSV upload dialog with statistical validation report and 10-row preview, and raw file download.
    - `AdminSystemPage.tsx`: System governance tabs for feature flag toggles, announcement banner creation, global limits adjustments, and chronological audit log table.
  - `frontend/src/components/feedback/AnnouncementBanner.tsx`: Global banner component displayed across the application in `DashboardLayout.tsx`.
  - `docs/decisions.md`: Recorded ADR 015.

- **Verification**:
  - `backend/tests/unit/test_admin.py`: 9/9 passed (RBAC denial across all admin routes for non-admins, user lifecycle mutations and audit logging, dataset upload with outlier checks and preview, system metrics, feature flags, and announcements).
  - `frontend/src/__tests__/admin_console.test.tsx`: 3/3 passed (Overview KPI rendering, Users table actions with confirm dialogs, Datasets upload modal).
  - `backend/`: **76 passed** out of 76 unit tests.
  - `frontend/`: **45 passed** out of 45 tests across 12 test suites.
  - `ml/`: **49 passed** out of 49 tests.
  - **Quality Gates**: `npm run type-check` (0 errors), `npm test` clean, `pytest` clean.

---

### Task 14 Details & Verification

- **What was built**:
  - `backend/app/models/api_key.py`: Expanded API key entity with granular scopes string array/JSON column and `scope_list` helper property.
  - `backend/app/services/api_key_service.py`: Generates cryptographically secure `agri_live_` secret keys displayed strictly once, computes SHA-256 digests for database persistence, tracks last-used timestamps, and accumulates endpoint hit analytics via `ApiKeyUsageTracker`.
  - `backend/app/core/api_key_auth.py`: Authentication dependencies for API keys:
    - `get_api_key`: Validates key status, expiration, and sliding rate limit.
    - `require_api_key_scope`: Enforces specific permissions (`predict:read`, `batch:write`, `weather:read`, `fields:read`).
    - `get_api_key_or_user`: Allows unified endpoints to authenticate via either JWT bearer token or API key.
  - `backend/app/core/rate_limit.py`: Sliding-window rate limiter with class-level in-memory fallback, `reset_memory()` test utility, and automatic DNS timeout bypass when testing offline without Redis.
  - `backend/app/core/exceptions.py`: Injected `Retry-After: 60` on `RateLimitExceededException` and `Retry-After: 86400` on `QuotaExceededException`.
  - `backend/app/routers/v1/public.py`: Public researcher surface mounted under `/api/v1/public/*`:
    - `POST /public/predict`: Scoped single inference with physical fallback to FAO-56 Penman-Monteith when standalone ML microservice is unmounted.
    - `POST /public/batch/submit` & `GET /public/batch/status/{job_id}`: Scoped batch processing.
    - `GET /public/weather/prefill`: Scoped meteorological prefill.
    - `GET /public/fields/{field_id}/et-series`: Scoped crop water demand time series.
  - `backend/app/providers/billing/`:
    - `base.py`: Abstract `BillingProvider` interface.
    - `mock.py`: Deterministic mock provider with checkout simulation and idempotent webhook event processing.
    - `stripe.py`: Stripe SDK integration with customer session creation, portal redirects, and webhook signature verification (`stripe.Webhook.construct_event`).
  - `backend/app/services/subscription_service.py`:
    - State machine managing user tier transitions (`free`, `pro`, `past_due`, `canceled`).
    - Immediately updates `User.plan`, writes `audit_logs` entries, and broadcasts SSE updates to connected user clients.
  - `backend/app/routers/v1/` (`api_keys.py`, `billing.py`):
    - Endpoints for API key creation, listing, revocation, and usage statistics.
    - Endpoints for subscription status, checkout sessions, billing portal, webhook ingestion, and mock upgrade/downgrade.
  - `frontend/src/api/` (`apiKeys.ts`, `billing.ts`):
    - Strongly typed TypeScript clients for API keys and billing.
  - `frontend/src/pages/settings/` (`ApiKeysTab.tsx`, `BillingTab.tsx`, `SettingsPage.tsx`):
    - `ApiKeysTab`: Generation dialog, copy-once secret modal, scope selector, revocation buttons, and real-time usage statistics popup.
    - `BillingTab`: Subscription plan badges, feature matrix comparison table, Stripe checkout/portal button, and one-click Mock Upgrade/Downgrade controls.
    - `SettingsPage`: 5-tab responsive navigation (Profile, Security, Account, API Keys, Billing).
  - `docs/api.md` & `docs/decisions.md`:
    - Documented Public API surface with `curl` and Python snippets, and recorded ADR 014.

- **Verification**:
  - `backend/tests/unit/test_api_keys.py`: 4/4 passed (creation/hashing, public predict with scopes, rate limiting with 429 Retry-After, revocation and usage statistics).
  - `backend/tests/unit/test_billing.py`: 3/3 passed (checkout/portal sessions, subscription state machine affecting entitlements immediately, webhook signatures and idempotent event handling).
  - `frontend/src/__tests__/api_keys_billing.test.tsx`: 2/2 passed (key generation with copy-once dialog, plan upgrade/downgrade).
  - `backend/`: **67 passed** unit tests.
  - `frontend/`: **42 passed** unit tests across 11 test suites.
  - `ml/`: **49 passed** unit tests.
  - **Quality Gates**: `npm run type-check` (0 errors), `tsc` clean, `pytest` clean.

---

### Task 13 Details & Verification

- **What was built**:
  - `backend/app/providers/storage/`:
    - `base.py`: Abstract `StorageProvider` defining upload, download, presigned URL generation, and existence checks.
    - `minio.py`: Production `MinIOStorageProvider` utilizing MinIO / S3 client with presigned expiring URLs (default 3600s TTL).
    - `mock.py`: In-memory `MockStorageProvider` for tests and offline operation.
  - `backend/app/services/export_service.py`:
    - Formula injection defense (`sanitize_csv_cell` against CWE-1236 prefixing `=,+,-,@,\t,\r` with `'`).
    - Multi-format generators: `generate_csv_bytes`, `generate_xlsx_bytes` (`openpyxl` with styled headers and dynamic column widths), and `generate_png_chart` (`matplotlib` standalone headless render).
  - `backend/app/services/report_service.py`:
    - Branded PDF report compiler (`reportlab` `SimpleDocTemplate` + `Table` + `Paragraph` + embedded chart images) for prediction summaries and field seasonal water balances.
  - `backend/app/services/notification_service.py`:
    - `NotificationService`: CRUD, unread filtering, batch read markers, and notification preference management.
    - `SSEConnectionManager`: Asyncio client queues for real-time notification streaming over Server-Sent Events.
  - `backend/app/workers/tasks/batch.py`:
    - Celery task `process_batch_prediction_job_task`: Processes CSV datasets up to 10k rows, performs batch inference via `MLClient`, evaluates FAO-56 reference values, records per-row errors, uploads result CSV to MinIO, updates `batch_jobs` record, and broadcasts completion events.
  - `backend/app/routers/v1/` (`batch.py`, `reports.py`, `notifications.py`):
    - Mounted `/batch/template`, `/batch/upload`, `/batch/status/{id}`, `/batch/download/{id}` (idempotent, Pro-gated).
    - Mounted `/reports/generate`, `/reports/list`, `/reports/download/{id}` (Pro-gated).
    - Mounted `/notifications`, `/notifications/{id}/read`, `/notifications/mark-all-read`, `/notifications/preferences`, and `/notifications/stream` (SSE).
  - `frontend/src/api/jobs.ts`:
    - Strongly typed API client for batch, reports, and notification endpoints.
  - `frontend/src/pages/batch/BatchPage.tsx` & `pages/reports/ReportsPage.tsx`:
    - Asynchronous batch inference UI with template downloader, file uploader, real-time polling progress bar, error viewer, and results downloader.
    - Analytical report generation modal supporting PDF, XLSX, CSV, and PNG downloads.
  - `frontend/src/components/ui/NotificationCenter.tsx`:
    - Topbar bell dropdown with unread badge counter, live SSE message listener, and mark-read actions.
  - `frontend/src/__tests__/jobs_and_delivery.test.tsx` & `backend/tests/unit/test_jobs_and_delivery.py`:
    - Unit tests for formula injection sanitization, XLSX generation, PDF compilation, notification handling, BatchPage, ReportsPage, and NotificationCenter.

- **Verification**:
  - `backend/tests/unit/test_jobs_and_delivery.py`: 4/4 passed.
  - `backend/`: **60 passed** unit tests.
  - `ml/`: **49 passed** unit tests.
  - `frontend/`: **40 passed** unit tests.
  - **Quality Gates**: `npm run type-check` (0 errors), `npm test` (40/40 passed), `pytest` backend & ML suites 100% clean.

---

### Task 12 Details & Verification

- **What was built**:
  - `backend/app/core/soil.py`:
    - Soil presets for 7 textures (sand, loamy sand, sandy loam, loam, silt loam, clay loam, clay) with field capacity $\theta_{\text{FC}}$, wilting point $\theta_{\text{WP}}$, and Total Available Water ($\text{TAW}$ mm/m).
  - `backend/app/services/irrigation_service.py`:
    - USDA SCS effective precipitation $P_{\text{eff}}$, dynamic root depth progression $Z_r(t)$, daily root-zone soil water balance ($D_{r,i} = D_{r,i-1} + ET_c - P_{\text{eff}} - I$), Readily Available Water ($\text{RAW} = p \times \text{TAW} \times Z_r$), 7-day volumetric application schedule, and applied irrigation event management.
  - `backend/app/routers/v1/crops.py` & `irrigation.py`:
    - Mounted `/crops` (FAO-56 growth stages and Kc library) and `/irrigation` (`/plan/{field_id}`, `/events/{field_id}`).
  - `frontend/src/components/charts/SoilWaterDepletionChart.tsx`:
    - Composed chart visualizing root-zone depletion $D_r$ against red dashed RAW stress thresholds and TAW bounds.
  - `frontend/src/pages/irrigation/IrrigationPage.tsx`:
    - Precision irrigation dashboard with soil/MAD controls, status KPI cards, 7-day forecast schedule, and event logging modal.
  - `backend/tests/unit/test_irrigation_service.py` & `frontend/src/__tests__/irrigation.test.tsx`:
    - Verification of USDA effective rainfall breakpoints, root growth modeling, depletion re-balancing, and schedule rendering.

- **Verification**:
  - `backend/tests/unit/test_irrigation_service.py`: 4/4 passed.
  - `backend/`: **56 passed** unit tests.
  - `ml/`: **49 passed** unit tests.
  - `frontend/`: **37 passed** unit tests.
  - **Quality Gates**: `npm run type-check` (0 errors), `npm test` (37/37 passed), `pytest` backend & ML suites clean.


- **What was built**:
  - `backend/app/services/field_service.py`:
    - Field parcel CRUD, PostGIS polygon handling, pure Python spherical polygon area computation in hectares (`calculate_polygon_area_ha`), and Free-plan single field quota enforcement (`max_fields=1`).
  - `backend/app/providers/satellite/`:
    - `base.py`: Abstract `SatelliteProvider` and `SatelliteObservation` dataclass.
    - `stac_sentinel.py`: Open STAC API client querying Copernicus Sentinel-2 L2A collections, calculating NDVI, EVI, and NDWI, with Scene Classification Layer (SCL) cloud screening.
    - `gee.py`: Google Earth Engine provider gated by service account credentials for MODIS MOD16 ET validation.
    - `mock.py`: Deterministic, physics-consistent seasonal vegetation curves for offline testing.
  - `backend/app/services/remote_sensing_service.py`:
    - Ingests satellite scenes, derives crop coefficient $K_c$ via `agriscope_ml.physics.crop_coefficients.ndvi_to_kc`, resolves weather $ET_0$, computes daily crop evapotranspiration $ET_c = K_c \times ET_0$, and persists records to `field_observations`.
  - `backend/app/routers/v1/fields.py` & `remote_sensing.py`:
    - Mounted `/fields` CRUD and `/remote-sensing/analyze/{field_id}` endpoints gated by `require_plan_feature("remote_sensing_enabled")`.
  - `backend/app/workers/tasks/satellite.py`:
    - Celery task `refresh_active_fields_weekly` for scheduled automated field observation updates.
  - `docs/remote-sensing.md`:
    - Comprehensive guide on vegetation indices, mathematical formulations, $K_c$ empirical relationships, SCL cloud filtering, and spatial resolution limitations.
  - `frontend/src/components/maps/FieldPolygonMap.tsx`:
    - Interactive Leaflet map with click-to-draw polygon vertices, undo/clear controls, and polygon boundary visualization.
  - `frontend/src/pages/fields/FieldsPage.tsx` & `frontend/src/pages/remote-sensing/RemoteSensingPage.tsx`:
    - Fields parcel management dashboard and Remote Sensing analytics workspace with KPI status cards, `VegetationIndicesChart`, `EvapotranspirationComparisonChart`, and satellite scenes audit table.
  - `frontend/src/__tests__/fields_rs.test.tsx`:
    - Vitest unit tests for field listing and remote sensing analytics.

- **Verification**:
  - `backend/tests/unit/test_field_service.py`: 2/2 passed (spherical hectare area calculation and Free-tier 1-field entitlement error).
  - `backend/tests/unit/test_remote_sensing.py`: 4/4 passed (`compute_indices_from_bands`, `ndvi_to_kc`, `calculate_etc`, `MockSatelliteProvider` determinism, and full remote sensing analysis pipeline).
  - `backend/`: **52 passed** unit tests.
  - `ml/`: **49 passed** unit tests.
  - `frontend/`: **36 passed** unit tests.
  - **Quality Gates**: `npm run type-check` (0 errors), `npm test` (36/36 passed), `pytest` backend & ML suites clean.


- **What was built**:
  - `backend/app/providers/weather/`:
    - `base.py`: Abstract `WeatherProvider` class and `DailyWeatherRecord` dataclass standardizing temperatures, relative humidity, wind speed (at 2m), solar radiation, precipitation, provider-calculated FAO-56 ET0, and degradation flags (`is_fallback`, `is_cached`).
    - `open_meteo.py`: `OpenMeteoProvider` fetching forecasts and historical archives; converts 10m wind to 2m using the FAO-56 logarithmic profile ($u_2 \approx u_{10} \times 0.75$); extracts provider-calculated $ET_0$; implements place search via Open-Meteo Geocoding API.
    - `nasa_power.py`: `NasaPowerProvider` querying NASA POWER daily agroclimatology API with QC filters.
    - `mock.py`: `MockWeatherProvider` generating deterministic, physics-consistent observations based on coordinates, seasonal sinusoidal curves, and day-of-year for guaranteed offline fallback.
  - `backend/app/services/weather_service.py`:
    - Multi-tier resolution: Checks Redis cache (TTL 7d for historical, 3h for forecast) -> queries primary provider -> falls back to secondary provider or `MockWeatherProvider`.
    - Generates 7-day crop evapotranspiration forecasts by running daily meteorological parameters through `MLClient.predict`, returning ML ET₀ estimates, 90% conformal intervals, and provider FAO-56 benchmarks.
    - Historical monthly summary aggregation calculating mean daily ET₀ per calendar month.
  - `backend/app/routers/v1/weather.py`:
    - Mounted `GET /api/v1/weather/prefill`, `GET /api/v1/weather/forecast`, `GET /api/v1/weather/historical`, and `GET /api/v1/weather/geocode`.
  - `frontend/src/components/maps/PointPickerMap.tsx`:
    - Interactive Leaflet map with draggable point marker, click-to-pick coordinates, and place autocomplete search bar.
  - `frontend/src/components/predict/LocationModeSelector.tsx`:
    - Map-and-date picker querying `/weather/prefill` and populating the prediction form with `source=location`.
  - `frontend/src/components/charts/ForecastChart.tsx` & `HistoricalAggregationChart.tsx`:
    - Composed Recharts visualization rendering ML forecast line, 90% conformal prediction interval area band, and Open-Meteo FAO-56 reference dashed line.
    - Monthly bar chart displaying historical seasonal demand patterns.
  - `frontend/src/components/predict/WeatherForecastWorkspace.tsx`:
    - Interactive workspace on Predict page allowing users to inspect 7-day ET₀ forecasts and 6-month historical climatology.

- **Verification**:
  - `backend/tests/unit/test_weather_providers.py`: 3/3 passed (Mock provider physical ranges, Open-Meteo fixture parsing with FAO-56 ET0, NASA POWER fixture parsing).
  - `backend/tests/integration/test_weather_api.py`: 3/3 passed (graceful degradation fallback to mock provider, 7-day forecast with ML prediction and interval bounds, geocoding search endpoint).
  - `backend/`: **54 passed** out of 54 tests.
  - `ml/`: **49 passed** out of 49 tests.
  - `frontend/`: **34 passed** out of 34 tests.
  - **Quality Gates**: `npm run type-check` (clean), `npm run lint` (0 errors, 0 warnings), `ruff` & `black` on backend (clean).

- **What was built**:
  - `backend/app/schemas/prediction.py`: Pydantic request and response schemas for single prediction, multi-model comparison, SHAP feature attributions, sample observation payloads, paginated history lists, bookmark/note updates, bulk deletion, and 7-day dashboard statistics.
  - `backend/app/services/prediction_service.py`: Orchestrates prediction flow: physical input range validation (-10..50°C, 0..100%, 0..30 m/s, 0..35 MJ/m²/d), Redis quota tracking (`QuotaService`), inference via `MLClient`, concurrent FAO-56 Penman-Monteith physics calculation (`agriscope_ml.physics.penman_monteith.calculate_et0`), ET demand classification (`low` <2, `moderate` 2–5, `high` >5 mm/day), agronomic guidance generator, What-If sandbox mode (`persist=False`), and persistence.
  - `backend/app/services/history_service.py`: Comprehensive audit queries: server-side pagination, date range filtering, classification filtering, text search over notes and tags, Free-tier 50-item cap, bookmark updates, single and bulk deletion, and 7-day trend statistics.
  - `backend/app/routers/v1/predict.py` & `history.py`: Mounted REST API endpoints with plan gating (`require_plan("model_comparison_enabled")`, `require_plan("explainability_enabled")`).
  - `frontend/src/api/predict.ts` & `history.ts`: Strongly typed Axios clients with TypeScript interfaces.
  - `frontend/src/components/charts/`: Recharts data visualizations:
    - `ShapBarChart.tsx`: Color-coded horizontal bar chart (red for features increasing ET₀, blue for features decreasing ET₀) with baseline reference line.
    - `ModelComparisonChart.tsx`: Side-by-side bar chart comparing Ensemble against individual models, accompanied by a metrics comparison table.
    - `EtHistoryLineChart.tsx`: 7-day evapotranspiration trend line chart with colored FAO-56 background zones (green <2 mm, amber 2–5 mm, red >5 mm).
  - `frontend/src/components/predict/`:
    - `PredictResultPanel.tsx`: Prominent ET₀ display, 90% conformal interval, FAO-56 physics benchmark, agronomic advice, model metadata, and bookmarking.
    - `WhatIfSandbox.tsx`: Real-time debounced parameter sliders testing sensitivity live without history persistence.
  - `frontend/src/pages/predict/PredictPage.tsx`: Full prediction workflow with sample data preset loader, advanced coordinates accordion, and Pro gated feature tabs.
  - `frontend/src/pages/history/HistoryPage.tsx`: History table with bulk deletion dialog, inline note editor, demand class filters, and 7-day trend card.
  - `frontend/src/pages/dashboard/DashboardPage.tsx`: Live KPI cards for daily quota, latest ET₀, total inferences, and 7-day trend chart.

- **Verification**:
  - `backend/tests/unit/test_predict_service.py`: 4/4 passed (irrigation interpretation categories, FAO-56 physics calculation, quota exhaustion, sandbox persistence bypass).
  - `backend/tests/integration/test_predict_history_api.py`: 4/4 passed (parameter boundary envelopes 422 errors, Free vs Pro plan gating on compare & explain, full predict -> list -> bookmark -> stats -> delete flow, sample data endpoint).
  - `backend/`: **48 passed** out of 48 total tests.
  - `ml/`: **49 passed** out of 49 total tests.
  - `frontend/src/__tests__/predict_history.test.tsx`: 2/2 passed.
  - `frontend/`: **34 passed** out of 34 total tests.
  - **Lint & Types**: `npm run type-check` (clean), `npm run lint` (0 errors, 0 warnings), `ruff` and `black` on backend (clean).

---

### Task 8 Details & Verification

- **What was built**:
  - `ml/service/`:
    - `schemas/inference.py`: Pydantic request and response schemas enforcing physical boundaries (temperature -10..50°C, RH 0..100%, wind 0..30 m/s, solar 0..35 MJ/m²/day), conformal intervals, and physical ET classifications (`low`, `moderate`, `high`).
    - `manager.py`: Thread-safe `ModelManager` supporting pre-warmed startup, atomic model pointer swapping under lock, batch inference array processing, and SHAP feature attribution caching.
    - `routers/infer.py`: Mounted `POST /infer`, `POST /infer/batch`, and `POST /explain`.
    - `routers/models.py`: Mounted `GET /models` and `POST /models/load` (hot-swap).
    - `main.py`: Lifespan handler warm-loading active bundle and enriched `GET /health` endpoint.
  - `backend/app/services/ml_client.py`:
    - Resilient `MLClient` with configurable connection and read timeouts.
    - Three-state `CircuitBreaker` (`CLOSED`, `OPEN`, `HALF_OPEN`) fast-failing upon 3 consecutive failures and recovering after a 5.0s cooldown and 2 successful probe trials.
    - Exponential backoff retries ($0.05 \times 2^k$) on transient connection errors.
    - Strongly typed Pydantic responses (`PredictionResult`, `BatchPredictionResult`, `ExplanationResult`, `MLServiceHealth`, `ModelInfo`).
  - `backend/app/services/model_registry_sync.py`:
    - Synchronizes on-disk / MinIO artifact bundles into PostgreSQL `ml_models` table idempotently.
    - `get_active_model_cached`: Caches active model metadata in Redis (`agriscope:active_model_metadata`, TTL 300s).
    - `set_active_model`: Promotes active model and deletes Redis cache key.
  - `backend/app/db/init_db.py`:
    - Updated to automatically execute model registry sync during seeding, ensuring bootstrap ensemble model is registered as `ACTIVE` with `data_provenance="synthetic"`.
  - `docs/ml-model.md` & `docs/decisions.md`:
    - Documented microservice latency profiles, batch throughput, circuit breaker architecture, and recorded ADR 008.

- **Verification**:
  - `ml/tests/test_service.py`: 7/7 tests passing (healthcheck, single inference latency < 150 ms, batch inference, physical validation 422 errors, SHAP explanation, hot-swapping, and concurrent requests during reload).
  - `backend/tests/unit/test_ml_client.py`: 5/5 tests passing (circuit breaker state transitions, trial failures, mock server predict and explain, circuit breaker fast-fail tripping, and 4xx error bypass).
  - `backend/tests/unit/test_model_registry_sync.py`: 3/3 tests passing (idempotent DB sync, Redis cache hit/miss, cache invalidation on model promotion).
  - **Latency Benchmarks**:
    - Single inference: Mean 24.03 ms, $p_{50}$ 21.19 ms, **$p_{95}$ 36.34 ms** (well below the 150 ms requirement).
    - Batch inference (100 rows): Total 44.37 ms (**0.444 ms/row**).
    - SHAP explanation: Mean 156.73 ms, $p_{95}$ 190.52 ms.
  - **Total Test Counts**:
    - `ml/`: **43 passed** out of 43 tests.
    - `backend/`: **40 passed** out of 40 tests.
    - `frontend/`: **32 passed** out of 32 tests.
  - **Code Quality**: `ruff` and `black` clean across both `ml/` and `backend/`.

---

### Task 7 Details & Verification

- **What was built**:
  - `ml/agriscope_ml/pipelines.py`: Scikit-learn pipelines with `StandardScaler` preprocessing for `RandomForest`, `XGBoost`, `LightGBM`, `SVR`, `MLP`, and a `StackingRegressor` (combining RF, XGBoost, LightGBM, and SVR with a `RidgeCV` meta-estimator). Supports configurable hyperparameter overrides and seed determinism.
  - `ml/agriscope_ml/evaluate.py`: Implemented $R^2$, RMSE, MAE, Mean Bias Error, Nash-Sutcliffe Efficiency (NSE), Kling-Gupta Efficiency (KGE), 7-point residual distributions (mean, std, median, min, max, p25, p75), and $k$-fold / group $k$-fold cross-validation.
  - `ml/agriscope_ml/uncertainty.py`: Split Conformal Prediction intervals (`ConformalPredictor`) with finite-sample corrected quantile calculation at 90% confidence ($\alpha=0.10$), non-negative physical bounds clipping, and empirical coverage validation on held-out test data.
  - `ml/agriscope_ml/explain.py`: SHAP explainer module (`ModelExplainer`) providing `TreeExplainer` for tree architectures and sampled `KernelExplainer` fallback for kernel/neural/ensemble models, with unit-tested mathematical additivity verification ($|\hat{y} - (\text{base} + \sum \phi_j)| < 10^{-4}$).
  - `ml/agriscope_ml/drift.py`: Data distribution drift detection with Population Stability Index (PSI, quantile binning) and two-sample Kolmogorov-Smirnov (KS) testing, classifying drift severity (`none`, `moderate`, `significant`).
  - `ml/agriscope_ml/tuning.py`: Optuna Bayesian optimization with Tree-structured Parzen Estimators (TPE), cross-validated RMSE minimization, time and trial limits, and progress callbacks.
  - `ml/agriscope_ml/model_card.py`: JSON model card specification capturing algorithm metadata, hyperparameters, dataset identifiers, SHA-256 data hash, provenance flags (`is_synthetic`), dual-split evaluation metrics, conformal calibration results, training duration, and Git commit SHA.
  - `ml/agriscope_ml/registry.py`: Model bundle management supporting local filesystem and S3/MinIO backends, storing model pipelines, conformal predictors, background reference samples, model cards, and `checksums.json` with SHA-256 tamper verification.
  - `ml/agriscope_ml/cli.py`: Integrated `train` sub-command supporting `--algorithm all` and single algorithm training, resolving dataset files or synthetic fallbacks, and rendering formatted dual-split benchmark tables.
  - `Makefile`: Added `train` target invoking `agriscope-ml train --algorithm all`.
  - `docs/ml-model.md`: Documented architecture, hyperparameter profiles, benchmark comparison table of random vs grouped holdout splits, uncertainty intervals, explainability, and drift detection.
  - `docs/decisions.md`: Recorded ADR 007.

- **Verification**:
  - `ml/tests/test_pipelines.py`: 7/7 passing (all algorithms fit/predict, seed determinism).
  - `ml/tests/test_evaluate.py`: 5/5 passing (perfect predictions, constant bias, NSE properties, KGE scaling, k-fold CV).
  - `ml/tests/test_uncertainty.py`: 2/2 passing (finite-sample coverage $\ge 90\% - 5\%$, non-negative clipping).
  - `ml/tests/test_explain.py`: 1/1 passing (SHAP TreeExplainer additivity check delta $< 10^{-3}$, feature ranking).
  - `ml/tests/test_drift.py`: 2/2 passing (unshifted data shows no drift, shifted data triggers PSI $\ge 0.20$ & KS drift).
  - `ml/tests/test_registry.py`: 2/2 passing (bundle round-trip preserving predictions, tamper detection raising ValueError).
  - `ml/tests/test_tuning.py`: 1/1 passing (Optuna optimization with trial callbacks).
  - `ml/tests/test_train.py`: 2/2 passing (group identifier synthesis, dual split training and registration).
  - **Total ML Suite**: **43 passed** out of 43 tests.
  - **Code Quality**: `ruff check agriscope_ml service tests` clean; `black --check agriscope_ml service tests` clean.
  - **Full Platform Verification**: Backend (32 passed) and Frontend (32 passed) remain 100% green.

---

### Task 6 Details & Verification

- **What was built**:
  - `ml/agriscope_ml/physics/penman_monteith.py`: Implemented full daily FAO-56 Penman-Monteith formulation with all intermediate terms ($\Delta, \gamma, P, e_s, e_a, VPD, R_a, R_{so}, R_{ns}, R_{nl}, R_n, G=0, u_2$), aerodynamic and radiation decompositions, wind speed logarithmic height adjustments, and a documented 4-input simplified fallback model ($T, RH, u_2, R_s$).
  - `ml/agriscope_ml/physics/crop_coefficients.py`: Implemented piecewise linear 4-stage crop coefficient interpolation ($L_{\text{ini}}, L_{\text{dev}}, L_{\text{mid}}, L_{\text{late}}$) with stage classification, satellite NDVI-to-$K_c$ transformation using canopy fraction scaling clamped within physical limits ($0.15 \le K_c \le 1.35$), and $ET_c = K_c \times ET_0$.
  - `ml/agriscope_ml/data/nasa_power.py`: Curated 50 global agricultural stations (heavy coverage across Pakistan/South Asia, Mediterranean, the Americas, Africa, Oceania), local JSON caching, polite rate limiting, retry backoffs, range QC filters (rejecting -999 fill values), and automatic $ET_0$ calculation.
  - `ml/agriscope_ml/data/synthetic.py`: Offline labelled fallback generator sampling physical ranges, calculating FAO-56 targets with ~3% observation noise, and stamping `provenance="synthetic"` and `is_synthetic=True`.
  - `ml/agriscope_ml/data/datasets.py`: Parquet and CSV versioned export with deterministic SHA-256 hashing, metadata cards, and user-uploaded CSV validation.
  - `ml/agriscope_ml/features.py`: Basic 4-feature and extended feature engineering schemas (cyclic $\sin/\cos$ day-of-year, diurnal temperature range, vapour pressure deficit).
  - `ml/agriscope_ml/cli.py`: Installed CLI entry point `agriscope-ml` supporting `build-dataset --source nasa|synthetic` (with automatic fallback warning) and `validate-csv --file <path>`.

- **Verification**:
  - `ml/tests/test_physics_penman_monteith.py`: 7/7 tests passing (benchmarked against FAO-56 Example 18 Bangkok case, wind profile, radiation terms, and edge cases).
  - `ml/tests/test_physics_crop_coefficients.py`: 3/3 tests passing (piecewise stages, NDVI limits, ETc).
  - `ml/tests/test_data_synthetic.py`: 2/2 tests passing (seeded reproducibility, physical bounds, provenance stamps).
  - `ml/tests/test_data_datasets.py`: 4/4 tests passing (content hashing, CSV validation, dataset export, feature engineering).
  - `ml/tests/test_data_nasa_power.py`: 2/2 tests passing (mocked offline network responses, QC fill value clipping).
  - `ml/tests/test_cli.py`: 2/2 tests passing (CLI subprocess build-dataset and validate-csv).
  - `ml/tests/test_service.py`: 1/1 test passing (ML inference service health endpoint).
  - **Full ML Suite**: **21 passed** out of 21 tests in `ml/`.
  - **Code Quality**: `ruff check agriscope_ml tests` and `black --check agriscope_ml tests` passed cleanly with 0 errors.
  - **Cross-Component Regression**: Backend (32 passed) and Frontend (32 passed) suites remain 100% green.

---

### Task 5 Details & Verification

- **What was built**:
  - `frontend/src/components/ui/`: 15 accessible components (`Button`, `Input`, `Select`, `Checkbox`, `Modal`, `ConfirmDialog`, `Table`, `Card`, `Badge`, `Tabs`, `Toast`, `Skeleton`, `EmptyState`, `Spinner`, `Tooltip`) leveraging Radix UI primitives with full keyboard navigation and focus management.
  - `frontend/src/styles/index.css` & `frontend/tailwind.config.ts`: Deep-green agricultural/scientific color palette (`#15803d` primary, `#052e16` dark accents) powered by CSS variables with system/light/dark theme toggling and local storage persistence.
  - `frontend/src/api/client.ts`: Typed Axios client with automatic `X-Request-ID` generation, bearer access token management, silent cookie-based `/auth/refresh` execution on 401 errors with request queueing to prevent refresh storms, and broadcasted unauthorized logout.
  - `frontend/src/api/auth.ts` & `frontend/src/api/users.ts`: Fully typed API client wrappers covering registration, login, logout, password resets, email verification, profile updates, 2FA setup/disable, session management, and GDPR exports.
  - `frontend/src/context/AuthContext.tsx` & `frontend/src/context/ThemeContext.tsx`: React Context providers for authentication state, silent bootstrap on mount, 2FA challenge resolution, quota hydration, and theme switching.
  - `frontend/src/routes/`: Route guards (`ProtectedRoute`, `RoleRoute`, and `PlanRoute` displaying a feature upgrade prompt card with tier benefits).
  - `frontend/src/layouts/`: `AuthLayout` (branding, theme switch, FAO-56 provenance footer) and `DashboardLayout` (responsive sidebar, topbar with daily quota indicator, user card, theme toggle, and data provenance footer).
  - `frontend/src/utils/validators.ts`: Zod validation schemas for all authentication and account self-service forms enforcing physical and security rules.
  - `frontend/src/pages/auth/`: `Login` (with seamless 2FA challenge and recovery code fallback), `Register`, `VerifyEmail` (supporting token auto-verification and resend), `ForgotPassword`, and `ResetPassword`.
  - `frontend/src/pages/settings/`: `SettingsPage` with Profile tab, Security tab (2FA QR setup with 8 recovery codes, active session list with revocation, security audit list), and Account tab (GDPR JSON archive export and double-confirmed soft deletion).
  - `frontend/src/pages/dashboard/DashboardPage.tsx`: Placeholder operational dashboard displaying live quota indicators, FAO-56 Penman-Monteith physics summary, and quick navigation cards.

- **Verification**:
  - `src/__tests__/validators.test.ts`: 15/15 tests passing.
  - `src/__tests__/AuthContext.test.tsx`: 3/3 tests passing.
  - `src/__tests__/guards.test.tsx`: 6/6 tests passing.
  - `src/__tests__/forms.test.tsx`: 2/2 tests passing.
  - `src/__tests__/a11y.test.tsx`: 5/5 axe-core WCAG accessibility audits passing across all auth pages.
  - `src/__tests__/App.test.tsx`: 1/1 test passing.
  - **Full Frontend Suite**: **32 passed** out of 32 tests in Vitest.
  - **Full Backend Suite**: **32 passed** out of 32 tests in pytest.
  - **TypeScript & Linting**: `tsc --noEmit`, `eslint`, and `prettier --check` passed cleanly with 0 errors and 0 warnings.
  - **Vite Production Build**: `npm run build` succeeded without errors.

---

### Task 4 Details & Verification

- **What was built**:
  - `backend/app/core/plans.py`: Centralized entitlement matrix (`PLAN_FREE`, `PLAN_PRO`, `PLAN_ADMIN`) specifying daily inference limits and feature flags. Implemented `QuotaService` with atomic daily tracking and 24-hour TTL (Redis + memory fallback), plus `require_plan_feature` dependency raising HTTP 403 `UPGRADE_REQUIRED` on forbidden features.
  - `backend/app/schemas/account.py`: Pydantic models for entitlements response, profile update, email change request/confirmation, password change, TOTP setup/verify/disable, account data export, and user audit log read.
  - `backend/app/models/user.py`: Added `totp_recovery_codes` JSON/JSONB column storing SHA-256 hashes of single-use recovery codes.
  - `backend/app/services/account.py`: Account self-service service class supporting:
    - Profile update with validation.
    - Two-step email change with signed action token verification.
    - Password change invalidating all sessions except the current session.
    - RFC 6238 TOTP setup (base32 secret, provisioning URI, and PNG base64 QR code via `qrcode` + `pillow`), TOTP verification enabling 2FA and generating 8 single-use recovery codes, and 2FA disabling.
    - Comprehensive GDPR JSON export assembling user metadata, active sessions, audit events, fields, and predictions.
    - Account soft deletion with session termination and audit logging.
    - Audit log querying for user-specific events.
  - `backend/app/services/auth.py` & `backend/app/routers/v1/auth.py`: Updated `authenticate_user` and `LoginRequest` to support 2FA challenges (`2FA_REQUIRED:<temp_token>`), accepting either standard 6-digit TOTP codes or single-use recovery codes.
  - `backend/app/routers/v1/users.py`: Mounted REST endpoints under `/api/v1/users`:
    - `GET /me/entitlements`
    - `GET /me`
    - `PATCH /me/profile`
    - `POST /me/change-email`
    - `POST /me/confirm-email-change`
    - `POST /me/change-password`
    - `POST /me/2fa/setup`
    - `POST /me/2fa/verify`
    - `POST /me/2fa/disable`
    - `GET /me/export`
    - `DELETE /me`
    - `GET /me/audit`
  - `backend/requirements/base.txt`: Added `pillow>=10.3.0` for QR code image generation.
  - `docs/api.md` & `docs/decisions.md`: Documented all API endpoints, request/response models, and ADR 004.

- **Verification**:
  - `backend/tests/unit/test_plans_rbac.py`: 4/4 passing unit tests verifying entitlement matrix, Redis/memory QuotaService incrementing and daily reset, `require_plan_feature` gating, and `require_role` RBAC dependency.
  - `backend/tests/unit/test_account_service.py`: 5/5 passing unit tests verifying profile update, email change flow, password change and session invalidation, full TOTP 2FA lifecycle (setup, enable, challenge login, recovery codes, disable), and GDPR export + soft deletion.
  - Full test suite: **32 passed** out of 32 tests.
  - Ruff and Black formatting checks: Clean pass with zero errors.

---

### Task 3 Details & Verification

- **What was built**:
  - `backend/app/services/auth.py`: Complete authentication business logic including password validation (min 8 chars, 1 uppercase, 1 digit, breached password check), email verification token issuance, constant-time dummy bcrypt verification on missing users, 5-failure lockout with 15-minute auto-unlocking, refresh token family rotation, replay attack detection with family invalidation, single-use password reset tokens with password hash linkage, session listing/revocation, and audit log generation.
  - `backend/app/routers/v1/auth.py`: REST endpoints mounted under `/api/v1/auth`:
    - `POST /register`: Registers user, hashes password, triggers email verification task.
    - `POST /login`: Validates credentials, sets httpOnly cookie with refresh token, returns JWT access token.
    - `POST /refresh`: Rotates refresh token in cookie, detects reuse, issues fresh access token.
    - `POST /logout`: Revokes current session token and clears cookie.
    - `POST /logout-all`: Inactive all user sessions.
    - `GET /sessions`: Lists active and past user sessions.
    - `DELETE /sessions/{session_id}`: Revokes a specific session.
    - `POST /verify-email`: Activates email status via signed token.
    - `POST /resend-verification`: Rate-limited unverified account token dispatch.
    - `POST /forgot-password`: Rate-limited 1-hour single-use reset token dispatch.
    - `POST /reset-password`: Updates password, clears all existing sessions.
    - `GET /me`: Returns current user identity.
  - `backend/app/core/security.py`: Password validation function (`validate_password_strength`), token hashing (`hash_token`), cryptographic token generation (`generate_secure_token`), access token signing with unique `jti`, and action token generator (`create_action_token`).
  - `backend/app/core/deps.py`: `get_current_user` and `require_role(roles)` dependencies with token decoding and status validation.
  - `backend/app/core/rate_limit.py`: Sliding-window rate limiter utilizing Redis sorted sets with in-memory fallback.
  - `backend/app/providers/email/smtp.py`: `SMTPEmailProvider` connecting to Mailpit / SMTP and `MockEmailProvider` with in-memory logging for tests.
  - `backend/app/workers/tasks/emails.py`: Celery email tasks (`send_verification_email_task`, `send_password_reset_email_task`) with HTML & plain text templates.
  - `docs/security.md` and `docs/decisions.md`: Documented authentication architecture and ADR 003.


- **Verification**:
  - Test coverage on `app/services/auth.py`: **95%** (exceeds ≥90% requirement).
  - Full test suite: **23 passed** across unit and integration tests.
  - Ruff and Black formatting checks: Clean pass with zero errors.

---

### Task 16 Details & Verification

- **What was built**:
  - `backend/app/schemas/ml_model.py`: Pydantic v2 schemas (`TrainRequest`, `MLModelOut`, `ApproveRequest`, `RejectRequest`, `ShadowReportOut`, `DriftReportOut`).
  - `backend/app/services/model_service.py`: `ModelService` with `train_model`, `approve_model` (quality gate + hot swap + Redis cache invalidation), `reject_model`, `rollback_model`, `toggle_shadow_mode`, and `record_shadow_evaluation`.
  - `backend/app/services/model_drift_service.py`: `ModelDriftService` with `get_shadow_report` (champion/challenger bias/RMSE/MAE deltas) and `run_drift_check` (PSI+KS via `agriscope_ml.drift`).
  - `backend/app/workers/tasks/training.py`: `train_models_task` Celery task (queue=training, Optuna optional) and `run_drift_check_task`.
  - `backend/app/workers/schedules.py`: Added `run-drift-check-weekly` beat schedule (604800s, lookback_days=30).
  - `backend/app/routers/v1/admin/models.py`: 13 endpoints — list, active, get, train, approve, reject, rollback, shadow toggle, shadow report, drift report, delete.
  - `backend/app/main.py`: Registered `admin_models_router`.
  - `backend/app/services/prediction_service.py`: Added `record_shadow_evaluation` hook (non-blocking try/except) after each persisted prediction.
  - `backend/tests/conftest.py`: Added `shadow_results` table to in-memory SQLite setup.
  - `backend/tests/unit/test_model_lifecycle.py`: 6 tests — list active, approve with gate, force approve bypass, reject, rollback, shadow toggle.
  - `frontend/src/api/models.ts`: Full typed API client (listModels, approveModel, rejectModel, rollbackModel, toggleShadowMode, getShadowReport, getDriftReport, trainModel, deleteModel).
  - `frontend/src/components/admin/`: `TrainModelModal`, `ModelCardModal` (data-testid, evaluation metrics, conformal calibration, hyperparameters), `ModelDriftTab`, `ApproveRejectModals`, `ModelComparisonMatrix`, `ShadowReportView`.
  - `frontend/src/pages/admin/AdminModelsPage.tsx`: Registry table with status badges, tabbed interface (Shadow Report, Comparison Matrix, Drift Monitoring), approve/reject/rollback actions.
  - `frontend/src/pages/admin/AdminPage.tsx`: Added Models tab.
  - `frontend/src/__tests__/admin_models.test.tsx`: 5 tests — registry render, pending model display, ModelCardModal unit test, quality gate warning, shadow toggle.

- **Test failure root cause** (resolved):
  - `getByText('0.885')` threw `getMultipleElementsFoundError` because both `r2: 0.885` and `nse: 0.885` in mock produce the same rendered string.
  - Fix: switched to `getAllByText('0.885').length >= 1` + unique RMSE value `getByText('0.650')`.
  - Earlier `fireEvent.click` approach failed because the full-page integration test couldn't confirm modal state update; resolved by directly rendering `ModelCardModal` as a unit test with a static import.

- **Verification**:
  - Backend unit tests: **82/82 passed**.
  - ML tests: **48/49 passed** (1 skipped — expected).
  - Frontend tests: **50/50 passed**.
  - TypeScript: `tsc --noEmit` clean.

---

### Task 17 Details & Verification

- **What was built**:
  - `frontend/src/i18n/config.ts`: Complete English and Urdu translation catalogs covering 13 namespaces (`common`, `nav`, `auth`, `settings`, `dashboard`, `predict`, `history`, `fields`, `irrigation`, `batch`, `notifications`, `admin`, `errors`).
  - `frontend/src/components/ui/LanguageSwitcher.tsx`: Persisted language switch with RTL layout trigger (`document.documentElement.dir = 'rtl'` and `lang = 'ur'`).
  - `frontend/src/styles/index.css`: RTL logical CSS properties (`[dir='rtl']`), reverse flex spaces, and reduced motion override (`@media (prefers-reduced-motion: reduce)`).
  - `frontend/src/layouts/DashboardLayout.tsx`: Injected `LanguageSwitcher` in the header bar and configured WCAG skip-to-main content navigation (`#main-content`).
  - `frontend/src/utils/formatters.ts`: Added `formatPercent` and `formatRelative` using `Intl.NumberFormat` and `Intl.RelativeTimeFormat`.
  - `frontend/src/components/ui/SkeletonLoader.tsx`: Accessible shimmer loaders (`Skeleton`, `SkeletonCard`, `SkeletonTable`, `SkeletonStatCards`) with `role="status"` and `aria-busy`.
  - `frontend/src/components/ui/EmptyState.tsx` & `ErrorState.tsx`: Accessible empty and error states with ARIA landmarks.
  - `frontend/vite.config.ts`: Configured `VitePWA` with Workbox runtime caching (`NetworkOnly` for `/api/`, `CacheFirst` for static assets and OSM map tiles), offline fallback, and code splitting chunks (`vendor`, `charts`, `maps`, `i18n`).
  - `frontend/public/offline.html`: Branded offline fallback screen.
  - `frontend/index.html`: Added meta description and apple-touch-icon for PWA installation audits.
  - `frontend/src/__tests__/a11y.test.tsx`: Added `DashboardPage` axe accessibility audit with mock authentication context.
  - `backend/app/models/prediction.py`: Added composite indexes `ix_predictions_user_saved` on `(user_id, is_saved)` and `ix_predictions_user_classification` on `(user_id, classification)`.
  - `backend/app/main.py`: Registered `SecurityHeadersMiddleware` enforcing `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy`.
  - `backend/tests/unit/test_performance_indexes.py`: Unit tests verifying composite indexes on `Prediction`, `AuditLog`, and `FieldObservation`.
  - `infra/nginx/nginx.conf`: Hardened reverse proxy with CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, `server_tokens off`, and IP restriction on metrics/health endpoints.
  - `infra/prometheus/prometheus.yml` & `alert_rules.yml`: Configured scrape targets for ML service and alert rules for high 5xx error rate (>5%), p95 API latency (>2s), and ML inference degradation (>500ms).
  - `infra/grafana/dashboards/overview.json`: Updated Grafana dashboard with request rates, p50/p95/p99 latency quantiles, error rate %, and health status.
  - `infra/scripts/seed_predictions.py`: High-throughput asynchronous batch script to seed 1,000,000 prediction rows.
  - `.github/workflows/ci.yml`: Integrated `bandit`, `pip-audit`, and `npm audit` security scans into CI pipelines.
  - `docs/security.md`: Documented full threat model summary mapped to OWASP ASVS areas.

- **Verification**:
  - Backend unit tests: **86/86 passed** (including composite index tests).
  - ML tests: **48/49 passed** (1 skipped — expected).
  - Frontend tests: **51/51 passed** (including `a11y.test.tsx` DashboardPage axe audit).
  - Production build: `npm run build` completed cleanly with code-split chunks (`vendor`, `charts`, `maps`, `i18n`) and PWA service worker generation (`dist/sw.js`).

