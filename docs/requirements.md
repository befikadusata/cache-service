# Requirements and acceptance criteria

The service must satisfy the supplied Python caching assessment. Required behavior is separated from provisional interpretations and additional reliability goals so that implementation choices remain reviewable.

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

## Pending clarification

| Question | Provisional interpretation | Affected decisions |
| --- | --- | --- |
| Is payload reuse based on identical input or identical generated output? | Identical ordered input lists | Identity key and reuse tests |
| Does payload files require actual files on disk? | Store generated payloads in the database | Storage model and deployment |
| Is uppercase the intended transformer? | Deterministic uppercase conversion following the sample | Transformer implementation and expected output |

These interpretations are not confirmed requirements. Record the task author's response here and revise affected decisions before implementation relies on different behavior.

## Proposed input and CLI policy

- Preserve string content, whitespace, case, duplicates, and ordering in input identity.
- Reject unequal lengths and non-string items without coercing them silently.
- Accept two empty lists and produce an empty output unless clarification specifies otherwise.
- Reserve the conflicting short option -h for help; use --host for the server address.
- Require exactly one input source: inline JSON or file input, with stdin represented by a dash.
- Require a positive repeat count. Each iteration creates or reuses a payload and reads its output.
- Default output to stdout and send diagnostics to stderr. Decide the repeated-output format before CLI implementation.
- Select and document numeric input limits, deadlines, and pool capacity during the foundation stage; they are not specified in the brief. The timeout and failure policy is defined in the architecture document.

## Additional reliability goals

Concurrent successful requests should reuse work for the same missing string, including when different payloads overlap. Define the supported process model and prove coordination within it. Database uniqueness alone does not prove minimized transformer calls.

Transformation failures must not be cached as successful results. Reads must never expose an incomplete generated payload. Specify whether successful individual transformations survive failure of the larger request.

## Delivery requirements

Submit a public GitHub or GitLab repository with a neutral name and meaningful, unsquashed development history. Provide an English video walkthrough of at most 15 minutes with screen sharing and camera on. Trace a request through the code and database, then cover CLI and tests. Report actual hours spent. The public repository must contain maintainable technical documentation; personal preparation stays outside it.
