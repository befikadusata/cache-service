# Architecture decisions

Use PostgreSQL with SQLAlchemy 2.x asynchronous database access, per-string session advisory locks, and short transactions. This design coordinates workers sharing the database while retaining successful transformations independently of complete payload publication. The task author delegated identity and storage decisions: select exact ordered inputs under the transformer version for identity, and PostgreSQL for complete payload storage. The README records these assumptions.

## Responsibility boundaries

HTTP handling validates input and translates application outcomes into responses. The application layer manages payload identity, transformation reuse, and composition. A replaceable transformer represents the external operation. Persistence owns queries, constraints, transaction boundaries, and connection-scoped coordination.

Start with these responsibilities rather than a framework of generic repositories or additional infrastructure. The implementation must remain straightforward to trace and change.

## Selected decisions and alternatives

| Decision | Selected approach | Reason and trade-off |
| --- | --- | --- |
| Database | PostgreSQL | Cross-worker coordination and practical concurrent writes; requires a database container |
| Database access | SQLAlchemy 2.x async engine | Explicit connection ownership and transactions; asynchronous resources require reliable cleanup |
| Coordination | Session advisory lock per transformation identity | No transaction needs to span the external operation; a connection remains occupied |
| Lock scope | One string at a time | No nested advisory locks and no multiple-lock ordering requirement; sequential missing-string processing |
| Payload identifier | Generated UUID associated with unique input digest | Separates public identity from deduplication; identifiers are not stable across fresh databases |
| Partial success | Commit successful transformations individually | Retries reuse work; a failed payload request may populate the cache |
| Publication | Insert complete payload in a short transaction | No incomplete payload can be read; competing inserts return the stored identifier |
| Deployment | Direct PostgreSQL connection and Docker Compose | Simple reviewer setup; transaction-mode PgBouncer is unsupported |

SQLite with one worker remains a simpler alternative but limits coordination to that process. Durable work claims would release connections during external work but add leases and ownership recovery. Neither durable claims nor advisory locks alone guarantee exactly one external call across crashes. Redis, queues, and background workers are outside current scope.

## Data model and identity

A transformation record stores its transformer version, source digest, exact source string, and successful result. A unique constraint covers version and source digest. Retain the source string to detect digest collisions; never return a cached result unless it matches the actual input.

A payload record stores a generated UUID, input digest, canonical input including transformer version, and complete output. The digest is unique. Retain canonical input for comparison on reuse and conflict resolution.

Use an explicitly specified canonical JSON encoding with fixed field names, consistent ordering, fixed separators, and UTF-8. Preserve list boundaries, element order, and exact string content. Use SHA-256 for database lookup keys rather than indexing unbounded source text. On a digest mismatch, fail explicitly rather than serving another input's data. Supporting both colliding values is outside scope.

Transformer version is an explicit implementation constant identifying behavior. Change it when transformation semantics change. Include it in both identity types and advisory-lock derivation. Existing payloads remain readable by identifier after a version change; the service does not automatically migrate or delete old cache entries.

Advisory keys use a stable signed 64-bit derivation of transformation identity, never Python's process-dependent hash. Different identities mapping to the same advisory key merely wait for each other because cache access still verifies actual identity. Reserve this key derivation for transformation coordination.

## Request flow

1. Validate input and compute canonical payload identity.
2. Look up a complete payload in a short transaction, verify identity, and return its stored identifier if present.
3. Deduplicate strings while preserving their first occurrence order. Batch-load existing transformations and verify source identity. Finish this transaction before coordination.
4. For each missing string, obtain a bounded admission slot before checking out a database connection. Do not retain another connection while waiting.
5. On that connection, acquire one session advisory lock with bounded database waiting. Finish the acquisition transaction while retaining the same physical connection.
6. Recheck the cache in a new short READ COMMITTED transaction. A previous owner may have committed while this request waited. Finish the transaction before transformation.
7. If still missing, run the external operation under a bounded timeout with no database transaction open.
8. On the same connection, insert the successful result with conflict handling. Read the stored row in a subsequent statement, verify identity, and commit before releasing the lock. Return the stored result rather than an uncommitted local value.
9. Release the lock explicitly, finish cleanup, return the connection, and release admission before processing another string.
10. Reconstruct alternating output in original order. Insert the complete payload with conflict handling, verify stored canonical identity, and return the authoritative identifier.

