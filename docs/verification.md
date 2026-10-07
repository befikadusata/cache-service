# Verification strategy

Verify externally observable behavior and cache guarantees. Unit tests isolate transformation and composition; integration tests use the selected real database and exercise HTTP behavior. Concurrency evidence must match the deployed worker model.

## Required scenarios

| Scenario | Expected evidence |
| --- | --- |
| Valid lists | Correct alternating output and identifier |
| Unequal lengths or invalid item types | Validation rejection with no generated payload |
| Empty lists and strings | Behavior matches documented policy |
| Duplicate strings in one request | One successful transformation per distinct uncached string |
| Strings reused by different payloads | Previously stored outcomes avoid new calls |
| Same ordered input submitted again | Same identifier |
| Distinct input with equal uppercase output | Identity follows the agreed input or output policy |
| Application restarted against existing storage | Cache and identifiers remain reusable |
| Unknown identifier | 404 response |
| Simultaneous identical requests | Same identifier; transformer call count matches the declared guarantee |
| Simultaneous different payloads sharing strings | Shared missing strings are coordinated |
| Transformer fails after some strings succeed | No complete payload; partial-success and retry policy respected |
| Timeout or cancellation after an earlier success | Committed result survives; fresh-application retry transforms only misses |
| Payload publication fails after INSERT or before commit | Payload rolls back; attempted UUID is unreadable; retry reuses all committed transformations |
| Database conflicts or failure | No misleading success response or corrupt state |
| Cancellation during acquisition or transformation | Lock released or physical connection invalidated; next request can proceed |
| Many waiters exceeding pool capacity | Bounded waiting and retryable errors; holder completes without another connection |
| Forced advisory-key collision | Unrelated strings serialize but retain their correct values |
| Forced cache or payload digest collision | Mismatched original identity is rejected; incorrect result is never returned |
| Transformer version change | New work uses the new version; old payload remains readable |
| Connection loss during transformation | No assumption of retained lock; outcome follows documented repeat-work limitation |
| Slow transformation | Configured deadline applies; no transaction remains open during the call |
| CLI parsing and I/O | All declared modes work; invalid inputs and server failures produce useful errors |

## Guarantee evidence

These references map current documentation to implemented checks. Recorded execution outcomes
are in the [backlog](backlog.md); this mapping does not claim a new full-suite run. PostgreSQL
checks require a migrated database and `TEST_DATABASE_URL`; they skip when it is absent.

