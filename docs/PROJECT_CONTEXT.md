# AgriScope Project Context

## A. VISION
Users estimate ET three ways: (a) manual input of temperature, humidity, wind speed, solar radiation; (b) location-based, picking a point or field polygon on a map with weather fetched automatically; (c) remote sensing, deriving NDVI/EVI from satellite imagery for a field polygon and combining with ET0 and a crop coefficient to estimate crop ET (ETc). Results become actionable: ET trends, 7-day forecast, crop water requirement, irrigation schedule, explainability, exportable reports. Admins manage users, datasets, the full ML model lifecycle, and system health.

## B. ROLES AND PLANS
- Free: single predictions, last 50 in history, basic charts, 1 field, 30 predictions/day, no export.
- Pro/Researcher: batch CSV (≤10k rows), unlimited history, multiple fields, remote sensing, forecasts, model comparison, explainability, exports (CSV/XLSX/PNG/PDF), API keys, higher quotas.
- Admin: everything plus the admin console.
All limits come from one entitlement module (`plans.py`). Billing uses a `BillingProvider` interface (Stripe test mode + mock default).

## C. TECH STACK (fixed)
Frontend: React 18 + TypeScript + Vite, Tailwind, Radix/shadcn, TanStack Query, React Router, React Hook Form + Zod, Recharts, Leaflet + react-leaflet + leaflet-draw, i18next (English + Urdu RTL), vite-plugin-pwa, dark mode.
API: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic.
ML: separate FastAPI inference service plus an installable package `agriscope_ml` (scikit-learn, XGBoost/LightGBM, MLP, SHAP, conformal intervals via MAPIE or equivalent, joblib, pandas, numpy).
Workers: Celery + Redis (+ beat).
Data: PostgreSQL 16 + PostGIS, Redis, MinIO (S3-compatible).
Auth: JWT access (15 min) + rotating refresh token in httpOnly secure cookie, bcrypt (12 rounds), optional TOTP 2FA.
Email: SMTP provider interface (Mailpit in dev).
Observability: JSON logs, Prometheus, Grafana, env-gated Sentry, health/readiness endpoints.
Infra: Docker, docker-compose (dev + prod), Nginx, GitHub Actions.
Tests: pytest + pytest-cov, Vitest + Testing Library, Playwright, Locust.

