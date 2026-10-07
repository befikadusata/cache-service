# Architecture decisions

Use PostgreSQL with SQLAlchemy 2.x asynchronous database access, per-string session advisory locks, and short transactions. This design coordinates workers sharing the database while retaining successful transformations independently of complete payload publication. The task author delegated identity and storage decisions: select exact ordered inputs under the transformer version for identity, and PostgreSQL for complete payload storage. The README records these assumptions.

## Responsibility boundaries

HTTP handling validates input and translates application outcomes into responses. The application layer manages payload identity, transformation reuse, and composition. A replaceable transformer represents the external operation. Persistence owns queries, constraints, transaction boundaries, and connection-scoped coordination.

Start with these responsibilities rather than a framework of generic repositories or additional infrastructure. The implementation must remain straightforward to trace and change.

B06 implements `src/cache_service/transformation.py`: `Transformer` is an async callable
protocol, and `uppercase_transform` implements the `uppercase-v1` identity semantics using
Python's Unicode `str.upper()`. Whitespace and punctuation remain intact; some Unicode
characters expand, such as `ß` becoming `SS`. Replacements must use the matching identity
version when their semantics change. Transformer exceptions propagate to the application
layer for HTTP mapping and successful-result-only caching.

`compose_output` accepts already transformed sequences, alternates their elements and joins
them with `, `. It preserves duplicates and empty elements, returns `""` for two empty
sequences, and rejects unequal lengths rather than silently truncating. Keeping composition
separate lets subsequent request code combine cached and newly transformed results without
invoking the transformer again. Endpoint orchestration is implemented in B07.

B07 implements `payloads.py` and the POST/GET routes in `main.py`. Payload lookup closes its
connection before transformation. Successful generation publishes only a complete output in a
short transaction, uses `ON CONFLICT (input_digest) DO NOTHING`, then verifies the authoritative
row in a separate READ COMMITTED statement before returning its UUID after commit. Both initial
lookup and conflict readback reject mismatched canonical identities. GET reads by UUID, independent
of the current transformer version. The app factory accepts a replacement transformer and version.

B09 adds `cache.py`: deduplicate exact strings in first-occurrence order, compute versioned
identities and load cache rows in batches of at most 500 digests. Each row's source and version
must match before reuse. The read connection closes before transformation. For each miss,
transform once within the request, insert the successful result in its own short transaction
with `ON CONFLICT (version, source_digest) DO NOTHING`, then read and verify the authoritative
row in a separate statement. Use its result only after commit. Reconstruct original list order
and duplicates from the result mapping before composing and publishing the payload.

Successful transformations survive a later failure, timeout or cancellation. Failed operations
are not inserted as results. Empty input avoids cache access. Request-local digest collisions
are rejected before database lookup. The existing `0001` schema supports this flow unchanged.
B10 adds one session advisory lock per missing string. The acquisition transaction commits,
then a new short transaction rechecks and verifies the cache. If still missing, transformation
runs without an open transaction while retaining the connection. Persistence and authoritative
readback use that same connection and commit before explicit unlock. Each connection returns
before the next string begins. On any exception, including acquisition uncertainty or failed
unlock, invalidate the connection rather than returning possible session ownership to the pool.
B11 uses transaction-local lock and statement timeouts for acquisition, admission below fixed
pool capacity, an external-operation deadline, and bounded cancellation-protected cleanup.
B13 verifies forced backend loss and ownership loss. B14 verifies separate spawned application
processes sharing PostgreSQL, including actual lock contention, per-source call counts,
identical IDs and reuse after process restart; see `tests/test_multiprocess.py`.
Healthy concurrent sessions now serialize shared misses and reuse committed results.
Configured overall deadlines and generic error responses are wired; 503 includes Retry-After. PostgreSQL text storage does not support every possible
Python string, including NUL and lone surrogate values; such storage failures return a generic
error and never a successful identifier.

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

