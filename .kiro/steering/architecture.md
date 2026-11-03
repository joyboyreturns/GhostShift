# Architecture steering

Codex-authored initial handoff. Kiro must review this in a real session.
React/TypeScript/Vite → typed /api FastAPI → service layer → SQLAlchemy/Alembic/SQLite.
See docs/architecture.md. Validate graph topology and document-scoped source evidence.
Approved versions and original source records remain immutable. Never evaluate executable
conditions. Implement deterministic simulation behind app/engine/interfaces.py; review the
contract before expanding it. Do not add LLM dependence for core functionality.

## Codex status update after engine review — November 3, 2026

The M2 engine core is implemented and verified. One real Kiro session authored the initial engine
spec/code and 60 tests; Codex review corrections and 22 regressions are separately attributed.
Current tests: 100 backend, 3 frontend unit, 4 browser. See docs/ENGINE_REVIEW.md and docs/kiro-evidence.md.
Persisted simulation/session/replay/fork/report APIs and UI remain future. Conserve the user's Kiro
credits: reuse existing artifacts and do not start another Kiro model session without an explicit request.

## Codex integration update after M3 — November 3, 2026

Codex integrated persisted scenarios/sessions/events, optimistic choice revisions, verified replay,
checkpoint forks, comparisons/reports, and Simulation Room around the unchanged engine. Current
checks pass: 114 backend, 4 frontend unit and 8 browser tests. See docs/PERSISTED_REHEARSALS.md.
No additional Kiro model calls were made. That was the M3 boundary; see the subsequent M4 update below.


Codex integration update: M4 policy/revision/proposal workflows and manual source modeling reuse
the engine unchanged. SQLite writes retry only before commit; version/source evidence and explicit
human authority remain separate. See docs/POLICY_REVIEW.md. This note is not Kiro usage evidence.


Codex M4 update: manual source modeling, evidence review, source/playbook revisions and saved
proposed-policy rehearsal/comparison are implemented. Verified: 126 backend, 4 frontend unit and
11 browser tests, lint, type checks and build. No new Kiro calls. Public deployment controls remain
next; see docs/POLICY_REVIEW.md and docs/VALIDATION.md. This is Codex-authored status, not Kiro evidence.


Codex M5 status: public-mode isolation, limits, signed temporary cookies, retention, quota handling,
backup replay, Caddy production-path verification and deployment/CI configuration are implemented.
See docs/PUBLIC_DEMO.md. One API instance is required; public scopes never copy private development
data. Real server/Docker/TLS checks remain. No additional Kiro calls or engine changes were made.


Codex M6 status: library/search, custom scenarios, version history, Replay Lab, action-step editing,
PDF text/page provenance, linked onboarding and portable session/comparison exports are implemented.
See docs/PRODUCT_COMPLETION.md and docs/VALIDATION.md. Engine/Kiro evidence is unchanged; no additional
Kiro model calls were used. Deployment is excluded by the user. This note is Codex-authored.
