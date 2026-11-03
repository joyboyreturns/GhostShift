"""Thin HTTP adapters; persistence, authority and replay live in the service."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.policy import ProposalInput, ProposalOutput, ProposalRehearsalInput
from app.schemas.simulation import (
    ChoiceInput,
    ComparisonOutput,
    ForkInput,
    ReplayOutput,
    ScenarioOutput,
    SessionCreate,
    SessionOutput,
    SessionReport,
)
from app.services import simulation
from app.services.transactions import sqlite_write

router = APIRouter(prefix="/api")
Database = Annotated[Session, Depends(get_db)]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioOutput)
def scenario(scenario_id: str, db: Database) -> ScenarioOutput:
    return simulation.scenario_output(simulation.require_scenario(db, scenario_id))


# Static compare route must precede /sessions/{session_id}.
@router.get("/sessions/compare", response_model=ComparisonOutput)
def compare(
    left_id: str, right_id: str, db: Database, allow_policy_change: bool = False
) -> ComparisonOutput:
    return simulation.compare(db, left_id, right_id, allow_policy_change)


@router.post("/sessions", response_model=SessionOutput, status_code=201)
@sqlite_write
def create(data: SessionCreate, db: Database) -> SessionOutput:
    return simulation.create_session(db, data)


@router.get("/sessions/{session_id}", response_model=SessionOutput)
def get(session_id: str, db: Database) -> SessionOutput:
    return simulation.session_output(db, session_id)


@router.post("/sessions/{session_id}/choose", response_model=SessionOutput)
@sqlite_write
def choose(session_id: str, data: ChoiceInput, db: Database) -> SessionOutput:
    return simulation.choose(db, session_id, data)


@router.post("/sessions/{session_id}/fork", response_model=SessionOutput, status_code=201)
@sqlite_write
def fork(session_id: str, data: ForkInput, db: Database) -> SessionOutput:
    return simulation.fork(db, session_id, data)


@router.get("/sessions/{session_id}/replay", response_model=ReplayOutput)
def replay(session_id: str, db: Database) -> ReplayOutput:
    return simulation.replay(db, session_id)


@router.get("/sessions/{session_id}/report", response_model=SessionReport)
def report(session_id: str, db: Database) -> SessionReport:
    return simulation.report(db, session_id)


@router.post("/sessions/{session_id}/proposals", response_model=ProposalOutput, status_code=201)
@sqlite_write
def propose(session_id: str, data: ProposalInput, db: Database) -> ProposalOutput:
    return simulation.propose(db, session_id, data)


@router.get("/proposals/{proposal_id}", response_model=ProposalOutput)
def get_proposal(proposal_id: str, db: Database) -> ProposalOutput:
    return simulation.proposal_output(simulation.require_proposal(db, proposal_id))


@router.post("/proposals/{proposal_id}/rehearse", response_model=SessionOutput, status_code=201)
@sqlite_write
def rehearse_proposal(
    proposal_id: str, data: ProposalRehearsalInput, db: Database
) -> SessionOutput:
    return simulation.rehearse_proposal(db, proposal_id)


@router.get("/playbooks/{playbook_id}/scenarios", response_model=list[ScenarioOutput])
def compatible_scenarios(playbook_id: str, db: Database) -> list[ScenarioOutput]:
    return simulation.compatible_scenarios(db, playbook_id)
