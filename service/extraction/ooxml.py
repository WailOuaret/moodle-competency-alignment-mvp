"""DOCX and PPTX text. Macros and embedded objects are not executed."""

from __future__ import annotations

import io

from service.extraction.errors import DocumentError
from service.extraction.limits import MAX_DOCX_PARAGRAPHS, MAX_EXTRACTED_CHARS, MAX_SLIDES
from service.extraction.safety import inspect_ooxml


def _bounded(segments: list[dict[str, str]]) -> list[dict[str, str]]:
    total = sum(len(segment["text"]) for segment in segments)
    if total > MAX_EXTRACTED_CHARS:
        raise DocumentError("document_too_large", "The document is too large for analysis.")
    if not segments:
        raise DocumentError("document_no_text", "The document does not contain enough text.")
    return segments


def extract_docx(data: bytes) -> list[dict[str, str]]:
    inspect_ooxml(data)
    if b"word/document.xml" not in data[: min(len(data), 2_000_000)] and b"word/document.xml" not in data:
        # The name lives in the zip central directory, which inspect_ooxml already opened.
        pass

    try:
        import zipfile

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise DocumentError("document_malformed", "The document could not be read.")
        from docx import Document
    except DocumentError:
        raise
    except ImportError as exc:
        raise DocumentError(
            "document_unsupported",
            "DOCX extraction is not available on this service.",
        ) from exc

    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError("document_malformed", "The document could not be read.") from exc

    segments: list[dict[str, str]] = []
    paragraph_index = 0
    heading = ""
    for paragraph in document.paragraphs:
        paragraph_index += 1
        if paragraph_index > MAX_DOCX_PARAGRAPHS:
            raise DocumentError("document_too_large", "The document is too large for analysis.")
        text = " ".join(paragraph.text.split())
        if not text:
            continue
        style = ""
        if paragraph.style is not None and paragraph.style.name:
            style = paragraph.style.name
        if style.lower().startswith("heading"):
            heading = text
        segments.append({
            "kind": "paragraph",
            "number": str(paragraph_index),
            "heading": heading,
            "text": text,
        })

    for table_index, table in enumerate(document.tables, start=1):
        rows: list[str] = []
        for row in table.rows:
            cells = [" ".join(cell.text.split()) for cell in row.cells]
            cells = [cell for cell in cells if cell]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            segments.append({
                "kind": "table",
                "number": str(table_index),
                "heading": heading,
                "text": "\n".join(rows),
            })

    return _bounded(segments)


def extract_pptx(data: bytes) -> list[dict[str, str]]:
    inspect_ooxml(data)

    try:
        import zipfile

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if not any(name.startswith("ppt/slides/slide") for name in archive.namelist()):
                raise DocumentError("document_malformed", "The document could not be read.")
        from pptx import Presentation
    except DocumentError:
        raise
    except ImportError as exc:
        raise DocumentError(
            "document_unsupported",
            "PPTX extraction is not available on this service.",
        ) from exc

    try:
        presentation = Presentation(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError("document_malformed", "The document could not be read.") from exc

    if len(presentation.slides) > MAX_SLIDES:
        raise DocumentError("document_too_large", "The document is too large for analysis.")

    segments: list[dict[str, str]] = []
    for number, slide in enumerate(presentation.slides, start=1):
        pieces: list[str] = []
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = " ".join(paragraph.text.split())
                if text:
                    pieces.append(text)
        # Speaker notes are left out. They are not part of the slide the student sees.
        if pieces:
            segments.append({
                "kind": "slide",
                "number": str(number),
                "text": "\n".join(pieces),
            })

    return _bounded(segments)