| Documented behavior | Supporting checks | Scope and limits |
| --- | --- | --- |
| Strict lists, equal lengths, configured character/item limits, invalid JSON/UUID rejection | [Schemas](../tests/test_schemas.py), [payload validation](../tests/test_payloads.py): `test_invalid_payload_is_rejected_before_database_access`, `test_request_validation_uses_configured_limits`, `test_custom_limit_can_exceed_default`, `test_malformed_json_and_uuid_are_rejected_before_database_access` | Application validation; no raw-body byte limit |
| Unicode uppercase and alternating output, duplicates and empty elements | [Transformation tests](../tests/test_transformation.py), [payload tests](../tests/test_payloads.py): `test_empty_and_unknown_payload`, `test_create_read_reuse_and_restart` | Current uppercase implementation; output is a joined string, not a reversible list encoding |
| Exact ordered identity; case, whitespace, boundaries, order, version affect reuse | [Identity vectors](../tests/test_identity.py), [payload tests](../tests/test_payloads.py): `test_api_identity_preserves_exact_ordered_inputs`, `test_version_change_creates_new_id_and_keeps_old_payload_readable` | UUIDs persist in existing storage; new databases generate new IDs |
| Known ID retrieval, 404 for unknown ID, same ID on reuse and concurrent publication | [Payload tests](../tests/test_payloads.py): `test_create_read_reuse_and_restart`, `test_empty_and_unknown_payload`, `test_concurrent_publication_returns_authoritative_id` | Complete committed payloads only |
| Distinct-source deduplication, batched reads, reuse across payloads/restart | [Cache tests](../tests/test_cache.py): `test_deduplication_batch_reads_and_no_transaction_during_transform`, `test_large_cached_request_uses_bounded_batches`, `test_payload_overlap_and_restart_reuse_cached_strings` | Batches of at most 500 digests; misses processed sequentially |
| Commit before unlock; no transaction during transformation; same session recheck | [Cache tests](../tests/test_cache.py): `test_concurrent_miss_waits_then_rechecks_on_same_session`, `test_deduplication_batch_reads_and_no_transaction_during_transform` | A physical connection remains occupied during the call |
| Healthy concurrent workers share successful missing-string work | [Separate-process tests](../tests/test_multiprocess.py): `test_processes_coordinate_calls_and_restart_reuses_storage` | Identical/overlapping payloads with real advisory contention; no throughput claim |
| Successful results survive later failure, timeout, cancellation, or publication rollback | [Payload tests](../tests/test_payloads.py): `test_partial_success_survives_interruption_and_restart`, `test_publication_rollback_preserves_cache_and_retry_avoids_transform`; [cache tests](../tests/test_cache.py): `test_failure_retains_successful_results_and_retries_only_misses` | Complete payload rolls back; prior per-string commits remain |
| Admission, checkout and advisory waiting fail safely without uncoordinated fallback | [Coordination tests](../tests/test_coordination.py): `test_saturated_admission_preserves_read_capacity_and_recovers`, `test_checkout_timeout_releases_admission`, `test_lock_wait_timeout_does_not_transform_and_retry_succeeds`, `test_admission_failure_returns_retryable_503` | Controlled capacity settings; 503 with Retry-After for payload operations |
| Transformer, generation and read deadlines | [Coordination tests](../tests/test_coordination.py): `test_transform_deadline_returns_504_and_releases_connection`; [payload tests](../tests/test_payloads.py): `test_generation_deadline_does_not_publish_and_retry_succeeds`, `test_read_deadline_releases_connection_and_retry_succeeds` | Cooperative async work; cleanup can extend response latency. GET test blocks SELECT with a real PostgreSQL table lock, verifies 504 and connection return, then retries successfully |
| Cancellation, uncertain acquisition, failed unlock, and stalled cleanup dispose ownership | [Coordination tests](../tests/test_coordination.py): `test_cleanup_survives_repeated_cancellation`, `test_cancellation_during_server_lock_wait_releases_capacity`, `test_uncertain_acquisition_is_discarded_and_wait_settings_do_not_leak`, `test_cleanup_timeout_force_closes_session_and_releases_lock`, `test_unconfirmed_unlock_discards_session_and_preserves_committed_result` | Force-close path depends on asyncpg and an available event loop |
| Lock-key collisions serialize safely; digest collisions never reuse mismatched data | [Coordination tests](../tests/test_coordination.py): `test_advisory_key_collision_serializes_without_reusing_wrong_result`; [cache tests](../tests/test_cache.py): `test_collision_is_rejected_at_lookup_and_readback`; [payload tests](../tests/test_payloads.py): `test_payload_digest_collision_is_rejected`, `test_collision_on_publication_readback_is_rejected` | Forced collisions establish rejection; storage does not support both colliding identities |
| Connection loss can repeat external work without stale publication | [Coordination tests](../tests/test_coordination.py): `test_backend_loss_allows_repeat_work_but_never_publishes_stale_result` | Backend terminated while transformer is paused; no universal exactly-once guarantee |
| CLI flags, environment isolation, input/output modes, incremental JSON Lines, safe failures | [Parsing](../tests/test_cli.py), [execution](../tests/test_cli_execution.py), [live CLI](../tests/test_cli_integration.py) | MockTransport unit checks plus live Uvicorn/PostgreSQL subprocess checks; no automatic retries |
| Masked connection diagnostics, valid settings, health checks | [Database settings](../tests/test_database_settings.py), [foundation](../tests/test_foundation.py), [coordination settings](../tests/test_coordination.py): `test_capacity_and_budgets_are_validated` | Readiness checks connectivity and two tables, not all schema constraints; validation responses may echo input |
| Packaged startup, clean migration, HTTP/CLI access, cache and ID reuse after recreation | [Deployment script](../scripts/verify_deployment.py), [procedure](#docker-deployment) | Fresh isolated Docker project, one worker, retained volume; no backup/restore test |

## Concurrency evidence

Use controlled synchronization so requests actually overlap before a result is cached. Arbitrary sleeps alone can conceal races. Count transformer invocations by input value: one payload containing several distinct strings requires several transformations.

The selected deployment supports multiple workers: include a test across separate processes sharing PostgreSQL. A single-process test cannot establish that guarantee. Test restart separately from concurrent execution and state the remaining crash window.

`tests/test_multiprocess.py` exercises identical and overlapping requests in separate spawned
application processes. IPC reports transformer calls; an event pauses the first shared call
until PostgreSQL reports a real waiter on its advisory key. A fresh process then verifies
payload ID reuse and a new input composed from persisted strings without transformer calls.
The requests use in-process HTTP transport within each child; networked deployment evidence
is recorded in the [Docker deployment procedure](#docker-deployment).

## CLI evidence

`tests/test_cli.py` covers Pydantic Settings parsing, help and environment isolation.
`tests/test_cli_execution.py` covers input and output modes, repeats, URL prefixes,
JSON Lines framing, incremental flushing, malformed responses, HTTP/network/file errors,
interrupts and preserving earlier records after later failure. HTTP unit tests use
MockTransport; they do not establish network or database behavior.

`tests/test_cli_integration.py` starts the current application through Uvicorn on a reserved
loopback socket and runs the installed `cache-cli` and compatibility `cache-service`
executables in separate subprocesses.
It uses the migrated PostgreSQL database specified by `TEST_DATABASE_URL`. Inline JSON,
UTF-8 files, stdin, stdout and output files produce identical results and reuse the stored
ID across CLI processes. Newline/Unicode output survives JSON Lines encoding. Instrumented
transformer calls and independent database queries verify deduplication and committed output.
A real transformer failure verifies HTTP 502 diagnostics, nonzero exit, no payload publication
and retained partial cache success. Test-specific transformer versions isolate storage; cleanup
removes only rows belonging to those versions. Server tasks and CLI subprocesses have bounded shutdown.

After `uv sync --locked` and migration, run:

```sh
uv run pytest tests/test_cli.py tests/test_cli_execution.py -q
# Export TEST_DATABASE_URL securely; do not print its value.
uv run pytest tests/test_cli_integration.py -q
```

The normal integration suite and CI include these tests. This verifies current source over
real HTTP and PostgreSQL; the [Docker deployment check](#docker-deployment) verifies
packaged startup and restart persistence separately.

## Assessment compatibility verification

On 2026-10-07, the assessment paths and field names were added with compatibility for
existing callers. `test_assessment_sample_routes_fields_and_cli` exercises the exact
sample through `POST /payload` and `GET /payload/{id}` against live HTTP and PostgreSQL.
It checks the expected interleaved output, legacy route/input reuse of the same UUID,
OpenAPI paths, and the installed `cache-cli` with `-j`, `-r`, `-i`, and `-o`.
File and stdin inputs and file/stdout outputs reuse the stored result without extra
transformer calls. Parser/schema tests also check strict validation and duplicate spellings.

| Executed check | Result |
| --- | --- |
| `uv sync --locked --offline` using the existing cache outside the sandbox | Passed; both CLI entry points installed; lockfile unchanged |
| Full `.venv/bin/pytest -q --tb=short` with securely supplied `TEST_DATABASE_URL` | 211 passed in 30.80 seconds; one upstream TestClient deprecation warning |
| `.venv/bin/ruff check .` and `git diff --check` | Passed |
| `.venv/bin/cache-cli --help` | Passed; short options displayed; `-h` remains help |

The initial offline sync with an empty temporary cache could not find Hatchling; retry
using the existing cache succeeded. No migration was needed because internal identity
encoding and stored records are unchanged. Docker build/deployment was not repeated in
this follow-up; the earlier deployment evidence remains historical.

## Docker deployment

Run from the repository root with Docker access and Docker Compose 2.24.4 or newer:

```sh
python3 scripts/verify_deployment.py
```

The script creates a unique Compose project, generated credentials and a fresh volume. It
does not read `.env`, publishes no database port, and assigns an available localhost API port.
It performs a no-cache image build, checks migration completion and Alembic head, polls
readiness with a deadline, and verifies both health endpoints. The CLI installed in the image
creates and reads payloads over HTTP; an independent host HTTP request verifies retrieval.
Direct database queries verify complete publication and three distinct cached transformations.

After stopping and recreating the database and API containers with the same volume, it checks
the old UUID and identical-input reuse. A mounted verification-only factory replaces the
transformer with a rejecting callable under the existing transformer version. A new reordered
payload must succeed entirely from persisted transformations; uncached input must return 502,
proving the probe is active. Persisted cache records must match the pre-recreation snapshot.
Application code still comes from the built image. The probe adds no production endpoint or
setting. This check runs one worker; B14 supplies controlled separate-process contention and
call-count evidence. Neither check establishes production throughput or universal exactly-once
execution across crashes.

Commands have bounded timeouts and failures return nonzero. Captured container diagnostics
are omitted to avoid exposing credentials. On failure, inspect the named project's containers
and logs locally, taking care not to share secrets. The script stops its containers in cleanup
and prints the retained volume name. Existing projects and volumes are untouched; no volume
is removed automatically. Docker dependency installation still resolves the ranges in
`pyproject.toml`; local development and CI use `uv.lock`.

## Demonstration

Show the first request producing transformations, an identical request reusing the payload identifier, a different request reusing strings, and overlapping requests sharing missing work. Expose call counts through test instrumentation or a demonstration harness without adding an unnecessary public API.

## Verification discipline

Run focused checks while implementing and the complete required suite before submission. Record actual commands and outcomes when available. Do not claim successful tests or deployment before executing them.
