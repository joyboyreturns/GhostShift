"""Workspace discovery and explicit human-authored scenario contracts."""

from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.engine.interfaces import Facts, Inject, RunStatus
from app.schemas.graph import StrictModel
from app.schemas.simulation import ScenarioOutput
from app.schemas.time import UtcDatetime


def validate_facts(facts: Facts) -> Facts:
    if len(facts) > 64 or any(not field.strip() or len(field) > 100 for field in facts):
        raise ValueError("Use at most 64 facts with nonblank names of at most 100 characters")
    if any(isinstance(value, str) and len(value) > 500 for value in facts.values()):
        raise ValueError("Text fact values must not exceed 500 characters")
    return facts


class ScenarioInject(Inject):
    before_node_id: str = Field(min_length=1, max_length=100)

    @field_validator("facts")
    @classmethod
    def bounded_facts(cls, value: Facts) -> Facts:
        return validate_facts(value)


class ScenarioInput(StrictModel):
    playbook_version_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    initial_facts: Facts = Field(default_factory=dict)
    injects: list[ScenarioInject] = Field(default_factory=list, max_length=20)
    seed: int = Field(default=0, ge=0, le=2147483647, strict=True)
    fictional: Literal[True]

    @field_validator("initial_facts")
    @classmethod
    def bounded_facts(cls, value: Facts) -> Facts:
        return validate_facts(value)

    @model_validator(mode="after")
    def nonblank(self) -> Self:
        if not self.title.strip():
            raise ValueError("Scenario title must not be blank")
        names = set(self.initial_facts)
        for inject in self.injects:
            names.update(inject.facts)
        if len(names) > 64:
            raise ValueError("Use at most 64 distinct facts across the entire scenario")
        return self


class DocumentSummary(BaseModel):
    id: str
    title: str
    source_type: str
    created_at: UtcDatetime
    segment_count: int
    playbook_count: int


class VersionSummary(BaseModel):
    id: str
    document_id: str
    parent_version_id: str | None
    title: str
    version: int
    status: Literal["draft", "approved"]
    created_at: UtcDatetime
    node_count: int


class SessionSummary(BaseModel):
    id: str
    scenario_id: str
    scenario_title: str
    playbook_version_id: str
    playbook_title: str
    parent_session_id: str | None
    status: RunStatus
    revision: int
    created_at: UtcDatetime


class LibraryPage(BaseModel):
    documents: list[DocumentSummary]
    playbooks: list[VersionSummary]
    scenarios: list[ScenarioOutput]
    sessions: list[SessionSummary]
    totals: dict[Literal["documents", "playbooks", "scenarios", "sessions"], int]
    offset: int
    limit: int


class VersionHistory(BaseModel):
    selected_id: str
    versions: list[VersionSummary]
