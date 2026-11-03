"""Codex persistence integration around the existing Kiro/Codex engine.

Engine pause termination markers are response checkpoints, not durable terminal events.
Omitting only that marker gives an append-only prefix when a real user choice arrives.
All real terminal events (gaps, overlap, end, budget) remain in the ledger.
"""

from itertools import takewhile

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.engine.interfaces import (
    Decision,
    DecisionEvaluation,
    EngineError,
    Inject,
    LogicalEvent,
    RunInput,
    RunResult,
    TraversalBudgetExceeded,
)
from app.engine.interfaces import (
    Scenario as EngineScenario,
)
from app.engine.interpreter import GhostShiftEngine
from app.models.entities import (
    Document,
    PlaybookVersion,
    RuleProposal,
    Scenario,
    SessionEvent,
    SimulationSession,
    SourceSegment,
)
from app.schemas.api import PlaybookInput
from app.schemas.graph import Graph
from app.schemas.policy import ProposalInput, ProposalOutput
from app.schemas.simulation import (
    ChoiceInput,
    ComparisonOutput,
    EventOutput,
    ForkInput,
    ReplayOutput,
    ReportDecision,
    ReportEvidence,
    ReportFinding,
    ScenarioOutput,
    SessionCreate,
    SessionOutput,
    SessionReport,
)
from app.services.playbooks import create_playbook, graph_hash, review_output

ENGINE_VERSION = "ghostshift-engine-1"


def require_scenario(db: Session, scenario_id: str) -> Scenario:
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(404, "Scenario not found")
    return scenario


def scenario_output(scenario: Scenario) -> ScenarioOutput:
    return ScenarioOutput(
        id=scenario.id,
        playbook_version_id=scenario.playbook_version_id,
        title=scenario.title,
        description=scenario.description,
        initial_facts=scenario.initial_facts_json,
        injects=[Inject.model_validate(inject) for inject in scenario.injects_json],
        seed=scenario.seed,
        fictional=scenario.fictional,
    )


def require_session(db: Session, session_id: str) -> SimulationSession:
    row = db.get(SimulationSession, session_id)
    if row is None:
        raise HTTPException(404, "Session not found")
    if row.engine_version != ENGINE_VERSION:
        raise HTTPException(409, "This session requires an older engine; its history is preserved")
    return row


def _execute(request: RunInput) -> RunResult:
    try:
        return GhostShiftEngine().run(request)
    except TraversalBudgetExceeded as exc:
        if exc.partial_result is not None:
            return exc.partial_result
        raise HTTPException(422, "Traversal budget exhausted") from exc
    except EngineError as exc:
        raise HTTPException(422, str(exc)) from exc


def _durable(result: RunResult) -> list[LogicalEvent]:
    return result.events[:-1] if result.status == "awaiting_decision" else result.events


def _state(row: SimulationSession) -> RunResult:
    try:
        return RunResult.model_validate(row.state_json)
    except ValidationError as exc:
        raise HTTPException(409, "Stored run state is invalid; history was preserved") from exc


def _events(db: Session, session_id: str) -> list[SessionEvent]:
    return list(
        db.scalars(
            select(SessionEvent)
            .where(
                SessionEvent.session_id == session_id,
            )
            .order_by(SessionEvent.sequence_number)
        )
    )


def _verified(db: Session, row: SimulationSession) -> tuple[RunResult, list[SessionEvent]]:
    stored = _state(row)
    reproduced = _execute(stored.input_snapshot)
    if (
        reproduced != stored
        or row.status != stored.status
        or row.playbook_version_id != stored.playbook_version_id
        or row.current_node_id != _node(stored)
    ):
        raise HTTPException(409, "Replay differs from the stored state; history was preserved")
    events = _events(db, row.id)
    expected = _durable(reproduced)
    if len(events) != len(expected):
        raise HTTPException(409, "Stored event history is incomplete; history was preserved")
    for event, logical in zip(events, expected, strict=True):
        if (
            event.sequence_number != logical.sequence
            or event.event_type != logical.event_type
            or event.state_hash != logical.state_hash
            or event.payload_json != logical.model_dump(mode="json")
        ):
            raise HTTPException(
                409, "Stored event history failed verification; history was preserved"
            )
    return stored, events


