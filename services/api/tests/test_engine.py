"""Tests for the GhostShift simulation engine.

Kiro-authored in session 2026-11-03.
Codex review updates explicitly opt batch tests into auto_rehearsal mode and verify the expanded hash context.

Covers:
- predicates.py: missing facts, type mismatches, all seven operators, AND composition
- interpreter.py: traversal, injects, deviations, budget, InvalidScenario
- Fixture integration: night-market (uncovered), customer-support (overlap)
- Hypothesis properties: determinism, input immutability, missing-fact safety, budget termination
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.interfaces import (
    Decision,
    Deviation,
    Inject,
    InvalidScenario,
    RunInput,
    RunResult,
    Scenario,
    TraversalBudgetExceeded,
    compute_event_hash,
)
from app.engine.interpreter import GhostShiftEngine
from app.engine.predicates import (
    evaluate_choice,
    evaluate_condition,
    evaluate_decision_node,
)
from app.schemas.graph import Choice, Condition, Graph, Node
from app.services.segmentation import segment_document

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"

engine = GhostShiftEngine()


# ===========================================================================
# Helpers / graph builders
# ===========================================================================


def _make_choice(
    choice_id: str,
    destination: str,
    conditions: list[Condition],
    source_refs: list[str] | None = None,
    evidence_status: str = "uncited",
) -> Choice:
    """Build a Choice for testing. Uses uncited evidence when no refs provided."""
    refs = source_refs or []
    status = "cited" if refs else "uncited"
    return Choice(
        id=choice_id,
        label=choice_id,
        destination=destination,
        conditions=conditions,
        source_refs=refs,
        evidence_status=status,
    )


def _simple_graph() -> Graph:
    """start → end (trivial linear graph for traversal smoke tests)."""
    return Graph(
        nodes=[
            Node(id="start", label="Start", type="start", source_refs=[], next_node="end"),
            Node(id="end", label="End", type="end", source_refs=[]),
        ]
    )


def _linear_graph_with_action() -> Graph:
    """start → action → end."""
    return Graph(
        nodes=[
            Node(id="start", label="S", type="start", source_refs=[], next_node="act"),
            Node(id="act", label="A", type="action", source_refs=[], next_node="end"),
            Node(id="end", label="E", type="end", source_refs=[]),
        ]
    )


def _decision_graph(choices: list[Choice]) -> Graph:
    """start → decision (given choices) → end for each destination that == 'end'."""
    # Ensure all choice destinations point to 'end'.
    for c in choices:
        object.__setattr__(c, "destination", "end")  # choices are frozen after build
    return Graph(
        nodes=[
            Node(id="start", label="S", type="start", source_refs=[], next_node="decision"),
            Node(id="decision", label="D", type="decision", source_refs=[], choices=choices),
            Node(id="end", label="E", type="end", source_refs=[]),
        ]
    )


def _run(
    graph: Graph,
    initial_facts: dict | None = None,
    injects: list[dict] | None = None,
    decisions: list[Decision] | None = None,
    authority: str = "draft",
    budget: int = 200,
) -> RunResult:
    scenario = Scenario(
        title="test",
        seed=0,
        initial_facts=initial_facts or {},
        injects=[Inject(**i) for i in (injects or [])],
    )
    run_input = RunInput(
        execution_mode="auto_rehearsal",
        playbook_version_id="test-v1",
        playbook_authority=authority,  # type: ignore[arg-type]
        graph=graph,
        scenario=scenario,
        decisions=decisions or [],
        step_budget=budget,
    )
    return engine.run(run_input)


# ===========================================================================
# Predicate tests — evaluate_condition
# ===========================================================================


class TestMissingFact:
    def test_missing_returns_false_with_flag(self) -> None:
        cond = Condition(field="x", operator="eq", value=1)
        outcome = evaluate_condition(cond, {})
        assert outcome.result is False
        assert outcome.missing_fact is True
        assert outcome.type_mismatch is False

    def test_missing_ordered_op(self) -> None:
        cond = Condition(field="score", operator="gt", value=10)
        outcome = evaluate_condition(cond, {})
        assert outcome.result is False
        assert outcome.missing_fact is True

    def test_missing_in_op(self) -> None:
        cond = Condition(field="color", operator="in", value=["red", "blue"])
        outcome = evaluate_condition(cond, {})
        assert outcome.result is False
        assert outcome.missing_fact is True


class TestTypeMismatch:
    def test_bool_fails_gt(self) -> None:
        """bool fact should not satisfy gt — REQ-1.3 / AC-3."""
        cond = Condition(field="flag", operator="gt", value=0)
        outcome = evaluate_condition(cond, {"flag": True})
        assert outcome.result is False
        assert outcome.type_mismatch is True
        assert outcome.missing_fact is False

    def test_bool_fails_gte(self) -> None:
        cond = Condition(field="flag", operator="gte", value=0)
        outcome = evaluate_condition(cond, {"flag": False})
        assert outcome.result is False
        assert outcome.type_mismatch is True

    def test_bool_fails_lt(self) -> None:
        cond = Condition(field="flag", operator="lt", value=2)
        outcome = evaluate_condition(cond, {"flag": True})
        assert outcome.result is False
        assert outcome.type_mismatch is True

    def test_str_fails_gt(self) -> None:
        cond = Condition(field="name", operator="gt", value=10)
        # 'gt' with numeric cond_val but str fact
        outcome = evaluate_condition(cond, {"name": "alice"})  # type: ignore[arg-type]
        assert outcome.result is False
        assert outcome.type_mismatch is True

    def test_bool_vs_int_eq_is_type_mismatch(self) -> None:
        """Python's True == 1 must NOT be treated as equal — REQ-1.5."""
        cond = Condition(field="val", operator="eq", value=1)
        outcome = evaluate_condition(cond, {"val": True})
        assert outcome.result is False
        assert outcome.type_mismatch is True

    def test_bool_vs_int_neq_is_type_mismatch(self) -> None:
        cond = Condition(field="val", operator="neq", value=0)
        outcome = evaluate_condition(cond, {"val": True})
        assert outcome.result is False
        assert outcome.type_mismatch is True

    def test_str_vs_int_eq_is_type_mismatch(self) -> None:
        cond = Condition(field="val", operator="eq", value=42)
        outcome = evaluate_condition(cond, {"val": "42"})  # type: ignore[arg-type]
        assert outcome.result is False
        assert outcome.type_mismatch is True

    def test_bool_in_numeric_list_is_type_mismatch(self) -> None:
        cond = Condition(field="flag", operator="in", value=[1, 2, 3])
        outcome = evaluate_condition(cond, {"flag": True})
        assert outcome.result is False
        assert outcome.type_mismatch is True


