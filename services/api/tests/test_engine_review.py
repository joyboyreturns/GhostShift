"""Codex-authored review regressions; no additional Kiro model calls were used."""

import copy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.engine.interfaces import (
    Decision,
    Inject,
    InvalidDecision,
    RunInput,
    RunResult,
    Scenario,
    TraversalBudgetExceeded,
    compute_event_hash,
)
from app.engine.interpreter import GhostShiftEngine
from app.schemas.graph import Choice, Graph, Node


def choice(id: str, destination: str, field: str, operator: str, value: int, ref: str) -> Choice:
    return Choice.model_validate(
        {
            "id": id,
            "label": id,
            "destination": destination,
            "conditions": [{"field": field, "operator": operator, "value": value}],
            "source_refs": [ref],
            "evidence_status": "cited",
        }
    )


def request() -> RunInput:
    return RunInput(
        playbook_version_id="review-v1",
        playbook_authority="draft",
        scenario=Scenario(title="Review", initial_facts={"x": 5}),
        graph=Graph(
            nodes=[
                Node(id="s", label="Start", type="start", next_node="d"),
                Node(
                    id="d",
                    label="Decide",
                    type="decision",
                    source_refs=["segment-1"],
                    choices=[
                        choice("high", "e", "x", "gt", 0, "segment-1"),
                        choice("low", "e", "x", "lt", 0, "segment-1"),
                    ],
                ),
                Node(id="e", label="End", type="end"),
            ]
        ),
    )


def test_interactive_run_requires_a_choice() -> None:
    result = GhostShiftEngine().run(request())
    assert result.status == "awaiting_decision"
    assert result.checkpoint is not None
    assert result.checkpoint.node_id == "d"
    assert result.checkpoint.matching_choice_ids == ["high"]
    assert result.decisions_made == []
    assert not any(event.event_type == "decision_selected" for event in result.events)


@pytest.mark.parametrize("automatic", [False, True])
def test_recorded_decisions_reproduce_the_same_history(automatic: bool) -> None:
    original = request().model_copy(
        update={
            "execution_mode": "auto_rehearsal" if automatic else "interactive",
            "decisions": [] if automatic else [Decision(node_id="d", selected_choice_id="low")],
        }
    )
    result = GhostShiftEngine().run(original)
    assert [decision.node_id for decision in result.decisions_made] == ["d"]
    replay = GhostShiftEngine().run(
        original.model_copy(update={"decisions": result.decisions_made})
    )
    assert replay.events == result.events
    assert replay.status == result.status
    assert result.status == ("completed" if automatic else "deviation")


def test_serialized_snapshot_contains_injects_and_can_be_reused() -> None:
    original = request().model_copy(
        update={
            "scenario": Scenario(
                title="Injected",
                seed=42,
                initial_facts={"x": -1},
                injects=[Inject(before_node_id="d", facts={"x": 5})],
            ),
            "decisions": [Decision(node_id="d", selected_choice_id="low")],
        }
    )
    result = GhostShiftEngine().run(original)
    restored = RunResult.model_validate_json(result.model_dump_json())
    assert restored.input_snapshot.scenario.initial_facts == {"x": -1}
    assert restored.input_snapshot.scenario.injects[0].facts == {"x": 5}
    assert GhostShiftEngine().run(restored.input_snapshot) == result
    restored.input_snapshot.scenario.initial_facts["x"] = 999
    assert original.scenario.initial_facts == {"x": -1}
    assert result.input_snapshot.scenario.initial_facts == {"x": -1}


@pytest.mark.parametrize(
    "decision",
    [
        Decision(node_id="absent", selected_choice_id="high"),
        Decision(node_id="s", selected_choice_id="high"),
        Decision(node_id="d", selected_choice_id="absent"),
        Decision(node_id="d", selected_choice_id="high", selection_origin="automatic_rehearsal"),
    ],
)
def test_invalid_decisions_are_not_silently_ignored(decision: Decision) -> None:
    with pytest.raises(InvalidDecision):
        GhostShiftEngine().run(request().model_copy(update={"decisions": [decision]}))


def test_extra_decisions_after_completion_are_rejected() -> None:
    decisions = [Decision(node_id="d", selected_choice_id="high")] * 2
    with pytest.raises(InvalidDecision, match="unused"):
        GhostShiftEngine().run(request().model_copy(update={"decisions": decisions}))


def test_out_of_order_decision_stream_is_rejected() -> None:
    original = request().model_copy(deep=True)
    second = original.graph.nodes[1].model_copy(deep=True, update={"id": "d2"})
    original.graph.nodes.insert(2, second)
    for candidate in original.graph.nodes[1].choices:
        candidate.destination = "d2"
    original = original.model_copy(
        update={
            "decisions": [
                Decision(node_id="d2", selected_choice_id="high"),
                Decision(node_id="d", selected_choice_id="high"),
            ]
        }
    )
    with pytest.raises(InvalidDecision, match="Expected a decision"):
        GhostShiftEngine().run(original)


