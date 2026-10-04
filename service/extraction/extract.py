"""Choose an extractor from the declared type and the file signature."""

from __future__ import annotations

import hashlib
from typing import Any

from service.extraction.captions import cues_to_text, parse_captions
from service.extraction.errors import DocumentError
from service.extraction.limits import EXTRACTOR_VERSION, MAX_FILE_BYTES
from service.extraction.ooxml import extract_docx, extract_pptx
from service.extraction.pdftext import extract_pdf
from service.extraction.safety import reject_oversized
from service.extraction.text import decode_text, markdown_to_plain

_FORMATS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text": "text/plain",
    "markdown": "text/markdown",
    "vtt": "text/vtt",
    "srt": "application/x-subrip",
}


def _signature(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"PK"):
        return "ooxml"
    return "text"


def _join(segments: list[dict[str, str]]) -> str:
    return "\n\n".join(segment["text"] for segment in segments if segment.get("text"))


def extract_document(data: bytes, declared_format: str) -> dict[str, Any]:
    """Return canonical text and the segments a quote can be traced to.

    ``declared_format`` is one of pdf, docx, pptx, text, markdown, vtt, srt.
    A signature that contradicts that declaration is rejected.
    """

    declared_format = declared_format.strip().lower()
    if declared_format not in _FORMATS:
        raise DocumentError("document_unsupported", "Unsupported resource type.")

    if not data:
        raise DocumentError("document_no_text", "The document does not contain enough text.")

    reject_oversized(data, MAX_FILE_BYTES)
    signature = _signature(data)

    if declared_format == "pdf" and signature != "pdf":
        raise DocumentError("document_malformed", "The file does not match its declared type.")
    if declared_format in {"docx", "pptx"} and signature != "ooxml":
        raise DocumentError("document_malformed", "The file does not match its declared type.")
    if declared_format in {"text", "markdown", "vtt", "srt"} and signature != "text":
        raise DocumentError("document_malformed", "The file does not match its declared type.")

    if declared_format == "pdf":
        segments = extract_pdf(data)
        text = _join(segments)
    elif declared_format == "docx":
        segments = extract_docx(data)
        text = _join(segments)
    elif declared_format == "pptx":
        segments = extract_pptx(data)
        text = _join(segments)
    elif declared_format in {"text", "markdown"}:
        plain = decode_text(data)
        if declared_format == "markdown":
            plain = markdown_to_plain(plain)
        if not plain:
            raise DocumentError("document_no_text", "The document does not contain enough text.")
        segments = [{"kind": "text", "number": "1", "text": plain}]
        text = plain
    else:
        plain = decode_text(data)
        segments = parse_captions(plain, declared_format)
        text = cues_to_text(segments)

    return {
        "extractor_version": EXTRACTOR_VERSION,
        "content_sha256": hashlib.sha256(data).hexdigest(),
        "text": text,
        "segments": segments,
    }
