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
| B01 | Record author response, identity/storage choices and transformer assumption; resolve CLI flag conflict and output format | Done | None | Author delegated identity/storage; [README design decisions](../README.md#design-decisions) and [CLI policy](../README.md#cli-usage) recorded; JSON Lines selected; documentation consistency and `git diff --check` passed; personal notes updated; commit titled `feat: define CLI JSON Lines output policy` on `feat/b01-cli-output-policy` |
| B02 | Application lifecycle, PostgreSQL configuration, migration and Compose; inspect setup artifacts | Done | None | [Application](../src/cache_service/main.py), [migration](../migrations/versions/0001_initial.py), [Compose](../compose.yaml); commit `6a492e7` |
| B03 | Install dependencies, generate lockfile, run lint and foundation tests, apply clean migration, check both health endpoints and image startup | Done | B02; execution/network access | Runtime checks passed on 2026-10-06; `uv.lock` generated; PostgreSQL host port 55432; see verification record below; personal notes updated |
| B04 | Freeze POST and GET response schemas, strict input validation, empty behavior, configurable limits and request deadlines | Done | Selected B01 assumptions | [Contract](api-contract.md), [models](../src/cache_service/schemas.py), [settings](../src/cache_service/config.py), [tests](../tests/test_schemas.py); 18 focused tests and Ruff passed; personal notes updated; commit titled `Define payload API contract and validation`. Endpoint enforcement completed in B07/B11 |
| B05 | Define canonical encoding, version and digest identities; verify list boundaries, order, whitespace and collision handling | Done | B04 | [Identity helpers](../src/cache_service/identity.py), [tests](../tests/test_identity.py), exact format in [architecture](architecture.md); 18 focused tests and 44 unit tests passed; personal notes updated; commit titled `Add versioned input identities` on `feat/versioned-identities` |
| B06 | Replaceable uppercase transformer and alternating composition; meaningful isolated tests | Done | B04 | [Transformer and composition](../src/cache_service/transformation.py), [tests](../tests/test_transformation.py); 21 focused tests, 65 unit tests and Ruff passed; personal notes updated; commit titled `feat: add replaceable transformer and payload composition` on `feat/b06-transformer-composition` |
| B07 | Create and read complete payloads; generated UUID plus unique input digest; duplicate creation returns stored ID | Done | B03–B06 | [Payload flow](../src/cache_service/payloads.py), [routes](../src/cache_service/main.py), [tests](../tests/test_payloads.py); 80 tests and Ruff passed, including real PostgreSQL publication races and restart reuse; personal notes updated; commit titled `feat: add payload creation and retrieval` on `feat/b07-payload-endpoints` |
| B08 | API tests for sample output, invalid types/lengths, empty input, unknown ID, retry and identity policy | Done | B07 | [Payload tests](../tests/test_payloads.py); API coverage reviewed against the contract; 103 tests and Ruff passed, including real PostgreSQL identity/version and retry checks; see B08 acceptance evidence; commit titled `test: complete B08 payload API coverage` on `feat/b08-api-coverage` |
| B09 | Batch cache reads and request deduplication; persist successful results with versioned keys and authoritative readback | Done | B03, B05, B06 | [Cache flow](../src/cache_service/cache.py), [payload integration](../src/cache_service/payloads.py), [cache tests](../tests/test_cache.py); 116 full-suite tests and Ruff passed against PostgreSQL; personal notes updated; commit titled `feat: add persistent transformation caching` on `feat/b09-transformation-cache` |
| B10 | One advisory lock at a time, recheck after acquire, same connection for writes; no transaction over external call | Done | B09 | [Cache coordination](../src/cache_service/cache.py), [tests](../tests/test_cache.py); 120 full-suite tests and Ruff passed against PostgreSQL; see B10 evidence below; personal notes updated; commit titled `feat: coordinate transformation misses with advisory locks` on `feat/b10-advisory-coordination` |
| B11 | Bounded admission and waits, cancellation-safe cleanup, invalidate uncertain ownership; map operational failures to documented HTTP responses | Done | B10, B04 | [Coordination](../src/cache_service/coordination.py), [cache flow](../src/cache_service/cache.py), [tests](../tests/test_coordination.py); 137 full-suite tests and Ruff passed against PostgreSQL; see B11 evidence below; personal notes updated; commit titled `feat: bound cache coordination and protect cleanup` on `feat/b11-bounded-coordination` |
| B12 | Preserve successful transformations on later failure; publish complete payload atomically; verify safe retries | Done | B07, B09–B11 | [Payload tests](../tests/test_payloads.py); five new PostgreSQL cases, 142 full-suite tests and Ruff passed; see B12 evidence below; personal notes updated; commit titled `Verify partial success and atomic payload retries` on `feat/b12-atomic-publication-retries` |
| B13 | Real PostgreSQL tests for timeout, cancellation, saturation, lock loss, collisions, version changes and no open transaction during transform | Done | B11, B12 | [Coordination tests](../tests/test_coordination.py), [cache tests](../tests/test_cache.py), [payload tests](../tests/test_payloads.py); 21 focused tests, 146 full-suite tests and Ruff passed against PostgreSQL; see B13 evidence below; personal notes updated; commit titled `feat: verify PostgreSQL coordination failure recovery` on `feat/b13-postgresql-failure-evidence` |
| B14 | Multi-process identical and overlapping requests; call counts per distinct string, consistent IDs and restart reuse | Done | B12 | [Separate-process tests](../tests/test_multiprocess.py); two focused cases and 148 full-suite tests passed against PostgreSQL; Ruff passed; see B14 evidence below; personal notes updated; commit titled `feat: verify multi-process cache coordination` on `feat/b14-multiprocess-concurrency` |
| B15 | Pydantic Settings CLI parsing; host, repeat and mutually exclusive input source validation; resolve help alias | Done | B01 output policy; B04 | [Parser](../src/cache_service/cli.py), [tests](../tests/test_cli.py); 24 focused tests, 123 unit tests and Ruff passed; see B15 evidence below; personal notes updated; commit titled `feat: add CLI argument parsing and validation` on `feat/b15-cli-parsing` |
| B16 | CLI create/read loop, file/stdin/JSON input, file/stdout output, stderr diagnostics and nonzero failure exit | Done | B07, B15 | [Executable](../src/cache_service/cli.py), [execution tests](../tests/test_cli_execution.py), [usage](../README.md#cli-usage); 49 focused CLI tests, 148 unit tests and Ruff passed; see B16 evidence below; personal notes updated; commit titled `Add CLI execution and JSON Lines output` on `feat/b16-cli-execution` |
| B17 | CLI parsing and I/O tests plus a real-service integration scenario | Done | B16 | [CLI tests](../tests/test_cli_execution.py), [live-service tests](../tests/test_cli_integration.py), [verification](verification.md#cli-evidence); two focused live-service cases and 201 full-suite tests passed against PostgreSQL; Ruff passed; personal notes updated; commit titled `Verify CLI against live API and PostgreSQL` on `feat/b17-cli-verification` |
| B18 | Clean Docker build and migration/start smoke test; storage reuse after restart; document supported worker/connection budget | Done | B03, B12, B17 | [Deployment smoke script](../scripts/verify_deployment.py), [procedure](verification.md#docker-deployment), worker/connection guidance in README and architecture; all runtime checks and Ruff passed on 2026-10-07; see B18 evidence below; personal notes updated; commit titled `Verify Docker deployment and restart persistence` |
| B19 | Complete public setup, usage, configuration, architecture and limitations; reconcile every guarantee with tests | Done | B14, B17, B18 | [Configuration](configuration.md), [guarantee evidence](verification.md#guarantee-evidence), README, API contract and architecture reconciled with current code/tests; documentation checks, CLI help, Ruff and whitespace checks passed; see B19 evidence below; personal notes updated |
| B20 | Final code review and requirement audit; full required suite passes; remove unnecessary complexity and inspect repository contents | Done | B13, B14, B17–B19 | [Final review](final-review.md); new real PostgreSQL GET-deadline/cleanup/retry test; 202 full-suite tests, Ruff, whitespace, locked dependency check, Compose validation and Docker build passed; tracked-file inspection passed; personal notes updated |
| B21 | Preserve real incremental commits; verify neutral repository name and public artifacts contain no personal preparation or active secrets; account for retired exposed credentials | Done | Ongoing; final audit B20 | [Repository audit](repository-audit.md): neutral public name verified; 47 commits and 174 historical blobs inspected; no current credential/key/token or private-file matches; known historical development password remains public and is independently verified rejected by local PostgreSQL; personal notes updated |
| B22 | Prepare and record English walkthrough with camera and screen, code trace, CLI and tests; verify duration at most 15 minutes | Written | B20 | Personal timed script and rehearsal helper saved in sibling private workspace; live CLI/SQL/restart demo and 28 focused tests passed on 2026-10-07; candidate recording, playback and actual duration verification remain pending |
| B23 | Track actual time from available records; candidate reconciles previous work; report honest total without estimating missing history as fact | Ready | Ongoing | No authoritative total yet; candidate confirmation required |
| B24 | Publish final repository revision and video, verify both links, draft reply with actual hours, submit when explicitly authorized | Waiting | B20–B23 | Neutral public repository exists; published main is B17 (`425e0b3`), with B18–B20 local at the B21 audit; final revision publication, video and submission remain |
| B25 | Minimal GitHub Actions CI: Python 3.12, locked uv install, Ruff, unit tests, PostgreSQL 17 health check and migrations, integration tests, Docker build; verify configuration and local commands, then observe an actual GitHub run | Done | B03; first push or pull request for hosted evidence | [Workflow](../.github/workflows/ci.yml), [commands](../README.md#continuous-integration); local checks and [hosted run](https://github.com/befikadusata/cache-service/actions/runs/37461411063) passed; personal notes updated; development commit titled `Add minimal GitHub Actions CI` |
| B26 | Align assessment API paths, JSON fields, CLI command and short options; verify the exact sample and retain legacy identity reuse | Done | B20 | `main.py`, `schemas.py`, `cli.py`, packaged `cache-cli`, schema/parser/live-CLI tests and [compatibility verification](verification.md#assessment-compatibility-verification); 211 tests, Ruff, whitespace and locked offline install passed on 2026-10-07; commit titled `fix: add payload routes, JSON field aliases, and cache-cli options` |

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

B03–B14 are complete, including partial-success preservation, atomic publication, safe retries,
controlled PostgreSQL failure recovery and separate-process coordination. B01 CLI output
policy, B15 CLI parsing, B16 CLI execution and B17 live-service verification are complete.
B18 deployment verification, B19 documentation reconciliation and B20 final implementation
review and B21 repository history/public-artifact audit are complete. Next is B22 video
preparation and recording; B23 actual-hours reconciliation and B24 final publication/delivery
remain.

Submission is ready only when mandatory behavior, documented reliability guarantees, reproducible setup, and final checks pass; repository history is retained; private material is excluded; video meets the brief; and actual hours are reconciled. B24 remains separate from implementation completion because publishing and sending are delivery actions.

## B21 acceptance evidence

Audit on 2026-10-07 is recorded in [the repository and history audit](repository-audit.md).
GitHub metadata verifies public `befikadusata/cache-service`, neutral name `cache-service`
and default branch `main`. Published main is `425e0b3`; local B18–B20 commits are unpublished.
All 14 remote branch heads belong to audited history; no tags, releases or release assets exist.

- Preserved 47 real commits, including 33 non-merge development commits and 14 merges.
  All locally reachable commits are ancestors of current main; no rewrite or push occurred.
- Inspected 47 tracked files and 174 distinct historical blobs, plus commit content, for current
  local credentials, common key/token patterns and private/local artifacts; no such matches.
  Compared historical blobs against 15 private files; no exact copies. Reviewed public prose.
- Manually reviewed 19 database-URL and nine password-assignment candidate blobs with values
  redacted. The previously recorded fixed development password remains in old history; current
  secrets are absent. Current database authentication passed and historical password
  authentication was independently rejected. No clean-history or exhaustive-scanner claim.
- Ignore rules exclude local credentials and private preparation. Personal audit notes updated
  outside Git. Documentation checks and whitespace validation passed; runtime code unchanged.
- Corrected stale B24 publication status. B22 video, B23 actual hours and B24 final publication
  and submission remain; existing history and database volumes are preserved.

## B20 acceptance evidence

Final review on 2026-10-07 is recorded in [the requirement and code audit](final-review.md).
Reviewed all service/CLI modules, migration, setup/deployment artifacts, CI and associated
tests against R01–R13 and documented transaction/resource guarantees. No production code
change or complexity removal was justified. Closed one verification gap with a real
PostgreSQL blocked-GET test that checks 504, connection return and successful retry.

- Baseline suite: 201 passed. New GET test alone: 1 passed. Final suite with securely supplied
  `TEST_DATABASE_URL`: 202 passed (150 unit, 52 integration), no skips, in 22.67 seconds.
  One upstream Starlette TestClient/httpx deprecation warning remains.
- `uv sync --locked --offline`, `.venv/bin/ruff check .`, `git diff --check`,
  `docker compose config --quiet`, and `docker build --tag cache-service:b20-review .` passed.
  PostgreSQL schema revision is `0001`, matching head.
- Inspected all 46 tracked files for current local credentials, common private-key/token
  patterns and tracked local/private artifacts; no matches. This scoped check does not replace
  B21's history/public-artifact audit. Existing database volumes were preserved.
- Local suite used Python 3.14.6 and PostgreSQL 17; the built image uses Python 3.12.
  No new hosted CI, Python 3.12 full suite or B18 deployment recreation run is claimed.
- Personal final-review walkthrough notes updated outside Git. Implementation review is
  complete; video, actual hours and delivery remain separate acceptance gates.

## B18 acceptance evidence

Verification on 2026-10-07, with approved Docker execution outside the sandbox:

| Check | Result and scope |
| --- | --- |
| `.venv/bin/python scripts/verify_deployment.py`, first attempt | Clean build passed; first readiness request hit a connection reset during startup. Fixed bounded polling to retry connection errors; failed attempt remains recorded here |
| `.venv/bin/python scripts/verify_deployment.py`, complete rerun | Passed in isolated project `cache-b18-c516b5b4e642`, fresh credentials/storage, no published database port and dynamically assigned localhost API port |
| No-cache Docker build and Compose startup | Passed; migration service exited 0, stored revision matched Alembic head `0001`, both health endpoints returned 200 |
| Packaged CLI, HTTP and independent SQL checks | Passed; correct alternating Unicode output, repeated UUID, complete committed payload and three distinct transformation records; overlapping payload succeeded |
| Container recreation retaining volume | Passed; old UUID readable and reused; a new reordered payload succeeded with transformations disabled; cache snapshot unchanged; uncached input returned 502, proving the restart probe was active |
| `.venv/bin/ruff check .` and `git diff --check` | Passed |

The smoke check uses one worker and the packaged application code. B14 remains the controlled
separate-process coordination evidence. README and architecture now describe launching multiple
workers and budgeting `workers × POOL_SIZE` connections plus migration/administration capacity.
Docker still resolves dependency ranges, unlike the locked local/CI environment. No application
behavior or schema changed; no additional pytest run was required for this smoke script and
documentation. Personal deployment notes updated outside Git. Both attempts stopped their
containers and retained their isolated volumes; existing deployment storage was untouched.
Development commit titled `Verify Docker deployment and restart persistence`.

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

## B12 acceptance evidence

Verification on 2026-10-06:

- `.venv/bin/pytest tests/test_payloads.py -k 'partial_success or publication_rollback' -q`
  with TEST_DATABASE_URL derived from masked local Settings: 5 passed, 37 deselected.
- Full `.venv/bin/pytest -q` with the same database configuration: 142 passed,
  including real PostgreSQL tests; one existing upstream TestClient deprecation warning.
- `.venv/bin/ruff check .` and `git diff --check`: passed.
- Sandbox database execution failed/stalled and was interrupted; approved focused and full
  execution outside the sandbox passed. Database URLs and credentials were not printed.

Controlled API tests pause the second transformation and use an independent connection to
verify the first result is already committed while no payload exists. Transformer failure,
timeout and cancellation preserve that result and publish no payload. A fresh application
retries only the missing strings, reconstructs complete alternating output and reuses the ID
on subsequent identical requests.

Publication tests inject exceptions after the real payload INSERT and immediately before
commit. Both roll back the payload, return generic retryable 503 responses, retain all
successful transformations and leave the attempted UUID unreadable. Fresh-application retries
perform no transformations and return a complete readable payload with a reusable identifier.
Existing concurrent publication tests continue to verify one authoritative stored ID.

The existing implementation satisfies these cases; no production change, schema revision or
dependency change was needed. These faults precede commit and do not establish behavior for
lost commit acknowledgments or all connection-loss windows. Broader failure and multi-process
evidence remains B13/B14. Personal request-flow and design notes updated outside Git.

## B13 acceptance evidence

Verification on 2026-10-06:

- Focused `.venv/bin/pytest tests/test_coordination.py -q --tb=short` against PostgreSQL:
  21 passed, including four new integration scenarios.
- Full `.venv/bin/pytest -q --tb=short` with TEST_DATABASE_URL derived internally from masked
  Settings: 146 passed; one existing upstream TestClient deprecation warning.
- `.venv/bin/ruff check .` and `git diff --check`: passed.
- Initial sandbox run could not open PostgreSQL sockets. The first approved focused run
  exposed a test setup problem: a single admission slot prevented the intended competing
  request, and the 50 ms checkout budget was too short for a cold connection. A separate
  application models the competitor; the fixture now allows 500 ms for checkout. Approved
  focused and full reruns passed. No database URLs or credentials were printed.

New tests observe PostgreSQL lock waiters before cancelling or releasing them. Cancellation
while waiting does not invoke the transformer or populate the cache, releases checkout and
admission, and permits a retry. Forced advisory-key collisions serialize distinct strings but
retain separate correct cache values. Removing session ownership before cleanup produces a
failure, discards the connection, and preserves a result already committed.

The backend-loss test identifies only its own lock holder's PID, verifies PostgreSQL reports
an idle session with no transaction, and terminates that backend. A separate application
successfully repeats the transformation while the original external call remains paused.
The original request returns generic HTTP 503 with Retry-After and cannot overwrite the
recovered result or publish another payload. Retry reuses the recovered identifier without
another call. This proves the documented connection-loss repeat-work window, not exactly-once
execution or behavior for every possible lost commit acknowledgment.

Existing B10–B12 evidence supplies timeout, saturation, uncertain acquisition, partial-success,
digest-collision, version-change, same-session persistence and transaction-boundary checks.
The backend-loss scenario also independently checks transaction state through pg_stat_activity.
No production code, migration or dependency change was required. Personal coordination notes
and recovery cookbook updated outside Git. B14 still owns separate-process concurrency evidence.


## B14 acceptance evidence

Verification on 2026-10-06:

- `tests/test_multiprocess.py`: two PostgreSQL cases passed using the multiprocessing spawn context, independent application engines and event loops, and IPC transformer-call reporting.
- The holder pauses on the first shared transformation until `pg_locks` shows a holder and waiter on its exact key with different backend PIDs. Identical and overlapping requests each make one call per distinct missing string; request duplicates cause no extra calls.
- Identical inputs return the same UUID; overlapping distinct inputs return different UUIDs and correct alternating output. After both original processes exit, a fresh process reuses both UUIDs and generates a new ordered payload entirely from cached strings with zero transformer calls.
- `.venv/bin/pytest -q` with `TEST_DATABASE_URL` supplied privately from validated settings: 148 passed, one existing upstream TestClient deprecation warning. Focused run: 2 passed. Ruff and `git diff --check` passed.
- The sandbox focused attempt stalled and was interrupted; the approved run outside the sandbox passed. Private multi-process walkthrough notes updated outside Git.

HTTP requests use ASGITransport inside separate application processes. This proves cross-process PostgreSQL coordination and persisted reuse; networked deployment startup remains B18. Crash and connection-loss repeat-work limitations remain as documented in architecture and verified by B13. No application behavior or schema changes were needed.


## B15 acceptance evidence

Verification on 2026-10-07:

| Check | Result and scope |
| --- | --- |
| `.venv/bin/pytest tests/test_cli.py -q` | 24 passed: defaults, explicit host/repeat/output, file/stdin/inline input, exactly one source, invalid values and flags, both help aliases, process arguments and environment isolation |
| `.venv/bin/ruff check .` | Passed |
| `.venv/bin/pytest -m 'not integration' -q` | Sandbox run stalled and was interrupted; approved rerun passed: 123 passed, 49 integration cases deselected; one existing upstream TestClient deprecation warning |
| `git diff --check` | Passed |

The parser uses Pydantic Settings without loading API/database configuration. It returns
validated options, preserves input contents for B16, and does no HTTP or file I/O.
Help exits successfully; parser and value errors remain exceptions for B16's entry point
to map to stderr and a nonzero exit. No dependencies or lockfile changes were needed.
Personal CLI learning notes updated outside Git.


## B16 acceptance evidence

Verification on 2026-10-07:

| Check | Result and scope |
| --- | --- |
| `uv lock --offline` and `uv sync --locked --offline` | Sandbox cache access denied; approved rerun passed; HTTPX promoted to runtime dependency, lockfile synchronized and executable installed |
| `.venv/bin/pytest tests/test_cli.py tests/test_cli_execution.py -q` | 49 passed: argument parsing plus mocked create/read repeats, path prefix, all input sources, file overwrite, same input/output path, empty output, newline escaping, input/HTTP/response/network/file/flush failures and earlier-record preservation |
| `.venv/bin/pytest -m 'not integration' -q` | Sandbox run stalled and was interrupted; approved rerun passed with 144 tests; final rerun after four added edge cases passed with 148 tests, 49 integration cases deselected; one existing upstream TestClient deprecation warning |
| `.venv/bin/ruff check .` | Passed |
| `.venv/bin/cache-service --help` | Passed; installed executable exposes all options and exits successfully |
| `git diff --check` | Passed |

Input is read and validated once before output is opened. Each iteration performs POST then GET
and flushes a JSON Lines record only after both responses validate. Errors produce safe stderr
diagnostics and a nonzero exit. One synchronous HTTP client serves the sequential loop, with
explicit connect/write/pool/read timeouts and no automatic retries. Local input limits use API
defaults; output files overwrite. README documents these policies and failure limitations.
Focused HTTP tests use MockTransport; actual service execution remains B17 evidence.
Personal CLI learning notes updated outside Git.


## B17 acceptance evidence

Verification on 2026-10-07:

| Check | Result and scope |
| --- | --- |
| Existing Compose database status | PostgreSQL 17 healthy on local port 55432; Docker socket denied in sandbox, approved read-only check passed |
| `.venv/bin/pytest tests/test_cli_integration.py -q` with `TEST_DATABASE_URL` | Approved execution passed: 2 live-service tests using a temporary Uvicorn server, installed CLI subprocesses and actual migrated PostgreSQL |
| Full `.venv/bin/pytest -q` with `TEST_DATABASE_URL` | Approved execution passed: 201 tests, including all unit and PostgreSQL integration tests; one existing upstream TestClient deprecation warning |
| `.venv/bin/ruff check .` | Passed |
| `git diff --check` | Passed |

The database URL was obtained from masked application settings and supplied through the test
process environment without printing it. Each live-service fixture uses an isolated transformer
version and deletes only its own rows. CLI subprocess environments omit database configuration.
Coverage includes every input/output mode, repeated-ID reuse across subprocesses, actual UTF-8
and newline encoding, minimized calls for duplicated strings, independently verified committed
storage, real HTTP 502 diagnostics, nonzero exit and preserved partial success. Unit coverage
also explicitly checks interrupt status and rejects invalid input before constructing a client.
The existing CI integration command discovers these tests without workflow changes; no hosted
B17 run has been observed yet. Docker deployment evidence remains B18. Personal notes updated.


## B19 acceptance evidence

Documentation reconciliation on 2026-10-07:

- README, API contract, requirements, architecture, verification, and repository guidelines
  now describe completed payload, cache, concurrency, CLI, and deployment work. Historical
  staged verification records above retain their original scope and outcomes.
- Added a configuration reference covering settings precedence, validated defaults, credentials,
  local versus container ports, explicit Compose budget overrides, and worker connection capacity.
  Local dependency installation uses `uv sync --locked`.
- Added a guarantee-to-test mapping, with named checks for validation, identity, cache reuse,
  transactions, failure recovery, publication, coordination, CLI, health, and deployment.
  Clarified evidence limits: controlled concurrency is not throughput evidence; GET's outer
  deadline has no dedicated slow-GET integration test; volume reuse is not backup/restore evidence.
- Clarified limits of the implemented service, including plaintext storage, no automatic expiry,
  no authentication or raw-body byte limit, validation responses that may include input, and
  repeated external work after ownership loss. No application behavior or schema was changed.
- Read and compared current settings, application, persistence, identity, CLI, Compose, Dockerfile,
  setup script, and test definitions. A stdlib documentation check passed for local link targets
  and all 37 named evidence references. All 14 documented numeric defaults matched Settings.
- `.venv/bin/cache-service --help`, `.venv/bin/ruff check .`, and `git diff --check` passed.
  No new pytest, Docker runtime, or hosted CI execution is claimed for this documentation change;
  prior runtime evidence remains recorded under B13–B18, and B20 requires final suite execution.
- Personal walkthrough notes updated outside Git. B20 is now ready; video and submission remain
  separate delivery work.


## B26 assessment compatibility follow-up

The first five submission gaps are resolved: assessment `/payload` routes, `list_1`/`list_2`
fields, installed `cache-cli`, short options `-r`/`-i`/`-j`/`-o`, and exact-sample verification.
Legacy routes, input names and `cache-service` remain supported. Internal canonical identity
is unchanged, so both wire spellings return the same stored UUID. Supplying both spellings
for a list is rejected. OpenAPI and public usage document the assessment names.

Full PostgreSQL/live HTTP/subprocess verification passed: 211 tests in 30.80 seconds,
with one upstream TestClient deprecation warning. Ruff, whitespace checks, CLI help and
locked offline package installation passed; no lockfile or migration changes were required.
See [verification](verification.md#assessment-compatibility-verification) for test mapping
and the initial empty-cache installation failure resolved by the successful retry.
No Docker rebuild or hosted CI rerun is claimed. Recorded in commit titled
`fix: add payload routes, JSON field aliases, and cache-cli options`. B22–B24 recording, hours reconciliation and publication/submission remain pending.
This adds compatibility at existing boundaries without a new architecture or request flow;
existing personal explanations remain applicable.
