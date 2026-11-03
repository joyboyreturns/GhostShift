"""Isolated application code for PDF text extraction. Input bytes are parsed, never executed."""

import io
import json
import logging
import resource
import sys


class RejectedPdf(ValueError):
    pass


def main() -> None:
    logging.disable(logging.CRITICAL)
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    # Linux is the production target. macOS does not reliably enforce address-space limits.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024, 512 * 1024))
    from pypdf import PdfReader, filters
    from pypdf.errors import PyPdfError

    try:
        filters.ZLIB_MAX_OUTPUT_LENGTH = 4 * 1024 * 1024
        data = sys.stdin.buffer.read(256 * 1024 + 1)
        if len(data) > 256 * 1024 or not data.startswith(b"%PDF-"):
            raise RejectedPdf("Use a PDF no larger than 256 KiB")
        reader = PdfReader(
            io.BytesIO(data), root_object_recovery_limit=1000, xref_stream_maximum_entries=10000
        )
        if reader.is_encrypted:
            raise RejectedPdf(
                "Encrypted PDFs are not supported. Export an unprotected text-based PDF"
            )
        if not 1 <= len(reader.pages) <= 20:
            raise RejectedPdf("PDFs must contain between 1 and 20 pages")
        pages: list[str] = []
        characters = 0
        for page in reader.pages:
            content = page.get_contents()
            if content is not None and len(content.get_data()) > 4 * 1024 * 1024:
                raise RejectedPdf("A PDF page exceeds the supported content-stream limit")
            text = page.extract_text() or ""
            if "\x00" in text:
                raise RejectedPdf("PDF text encoding is not readable. Paste readable text instead")
            characters += len(text) + (2 if pages else 0)
            if characters > 100000:
                raise RejectedPdf("Extracted PDF text exceeds 100,000 characters")
            pages.append(text)
        if not any(page.strip() for page in pages):
            raise RejectedPdf(
                "No readable text was found. Scanned PDFs require OCR, which is not included"
            )
        print(json.dumps({"pages": pages}, ensure_ascii=False))
    except RejectedPdf as exc:
        print(json.dumps({"error": str(exc)}))
    except (
        PyPdfError,
        ValueError,
        OSError,
        MemoryError,
        RecursionError,
        TypeError,
        KeyError,
        IndexError,
        OverflowError,
    ):
        # Parser diagnostics can include source text. Return only this fixed message.
        print(json.dumps({"error": "PDF parsing failed or exceeded a supported limit"}))


if __name__ == "__main__":
    main()
