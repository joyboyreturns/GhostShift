from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.api import PlaybookInput
from app.schemas.graph import Choice, StrictModel
from app.schemas.time import UtcDatetime


class DraftInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)


class RevisionInput(PlaybookInput):
    pass


class ReviewedChoice(StrictModel):
    node_id: str
    choice_id: str


class ApprovalInput(StrictModel):
    expected_graph_hash: str = Field(min_length=64, max_length=64)
    reviewer: str = Field(min_length=1, max_length=100)
    notes: str = Field(min_length=1, max_length=2000)
    reviewed_choices: list[ReviewedChoice] = Field(max_length=10000)
    confirmed_source_support: Literal[True]

    @field_validator("reviewer", "notes")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class ReviewOutput(BaseModel):
    id: str
    reviewer: str
    notes: str
    graph_hash: str
    created_at: UtcDatetime


class ProposalInput(StrictModel):
    expected_revision: int = Field(ge=0, strict=True)
    rationale: str = Field(min_length=1, max_length=2000)
    choices: list[Choice] = Field(min_length=1, max_length=50)

    @field_validator("rationale")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rationale must not be blank")
        return value.strip()


class ProposalOutput(BaseModel):
    id: str
    session_id: str
    playbook_version_id: str
    proposed_playbook_version_id: str
    target_node_id: str
    rationale: str
    choices: list[Choice]
    evidence_status: Literal["uncited"]
    review_status: Literal["pending"]
    created_at: UtcDatetime


class ProposalRehearsalInput(StrictModel):
    allow_draft_rehearsal: Literal[True]
