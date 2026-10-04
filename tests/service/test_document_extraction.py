"""Offline tests for document and caption extraction."""

from __future__ import annotations

import io
import zipfile

import pytest
from docx import Document
from pptx import Presentation

from service.extraction.errors import DocumentError
from service.extraction.extract import extract_document
from service.extraction.limits import EXTRACTOR_VERSION


def _pdf_with_sentence(sentence: str) -> bytes:
    # A one-page PDF whose text layer is the sentence. Built without a renderer.
    stream = f"BT /F1 12 Tf 50 250 Td ({sentence}) Tj ET".encode("ascii")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        ),
        b"4 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n" + stream + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    body = b"%PDF-1.4\n"
    offsets = [0]
    for item in objects:
        offsets.append(len(body))
        body += item
    xref_at = len(body)
    xref = [f"xref\n0 {len(offsets)}\n", "0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    trailer = (
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    )
    return body + "".join(xref).encode("ascii") + trailer.encode("ascii")


def _docx(paragraphs: list[str], table: list[list[str]] | None = None) -> bytes:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    if table:
        grid = document.add_table(rows=len(table), cols=len(table[0]))
        for row_index, row in enumerate(table):
            for column_index, cell in enumerate(row):
                grid.rows[row_index].cells[column_index].text = cell
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _pptx(slides: list[str]) -> bytes:
    presentation = Presentation()
    layout = presentation.slide_layouts[5]
    for text in slides:
        slide = presentation.slides.add_slide(layout)
        slide.shapes.title.text = text
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def test_pdf_keeps_the_page_and_the_sentence() -> None:
    sentence = "Transactions protect groups of related operations."
    result = extract_document(_pdf_with_sentence(sentence), "pdf")

    assert result["extractor_version"] == EXTRACTOR_VERSION
    assert sentence in result["text"]
    assert result["segments"][0]["kind"] == "page"
    assert result["segments"][0]["number"] == "1"
    assert sentence in result["segments"][0]["text"]


def test_image_only_pdf_is_not_treated_as_empty_success() -> None:
    # A page with no text operators.
    data = _pdf_with_sentence("")
    # The empty Tj still creates a text operator with no characters. Build a blank page.
    blank = _pdf_with_sentence(" ")
    # A space-only sentence collapses to nothing after normalisation inside pypdf
    # may still return spaces. Force the no-text path with a PDF that has no contents.
    raw = blank.replace(b"( ) Tj", b"")
    with pytest.raises(DocumentError) as caught:
        extract_document(raw, "pdf")
    assert caught.value.code in {"document_no_text", "document_malformed"}


def test_docx_paragraphs_and_tables() -> None:
    result = extract_document(
        _docx(
            ["Security requirements", "Passwords are stored as hashes."],
            [["Control", "Hashing"]],
        ),
        "docx",
    )

    assert "Passwords are stored as hashes." in result["text"]
    assert any(segment["kind"] == "table" and "Hashing" in segment["text"] for segment in result["segments"])
    assert "page" not in {segment["kind"] for segment in result["segments"]}


def test_pptx_keeps_the_slide_number() -> None:
    result = extract_document(
        _pptx(["Load balancing", "Requests are shared across instances."]),
        "pptx",
    )

    assert result["segments"][0]["kind"] == "slide"
    assert result["segments"][0]["number"] == "1"
    assert "Load balancing" in result["segments"][0]["text"]
    assert "Requests are shared across instances." in result["segments"][1]["text"]


def test_markdown_is_text_not_html() -> None:
    source = b"# Title\n\nSee [the guide](https://example.invalid/secret) for *hashing*.\n"
    result = extract_document(source, "markdown")

    assert "hashing" in result["text"]
    assert "example.invalid" not in result["text"]
    assert "<a " not in result["text"]


def test_invalid_utf8_is_rejected() -> None:
    with pytest.raises(DocumentError) as caught:
        extract_document(b"\xff\xfe not utf-8", "text")
    assert caught.value.code == "document_malformed"


def test_mime_mismatch_is_rejected() -> None:
    with pytest.raises(DocumentError) as caught:
        extract_document(b"plain words", "pdf")
    assert caught.value.code == "document_malformed"


def test_zip_with_path_traversal_is_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("../escape.xml", "<x/>")
        archive.writestr("word/document.xml", "<w:document/>")
    with pytest.raises(DocumentError) as caught:
        extract_document(buffer.getvalue(), "docx")
    assert caught.value.code == "document_malformed"


def test_declared_zip_bomb_is_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", "<w:document/>")
        for index in range(401):
            archive.writestr(f"word/extra{index}.xml", "<x/>")
    with pytest.raises(DocumentError) as caught:
        extract_document(buffer.getvalue(), "docx")
    assert caught.value.code == "document_too_large"


def test_vtt_keeps_timestamps_and_exact_quote() -> None:
    vtt = (
        "WEBVTT\n\n"
        "00:08:42.000 --> 00:08:57.000\n"
        "Load balancing distributes requests across several instances.\n"
    )
    result = extract_document(vtt.encode(), "vtt")

    quote = "Load balancing distributes requests across several instances."
    assert quote in result["text"]
    assert result["segments"][0]["start"] == "00:08:42"
    assert result["segments"][0]["end"] == "00:08:57"
    assert quote == result["segments"][0]["text"]


def test_srt_cue() -> None:
    srt = "1\n00:12:10,000 --> 00:12:34,000\nNormalization removes repeated facts.\n"
    result = extract_document(srt.encode(), "srt")

    assert result["segments"][0]["start"] == "00:12:10"
    assert "Normalization removes repeated facts." in result["text"]


def test_french_and_arabic_round_trip() -> None:
    text = "Qualité logicielle.\nجودة البرمجيات.\n"
    result = extract_document(text.encode(), "text")

    assert "Qualité logicielle." in result["text"]
    assert "جودة البرمجيات." in result["text"]
