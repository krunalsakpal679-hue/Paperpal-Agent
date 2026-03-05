# ============================================================================
# Agent Paperpal — Makefile
# Single-command local dev environment management
# ============================================================================

.PHONY: install dev-backend dev-frontend dev-celery dev migrate lint test format help

# ── Primary Commands ────────────────────────────────────────────────────────

install: ## Install all dependencies (Backend and Frontend)
	@echo "🚀 Installing dependencies..."
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev-backend: ## Start Backend dev server
	cd backend && uvicorn app.main:app --reload

dev-frontend: ## Start Frontend dev server
	cd frontend && npm run dev

dev-celery: ## Start Celery worker
	cd backend && celery -A app.core.celery_app worker --loglevel=info

dev: ## Local Dev instructions
	@echo "Without Docker, please run the following commands in separate terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-celery"
	@echo "  make dev-frontend"
	@echo ""
	@echo "Ensure PostgreSQL and Redis are running natively on your system!"

# ── Database ────────────────────────────────────────────────────────────────

migrate: ## Run Alembic migrations (upgrade head)
	cd backend && python -m alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add_column")
	cd backend && python -m alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade: ## Downgrade one migration
	cd backend && python -m alembic downgrade -1

# ── Testing ─────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests with pytest
	cd backend && python -m pytest tests/ -v --tb=short

test-frontend: ## Run frontend tests with vitest
	cd frontend && npx vitest run --reporter=verbose

# ── Linting ─────────────────────────────────────────────────────────────────

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend with ruff
	cd backend && ruff check app/ tests/

lint-frontend: ## Lint frontend with eslint
	cd frontend && npx eslint src/ --ext .js,.jsx,.ts,.tsx

format: ## Auto-format backend code with ruff
	cd backend && ruff format app/ tests/

# ── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
