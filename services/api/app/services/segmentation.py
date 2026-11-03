import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    id: str
    document_id: str
    ordinal: int
    text: str
    start_offset: int
    end_offset: int


def segment_document(document_id: str, content: str) -> list[Segment]:
    """Blank-line paragraphs; exact Unicode offsets; immutable document-scoped IDs."""
    result: list[Segment] = []
    for match in re.finditer(r"\S[\s\S]*?(?=\r?\n[ \t]*\r?\n|\Z)", content):
        text = match.group().rstrip()
        ordinal = len(result) + 1
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        result.append(
            Segment(
                id=f"{document_id}:s{ordinal}:{digest}",
                document_id=document_id,
                ordinal=ordinal,
                text=text,
                start_offset=match.start(),
                end_offset=match.start() + len(text),
            )
        )
    return result
