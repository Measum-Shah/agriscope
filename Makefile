.PHONY: help up down logs migrate seed test lint fmt e2e load train

help:
	@echo "AgriScope Makefile targets:"
	@echo "  make up       - Start all containers in development mode"
	@echo "  make down     - Stop all running containers"
	@echo "  make logs     - Follow logs from docker compose"
	@echo "  make migrate  - Run database migrations"
	@echo "  make seed     - Seed initial database data"
	@echo "  make test     - Run all unit and integration tests (backend, ml, frontend)"
	@echo "  make lint     - Run linters across python and frontend"
	@echo "  make fmt      - Auto-format backend, ml, and frontend code"
	@echo "  make train    - Train and register all ML models with agriscope-ml"
	@echo "  make e2e      - Run Playwright end-to-end tests"
	@echo "  make load     - Run Locust load testing suite"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.db.init_db

test:
	@echo "==> Running Backend Tests..."
	cd backend && pytest
	@echo "==> Running ML Tests..."
	cd ml && pytest
	@echo "==> Running Frontend Tests..."
	cd frontend && npm run test

lint:
	@echo "==> Linting Backend..."
	cd backend && ruff check app tests && black --check app tests
	@echo "==> Linting ML..."
	cd ml && ruff check agriscope_ml service tests && black --check agriscope_ml service tests
	@echo "==> Linting Frontend..."
	cd frontend && npm run lint && npm run type-check

fmt:
	@echo "==> Formatting Backend..."
	cd backend && ruff check --fix app tests && black app tests
	@echo "==> Formatting ML..."
	cd ml && ruff check --fix agriscope_ml service tests && black agriscope_ml service tests
	@echo "==> Formatting Frontend..."
	cd frontend && npm run format

e2e:
	cd e2e && npx playwright test

load:
	cd loadtests && locust -f locustfile.py --headless -u 10 -r 2 --run-time 30s --host http://localhost:8000

train:
	@echo "==> Training and Registering AgriScope ML Models..."
	cd ml && python -m agriscope_ml.cli train --algorithm all --schema basic --version v1.0
