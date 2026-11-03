# Kiro development evidence — November 3, 2026

This factual record was prepared by Codex from the actual Kiro CLI transcript and independent
local verification. It does not relabel Codex work as Kiro work.

## Actual session

- Tool: Kiro CLI 2.37.1, authenticated by the user.
- Session ID: `8b21a265-5723-4164-92b7-d17d990e23bc` (V2 local session).
- Prompt: docs/KIRO_MILESTONE_2_PROMPT.md, prepared by Codex.
- Actual transcript: .kiro/evidence/2026-11-03-engine-session.log.
- Launcher timestamps/exit status: .kiro/evidence/2026-11-03-engine-session.json.
- Started November 2 at 20:41 UTC, which is November 3 in the user's India timezone.
- The provider throttled the session at 20:47 UTC. The process exited with code 1. Its work was
  retained and reviewed; no successful completion of that Kiro process is claimed.

## Work actually authored by Kiro

1. Reviewed the supplied PRD, architecture, graph schemas, source fixtures, and initial engine
   Protocol. Produced requirements.md, design.md and tasks.md under .kiro/specs/simulation-engine/.
2. Expanded the placeholder Protocol into typed run/scenario/inject/decision/evaluation/event
   contracts, and implemented declarative predicate evaluation and deterministic graph traversal.
3. Implemented missing-fact/type mismatch handling, AND conditions, exact/uncovered/overlap
   classification, inject application, bounded traversal, deviation recording and event hashing.
4. Wrote the initial 60 engine tests, including both domain fixtures and initial Hypothesis tests.
5. Its tests caught a genuine bug: reaching an end node overwrote deviation status with completed.
   The transcript records Kiro finding and fixing this. Kiro also corrected cyclic test graphs and
   fixture paths after running tests.

Codex independently verified that the initial output passed 78 backend tests (18 foundation +
60 Kiro tests). Formatting and strict typing were still failing when Kiro stopped. The initial
prospective verification checklist was corrected; no unexecuted Kiro e2e/build pass is claimed.

## Separately authored by Codex

- All M0/M1 foundation code, UI, fixtures, source segmentation, persistence, and initial tests.
- Initial steering notes, spec/hook placeholders, launch prompt, snapshots and session launcher.
- Independent engine review and local corrections described in docs/ENGINE_REVIEW.md: explicit
  checkpoints/mode, replayable choice streams, full input snapshots, event authority/diagnostics,
  strict finite inputs, stronger hash context, and accessible budget-exhaustion history.
- The 22 new regression/property tests in tests/test_engine_review.py, including generated valid
  branch graphs and independent choice/outcome/evidence/isolation assertions.
- Integration demo harness, documentation updates, and final independent verification.

The initial Kiro test file was adjusted locally to explicitly opt batch traversal into
`auto_rehearsal` and to check expanded hash context. Those adjustments are Codex corrections.
The current interpreter has both authorship stages; its header identifies them explicitly.

## Credit conservation

Exactly one Kiro implementation session was launched. A session can contain multiple model
requests; actual credit consumption was not measured and is not estimated here. After the user
requested conservation of limited credits, no further Kiro model calls were made. Codex completed
review corrections and verification locally. Future Kiro model sessions require an explicit user
request; existing specs and code should be reused rather than regenerated.

## Verification of the M2 integrated state

- `make lint`: passed.
- `make typecheck`: passed, strict mypy on 20 application files plus TypeScript.
- `make test`: 100 backend tests and 3 frontend unit tests passed.
- `make e2e`: all 4 real browser tests passed.
- `cd apps/web && npm run build`: passed.
- `make engine-demo`: actual draft fixtures return uncovered/weather and overlap/refund.

No Kiro-authored hooks, persisted replay/fork APIs, approval workflow, report API, simulation UI,
source-studio spec, or replay-lab spec is claimed. Those remain later work. The root .kiro directory
contains genuine engine specs plus clearly labeled Codex material; placeholder files are not usage.

## Subsequent Codex integration — Milestone 3

After the engine milestone, Codex added persisted session/event models, migration 0002, atomic
choice revisions, replay/fork/comparison/report services and APIs, plus Simulation Room/report UI
and corresponding tests. The existing engine was reused unchanged. This work is Codex-authored,
not additional Kiro work, and no new Kiro model calls were made. Earlier statements about unbuilt
persistence/UI describe the boundary at the original Kiro session, not the current integrated app.
See PERSISTED_REHEARSALS.md for the implementation and VALIDATION.md for current check results.


## Subsequent Codex integration — Milestone 4

Codex added migration 0003, immutable proposal/review records, hash-bound human approval, source
revisions and version ancestry, manual choice/condition/evidence authoring, saved proposals,
unapproved proposed-policy rehearse/compare, report proposal sections, and browser/integration
tests. Codex also fixed write contention discovered in concurrent browser testing with bounded
pre-commit SQLite retries and protection against retrying a committed write. No engine files were
changed, and no Kiro model calls were made. See POLICY_REVIEW.md and VALIDATION.md.


## Subsequent Codex integration — Milestone 5

Codex implemented public-mode limits and anonymous database isolation, signed expiry cookies,
retention and capacity/page quotas, clean-template preparation, maintenance/error behavior, snapshot
backups and restore checks, Caddy/Compose deployment configuration, production-path browser tests
and CI configuration. The engine and original Kiro artifacts were reused unchanged; no Kiro model
session was launched. This work is not Kiro usage evidence. Hosting and remote CI are not claimed.


## Subsequent Codex integration — Milestone 6

Codex added workspace discovery/search, custom fictional scenario authoring, source/version history,
Replay Lab and comparison print/export, action-step editing/removal, PDF text extraction and page/file
provenance (migration 0004), explicit UTC transport metadata, onboarding and regression tests.
Portable reports include actual cited text, pinned replay inputs, durable events and captured review
provenance. Existing engine code and original Kiro artifacts are unchanged. No further Kiro model
sessions were launched. Deployment was explicitly excluded. See PRODUCT_COMPLETION.md and VALIDATION.md.
