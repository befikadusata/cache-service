# Repository Guidelines

## Project Structure & Module Organization

This Python 3.12–3.14 project provides a FastAPI service backed by PostgreSQL. Source lives in `src/cache_service/`: `main.py` defines the application and health endpoints, `config.py` validates settings, and `database.py` configures the async engine. Alembic revisions belong in `migrations/versions/`; tests live in `tests/`. Consult `docs/architecture.md`, `docs/requirements.md`, and `docs/backlog.md` before changing behavior. Payload endpoints, transformation caching, and the CLI remain planned work.

## Build, Test, and Development Commands

Run commands from the repository root:

- `python3 scripts/configure_local.py`: generate local credentials in `.env` before first startup.
- `uv sync --locked`: install dependencies from `uv.lock`.
- `make up`: build and start the API, migrations, and PostgreSQL through Compose.
- `make down` / `make logs`: stop containers while preserving storage, or follow logs.
- `uv run alembic upgrade head`: apply migrations to the configured local database.
- `uv run uvicorn cache_service.main:create_app --factory`: run the API locally with PostgreSQL available.
- `make lint`: run Ruff checks.
- `make test`: run tests that do not require PostgreSQL.
- `make test-integration`: run database tests with exported `TEST_DATABASE_URL` pointing to a migrated database.

## Coding Style & Naming Conventions

Use four-space indentation, descriptive `snake_case` functions and modules, and `PascalCase` classes. Add type annotations consistent with existing code. Ruff targets Python 3.12 with a 100-character line limit and checks errors, imports, modern syntax, and common bugs. Keep dependency changes synchronized with `uv.lock`; add schema changes as Alembic revisions rather than creating tables during API startup.

## Testing Guidelines

Use pytest and pytest-asyncio; name files `test_*.py` and functions `test_*`. Mark PostgreSQL-dependent tests with `@pytest.mark.integration`. No numeric coverage threshold is configured. Cover observable behavior and failure paths; follow `docs/verification.md` for persistence, concurrency, and cache guarantees. Record executed checks accurately. CI also applies migrations and builds the Docker image.

## Commit & Pull Request Guidelines

Recent commits use concise imperative subjects, such as `Add minimal GitHub Actions CI`, without mandatory prefixes. Follow that style. PR descriptions should explain the behavior change, relevant backlog items or issues, and validation commands with outcomes. Update documentation when assumptions or configuration change.

## Security & Configuration

Keep `.env` and credentials out of Git. Never print database URLs or expanded Compose configuration. Preserve masked settings diagnostics. Removing the PostgreSQL volume deletes stored data.
