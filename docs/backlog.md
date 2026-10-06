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
| B05 | Define canonical encoding, version and digest identities; verify list boundaries, order, whitespace and collision handling | Done | B04 | [Identity helpers](../src/cache_service/identity.py), [tests](../tests/test_identity.py), exact format in [architecture](architecture.md); 18 focused tests and 44 unit tests passed; personal notes updated; commit titled `Add versioned input identities` on `feat/versioned-identities` |
| B06 | Replaceable uppercase transformer and alternating composition; meaningful isolated tests | Done | B04 | [Transformer and composition](../src/cache_service/transformation.py), [tests](../tests/test_transformation.py); 21 focused tests, 65 unit tests and Ruff passed; personal notes updated; commit titled `feat: add replaceable transformer and payload composition` on `feat/b06-transformer-composition` |
| B07 | Create and read complete payloads; generated UUID plus unique input digest; duplicate creation returns stored ID | Done | B03–B06 | [Payload flow](../src/cache_service/payloads.py), [routes](../src/cache_service/main.py), [tests](../tests/test_payloads.py); 80 tests and Ruff passed, including real PostgreSQL publication races and restart reuse; personal notes updated; commit titled `feat: add payload creation and retrieval` on `feat/b07-payload-endpoints` |
| B08 | API tests for sample output, invalid types/lengths, empty input, unknown ID, retry and identity policy | Done | B07 | [Payload tests](../tests/test_payloads.py); API coverage reviewed against the contract; 103 tests and Ruff passed, including real PostgreSQL identity/version and retry checks; see B08 acceptance evidence; commit titled `test: complete B08 payload API coverage` on `feat/b08-api-coverage` |
| B09 | Batch cache reads and request deduplication; persist successful results with versioned keys and authoritative readback | Done | B03, B05, B06 | [Cache flow](../src/cache_service/cache.py), [payload integration](../src/cache_service/payloads.py), [cache tests](../tests/test_cache.py); 116 full-suite tests and Ruff passed against PostgreSQL; personal notes updated; commit titled `feat: add persistent transformation caching` on `feat/b09-transformation-cache` |
| B10 | One advisory lock at a time, recheck after acquire, same connection for writes; no transaction over external call | Done | B09 | [Cache coordination](../src/cache_service/cache.py), [tests](../tests/test_cache.py); 120 full-suite tests and Ruff passed against PostgreSQL; see B10 evidence below; personal notes updated; commit titled `feat: coordinate transformation misses with advisory locks` on `feat/b10-advisory-coordination` |
| B11 | Bounded admission and waits, cancellation-safe cleanup, invalidate uncertain ownership; map operational failures to documented HTTP responses | Done | B10, B04 | [Coordination](../src/cache_service/coordination.py), [cache flow](../src/cache_service/cache.py), [tests](../tests/test_coordination.py); 137 full-suite tests and Ruff passed against PostgreSQL; see B11 evidence below; personal notes updated; commit titled `feat: bound cache coordination and protect cleanup` on `feat/b11-bounded-coordination` |
| B12 | Preserve successful transformations on later failure; publish complete payload atomically; verify safe retries | Ready | B07, B09–B11 | Policy recorded; implementation pending |
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
| B25 | Minimal GitHub Actions CI: Python 3.12, locked uv install, Ruff, unit tests, PostgreSQL 17 health check and migrations, integration tests, Docker build; verify configuration and local commands, then observe an actual GitHub run | Done | B03; first push or pull request for hosted evidence | [Workflow](../.github/workflows/ci.yml), [commands](../README.md#continuous-integration); local checks and [hosted run](https://github.com/befikadusata/cache-service/actions/runs/37461411063) passed; personal notes updated; development commit titled `Add minimal GitHub Actions CI` |

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

B03 runtime verification, B04 contract and model checks, B05 identity helpers, and B06 transformation and composition are complete. B07 payload creation and retrieval and B08 API coverage review are also complete. B09 persistent transformation caching is complete. B10 advisory coordination is also complete. B11 bounded admission, waits and protected cleanup is complete. Next is B12 acceptance for partial-success preservation, atomic publication and safe retries, then broader failure/concurrency evidence, CLI and deployment.

Submission is ready only when mandatory behavior, documented reliability guarantees, reproducible setup, and final checks pass; repository history is retained; private material is excluded; video meets the brief; and actual hours are reconciled. B24 remains separate from implementation completion because publishing and sending are delivery actions.

## B06 acceptance evidence

Verification on 2026-10-06:

| Check | Result and scope |
| --- | --- |
| `.venv/bin/pytest tests/test_transformation.py` | 21 passed: uppercase, Unicode expansion, preserved whitespace, replacement, failure propagation, alternating order, duplicates, empty elements and unequal lengths |
| `.venv/bin/ruff check .` | Passed |
| `.venv/bin/pytest -m 'not integration'` | Sandbox run stalled in the existing TestClient health test and was interrupted; approved rerun outside the sandbox passed: 65 passed, 1 integration test deselected, 1 upstream TestClient deprecation warning |

Personal transformation notes updated outside Git. No schema or database behavior changed;
payload routes, caching, operational error mapping and deadlines remain later work.


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
| Actual GitHub Actions execution | Passed: [main run 37461411063](https://github.com/befikadusata/cache-service/actions/runs/37461411063), including DB_* configuration, migrations, tests and Docker build |

The initial sandbox action-tag lookup failed DNS resolution; approved execution resolved it. uv cache access also required approved execution. Tests retain one upstream Starlette TestClient deprecation warning. Private workflow explanation and troubleshooting notes updated. B25 is Done after hosted verification; there is no dependency-resolution blocker.

## B04 acceptance evidence

On 2026-10-06, `.venv/bin/pytest tests/test_schemas.py -q` passed all 18 tests; `.venv/bin/ruff check .` and `git diff --check` passed. Contract, strict request models, response serialization, configurable limits and finite positive deadline settings are verified. Personal notes updated. HTTP endpoint wiring and runtime deadline enforcement are pending B07/B11; no payload runtime evidence is claimed. Recorded in the commit titled `Define payload API contract and validation` on `feat/payload-contract`.

## Database naming consistency follow-up

Project configuration now exposes DB_HOST, DB_PORT, DB_USER, DB_NAME and DB_PASS in settings, Compose, local generation, examples and CI. DATABASE_URL remains an explicit override for existing local setups. PostgreSQL image keys are retained only at the documented container boundary. URL construction escapes credentials and preserves SecretStr masking. Existing database volumes are unchanged. Commit subject: `Standardize database configuration names`.

Verification: full `.venv/bin/pytest -q` passed all 27 tests with TEST_DATABASE_URL set from masked local settings, including real PostgreSQL readiness. Readiness also returned 200 using DB_* settings without a DATABASE_URL override. Ruff, actionlint v1.7.7, Compose configuration and git diff whitespace checks passed. One upstream Starlette TestClient deprecation warning remains.

Hosted CI run `37461260126` failed during container creation: GitHub runner argument parsing rejected single-quoted health-command grouping (`unknown shorthand flag: U`). Follow-up uses double-quoted grouping for the Docker option; Resolved in commit `2af2e17`: [hosted rerun 37461411063](https://github.com/befikadusata/cache-service/actions/runs/37461411063) passed every step. Database naming implementation is commit `c1b59e4`. Personal notes updated.

## B05 acceptance evidence

On 2026-10-06, `.venv/bin/pytest tests/test_identity.py -q` passed 18 tests. Fixed vectors verify canonical JSON, SHA-256 digests and stable signed advisory keys. Additional checks cover exact input distinctions, empty inputs, Unicode without normalization, version changes, and simulated digest and advisory-key collisions. Retained identity comparisons reject mismatches with fixed messages containing no input. The existing migration already matches these 32-byte keys; no schema change was needed.

The full `.venv/bin/pytest -m 'not integration' -q` suite initially stalled in the sandbox health test and was interrupted. The approved rerun passed 44 tests with one integration test deselected and the existing upstream Starlette TestClient deprecation warning. `.venv/bin/ruff check .` and `git diff --check` passed. Personal design notes updated. Recorded in the commit titled `Add versioned input identities` on `feat/versioned-identities`. These checks establish pure identity behavior; persistence readback, HTTP error mapping and real advisory coordination remain later work.

## B07 acceptance evidence

On 2026-10-06, branch `feat/b07-payload-endpoints` implements POST/GET payload routes,
configured strict validation, replacement transformer injection, overall request deadlines,
immutable complete-output publication, identity verification and generic operational responses.
The existing migration supports this flow; no schema change is needed.

| Check | Result and scope |
| --- | --- |
| `.venv/bin/pytest tests/test_payloads.py -m 'not integration' -q` | 6 passed, 5 deselected at that stage; input rejection and configured lower limits |
| Focused payload integration tests with local `TEST_DATABASE_URL` | Initial sandbox run failed because socket creation was denied; approved rerun passed all 5 tests present at that stage |
| Full `.venv/bin/pytest -q --tb=short` with local `TEST_DATABASE_URL` | 80 passed, including 8 payload integration tests and foundation readiness; one existing upstream TestClient deprecation warning |
| `.venv/bin/ruff check .` and `git diff --check` | Passed |

PostgreSQL evidence covers alternating output, empty output/elements, ID reuse, distinct-input
identity, fresh application/pool reuse, synchronized competing publication, retained identity
collisions during both lookup and publication, no payload on transformer failure or generation
deadline, successful retry, and configured limits above defaults. Concurrent misses still repeat
transformation: no per-string cache or advisory-lock guarantee is claimed in B07. B08 retains
its separate API coverage review; B09–B14 retain caching and coordination work. Personal request
flow notes updated outside Git. Recorded in commit titled `feat: add payload creation and retrieval`.

## B08 acceptance evidence

On 2026-10-06, branch `feat/b08-api-coverage` completes the API coverage review against
[the contract](api-contract.md). It extends tests without changing service behavior.

| Acceptance scenario | HTTP evidence in `tests/test_payloads.py` |
| --- | --- |
| Alternating uppercase output and UUID response | Existing create/read test; new identity cases assert exact response objects, Unicode expansion and preserved whitespace |
| Strict input and configured limits | Missing fields, invalid arrays/items in both lists, unequal lengths, extra fields and malformed JSON return 422 before database access; all three configurable limit types are exercised |
| Empty lists/elements and unknown IDs | Existing PostgreSQL checks verify empty output, retained empty elements and 404; malformed UUID validation also runs without PostgreSQL |
| Repeated input and safe retry | Identical input returns its stored ID; failed transformation publishes nothing, then a healthy retry creates readable output and subsequent reuse returns the same ID; deadline retry remains covered |
| Exact ordered input identity | Case, whitespace, order, list boundaries, duplicate multiplicity and Unicode normalization differences produce distinct IDs, including equal-output inputs |
| Transformer version and persistence | A replacement version creates a new ID/output while the old payload stays readable; existing fresh-application test verifies persisted ID reuse |

| Executed check | Result |
| --- | --- |
| `.venv/bin/pytest tests/test_payloads.py -m 'not integration' -q` | 22 passed, 15 deselected |
| Focused PostgreSQL tests inside the sandbox | Failed because database socket creation was denied; resolved by approved execution outside the sandbox |
| Full `.venv/bin/pytest -q --tb=short` with local `TEST_DATABASE_URL` | 103 passed, including all 15 payload integration cases and foundation readiness; one existing upstream TestClient deprecation warning |
| `.venv/bin/ruff check .`, `.venv/bin/ruff format --check tests/test_payloads.py` and `git diff --check` | Passed |

The full suite was invoked through a temporary runner that loads the ignored local settings
and supplies `TEST_DATABASE_URL` to pytest without printing credentials. No new architecture,
request flow or operational policy was introduced, so existing personal B07 notes remain
applicable. Per-string caching and concurrent transformer call-count guarantees remain
B09–B14. Recorded in commit titled `test: complete B08 payload API coverage`.


## B09 acceptance evidence

Verification on 2026-10-06, branch `feat/b09-transformation-cache`, commit titled
`feat: add persistent transformation caching`:

| Check | Result and scope |
| --- | --- |
| Focused cache and payload tests with local `TEST_DATABASE_URL` | Initial sandbox database run failed and was interrupted; approved rerun passed 48 tests before the final two unit checks were added |
| Full `.venv/bin/python` runner loading ignored local settings and invoking `pytest -q` with `TEST_DATABASE_URL` | 116 passed, including all PostgreSQL tests; one existing Starlette TestClient deprecation warning |
| `.venv/bin/ruff check .` | Passed |
| `git diff --check` | Passed |

B09 adds 13 cache tests: three isolated checks and ten PostgreSQL cases. Evidence covers exact
source deduplication, one batched read for normal input, two bounded batches for 501 cached
sources, empty input/results, reuse by distinct payloads and by a fresh application generating
a new payload, version separation, successful-result retention on later failure, retry of only
remaining misses, timeout/cancellation without caching failed work, collisions within a request
and at lookup/conflict readback, and authoritative stored results after insert conflict. A
transformer assertion verifies that no connection is checked out during the external operation.
Existing payload tests now use unique sources where call counts or forced failures require misses
and remove marked transformation rows alongside payloads.

The existing migration already provides the transformation primary key and retained identity;
no schema change is required. README, API contract and architecture reflect the implemented
scope. Personal cache walkthrough, design alternatives, payload trace and conventional-commit
preference were updated outside Git. Concurrent misses can still repeat transformer calls;
advisory ownership and multi-process minimized-call guarantees remain B10–B14. B12 retains
coordinated retry and atomic-publication evidence as its completion gate.

## B10 acceptance evidence

Verification on 2026-10-06:

- Full `.venv/bin/pytest -q -x`, with `TEST_DATABASE_URL` loaded from masked local settings:
  **120 passed**, including real PostgreSQL integration; one existing TestClient deprecation warning.
- `.venv/bin/ruff check .` and `git diff --check`: passed.
- Two independent engines overlap on a missing string. The test observes an actual ungranted
  PostgreSQL advisory lock before releasing the holder, then verifies one shared transformer
  call, cache recheck reuse and successful overlapping work.
- PostgreSQL reports the holder `idle` with no transaction during transformation. SQL event
  instrumentation proves lock acquisition and persistence use the same connection. Explicit
  unlock permits another session to acquire immediately after success.
- Failure, transformer timeout and cancellation discard the session and permit a retry;
  existing collision/readback, partial-success and concurrent payload identifier checks pass.
- Initial sandbox database execution failed because sockets were denied; approved execution
  passed. Private cache walkthrough and working agreement updated outside Git.

Lock acquisition currently uses the ordinary statement timeout. Separate budgets, admission,
bounded cancellation-protected cleanup, forced ownership-loss tests and multiple-process
call-count evidence remain B11–B14. No schema migration or dependency change was needed.


## B11 acceptance evidence

Verification on 2026-10-06:

- `.venv/bin/ruff check .`: passed.
- Focused coordination/cache suite: 32 passed against PostgreSQL before two additional acceptance tests.
- Full suite with TEST_DATABASE_URL derived from masked local Settings: 137 passed, including
  38 real PostgreSQL tests; one existing upstream TestClient deprecation warning.
- Initial sandbox-only unit execution stalled in the existing health TestClient test; interrupted.
  Initial database execution failed under sandbox network restrictions and was interrupted.
  Approved full execution outside the sandbox resolved both limitations.

Evidence covers validated capacity and finite budgets, admission saturation with spare read
progress, retryable HTTP 503 with Retry-After, lock waiting without a transformer fallback,
checkout timeout releasing admission, independent transformer HTTP 504, cancellation and
uncertain acquisition releasing session ownership, transaction-local settings reverting,
repeated cancellation protection, and force-close after stalled cleanup. Existing B10 tests
continue to prove no transaction during transformation and same-session persistence.
Broader disconnect, crash and multi-process evidence remains B13/B14. Personal learning notes
and a timeout/cancellation cookbook were updated outside Git.
