"""Text-layer PDF extraction. Image-only pages are reported, not OCR'd."""

from __future__ import annotations

import io

from service.extraction.errors import DocumentError
from service.extraction.limits import MAX_EXTRACTED_CHARS, MAX_PDF_PAGES


def extract_pdf(data: bytes) -> list[dict[str, str]]:
    if not data.startswith(b"%PDF"):
        raise DocumentError("document_malformed", "The document could not be read.")

    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise DocumentError(
            "document_unsupported",
            "PDF extraction is not available on this service.",
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise DocumentError("document_malformed", "The document could not be read.") from exc
    except Exception as exc:
        raise DocumentError("document_malformed", "The document could not be read.") from exc

    if getattr(reader, "is_encrypted", False):
        raise DocumentError(
            "document_encrypted",
            "This PDF is password-protected and cannot be analysed.",
        )

    try:
        page_count = len(reader.pages)
    except Exception as exc:
        raise DocumentError("document_malformed", "The document could not be read.") from exc

    if page_count > MAX_PDF_PAGES:
        raise DocumentError("document_too_large", "The document is too large for analysis.")

    segments: list[dict[str, str]] = []
    total = 0
    for number, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception as exc:
            raise DocumentError("document_malformed", "The document could not be read.") from exc

        text = " ".join(raw.split())
        if not text:
            continue
        total += len(text)
        if total > MAX_EXTRACTED_CHARS:
            raise DocumentError("document_too_large", "The document is too large for analysis.")
        segments.append({"kind": "page", "number": str(number), "text": text})

    if not segments:
        raise DocumentError(
            "document_no_text",
            "This PDF does not contain enough extractable text. OCR is not enabled in this release.",
        )

    return segments
