# Implementation plan

Build in reviewable stages, with working behavior and verification developed together. The selected design is PostgreSQL, SQLAlchemy 2.x async access, per-string session advisory locks, and independent persistence of successful transformations. Follow the contracts in the architecture document during implementation.

Track current status, dependencies, requirement coverage, and executed evidence in the [implementation and submission backlog](backlog.md). Update it with each implementation change. This plan describes stage order; the backlog owns completion status.

## Stage 1 Requirements and design

Reconcile any task-author responses with the acceptance criteria. Database, coordination, transaction, versioning, and partial-success decisions are recorded. Identity and storage choices were delegated by the task author and are recorded in the README; reconcile any future changes with the design. Specify API response schemas, canonical encoding, input limits, CLI output format, and initial configurable timeout and capacity values before their implementation.

Exit evidence: each mandatory requirement has an acceptance check; consequential architecture decisions have clear rationale and limits.

## Stage 2 Runnable foundation

Create the minimal application, database configuration and lifecycle, dependency setup, and test harness. Keep configuration explicit and local secrets out of version control. Establish an initial schema migration and an explicit migration command. Add PostgreSQL Compose support at this stage so real database tests are available throughout development; complete deployment documentation in Stage 6.

Current status: foundation runtime verification passed on 2026-10-06. Dependencies and lockfile are available, lint and all three foundation tests pass, and Docker starts against a clean migrated PostgreSQL database. Both health endpoints return HTTP 200. See the backlog for commands and environment.

Exit evidence: application starts against a clean database and a real database integration test passes.

## Stage 3 Complete payload flow

Implement strict validation, replaceable uppercase transformation, alternating composition, payload persistence, identifier response, and retrieval. Establish stable input identity and database constraints. Add basic API and transformation tests with the implementation.

Exit evidence: valid creation and read work end to end; invalid input and unknown identifiers have defined responses; repeated input reuses its identifier.

## Stage 4 Transformation caching and concurrency

Deduplicate strings within a request, load cached values in batches, and implement the selected missing-work coordination. Acquire only one advisory lock at a time. Use the same physical connection for persistence, short READ COMMITTED transactions, bounded admission and lock waiting, and cancellation-protected cleanup. Invalidate connections when ownership or cleanup is uncertain. Handle uniqueness races and failures deliberately. Implement partial-success and retry policy.

Exit evidence: sequential and multi-process call-count tests prove coordination for identical and overlapping payloads. Saturated waiters do not prevent the holder from committing. Failed work never becomes a complete payload. Cancellation and exceptions release or invalidate ownership. Forced lock-key collisions preserve correct results. Inspect PostgreSQL transaction state to prove no transaction spans external work.

## Stage 5 CLI

Use Pydantic Settings for argument parsing and validation. Implement input sources, repeats, host selection, output destinations, and clear failures. Verify clean stdout, diagnostic stderr, and nonzero failure exit status. Address the short-option conflict in user documentation.

The B01 output policy is JSON Lines: emit a compact `id`/`output` object and newline after
each successful create/read iteration to stdout or a file. Stop on failure with a nonzero exit
status, preserving earlier complete records. Verify repeated IDs, embedded newline escaping,
and failure after a successful iteration. See the [planned CLI policy](../README.md#planned-cli-policy).

Exit evidence: automated tests exercise parsing and malformed input; an integration scenario creates and reads a payload through the real service.

## Stage 6 Deployment and persistence

Build Docker support for the selected database and process model. Document startup, persistent storage, configuration, and shutdown. Ensure advertised worker settings match the concurrency guarantee.

Exit evidence: clean build, request smoke test, and reuse after restart succeed using persistent storage.

## Stage 7 Review and delivery

Review requirements coverage, transaction boundaries, resource cleanup, test reliability, and unnecessary abstractions. Provide reproducible cache and concurrency demonstrations. Complete setup, usage, architecture, and limitations documentation.

Exit evidence: required checks pass; a reader can run the service from a clean checkout; documented guarantees match tests and deployment.

## Development history

Commit actual coherent development steps with relevant tests. Do not manufacture history or defer all verification to a final commit. Keep the planning baseline as an initial reviewable step, followed by implementation stages as they become complete.

## Review prompts

At each stage ask what happens on duplicate requests, overlapping work, transformer failure, database failure, cancellation, and restart. Consider algorithmic cost and database query count for growing inputs. Resolve material issues before advancing.