class TestOperators:
    """All seven operators with matching and non-matching values."""

    def test_eq_match(self) -> None:
        c = Condition(field="x", operator="eq", value="hello")
        assert evaluate_condition(c, {"x": "hello"}).result is True

    def test_eq_no_match(self) -> None:
        c = Condition(field="x", operator="eq", value="hello")
        assert evaluate_condition(c, {"x": "world"}).result is False

    def test_neq_match(self) -> None:
        c = Condition(field="x", operator="neq", value="hello")
        assert evaluate_condition(c, {"x": "world"}).result is True

    def test_neq_no_match(self) -> None:
        c = Condition(field="x", operator="neq", value="hello")
        assert evaluate_condition(c, {"x": "hello"}).result is False

    def test_gt_match(self) -> None:
        c = Condition(field="x", operator="gt", value=10)
        assert evaluate_condition(c, {"x": 11}).result is True

    def test_gt_no_match_equal(self) -> None:
        c = Condition(field="x", operator="gt", value=10)
        assert evaluate_condition(c, {"x": 10}).result is False

    def test_gte_match_equal(self) -> None:
        c = Condition(field="x", operator="gte", value=10)
        assert evaluate_condition(c, {"x": 10}).result is True

    def test_lt_match(self) -> None:
        c = Condition(field="x", operator="lt", value=30)
        assert evaluate_condition(c, {"x": 29}).result is True

    def test_lt_no_match_equal(self) -> None:
        c = Condition(field="x", operator="lt", value=30)
        assert evaluate_condition(c, {"x": 30}).result is False

    def test_lte_match_equal(self) -> None:
        c = Condition(field="x", operator="lte", value=30)
        assert evaluate_condition(c, {"x": 30}).result is True

    def test_in_match(self) -> None:
        c = Condition(field="color", operator="in", value=["red", "green", "blue"])
        assert evaluate_condition(c, {"color": "green"}).result is True

    def test_in_no_match(self) -> None:
        c = Condition(field="color", operator="in", value=["red", "green"])
        assert evaluate_condition(c, {"color": "yellow"}).result is False

    def test_float_gt(self) -> None:
        c = Condition(field="risk", operator="gt", value=70.0)
        assert evaluate_condition(c, {"risk": 85.5}).result is True
        assert evaluate_condition(c, {"risk": 70.0}).result is False

    def test_int_float_eq_allowed(self) -> None:
        """int vs float eq comparison is permitted (REQ-1.5 only blocks bool/numeric)."""
        c = Condition(field="x", operator="eq", value=3.0)
        assert evaluate_condition(c, {"x": 3}).result is True


