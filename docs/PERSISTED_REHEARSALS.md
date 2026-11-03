# Persisted rehearsals — Milestone 3

Codex-authored integration of the existing Kiro/Codex engine. No additional Kiro model calls were
made for this milestone. The engine modules and their existing tests remain unchanged.

## Working journey

Source Studio → Rehearse scenario → explicitly acknowledge the fictional draft model → start →
choose escalation → reach the weather/capacity gap → reload the same URL → verify replay → fork
before the delivery decision → choose routine intake as a deviation → compare with the unchanged
parent → open the actual-event report → download JSON or print.

The refund fixture uses the same engine and persistence service. It immediately stops when both
refund rules match, exposes both original sections, and refuses to invent precedence.

## Persistence and transaction design

Alembic 0002 adds Scenario, SimulationSession and SessionEvent. Scenario rows and event rows are
immutable through ORM guards and SQLite triggers. A trigger also pins each session's identity,
scenario/playbook/document references, lineage, engine version and creation time. Only the current
state, status, node and revision advance. Event rows have a unique (session_id, sequence_number).

Each session owns a full validated RunInput snapshot: original graph, scenario facts/injects/seed,
authority, mode, budget and decisions. Draft edits after a session begins cannot rewrite it.
Scenario and authority are obtained from stored records. A browser cannot submit a graph, facts,
seed, approval status or forged engine history through the session endpoints. Draft execution is
explicitly acknowledged at creation and remains an unapproved model rehearsal throughout forks.

Every read verifies the stored snapshot by executing the existing engine and comparing its full
result and durable ledger. A future engine change must bump the supported engine version or retain
an implementation for old sessions; unsupported versions fail closed with their data preserved.

The library's awaiting_decision run_terminated event is an ephemeral response pause marker. It is
not persisted as a terminal ledger event. All preceding events are persisted, and the next choice
must reproduce exactly that prefix before any new event may be appended. Real terminal markers
(uncovered, overlap, end, budget) remain durable. This avoids rewriting history when an interactive
pause is resumed. Both the full response result and the durable event ledger are exposed explicitly.

Choice submissions require an integer expected_revision. A conditional SQL UPDATE claims exactly
that revision, followed by event inserts in the **same transaction**. Stale/racing requests receive
409; invalid choices receive 422; terminal runs cannot be advanced. New forks start at revision 0,
which counts branch-local successful writes, even when they inherit earlier logical decisions.

Python 3.12 SQLite autocommit=False makes read queries participate in the transaction, so stored
state and ledger queries see one snapshot while another request writes. Connection PRAGMAs are
set temporarily outside the transaction; FK enforcement and WAL remain enabled. See the official
[SQLAlchemy SQLite transaction documentation](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html#enabling-non-legacy-sqlite-transactional-modes-with-the-sqlite3-or-aiosqlite-driver).

## Replay, forks and reports

- Replay re-executes pinned inputs and compares state, ordered logical events, payloads and hashes.
  A success response is emitted only after the checks pass; corrupted state is not repaired silently.
- Forks accept an existing decision_evaluated event index. The service reconstructs only the choices
  before that checkpoint and verifies the prefix, then creates a separate session and separate event
  rows. Parent rows/events are untouched. Forking at an unresolved gap remains unresolved.
- Comparison requires the same scenario, pinned graph/version and authority context. It reports real
  outcomes, deviation/finding counts, and the length of the matching logical-event prefix. Cross-policy
  variant comparison is future work and is not smuggled into this endpoint.
- Reports derive choices, deviations, missing paths, overlaps and citations from verified events.
  A cited draft choice is never labeled reviewed support. In-progress reports are labeled explicitly.
  JSON downloads are actual API responses; print uses the report page and original source text.

## API

- GET /api/scenarios/{id}
- POST /api/sessions — {scenario_id, allow_draft_rehearsal}
- GET /api/sessions/{id}
- POST /api/sessions/{id}/choose — {choice_id, expected_revision}
- POST /api/sessions/{id}/fork — {event_index}
- GET /api/sessions/{id}/replay
- GET /api/sessions/{id}/report
- GET /api/sessions/compare?left_id=...&right_id=...

## Tested boundaries

Migrated file-backed SQLite API tests cover explicit draft consent, event-prefix preservation,
stale/duplicate/invalid/terminal submissions, two concurrent writers with only one successful commit,
consistent reader snapshots, rollback between revision claim and event append, forks and unchanged
parents, unresolved-gap forks, real report data, incompatible comparisons, immutable records, draft
snapshot pinning, and corrupt-state replay detection. Browser tests cover persistence after reload,
actual source evidence, replay, alternate choices/comparison, JSON downloads, both fixtures and mobile.

## Remaining work at the M3 boundary

Policy review/approval/revisions, proposed rules and replay under an explicitly labeled proposed
policy remain next. A fork changes decisions, not policy. No proposal is silently approved. Public
write limits, anonymous isolation/retention, hosting and deployment verification are still required
before public release. No authentication or paid AI service was added to this local milestone.


M4 follow-up: human review, revisions and proposed-policy rehearsals/comparison are now implemented
by Codex; see POLICY_REVIEW.md. Same-policy M3 fork invariants remain unchanged. HTTP POST writes
now use bounded SQLite contention retries before commit; successful writes are never retried after
commit. The original engine code is unchanged. Public hardening/hosting remain outstanding.
