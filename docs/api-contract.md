# Payload API contract

Payload routes enforce configured input validation and overall POST/GET deadlines.
Per-string caching, bounded coordination, and protected cleanup are implemented.
See [guarantee evidence](verification.md#guarantee-evidence) for supporting tests and scope.

`POST /payload` accepts a JSON object containing exactly `list_1` and `list_2`.
The legacy `/payloads` routes and `list1`/`list2` fields remain accepted. Either
spelling maps to the same internal identity and stored UUID. Supplying both spellings
for one list is rejected as extra input. OpenAPI presents only the assessment names.
Both must be arrays of strings of equal length. Missing fields, extra fields,
non-string elements, nulls, unequal lengths and exceeded limits return 422 using
FastAPI's validation error envelope (`detail` is a list). No coercion is allowed.
Whitespace, case, Unicode and duplicates are preserved. Two empty arrays are valid
and produce an empty output; empty strings are valid elements.

Successful creation and reuse both return 200 with `{"id": "<uuid>"}`.
Using one status lets the CLI treat retries identically. The identifier is a generated
UUID, separate from the input digest. B05 defines canonical identity.

`GET /payload/{id}` accepts a UUID and returns 200 with `{"output": "..."}`.
Output alternates transformed list1 and list2 elements, joined by comma and space.
Malformed UUIDs return 422; a syntactically valid unknown UUID returns 404 with
`{"detail": "Payload not found"}`. Existing payloads remain readable after a
transformer version change.

## Limits and deadlines

| Environment setting | Default | Scope |
| --- | --- | --- |
| MAX_LIST_ITEMS | 100 | Items in each list |
| MAX_STRING_CHARACTERS | 10000 | Unicode code points in each source string |
| MAX_TOTAL_CHARACTERS | 100000 | Sum of code points across both lists, including duplicates |
| GENERATION_TIMEOUT_SECONDS | 60 | Overall POST application work after input validation |
| READ_TIMEOUT_SECONDS | 10 | Overall GET database lookup |
| POOL_SIZE | 10 | Fixed connections per application worker; no overflow |
| COORDINATION_SLOTS | 8 | Active missing-string holders and waiters; less than POOL_SIZE |
| ADMISSION_TIMEOUT_SECONDS | 5 | Wait before checking out a coordination connection |
| POOL_TIMEOUT_SECONDS | 5 | Pool checkout; coordination also bounds total checkout elapsed time |
| DATABASE_CONNECT_TIMEOUT_SECONDS | 5 | Driver connection establishment |
| DATABASE_STATEMENT_TIMEOUT_SECONDS | 5 | Ordinary PostgreSQL statements |
| ADVISORY_LOCK_TIMEOUT_SECONDS | 35 | Transaction-local advisory waiting; at least 0.001 seconds |
| TRANSFORMATION_TIMEOUT_SECONDS | 30 | Each external transformation call |
| CLEANUP_TIMEOUT_SECONDS | 5 | Cleanup, split between graceful release and forced disposal |

Input limits must be positive integers; deadlines must be positive finite numbers.
POOL_SIZE must be between 2 and 100 and COORDINATION_SLOTS must be at least 1 and
less than POOL_SIZE. See [configuration](configuration.md) for environment propagation.
`PayloadCreate.model_validate(data, context={"settings": settings})` applies the
configured limits; without context it uses defaults. POST validation passes app settings,
including when configured limits exceed defaults. These are initial safety budgets, subject to integration
measurements. Character limits do not bound raw HTTP bytes, JSON whitespace or
uppercase expansion. Transport/body-read limits are outside this contract.

Deadlines use monotonic elapsed time and include database and admission waits,
transformation, and publication. They exclude body reading, validation, response
transmission, and bounded resource cleanup. Cleanup may extend response latency;
a deadline is not a guarantee that remote work stopped or a commit did not occur.
Retries reuse already committed results.

Operational errors use `{"detail": "<generic message>"}`: 503 for admission,
pool, lock-wait or database unavailability; 504 for transformation or overall
request deadline; 502 for transformer failure; 500 for invariant or digest collision
failure. Operational responses and application warning messages omit raw input and database credentials.
FastAPI validation errors may include the submitted value in their `input` field.
Clients may retry 502/503/504 with bounded backoff using identical input; validation
failures require correcting input. No uncoordinated fallback is permitted.


B11 waits for admission before connection checkout and releases admission only after cleanup.
Advisory acquisition uses transaction-local lock_timeout and a statement_timeout one second
longer than the lock budget; both revert at transaction end. Timeout never triggers an
uncoordinated transformer call. Cleanup is shielded against repeated request cancellation.
Failure invalidates the session; failed unlock or stalled graceful cleanup force-terminates
its asyncpg socket before invalidation and close. Cleanup can extend the overall request deadline
by its configured budget. These bounds rely on cooperative async operations and an available
event loop; a blocking transformer must be adapted before use.

Payload-operation 503 responses include Retry-After: 1. Clients may retry with backoff; 502 and 504 retries can
reuse committed transformations but may repeat externally completed, uncommitted work.
