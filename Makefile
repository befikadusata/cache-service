.DEFAULT_GOAL := help

.PHONY: help up down logs test test-integration lint migrate

help:
	@echo "up                Build and start the service and PostgreSQL"
	@echo "down              Stop containers (preserves database storage)"
	@echo "logs              Follow container logs"
	@echo "test              Run local tests without PostgreSQL"
	@echo "test-integration  Run database tests (requires TEST_DATABASE_URL)"
	@echo "lint              Check Python code with Ruff"
	@echo "migrate           Apply migrations using Compose"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs --follow

test:
	uv run pytest -m 'not integration'

test-integration:
	@test -n "$$TEST_DATABASE_URL" || { echo "Set TEST_DATABASE_URL to a migrated PostgreSQL database" >&2; exit 1; }
	uv run pytest -m integration

lint:
	uv run ruff check .

migrate:
	docker compose run --rm migrate