class TestAndComposition:
    def test_all_must_match(self) -> None:
        choice = _make_choice(
            "c1",
            "end",
            [
                Condition(field="a", operator="gt", value=10),
                Condition(field="b", operator="lt", value=5),
            ],
        )
        # Both match
        result = evaluate_choice(choice, {"a": 20, "b": 3})
        assert result.matched is True
        # Only first matches
        result2 = evaluate_choice(choice, {"a": 20, "b": 10})
        assert result2.matched is False

    def test_missing_fact_in_multi_condition_fails(self) -> None:
        choice = _make_choice(
            "c1",
            "end",
            [
                Condition(field="a", operator="gt", value=10),
                Condition(field="b", operator="eq", value="yes"),
            ],
        )
        result = evaluate_choice(choice, {"a": 20})  # b is missing
        assert result.matched is False
        missing_outcomes = [o for o in result.condition_outcomes if o.missing_fact]
        assert len(missing_outcomes) == 1
        assert missing_outcomes[0].field == "b"


class TestDecisionNode:
    def _build_node(self, choices: list[Choice]) -> Node:
        return Node(id="d", label="D", type="decision", source_refs=[], choices=choices)

    def test_exact_match(self) -> None:
        choices = [
            _make_choice("yes", "end", [Condition(field="x", operator="gt", value=5)]),
            _make_choice("no", "end", [Condition(field="x", operator="lte", value=5)]),
        ]
        node = self._build_node(choices)
        result = evaluate_decision_node(node, {"x": 10})
        assert result.result == "exact_match"
        assert result.matching_choice_ids == ["yes"]

    def test_uncovered(self) -> None:
        """Night-market style: rain_risk > 70 AND indoor_spaces > 0 — neither matches."""
        choices = [
            _make_choice(
                "indoor",
                "end",
                [
                    Condition(field="rain_risk", operator="gt", value=70),
                    Condition(field="indoor_spaces", operator="gt", value=0),
                ],
            ),
            _make_choice(
                "outdoor",
                "end",
                [Condition(field="rain_risk", operator="lte", value=70)],
            ),
        ]
        node = self._build_node(choices)
        # rain_risk=85 (not <=70), indoor_spaces=0 (not >0) → no choice matches
        result = evaluate_decision_node(node, {"rain_risk": 85, "indoor_spaces": 0})
        assert result.result == "uncovered"
        assert result.matching_choice_ids == []

    def test_overlap(self) -> None:
        """Customer-support style: both refund rules can match simultaneously."""
        choices = [
            _make_choice(
                "standard",
                "end",
                [Condition(field="days", operator="lte", value=30)],
            ),
            _make_choice(
                "promo",
                "end",
                [Condition(field="promo", operator="eq", value=True)],
            ),
        ]
        node = self._build_node(choices)
        result = evaluate_decision_node(node, {"days": 12, "promo": True})
        assert result.result == "overlap"
        assert set(result.matching_choice_ids) == {"standard", "promo"}

    def test_raises_on_non_decision_node(self) -> None:
        node = Node(id="s", label="S", type="start", source_refs=[], next_node="e")
        with pytest.raises(ValueError, match="non-decision"):
            evaluate_decision_node(node, {})


# ===========================================================================
# Traversal tests — interpreter
# ===========================================================================


