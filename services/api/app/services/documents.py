import hashlib
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Document, SourceSegment
from app.schemas.api import DocumentInput, DocumentOutput, SegmentOutput
from app.services.segmentation import segment_document


def create_document(
    db: Session,
    data: DocumentInput,
    document_id: str | None = None,
    *,
    original_file_hash: str | None = None,
    page_texts: list[str] | None = None,
) -> Document:
    if (original_file_hash is None) != (page_texts is None) or (
        page_texts is not None and "\n\n".join(page_texts) != data.content
    ):
        raise ValueError("PDF provenance must match the exact extracted text")
    document = Document(
        title=data.title,
        content=data.content,
        source_type="pdf" if page_texts is not None else data.source_type,
        original_file_hash=original_file_hash,
        page_count=len(page_texts) if page_texts is not None else None,
        empty_pages_json=[index + 1 for index, text in enumerate(page_texts) if not text.strip()]
        if page_texts is not None
        else None,
        content_hash=hashlib.sha256(data.content.encode()).hexdigest(),
    )
    if document_id:
        document.id = document_id
    db.add(document)
    db.flush()
    ranges: list[tuple[int, int, int]] = []
    offset = 0
    for index, text in enumerate(page_texts or []):
        ranges.append((offset, offset + len(text), index + 1))
        offset += len(text) + 2
    db.add_all(
        SourceSegment(
            **asdict(segment),
            page_number=next(
                (
                    page
                    for start, end, page in ranges
                    if start <= segment.start_offset and segment.end_offset <= end
                ),
                None,
            ),
        )
        for segment in segment_document(document.id, document.content)
    )
    db.flush()
    return document


def document_output(db: Session, document: Document) -> DocumentOutput:
    segments = db.scalars(
        select(SourceSegment)
        .where(
            SourceSegment.document_id == document.id,
        )
        .order_by(SourceSegment.ordinal)
    ).all()
    return DocumentOutput(
        **{
            key: getattr(document, key)
            for key in [
                "id",
                "title",
                "content",
                "content_hash",
                "source_type",
                "created_at",
            ]
        },
        segments=[SegmentOutput.model_validate(s) for s in segments],
        original_file_hash=document.original_file_hash,
        page_count=document.page_count,
        empty_pages=document.empty_pages_json or [],
    )
