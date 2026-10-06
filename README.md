# Persistent caching service

A FastAPI service that transforms two lists of strings, interleaves their results, and persists reusable transformations and generated payloads. A CLI exercises the API.

## Project status

The foundation and payload endpoints are implemented: strict validation, uppercase transformation,
alternating composition, PostgreSQL storage, and reuse of identifiers for identical inputs.
Per-string transformation caching is implemented. Worker coordination and the CLI remain
planned work.

## Payload API

Create a payload:

```sh
curl -sS http://localhost:8000/payloads \
  -H 'Content-Type: application/json' \
  -d '{"list1":["hello","world"],"list2":["one","two"]}'
```

The response is `{"id":"<uuid>"}`. Read it with
`curl -sS http://localhost:8000/payloads/<uuid>` to obtain
`{"output":"HELLO, ONE, WORLD, TWO"}`. Repeating identical ordered input under the same
transformer version returns the stored identifier, including after application restart.
Concurrent publication also returns the stored winner's identifier; concurrent misses can
still repeat transformation until coordination is implemented.

Both lists must contain strings and have equal lengths. Two empty lists produce an empty
output. Unknown UUIDs return 404, and invalid input returns 422. Configurable input limits,
deadlines, and error responses are described in the [API contract](docs/api-contract.md).
Only complete outputs are published. Successful individual transformations are cached under
their exact source and transformer version, including after restart. Strings shared by different
payloads reuse those results, and duplicates within a request are transformed once. Successful
results survive a later transformer failure so retries only transform remaining misses. Cache
reads are batched; conflicting inserts use verified authoritative readback. Concurrent misses
can still repeat calls until advisory coordination is implemented in B10.

## Assessment assumptions

The task author delegated the payload identity and storage choices to us and asked that assumptions be documented here.

- **Payload identity:** identical ordered input lists under the same transformer version reuse the same identifier. Case, whitespace, list boundaries, duplicates and order are preserved. Different inputs may produce the same uppercase output and still receive different identifiers. This treats creation as a repeatable operation on a request without conflating distinct requests.
- **Payload storage:** complete generated payloads are stored in PostgreSQL and retrieved by identifier. No filesystem payload files are created. Keeping payloads and reusable transformations in one durable database simplifies atomic publication and multi-worker access.
- **Transformer:** deterministic uppercase conversion follows the sample. This remains our implementation assumption rather than an explicitly confirmed transformation contract.

## Engineering documentation

- [Implementation and submission backlog](docs/backlog.md)
- [Requirements and acceptance criteria](docs/requirements.md)
- [Payload API contract](docs/api-contract.md)
- [Architecture decisions](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Verification strategy](docs/verification.md)

## Start the foundation

From this directory, run:

```sh
python3 scripts/configure_local.py
docker compose up --build
```

Compose waits for PostgreSQL, runs migrations, then starts the API. Run the setup script once to generate local credentials in `.env`. `DB_USER`, `DB_NAME`, `DB_PASS`, `DB_HOST`, and `DB_PORT` configure local database access. Compose uses `DB_USER`, `DB_NAME`, and `DB_PASS` for the database and application containers; the application connects to `database:5432`, while `DB_PORT` selects the published host port. Both exposed ports bind to localhost; database storage persists in a named volume.

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
python3 scripts/configure_local.py  # once, before starting Compose
docker compose up -d database
uv sync
uv run alembic upgrade head
uv run uvicorn cache_service.main:create_app --factory
```

The application builds its connection URL from `DB_HOST` (default `127.0.0.1`), `DB_PORT` (5432), `DB_USER` (`cache`), `DB_NAME` (`cache`), and required `DB_PASS`. Credentials are URL-escaped and masked in diagnostics. An optional nonempty `DATABASE_URL` overrides these connection values, preserving existing local configurations; omit it when using separate `DB_*` settings. Compose supplies separate settings and does not forward that local override. Initial pool capacity is ten connections per process, with no overflow; connection checkout, connection establishment, and ordinary database statements each have a five-second budget. These are configurable starting values, not performance claims. Lock coordination will explicitly override the statement budget for lock acquisition in its short transaction.

## Verification

```sh
uv run ruff check .
uv run pytest -m 'not integration'
uv run python -c 'import os, subprocess, sys; from cache_service.config import Settings; os.environ["TEST_DATABASE_URL"] = Settings().database_url.get_secret_value(); raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-m", "integration"]))'
```

Integration tests require migrations to have been applied. They exercise readiness and payload
creation, reads, reuse, restart, publication conflicts, collisions, failure, and deadlines against
PostgreSQL. Without `TEST_DATABASE_URL`, they skip explicitly. Payload tests remove their own
uniquely marked rows; no test drops or recreates a database.

Foundation verification passed on 2026-10-06: dependency resolution and `uv.lock` generation, Ruff, all three foundation tests (including real PostgreSQL readiness), Docker image build, clean migration revision `0001`, and both health endpoints. Approved execution outside the sandbox was required. If port 5432 is occupied, use `DB_PORT=55432 docker compose up --build -d` and point local database URLs at port 55432. Docker currently installs the version ranges from `pyproject.toml`; the local uv environment uses the lockfile.

The migration environment follows [Alembic's async migration recipe](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic). Migrations run explicitly; API workers do not create tables during startup.

Keep `.env` out of Git and avoid printing connection strings or expanded Compose configuration. Settings mask the database URL in diagnostics. Changing `DB_PASS` in `.env` does not change the password in an existing PostgreSQL volume; update the database role when rotating credentials.

## Continuous integration

[CI workflow](.github/workflows/ci.yml) runs on every pull request and push to `main`. One Ubuntu job uses Python 3.12, uv 0.9.5, and the committed `uv.lock`. It runs these established commands:

```sh
uv sync --locked
make lint
make test
uv run alembic upgrade head
make test-integration
docker build --tag cache-service:ci .
```

CI sets `UV_PYTHON=3.12` and `UV_LOCKED=true`, so subsequent `uv run` commands also reject a stale lockfile. Application and migration settings use `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_NAME`, and `DB_PASS`, pointing to a health-checked PostgreSQL 17 service. The integration step derives `TEST_DATABASE_URL` from those same settings without printing it. Its disposable credentials are only for that run and require no repository secrets. For local checks, use your own migrated database URLs; avoid copying CI credentials into persistent environments.

The job has read-only repository permissions, a 15-minute timeout, and cancels superseded runs for the same branch or pull request. Checkout does not retain credentials. External actions are pinned to commit SHAs verified against their upstream release tags. See [setup-uv documentation](https://github.com/astral-sh/setup-uv/tree/v6.0.1) and [GitHub PostgreSQL service documentation](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).

Local acceptance evidence is recorded in the [backlog](docs/backlog.md#ci-acceptance-evidence). Workflow validation and local command success do not establish a successful GitHub Actions run. Docker build verification uses the existing Dockerfile, which installs dependency ranges rather than the uv lockfile.

## Database container environment boundary

Project configuration uses `DB_*` names, with no application-specific environment prefix. The [official PostgreSQL image](https://hub.docker.com/_/postgres) requires `POSTGRES_USER`, `POSTGRES_DB`, and `POSTGRES_PASSWORD` internally. Compose maps `DB_USER`, `DB_NAME`, and `DB_PASS` to those image keys; CI supplies matching disposable values at the same boundary. The application does not read the image-specific names. Existing volumes retain their database, role, and password: changing environment values does not rename them or rotate credentials.
