# ============================================================================
# Agent Paperpal — Makefile
# Single-command local dev environment management
# ============================================================================

.PHONY: dev test migrate lint logs clean build stop restart shell

# ── Primary Commands ────────────────────────────────────────────────────────

dev: ## Start full dev environment
	@echo "🚀 Starting Agent Paperpal dev stack..."
	cp -n .env.example .env 2>/dev/null || true
	docker-compose up -d --build
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 8
	docker-compose exec backend alembic upgrade head
	@echo ""
	@echo "✅ Agent Paperpal is running!"
	@echo "   Backend API:    http://localhost:8000/api/v1/health"
	@echo "   Frontend:       http://localhost:5173"
	@echo "   MinIO Console:  http://localhost:9001"
	@echo "   PostgreSQL:     localhost:5432"
	@echo "   Redis:          localhost:6379"

stop: ## Stop all services
	docker-compose stop

restart: ## Restart all services
	docker-compose restart

build: ## Rebuild all containers
	docker-compose build --no-cache

# ── Database ────────────────────────────────────────────────────────────────

migrate: ## Run Alembic migrations (upgrade head)
	docker-compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add_column")
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade: ## Downgrade one migration
	docker-compose exec backend alembic downgrade -1

# ── Testing ─────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests with pytest
	docker-compose exec backend python -m pytest tests/ -v --tb=short

test-frontend: ## Run frontend tests with vitest
	docker-compose exec frontend npx vitest run --reporter=verbose

# ── Linting ─────────────────────────────────────────────────────────────────

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend with ruff
	docker-compose exec backend ruff check app/ tests/

lint-frontend: ## Lint frontend with eslint
	docker-compose exec frontend npx eslint src/ --ext .js,.jsx,.ts,.tsx

format: ## Auto-format backend code with ruff
	docker-compose exec backend ruff format app/ tests/

# ── Logging & Debugging ────────────────────────────────────────────────────

logs: ## Tail backend + celery logs
	docker-compose logs -f backend celery_worker

logs-all: ## Tail ALL service logs
	docker-compose logs -f

shell: ## Open a shell in the backend container
	docker-compose exec backend /bin/bash

# ── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Stop containers and remove volumes
	@echo "🧹 Cleaning up Agent Paperpal..."
	docker-compose down -v --remove-orphans
	@echo "✅ All containers and volumes removed."

# ── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
