# Implementation and submission backlog

This backlog tracks the assessment from requirements through submission. It is the authoritative work status; the implementation plan describes sequencing, architecture explains decisions, and verification describes test scenarios. Written code is not complete until its acceptance evidence passes.

## Status and update rules

- **Done**: acceptance evidence has been checked and recorded.
- **Written**: artifacts exist, but required runtime evidence is pending.
- **Ready**: work can start with the current assumptions.
- **Waiting**: clarification or a predecessor is pending.
- **Blocked**: an external restriction prevents the next check or action.

For each implementation change, update the affected item, add code or test links and the commit, and record executed verification. Keep failed checks visible until resolved. A commit alone does not prove acceptance. Any changed requirement must update its mapped items and tests. Use the current provisional interpretations until the task author replies; confirmation is not required to make independent progress.

## Requirement coverage

| ID | Assessment requirement | Work items |
| --- | --- | --- |
| R01 | FastAPI creation and read endpoints | B04, B07, B08 |
| R02 | Two equal-length string lists, transformation and interleaving | B04, B06, B07 |
| R03 | Persistent transformer caching and minimized calls | B09, B10, B11, B13, B14 |
| R04 | Reuse generated payload identifiers | B05, B07, B12, B14 |
| R05 | SQLite or PostgreSQL with SQLAlchemy or SQLModel | B02, B03, B07, B09 |
| R06 | Docker deployment | B02, B03, B18 |
| R07 | CLI parsing and validation with Pydantic Settings | B15, B16, B17 |
| R08 | CLI host, repeat, file or stdin, inline JSON, file or stdout, help | B01, B15, B16, B17 |
| R09 | Unit and integration tests | B03, B06, B08, B13, B14, B17, B18, B20 |
| R10 | Communicate ambiguities, explain shortcuts, maintain clear code | B01, B19, B20 |
| R11 | Small meaningful Git commits, neutral public repository, preserved history | B21, B24 |
| R12 | English video up to 15 minutes, camera and screen, code trace, CLI and tests | B22, B24 |
| R13 | Reply with repository and video links and actual hours | B23, B24 |

## Work items

Dependencies identify the required predecessor, rather than requiring every earlier numbered item to finish first.

