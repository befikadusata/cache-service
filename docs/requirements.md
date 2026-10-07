# Requirements and acceptance criteria

The service must satisfy the supplied Python caching assessment. Required behavior is separated from documented assumptions and additional reliability goals so that implementation choices remain reviewable.

## Required behavior

| Requirement | Acceptance evidence |
| --- | --- |
| FastAPI creation endpoint accepts two equal-length lists of strings | Valid request returns a payload identifier; invalid shape or unequal lengths is rejected |
| Transform strings and interleave the two lists | Output follows alternating list order and the sample comma-and-space format |
| Read endpoint returns the generated payload | Known identifier returns an output object; unknown identifier returns 404 |
| Reuse transformer outcomes across requests | Call-count tests show successful cached strings do not trigger another transformation |
| Reuse identifiers for previously generated payloads | Repeated equivalent requests return the existing identifier under the documented identity rule |
| Persist cached transformations in SQLite or PostgreSQL | Integration test verifies reuse after application restart |
| Use SQLAlchemy or SQLModel | Persistence goes through the selected supported library |
| Provide a CLI using Pydantic Settings for argument parsing and validation | Exercise host, repeat, input file or stdin, inline JSON, output file or stdout, and help |
| Dockerize the application | Build and run checks verify API access and documented database persistence |
| Demonstrate unit and integration testing | Tests cover isolated transformation behavior and real API/database interaction |

## Delegated decisions and assumptions

The task author responded that both payload identity and storage are our call and requested assumptions in the README. These choices are now selected rather than awaiting confirmation.

| Topic | Selected interpretation | Affected decisions |
| --- | --- | --- |
| Payload reuse | Identical ordered input lists under the same transformer version | Identity key and reuse tests; equal output alone does not imply reuse |
| Payload files | Complete generated payloads stored in PostgreSQL, without filesystem files | Storage model, atomic publication and deployment |
| Transformer | Deterministic uppercase conversion following the sample | Implementation assumption, not a separately confirmed contract |

See the [README design decisions](../README.md#design-decisions) for rationale. Revisit these choices if new instructions change the contract.

## Input and CLI policy

- Match `/payload`, `/payload/{id}`, and `list_1`/`list_2` from the assessment.
  Retain legacy routes and input names with identical cache identity.
- Preserve string content, whitespace, case, duplicates, and ordering in input identity.
- Reject unequal lengths and non-string items without coercing them silently.
- Reject NUL and lone surrogate code points before database access in API and CLI input;
  preserve other Unicode scalar values without normalization.
- Accept two empty lists and produce an empty output unless clarification specifies otherwise.
- Provide `cache-cli` with `-r`, `-i`, `-j`, and `-o` plus their long options.
  Reserve the conflicting short option -h for help; use --host for the server address.
  Keep `cache-service` as a compatibility command.
- Require exactly one input source: inline JSON or file input, with stdin represented by a dash.
- Require a positive repeat count. Each iteration creates or reuses a payload and reads its output.
- Default output to stdout and send diagnostics to stderr. Use JSON Lines for stdout and files:
  one compact object containing `id` and `output`, followed by a newline, per successful repeat.
  Escape embedded newlines through JSON encoding. Emit each record after creation and read
  succeed, including when an ID is reused. On failure, stop with a nonzero exit status and no
  result record for the failed iteration; retain earlier complete records.
- The [payload API contract](api-contract.md) freezes schemas, HTTP statuses, configurable input limits and overall deadlines. Routes, runtime deadlines, and coordination capacity are implemented; [verification](verification.md#guarantee-evidence) maps their guarantees to evidence.

## Additional reliability goals

Concurrent successful requests should reuse work for the same missing string, including when different payloads overlap. Define the supported process model and prove coordination within it. Database uniqueness alone does not prove minimized transformer calls.

Transformation failures must not be cached as successful results. Reads must never expose an incomplete generated payload. Specify whether successful individual transformations survive failure of the larger request.

## Delivery requirements

Submit a public GitHub or GitLab repository with a neutral name and meaningful, unsquashed development history. Provide an English video walkthrough of at most 15 minutes with screen sharing and camera on. Trace a request through the code and database, then cover CLI and tests. Report actual hours spent. The public repository must contain maintainable technical documentation; personal preparation stays outside it.