def _append(db: Session, session_id: str, events: list[LogicalEvent]) -> None:
    db.add_all(
        SessionEvent(
            session_id=session_id,
            sequence_number=event.sequence,
            event_type=event.event_type,
            payload_json=event.model_dump(mode="json"),
            state_hash=event.state_hash,
        )
        for event in events
    )


def _node(result: RunResult) -> str:
    return result.checkpoint.node_id if result.checkpoint else result.events[-1].node_id


def _commit(db: Session) -> None:
    db.commit()


def _new_session(
    db: Session,
    scenario_id: str,
    document_id: str,
    result: RunResult,
    parent_session_id: str | None = None,
    fork_event_index: int | None = None,
) -> SessionOutput:
    row = SimulationSession(
        scenario_id=scenario_id,
        playbook_version_id=result.playbook_version_id,
        document_id=document_id,
        engine_version=ENGINE_VERSION,
        parent_session_id=parent_session_id,
        fork_event_index=fork_event_index,
        revision=0,
        status=result.status,
        current_node_id=_node(result),
        state_json=result.model_dump(mode="json"),
    )
    db.add(row)
    db.flush()
    _append(db, row.id, _durable(result))
    _commit(db)
    return session_output(db, row.id)


def create_session(db: Session, data: SessionCreate) -> SessionOutput:
    scenario = require_scenario(db, data.scenario_id)
    playbook = db.get(PlaybookVersion, data.playbook_version_id or scenario.playbook_version_id)
    if playbook is None:
        raise HTTPException(409, "Scenario playbook is missing")
    ancestor: PlaybookVersion | None = playbook
    seen: set[str] = set()
    while ancestor is not None and ancestor.id != scenario.playbook_version_id:
        if ancestor.id in seen:
            raise HTTPException(409, "Playbook lineage contains a cycle")
        seen.add(ancestor.id)
        ancestor = (
            db.get(PlaybookVersion, ancestor.parent_version_id)
            if ancestor.parent_version_id
            else None
        )
    if ancestor is None:
        raise HTTPException(422, "This version is not a revision of the scenario's playbook")
    if playbook.status == "approved":
        approval = review_output(db, playbook.id)
        if approval is None or approval.graph_hash != graph_hash(playbook):
            raise HTTPException(
                409, "The approved model's review record is missing or inconsistent"
            )
    if playbook.status == "draft" and not data.allow_draft_rehearsal:
        raise HTTPException(
            409, "This playbook is unapproved. Explicitly allow a draft model rehearsal."
        )
    try:
        graph = Graph.model_validate(playbook.graph_json)
    except ValidationError as exc:
        raise HTTPException(409, "The stored playbook is invalid; create a valid revision") from exc
    refs = set(
        db.scalars(
            select(SourceSegment.id).where(SourceSegment.document_id == playbook.document_id)
        )
    )
    try:
        graph.validate_references(refs)
    except ValueError as exc:
        raise HTTPException(409, "The playbook has invalid evidence references") from exc
    if any(
        inject["before_node_id"] not in {node.id for node in graph.nodes}
        for inject in scenario.injects_json
    ):
        raise HTTPException(422, "The revised graph removed a scheduled scenario checkpoint")
    result = _execute(
        RunInput(
            playbook_version_id=playbook.id,
            playbook_authority=playbook.status,
            graph=graph,
            execution_mode="interactive",
            scenario=EngineScenario(
                title=scenario.title,
                seed=scenario.seed,
                initial_facts=scenario.initial_facts_json,
                injects=[Inject.model_validate(inject) for inject in scenario.injects_json],
            ),
        )
    )
    return _new_session(db, scenario.id, playbook.document_id, result)