Identity helpers are implemented in `src/cache_service/identity.py` and accept already validated inputs. Canonical JSON uses lexicographically sorted keys, separators `,` and `:`, no formatting whitespace, and ASCII Unicode escapes (`ensure_ascii=True`). Hash the resulting text encoded as UTF-8 with SHA-256, retaining the full 32-byte digest. The public fields `list_1`/`list_2` and legacy fields `list1`/`list2` map to the same internal attributes, so wire aliases do not change persisted identity. Payload identity objects contain exactly `list1`, `list2`, and `version`; transformation objects contain exactly `source` and `version`. For example, empty payload input is `{"list1":[],"list2":[],"version":"uppercase-v1"}`. Preserve list boundaries, element order, duplicate multiplicity, case, whitespace, and exact Unicode code points without normalization. ASCII escaping is a representation choice and does not expand the database's supported text values.

Use SHA-256 for database lookup keys rather than indexing unbounded source text. Despite its column name, `source_digest` hashes the canonical transformation object including version; the database primary key retains its separate version column. After every lookup or conflict readback, compare retained canonical input for payloads, or both version and exact source for transformations. The identity helpers raise `IdentityCollisionError` on mismatch with a fixed message containing no raw input. Supporting both colliding values is outside scope. Payload persistence and HTTP collision mapping are implemented in B07; transformation-cache persistence is implemented in B09, and coordination error mapping is implemented in `main.py`.

Transformer version is an explicit implementation constant identifying behavior. Change it when transformation semantics change. Include it in both identity types and advisory-lock derivation. Existing payloads remain readable by identifier after a version change; the service does not automatically migrate or delete old cache entries.

Advisory keys hash the byte prefix `b"cache-service:transformation-lock:v1\x00"` followed by the full transformation digest with SHA-256. Interpret the first eight bytes as a signed big-endian 64-bit integer, compatible with PostgreSQL's single-bigint advisory lock functions. This derivation is stable across processes and reserved for transformation coordination. Different identities mapping to the same advisory key merely wait for each other because cache access still uses the full digest and verifies retained identity. Lock keys never establish cache equality. The encoding, transformer version, and lock derivation must agree across workers; changing them requires a coordinated rollout.

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

The lock holder reuses its connection for all work needed to persist its result. It must not acquire another pooled connection while holding the lock. Payload orchestration holds no separate database connection while the cache layer
retains its checked-out lock session during a missing-string transformation.

Session locks survive commits and rollbacks, and repeated acquisition by the same session stacks ownership. Acquire once and unlock once. On failure, roll back an aborted transaction before attempting unlock. Rollback alone does not release this lock. See [PostgreSQL advisory locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS).

Cleanup must run on success, failure, timeout, cancellation, and shutdown. Use bounded cancellation-protected cleanup. If acquisition outcome is uncertain, unlock cannot be confirmed, or connectivity is lost, invalidate the physical connection so it cannot reenter the pool carrying session state. Do not automatically reconnect and continue as though the original lock remained held.

Pool rollback-on-return is not our advisory-lock cleanup mechanism. Enable connection health checks for checkout, while recognizing that a connection can fail after checkout. Verify actual driver cancellation and invalidation behavior in integration tests. See [SQLAlchemy pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html).

## Capacity and timeout policy

Limit active coordination operations per process below the fixed pool capacity and disable uncontrolled overflow. Count lock waiters as occupied connections. Bound admission waiting as well as connection checkout. A holder never needs an additional connection, while spare capacity lets ordinary reads proceed. Calculate total database connection demand across all workers.

Use separate configurable budgets for admission, checkout, advisory waiting, transformation, ordinary database statements, cleanup, and overall payload generation. Input limits and an overall deadline prevent a large list from multiplying per-string timeouts indefinitely.

