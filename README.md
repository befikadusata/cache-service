# Persistent caching service

A FastAPI service that transforms two lists of strings, interleaves their results, and persists reusable transformations and generated payloads. A CLI exercises the API.

## Project status

Runnable foundation added: application lifecycle, health endpoints, database configuration, initial migration, and Docker Compose. Payload endpoints, transformation caching, and CLI are not implemented yet. Payload identity and payload storage assumptions remain subject to clarification from the task author.

## Engineering documentation

- [Implementation and submission backlog](docs/backlog.md)
- [Requirements and acceptance criteria](docs/requirements.md)
- [Architecture decisions](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Verification strategy](docs/verification.md)

## Start the foundation

From this directory, run:

```sh
docker compose up --build
```

Compose waits for PostgreSQL, runs migrations in a separate process, then starts the API. Local development credentials in Compose are intentionally public and must be replaced for deployment. Both exposed ports bind to localhost. Database storage persists in a named volume.

- `GET http://localhost:8000/health/live` checks application responsiveness.
- `GET http://localhost:8000/health/ready` checks database connectivity and both initial tables; it returns 503 when unavailable.
- Interactive API documentation is at `http://localhost:8000/docs`.

Stop with `docker compose down`. Removing the named volume deletes stored data.

## Command shortcuts

An optional Makefile provides `make up`, `make down`, `make logs`, `make test`, `make test-integration`, `make lint`, and `make migrate`. Run `make help` to list them. Run these commands from this directory.

`make up` starts Compose in the background. `make migrate` applies migrations through the Compose migration service; local Python development uses `uv run alembic upgrade head`. Integration tests require an exported `TEST_DATABASE_URL` pointing to a migrated database. Stopping containers preserves the database volume.

The direct commands in this guide remain available without Make.

## Local Python development

Requires Python 3.12–3.14 and uv. Start PostgreSQL first:

```sh
docker compose up -d database
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn cache_service.main:create_app --factory
```

The application requires `CACHE_DATABASE_URL`. Initial pool capacity is ten connections per process, with no overflow; connection checkout, connection establishment, and ordinary database statements each have a five-second budget. These are configurable starting values, not performance claims. Lock coordination will explicitly override the statement budget for lock acquisition in its short transaction.

## Verification

```sh
uv run ruff check .
uv run pytest -m 'not integration'
TEST_DATABASE_URL=postgresql+asyncpg://cache:local-development-only@localhost:5432/cache uv run pytest -m integration
```

The integration test requires migrations to have been applied. It exercises actual API readiness against PostgreSQL. Without `TEST_DATABASE_URL`, it skips explicitly. No test drops or recreates a database.

Foundation verification in the assessment workspace: Python compilation and Compose configuration validation passed. Dependency resolution could not complete because outbound DNS/network access is restricted; Docker daemon access and local PostgreSQL listening sockets are also restricted. Therefore runtime tests, migrations against a live server, and image builds remain unverified. A dependency lockfile will be generated when package resolution is available.

The migration environment follows [Alembic's async migration recipe](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic). Migrations run explicitly; API workers do not create tables during startup.
