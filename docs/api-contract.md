# Payload API contract (B04)

These are frozen implementation contracts. Payload routes are not available until B07;
coordination and deadline failure evidence follows in B11–B13.

`POST /payloads` accepts a JSON object containing exactly `list1` and `list2`.
Both must be arrays of strings of equal length. Missing fields, extra fields,
non-string elements, nulls, unequal lengths and exceeded limits return 422 using
FastAPI's validation error envelope (`detail` is a list). No coercion is allowed.
Whitespace, case, Unicode and duplicates are preserved. Two empty arrays are valid
and produce an empty output; empty strings are valid elements.

Successful creation and reuse both return 200 with `{"id": "<uuid>"}`.
Using one status lets the CLI treat retries identically. The identifier is a generated
UUID, separate from the input digest. B05 defines canonical identity.

`GET /payloads/{id}` accepts a UUID and returns 200 with `{"output": "..."}`.
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

Limits must be positive integers; deadlines must be positive finite numbers.
`PayloadCreate.model_validate(data, context={"settings": settings})` applies the
configured limits; without context it uses defaults. B07 must pass app settings
when validating requests. These are initial safety budgets, subject to integration
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
failure. Responses and logs must not expose raw input or database credentials.
Clients may retry 502/503/504 with bounded backoff using identical input; validation
failures require correcting input. Numeric coordination and cleanup budgets remain
B11 work. No uncoordinated fallback is permitted.
