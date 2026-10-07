# Repository and history audit

B21 audit on 2026-10-07, at local revision `862a2fd`. Repository name, incremental history,
current tracked content and reachable historical objects were reviewed. The audit passes with
the already documented retired development credential retained in history; it does not claim
that the history has never contained a password.

## Name, history and publication

- GitHub reports [befikadusata/cache-service](https://github.com/befikadusata/cache-service)
  as public, with neutral repository name `cache-service` and default branch `main`.
- The audited history contains 47 commits: 33 non-merge development commits and 14 merges.
  Commits trace foundation, identity, API, caching, coordination, CLI and verification work.
  All locally reachable commits are ancestors of current `main`; no history was rewritten.
- Published `main` is `425e0b3`, the B17 merge. Local B18, B19 and B20 commits
  (`0974821`, `68a6a42`, `862a2fd`) are not yet published. This audit changes no remote state.
  B24 must publish and verify the final revision and video before submission.
- All 14 GitHub branch heads are present in the audited local history. GitHub reports no
  tags, releases or release attachments requiring separate inspection.

## Content and credential checks

Inspected 47 current tracked files and all locally reachable objects: 47 commits,
122 trees and 174 distinct file blobs. Checks searched filenames for local configuration,
private preparation, keys, database files and generated artifacts; scanned blob and commit
content for current local database credentials and common private-key/token patterns; and
reviewed historical database URL/password assignments with values redacted from output.

| Check | Finding |
| --- | --- |
| Current local database password or complete URL in reachable content | No matches |
| Private-key headers, GitHub token, AWS access-key and OpenAI key patterns | No matches |
| Historical private/local file paths | No populated `.env`, private preparation, virtual environment, database or key files found |
| Private workspace copies | 174 historical blobs compared with 15 private files; no exact file copies |
| Current public documentation | Technical requirements, architecture, usage, checks and delivery status; personal preparation content remains outside Git |
| Ignore rules | `.env`, `.venv` and an in-repository private-preparation path are ignored; `.env.example` remains tracked intentionally |
| `git archive HEAD` contents | 47 files; no local/private artifacts |
| Database URL literals | 19 historical blobs reviewed: development examples, dummy test values, generated-value templates and disposable CI configuration |
| Password assignment candidates | Nine historical blobs reviewed: retired development default, empty examples, environment substitutions and generated-value code |

The initial foundation committed a fixed development database password in Compose and examples.
The [configuration follow-up](backlog.md#secrets-and-configuration-follow-up), introduced in
`1499afd`, removed fixed runtime credentials, required generated local secrets, masked settings
and recorded rotation of the existing database role without deleting storage.

This audit independently verifies that the current configured credential authenticates and the
historical exposed development password is rejected by PostgreSQL for the same local role.
Neither credential was printed. The old value must remain treated as public and unusable for
any future environment. Historical test fixtures and disposable CI passwords are examples,
not current persistent credentials. History is retained to satisfy the incremental-history
requirement; the retired value is not described as an active secret or a clean-history result.

## Scope and remaining delivery work

These checks combine literal matching, selected secret patterns, filename inspection,
exact private-file comparison and manual review. They cannot prove absence of every possible
secret or copied fragment. Dedicated secret scanners were unavailable locally; no scanner
installation or external upload of repository content was performed.

Final documentation validation checked 109 local Markdown links and heading anchors;
`git diff --check` passed, and private audit notes were verified against the prepared copy.

Runtime code and configuration were unchanged. B20's 202 passing tests and Docker build
remain the implementation evidence; no new suite or hosted CI run is claimed for this audit.
No commits were squashed, no repository visibility changed, no push occurred and no database
volume was removed. B22 video, B23 authoritative actual hours and B24 final publication and
submission remain open. Personal audit notes were updated outside Git.
