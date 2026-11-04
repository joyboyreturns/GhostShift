# Kiro handoff status — November 3, 2026

Codex-authored status record; see docs/kiro-evidence.md for the actual contribution record.

- M0/M1: verified foundation; the original baseline had 18 backend, 3 unit frontend and 4 browser tests.
- Kiro CLI 2.37.1: installed and authenticated by the user.
- One real engine implementation session ran: `8b21a265-5723-4164-92b7-d17d990e23bc`.
- Kiro authored engine requirements/design/tasks, core implementation and 60 tests, then hit service
  throttling. Codex reviewed the partial output, made local corrections and added 22 regression tests.
- After M2, checks passed: 100 backend, 3 frontend unit and 4 browser tests; lint, type checks and build.
- No further Kiro model calls were made after the user's credit-conservation request. Do not launch
  another session without an explicit request. Actual credit usage is not measured.
- Next: persisted simulation sessions/events and optimistic concurrency, then replay/branch/report/UI.

The tested foundation snapshot is tree `730661adf433f8d452765d949937b58c6afc303d`, anchored by
`refs/ghostshift/baselines/m0-m1`. The pre-Kiro handoff is anchored by
`refs/ghostshift/baselines/m2-handoff`. These are Git tree snapshots, **not commits**. No Git author
identity was invented and nothing was published. Transcript and launcher metadata are in .kiro/evidence/.

The integrated engine snapshot is anchored by `refs/ghostshift/baselines/m2-engine-core`.

## Current integration status

Milestone 3 was implemented locally by Codex with no further Kiro calls. Persisted session/event
history, atomic choice revisions, replay verification, checkpoint forks, comparisons, reports and
Simulation Room are working. Existing
Kiro contribution attribution is unchanged; see docs/PERSISTED_REHEARSALS.md.

M3 checks passed: 114 backend, 4 frontend unit and 8 browser tests, plus lint, type checks and build.
The integrated M3 snapshot is anchored by `refs/ghostshift/baselines/m3-persisted-rehearsals`.

## Status after M4–M6 and the visual overhaul

Codex implemented M4 (policy review, immutable revisions, proposals), M5 (public-demo isolation and
limits) and M6 (library, custom scenarios, version history, PDF provenance, Replay Lab and portable
reports) locally, with no further Kiro calls. See POLICY_REVIEW.md, PUBLIC_DEMO.md and
PRODUCT_COMPLETION.md. A presentation-only visual overhaul followed (DESIGN.md).
The Kiro contribution record is unchanged: there is still exactly one Kiro session. No new Kiro
work is planned unless the user explicitly requests it. Remaining work is deployment and
submission only (see submission-checklist.md).

## Update 2026-11-05

The user authorized further real Kiro work for Kiroween (credits requested, not yet received). Session
briefs are in docs/kiro-briefs/ and are run with scripts/kiro_session.py. Until a session runs, the Kiro
contribution record is unchanged: exactly one session. The statements above that no Kiro work is planned
are superseded.
