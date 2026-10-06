# Persistent caching service

A FastAPI service that transforms two lists of strings, interleaves their results, and persists reusable transformations and generated payloads. A CLI exercises the API.

## Project status

Runnable foundation added: application lifecycle, health endpoints, database configuration, initial migration, and Docker Compose. Payload endpoints, transformation caching, and CLI are not implemented yet.

## Assessment assumptions

The task author delegated the payload identity and storage choices to us and asked that assumptions be documented here.

- **Payload identity:** identical ordered input lists under the same transformer version reuse the same identifier. Case, whitespace, list boundaries, duplicates and order are preserved. Different inputs may produce the same uppercase output and still receive different identifiers. This treats creation as a repeatable operation on a request without conflating distinct requests.
- **Payload storage:** complete generated payloads are stored in PostgreSQL and retrieved by identifier. No filesystem payload files are created. Keeping payloads and reusable transformations in one durable database simplifies atomic publication and multi-worker access.
- **Transformer:** deterministic uppercase conversion follows the sample. This remains our implementation assumption rather than an explicitly confirmed transformation contract.

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

Foundation verification passed on 2026-10-06: dependency resolution and `uv.lock` generation, Ruff, all three foundation tests (including real PostgreSQL readiness), Docker image build, clean migration revision `0001`, and both health endpoints. Approved execution outside the sandbox was required. If port 5432 is occupied, use `CACHE_DATABASE_PORT=55432 docker compose up --build -d` and point local database URLs at port 55432. Docker currently installs the version ranges from `pyproject.toml`; the local uv environment uses the lockfile.

The migration environment follows [Alembic's async migration recipe](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic). Migrations run explicitly; API workers do not create tables during startup.
