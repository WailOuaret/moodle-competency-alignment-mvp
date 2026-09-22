"""Resource ingestion tests. No live Moodle, Gemini, or Ollama calls."""

from __future__ import annotations

from hashlib import sha256

import pytest

from moodle_competency.resource_ingestion import (
    EmptyResourceError,
    PdfTextUnavailableError,
    UnsupportedFileError,
    extract_text_pdf,
    ingest_existing_moodle_resource,
    ingest_html,
    ingest_pasted_text,
    ingest_text_pdf,
    ingest_txt,
    ingest_uploaded_file,
    sanitize_filename,
    sha256_text,
)


PASTE_TEXT = (
    "Software verification includes testing software against specified "
    "requirements. User testing can also evaluate interface usability."
)


def _pdf_with_text(text: str) -> bytes:
    escaped = (
        text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    )
    stream = f"BT /F1 12 Tf 40 80 Td ({escaped}) Tj ET".encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj"
        ),
        (
            b"4 0 obj << /Length "
            + str(len(stream)).encode("ascii")
            + b" >> stream\n"
            + stream
            + b"\nendstream endobj"
        ),
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []

    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
        out.extend(b"\n")

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")

    for offset in offsets:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    out.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
    )
    out.extend(f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    return bytes(out)


def test_pasted_text_ingestion() -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Verification notes")

    assert resource["title"] == "Verification notes"
    assert resource["source_type"] == "paste"
    assert resource["research_status"] == "RUNTIME_DEMO"
    assert "verification" in resource["text"].casefold()
    assert resource["runtime_resource_id"].startswith("runtime:paste:")


def test_txt_ingestion() -> None:
    resource = ingest_txt(
        PASTE_TEXT.encode("utf-8"),
        title="From txt",
        original_filename="notes.txt",
    )

    assert resource["source_type"] == "txt"
    assert resource["original_filename"] == "notes.txt"
    assert resource["text"]


def test_html_ingestion_strips_scripts() -> None:
    html = """
    <html><body>
    <h1>Software testing</h1>
    <p>Testing and verification are performed throughout development.</p>
    <script>alert('xss')</script>
    </body></html>
    """
    resource = ingest_html(html, title="HTML page", original_filename="x.html")

    assert "alert" not in resource["text"]
    assert "verification" in resource["text"].casefold()
    assert resource["source_structure"] == "heading_paragraph"
    assert resource["metadata"]["html_executed"] is False


def test_text_native_pdf_ingestion() -> None:
    payload = _pdf_with_text("Software verification testing requirements")
    extracted = extract_text_pdf(payload)
    assert "Software" in extracted or "verification" in extracted.casefold()

    resource = ingest_text_pdf(
        payload,
        title="PDF notes",
        original_filename="notes.pdf",
    )
    assert resource["source_type"] == "pdf"
    assert resource["metadata"]["ocr_used"] is False


def test_empty_input_rejected() -> None:
    with pytest.raises(EmptyResourceError):
        ingest_pasted_text("   \n  ", title="Empty")

    with pytest.raises(EmptyResourceError):
        ingest_txt(b"", title="Empty", original_filename="empty.txt")


def test_unsupported_file_type() -> None:
    with pytest.raises(UnsupportedFileError):
        ingest_uploaded_file(
            b"fake",
            filename="slides.docx",
            title="Slides",
        )


def test_stable_hashes() -> None:
    first = ingest_pasted_text(PASTE_TEXT, title="A")
    second = ingest_pasted_text(PASTE_TEXT, title="A")

    assert first["raw_text_hash"] == second["raw_text_hash"]
    assert first["normalized_text_hash"] == second["normalized_text_hash"]
    assert first["runtime_resource_id"] == second["runtime_resource_id"]
    assert first["raw_text_hash"] == sha256_text(first["raw_text"])
    assert len(first["raw_text_hash"]) == 64


def test_filename_sanitization() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\\\Users\\\\a\\\\file.txt") == "file.txt"
    assert "/" not in sanitize_filename("weird name (1).txt")
    assert sanitize_filename("notes.txt") == "notes.txt"


def test_empty_pdf_reports_no_ocr() -> None:
    from pypdf import PdfWriter
    from io import BytesIO

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)

    with pytest.raises(PdfTextUnavailableError, match="OCR is outside"):
        ingest_text_pdf(buffer.getvalue(), title="Blank")


def test_existing_moodle_page() -> None:
    catalogue = [
        {
            "resource_id": "page:1",
            "resource_type": "page",
            "title": "Software Testing Introduction",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "text": "Testing and verification are performed throughout development.",
        }
    ]
    resource = ingest_existing_moodle_resource(
        "page:1",
        resources=catalogue,
    )

    assert resource["source_type"] == "moodle"
    assert resource["course_shortname"] == "MVP-SW"
    assert resource["resource_type"] == "page"


def test_quiz_question_stays_one_resource() -> None:
    catalogue = [
        {
            "resource_id": "quiz_question:1:4",
            "resource_type": "quiz_question",
            "title": "SW_Q2",
            "course_shortname": "MVP-SW",
            "text": "What is the main purpose of software testing?",
            "search_text": "What is the main purpose of software testing?",
        }
    ]
    resource = ingest_existing_moodle_resource(
        "quiz_question:1:4",
        resources=catalogue,
    )
    assert resource["source_structure"] == "quiz_question"
    assert sha256(
        resource["raw_text"].encode("utf-8")
    ).hexdigest() == resource["raw_text_hash"]
