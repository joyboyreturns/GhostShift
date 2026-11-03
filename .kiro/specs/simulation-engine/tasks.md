# Simulation Engine — Tasks

**Authored by Kiro in session 2026-11-03.**

---

## Task status legend

- [x] Complete in the integrated milestone; authorship notes distinguish Kiro and Codex work
- [ ] Future milestone

---

## This session (Milestone 2)

### T-1: Expand `interfaces.py` with richer engine contracts [x]

- Define `FactValue`, `Facts`, `Inject`, `Scenario`, `Decision`, `PlaybookAuthority`
- Define `ConditionOutcome`, `ChoiceOutcome`, `DecisionEvaluation`
- Define `Deviation`, `LogicalEvent`, `RunInput`, `RunResult`
- Define updated `SimulationEngine` Protocol with `run()` method
- Define `EngineError`, `TraversalBudgetExceeded`, `InvalidScenario` exceptions

### T-2: Implement `predicates.py` [x]

- `evaluate_condition`: missing-fact detection, type-mismatch detection, seven operators
- `evaluate_choice`: AND-composition of conditions
- `evaluate_decision_node`: classify exact/uncovered/overlap

### T-3: Implement `interpreter.py` [x]

- Pre-flight scenario validation (`InvalidScenario`)
- Main traversal loop with step budget (`TraversalBudgetExceeded`)
- Inject application (exactly once per inject, shallow-merge)
- `LogicalEvent` recording and SHA-256 hash chain
- Deviation detection and recording
- `RunResult` construction with `rehearsal_notice`

### T-4: Write unit tests for predicates [x]

- Missing fact → `False`, `missing_fact=True`
- Type mismatch: `bool` vs numeric op, `str` vs `gt`
- `True` does NOT satisfy `gt(field, 0)`
- `eq`/`neq` cross-type mismatch (bool ≠ int)
- All seven operators with matching and non-matching values
- AND-composition: all must match; any failure fails the choice

### T-5: Write unit tests for traversal [x]

- Simple straight-line graph (start → action → end)
- Decision node: exact match traversal
- Decision node: uncovered (zero matches) — run terminates
- Decision node: overlap (two matches) — run terminates
- Deviation: selected ≠ matched, deviation recorded, traversal continues
- Step budget: graph with cycle raises `TraversalBudgetExceeded`
- Inject: facts updated before named node, inject consumed once
- `InvalidScenario`: inject references absent node

### T-6: Write fixture integration tests [x]

- Night-market scenario: inject rain_risk=85 before weather; indoor_spaces=0 → `uncovered`
- Customer-support scenario: days_since_purchase=12, promotional=true → `overlap`
- Both runs carry `playbook_authority: "draft"`
- Both runs carry `rehearsal_notice`

### T-7: Write Hypothesis property tests [x]

- Determinism: same input → identical hash sequence
- Input immutability: original facts/graph unchanged after run
- Missing/mismatched facts never raise exceptions
- Budget: sufficiently deep graph always terminates within budget

### T-8: Run verification suite [x] — final verification by Codex

Kiro wrote this checklist prospectively, but its session was throttled before completing it.
Codex independently confirmed 78 backend tests and 3 frontend tests passed on the initial output,
while formatting and strict typing still failed. After local corrections, Codex ran make lint, make typecheck, make test (100 backend + 3 frontend),
make e2e (4 browser tests), and the frontend production build: all passed.
No Kiro e2e/build pass is claimed.

---

## Future milestones

### T-9: Session persistence [ ]

- Add `Scenario`, `SimulationSession`, `SessionEvent` migrations
- Persist `RunResult` as append-only `SessionEvent` rows
- Optimistic concurrency with `expected_revision`

### T-10: Replay and fork [ ]

- `POST /api/sessions` creates a new session
- `POST /api/sessions/{id}/choose` advances one decision step
- `POST /api/sessions/{id}/fork` from checkpoint
- Replay: same `RunInput` → identical `state_hash` sequence

### T-11: Approval workflow [ ]

- `POST /api/playbooks/{id}/approve` — explicit human review gate
- `POST /api/playbooks/{id}/revisions` — new version preserving immutable original

### T-12: Reports and comparison [ ]

- `GET /api/sessions/{id}/report` — decisions, evidence, deviations, gaps, overlaps
- `GET /api/sessions/compare` — two sessions side by side

### T-13: Simulation Room and Replay Lab UI [ ]

- React components for facts panel, decision panel, timeline, evidence drawer
- Replay Lab: checkpoint selector, fork, alternate choice, deterministic replay
- All wired to real API endpoints, no mocked state

### T-14: Harden for public deployment [ ]

- Rate limiting, body size limits, anonymous isolation, CORS hardening
- Persistent backup, fresh-install documentation, hosted demo

## Later Codex integration status (M3)

Without further Kiro calls, Codex implemented the persisted session/event work from T-9, the API
replay/fork work from T-10, reports/comparison from T-12, and Simulation Room with inline checkpoint
fork/comparison controls from T-13. These are Codex integration contributions, not work performed
in the original Kiro session. The original future-milestone checklist above records that session's
boundary. T-11 policy review and T-14 public hardening remain pending.
See docs/PERSISTED_REHEARSALS.md and docs/VALIDATION.md for exact scope and tests.
