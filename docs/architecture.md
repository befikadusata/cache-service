# Architecture options and decisions

The architecture must make cache behavior, concurrency, and failure handling explicit while keeping the service small. Database selection and coordination strategy remain open until the alternatives below have been evaluated.

## Responsibility boundaries

HTTP handling validates requests and translates results into responses. The application layer controls payload identity and generation. A replaceable transformer represents the external operation. Persistence owns database queries, constraints, and transaction handling.

Separate transformation reuse from payload reuse. A transformation record associates an exact source string with a successful result. A payload record associates an input identity with its identifier and complete output. Coordination state may be needed depending on the selected design.

## Proposed request flow

1. Validate both lists and compute their ordered input identity.
2. Return the identifier if a complete payload already exists.
3. Find distinct strings across both lists and retrieve existing transformations in batches.
4. Coordinate ownership of missing transformations and recheck the cache after obtaining ownership.
5. Transform missing strings under a defined timeout and concurrency policy; persist only successful results.
6. Reconstruct alternating output using original order and duplicate positions.
7. Persist a complete payload using a uniqueness constraint, resolving competing creation to the existing identifier.

A database transaction must not accidentally remain open for the entire external operation. If coordination deliberately holds a transaction or connection, document its duration, timeout, and contention consequences.

## Database and coordination alternatives

| Option | Benefits | Limits and costs |
| --- | --- | --- |
| SQLite with process-local coordination and one application worker | Small deployment; simple persistence and coordination | Coordination does not cover multiple processes or instances; deployment restriction must be explicit |
| PostgreSQL with database-backed locks | Coordinates across workers sharing the database | Connection use, lock ordering, cancellation, and lock duration need deliberate handling |
| PostgreSQL with durable work claims | Makes ownership and recovery state explicit | Leases, abandoned work, retries, and state transitions add significant complexity |

Choose one approach after comparing supported guarantees, operational burden, and explainability. Redis is not required by the assessment. Neither PostgreSQL nor SQLite is selected yet.

## Payload identity alternatives

Canonical serialization must preserve list boundaries, element order, and exact string content. Simple concatenation is ambiguous.

A deterministic digest can serve as a lookup key and optionally the public identifier. Alternatively, store a generated identifier against a unique input key. Both can satisfy reuse; deterministic public identifiers are not mandatory. Decide how canonical input is retained and how a digest collision would be recognized. Transformer versioning is optional and should be added only with a defined invalidation policy.

## Guarantees to decide and prove

- Repeated completed requests reuse identifiers and successful transformations.
- Concurrent requests share missing-string work within the selected deployment model.
- Different payloads sharing a string participate in the same coordination.
- No partially generated payload becomes readable.
- Failed transformations remain retryable.
- Successful partial transformation work either survives or rolls back according to an explicit policy.
- Crash recovery does not leave ownership permanently stuck.

Exactly one external call across every crash boundary is not automatically guaranteed. A process can finish an external operation and crash before persisting its result. Distinguish stored-result correctness from external-call deduplication.

## Decision record format

For each consequential choice, record the problem, alternatives, selected approach, rationale, supported guarantees, limitations, verification, and consequences for future changes. Keep records short and revise provisional choices when clarification arrives.
