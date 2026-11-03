# Simulation Engine — Requirements

**Authored by Kiro in session 2026-11-03.**
The placeholder README.md in this directory was Codex-authored. This spec begins Kiro's review.

**Codex review addendum (same date):** The initial Kiro session was throttled before final
verification. Local corrections are documented in docs/ENGINE_REVIEW.md and take precedence over
the initial sketches below. Interactive runs now pause by default; auto_rehearsal requires explicit
opt-in. Results retain a complete input snapshot and checkpoint diagnostics; every event carries
hashed authority/version/mode/context. Only actual decision choices enter decisions_made. Strict
finite facts, validated choice streams, and partial budget history are required. These corrections
and the additional generated-graph regressions were authored locally by Codex, without more Kiro calls.

---

## Context

The Codex-authored steering notes in `.kiro/steering/architecture.md` describe
`app/engine/interfaces.py` as "a Protocol contract only" and explicitly reserve matching,
overlap, and deviation interpretation for Kiro. The PRD states:

> Exactly one match is an unambiguous modeled path; zero matches is uncovered; multiple
> matches is potential overlap; selecting a nonmatch records a deviation.

The existing `SimulationEngine` Protocol exposes a single `evaluate()` method — too narrow.
This spec expands the contract to cover safe fact evaluation, scenario injection, traversal,
explicit deviations, deterministic hashing, and the authority boundary between draft rehearsal
and approved policy.

---

## REQ-1: Safe declarative predicates

**REQ-1.1** The engine MUST evaluate `Condition` objects (field/operator/value) without
executing user-supplied code. No `eval`, `exec`, `compile`, or dynamic attribute access on
arbitrary objects is permitted.

