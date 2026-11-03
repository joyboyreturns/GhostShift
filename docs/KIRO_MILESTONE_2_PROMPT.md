# Kiro Milestone 2 — deterministic engine

This launch prompt is authored by Codex. It is not Kiro implementation or usage evidence.
The user authorized continuing the project plan after the verified M0/M1 foundation.

You are Kiro, implementing the next GhostShift milestone. Read AGENTS.md, docs/PRD.md,
docs/architecture.md, docs/NEXT_KIRO_TASKS.md, .kiro/steering/, fixtures/, and the existing backend
schemas, services, tests, and app/engine/interfaces.py before making changes.

## First: review and specify

Review the current architecture and source/graph authority boundary. Create genuine Kiro-authored
requirements.md, design.md, and tasks.md under .kiro/specs/simulation-engine/. Explain any changes
needed to the initial Protocol. Keep the Codex origin of existing steering notes explicit; append
your review rather than claiming authorship of those original notes.

Define concrete acceptance criteria for safe predicates and AND composition, typed and missing
facts, zero/one/multiple matching choices, explicit deviations, inject ordering, deterministic
logical events and hashes, traversal budgets, draft authority, and future replay/branch isolation.
Then implement the engine milestone and its tests in this same real Kiro session.

## Implement now

- A domain-independent deterministic interpreter in services/api/app/engine/, with typed input
  and output contracts. Never use eval or execute user-supplied expressions.
- Explicit operator semantics: eq/neq/gt/gte/lt/lte/in. Do not conflate booleans with numbers;
  missing or incompatible facts must have documented, tested behavior.
- Safe traversal through start/action nodes, bounded cycle handling, immutable input graph/facts,
  and explicit decision checkpoints. Exactly one match is supported by the modeled rules;
  zero is uncovered; multiple is potential overlap. Do not invent a correct policy response.
- Record a nonmatching selected action as a deviation, retaining evidence and authority metadata.
- Deterministic scenario injects applied at documented checkpoints, once each, without ambient
  time/randomness. Use scenario seed only through explicit reproducible semantics.
- Canonical logical event/state hashing that excludes generated UUIDs and wall-clock timestamps.
  Replaying identical inputs and decisions must produce identical logical history. Full persisted
  replay and forks belong to the following milestone; prepare clean contracts, not fake endpoints.
- Load both existing scenario JSON fixtures through the same engine in tests. The night-market
  run must reach a real uncovered weather/capacity condition; the refund fixture must detect both
  matching refund rules. Any draft rehearsal must be explicit and labeled unapproved/model-only.
- Preserve all existing approved-version/source immutability and source-reference validation.
  Weather's capacity guard is a modeled assumption, not supported authority just because its
  choice cites the weather paragraph. Do not silently promote seeded drafts to approved policy.
- Meaningful pytest cases and Hypothesis-generated small graphs/decision sequences testing
  determinism, reference integrity, type/missing-fact behavior, input/branch isolation, and bounds.

## Boundaries

Do not implement the whole remaining product. Keep this session focused on the engine and its
real specification/tests. Persistent sessions/events, optimistic concurrency endpoints, approval
and revisions, replay/fork APIs, comparison/reports, and Simulation Room/Replay Lab UI follow later.
Do not add placeholder successful simulation endpoints, AI dependencies, authentication, paid
services, or microservices. Existing Source Studio must keep working.

Work only in this repository; do not read credentials or personal documents, alter global machine
configuration, install software, publish/deploy, send messages, or change Git identity. Do not commit
or push. Use installed Python 3.12/uv dependencies and existing locks. Do not claim a test passed
unless you ran it. No contribution evidence may claim work that you did not actually perform.

## Verify and hand back

Run make lint, make typecheck, make test, make e2e, and the frontend production build where needed.
Fix regressions you reproduce. Mark spec tasks accurately. Return the changed files, key semantic
decisions, exact checks/results, limitations, and next milestone boundary. Record a factual Kiro
session summary in docs/kiro-evidence.md, with the session ID if available and concrete examples of
your authored changes/bugs caught. Never relabel the Codex foundation as Kiro output.

The launching Codex session will independently review your diff and rerun relevant checks.
