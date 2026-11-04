# Next implementation tasks for Kiro

> **Update 2026-11-05:** the statements below that no new Kiro calls are authorized are superseded.
> The user authorized real Kiro work for Kiroween. Briefs: docs/kiro-briefs/. Runner:
> scripts/kiro_session.py. Credits are requested; no new session has run yet.


These are Codex-authored planning tasks. The M2 engine specification, initial implementation and
60 tests were authored by one actual Kiro session; Codex reviewed/corrected the result and added
22 tests. Final checks pass. See kiro-evidence.md and ENGINE_REVIEW.md.

Conserve limited credits: no new Kiro model session without an explicit user request. Reuse the
existing engine specs/code. Codex has now integrated persisted sessions/events, optimistic concurrency, replay verification,
checkpoint forks, comparison, reports and Simulation Room without more Kiro calls. The latest local completion also includes review/proposals, library discovery, custom scenarios,
version history, Replay Lab, PDF text import, action-step editing, onboarding and portable reports.
See PRODUCT_COMPLETION.md and VALIDATION.md. No new Kiro calls are needed or authorized.
Deployment/publication is deferred by the user. Optional AI features remain excluded by the active
no-LLM dependency rule; P2 collaboration/integrations are not required for this MVP.

The numbered roadmap below is historical planning, not outstanding implementation or permission
to launch Kiro. The engine, persistence, replay/forks, reviews, reports and UI are implemented; use
existing artifacts for any future review. Preserve genuine authorship in kiro-evidence.md.

1. In a real Kiro session, review PRD and architecture; create requirements/design/tasks for
   simulation-engine, source-studio and replay-lab under .kiro/specs. Record actual contributions.
2. Formalize engine contract: typed facts, missing/wrong-type fact behavior, declarative AND,
   safe operators, bounded traversal/cycles, inject timing, seed/version semantics, and canonical
   logical event hashing. Separate timestamps/UUIDs from reproducible logical history.
3. Implement decision evaluation: exactly one/zero/multiple matches, uncovered/overlap review
   stops, deviations, and clear distinction between approved policy and modeled assumptions.
   The weather capacity guard is not established by its citation; review it explicitly.
4. Add Scenario, SimulationSession, append-only SessionEvent and RuleProposal migrations.
   Define atomic expected-revision checks and duplicate/conflicting decision responses.
5. Implement event history and deterministic replay. Pin immutable playbook/scenario/seed;
   persist ordered events and validate state hashes. Same inputs must reproduce logical outcomes.
6. Implement checkpoint forks and branch isolation. Reject invalid checkpoints; preserve the
   parent. Property-test generated small graphs, reference integrity, replay and fork behavior.
7. Implement source review and approval/revisions. Approve only after explicit human review;
   cite real segments, retain draft/uncited proposals, create new immutable approved versions.
8. Implement actual-event reports and comparison. Include decisions, evidence, deviations,
   gaps, overlaps, assumptions and proposals, version IDs, JSON download and print view.
9. Build Simulation Room and Replay Lab against real endpoints. Run both fixtures through the
   same engine. Add full E2E tests, keyboard checks, concurrency and authority tests.
10. Harden public deployment: write/body limits, rate limiting, anonymous isolation/retention,
    CORS/config, reverse proxy/static hosting, persistent backup/recovery. Verify fresh install.
11. Record truthful Kiro-authored changes, discovered bugs, tests and hooks in docs/kiro-evidence.md.
    Do not retroactively label Codex artifacts as Kiro output. Host and verify judge walkthrough.
