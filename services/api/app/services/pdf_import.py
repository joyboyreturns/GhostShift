"""Bounded PDF parsing through an isolated worker, with immutable extracted-text provenance."""

import base64
import binascii
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.models.entities import Document
from app.schemas.api import DocumentInput
from app.schemas.graph import StrictModel
from app.services.documents import create_document

_parser_slot = BoundedSemaphore(1)


class PdfInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    pdf_base64: str = Field(min_length=1, max_length=349528)


class ExtractedPdf(BaseModel):
    pages: list[str] = Field(min_length=1, max_length=20)


def import_pdf(db: Session, data: PdfInput) -> Document:
    try:
        content = base64.b64decode(data.pdf_base64.encode("ascii"), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(422, "PDF payload is not valid base64") from exc
    if len(content) > 256 * 1024 or not content.startswith(b"%PDF-"):
        raise HTTPException(422, "Use a PDF no larger than 256 KiB")
    worker = Path(__file__).with_name("pdf_worker.py")
    if not _parser_slot.acquire(blocking=False):
        raise HTTPException(429, "PDF import is busy. Retry shortly", headers={"Retry-After": "5"})
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(worker)],
            input=content,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            422, "PDF extraction exceeded its time limit. Use a simpler PDF or paste text"
        ) from exc
    except OSError as exc:
        raise HTTPException(
            503, "The PDF parser is unavailable. Paste text or retry shortly"
        ) from exc
    finally:
        _parser_slot.release()
    if result.returncode != 0 or len(result.stdout) > 1024 * 1024:
        raise HTTPException(422, "PDF extraction exceeded a supported resource limit")
    try:
        payload = json.loads(result.stdout)
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            raise HTTPException(422, payload["error"])
        extracted = ExtractedPdf.model_validate(payload)
        text = "\n\n".join(extracted.pages)
        imported = DocumentInput(title=data.title, content=text, source_type="text")
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            422, "PDF extraction did not produce readable text within the supported limits"
        ) from exc
    return create_document(
        db,
        imported,
        original_file_hash=hashlib.sha256(content).hexdigest(),
        page_texts=extracted.pages,
    )