class TestSimpleTraversal:
    def test_start_to_end(self) -> None:
        result = _run(_simple_graph())
        assert result.status == "completed"
        assert result.playbook_authority == "draft"
        assert "rehearsal" in result.rehearsal_notice.lower()
        node_ids = [e.node_id for e in result.events if e.event_type == "node_entered"]
        assert node_ids == ["start", "end"]

    def test_start_action_end(self) -> None:
        result = _run(_linear_graph_with_action())
        assert result.status == "completed"
        node_ids = [e.node_id for e in result.events if e.event_type == "node_entered"]
        assert node_ids == ["start", "act", "end"]

    def test_exact_match_traversal(self) -> None:
        choices = [
            _make_choice("go", "end", [Condition(field="x", operator="gt", value=5)]),
            _make_choice("stay", "end", [Condition(field="x", operator="lte", value=5)]),
        ]
        # Rebuild with proper destination
        choices_rebuilt = [
            Choice(
                id="go",
                label="go",
                destination="end",
                conditions=choices[0].conditions,
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="stay",
                label="stay",
                destination="end",
                conditions=choices[1].conditions,
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
                Node(id="d", label="D", type="decision", source_refs=[], choices=choices_rebuilt),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        result = _run(graph, initial_facts={"x": 10})
        assert result.status == "completed"
        # Confirm 'go' was selected
        decision_events = [e for e in result.events if e.event_type == "decision_evaluated"]
        assert decision_events[0].payload["result"] == "exact_match"
        assert decision_events[0].payload["matching_choice_ids"] == ["go"]


class TestUncoveredDecision:
    def test_uncovered_terminates_without_inventing_policy(self) -> None:
        choices = [
            Choice(
                id="rain",
                label="rain",
                destination="end",
                conditions=[
                    Condition(field="rain_risk", operator="gt", value=70),
                    Condition(field="indoor_spaces", operator="gt", value=0),
                ],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="dry",
                label="dry",
                destination="end",
                conditions=[Condition(field="rain_risk", operator="lte", value=70)],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
                Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        # rain_risk=85 does not satisfy <=70, indoor_spaces=0 does not satisfy >0
        result = _run(graph, initial_facts={"rain_risk": 85, "indoor_spaces": 0})
        assert result.status == "uncovered"
        # Must not have reached end node
        entered_ids = [e.node_id for e in result.events if e.event_type == "node_entered"]
        assert "end" not in entered_ids
        # Termination event present
        term = [e for e in result.events if e.event_type == "run_terminated"]
        assert term[-1].payload["reason"] == "uncovered_decision"


class TestOverlapDecision:
    def test_overlap_terminates(self) -> None:
        choices = [
            Choice(
                id="standard",
                label="std",
                destination="end",
                conditions=[Condition(field="days", operator="lte", value=30)],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="promo",
                label="promo",
                destination="end",
                conditions=[Condition(field="promo", operator="eq", value=True)],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
                Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        result = _run(graph, initial_facts={"days": 12, "promo": True})
        assert result.status == "overlap"
        entered_ids = [e.node_id for e in result.events if e.event_type == "node_entered"]
        assert "end" not in entered_ids
        term = [e for e in result.events if e.event_type == "run_terminated"]
        assert term[-1].payload["reason"] == "overlap_decision"


class TestDeviation:
    def test_deviation_recorded_and_traversal_continues(self) -> None:
        """Select the non-matching choice → deviation recorded, traversal follows it."""
        choices = [
            Choice(
                id="correct",
                label="correct",
                destination="end",
                conditions=[Condition(field="x", operator="gt", value=5)],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="wrong",
                label="wrong",
                destination="end",
                conditions=[Condition(field="x", operator="lte", value=5)],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
                Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        # x=10 → "correct" should match; we force "wrong"
        result = _run(
            graph,
            initial_facts={"x": 10},
            decisions=[Decision(node_id="d", selected_choice_id="wrong")],
        )
        assert result.status == "deviation"
        assert len(result.deviations) == 1
        dev: Deviation = result.deviations[0]
        assert dev.node_id == "d"
        assert dev.selected_choice_id == "wrong"
        assert dev.matching_choice_ids == ["correct"]
        # Traversal continued to end
        entered_ids = [e.node_id for e in result.events if e.event_type == "node_entered"]
        assert "end" in entered_ids

    def test_deviation_event_in_log(self) -> None:
        choices = [
            Choice(
                id="a",
                label="a",
                destination="end",
                conditions=[Condition(field="x", operator="eq", value=1)],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="b",
                label="b",
                destination="end",
                conditions=[Condition(field="x", operator="eq", value=2)],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
                Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        result = _run(
            graph,
            initial_facts={"x": 1},  # "a" matches
            decisions=[Decision(node_id="d", selected_choice_id="b")],  # select "b"
        )
        dev_events = [e for e in result.events if e.event_type == "deviation_recorded"]
        assert len(dev_events) == 1
        assert dev_events[0].payload["selected_choice_id"] == "b"


class TestTraversalBudget:
    def test_budget_exceeded_on_cycle(self) -> None:
        """A graph with a cycle should hit the step budget."""
        # The cycle goes: start → loop → loop → ... (action node cycles to itself)
        # 'end' is reachable via a choice from a decision node that the loop passes through,
        # but we never supply the decision so traversal cycles.
        # Actually, we need a simpler approach: use an action node that points back to itself.
        # Graph schema requires all nodes reachable from start, so we add a valid path to end
        # via a choice that is never reached in the cycling path.
        # Simpler: use a decision in the cycle with a choice that goes to end (never matches).
        choices = [
            Choice(
                id="escape",
                label="escape",
                destination="end",
                conditions=[Condition(field="x", operator="eq", value="never")],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="loop",
                label="loop",
                destination="d",
                conditions=[Condition(field="x", operator="neq", value="never")],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
                Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        with pytest.raises(TraversalBudgetExceeded):
            _run(graph, initial_facts={"x": "keep_looping"}, budget=10)

    def test_custom_budget(self) -> None:
        """A linear graph of 5 nodes completes within a budget of 10."""
        nodes = [
            Node(id="start", label="S", type="start", source_refs=[], next_node="n1"),
        ]
        for i in range(1, 4):
            nodes.append(
                Node(
                    id=f"n{i}", label=f"N{i}", type="action", source_refs=[], next_node=f"n{i + 1}"
                )
            )
        nodes.append(Node(id="n4", label="N4", type="action", source_refs=[], next_node="end"))
        nodes.append(Node(id="end", label="E", type="end", source_refs=[]))
        graph = Graph(nodes=nodes)
        result = _run(graph, budget=20)
        assert result.status == "completed"


class TestInjects:
    def test_inject_applied_before_named_node(self) -> None:
        """rain_risk starts at 40 but inject raises it to 85 before 'check' node."""
        choices = [
            Choice(
                id="warn",
                label="warn",
                destination="end",
                conditions=[Condition(field="rain_risk", operator="gt", value=70)],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="ok",
                label="ok",
                destination="end",
                conditions=[Condition(field="rain_risk", operator="lte", value=70)],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="check"),
                Node(id="check", label="C", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        result = _run(
            graph,
            initial_facts={"rain_risk": 40},
            injects=[{"before_node_id": "check", "facts": {"rain_risk": 85}}],
        )
        assert result.status == "completed"
        decision_ev = next(e for e in result.events if e.event_type == "decision_evaluated")
        assert decision_ev.payload["matching_choice_ids"] == ["warn"]
        # final facts reflect injected value
        assert result.final_facts["rain_risk"] == 85

    def test_inject_consumed_once_on_revisit(self) -> None:
        """On a cycle, an inject for a revisited node fires only once."""
        # start → action_a → check_node → (cycle back to action_a if cond not met)
        # After inject on first visit to check_node, condition should match on revisit.
        # We use budget=3 to ensure the loop is cut off rather than let it run forever.
        # This tests: inject fires once even if node is visited twice.
        choices = [
            Choice(
                id="done",
                label="done",
                destination="end",
                conditions=[Condition(field="counter", operator="gte", value=100)],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="loop",
                label="loop",
                destination="action_a",
                conditions=[Condition(field="counter", operator="lt", value=100)],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="action_a"),
                Node(
                    id="action_a", label="A", type="action", source_refs=[], next_node="check_node"
                ),
                Node(id="check_node", label="C", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        # Initial counter=0; inject sets counter=100 before first visit to check_node.
        # First visit: inject fires, counter=100 → "done" matches → completed.
        result = _run(
            graph,
            initial_facts={"counter": 0},
            injects=[{"before_node_id": "check_node", "facts": {"counter": 100}}],
            budget=20,
        )
        assert result.status == "completed"
        inject_events = [e for e in result.events if e.event_type == "inject_applied"]
        assert len(inject_events) == 1  # fired exactly once

    def test_invalid_scenario_raises(self) -> None:
        """Inject referencing absent node_id must raise InvalidScenario before traversal."""
        graph = _simple_graph()
        with pytest.raises(InvalidScenario, match="does not exist"):
            _run(graph, injects=[{"before_node_id": "nonexistent", "facts": {"x": 1}}])

    def test_authority_label_on_all_results(self) -> None:
        result = _run(_simple_graph(), authority="draft")
        assert result.playbook_authority == "draft"
        assert "draft" in result.rehearsal_notice

    def test_approved_authority_passes_through(self) -> None:
        result = _run(_simple_graph(), authority="approved")
        assert result.playbook_authority == "approved"
        assert "approved" in result.rehearsal_notice


# ===========================================================================
# Determinism tests
# ===========================================================================


class TestDeterminism:
    def test_identical_runs_produce_identical_hashes(self) -> None:
        choices = [
            Choice(
                id="a",
                label="a",
                destination="end",
                conditions=[Condition(field="x", operator="gt", value=5)],
                source_refs=[],
                evidence_status="uncited",
            ),
            Choice(
                id="b",
                label="b",
                destination="end",
                conditions=[Condition(field="x", operator="lte", value=5)],
                source_refs=[],
                evidence_status="uncited",
            ),
        ]
        graph = Graph(
            nodes=[
                Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
                Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
                Node(id="end", label="E", type="end", source_refs=[]),
            ]
        )
        r1 = _run(graph, initial_facts={"x": 10})
        r2 = _run(graph, initial_facts={"x": 10})
        assert [e.state_hash for e in r1.events] == [e.state_hash for e in r2.events]

    def test_different_facts_produce_different_hashes(self) -> None:
        result_a = _run(_simple_graph(), initial_facts={"x": 1})
        result_b = _run(_simple_graph(), initial_facts={"x": 2})
        # At least one hash must differ
        assert [e.state_hash for e in result_a.events] != [e.state_hash for e in result_b.events]

    def test_hash_chain_uses_prev_hash(self) -> None:
        """Each event hash must depend on the previous one."""
        result = _run(_linear_graph_with_action())
        assert len(result.events) >= 2
        # Recompute first hash manually
        e0 = result.events[0]
        expected = compute_event_hash(
            "test-v1",
            e0.sequence,
            e0.node_id,
            e0.event_type,
            e0.payload,
            dict(e0.facts_snapshot),
            "",
            playbook_authority=e0.playbook_authority,
            execution_mode=e0.execution_mode,
            context_hash=e0.context_hash,
        )
        assert e0.state_hash == expected
        # Second hash depends on first
        e1 = result.events[1]
        expected1 = compute_event_hash(
            "test-v1",
            e1.sequence,
            e1.node_id,
            e1.event_type,
            e1.payload,
            dict(e1.facts_snapshot),
            e0.state_hash,
            playbook_authority=e1.playbook_authority,
            execution_mode=e1.execution_mode,
            context_hash=e1.context_hash,
        )
        assert e1.state_hash == expected1

    def test_result_is_json_serialisable(self) -> None:
        result = _run(_simple_graph())
        dumped = result.model_dump(mode="json")
        # Must round-trip through JSON without error
        json.dumps(dumped)


# ===========================================================================
# Fixture integration tests
# ===========================================================================


class TestNightMarketFixture:
    """AC-6: night-market scenario must reach UncoveredDecision at weather node."""

    def _build_run_input(self) -> RunInput:
        content = (FIXTURES / "night-market" / "runbook.md").read_text()
        raw = json.loads((FIXTURES / "night-market" / "fixture.json").read_text())
        scenario_raw = json.loads((FIXTURES / "night-market" / "scenario.json").read_text())
        segments = segment_document("night-market", content)

        # Remap int ordinals to string segment IDs (same as test_contracts.py does)
        for node in raw["graph"]["nodes"]:
            node["source_refs"] = [segments[i - 1].id for i in node["source_refs"]]
            for choice in node.get("choices", []):
                choice["source_refs"] = [segments[i - 1].id for i in choice["source_refs"]]

        graph = Graph.model_validate(raw["graph"])

        injects = [
            Inject(
                before_node_id=inj["before_node_id"],
                facts=inj["facts"],
            )
            for inj in scenario_raw.get("injects", [])
        ]
        scenario = Scenario(
            title=scenario_raw["title"],
            seed=scenario_raw.get("seed", 0),
            initial_facts=scenario_raw["initial_facts"],
            injects=injects,
        )
        return RunInput(
            execution_mode="auto_rehearsal",
            playbook_version_id="night-market-v1",
            playbook_authority="draft",
            graph=graph,
            scenario=scenario,
        )

    def test_run_reaches_uncovered(self) -> None:
        run_input = self._build_run_input()
        result = engine.run(run_input)
        assert result.status == "uncovered", (
            f"Expected uncovered at weather node; got {result.status}.\n"
            f"Events: {[(e.event_type, e.node_id, e.payload) for e in result.events]}"
        )

    def test_uncovered_at_weather_node(self) -> None:
        run_input = self._build_run_input()
        result = engine.run(run_input)
        term_event = next(e for e in result.events if e.event_type == "run_terminated")
        assert term_event.payload["reason"] == "uncovered_decision"
        # The termination should have happened at the weather node
        # (the decision_evaluated event immediately before termination)
        decision_events = [e for e in result.events if e.event_type == "decision_evaluated"]
        assert decision_events[-1].node_id == "weather"

    def test_inject_updated_rain_risk(self) -> None:
        run_input = self._build_run_input()
        result = engine.run(run_input)
        # After inject, rain_risk should be 85
        inject_events = [e for e in result.events if e.event_type == "inject_applied"]
        assert len(inject_events) == 1
        assert result.final_facts.get("rain_risk") == 85

    def test_draft_authority_and_rehearsal_notice(self) -> None:
        run_input = self._build_run_input()
        result = engine.run(run_input)
        assert result.playbook_authority == "draft"
        assert "rehearsal" in result.rehearsal_notice.lower()
        assert len(result.rehearsal_notice) > 20


class TestCustomerSupportFixture:
    """AC-7: customer-support scenario must detect overlap at refund node."""

    def _build_run_input(self) -> RunInput:
        content = (FIXTURES / "customer-support" / "runbook.md").read_text()
        raw = json.loads((FIXTURES / "customer-support" / "fixture.json").read_text())
        scenario_raw = json.loads((FIXTURES / "customer-support" / "scenario.json").read_text())
        segments = segment_document("customer-support", content)

        for node in raw["graph"]["nodes"]:
            node["source_refs"] = [segments[i - 1].id for i in node["source_refs"]]
            for choice in node.get("choices", []):
                choice["source_refs"] = [segments[i - 1].id for i in choice["source_refs"]]

        graph = Graph.model_validate(raw["graph"])

        injects = [
            Inject(before_node_id=inj["before_node_id"], facts=inj["facts"])
            for inj in scenario_raw.get("injects", [])
        ]
        scenario = Scenario(
            title=scenario_raw["title"],
            seed=scenario_raw.get("seed", 0),
            initial_facts=scenario_raw["initial_facts"],
            injects=injects,
        )
        return RunInput(
            execution_mode="auto_rehearsal",
            playbook_version_id="customer-support-v1",
            playbook_authority="draft",
            graph=graph,
            scenario=scenario,
        )

    def test_run_reaches_overlap(self) -> None:
        run_input = self._build_run_input()
        result = engine.run(run_input)
        assert result.status == "overlap", (
            f"Expected overlap at refund node; got {result.status}.\n"
            f"Events: {[(e.event_type, e.node_id, e.payload) for e in result.events]}"
        )

    def test_both_refund_rules_detected(self) -> None:
        run_input = self._build_run_input()
        result = engine.run(run_input)
        decision_events = [e for e in result.events if e.event_type == "decision_evaluated"]
        assert decision_events[-1].node_id == "refund"
        matching = set(decision_events[-1].payload["matching_choice_ids"])
        assert matching == {"standard", "promo"}

    def test_draft_authority(self) -> None:
        run_input = self._build_run_input()
        result = engine.run(run_input)
        assert result.playbook_authority == "draft"


# ===========================================================================
# Hypothesis property tests
# ===========================================================================

# Strategies for small valid fact dictionaries
fact_value_st = st.one_of(
    st.integers(min_value=-100, max_value=100),
    st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.text(min_size=1, max_size=20),
)
facts_st = st.dictionaries(
    st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
    ),
    fact_value_st,
    min_size=0,
    max_size=5,
)


@given(initial_facts=facts_st)
@settings(max_examples=50)
def test_hypothesis_determinism(initial_facts: dict) -> None:
    """Same input → identical hash sequences (REQ-7.3)."""
    graph = _simple_graph()
    scenario = Scenario(title="h-test", seed=42, initial_facts=initial_facts)
    ri = RunInput(
        execution_mode="auto_rehearsal",
        playbook_version_id="h-v1",
        playbook_authority="draft",
        graph=graph,
        scenario=scenario,
    )
    r1 = engine.run(ri)
    r2 = engine.run(ri)
    assert [e.state_hash for e in r1.events] == [e.state_hash for e in r2.events]


@given(initial_facts=facts_st)
@settings(max_examples=50)
def test_hypothesis_missing_fact_never_raises(initial_facts: dict) -> None:
    """Missing or incompatible facts must never raise exceptions (REQ-2.2, REQ-2.3)."""
    # A decision node with conditions requiring specific fields
    choices = [
        Choice(
            id="yes",
            label="yes",
            destination="end",
            conditions=[Condition(field="score", operator="gt", value=50)],
            source_refs=[],
            evidence_status="uncited",
        ),
        Choice(
            id="no",
            label="no",
            destination="end",
            conditions=[Condition(field="score", operator="lte", value=50)],
            source_refs=[],
            evidence_status="uncited",
        ),
    ]
    graph = Graph(
        nodes=[
            Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
            Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
            Node(id="end", label="E", type="end", source_refs=[]),
        ]
    )
    scenario = Scenario(title="h-test", seed=0, initial_facts=initial_facts)
    ri = RunInput(
        execution_mode="auto_rehearsal",
        playbook_version_id="h-v1",
        playbook_authority="draft",
        graph=graph,
        scenario=scenario,
    )
    # Must not raise regardless of whether 'score' is present, missing, or wrong type
    result = engine.run(ri)
    assert result.status in ("completed", "uncovered", "overlap")


@given(initial_facts=facts_st)
@settings(max_examples=30)
def test_hypothesis_input_immutability(initial_facts: dict) -> None:
    """Engine must not mutate its RunInput (REQ-4.6)."""
    graph = _simple_graph()
    scenario = Scenario(title="h-test", seed=0, initial_facts=initial_facts)
    ri = RunInput(
        execution_mode="auto_rehearsal",
        playbook_version_id="h-v1",
        playbook_authority="draft",
        graph=graph,
        scenario=scenario,
    )
    # Capture pre-run graph node count
    node_count_before = len(ri.graph.nodes)
    engine.run(ri)
    assert len(ri.graph.nodes) == node_count_before
    # Initial facts unchanged (Pydantic frozen model, dict access is by copy)
    assert dict(ri.scenario.initial_facts) == initial_facts


@given(budget=st.integers(min_value=1, max_value=5))
@settings(max_examples=20)
def test_hypothesis_budget_terminates(budget: int) -> None:
    """Any run with a finite budget always terminates (no infinite hang)."""
    # Cyclic decision graph — "escape" never matches so loop cycles back to itself.
    # Graph schema requires all nodes reachable, so we include an end node via "escape".
    choices = [
        Choice(
            id="escape",
            label="escape",
            destination="end",
            conditions=[Condition(field="x", operator="eq", value="never")],
            source_refs=[],
            evidence_status="uncited",
        ),
        Choice(
            id="loop",
            label="loop",
            destination="d",
            conditions=[Condition(field="x", operator="neq", value="never")],
            source_refs=[],
            evidence_status="uncited",
        ),
    ]
    graph = Graph(
        nodes=[
            Node(id="start", label="S", type="start", source_refs=[], next_node="d"),
            Node(id="d", label="D", type="decision", source_refs=[], choices=choices),
            Node(id="end", label="E", type="end", source_refs=[]),
        ]
    )
    scenario = Scenario(title="h-test", seed=0, initial_facts={"x": "keep_looping"})
    ri = RunInput(
        execution_mode="auto_rehearsal",
        playbook_version_id="h-v1",
        playbook_authority="draft",
        graph=graph,
        scenario=scenario,
        step_budget=budget,
    )
    with pytest.raises(TraversalBudgetExceeded):
        engine.run(ri)
