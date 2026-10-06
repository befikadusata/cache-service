# Implementation and submission backlog

This backlog tracks the assessment from requirements through submission. It is the authoritative work status; the implementation plan describes sequencing, architecture explains decisions, and verification describes test scenarios. Written code is not complete until its acceptance evidence passes.

## Status and update rules

- **Done**: acceptance evidence has been checked and recorded.
- **Written**: artifacts exist, but required runtime evidence is pending.
- **Ready**: work can start with the current assumptions.
- **Waiting**: clarification or a predecessor is pending.
- **Blocked**: an external restriction prevents the next check or action.

For each implementation change, update the affected item, add code or test links and the commit, and record executed verification. Keep failed checks visible until resolved. A commit alone does not prove acceptance. Any changed requirement must update its mapped items and tests. The task author delegated identity and storage choices; use the assumptions recorded in the README and revisit affected items if new instructions arrive.

## Personal preparation alongside implementation

Personal preparation lives at `../private-preparation/`, resolved relative to the `cache-service/` repository root. It is a sibling directory outside Git. Personal content must stay there; public documentation retains the technical reasoning needed to maintain the service.

When a work item introduces a consequential decision, an unfamiliar concept, a failure mechanism, or a likely live modification, write or update the relevant personal material in the same development step. Routine changes do not need duplicate notes. Keep explanations consistent with the current code and revise them when the design changes.

| Trigger and work items | Personal destination | Required content when applicable |
| --- | --- | --- |
| Alternatives, identity, versioning and architecture decisions; B01, B04–B05, B09–B12 | `../private-preparation/learning/design-options.md` | Alternatives, trade-offs, selected rationale, limitations and reasons to reconsider |
| Foundation and setup; B02–B03 | `../private-preparation/learning/foundation.md` | Lifecycle, migrations, connections and actual verification limits |
| New request flow, caching, concurrency or CLI concepts; B06–B17 | `../private-preparation/learning/` | Plain-language execution trace, important code references and failure behavior |
| Debugging, operational checks or likely live changes; B03, B11, B13–B14, B17–B18 | `../private-preparation/cookbooks/` | Reproducible exercise, expected result, explanation and recovery steps |
| Collaboration preferences or AI working instructions change | `../private-preparation/instructions/working-agreement.md` | Updated working rules and personal preferences |
| Explanation practice, final review and video; B19–B22 | `../private-preparation/interview/` | Walkthrough outline, defense questions and live-change rehearsal |
| Actual hours and submission preparation; B23–B24 | `../private-preparation/` | Honest time log and private submission preparation; no invented historical totals |

Before closing an applicable item, check that its personal explanation reflects the implemented behavior and can support a code walkthrough. Track completion here only at the level of “personal notes updated”; do not copy personal content into this public backlog. Private preparation is a collaboration requirement, not an additional assessment requirement.

## Requirement coverage

| ID | Assessment requirement | Work items |
| --- | --- | --- |
| R01 | FastAPI creation and read endpoints | B04, B07, B08 |
| R02 | Two equal-length string lists, transformation and interleaving | B04, B06, B07 |
| R03 | Persistent transformer caching and minimized calls | B09, B10, B11, B13, B14 |
| R04 | Reuse generated payload identifiers | B05, B07, B12, B14 |
| R05 | SQLite or PostgreSQL with SQLAlchemy or SQLModel | B02, B03, B07, B09 |
| R06 | Docker deployment | B02, B03, B18 |
| R07 | CLI parsing and validation with Pydantic Settings | B15, B16, B17 |
| R08 | CLI host, repeat, file or stdin, inline JSON, file or stdout, help | B01, B15, B16, B17 |
| R09 | Unit and integration tests | B03, B06, B08, B13, B14, B17, B18, B20 |
| R10 | Communicate ambiguities, explain shortcuts, maintain clear code | B01, B19, B20 |
| R11 | Small meaningful Git commits, neutral public repository, preserved history | B21, B24 |
| R12 | English video up to 15 minutes, camera and screen, code trace, CLI and tests | B22, B24 |
| R13 | Reply with repository and video links and actual hours | B23, B24 |

## Work items

Dependencies identify the required predecessor, rather than requiring every earlier numbered item to finish first.

