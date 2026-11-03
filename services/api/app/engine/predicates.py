"""Safe declarative predicate evaluation for GhostShift simulation engine.

Kiro-authored in session 2026-11-03.
Codex review added typed outcome construction, evidence preservation and finite-fact checks.

Implements REQ-1 through REQ-3 from .kiro/specs/simulation-engine/requirements.md.

Key invariants:
- NO eval, exec, compile, or dynamic attribute access on arbitrary objects.
- Boolean values are NEVER treated as numbers. True/False do NOT satisfy gt/gte/lt/lte.
- Missing facts produce result=False with missing_fact=True — not an exception.
- Type mismatches produce result=False with type_mismatch=True — not an exception.
- eq/neq cross-bool/numeric comparisons are type mismatches (Python True==1 is suppressed).
"""

from __future__ import annotations

from math import isfinite

from app.engine.interfaces import (
    ChoiceOutcome,
    ConditionOutcome,
    DecisionEvaluation,
    DecisionResult,
    Facts,
    FactValue,
)
from app.schemas.graph import Choice, Condition, Node


def _outcome(
    condition: Condition, *, result: bool, missing_fact: bool = False, type_mismatch: bool = False
) -> ConditionOutcome:
    return ConditionOutcome(
        field=condition.field,
        operator=condition.operator,
        value=condition.value,
        result=result,
        missing_fact=missing_fact,
        type_mismatch=type_mismatch,
    )


def evaluate_condition(condition: Condition, facts: Facts) -> ConditionOutcome:
    """Evaluate one Condition against the current fact dictionary.

    Returns a ConditionOutcome with:
    - result: bool — whether the condition is satisfied
    - missing_fact: True if the field is absent from facts
    - type_mismatch: True if the fact type is incompatible with the operator
    """
    # --- 1. Missing fact ---
    if condition.field not in facts:
        return _outcome(condition, result=False, missing_fact=True)

    fact_val: FactValue = facts[condition.field]
    if isinstance(fact_val, float) and not isfinite(fact_val):
        return _outcome(condition, result=False, type_mismatch=True)
    op = condition.operator
    cond_val = condition.value

    # --- 2. Type compatibility checks ---

    if op in {"gt", "gte", "lt", "lte"}:
        # Both sides must be int or float, and NOT bool.
        # schema already enforces cond_val is numeric non-bool, but we check both sides.
        if isinstance(fact_val, bool) or not isinstance(fact_val, (int, float)):
            return _outcome(condition, result=False, type_mismatch=True)
        # cond_val guaranteed numeric non-bool by Condition schema validator
        # but belt-and-suspenders:
        if isinstance(cond_val, bool) or not isinstance(cond_val, (int, float)):  # pragma: no cover
            return _outcome(condition, result=False, type_mismatch=True)

    elif op in {"eq", "neq"}:
        # Suppress Python's True==1 cross-type equality.
        # bool is a subclass of int, so we must explicitly check for cross-bool/numeric.
        if type(fact_val) is not type(cond_val):
            # Allow int vs float comparisons (3 == 3.0 is legitimate in policy data).
            # Disallow bool vs int/float, str vs anything numeric, etc.
            fv_numeric = isinstance(fact_val, (int, float)) and not isinstance(fact_val, bool)
            cv_numeric = isinstance(cond_val, (int, float)) and not isinstance(cond_val, bool)
            if not (fv_numeric and cv_numeric):
                return _outcome(condition, result=False, type_mismatch=True)

    elif op == "in":
        # cond_val is a list (schema-enforced). fact_val must be scalar.
        if isinstance(fact_val, list):  # facts must be scalars
            return _outcome(condition, result=False, type_mismatch=True)
        assert isinstance(cond_val, list), "schema ensures in-operator value is a list"
        # Type check: every list element and fact_val must be compatible (same type rules
        # as eq). If any element is type-incompatible, we treat the membership as False
        # with type_mismatch to avoid silent cross-type comparisons.
        for elem in cond_val:
            if type(elem) is not type(fact_val):
                fv_n = isinstance(fact_val, (int, float)) and not isinstance(fact_val, bool)
                el_n = isinstance(elem, (int, float)) and not isinstance(elem, bool)
                if not (fv_n and el_n):
                    return _outcome(condition, result=False, type_mismatch=True)

    # --- 3. Evaluate ---

    result: bool
    if op == "eq":
        result = fact_val == cond_val
    elif op == "neq":
        result = fact_val != cond_val
    elif op == "gt":
        assert isinstance(fact_val, (int, float)) and not isinstance(fact_val, bool)
        assert isinstance(cond_val, (int, float)) and not isinstance(cond_val, bool)
        result = fact_val > cond_val
    elif op == "gte":
        assert isinstance(fact_val, (int, float)) and not isinstance(fact_val, bool)
        result = fact_val >= cond_val  # type: ignore[operator]
    elif op == "lt":
        assert isinstance(fact_val, (int, float)) and not isinstance(fact_val, bool)
        result = fact_val < cond_val  # type: ignore[operator]
    elif op == "lte":
        assert isinstance(fact_val, (int, float)) and not isinstance(fact_val, bool)
        result = fact_val <= cond_val  # type: ignore[operator]
    elif op == "in":
        assert isinstance(cond_val, list)
        result = fact_val in cond_val
    else:
        # Unreachable if Pydantic schema is enforced, but required by REQ-1.2.
        from app.engine.interfaces import EngineError

        raise EngineError(f"Unrecognised operator: {op!r}")

    return _outcome(condition, result=result)


def evaluate_choice(choice: Choice, facts: Facts) -> ChoiceOutcome:
    """Evaluate all conditions on a choice with AND composition.

    A choice matches only if ALL conditions evaluate to True.
    Any missing-fact or type-mismatch condition causes the choice not to match.
    """
    outcomes = [evaluate_condition(c, facts) for c in choice.conditions]
    matched = all(o.result for o in outcomes)
    return ChoiceOutcome(
        choice_id=choice.id,
        matched=matched,
        condition_outcomes=outcomes,
        source_refs=list(choice.source_refs),
        evidence_status=choice.evidence_status,
    )


def evaluate_decision_node(node: Node, facts: Facts) -> DecisionEvaluation:
    """Evaluate all choices on a decision node and classify the result.

    Returns a DecisionEvaluation with:
    - result: "exact_match" | "uncovered" | "overlap"
    - matching_choice_ids: list of choice IDs whose conditions all held
    - choice_outcomes: full per-choice breakdown for audit/debugging
    - facts_snapshot: copy of facts at evaluation time
    """
    if node.type != "decision":
        raise ValueError(f"evaluate_decision_node called on non-decision node {node.id!r}")

    choice_outcomes = [evaluate_choice(c, facts) for c in node.choices]
    matching = [o.choice_id for o in choice_outcomes if o.matched]

    result: DecisionResult
    if len(matching) == 1:
        result = "exact_match"
    elif len(matching) == 0:
        result = "uncovered"
    else:
        result = "overlap"

    return DecisionEvaluation(
        node_id=node.id,
        result=result,
        matching_choice_ids=matching,
        choice_outcomes=choice_outcomes,
        facts_snapshot=dict(facts),
        node_source_refs=list(node.source_refs),
    )