def test_same_node_injects_keep_declared_order() -> None:
    original = request().model_copy(
        update={
            "scenario": Scenario(
                title="Ordered injects",
                initial_facts={"x": 0},
                injects=[
                    Inject(before_node_id="d", facts={"x": -1}),
                    Inject(before_node_id="d", facts={"x": 2}),
                ],
            )
        }
    )
    first = GhostShiftEngine().run(original)
    reversed_input = original.model_copy(
        update={
            "scenario": original.scenario.model_copy(
                update={"injects": list(reversed(original.scenario.injects))}
            )
        }
    )
    second = GhostShiftEngine().run(reversed_input)
    assert first.checkpoint is not None and first.checkpoint.matching_choice_ids == ["high"]
    assert second.checkpoint is not None and second.checkpoint.matching_choice_ids == ["low"]
    assert [
        event.payload["inject_index"]
        for event in first.events
        if event.event_type == "inject_applied"
    ] == [0, 1]
    assert first.final_facts == {"x": 2} and second.final_facts == {"x": -1}


@pytest.mark.parametrize(
    "facts, diagnostic", [({}, "missing_fact"), ({"x": "bad"}, "type_mismatch")]
)
def test_missing_and_incompatible_facts_remain_inspectable(facts: dict, diagnostic: str) -> None:
    original = request().model_copy(
        update={"scenario": Scenario(title="Review", initial_facts=facts)}
    )
    result = GhostShiftEngine().run(original)
    assert result.status == "uncovered" and result.checkpoint is not None
    assert all(
        out.condition_outcomes[0].model_dump()[diagnostic]
        for out in result.checkpoint.choice_outcomes
    )
    evaluated = next(event for event in result.events if event.event_type == "decision_evaluated")
    assert all(
        out["condition_outcomes"][0][diagnostic] for out in evaluated.payload["choice_outcomes"]
    )
    assert evaluated.payload["node_source_refs"] == ["segment-1"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_facts_are_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        Scenario(title="Nonfinite", initial_facts={"x": value})
    with pytest.raises(ValidationError):
        Inject(before_node_id="d", facts={"x": value})
    with pytest.raises(ValueError):
        compute_event_hash(
            "v",
            0,
            "d",
            "node_entered",
            {},
            {"x": value},
            "",
            playbook_authority="draft",
            execution_mode="interactive",
            context_hash="context",
        )


def test_authority_and_graph_context_are_bound_into_every_event() -> None:
    original = request().model_copy(
        update={"decisions": [Decision(node_id="d", selected_choice_id="high")]}
    )
    draft = GhostShiftEngine().run(original)
    approved = GhostShiftEngine().run(
        original.model_copy(update={"playbook_authority": "approved"})
    )
    changed_graph = original.graph.model_copy(deep=True)
    changed_graph.nodes[1].choices[0].conditions[0].value = 1
    revised = GhostShiftEngine().run(original.model_copy(update={"graph": changed_graph}))
    assert draft.events[0].state_hash != approved.events[0].state_hash
    assert draft.events[0].state_hash != revised.events[0].state_hash
    for event in draft.events:
        assert event.playbook_version_id == "review-v1"
        assert event.playbook_authority == "draft"
        assert event.execution_mode == "interactive"
        assert len(event.context_hash) == 64


@pytest.mark.parametrize("overlap", [False, True])
def test_unresolved_decision_never_executes_a_supplied_choice(overlap: bool) -> None:
    original = request().model_copy(deep=True)
    if overlap:
        original.graph.nodes[1].choices[1].conditions[0].operator = "gte"
    else:
        original.scenario.initial_facts["x"] = 0
    original = original.model_copy(
        update={"decisions": [Decision(node_id="d", selected_choice_id="high")]}
    )
    result = GhostShiftEngine().run(original)
    assert result.status == ("overlap" if overlap else "uncovered")
    assert result.decisions_made == [] and result.remaining_decisions == original.decisions
    assert not any(event.node_id == "e" for event in result.events)


def test_cycle_inject_runs_once_and_budget_exposes_partial_history() -> None:
    original = request().model_copy(deep=True)
    original.graph.nodes[1].choices[0].destination = "d"
    original = original.model_copy(
        update={
            "execution_mode": "auto_rehearsal",
            "step_budget": 6,
            "scenario": Scenario(
                title="Cycle",
                initial_facts={"x": 5},
                injects=[Inject(before_node_id="d", facts={"x": 6})],
            ),
        }
    )
    with pytest.raises(TraversalBudgetExceeded) as caught:
        GhostShiftEngine().run(original)
    partial = caught.value.partial_result
    assert partial is not None and partial.status == "budget_exceeded"
    assert len([event for event in partial.events if event.event_type == "inject_applied"]) == 1
    assert len([event for event in partial.events if event.event_type == "decision_evaluated"]) > 1
    assert partial.events[-1].event_type == "run_terminated" and partial.final_facts == {"x": 6}


@st.composite
def small_runs(draw: st.DrawFn) -> RunInput:
    """Vary valid branch topology, predicates, facts, injects and choice streams."""
    size = draw(st.integers(min_value=1, max_value=4))
    thresholds = draw(st.lists(st.integers(-20, 20), min_size=size, max_size=size))
    values = draw(st.lists(st.integers(-20, 20), min_size=size, max_size=size))
    high_choices = draw(st.lists(st.booleans(), min_size=size, max_size=size))
    inject_flags = draw(st.lists(st.booleans(), min_size=size, max_size=size))
    nodes = [Node(id="start", label="Start", type="start", next_node="d0")]
    facts, injects, decisions = {}, [], []
    for index in range(size):
        field, ref = f"score_{index}", f"segment-{index}"
        facts[field] = values[index]
        next_node = f"d{index + 1}" if index + 1 < size else "end"
        nodes.append(
            Node(
                id=f"d{index}",
                label=f"Decision {index}",
                type="decision",
                source_refs=[ref],
                choices=[
                    choice("high", f"high{index}", field, "gte", thresholds[index], ref),
                    choice("low", f"low{index}", field, "lt", thresholds[index], ref),
                ],
            )
        )
        nodes.extend(
            Node(
                id=f"{branch}{index}",
                label=branch,
                type="action",
                source_refs=[ref],
                next_node=next_node,
            )
            for branch in ("high", "low")
        )
        if inject_flags[index]:
            injects.append(Inject(before_node_id=f"d{index}", facts={field: values[index] + 1}))
        decisions.append(
            Decision(
                node_id=f"d{index}", selected_choice_id="high" if high_choices[index] else "low"
            )
        )
    nodes.append(Node(id="end", label="End", type="end"))
    graph = Graph(nodes=nodes)
    graph.validate_references({f"segment-{index}" for index in range(size)})
    return RunInput(
        playbook_version_id="generated-v1",
        playbook_authority="draft",
        graph=graph,
        scenario=Scenario(title="Generated", initial_facts=facts, injects=injects),
        decisions=decisions,
    )


@given(original=small_runs())
@settings(max_examples=60)
def test_generated_graphs_replay_decisions_and_preserve_evidence(original: RunInput) -> None:
    before = copy.deepcopy(original.model_dump())
    result = GhostShiftEngine().run(original)
    expected_deviations, effective_facts = 0, dict(original.scenario.initial_facts)
    for index, decision in enumerate(original.decisions):
        for inject in original.scenario.injects:
            if inject.before_node_id == decision.node_id:
                effective_facts.update(inject.facts)
        node = next(node for node in original.graph.nodes if node.id == decision.node_id)
        threshold = node.choices[0].conditions[0].value
        expected = "high" if effective_facts[f"score_{index}"] >= threshold else "low"
        expected_deviations += decision.selected_choice_id != expected
    assert len(result.deviations) == expected_deviations
    assert result.status == ("deviation" if expected_deviations else "completed")
    assert original.model_dump() == before
    replay = GhostShiftEngine().run(
        original.model_copy(update={"decisions": result.decisions_made})
    )
    assert replay.events == result.events
    for event in result.events:
        if event.event_type == "decision_evaluated":
            node = next(node for node in original.graph.nodes if node.id == event.node_id)
            assert event.payload["node_source_refs"] == node.source_refs
            for outcome, candidate in zip(
                event.payload["choice_outcomes"], node.choices, strict=True
            ):
                assert outcome["source_refs"] == candidate.source_refs
                assert outcome["evidence_status"] == candidate.evidence_status


@given(original=small_runs())
@settings(max_examples=60)
def test_generated_alternate_runs_do_not_mutate_parents(original: RunInput) -> None:
    parent = GhostShiftEngine().run(original)
    before = parent.model_dump_json()
    decisions = [decision.model_copy(deep=True) for decision in original.decisions]
    decisions[0] = decisions[0].model_copy(
        update={
            "selected_choice_id": "low" if decisions[0].selected_choice_id == "high" else "high"
        }
    )
    alternate = GhostShiftEngine().run(original.model_copy(update={"decisions": decisions}))
    first_selection = next(
        index
        for index, event in enumerate(parent.events)
        if event.event_type == "decision_selected"
    )
    assert alternate.events[:first_selection] == parent.events[:first_selection]
    assert alternate.events[first_selection].state_hash != parent.events[first_selection].state_hash
    alternate.final_facts["changed_only_in_alternate"] = True
    assert parent.model_dump_json() == before
    assert "changed_only_in_alternate" not in original.scenario.initial_facts
