"""Deterministic graph traversal interpreter for GhostShift.

Initial implementation and specification: Kiro, session 2026-11-03.
Codex review corrections: explicit checkpoints, validated choice streams, owned snapshots,
finite canonical hashing, full event diagnostics/authority, and replayable recorded decisions.
See docs/ENGINE_REVIEW.md for the review findings and attribution.

Persistence, approval, session concurrency, and fork APIs belong to subsequent milestones.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from copy import deepcopy

from pydantic import JsonValue

from app.engine.interfaces import (
    _REHEARSAL_NOTICE,
    Decision,
    DecisionEvaluation,
    Deviation,
    EventType,
    Facts,
    InvalidDecision,
    InvalidScenario,
    LogicalEvent,
    RunInput,
    RunResult,
    RunStatus,
    TraversalBudgetExceeded,
    compute_event_hash,
)
from app.engine.predicates import evaluate_decision_node
from app.schemas.graph import Node


class GhostShiftEngine:
    """Pure interpreter. Interactive runs pause until a caller supplies a choice.

    Automatic traversal of matching choices is available only through the explicit
    auto_rehearsal mode. Neither mode establishes policy authority or approves inputs.
    """

    def run(self, input: RunInput) -> RunResult:
        # Revalidate nested mutable models and own the entire input before traversal.
        snapshot = RunInput.model_validate(input.model_dump())
        node_map = {node.id: node for node in snapshot.graph.nodes}
        _validate_scenario(snapshot, node_map)
        context = snapshot.model_dump(mode="json", exclude={"decisions", "step_budget"})
        context_hash = hashlib.sha256(
            json.dumps(context, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        facts: Facts = dict(snapshot.scenario.initial_facts)
        events: list[LogicalEvent] = []
        deviations: list[Deviation] = []
        decisions_made: list[Decision] = []
        decision_queue = deque(snapshot.decisions)
        consumed_injects: set[int] = set()
        current_id = next(node.id for node in snapshot.graph.nodes if node.type == "start")
        prev_hash = ""
        step = 0

        def record(event_type: EventType, payload: dict[str, JsonValue]) -> None:
            nonlocal prev_hash
            event = LogicalEvent(
                playbook_version_id=snapshot.playbook_version_id,
                playbook_authority=snapshot.playbook_authority,
                execution_mode=snapshot.execution_mode,
                context_hash=context_hash,
                sequence=len(events),
                event_type=event_type,
                node_id=current_id,
                payload=deepcopy(payload),
                facts_snapshot=dict(facts),
                state_hash=compute_event_hash(
                    snapshot.playbook_version_id,
                    len(events),
                    current_id,
                    event_type,
                    payload,
                    facts,
                    prev_hash,
                    playbook_authority=snapshot.playbook_authority,
                    execution_mode=snapshot.execution_mode,
                    context_hash=context_hash,
                ),
            )
            events.append(event)
            prev_hash = event.state_hash

        def finish(
            status: RunStatus, reason: str, checkpoint: DecisionEvaluation | None = None
        ) -> RunResult:
            record("run_terminated", {"reason": reason, "status": status})
            return RunResult(
                input_snapshot=snapshot.model_copy(deep=True),
                playbook_version_id=snapshot.playbook_version_id,
                playbook_authority=snapshot.playbook_authority,
                scenario_title=snapshot.scenario.title,
                scenario_seed=snapshot.scenario.seed,
                status=status,
                events=events,
                deviations=deviations,
                final_facts=dict(facts),
                decisions_made=decisions_made,
                remaining_decisions=[decision.model_copy(deep=True) for decision in decision_queue],
                checkpoint=checkpoint,
                rehearsal_notice=_REHEARSAL_NOTICE.format(authority=snapshot.playbook_authority),
            )

        while True:
            if step >= snapshot.step_budget:
                partial = finish("budget_exceeded", "budget_exceeded")
                raise TraversalBudgetExceeded(
                    f"Traversal exceeded budget of {snapshot.step_budget} steps at {current_id!r}",
                    partial_result=partial,
                )
            step += 1

            for index, inject in enumerate(snapshot.scenario.injects):
                if index not in consumed_injects and inject.before_node_id == current_id:
                    consumed_injects.add(index)
                    facts = {**facts, **inject.facts}
                    record(
                        "inject_applied",
                        {
                            "inject_index": index,
                            "injected_keys": [key for key in sorted(inject.facts)],
                        },
                    )

            node = node_map[current_id]
            record("node_entered", {"node_type": node.type, "source_refs": list(node.source_refs)})
            if node.type == "end":
                if decision_queue:
                    raise InvalidDecision(
                        "Decision stream contains unused choices after the end node"
                    )
                return finish("deviation" if deviations else "completed", "end_node_reached")
            if node.type in {"start", "action"}:
                assert node.next_node is not None
                current_id = node.next_node
                continue

            evaluation = evaluate_decision_node(node, facts)
            record("decision_evaluated", evaluation.model_dump(mode="json"))
            if evaluation.result == "uncovered":
                # A caller selection cannot authorize traversal through an unresolved policy gap.
                return finish("uncovered", "uncovered_decision", evaluation)
            if evaluation.result == "overlap":
                return finish("overlap", "overlap_decision", evaluation)

            matched_id = evaluation.matching_choice_ids[0]
            if decision_queue and decision_queue[0].node_id != current_id:
                raise InvalidDecision(
                    f"Expected a decision for {current_id!r}, got {decision_queue[0].node_id!r}"
                )
            caller = decision_queue[0] if decision_queue else None
            if (caller is not None and caller.selected_choice_id is None) or (
                caller is None and snapshot.execution_mode == "interactive"
            ):
                return finish("awaiting_decision", "awaiting_decision", evaluation)

            if caller is not None:
                decision_queue.popleft()
                selected_id = caller.selected_choice_id
                assert selected_id is not None
                origin = caller.selection_origin
            else:
                selected_id = matched_id
                origin = "automatic_rehearsal"
            chosen = next(choice for choice in node.choices if choice.id == selected_id)
            selection = Decision(
                node_id=current_id, selected_choice_id=selected_id, selection_origin=origin
            )
            decisions_made.append(selection)
            record(
                "decision_selected",
                {
                    "selected_choice_id": selected_id,
                    "selection_origin": origin,
                    "source_refs": list(chosen.source_refs),
                    "evidence_status": chosen.evidence_status,
                },
            )
            if selected_id != matched_id:
                deviation = Deviation(
                    node_id=current_id,
                    selected_choice_id=selected_id,
                    matching_choice_ids=[matched_id],
                    node_source_refs=list(node.source_refs),
                    selected_choice_source_refs=list(chosen.source_refs),
                    selected_choice_evidence_status=chosen.evidence_status,
                )
                deviations.append(deviation)
                record("deviation_recorded", deviation.model_dump(mode="json"))
            current_id = chosen.destination


def _validate_scenario(input: RunInput, node_map: dict[str, Node]) -> None:
    for index, inject in enumerate(input.scenario.injects):
        if inject.before_node_id not in node_map:
            raise InvalidScenario(
                f"Inject #{index} references node {inject.before_node_id!r} which does not exist"
            )
    for decision in input.decisions:
        node = node_map.get(decision.node_id)
        if node is None or node.type != "decision":
            raise InvalidDecision(f"Unknown decision node {decision.node_id!r}")
        if decision.selected_choice_id is not None and decision.selected_choice_id not in {
            choice.id for choice in node.choices
        }:
            raise InvalidDecision(
                f"Unknown choice {decision.selected_choice_id!r} on node {node.id!r}"
            )
        if (
            decision.selection_origin == "automatic_rehearsal"
            and input.execution_mode != "auto_rehearsal"
        ):
            raise InvalidDecision("Automatic choices require explicit auto_rehearsal mode")