| ID | Work and acceptance evidence | Status | Dependencies | Current artifacts or evidence |
| --- | --- | --- | --- | --- |
| B01 | Record author answers about input/output identity, filesystem storage, uppercase; resolve CLI flag conflict and output format | Waiting | Author response for confirmation only | [Requirements](requirements.md); provisional choices recorded; CLI output format pending |
| B02 | Application lifecycle, PostgreSQL configuration, migration and Compose; inspect setup artifacts | Written | None | [Application](../src/cache_service/main.py), [migration](../migrations/versions/0001_initial.py), [Compose](../compose.yaml); commit `6a492e7` |
| B03 | Install dependencies, generate lockfile, run lint and foundation tests, apply clean migration, check both health endpoints and image startup | Blocked | B02; execution/network access | Syntax and Compose config passed; runtime checks blocked; see verification record below |
| B04 | Freeze POST and GET response schemas, strict input validation, empty behavior, configurable limits and request deadlines | Ready | Provisional B01 choices | POST identifier field and status, malformed ID behavior, bounds and deadlines still to specify |
| B05 | Define canonical encoding, version and digest identities; verify list boundaries, order, whitespace and collision handling | Ready | B04 | Design in [architecture](architecture.md); implementation pending |
| B06 | Replaceable uppercase transformer and alternating composition; meaningful isolated tests | Ready | B04 | Sample output and empty input policy in requirements |
| B07 | Create and read complete payloads; generated UUID plus unique input digest; duplicate creation returns stored ID | Waiting | B03–B06 | Initial schema written; request flow pending |
| B08 | API tests for sample output, invalid types/lengths, empty input, unknown ID, retry and identity policy | Waiting | B07 | [Verification scenarios](verification.md) |
| B09 | Batch cache reads and request deduplication; persist successful results with versioned keys and authoritative readback | Waiting | B03, B05, B06 | Implementation pending |
| B10 | One advisory lock at a time, recheck after acquire, same connection for writes; no transaction over external call | Waiting | B09 | Coordination design recorded; implementation pending |
| B11 | Bounded admission and waits, cancellation-safe cleanup, invalidate uncertain ownership; map operational failures to documented HTTP responses | Waiting | B10, B04 | Numeric budgets and cleanup code pending |
| B12 | Preserve successful transformations on later failure; publish complete payload atomically; verify safe retries | Waiting | B07, B09–B11 | Policy recorded; implementation pending |
| B13 | Real PostgreSQL tests for timeout, cancellation, saturation, lock loss, collisions, version changes and no open transaction during transform | Waiting | B11, B12 | Controlled synchronization and exact assertions pending |
| B14 | Multi-process identical and overlapping requests; call counts per distinct string, consistent IDs and restart reuse | Waiting | B12 | Test instrumentation pending; single-process evidence insufficient |
| B15 | Pydantic Settings CLI parsing; host, repeat and mutually exclusive input source validation; resolve help alias | Waiting | B01 output policy; B04 | Parsing implementation pending |
| B16 | CLI create/read loop, file/stdin/JSON input, file/stdout output, stderr diagnostics and nonzero failure exit | Waiting | B07, B15 | Implementation pending |
| B17 | CLI parsing and I/O tests plus a real-service integration scenario | Waiting | B16 | Tests pending |
| B18 | Clean Docker build and migration/start smoke test; storage reuse after restart; document supported worker/connection budget | Waiting | B03, B12, B17 | Compose exists; runtime deployment evidence pending |
| B19 | Complete public setup, usage, configuration, architecture and limitations; reconcile every guarantee with tests | Waiting | B14, B17, B18 | Public docs exist; final usage and evidence pending |
| B20 | Final code review and requirement audit; full required suite passes; remove unnecessary complexity and inspect repository contents | Waiting | B13, B14, B17–B19 | Final review pending |
| B21 | Preserve real incremental commits; verify neutral repository name and public artifacts contain no personal preparation or secrets | Ready | Ongoing; final audit B20 | Four commits recorded below; private preparation is outside repository |
| B22 | Prepare and record English walkthrough with camera and screen, code trace, CLI and tests; verify duration at most 15 minutes | Waiting | B20 | Personal rehearsal remains in sibling private workspace; candidate records video |
| B23 | Track actual time from available records; candidate reconciles previous work; report honest total without estimating missing history as fact | Ready | Ongoing | No authoritative total yet; candidate confirmation required |
| B24 | Create/publish neutral public repository and video, verify both links, draft reply with actual hours, submit when explicitly authorized | Waiting | B20–B23 | No public repository, video or submission yet |

## Current verification record

| Check | Result | Consequence |
| --- | --- | --- |
| Python compile check on source, migration and tests | Passed | Syntax checked only |
| `docker compose config --quiet` | Passed | Compose configuration valid; image and service not run |
| Make help and command dry runs | Passed | Shortcut expansion checked |
| Integration shortcut without database URL | Expected rejection | Prevents silently skipping the database check |
| Dependency installation | Blocked by DNS/network access | Dependencies and lockfile unavailable |
| Docker daemon access | Permission denied | Build and startup unverified |
| Local PostgreSQL startup | Sandbox denied listening socket | Migration and database integration unverified |

Record successful runtime commands, environment and outcomes here when access is available. Do not replace blocked results with success based on artifact inspection.

## Development evidence

| Commit | Actual change |
| --- | --- |
| `2a3ce1d` | Requirements, architecture options and implementation plan |
| `4028011` | PostgreSQL coordination and failure handling contracts |
| `6a492e7` | Application foundation, migration, Compose and foundation tests |
| `b76b0cc` | Make shortcuts and documentation |

## Next work and completion gate

Resolve B03 runtime verification first. B04–B06 can be refined independently while access is blocked. Then implement the payload flow and proceed through cache coordination, CLI and deployment evidence.

Submission is ready only when mandatory behavior, documented reliability guarantees, reproducible setup, and final checks pass; repository history is retained; private material is excluded; video meets the brief; and actual hours are reconciled. B24 remains separate from implementation completion because publishing and sending are delivery actions.