def session_output(db: Session, session_id: str) -> SessionOutput:
    row = require_session(db, session_id)
    result, events = _verified(db, row)
    return SessionOutput(
        id=row.id,
        scenario_id=row.scenario_id,
        playbook_version_id=row.playbook_version_id,
        document_id=row.document_id,
        parent_session_id=row.parent_session_id,
        fork_event_index=row.fork_event_index,
        engine_version=row.engine_version,
        revision=row.revision,
        status=row.status,
        current_node_id=row.current_node_id,
        created_at=row.created_at,
        result=result,
        proposal_id=db.scalar(
            select(RuleProposal.id).where(
                RuleProposal.proposed_playbook_version_id == row.playbook_version_id
            )
        ),
        events=[
            EventOutput(**event.payload_json, id=event.id, created_at=event.created_at)
            for event in events
        ],
    )


def choose(db: Session, session_id: str, data: ChoiceInput) -> SessionOutput:
    row = require_session(db, session_id)
    if row.revision != data.expected_revision:
        raise HTTPException(
            409, "This run changed elsewhere. Reload before submitting another choice."
        )
    previous, events = _verified(db, row)
    if row.status != "awaiting_decision" or previous.checkpoint is None:
        raise HTTPException(
            409, "This run is stopped. Fork an earlier decision to try another action."
        )
    decision = Decision(node_id=previous.checkpoint.node_id, selected_choice_id=data.choice_id)
    request = previous.input_snapshot.model_copy(
        deep=True,
        update={
            "decisions": [*previous.decisions_made, decision],
        },
    )
    result = _execute(request)
    durable = _durable(result)
    prefix = [event.payload_json for event in events]
    if [event.model_dump(mode="json") for event in durable[: len(prefix)]] != prefix:
        raise HTTPException(409, "The new run does not preserve its history; no choice was saved")
    claimed = db.execute(
        update(SimulationSession)
        .where(
            SimulationSession.id == session_id,
            SimulationSession.revision == data.expected_revision,
        )
        .values(
            revision=data.expected_revision + 1,
            status=result.status,
            current_node_id=_node(result),
            state_json=result.model_dump(mode="json"),
        )
        .returning(SimulationSession.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if claimed is None:
        db.rollback()
        raise HTTPException(
            409, "This run changed elsewhere. Reload before submitting another choice."
        )
    _append(db, session_id, durable[len(prefix) :])
    _commit(db)
    db.expire_all()
    return session_output(db, session_id)


def replay(db: Session, session_id: str) -> ReplayOutput:
    row = require_session(db, session_id)
    _, events = _verified(db, row)
    return ReplayOutput(
        session_id=row.id,
        event_count=len(events),
        last_state_hash=events[-1].state_hash,
        engine_version=row.engine_version,
    )


def fork(db: Session, session_id: str, data: ForkInput) -> SessionOutput:
    parent = require_session(db, session_id)
    previous, events = _verified(db, parent)
    if (
        data.event_index >= len(events)
        or events[data.event_index].event_type != "decision_evaluated"
    ):
        raise HTTPException(422, "Fork from an existing decision-evaluated checkpoint")
    decisions = [
        Decision.model_validate(
            {
                "node_id": event.payload_json["node_id"],
                "selected_choice_id": event.payload_json["payload"]["selected_choice_id"],
                "selection_origin": event.payload_json["payload"]["selection_origin"],
            }
        )
        for event in events[: data.event_index]
        if event.event_type == "decision_selected"
    ]
    request = previous.input_snapshot.model_copy(deep=True, update={"decisions": decisions})
    result = _execute(request)
    if (
        result.checkpoint is None
        or result.checkpoint.node_id != events[data.event_index].payload_json["node_id"]
        or [event.model_dump(mode="json") for event in _durable(result)[: data.event_index + 1]]
        != [event.payload_json for event in events[: data.event_index + 1]]
    ):
        raise HTTPException(409, "The fork checkpoint could not be reproduced")
    return _new_session(
        db,
        parent.scenario_id,
        parent.document_id,
        result,
        parent_session_id=parent.id,
        fork_event_index=data.event_index,
    )


def report(db: Session, session_id: str) -> SessionReport:
    session = session_output(db, session_id)
    result = session.result
    nodes = {node.id: node for node in result.input_snapshot.graph.nodes}
    decisions = []
    # Events disambiguate repeated visits to the same decision node in a cyclic graph.
    evaluations: dict[str, list[str]] = {}
    for event in session.events:
        if event.event_type == "decision_evaluated":
            evaluations[event.node_id] = DecisionEvaluation.model_validate(
                event.payload
            ).matching_choice_ids
        elif event.event_type == "decision_selected":
            node = nodes[event.node_id]
            choice_id = event.payload["selected_choice_id"]
            selected = next(choice for choice in node.choices if choice.id == choice_id)
            deviated = selected.id not in evaluations[node.id]
            decisions.append(
                ReportDecision(
                    node_id=node.id,
                    node_label=node.label,
                    choice_id=selected.id,
                    choice_label=selected.label,
                    outcome="deviation" if deviated else "modeled_match",
                    source_refs=list(selected.source_refs),
                    evidence_status=selected.evidence_status,
                    reviewed_support=(
                        not deviated
                        and result.playbook_authority == "approved"
                        and selected.evidence_status == "cited"
                    ),
                )
            )
    findings = []
    if result.checkpoint is not None and result.status in {"uncovered", "overlap"}:
        checkpoint = result.checkpoint
        findings.append(
            ReportFinding(
                kind="uncovered" if result.status == "uncovered" else "overlap",
                node_id=checkpoint.node_id,
                node_label=nodes[checkpoint.node_id].label,
                matching_choice_ids=checkpoint.matching_choice_ids,
                source_refs=checkpoint.node_source_refs,
                missing_conditions=sum(
                    condition.missing_fact
                    for choice in checkpoint.choice_outcomes
                    for condition in choice.condition_outcomes
                ),
                incompatible_conditions=sum(
                    condition.type_mismatch
                    for choice in checkpoint.choice_outcomes
                    for condition in choice.condition_outcomes
                ),
            )
        )
    document = db.get(Document, session.document_id)
    if document is None:
        raise HTTPException(409, "The pinned source is missing")
    cited_refs = {
        reference
        for node in result.input_snapshot.graph.nodes
        for reference in [
            *node.source_refs,
            *(reference for choice in node.choices for reference in choice.source_refs),
        ]
    }
    approval = (
        review_output(db, session.playbook_version_id)
        if result.playbook_authority == "approved"
        else None
    )
    if result.playbook_authority == "approved" and approval is None:
        raise HTTPException(409, "The pinned approval record is missing; history was preserved")
    return SessionReport(
        approval=approval,
        original_file_hash=document.original_file_hash,
        source_title=document.title,
        source_content_hash=document.content_hash,
        evidence=[
            ReportEvidence(
                id=segment.id,
                ordinal=segment.ordinal,
                text=segment.text,
                start_offset=segment.start_offset,
                end_offset=segment.end_offset,
                page_number=segment.page_number,
            )
            for segment in db.scalars(
                select(SourceSegment)
                .where(SourceSegment.document_id == document.id, SourceSegment.id.in_(cited_refs))
                .order_by(SourceSegment.ordinal)
            )
        ],
        replay_input=result.input_snapshot,
        logical_events=[
            LogicalEvent.model_validate(event.payload_json) for event in _events(db, session.id)
        ],
        final_facts=result.final_facts,
        session_id=session.id,
        parent_session_id=session.parent_session_id,
        scenario_id=session.scenario_id,
        scenario_title=result.scenario_title,
        scenario_seed=result.scenario_seed,
        playbook_version_id=session.playbook_version_id,
        playbook_authority=result.playbook_authority,
        document_id=session.document_id,
        status=session.status,
        revision=session.revision,
        in_progress=session.status == "awaiting_decision",
        decisions=decisions,
        findings=findings,
        decision_count=len(decisions),
        cited_decision_count=sum(bool(decision.source_refs) for decision in decisions),
        reviewed_supported_count=sum(decision.reviewed_support for decision in decisions),
        deviation_count=len(result.deviations),
        uncovered_count=int(result.status == "uncovered"),
        overlap_count=int(result.status == "overlap"),
        event_count=len(session.events),
        last_state_hash=session.events[-1].state_hash,
        rehearsal_notice=result.rehearsal_notice,
        proposals=[
            proposal_output(proposal)
            for proposal in db.scalars(
                select(RuleProposal)
                .where(
                    or_(
                        RuleProposal.session_id == session.id,
                        RuleProposal.proposed_playbook_version_id == session.playbook_version_id,
                    )
                )
                .order_by(RuleProposal.created_at, RuleProposal.id)
            )
        ],
    )


def compare(
    db: Session, left_id: str, right_id: str, allow_policy_change: bool = False
) -> ComparisonOutput:
    left = session_output(db, left_id)
    right = session_output(db, right_id)
    if (
        left.scenario_id != right.scenario_id
        or left.playbook_version_id != right.playbook_version_id
        or left.events[0].context_hash != right.events[0].context_hash
    ):
        proposal = db.scalar(
            select(RuleProposal).where(
                RuleProposal.session_id == left.id,
                RuleProposal.proposed_playbook_version_id == right.playbook_version_id,
            )
        )
        if (
            not allow_policy_change
            or proposal is None
            or left.scenario_id != right.scenario_id
            or left.result.input_snapshot.scenario != right.result.input_snapshot.scenario
            or right.result.playbook_authority != "draft"
            or right.result.input_snapshot.graph.model_dump()
            != proposal.proposed_change_json["graph"]
        ):
            raise HTTPException(
                422,
                "Compare the same pinned policy, or explicitly compare a linked proposed-policy rehearsal",
            )
        return ComparisonOutput(
            left=report(db, left_id),
            right=report(db, right_id),
            shared_event_prefix=None,
            scope="proposed_policy",
        )
    shared = len(
        list(
            takewhile(
                lambda pair: pair[0].state_hash == pair[1].state_hash,
                zip(left.events, right.events),
            )
        )
    )
    return ComparisonOutput(
        left=report(db, left_id),
        right=report(db, right_id),
        shared_event_prefix=shared,
        scope="same_policy",
    )


def proposal_output(row: RuleProposal) -> ProposalOutput:
    return ProposalOutput(
        id=row.id,
        session_id=row.session_id,
        playbook_version_id=row.playbook_version_id,
        proposed_playbook_version_id=row.proposed_playbook_version_id,
        target_node_id=row.target_node_id,
        rationale=row.rationale,
        choices=row.proposed_change_json["choices"],
        evidence_status="uncited",
        review_status="pending",
        created_at=row.created_at,
    )


def require_proposal(db: Session, proposal_id: str) -> RuleProposal:
    row = db.get(RuleProposal, proposal_id)
    if row is None:
        raise HTTPException(404, "Proposal not found")
    return row


def propose(db: Session, session_id: str, data: ProposalInput) -> ProposalOutput:
    parent = require_session(db, session_id)
    previous, _ = _verified(db, parent)
    if parent.revision != data.expected_revision:
        raise HTTPException(409, "The run changed. Reload before proposing a rule")
    if parent.status not in {"uncovered", "overlap"} or previous.checkpoint is None:
        raise HTTPException(409, "Propose a rule at a stopped uncovered or overlapping decision")
    graph = previous.input_snapshot.graph.model_copy(deep=True)
    node = next(node for node in graph.nodes if node.id == previous.checkpoint.node_id)
    refs = set(
        db.scalars(select(SourceSegment.id).where(SourceSegment.document_id == parent.document_id))
    )
    if any(not set(choice.source_refs).issubset(refs) for choice in data.choices):
        raise HTTPException(422, "Proposal contains invalid source references")
    originals = {choice.id: choice for choice in node.choices}
    if data.choices == node.choices:
        raise HTTPException(422, "Change at least one choice before saving a proposal")
    # Editing a modeled choice removes its old evidence claim. Citation is never inherited
    # merely because the user kept the same ID or copied source references into a request.
    choices = [
        choice.model_copy(deep=True, update={"source_refs": [], "evidence_status": "uncited"})
        if choice != originals.get(choice.id)
        else choice.model_copy(deep=True)
        for choice in data.choices
    ]
    node.choices = choices
    try:
        graph = Graph.model_validate(graph.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    version = create_playbook(
        db,
        PlaybookInput(
            document_id=parent.document_id,
            title=f"Proposal: {previous.scenario_title}"[:200],
            graph=graph,
        ),
    )
    version.parent_version_id = parent.playbook_version_id
    proposal = RuleProposal(
        session_id=parent.id,
        playbook_version_id=parent.playbook_version_id,
        proposed_playbook_version_id=version.id,
        target_node_id=node.id,
        rationale=data.rationale,
        proposed_change_json={
            "choices": [choice.model_dump() for choice in choices],
            "graph": graph.model_dump(),
        },
    )
    db.add(proposal)
    _commit(db)
    return proposal_output(proposal)


def rehearse_proposal(db: Session, proposal_id: str) -> SessionOutput:
    proposal = require_proposal(db, proposal_id)
    parent = require_session(db, proposal.session_id)
    previous, events = _verified(db, parent)
    version = db.get(PlaybookVersion, proposal.proposed_playbook_version_id)
    if (
        version is None
        or version.status != "draft"
        or version.document_id != parent.document_id
        or version.graph_json != proposal.proposed_change_json["graph"]
    ):
        raise HTTPException(409, "The proposed draft changed. Its original proposal is preserved")
    request = previous.input_snapshot.model_copy(
        deep=True,
        update={
            "graph": Graph.model_validate(proposal.proposed_change_json["graph"]),
            "playbook_version_id": version.id,
            "playbook_authority": "draft",
            "decisions": list(previous.decisions_made),
        },
    )
    result = _execute(request)
    # This is a changed-policy re-execution, not an identical-history fork.
    # Prior user choices are reused; the engine recomputes every event under the new context.
    checkpoint = next(
        event.sequence_number
        for event in reversed(events)
        if event.event_type == "decision_evaluated"
    )
    return _new_session(
        db,
        parent.scenario_id,
        parent.document_id,
        result,
        parent_session_id=parent.id,
        fork_event_index=checkpoint,
    )


def compatible_scenarios(db: Session, playbook_id: str) -> list[ScenarioOutput]:
    from app.services.playbooks import require_playbook

    row = require_playbook(db, playbook_id)
    nodes = {node.id for node in Graph.model_validate(row.graph_json).nodes}
    lineage: set[str] = set()
    ancestor: PlaybookVersion | None = row
    while ancestor is not None:
        if ancestor.id in lineage:
            raise HTTPException(409, "Playbook lineage contains a cycle")
        lineage.add(ancestor.id)
        ancestor = (
            db.get(PlaybookVersion, ancestor.parent_version_id)
            if ancestor.parent_version_id
            else None
        )
    return [
        scenario_output(scenario)
        for scenario in db.scalars(
            select(Scenario).where(Scenario.playbook_version_id.in_(lineage)).order_by(Scenario.id)
        )
        if all(inject["before_node_id"] in nodes for inject in scenario.injects_json)
    ]
