# Simulation Engine — Design

**Authored by Kiro in session 2026-11-03.**

**Codex review addendum (same date):** The initial Kiro session was throttled before final
verification. Local corrections are documented in docs/ENGINE_REVIEW.md and take precedence over
the initial sketches below. Interactive runs now pause by default; auto_rehearsal requires explicit
opt-in. Results retain a complete input snapshot and checkpoint diagnostics; every event carries
hashed authority/version/mode/context. Only actual decision choices enter decisions_made. Strict
finite facts, validated choice streams, and partial budget history are required. These corrections
and the additional generated-graph regressions were authored locally by Codex, without more Kiro calls.

---

## Review of initial Protocol

The Codex-authored `app/engine/interfaces.py` defines:

```python
class SimulationEngine(Protocol):
    def evaluate(self, graph: Graph, node_id: str, facts: dict[str, JsonValue]) -> Evaluation:
        ...
```

This single-method Protocol is intentionally minimal — Codex explicitly reserved the
semantics for Kiro. After reviewing the PRD, architecture, and fixtures, I identified
the following gaps:

1. **No traversal model.** `evaluate()` evaluates a single node. The engine needs to
   drive traversal across the whole graph (start → decision → action → end).
2. **No inject model.** Facts change mid-run via scenario injects. A single-call design
   cannot express this without callers managing state externally.
3. **No deviation model.** The caller's `selected_choice_id` is not accepted, so
   deviation detection is impossible.
4. **No hash model.** Deterministic hashing requires a sequence of events; a single
   `Evaluation` object cannot carry this.
5. **Evaluation return type too narrow.** `matching_choice_ids: list[str]` does not
   distinguish zero matches (uncovered) from multiple matches (overlap), nor does it
   surface the per-condition outcomes (missing fact, type mismatch).

**Decision:** Expand `interfaces.py` to define richer input/output contracts while
retaining backwards compatibility for the existing narrow `Evaluation` (renamed
`DecisionEvaluation`) as the per-node unit. Add `RunInput`, `RunResult`, and
`SimulationEngine` updated Protocol. The old method signature is superseded; no code
outside of tests referenced it at the time of this implementation.

---

## Module layout

```
services/api/app/engine/
    __init__.py          (unchanged)
    interfaces.py        (expanded — Kiro-authored types and Protocol)
    predicates.py        (Kiro) condition evaluation, type/missing-fact detection
    interpreter.py       (Kiro) graph traversal, inject application, hash chain
```

---

## Data model

### Input types

```
FactValue   = str | int | float | bool   (not list)
Facts       = dict[str, FactValue]

Inject = {before_node_id: str, facts: Facts}

Scenario = {
    title: str,
    seed: int,
    initial_facts: Facts,
    injects: list[Inject],
}

PlaybookAuthority = Literal["draft", "approved"]

RunInput = {
    playbook_version_id: str,
    playbook_authority: PlaybookAuthority,
    graph: Graph,
    scenario: Scenario,
    decisions: list[Decision],   # ordered, one per decision node visited
}

Decision = {
    node_id: str,
    selected_choice_id: str | None,
}
```

### Per-condition outcome

```
ConditionOutcome = {
    condition: Condition,
    result: bool,
    missing_fact: bool,
    type_mismatch: bool,
}
```

### Per-choice evaluation

```
ChoiceOutcome = {
    choice_id: str,
    matched: bool,
    condition_outcomes: list[ConditionOutcome],
}
```

### Decision evaluation (per node)

```
DecisionResult = "exact_match" | "uncovered" | "overlap"

DecisionEvaluation = {
    node_id: str,
    result: DecisionResult,
    matching_choice_ids: list[str],
    choice_outcomes: list[ChoiceOutcome],
    facts_snapshot: Facts,     # facts at time of evaluation (after any inject)
}
```

### Deviation

```
Deviation = {
    node_id: str,
    selected_choice_id: str,
    matching_choice_ids: list[str],
    node_source_refs: list[str],
    choice_source_refs: list[str],
    choice_evidence_status: str,
}
```

### Logical event and hash chain

Each traversal step produces a `LogicalEvent`:

```
EventType = "node_entered" | "inject_applied" | "decision_evaluated"
          | "deviation_recorded" | "run_terminated"

LogicalEvent = {
    sequence: int,           # 0-indexed, monotonically increasing
    event_type: EventType,
    node_id: str,
    payload: dict,           # event-specific data (choice_id, deviation, etc.)
    facts_snapshot: Facts,   # fact state after this event
    state_hash: str,         # SHA-256, see REQ-7
}
```

Hash input (serialised to compact JSON, sorted keys):

```json
{
  "playbook_version_id": "...",
  "sequence": 3,
  "node_id": "weather",
  "event_type": "decision_evaluated",
  "payload": { ... },
  "facts_snapshot": { ... },
  "prev_hash": "sha256 of event N-1, or empty string for event 0"
}
```

### Run result

```
RunStatus = "completed" | "uncovered" | "overlap" | "deviation"
          | "budget_exceeded" | "invalid_scenario"

RunResult = {
    playbook_version_id: str,
    playbook_authority: PlaybookAuthority,
    scenario_title: str,
    scenario_seed: int,
    status: RunStatus,
    events: list[LogicalEvent],
    deviations: list[Deviation],
    final_facts: Facts,
    decisions_made: list[Decision],    # echoed back from input or auto-traversed
    rehearsal_notice: str,             # always present — "This is a model-only rehearsal ..."
}
```

---

## Predicate evaluation (`predicates.py`)

```python
def evaluate_condition(condition: Condition, facts: Facts) -> ConditionOutcome:
```

Logic (no eval, no exec):