## D. DIRECTORY STRUCTURE (authoritative; never invent alternatives)
```text
agriscope/
├── README.md, Makefile, docker-compose.yml, docker-compose.prod.yml, .env.example, .gitignore, .editorconfig, .pre-commit-config.yaml
├── .github/workflows/ (ci.yml, cd.yml)
├── docs/ (PROJECT_CONTEXT.md, PROGRESS.md, architecture.md, api.md, ml-model.md, remote-sensing.md, security.md, deployment.md, decisions.md, user-guide.md)
├── infra/ (nginx/nginx.conf, prometheus/prometheus.yml, grafana/{provisioning,dashboards}, scripts/{backup.sh,restore.sh,seed.sh})
├── backend/
│   ├── Dockerfile, requirements/{base.txt,dev.txt}, pyproject.toml, alembic.ini, alembic/versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/ (config, security, deps, exceptions, rate_limit, logging, plans)
│   │   ├── db/ (base, session, init_db, seeds/crops.json)
│   │   ├── models/ (user, session, audit_log, prediction, batch_job, field, field_observation, crop, irrigation_event, ml_model, training_dataset, shadow_result, notification, api_key, report, subscription, feature_flag, announcement)
│   │   ├── schemas/ (mirrors models + common)
│   │   ├── routers/v1/ (auth, users, predict, batch, history, fields, remote_sensing, crops, irrigation, weather, reports, notifications, api_keys, billing, admin/{users,datasets,models,metrics,audit,system})
│   │   ├── services/ (one per domain; all business logic)
│   │   ├── providers/ (weather/{nasa_power,open_meteo}, satellite/{stac_sentinel,gee,mock}, billing/{stripe,mock}, email/smtp, storage/minio)
│   │   ├── workers/ (celery_app.py, tasks/{training,batch,satellite,reports,emails}.py, schedules.py)
│   │   ├── realtime/sse.py
│   │   └── utils/
│   └── tests/ (conftest.py, unit/, integration/, fixtures/)
├── ml/
│   ├── Dockerfile, pyproject.toml
│   ├── agriscope_ml/ (data/{nasa_power,synthetic,datasets}.py, physics/{penman_monteith,crop_coefficients}.py, features.py, pipelines.py, train.py, evaluate.py, tuning.py, uncertainty.py, explain.py, drift.py, registry.py, model_card.py, cli.py)
│   ├── service/ (main.py, routers/, schemas/)
│   ├── artifacts/.gitkeep
│   └── tests/
├── frontend/
│   ├── Dockerfile, package.json, tsconfig.json, vite.config.ts, tailwind.config.ts, .eslintrc.cjs, .prettierrc, index.html, public/{manifest, icons, locales/{en,ur}}
│   └── src/ (main.tsx, App.tsx, api/, hooks/, context/, routes/{ProtectedRoute,RoleRoute,PlanRoute}, layouts/, i18n/, store/, types/, pages/{auth,dashboard,predict,batch,fields,remote-sensing,irrigation,history,reports,notifications,settings/{profile,security,api-keys,billing},admin/{overview,users,datasets,models,reports,system}}, components/{ui,charts,maps,forms,tables,feedback,admin}, utils/ (constants.ts = single source of validation ranges), styles/, __tests__/)
├── e2e/ (playwright.config.ts, tests/)
└── loadtests/locustfile.py
```

## E. ARCHITECTURE RULES
- Dependency direction: routers → services → (models, providers, ml client). Routers contain no business logic.
- `agriscope_ml` imports nothing from FastAPI, SQLAlchemy, or the backend app.
- External systems (weather, satellite, billing, email, storage) are reachable only via provider interfaces, each with a mock selectable by env var. The project must run fully offline.
- One concern per file, ≤300 lines. snake_case Python, PascalCase React components, camelCase TS utilities/hooks. Tests mirror source layout.
- Components never call axios/fetch directly; only via `api/` modules and TanStack Query hooks.
- Validation ranges defined once per side: temperature -10..50 °C, humidity 0..100 %, wind 0..30 m/s, solar radiation 0..35 MJ/m²/day.
- API: /api/v1, JSON, error format {detail, code, request_id}, request-ID middleware, per-route rate limits.
- Account lockout: 5 consecutive failures → `locked_until` = now+15 min (auto-unlock, never a permanent suspended state).
- Classification: Low <2, Moderate 2–5, High >5 mm/day.

## F. DATA HONESTY RULES
Never present synthetic data as real. Every model card and the UI shows a "trained on: real-derived / synthetic" badge. Real data comes from NASA POWER with ET0 computed by a unit-tested FAO-56 Penman-Monteith implementation; synthetic is a labelled offline fallback only. Any mock satellite/weather/billing provider is clearly labelled in the UI when active.

## G. STANDARD TASK PROTOCOL (applies to every task)
1. Read docs/PROJECT_CONTEXT.md and docs/PROGRESS.md first.
2. Implement only the current task, following the structure above exactly. Stub nothing that the task lists as required.
3. Write tests for everything you add; run them plus lint and type checks; fix all failures.
4. Update the relevant docs in the same task.
5. Append to docs/PROGRESS.md: task number/name, what was built, files added, how to run/verify, known gaps.
6. Record non-obvious choices in docs/decisions.md.
7. Finish with: a summary, exact run/verify commands, and the output of `tree -L 3` for any new folders.
8. Do not refactor or alter completed work except to fix bugs or satisfy the current task; if you must, say so explicitly.