Use a blocking advisory acquisition with a transaction-local lock timeout. The statement timeout for that acquisition must permit the intended wait. Scope settings to the transaction so pooled connections do not leak configuration. The wait budget should normally accommodate transformation and persistence plus margin; it is not a correctness dependency. Lock-wait timeout limits waiting, not ownership duration. See [PostgreSQL timeout settings](https://www.postgresql.org/docs/current/runtime-config-client.html).

Never fall back to uncoordinated transformation after a lock timeout. Return 503 for admission, pool, lock-wait, or database unavailability; return 504 for transformer or overall-generation timeout; return 502 for an external transformation failure. Retry guidance should be explicit. Internal invariant or digest-collision failures return a generic server error and are logged without exposing raw input. Input, deadline, and coordination defaults are defined in the [API contract](api-contract.md); synthetic timeout and recovery tests verify
mechanics rather than establish production performance.

## Deployment and guarantees

Docker Compose provides the API, PostgreSQL, a database health check, and persistent database
storage. The migration service waits for healthy PostgreSQL; the API depends on its successful
completion. Schema migration runs before workers start. The image runs one Uvicorn worker by
default; multiple workers use the same factory with `--workers N`. Each worker owns its engine,
fixed pool and admission semaphore. Budget up to `N × POOL_SIZE` application connections plus
migration and administration connections; default capacity is ten pooled connections and eight
coordination slots per worker. All workers share identity encoding and transformer version.
Separate-process coordination evidence is B14; the isolated Docker startup and persistence
procedure is described in [verification](verification.md#docker-deployment).

Connect directly to PostgreSQL. Session advisory locks are incompatible with PgBouncer transaction pooling; ordinary SQLAlchemy pooling preserves a checked-out connection's session. See [PgBouncer compatibility](https://www.pgbouncer.org/features.html).

During healthy concurrent operation, cooperating workers share successful work for the same transformation identity, including overlapping payloads. Failed attempts remain retryable. Reads expose complete payloads only. Restart preserves committed cache results and identifiers.

A crash, lost database connection, timeout with ambiguous external completion, or persistence failure can cause transformation to repeat. If the session connection is lost during an external call, a new owner can begin while the old external work is still running. B13 verifies this window by terminating the holder's PostgreSQL backend while its transformer is paused: another application completes the same input, while the original request fails with 503 and cannot replace the committed result. Do not claim universal exactly-once execution or a maximum of one repeat. Durable claims improve recovery but do not close the external completion gap without external-service idempotency.

## Required evidence

Prove API behavior, restart persistence, multi-process coordination, overlapping strings, timeout behavior, cleanup after cancellation, saturated pool progress, lock-key collision safety, and rejection of cache digest collisions. Verify that no transaction stays open during external work and that the lock is retained until the result commits.

## Changes requiring a design review

Parallelizing strings requires revisiting capacity and connection ownership. Bulk lock acquisition requires ordering actual lock keys. Transaction-mode pooling requires a different coordination mechanism. A future requirement for output-based identity or filesystem payload storage would require revisiting the selected identity and persistence decisions.


## Coordination implementation trace

`create_engine` attaches one `Coordination` instance to engine execution options. Its semaphore
is shared by every cache operation using that application engine. Admission ends before checkout
begins; admission remains held through cleanup. No extra connection is acquired while a lock is
held. Pool overflow stays disabled and configured slots must leave at least one spare connection.

`cache.py` sets transaction-local lock_timeout and statement_timeout before acquiring one key.
The cache recheck and insertion retain their short transaction boundaries. Each transformer call
has an independent timeout; the outer POST timeout still limits total generation.

`coordination.py` owns release and disposal. Success unlocks and closes. Any interrupted body,
including uncertain acquisition, invalidates the physical connection instead of pooling it.
A separate cleanup task is shielded and awaited even after repeated request cancellation.
Half the cleanup budget allows graceful cleanup; if that fails, the captured asyncpg driver
socket is synchronously terminated and the remaining half bounds invalidation and close.
A failed or unconfirmed unlock returns 503. The admission slot releases after disposal finishes.
The force-close path deliberately depends on the selected asyncpg driver.
