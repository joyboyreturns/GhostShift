from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.entities import Document, PlaybookVersion
from app.schemas.api import (
    DemoCatalog,
    DemoWorkspace,
    DocumentInput,
    DocumentOutput,
    Health,
    PlaybookInput,
    PlaybookOutput,
    ResetInput,
)
from app.schemas.policy import ApprovalInput, DraftInput, ReviewOutput, RevisionInput
from app.services.documents import create_document, document_output
from app.services.pdf_import import PdfInput, import_pdf
from app.services.playbooks import (
    approve,
    create_playbook,
    document_draft,
    playbook_output,
    review_output,
    revision,
)
from app.services.seed import catalog
from app.services.transactions import sqlite_write

router = APIRouter(prefix="/api")
Database = Annotated[Session, Depends(get_db)]


def require_document(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    return document


@router.get("/health", response_model=Health)
def health(db: Database) -> Health:
    db.execute(text("SELECT 1"))
    return Health()


@router.get("/demo", response_model=DemoCatalog)
def demo(request: Request) -> DemoCatalog:
    result = catalog()
    workspace = getattr(request.state, "demo_workspace", None)
    if workspace is not None:
        result.workspace = DemoWorkspace(expires_at=workspace[1])
    return result


@router.post("/documents", response_model=DocumentOutput, status_code=201)
@sqlite_write
def import_document(data: DocumentInput, db: Database) -> DocumentOutput:
    document = create_document(db, data)
    db.commit()
    return document_output(db, document)


@router.get("/documents/{document_id}", response_model=DocumentOutput)
def get_document(document_id: str, db: Database) -> DocumentOutput:
    return document_output(db, require_document(db, document_id))


@router.post("/playbooks", response_model=PlaybookOutput, status_code=201)
@sqlite_write
def post_playbook(data: PlaybookInput, db: Database) -> PlaybookOutput:
    playbook = create_playbook(db, data)
    db.commit()
    return playbook_output(playbook)


@router.get("/playbooks/{playbook_id}", response_model=PlaybookOutput)
def get_playbook(playbook_id: str, db: Database) -> PlaybookOutput:
    playbook = db.get(PlaybookVersion, playbook_id)
    if playbook is None:
        raise HTTPException(404, "Playbook not found")
    return playbook_output(playbook)


@router.post("/playbooks/{playbook_id}/revisions", response_model=PlaybookOutput, status_code=201)
@sqlite_write
def revise_playbook(playbook_id: str, data: RevisionInput, db: Database) -> PlaybookOutput:
    row = revision(db, playbook_id, data)
    db.commit()
    return playbook_output(row)


@router.get("/playbooks/{playbook_id}/review", response_model=ReviewOutput | None)
def get_review(playbook_id: str, db: Database) -> ReviewOutput | None:
    return review_output(db, playbook_id)


@router.post("/playbooks/{playbook_id}/approve", response_model=PlaybookOutput)
@sqlite_write
def approve_playbook(playbook_id: str, data: ApprovalInput, db: Database) -> PlaybookOutput:
    return playbook_output(approve(db, playbook_id, data))


@router.post("/documents/{document_id}/draft", response_model=PlaybookOutput, status_code=201)
@sqlite_write
def model_document(document_id: str, data: DraftInput, db: Database) -> PlaybookOutput:
    row = document_draft(db, document_id, data.title)
    db.commit()
    return playbook_output(row)


@router.post("/demo/reset", response_model=DemoCatalog)
async def reset_demo(request: Request, data: ResetInput) -> DemoCatalog:
    allocate = getattr(request.state, "reset_workspace", None)
    if allocate is None:
        raise HTTPException(409, "Workspace reset is available only in the temporary public demo")
    await allocate()
    return demo(request)


@router.post("/documents/pdf", response_model=DocumentOutput, status_code=201)
@sqlite_write
def import_pdf_document(data: PdfInput, db: Database) -> DocumentOutput:
    document = import_pdf(db, data)
    db.commit()
    return document_output(db, document)