1. Look up `condition.field` in `facts`. If absent → `result=False, missing_fact=True`.
2. Check type compatibility per operator:
   - `gt/gte/lt/lte`: both fact value and condition value must be `int|float` and NOT `bool`.
     If not → `result=False, type_mismatch=True`.
   - `eq/neq`: types must match exactly (no cross-`bool`/numeric coercion).
     If not → `result=False, type_mismatch=True`.
   - `in`: fact value must be a scalar; condition value is always a list (schema-enforced).
     Type check: each list element must match the fact value's type.
     If not → `result=False, type_mismatch=True`.
3. Evaluate the operator:
   - `eq`: `fact_val == cond_val` (same type already confirmed)
   - `neq`: `fact_val != cond_val`
   - `gt`: `fact_val > cond_val`
   - `gte`: `fact_val >= cond_val`
   - `lt`: `fact_val < cond_val`
   - `lte`: `fact_val <= cond_val`
   - `in`: `fact_val in cond_val`

```python
def evaluate_choice(choice: Choice, facts: Facts) -> ChoiceOutcome:
    outcomes = [evaluate_condition(c, facts) for c in choice.conditions]
    matched = all(o.result for o in outcomes)
    return ChoiceOutcome(choice_id=choice.id, matched=matched, condition_outcomes=outcomes)
```

```python
def evaluate_decision_node(node: Node, facts: Facts) -> DecisionEvaluation:
    choice_outcomes = [evaluate_choice(c, facts) for c in node.choices]
    matching = [o.choice_id for o in choice_outcomes if o.matched]
    result = (
        "exact_match" if len(matching) == 1
        else "uncovered" if len(matching) == 0
        else "overlap"
    )
    return DecisionEvaluation(
        node_id=node.id, result=result,
        matching_choice_ids=matching,
        choice_outcomes=choice_outcomes,
        facts_snapshot=dict(facts),
    )
```

---

## Traversal interpreter (`interpreter.py`)

```python
def run(input: RunInput) -> RunResult:
```

Pre-flight validation:
- All `inject.before_node_id` values exist in the graph → else `InvalidScenario`.
- Build `node_map: dict[str, Node]`.
- Build `pending_injects: list[tuple[int, Inject]]` (index + inject, for consumed tracking).

Main loop:
```
facts = dict(input.scenario.initial_facts)
events = []
deviations = []
step = 0
current_id = start_node.id
decision_queue = list(input.decisions)   # pop front as needed

while True:
    if step >= budget: raise TraversalBudgetExceeded
    step += 1

    # apply pending injects for this node
    for inject in unconsulted_injects_for(current_id):
        facts = {**facts, **inject.facts}
        record LogicalEvent(inject_applied)
        mark inject consumed

    node = node_map[current_id]
    record LogicalEvent(node_entered)

    if node.type == "end":
        record LogicalEvent(run_terminated, status="completed")
        break

    if node.type in ("start", "action"):
        current_id = node.next_node
        continue

    # decision node
    evaluation = evaluate_decision_node(node, facts)
    record LogicalEvent(decision_evaluated, evaluation)

    if evaluation.result in ("uncovered", "overlap"):
        record LogicalEvent(run_terminated, status=evaluation.result)
        return RunResult(status=evaluation.result, ...)

    # exactly one match
    [matched_id] = evaluation.matching_choice_ids
    decision = decision_queue.pop(0) if decision_queue else None
    selected_id = decision.selected_choice_id if decision else matched_id

    if selected_id != matched_id:
        dev = Deviation(node_id=..., selected_choice_id=selected_id,
                        matching_choice_ids=[matched_id], ...)
        deviations.append(dev)
        record LogicalEvent(deviation_recorded, dev)

    # follow the selected destination
    chosen = next(c for c in node.choices if c.id == selected_id)
    current_id = chosen.destination
```

---

## Hashing

```python
def _compute_hash(
    playbook_version_id: str,
    sequence: int,
    node_id: str,
    event_type: str,
    payload: dict,
    facts_snapshot: dict,
    prev_hash: str,
) -> str:
    data = {
        "playbook_version_id": playbook_version_id,
        "sequence": sequence,
        "node_id": node_id,
        "event_type": event_type,
        "payload": payload,
        "facts_snapshot": facts_snapshot,
        "prev_hash": prev_hash,
    }
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"),
                           default=_json_default)
    return hashlib.sha256(canonical.encode()).hexdigest()
```

`_json_default` raises `TypeError` for any non-serialisable type, making hash computation
fail fast rather than silently encoding garbage.

---

## Updated `interfaces.py`

The old `Evaluation` model is replaced by the richer types described above. The Protocol
is updated to:

```python
class SimulationEngine(Protocol):
    def run(self, input: RunInput) -> RunResult:
        """Execute a full traversal; return a deterministic, immutable result."""
        ...
```

The old `evaluate()` signature is removed because no external code referenced it at this
milestone. The predicate-level `evaluate_decision_node` function remains accessible
for unit testing.

---

## Authority and rehearsal notice

Every `RunResult` carries:

```
rehearsal_notice = (
    "This is a model-only rehearsal of a {status} playbook. "
    "No result constitutes approved policy or emergency guidance. "
    "All seeded rules require human review before operational use."
)
```

The weather graph's capacity guard is a modeled assumption. Running it via the engine does
not change this. The engine has no mechanism to approve a draft.

---

## What this milestone does NOT implement

- Session persistence (no DB writes for simulation state)
- Replay/fork APIs or endpoints
- Simulation Room or Replay Lab UI
- Approval workflow
- RuleProposal model
- Comparison or after-action report endpoints

These belong to subsequent milestones per the PRD and `NEXT_KIRO_TASKS.md`.