**REQ-1.2** Supported operators are exactly: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`.
No other operator string will ever be passed by the schema (Pydantic `Literal` enforces this),
but the engine MUST raise `EngineError` if an unrecognised operator appears at runtime.

**REQ-1.3** Boolean values MUST NOT be treated as numbers. A fact `{"flag": True}` does
NOT satisfy `gt(flag, 0)`. The `gt/gte/lt/lte` operators require that *both* the fact value
and the condition value are `int` or `float` (and not `bool`). Any other combination is a
**type mismatch** (see REQ-2).

**REQ-1.4** The `in` operator requires the condition value to be a list (enforced by schema)
and the fact value to be a scalar comparable to the list elements (eq-compatible). Membership
is determined by structural equality, not identity.

**REQ-1.5** `eq`/`neq` compare structural equality; `bool` and `int`/`float` are not
interchangeable (Python `True == 1` is True by default — the engine MUST reject this
cross-type comparison as a type mismatch).

**REQ-1.6** A list of conditions on a single choice is composed with AND: all conditions
must hold for the choice to match.

---

## REQ-2: Typed and missing facts

**REQ-2.1** A fact value is one of: `str`, `int`, `float`, `bool`. Lists are not valid
fact values (they are valid only as `in` condition operands).

**REQ-2.2** If a fact required by a condition is **absent** from the current fact dictionary,
the condition evaluates to `False`. This is not an error; it is a documented *missing fact*
outcome and MUST be recorded in the evaluation result.

**REQ-2.3** If a fact is present but its type is incompatible with the operator
(e.g., `str` compared with `gt`), the condition evaluates to `False` with a
**type mismatch** outcome recorded. This is not an error; it signals a model inconsistency
requiring human review.

**REQ-2.4** Missing-fact and type-mismatch outcomes MUST be surfaced in the
`ChoiceOutcome` for each evaluated choice so test assertions and future reporting can
distinguish them from genuine predicate failures.

---

## REQ-3: Choice matching results

**REQ-3.1 — Exactly one match (supported path):** All conditions of exactly one choice
are satisfied. The engine records this as an unambiguous traversal step.

**REQ-3.2 — Zero matches (uncovered path):** No choice's conditions are all satisfied.
The engine records this as an `UncoveredDecision` outcome. The engine MUST NOT invent a
policy response or silently pick a default. The run terminates at this decision node.

**REQ-3.3 — Multiple matches (overlap):** More than one choice's conditions are all
satisfied. The engine records this as an `OverlapDecision` outcome. The engine MUST NOT
silently pick one; the run terminates at this decision node with all matching choice IDs
recorded.

**REQ-3.4** The engine accepts an **optional** caller-supplied `selected_choice_id`. If
supplied when the result is exactly one match and it matches, traversal continues normally.
If supplied but it does not match the sole matched choice, a **deviation** is recorded (see REQ-5).
For uncovered/overlap outcomes, `selected_choice_id` is ignored — the run stops.

---

## REQ-4: Graph traversal and budget

**REQ-4.1** Traversal starts at the `start` node (identified by `type == "start"`).

**REQ-4.2** `start` and `action` nodes are traversed automatically via `next_node`;
no external decision input is required.

**REQ-4.3** `decision` nodes pause traversal and produce a `DecisionCheckpoint` in the
run result. The caller supplies choices; the engine evaluates them.

**REQ-4.4** `end` nodes terminate traversal normally.

**REQ-4.5** The graph MAY contain cycles (schema allows them). The engine MUST enforce a
**step budget** (default 200 steps) to prevent infinite loops. Exceeding the budget raises
`TraversalBudgetExceeded`. The budget is configurable per run.

**REQ-4.6** The input graph and input facts MUST be treated as immutable throughout a run.
The engine MUST NOT mutate them. Inject application creates a new facts dictionary
(see REQ-6).

---

## REQ-5: Deviations

**REQ-5.1** A deviation occurs when the caller selects a choice that is NOT among the
matching choices at a decision node with exactly one match.

**REQ-5.2** The deviation MUST be recorded with:
- the node ID and choice ID where it occurred,
- the expected matching choice ID(s),
- the actually selected choice ID,
- the source evidence (node and choice `source_refs` and `evidence_status`) at the time
  of deviation.

**REQ-5.3** After recording a deviation, the engine follows the selected (non-matching)
destination. The run is labeled `unapproved_deviation` in its status.

**REQ-5.4** The authority metadata MUST clarify that a draft playbook rehearsal does not
establish policy. The `PlaybookAuthority` field in the run result carries
`status: "draft" | "approved"` from the caller. A deviation on a draft is doubly
unapproved.

---

## REQ-6: Scenario injects

**REQ-6.1** A scenario has `initial_facts` (dict) and `injects` (ordered list of
`{before_node_id, facts}` objects).

**REQ-6.2** Injects are applied **exactly once**, in order, immediately before the engine
processes the named node. An inject merges (shallow-updates) its facts over the current
fact dictionary, producing a new dictionary.

**REQ-6.3** Each inject is applied at most once per run even if the target node is visited
multiple times (cycle case). A consumed inject is marked and skipped on subsequent visits.

**REQ-6.4** The engine MUST NOT use wall-clock time or OS randomness. The `seed` field in
the scenario is reserved for reproducible future use (e.g., random-event selection) and is
passed through to the run result unchanged. It does not currently affect engine behavior.

**REQ-6.5** Injects referencing a `before_node_id` that does not exist in the graph MUST
raise `InvalidScenario` before the run begins.

---

## REQ-7: Deterministic logical hashing

**REQ-7.1** Every `LogicalEvent` in a run has a `state_hash` computed from:
- the playbook version ID (stable string from caller),
- the sequence number of the event,
- the current node ID,
- the current fact dictionary (sorted keys, values repr-stable),
- the event type and payload (choice ID, deviation flag),
- the hashes of all previous events in order.

**REQ-7.2** The hash MUST exclude: generated UUIDs, wall-clock timestamps, Python object
identity, OS-level random state, and anything else non-deterministic.

**REQ-7.3** Replaying the same graph, same scenario (version/seed/injects), and the same
sequence of selected choices MUST produce identical hashes for every event.

**REQ-7.4** The hash function is SHA-256 over the canonical JSON encoding of the event
inputs (sorted keys, no whitespace).

---

## REQ-8: Draft authority boundary

**REQ-8.1** The engine MUST accept a `playbook_authority` parameter indicating whether
the playbook being run is `"draft"` or `"approved"`.

**REQ-8.2** All run results and events MUST carry this authority label. No result from a
draft run may be presented without the label.

**REQ-8.3** The engine MUST NOT approve, elevate, or cache a playbook. It MUST NOT accept
a playbook that claims to be `"approved"` unless the caller explicitly asserts this. The
engine trusts the caller's assertion and records it; enforcement of the approval workflow
is the API layer's responsibility.

**REQ-8.4** In tests and rehearsals, any run using a seeded fixture graph MUST be labeled
`status: "draft"` because all seeded playbooks have `status == "draft"`.

---

## REQ-9: Future replay and fork contracts (boundary)

**REQ-9.1** The engine MUST produce a `RunResult` with enough information for a future
replay layer to reconstruct the identical run deterministically. This includes: the ordered
`LogicalEvent` list with hashes, the final fact state, the playbook version ID, the scenario
(version, seed, initial facts, injects), and the list of selected choices.

**REQ-9.2** Persisted replay, fork APIs, comparison, and session storage belong to the
NEXT milestone. This milestone MUST NOT add stub endpoints or fake success responses for
those features.

**REQ-9.3** The `RunResult` model MUST be serialisable to JSON (Pydantic `model_dump()`
with `mode="json"`). The serialisation is the canonical form for future persistence.

---

## Acceptance criteria summary

| ID     | Criterion |
|--------|-----------|
| AC-1   | `evaluate_condition` returns `False` (not error) for missing fact; records `missing_fact=True` |
| AC-2   | `evaluate_condition` returns `False` for type mismatch (bool vs numeric op); records `type_mismatch=True` |
| AC-3   | `True` fact does NOT satisfy `gt(field, 0)` |
| AC-4   | A decision node with zero matching choices produces `UncoveredDecision`; no traversal continues |
| AC-5   | A decision node with two matching choices produces `OverlapDecision`; no traversal continues |
| AC-6   | Night-market scenario (rain_risk injected to 85, indoor_spaces=0) reaches `UncoveredDecision` at `weather` |
| AC-7   | Customer-support scenario (days_since_purchase=12, promotional_purchase=True) produces `OverlapDecision` at `refund` |
| AC-8   | A selected choice that does not match records a `Deviation` and continues to that choice's destination |
| AC-9   | Two runs with identical inputs and decisions produce identical `state_hash` sequences |
| AC-10  | Exceeding the step budget raises `TraversalBudgetExceeded` |
| AC-11  | All run results carry `playbook_authority` label; draft runs are labeled accordingly |
| AC-12  | `InvalidScenario` raised for inject referencing absent node ID |
| AC-13  | Existing 18 backend tests continue to pass; Source Studio unaffected |
