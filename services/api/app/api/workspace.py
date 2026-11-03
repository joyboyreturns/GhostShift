from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.simulation import ScenarioOutput
from app.schemas.workspace import LibraryPage, ScenarioInput, VersionHistory, VersionSummary
from app.services import workspace
from app.services.simulation import scenario_output
from app.services.transactions import sqlite_write

router = APIRouter(prefix="/api")
Database = Annotated[Session, Depends(get_db)]


@router.get("/library", response_model=LibraryPage)
def library(
    db: Database,
    q: str = Query(default="", max_length=200),
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=24, ge=1, le=50),
) -> LibraryPage:
    return workspace.library(db, q.strip(), offset, limit)


@router.get("/playbooks/{playbook_id}/history", response_model=VersionHistory)
def history(playbook_id: str, db: Database) -> VersionHistory:
    return workspace.history(db, playbook_id)


@router.post("/scenarios", response_model=ScenarioOutput, status_code=201)
@sqlite_write
def create_scenario(data: ScenarioInput, db: Database) -> ScenarioOutput:
    row = workspace.create_scenario(db, data)
    db.commit()
    return scenario_output(row)


@router.get("/documents/{document_id}/models", response_model=list[VersionSummary])
def document_models(document_id: str, db: Database) -> list[VersionSummary]:
    return workspace.document_models(db, document_id)
