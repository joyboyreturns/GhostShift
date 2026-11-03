import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.entities import (
    Document,
    PlaybookReview,
    PlaybookVersion,
    RuleProposal,
    SourceSegment,
)
from app.schemas.api import PlaybookInput, PlaybookOutput
from app.schemas.graph import Graph
from app.schemas.policy import ApprovalInput, ReviewOutput, RevisionInput


def create_playbook(db: Session, data: PlaybookInput) -> PlaybookVersion:
    if db.get(Document, data.document_id) is None:
        raise HTTPException(404, "Document not found")
    refs = set(
        db.scalars(
            select(SourceSegment.id).where(
                SourceSegment.document_id == data.document_id,
            )
        )
    )
    try:
        data.graph.validate_references(refs)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    latest = (
        db.scalar(
            select(func.max(PlaybookVersion.version)).where(
                PlaybookVersion.document_id == data.document_id,
            )
        )
        or 0
    )
    playbook = PlaybookVersion(
        document_id=data.document_id,
        title=data.title,
        version=latest + 1,
        status="draft",
        graph_json=data.graph.model_dump(),
    )
    db.add(playbook)
    db.flush()
    return playbook


def playbook_output(playbook: PlaybookVersion) -> PlaybookOutput:
    return PlaybookOutput(
        id=playbook.id,
        document_id=playbook.document_id,
        title=playbook.title,
        version=playbook.version,
        status=playbook.status,
        graph=Graph.model_validate(playbook.graph_json),
        parent_version_id=playbook.parent_version_id,
        graph_hash=graph_hash(playbook),
    )


def require_playbook(db: Session, playbook_id: str) -> PlaybookVersion:
    row = db.get(PlaybookVersion, playbook_id)
    if row is None:
        raise HTTPException(404, "Playbook not found")
    return row


def graph_hash(row: PlaybookVersion) -> str:
    snapshot = {
        "graph": row.graph_json,
        "document_id": row.document_id,
        "parent_version_id": row.parent_version_id,
        "title": row.title,
        "version": row.version,
    }
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def revision(db: Session, playbook_id: str, data: RevisionInput) -> PlaybookVersion:
    parent = require_playbook(db, playbook_id)
    row = create_playbook(db, data)
    row.parent_version_id = parent.id
    row.version = max(row.version, parent.version + 1)
    db.flush()
    return row


def review_output(db: Session, playbook_id: str) -> ReviewOutput | None:
    require_playbook(db, playbook_id)
    row = db.scalar(select(PlaybookReview).where(PlaybookReview.playbook_version_id == playbook_id))
    return (
        None
        if row is None
        else ReviewOutput(
            id=row.id,
            reviewer=row.reviewer,
            notes=row.notes,
            graph_hash=row.graph_hash,
            created_at=row.created_at,
        )
    )


def approve(db: Session, playbook_id: str, data: ApprovalInput) -> PlaybookVersion:
    row = require_playbook(db, playbook_id)
    if row.status != "draft":
        raise HTTPException(409, "This version is already approved and immutable")
    if graph_hash(row) != data.expected_graph_hash:
        raise HTTPException(409, "The draft changed. Reload and review the current version")
    if db.scalar(
        select(RuleProposal.id).where(RuleProposal.proposed_playbook_version_id == row.id)
    ):
        raise HTTPException(
            422,
            "Proposal snapshots remain unapproved. Create and review a source-supported revision",
        )
    graph = Graph.model_validate(row.graph_json)
    if not any(node.type in {"decision", "action"} for node in graph.nodes):
        raise HTTPException(422, "Model at least one rule before requesting approval")
    refs = set(
        db.scalars(select(SourceSegment.id).where(SourceSegment.document_id == row.document_id))
    )
    try:
        graph.validate_references(refs)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    required = {(node.id, choice.id) for node in graph.nodes for choice in node.choices}
    reviewed = [(choice.node_id, choice.choice_id) for choice in data.reviewed_choices]
    if set(reviewed) != required or len(reviewed) != len(required):
        raise HTTPException(422, "Explicitly review every decision choice exactly once")
    if any(not choice.source_refs for node in graph.nodes for choice in node.choices) or any(
        node.type == "action" and not node.source_refs for node in graph.nodes
    ):
        raise HTTPException(
            422, "Uncited rules cannot be approved. Create a source-supported revision first"
        )
    changed = db.execute(
        update(PlaybookVersion)
        .where(PlaybookVersion.id == row.id, PlaybookVersion.status == "draft")
        .values(status="approved")
        .returning(PlaybookVersion.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if changed is None:
        db.rollback()
        raise HTTPException(409, "This version was reviewed elsewhere. Reload")
    db.add(
        PlaybookReview(
            playbook_version_id=row.id,
            graph_hash=data.expected_graph_hash,
            reviewer=data.reviewer,
            notes=data.notes,
            reviewed_choices_json=[choice.model_dump() for choice in data.reviewed_choices],
        )
    )
    db.commit()
    db.expire_all()
    return require_playbook(db, playbook_id)


def document_draft(db: Session, document_id: str, title: str) -> PlaybookVersion:
    graph = Graph.model_validate(
        {
            "nodes": [
                {"id": "start", "type": "start", "label": "Begin procedure", "next_node": "end"},
                {"id": "end", "type": "end", "label": "Procedure complete"},
            ]
        }
    )
    return create_playbook(db, PlaybookInput(document_id=document_id, title=title, graph=graph))
