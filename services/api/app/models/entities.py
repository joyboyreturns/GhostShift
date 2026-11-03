from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.engine.interfaces import RunStatus


def new_id() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    title: Mapped[str]
    content: Mapped[str]
    content_hash: Mapped[str]
    source_type: Mapped[str]
    original_file_hash: Mapped[str | None]
    page_count: Mapped[int | None]
    empty_pages_json: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now)


class SourceSegment(Base):
    __tablename__ = "source_segments"
    __table_args__ = (UniqueConstraint("document_id", "ordinal"),)
    id: Mapped[str] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    ordinal: Mapped[int]
    text: Mapped[str]
    start_offset: Mapped[int]
    end_offset: Mapped[int]
    page_number: Mapped[int | None]


class PlaybookVersion(Base):
    __tablename__ = "playbook_versions"
    __table_args__ = (UniqueConstraint("document_id", "version"),)
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    parent_version_id: Mapped[str | None] = mapped_column(ForeignKey("playbook_versions.id"))
    version: Mapped[int]
    title: Mapped[str]
    status: Mapped[Literal["draft", "approved"]] = mapped_column(String, default="draft")
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(primary_key=True)
    playbook_version_id: Mapped[str] = mapped_column(ForeignKey("playbook_versions.id"))
    title: Mapped[str]
    description: Mapped[str]
    initial_facts_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    injects_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    seed: Mapped[int]
    fictional: Mapped[bool] = mapped_column(default=True)


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    playbook_version_id: Mapped[str] = mapped_column(ForeignKey("playbook_versions.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    parent_session_id: Mapped[str | None] = mapped_column(ForeignKey("simulation_sessions.id"))
    fork_event_index: Mapped[int | None]
    engine_version: Mapped[str]
    status: Mapped[RunStatus] = mapped_column(String)
    revision: Mapped[int] = mapped_column(default=0)
    current_node_id: Mapped[str]
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)


class SessionEvent(Base):
    __tablename__ = "session_events"
    __table_args__ = (UniqueConstraint("session_id", "sequence_number"),)
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("simulation_sessions.id"), index=True)
    sequence_number: Mapped[int]
    event_type: Mapped[str]
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    state_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=now)


class PlaybookReview(Base):
    __tablename__ = "playbook_reviews"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    playbook_version_id: Mapped[str] = mapped_column(
        ForeignKey("playbook_versions.id"), unique=True
    )
    graph_hash: Mapped[str]
    reviewer: Mapped[str]
    notes: Mapped[str]
    reviewed_choices_json: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)


class RuleProposal(Base):
    __tablename__ = "rule_proposals"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("simulation_sessions.id"))
    playbook_version_id: Mapped[str] = mapped_column(ForeignKey("playbook_versions.id"))
    proposed_playbook_version_id: Mapped[str] = mapped_column(
        ForeignKey("playbook_versions.id"), unique=True
    )
    target_node_id: Mapped[str]
    rationale: Mapped[str]
    proposed_change_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    evidence_status: Mapped[str] = mapped_column(default="uncited")
    review_status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(default=now)


@event.listens_for(PlaybookReview, "before_update")
@event.listens_for(PlaybookReview, "before_delete")
@event.listens_for(RuleProposal, "before_update")
@event.listens_for(RuleProposal, "before_delete")
@event.listens_for(Document, "before_update")
@event.listens_for(Document, "before_delete")
@event.listens_for(SourceSegment, "before_update")
@event.listens_for(SourceSegment, "before_delete")
@event.listens_for(Scenario, "before_update")
@event.listens_for(Scenario, "before_delete")
@event.listens_for(SessionEvent, "before_update")
@event.listens_for(SessionEvent, "before_delete")
def immutable_source(*_: object) -> None:
    raise ValueError("source/scenario/event records are immutable; create a new record")


@event.listens_for(PlaybookVersion, "before_update")
@event.listens_for(PlaybookVersion, "before_delete")
def immutable_approved(_mapper: object, _connection: object, target: PlaybookVersion) -> None:
    from sqlalchemy import inspect

    previous = inspect(target).attrs.status.history.deleted
    was_approved = previous[0] == "approved" if previous else target.status == "approved"
    if was_approved:
        raise ValueError("approved playbook versions are immutable")