READ COMMITTED provides a fresh statement snapshot. A conflict can skip an insert because of a concurrent row not visible to that insert's snapshot; a subsequent read is necessary. Cache and payload records are immutable and are not concurrently deleted in this initial design. See [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html).

## Connection and cleanup contract

The lock holder reuses its connection for all work needed to persist its result. It must not acquire another pooled connection while holding the lock. Request code holds no database session across the transformation flow.

Session locks survive commits and rollbacks, and repeated acquisition by the same session stacks ownership. Acquire once and unlock once. On failure, roll back an aborted transaction before attempting unlock. Rollback alone does not release this lock. See [PostgreSQL advisory locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS).

Cleanup must run on success, failure, timeout, cancellation, and shutdown. Use bounded cancellation-protected cleanup. If acquisition outcome is uncertain, unlock cannot be confirmed, or connectivity is lost, invalidate the physical connection so it cannot reenter the pool carrying session state. Do not automatically reconnect and continue as though the original lock remained held.

Pool rollback-on-return is not our advisory-lock cleanup mechanism. Enable connection health checks for checkout, while recognizing that a connection can fail after checkout. Verify actual driver cancellation and invalidation behavior in integration tests. See [SQLAlchemy pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html).

## Capacity and timeout policy

Limit active coordination operations per process below the fixed pool capacity and disable uncontrolled overflow. Count lock waiters as occupied connections. Bound admission waiting as well as connection checkout. A holder never needs an additional connection, while spare capacity lets ordinary reads proceed. Calculate total database connection demand across all workers.

Use separate configurable budgets for admission, checkout, advisory waiting, transformation, ordinary database statements, cleanup, and overall payload generation. Input limits and an overall deadline prevent a large list from multiplying per-string timeouts indefinitely.

Use a blocking advisory acquisition with a transaction-local lock timeout. The statement timeout for that acquisition must permit the intended wait. Scope settings to the transaction so pooled connections do not leak configuration. The wait budget should normally accommodate transformation and persistence plus margin; it is not a correctness dependency. Lock-wait timeout limits waiting, not ownership duration. See [PostgreSQL timeout settings](https://www.postgresql.org/docs/current/runtime-config-client.html).

Never fall back to uncoordinated transformation after a lock timeout. Return 503 for admission, pool, lock-wait, or database unavailability; return 504 for transformer or overall-generation timeout; return 502 for an external transformation failure. Retry guidance should be explicit. Internal invariant or digest-collision failures return a generic server error and are logged without exposing raw input. Numeric defaults will be selected with the first integration measurements.

## Deployment and guarantees

Docker Compose will provide the API, PostgreSQL, a database health check, and persistent database storage. Schema migration runs as an explicit deployment step before workers start. All workers share identity encoding and transformer version.

Connect directly to PostgreSQL. Session advisory locks are incompatible with PgBouncer transaction pooling; ordinary SQLAlchemy pooling preserves a checked-out connection's session. See [PgBouncer compatibility](https://www.pgbouncer.org/features.html).

During healthy concurrent operation, cooperating workers share successful work for the same transformation identity, including overlapping payloads. Failed attempts remain retryable. Reads expose complete payloads only. Restart preserves committed cache results and identifiers.

A crash, lost database connection, timeout with ambiguous external completion, or persistence failure can cause transformation to repeat. If the session connection is lost during an external call, a new owner can begin while the old external work is still running. Do not claim universal exactly-once execution or a maximum of one repeat. Durable claims improve recovery but do not close the external completion gap without external-service idempotency.

## Required evidence

Prove API behavior, restart persistence, multi-process coordination, overlapping strings, timeout behavior, cleanup after cancellation, saturated pool progress, lock-key collision safety, and rejection of cache digest collisions. Verify that no transaction stays open during external work and that the lock is retained until the result commits.

## Changes requiring a design review

Parallelizing strings requires revisiting capacity and connection ownership. Bulk lock acquisition requires ordering actual lock keys. Transaction-mode pooling requires a different coordination mechanism. A future requirement for output-based identity or filesystem payload storage would require revisiting the selected identity and persistence decisions.
