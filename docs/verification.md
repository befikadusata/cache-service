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

## Concurrency evidence

Use controlled synchronization so requests actually overlap before a result is cached. Arbitrary sleeps alone can conceal races. Count transformer invocations by input value: one payload containing several distinct strings requires several transformations.

The selected deployment supports multiple workers: include a test across separate processes sharing PostgreSQL. A single-process test cannot establish that guarantee. Test restart separately from concurrent execution and state the remaining crash window.

`tests/test_multiprocess.py` exercises identical and overlapping requests in separate spawned
application processes. IPC reports transformer calls; an event pauses the first shared call
until PostgreSQL reports a real waiter on its advisory key. A fresh process then verifies
payload ID reuse and a new input composed from persisted strings without transformer calls.
The requests use in-process HTTP transport within each child; networked deployment evidence
is tracked separately in B18.

## CLI evidence

`tests/test_cli.py` covers Pydantic Settings parsing, help and environment isolation.
`tests/test_cli_execution.py` covers input and output modes, repeats, URL prefixes,
JSON Lines framing, incremental flushing, malformed responses, HTTP/network/file errors,
interrupts and preserving earlier records after later failure. HTTP unit tests use
MockTransport; they do not establish network or database behavior.

`tests/test_cli_integration.py` starts the current application through Uvicorn on a reserved
loopback socket and runs the installed `cache-service` executable in separate subprocesses.
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
real HTTP and PostgreSQL; Docker image startup and restart evidence remain B18 work.

## Demonstration

Show the first request producing transformations, an identical request reusing the payload identifier, a different request reusing strings, and overlapping requests sharing missing work. Expose call counts through test instrumentation or a demonstration harness without adding an unnecessary public API.

## Verification discipline

Run focused checks while implementing and the complete required suite before submission. Record actual commands and outcomes when available. Do not claim successful tests or deployment before executing them.
