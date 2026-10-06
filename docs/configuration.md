# Configuration reference

Run commands from the repository root. Application settings read process environment first,
then `.env`, then defaults; explicit `Settings(...)` arguments take precedence. Names are
case-insensitive and have no prefix. Unknown `.env` entries are ignored. The CLI reads only
arguments and does not inherit application options from environment or `.env`.

## Database connection

| Setting | Default | Validation and use |
| --- | --- | --- |
| DB_HOST | `127.0.0.1` | Nonempty host for local Python |
| DB_PORT | `5432` | Integer from 1 to 65535; Compose uses it for the published host port |
| DB_USER | `cache` | Nonempty role name |
| DB_NAME | `cache` | Nonempty database name |
| DB_PASS | None | Required and nonempty unless DATABASE_URL is provided |
| DATABASE_URL | Empty | Optional full `postgresql+asyncpg` URL; overrides connection fields |

`python3 scripts/configure_local.py` creates `.env` with a random password and mode 0600,
without printing credentials or overwriting existing configuration. For a different host port,
use `python3 scripts/configure_local.py --database-port 55432` before first setup.
If `.env` already exists, update its port deliberately instead of rerunning the generator.
Local Python reads that port automatically. Credentials in generated URLs are escaped and masked.

Compose forwards DB_USER, DB_NAME, and DB_PASS to its API and migration containers, forcing
DB_HOST=`database` and DB_PORT=`5432` there. It maps the same credentials to the PostgreSQL
image's POSTGRES_* variables. Local DATABASE_URL overrides are not forwarded to containers.
Existing storage retains its original roles and passwords; editing `.env` does not rotate them.

## Capacity, input limits, and deadlines

The complete settings table and defaults are in the [API contract](api-contract.md#limits-and-deadlines).
POOL_SIZE is 2–100; COORDINATION_SLOTS must be at least 1 and lower than POOL_SIZE.
Input limits are positive integers. Timeouts are positive finite numbers, with advisory waiting
at least 0.001 seconds. Invalid settings prevent application creation. Configuration changes
require recreating the application or container; there is no runtime reload of settings.

For local Python, export an option or put it in `.env` before launching Uvicorn. Compose does
not forward pool, coordination, input-limit, or timeout settings from the host automatically.
To configure its API, create a local `compose.override.yaml`, for example:

```yaml
services:
  api:
    environment:
      POOL_SIZE: "6"
      COORDINATION_SLOTS: "4"
      MAX_LIST_ITEMS: "50"
```

Then run `docker compose up --build -d` to apply the merged configuration. Keep credentials
in `.env`; this override needs no secrets. Use `docker compose config --quiet` to validate
Compose without printing expanded credentials. The migration container does not need API limits.

Capacity is per worker: budget `workers × POOL_SIZE` connections plus migration and
administration capacity. Admission includes lock holders and waiters. Spare pool connections
allow ordinary operations to proceed in controlled saturation tests; they do not guarantee
read latency under arbitrary load. The defaults are starting budgets, not performance targets.

The built-in transformer version is `uppercase-v1`, defined in `identity.py`. It is an
implementation constant, not an environment setting. The app factory accepts a replacement
async transformer and version for integrations and tests. Change the version when semantics
change; previously committed payloads remain readable, and old cache records are not deleted.
