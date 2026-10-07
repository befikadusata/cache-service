# Persistent caching service

A FastAPI service that uppercases two lists of strings, interleaves their results,
and stores the generated payloads in PostgreSQL. Successful string transformations
are cached across requests and application restarts. A CLI creates and retrieves
payloads through the API.

For example, `{"list1":["hello","world"],"list2":["one","two"]}` produces
`HELLO, ONE, WORLD, TWO`. Submitting the same ordered input again returns the same
payload identifier.

## Quick start

Requires Python 3 to generate local credentials and Docker with the Compose plugin.
Run commands from the repository root:

```sh
python3 scripts/configure_local.py
docker compose up --build -d
```

Run the setup script once. It creates an ignored `.env` file with a random database
password and preserves any existing configuration. Compose starts PostgreSQL,
applies Alembic migrations, then starts the API.

- [Interactive API documentation](http://localhost:8000/docs)
- [Liveness check](http://localhost:8000/health/live): application responsiveness
- [Readiness check](http://localhost:8000/health/ready): database connectivity and required tables

Follow logs with `docker compose logs --follow`. Stop with `docker compose down`;
the named database volume preserves committed payloads and cached transformations.
Removing that volume deletes the stored data. Published API and database ports bind
to localhost.

If database port 5432 is occupied, use
`python3 scripts/configure_local.py --database-port 55432` during first setup.
For existing configuration, update `DB_PORT` in `.env` before starting Compose.

## Payload API

Create a payload:

```sh
curl -sS http://localhost:8000/payloads \
  -H 'Content-Type: application/json' \
  -d '{"list1":["hello","world"],"list2":["one","two"]}'
```

The response contains its identifier:

```json
{"id":"550e8400-e29b-41d4-a716-446655440000"}
```

Retrieve the output using the identifier returned by your request:

```sh
PAYLOAD_ID='replace-with-the-id-returned-above'
curl -sS "http://localhost:8000/payloads/$PAYLOAD_ID"
```

```json
{"output":"HELLO, ONE, WORLD, TWO"}
```

Both lists must contain strings and have equal lengths. Empty lists produce an empty
output. Creation and reuse return HTTP 200; invalid input returns 422, and an unknown
UUID returns 404. By default, each list allows 100 items, each string allows 10,000
characters, and both lists together allow 100,000 characters.

See the [API contract](docs/api-contract.md) for validation, configurable limits,
deadlines, and error responses.

## CLI usage

Requires Python 3.12–3.14 and uv. With the API running, install the locked dependencies:

```sh
uv sync --locked
uv run cache-service --json '{"list1":["hello","world"],"list2":["one","two"]}' --repeat 2
```

Each repeat sends one create request followed by one read request, then writes a
JSON Lines record to stdout. Identical requests reuse the ID; each successful repeat
still emits a record:

```json
{"id":"550e8400-e29b-41d4-a716-446655440000","output":"HELLO, ONE, WORLD, TWO"}
```

| Option | Description | Default |
| --- | --- | --- |
| `--host` | HTTP/HTTPS service base URL | `http://127.0.0.1:8000` |
| `--repeat` | Positive number of create/read iterations | `1` |
| `--json` | Inline input JSON; exclusive with `--input` | Required unless `--input` is set |
| `--input` | UTF-8 JSON file, or `-` for stdin | Required unless `--json` is set |
| `--output` | JSON Lines output file, or `-` for stdout | `-` |
| `-h`, `--help` | Show usage | — |

Save the example input as `payload.json` to use a file or stdin:

```sh
uv run cache-service --input payload.json --output results.jsonl
uv run cache-service --input - --host http://127.0.0.1:8000 < payload.json
uv run cache-service --help
```

CLI options come from arguments; environment variables and `.env` do not supply them.
Input is validated before requests or output-file creation. Output files are overwritten.
Errors go to stderr and stop execution with a nonzero status; earlier complete records
remain available. There are no automatic retries. A failed CLI request may still have
created a payload on the server.

## Assessment assumptions

The implementation makes the following assumptions where the assessment leaves behavior open:

- **Payload identity:** identical ordered input lists under the same transformer version
  reuse one identifier. Case, whitespace, list boundaries, duplicates, and order matter.
  Different inputs can produce the same output and still have different identifiers.
- **Payload storage:** complete payloads and reusable transformations are stored in
  PostgreSQL. Payloads are retrieved by identifier; no payload files are written.
  A shared database supports durable storage and atomic publication across workers.
- **Transformation:** deterministic Python Unicode uppercase conversion follows the
  supplied example. This is an implementation assumption. A replacement transformer
  must use a new version when its semantics change.

## Local development

Requires Python 3.12–3.14, uv, and PostgreSQL. To run the API locally with the Compose database:

```sh
python3 scripts/configure_local.py  # first setup only
docker compose up -d database
uv sync --locked
uv run alembic upgrade head
uv run uvicorn cache_service.main:create_app --factory
```

Application settings read environment variables and `.env`. Database configuration uses
`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_NAME`, and `DB_PASS`; an optional `DATABASE_URL`
overrides them for local Python execution. Compose connects its application containers to
`database:5432` regardless of the published host port.

Keep `.env` out of Git. Changing its password does not rotate credentials in an existing
database volume. See the [configuration reference](docs/configuration.md) for settings,
Compose overrides, and worker connection budgets.

Source lives in [`src/cache_service/`](src/cache_service/), migrations in
[`migrations/versions/`](migrations/versions/), and tests in [`tests/`](tests/).
Schema changes use Alembic migrations; API startup does not create tables.
Run `make help` for optional command shortcuts.

## Testing

```sh
uv run ruff check .
uv run pytest -m 'not integration'
```

Integration tests require a migrated PostgreSQL database. To use the database configured
by your local application settings without printing its credentials:

```sh
uv run alembic upgrade head
uv run python - <<'PYTHON'
import os
import subprocess
import sys

from cache_service.config import Settings

os.environ["TEST_DATABASE_URL"] = Settings().database_url.get_secret_value()
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-m", "integration"]))
PYTHON
```

If `TEST_DATABASE_URL` is already exported, run `make test-integration` instead.
Integration tests skip when that variable is absent. Tests cover persistence, cache reuse,
concurrent requests, failure recovery, and the CLI against a live API.
The [verification guide](docs/verification.md) maps guarantees to tests and documents
an isolated Docker deployment check.

## Continuous integration

The [GitHub Actions workflow](.github/workflows/ci.yml) checks pull requests and pushes
to `main`. It installs locked dependencies, runs Ruff and unit tests, applies migrations
to PostgreSQL 17, runs integration tests, and builds the Docker image.
Local development and CI use `uv.lock`; the Dockerfile installs dependency ranges
from `pyproject.toml`.

## Guarantees and limitations

Successful transformations are reused across payloads and retained when later work fails.
Only complete payloads are published. PostgreSQL advisory locks coordinate shared missing
strings across cooperating workers, with bounded waits and request deadlines. Crashes or
connection loss can cause repeated transformation calls; exactly-once external execution
is not guaranteed.

Missing strings are processed sequentially, holding a database connection during each
transformation. Direct PostgreSQL connections are required; transaction-mode PgBouncer is
unsupported. Controlled concurrency tests establish correctness, not production throughput.

Inputs and outputs are stored in plaintext. The service has no authentication, automatic
expiry, deletion API, or raw request-body byte limit. Character limits apply after JSON
parsing, and validation errors may include submitted values. Backup and restore are outside
the current verification scope.

## Documentation

- [API contract](docs/api-contract.md): request schemas, responses, limits, and deadlines
- [Configuration](docs/configuration.md): database settings and deployment capacity
- [Architecture](docs/architecture.md): cache identity, transactions, and coordination
- [Verification](docs/verification.md): test coverage and deployment checks
- [Requirements](docs/requirements.md): assessment requirements and acceptance criteria
