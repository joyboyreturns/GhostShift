"""Typed transport contracts for persisted, explicit model rehearsals."""

from typing import Literal

from pydantic import BaseModel, Field

from app.engine.interfaces import (
    Facts,
    Inject,
    LogicalEvent,
    PlaybookAuthority,
    RunInput,
    RunResult,
    RunStatus,
)
from app.schemas.graph import StrictModel
from app.schemas.policy import ProposalOutput, ReviewOutput
from app.schemas.time import UtcDatetime


class ScenarioOutput(BaseModel):
    id: str
    playbook_version_id: str
    title: str
    description: str
    initial_facts: Facts
    injects: list[Inject]
    seed: int
    fictional: bool


class SessionCreate(StrictModel):
    scenario_id: str = Field(min_length=1, max_length=100)
    allow_draft_rehearsal: bool = False
    playbook_version_id: str | None = Field(default=None, max_length=100)


class ChoiceInput(StrictModel):
    choice_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=0, strict=True)


class ForkInput(StrictModel):
    event_index: int = Field(ge=0, strict=True)


class EventOutput(LogicalEvent):
    id: str
    created_at: UtcDatetime


class SessionOutput(BaseModel):
    id: str
    scenario_id: str
    playbook_version_id: str
    document_id: str
    parent_session_id: str | None
    fork_event_index: int | None
    engine_version: str
    revision: int
    status: RunStatus
    current_node_id: str
    created_at: UtcDatetime
    result: RunResult
    proposal_id: str | None
    events: list[EventOutput]


class ReplayOutput(BaseModel):
    session_id: str
    verified: Literal[True] = True
    event_count: int
    last_state_hash: str
    engine_version: str


class ReportDecision(BaseModel):
    node_id: str
    node_label: str
    choice_id: str
    choice_label: str
    outcome: Literal["modeled_match", "deviation"]
    source_refs: list[str]
    evidence_status: Literal["cited", "uncited"]
    reviewed_support: bool


class ReportFinding(BaseModel):
    kind: Literal["uncovered", "overlap"]
    node_id: str
    node_label: str
    matching_choice_ids: list[str]
    source_refs: list[str]
    missing_conditions: int
    incompatible_conditions: int


class ReportEvidence(BaseModel):
    id: str
    ordinal: int
    text: str
    start_offset: int
    end_offset: int
    page_number: int | None = None


class SessionReport(BaseModel):
    session_id: str
    parent_session_id: str | None
    scenario_id: str
    scenario_title: str
    scenario_seed: int
    playbook_version_id: str
    playbook_authority: PlaybookAuthority
    document_id: str
    status: RunStatus
    revision: int
    in_progress: bool
    decisions: list[ReportDecision]
    findings: list[ReportFinding]
    decision_count: int
    cited_decision_count: int
    reviewed_supported_count: int
    deviation_count: int
    uncovered_count: int
    overlap_count: int
    event_count: int
    last_state_hash: str
    rehearsal_notice: str
    proposals: list[ProposalOutput]
    approval: ReviewOutput | None = None
    source_title: str
    source_content_hash: str
    original_file_hash: str | None = None
    evidence: list[ReportEvidence]
    replay_input: RunInput
    logical_events: list[LogicalEvent]
    final_facts: Facts


class ComparisonOutput(BaseModel):
    left: SessionReport
    right: SessionReport
    shared_event_prefix: int | None
    scope: Literal["same_policy", "proposed_policy"]
