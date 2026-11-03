"""Small, genuinely text-based fictional PDFs generated for parser integration tests."""

import io

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def make_pdf(pages: list[str | None], *, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            }
        )
    )
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        if text is not None:
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            stream = DecodedStreamObject()
            escaped = (
                text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")
            )
            stream.set_data(b"BT /F1 12 Tf 40 740 Td (" + escaped + b") Tj ET")
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("fictional-test-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
