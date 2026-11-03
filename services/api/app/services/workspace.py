"""Bounded discovery, version ancestry and scenario authoring within the current database scope."""

from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Document,
    PlaybookVersion,
    Scenario,
    SimulationSession,
    SourceSegment,
    new_id,
)
from app.schemas.graph import Graph
from app.schemas.workspace import (
    DocumentSummary,
    LibraryPage,
    ScenarioInput,
    SessionSummary,
    VersionHistory,
    VersionSummary,
)
from app.services.playbooks import require_playbook
from app.services.simulation import scenario_output


def version_summary(row: PlaybookVersion) -> VersionSummary:
    return VersionSummary(
        id=row.id,
        document_id=row.document_id,
        parent_version_id=row.parent_version_id,
        title=row.title,
        version=row.version,
        status=row.status,
        created_at=row.created_at,
        node_count=len(row.graph_json.get("nodes", [])),
    )


def library(db: Session, query: str, offset: int, limit: int) -> LibraryPage:
    documents = select(Document).where(Document.title.icontains(query, autoescape=True))
    playbooks = select(PlaybookVersion).where(
        PlaybookVersion.title.icontains(query, autoescape=True)
    )
    scenarios = select(Scenario).where(Scenario.title.icontains(query, autoescape=True))
    sessions = (
        select(SimulationSession, Scenario.title, PlaybookVersion.title)
        .join(Scenario, Scenario.id == SimulationSession.scenario_id)
        .join(PlaybookVersion, PlaybookVersion.id == SimulationSession.playbook_version_id)
        .where(
            Scenario.title.icontains(query, autoescape=True)
            | SimulationSession.id.icontains(query, autoescape=True)
        )
    )
    totals: dict[Literal["documents", "playbooks", "scenarios", "sessions"], int] = {
        "documents": db.scalar(select(func.count()).select_from(documents.subquery())) or 0,
        "playbooks": db.scalar(select(func.count()).select_from(playbooks.subquery())) or 0,
        "scenarios": db.scalar(select(func.count()).select_from(scenarios.subquery())) or 0,
        "sessions": db.scalar(select(func.count()).select_from(sessions.subquery())) or 0,
    }
    docs = []
    for row in db.scalars(
        documents.order_by(Document.created_at.desc(), Document.id).offset(offset).limit(limit)
    ):
        docs.append(
            DocumentSummary(
                id=row.id,
                title=row.title,
                source_type=row.source_type,
                created_at=row.created_at,
                segment_count=db.scalar(
                    select(func.count())
                    .select_from(SourceSegment)
                    .where(SourceSegment.document_id == row.id)
                )
                or 0,
                playbook_count=db.scalar(
                    select(func.count())
                    .select_from(PlaybookVersion)
                    .where(PlaybookVersion.document_id == row.id)
                )
                or 0,
            )
        )
    return LibraryPage(
        documents=docs,
        playbooks=[
            version_summary(row)
            for row in db.scalars(
                playbooks.order_by(PlaybookVersion.created_at.desc(), PlaybookVersion.id)
                .offset(offset)
                .limit(limit)
            )
        ],
        scenarios=[
            scenario_output(row)
            for row in db.scalars(
                scenarios.order_by(Scenario.title, Scenario.id).offset(offset).limit(limit)
            )
        ],
        sessions=[
            SessionSummary(
                id=row.id,
                scenario_id=row.scenario_id,
                scenario_title=scenario_title,
                playbook_version_id=row.playbook_version_id,
                playbook_title=playbook_title,
                parent_session_id=row.parent_session_id,
                status=row.status,
                revision=row.revision,
                created_at=row.created_at,
            )
            for row, scenario_title, playbook_title in db.execute(
                sessions.order_by(SimulationSession.created_at.desc(), SimulationSession.id)
                .offset(offset)
                .limit(limit)
            )
        ],
        totals=totals,
        offset=offset,
        limit=limit,
    )


def history(db: Session, version_id: str) -> VersionHistory:
    selected = require_playbook(db, version_id)
    # Recursive CTEs traverse only this version family, not unrelated models sharing a source.
    ancestors = (
        select(PlaybookVersion.id, PlaybookVersion.parent_version_id)
        .where(PlaybookVersion.id == selected.id)
        .cte(recursive=True)
    )
    parent = select(PlaybookVersion.id, PlaybookVersion.parent_version_id).join(
        ancestors, PlaybookVersion.id == ancestors.c.parent_version_id
    )
    ancestors = ancestors.union(parent)
    roots = select(ancestors.c.id).where(ancestors.c.parent_version_id.is_(None))
    root_id = db.scalar(roots)
    if root_id is None:
        raise HTTPException(409, "Version ancestry is incomplete or cyclic")
    family = select(PlaybookVersion.id).where(PlaybookVersion.id == root_id).cte(recursive=True)
    family = family.union(
        select(PlaybookVersion.id).join(family, PlaybookVersion.parent_version_id == family.c.id)
    )
    rows = db.scalars(
        select(PlaybookVersion)
        .where(PlaybookVersion.id.in_(select(family.c.id)))
        .order_by(PlaybookVersion.created_at, PlaybookVersion.id)
        .limit(201)
    ).all()
    if len(rows) > 200:
        raise HTTPException(422, "Version family exceeds the interactive history limit")
    return VersionHistory(selected_id=version_id, versions=[version_summary(row) for row in rows])


def create_scenario(db: Session, data: ScenarioInput) -> Scenario:
    playbook = require_playbook(db, data.playbook_version_id)
    graph = Graph.model_validate(playbook.graph_json)
    if not any(node.type in {"decision", "action"} for node in graph.nodes):
        raise HTTPException(422, "Model a decision or action before authoring a scenario")
    references = set(
        db.scalars(
            select(SourceSegment.id).where(SourceSegment.document_id == playbook.document_id)
        )
    )
    try:
        graph.validate_references(references)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    nodes = {node.id for node in graph.nodes}
    if any(inject.before_node_id not in nodes for inject in data.injects):
        raise HTTPException(422, "Every scenario change must target an existing graph node")
    row = Scenario(
        id=new_id(),
        playbook_version_id=playbook.id,
        title=data.title.strip(),
        description=data.description,
        initial_facts_json=data.initial_facts,
        injects_json=[inject.model_dump(mode="json") for inject in data.injects],
        seed=data.seed,
        fictional=True,
    )
    db.add(row)
    db.flush()
    return row


def document_models(db: Session, document_id: str) -> list[VersionSummary]:
    if db.get(Document, document_id) is None:
        raise HTTPException(404, "Document not found")
    return [
        version_summary(row)
        for row in db.scalars(
            select(PlaybookVersion)
            .where(PlaybookVersion.document_id == document_id)
            .order_by(PlaybookVersion.created_at.desc(), PlaybookVersion.id)
            .limit(50)
        )
    ]