| ID | Work and acceptance evidence | Status | Dependencies | Current artifacts or evidence |
| --- | --- | --- | --- | --- |
| B01 | Record author response, identity/storage choices and transformer assumption; resolve CLI flag conflict and output format | Ready | None | Author delegated identity/storage; [README assumptions](../README.md#assessment-assumptions) recorded; uppercase assumption and help alias documented; CLI output format pending |
| B02 | Application lifecycle, PostgreSQL configuration, migration and Compose; inspect setup artifacts | Done | None | [Application](../src/cache_service/main.py), [migration](../migrations/versions/0001_initial.py), [Compose](../compose.yaml); commit `6a492e7` |
| B03 | Install dependencies, generate lockfile, run lint and foundation tests, apply clean migration, check both health endpoints and image startup | Done | B02; execution/network access | Runtime checks passed on 2026-10-06; `uv.lock` generated; PostgreSQL host port 55432; see verification record below; personal notes updated |
| B04 | Freeze POST and GET response schemas, strict input validation, empty behavior, configurable limits and request deadlines | Done | Selected B01 assumptions | [Contract](api-contract.md), [models](../src/cache_service/schemas.py), [settings](../src/cache_service/config.py), [tests](../tests/test_schemas.py); 18 focused tests and Ruff passed; personal notes updated; commit titled `Define payload API contract and validation`. Endpoint enforcement remains B07/B11 |
| B05 | Define canonical encoding, version and digest identities; verify list boundaries, order, whitespace and collision handling | Ready | B04 | Design in [architecture](architecture.md); implementation pending |
| B06 | Replaceable uppercase transformer and alternating composition; meaningful isolated tests | Ready | B04 | Sample output and empty input policy in requirements |
| B07 | Create and read complete payloads; generated UUID plus unique input digest; duplicate creation returns stored ID | Waiting | B03–B06 | Initial schema written; request flow pending |
| B08 | API tests for sample output, invalid types/lengths, empty input, unknown ID, retry and identity policy | Waiting | B07 | [Verification scenarios](verification.md) |
| B09 | Batch cache reads and request deduplication; persist successful results with versioned keys and authoritative readback | Waiting | B03, B05, B06 | Implementation pending |
| B10 | One advisory lock at a time, recheck after acquire, same connection for writes; no transaction over external call | Waiting | B09 | Coordination design recorded; implementation pending |
| B11 | Bounded admission and waits, cancellation-safe cleanup, invalidate uncertain ownership; map operational failures to documented HTTP responses | Waiting | B10, B04 | Numeric budgets and cleanup code pending |
| B12 | Preserve successful transformations on later failure; publish complete payload atomically; verify safe retries | Waiting | B07, B09–B11 | Policy recorded; implementation pending |
| B13 | Real PostgreSQL tests for timeout, cancellation, saturation, lock loss, collisions, version changes and no open transaction during transform | Waiting | B11, B12 | Controlled synchronization and exact assertions pending |
| B14 | Multi-process identical and overlapping requests; call counts per distinct string, consistent IDs and restart reuse | Waiting | B12 | Test instrumentation pending; single-process evidence insufficient |
| B15 | Pydantic Settings CLI parsing; host, repeat and mutually exclusive input source validation; resolve help alias | Waiting | B01 output policy; B04 | Parsing implementation pending |
| B16 | CLI create/read loop, file/stdin/JSON input, file/stdout output, stderr diagnostics and nonzero failure exit | Waiting | B07, B15 | Implementation pending |
| B17 | CLI parsing and I/O tests plus a real-service integration scenario | Waiting | B16 | Tests pending |
| B18 | Clean Docker build and migration/start smoke test; storage reuse after restart; document supported worker/connection budget | Waiting | B03, B12, B17 | Compose exists; runtime deployment evidence pending |
| B19 | Complete public setup, usage, configuration, architecture and limitations; reconcile every guarantee with tests | Waiting | B14, B17, B18 | Public docs exist; final usage and evidence pending |
| B20 | Final code review and requirement audit; full required suite passes; remove unnecessary complexity and inspect repository contents | Waiting | B13, B14, B17–B19 | Final review pending |
| B21 | Preserve real incremental commits; verify neutral repository name and public artifacts contain no personal preparation or secrets | Ready | Ongoing; final audit B20 | Development commits recorded below; private preparation is outside repository; credential configuration hardened and personal notes updated |
| B22 | Prepare and record English walkthrough with camera and screen, code trace, CLI and tests; verify duration at most 15 minutes | Waiting | B20 | Personal rehearsal remains in sibling private workspace; candidate records video |
| B23 | Track actual time from available records; candidate reconciles previous work; report honest total without estimating missing history as fact | Ready | Ongoing | No authoritative total yet; candidate confirmation required |
| B24 | Create/publish neutral public repository and video, verify both links, draft reply with actual hours, submit when explicitly authorized | Waiting | B20–B23 | No public repository, video or submission yet |
| B25 | Minimal GitHub Actions CI: Python 3.12, locked uv install, Ruff, unit tests, PostgreSQL 17 health check and migrations, integration tests, Docker build; verify configuration and local commands, then observe an actual GitHub run | Written | B03; first push or pull request for hosted evidence | [Workflow](../.github/workflows/ci.yml), [commands](../README.md#continuous-integration); local checks passed; hosted run pending; personal notes updated; development commit titled `Add minimal GitHub Actions CI` |

## Current verification record

| Check | Result | Consequence |
| --- | --- | --- |
| Python compile check on source, migration and tests | Passed | Syntax checked only |
| `docker compose config --quiet` | Passed | Compose configuration valid; image and service not run |
| Make help and command dry runs | Passed | Shortcut expansion checked |
| Integration shortcut without database URL | Expected rejection | Prevents silently skipping the database check |
| Dependency installation | Blocked by DNS/network access | Dependencies and lockfile unavailable |
| Docker daemon access | Permission denied | Build and startup unverified |
| Local PostgreSQL startup | Sandbox denied listening socket | Migration and database integration unverified |

The blocked results above are historical sandbox attempts. On 2026-10-06, approved execution outside the sandbox produced the following runtime evidence:

| Check | Result |
| --- | --- |
| `uv sync` | Passed; `uv.lock` generated; local Python 3.14.6 |
| `.venv/bin/ruff check .` | Passed |
| `.venv/bin/pytest -m 'not integration'` | 2 passed, 1 deselected |
| `docker compose up --build -d` | Image build passed; startup failed because host port 5432 was occupied |
| `DB_PORT=55432 docker compose up -d` | Passed against newly created PostgreSQL 17 volume; API started using Python 3.12 image |
| Full `.venv/bin/pytest` with `TEST_DATABASE_URL` on port 55432 | 3 passed, including real PostgreSQL readiness; one upstream TestClient deprecation warning |
| `SELECT version_num FROM alembic_version` | Revision `0001` applied |
| HTTP `/health/live` and `/health/ready` on port 8000 | Both returned HTTP 200 and `{"status":"ok"}` |

The sandbox-only health test stalled and was interrupted; the approved rerun passed. These checks verify the foundation, not the unimplemented payload or caching behavior.

## Development evidence

| Commit | Actual change |
| --- | --- |
| `2a3ce1d` | Requirements, architecture options and implementation plan |
| `4028011` | PostgreSQL coordination and failure handling contracts |
| `6a492e7` | Application foundation, migration, Compose and foundation tests |
| `b76b0cc` | Make shortcuts and documentation |

## Next work and completion gate

B03 runtime verification is complete. B04 contract and model checks are complete. Next implement B05–B06, then the payload flow and proceed through cache coordination, CLI and deployment evidence.

Submission is ready only when mandatory behavior, documented reliability guarantees, reproducible setup, and final checks pass; repository history is retained; private material is excluded; video meets the brief; and actual hours are reconciled. B24 remains separate from implementation completion because publishing and sending are delivery actions.


## Secrets and configuration follow-up

Removed the fixed development password from Compose, examples, and usage commands. Compose now requires DB_PASS; scripts/configure_local.py generates ignored local configuration with mode 0600 and refuses overwrites. The validated database URL is stored as SecretStr and only unwrapped at database connection boundaries. A regression test checks representation, JSON serialization, and formatted validation errors. The previously public development password remains in Git history and must be considered compromised; the local database role was rotated without deleting its volume. Expanded Compose configuration must not be used as public evidence. Personal foundation notes and working agreement updated.

Follow-up verification: Ruff passed; all four foundation tests passed against the rotated PostgreSQL role; Docker rebuild and migration/startup passed with the preserved volume; readiness returned HTTP 200. `docker compose --env-file /dev/null config --quiet` correctly rejected a missing password. `.env` is ignored by Git and has mode 0600.

Configuration naming follow-up: removed the former application-specific settings prefix and renamed variables to DATABASE_URL, DB_PASS, and DB_PORT throughout Compose, setup, examples, tests, and local configuration. Pool and timeout variables use their unprefixed setting names. Configuration guidance simplified; personal notes updated.

Naming verification: Ruff and all four foundation tests passed; Compose configuration, image rebuild, migrations, and API startup passed. Rebuilt API readiness returned HTTP 200.

## CI acceptance evidence

B25 adds a single job for pull requests and pushes to `main`, read-only `contents` permission, a 15-minute timeout, and cancellation of superseded runs. Checkout credentials are not persisted. `UV_LOCKED=true` also applies to Makefile commands. Disposable PostgreSQL credentials are unrelated to local or production secrets. No deployment, matrix, or coverage threshold was added.

Verification on 2026-10-06:

| Check | Result and scope |
| --- | --- |
| Upstream action tag verification with `git ls-remote` | checkout v4.2.2 = `11bd71901bbe5b1630ceea73d27597364c9af683`; setup-uv v6.0.1 = `6b9c6063abd6010835644d4c2e1bef4cf5cd0fca` |
| `actionlint` v1.7.7 | Passed; workflow configuration check only |
| `uv sync --locked` with Python 3.12.13 and uv 0.9.5 | Passed in isolated `/tmp` environment; existing committed lockfile unchanged |
| `make lint` and `make test` with `UV_LOCKED=true` | Ruff passed; 3 unit tests passed, 1 integration test deselected |
| Disposable PostgreSQL 17 container health check | Healthy; separate empty database on localhost port 55433 |
| `uv run alembic upgrade head` | Passed; revision `0001` confirmed against the disposable database |
| `make test-integration` with `TEST_DATABASE_URL` | 1 passed, 3 deselected; real PostgreSQL readiness |
| `docker build --tag cache-service:ci .` | Passed using the existing Dockerfile; Docker dependencies remain range-based |
| `git diff --check` | Passed |
| Actual GitHub Actions execution | Pending first remote push or pull request; no hosted success claimed |

The initial sandbox action-tag lookup failed DNS resolution; approved execution resolved it. uv cache access also required approved execution. Tests retain one upstream Starlette TestClient deprecation warning. Private workflow explanation and troubleshooting notes updated. B25 remains Written until a hosted run passes; there is no dependency-resolution blocker.

## B04 acceptance evidence

On 2026-10-06, `.venv/bin/pytest tests/test_schemas.py -q` passed all 18 tests; `.venv/bin/ruff check .` and `git diff --check` passed. Contract, strict request models, response serialization, configurable limits and finite positive deadline settings are verified. Personal notes updated. HTTP endpoint wiring and runtime deadline enforcement are pending B07/B11; no payload runtime evidence is claimed. Recorded in the commit titled `Define payload API contract and validation` on `feat/payload-contract`.

## Database naming consistency follow-up

Project configuration now exposes DB_HOST, DB_PORT, DB_USER, DB_NAME and DB_PASS in settings, Compose, local generation, examples and CI. DATABASE_URL remains an explicit override for existing local setups. PostgreSQL image keys are retained only at the documented container boundary. URL construction escapes credentials and preserves SecretStr masking. Existing database volumes are unchanged. Commit subject: `Standardize database configuration names`.

Verification: full `.venv/bin/pytest -q` passed all 27 tests with TEST_DATABASE_URL set from masked local settings, including real PostgreSQL readiness. Readiness also returned 200 using DB_* settings without a DATABASE_URL override. Ruff, actionlint v1.7.7, Compose configuration and git diff whitespace checks passed. One upstream Starlette TestClient deprecation warning remains.

Hosted CI run `37461260126` failed during container creation: GitHub runner argument parsing rejected single-quoted health-command grouping (`unknown shorthand flag: U`). Follow-up uses double-quoted grouping for the Docker option; hosted rerun pending.
