"""Ingest runtime teaching resources without modifying Moodle or gold data.

HTML is treated as data: scripts are stripped and never executed.
PDF support is text-native extraction only. OCR is out of scope.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote

from bs4 import BeautifulSoup

from moodle_competency.annotation import load_jsonl as load_resource_jsonl
from moodle_competency.html_clean import (
    html_to_text,
    normalize_whitespace,
)
from moodle_competency.settings import PROJECT_ROOT


EXTRACTOR_VERSION = "runtime-1.0"
NORMALIZATION_VERSION = "1.0"
RESEARCH_STATUS = "RUNTIME_DEMO"
SUPPORTED_UPLOAD_SUFFIXES = {".txt", ".html", ".htm", ".pdf"}
UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
PDF_EMPTY_MESSAGE = (
    "No machine-readable text was found. "
    "OCR is outside the current MVP."
)


class ResourceIngestionError(ValueError):
    """Raised when a runtime resource cannot be ingested."""


class EmptyResourceError(ResourceIngestionError):
    """Raised when the input contains no usable text."""


class UnsupportedFileError(ResourceIngestionError):
    """Raised for file types outside the MVP upload set."""


class PdfTextUnavailableError(ResourceIngestionError):
    """Raised when a PDF has no extractable text."""


class MoodleResourceUnavailableError(ResourceIngestionError):
    """Raised when a Moodle catalogue resource cannot be loaded."""


def utc_timestamp(moment: datetime | None = None) -> str:
    value = moment or datetime.now(timezone.utc)
    return value.replace(microsecond=0).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(str(value).encode("utf-8"))


def sanitize_filename(filename: str | None) -> str:
    """Return a path-safe basename. Never keep directory components."""

    raw = unquote(str(filename or "")).replace("\\", "/")
    name = Path(raw).name.strip()

    if not name or name in {".", ".."}:
        return "upload"

    cleaned = UNSAFE_FILENAME_CHARS.sub("_", name).strip("._")
    return (cleaned or "upload")[:200]


def html_to_block_text(value: str | None) -> str:
    """Extract heading/paragraph blocks. Scripts are discarded, not run."""

    if value is None or not str(value).strip():
        return ""

    soup = BeautifulSoup(str(value), "lxml")

    for unwanted in soup(
        ["script", "style", "noscript", "template", "iframe"]
    ):
        unwanted.decompose()

    blocks: list[str] = []

    for element in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]
    ):
        text = normalize_whitespace(element.get_text(" "))

        if text:
            blocks.append(text)

    if blocks:
        return "\n\n".join(blocks)

    return html_to_text(str(value))


def extract_text_pdf(payload: bytes) -> str:
    """Extract embedded PDF text. Does not perform OCR."""

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ResourceIngestionError(
            "PDF support requires the pypdf package."
        ) from exc

    try:
        reader = PdfReader(BytesIO(payload))
        pages = [
            str(page.extract_text() or "")
            for page in reader.pages
        ]
    except Exception as exc:
        raise PdfTextUnavailableError(PDF_EMPTY_MESSAGE) from exc

    text = "\n\n".join(
        normalize_whitespace(page)
        for page in pages
        if normalize_whitespace(page)
    )

    if not text:
        raise PdfTextUnavailableError(PDF_EMPTY_MESSAGE)

    return text


def _require_text(text: str, *, source: str) -> str:
    normalized = str(text or "").strip()

    if not normalized or not normalize_whitespace(normalized):
        raise EmptyResourceError(
            f"Empty resource: {source} contains no usable text."
        )

    return normalized


def _stable_runtime_id(
    *,
    source_type: str,
    raw_text: str,
    source_reference: str,
) -> str:
    digest = sha256_text(
        f"{source_type}|{source_reference}|{raw_text}"
    )[:16]
    return f"runtime:{source_type}:{digest}"


def _runtime_resource(
    *,
    title: str,
    resource_type: str,
    source_type: str,
    source_reference: str,
    raw_text: str,
    normalized_text: str,
    source_structure: str,
    course_id: int | None = None,
    course_shortname: str | None = None,
    original_filename: str | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    title_text = normalize_whitespace(title) or "Untitled resource"
    course_name = normalize_whitespace(course_shortname) or None
    filename = (
        sanitize_filename(original_filename)
        if original_filename
        else None
    )
    runtime_resource_id = _stable_runtime_id(
        source_type=source_type,
        raw_text=raw_text,
        source_reference=source_reference or filename or title_text,
    )

    return {
        "runtime_resource_id": runtime_resource_id,
        "resource_id": runtime_resource_id,
        "title": title_text,
        "course_id": course_id,
        "course_shortname": course_name,
        "resource_type": resource_type,
        "source_type": source_type,
        "source_reference": source_reference,
        "original_filename": filename,
        "raw_text": raw_text,
        "text": normalized_text,
        "search_text": normalized_text,
        "raw_text_hash": sha256_text(raw_text),
        "normalized_text_hash": sha256_text(normalized_text),
        "created_at": utc_timestamp(),
        "research_status": RESEARCH_STATUS,
        "source_structure": source_structure,
        "extractor_version": EXTRACTOR_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "metadata": dict(extra_metadata or {}),
    }


def ingest_pasted_text(
    text: str,
    *,
    title: str,
    course_id: int | None = None,
    course_shortname: str | None = None,
) -> dict[str, Any]:
    raw = _require_text(text, source="pasted text")
    normalized = normalize_whitespace(raw)
    _require_text(normalized, source="pasted text")
    return _runtime_resource(
        title=title,
        resource_type="pasted_text",
        source_type="paste",
        source_reference="clipboard",
        raw_text=raw,
        normalized_text=normalized,
        source_structure="paragraph",
        course_id=course_id,
        course_shortname=course_shortname,
    )


def ingest_txt(
    payload: bytes | str,
    *,
    title: str,
    original_filename: str | None = None,
    course_id: int | None = None,
    course_shortname: str | None = None,
) -> dict[str, Any]:
    filename = sanitize_filename(original_filename or "resource.txt")

    if isinstance(payload, bytes):
        raw = payload.decode("utf-8", errors="replace")
    else:
        raw = str(payload)

    raw = _require_text(raw, source=filename)
    normalized = normalize_whitespace(raw)
    _require_text(normalized, source=filename)
    return _runtime_resource(
        title=title or Path(filename).stem,
        resource_type="uploaded_txt",
        source_type="txt",
        source_reference=filename,
        raw_text=raw,
        normalized_text=normalized,
        source_structure="paragraph",
        course_id=course_id,
        course_shortname=course_shortname,
        original_filename=filename,
    )


def ingest_html(
    payload: bytes | str,
    *,
    title: str,
    original_filename: str | None = None,
    course_id: int | None = None,
    course_shortname: str | None = None,
) -> dict[str, Any]:
    filename = sanitize_filename(original_filename or "resource.html")

    if isinstance(payload, bytes):
        raw = payload.decode("utf-8", errors="replace")
    else:
        raw = str(payload)

    raw = _require_text(raw, source=filename)
    block_text = html_to_block_text(raw)
    normalized = _require_text(block_text, source=filename)
    heading_present = bool(
        BeautifulSoup(raw, "lxml").find(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        )
    )
    return _runtime_resource(
        title=title or Path(filename).stem,
        resource_type="uploaded_html",
        source_type="html",
        source_reference=filename,
        raw_text=raw,
        normalized_text=normalized,
        source_structure=(
            "heading_paragraph" if heading_present else "paragraph"
        ),
        course_id=course_id,
        course_shortname=course_shortname,
        original_filename=filename,
        extra_metadata={"html_executed": False},
    )


def ingest_text_pdf(
    payload: bytes,
    *,
    title: str,
    original_filename: str | None = None,
    course_id: int | None = None,
    course_shortname: str | None = None,
) -> dict[str, Any]:
    filename = sanitize_filename(original_filename or "resource.pdf")

    if not payload:
        raise EmptyResourceError("Empty resource: PDF upload is empty.")

    extracted = extract_text_pdf(payload)
    normalized = _require_text(extracted, source=filename)
    return _runtime_resource(
        title=title or Path(filename).stem,
        resource_type="uploaded_pdf",
        source_type="pdf",
        source_reference=filename,
        raw_text=extracted,
        normalized_text=normalized,
        source_structure="paragraph",
        course_id=course_id,
        course_shortname=course_shortname,
        original_filename=filename,
        extra_metadata={
            "ocr_used": False,
            "pdf_mode": "text_native",
        },
    )


def load_moodle_resource_catalogue(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Read already-extracted Moodle Pages and Quiz questions."""

    catalogue_path = path or (
        PROJECT_ROOT / "data" / "processed" / "resources.jsonl"
    )

    if not catalogue_path.exists():
        raise MoodleResourceUnavailableError(
            "Moodle unavailable: extracted resource catalogue was not found."
        )

    records = load_resource_jsonl(catalogue_path)
    return [
        record
        for record in records
        if str(record.get("resource_type", "")).strip()
        in {"page", "quiz_question"}
    ]


def list_moodle_courses(
    resources: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    catalogue = list(resources or load_moodle_resource_catalogue())
    seen: dict[str, dict[str, Any]] = {}

    for record in catalogue:
        shortname = normalize_whitespace(
            record.get("course_shortname")
        ) or "Unknown course"
        seen.setdefault(
            shortname,
            {
                "course_id": record.get("course_id"),
                "course_shortname": shortname,
                "course_fullname": record.get("course_fullname", ""),
            },
        )

    return sorted(
        seen.values(),
        key=lambda item: str(item["course_shortname"]),
    )


def list_moodle_resources_for_course(
    course_shortname: str,
    resources: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    catalogue = list(resources or load_moodle_resource_catalogue())
    wanted = normalize_whitespace(course_shortname)
    return [
        record
        for record in catalogue
        if normalize_whitespace(record.get("course_shortname")) == wanted
    ]


def ingest_existing_moodle_resource(
    resource_id: str,
    *,
    resources: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Copy an already-extracted Moodle Page or Quiz question.

    This does not call Moodle and does not modify Moodle.
    """

    wanted = normalize_whitespace(resource_id)

    if not wanted:
        raise EmptyResourceError("Empty resource: Moodle resource id is empty.")

    try:
        catalogue = list(resources or load_moodle_resource_catalogue())
    except MoodleResourceUnavailableError:
        raise

    match = next(
        (
            record
            for record in catalogue
            if normalize_whitespace(record.get("resource_id")) == wanted
        ),
        None,
    )

    if match is None:
        raise MoodleResourceUnavailableError(
            f"Moodle unavailable: resource {wanted!r} was not found "
            "in the extracted catalogue."
        )

    resource_type = normalize_whitespace(match.get("resource_type"))

    if resource_type not in {"page", "quiz_question"}:
        raise UnsupportedFileError(
            f"Unsupported Moodle resource type: {resource_type}."
        )

    if resource_type == "quiz_question":
        text = _require_text(
            str(
                match.get("search_text")
                or match.get("text")
                or ""
            ),
            source=wanted,
        )
        source_structure = "quiz_question"
    else:
        text = _require_text(
            str(match.get("text") or match.get("search_text") or ""),
            source=wanted,
        )
        source_structure = "heading_paragraph"

    return _runtime_resource(
        title=str(match.get("title") or wanted),
        resource_type=resource_type,
        source_type="moodle",
        source_reference=wanted,
        raw_text=text,
        normalized_text=normalize_whitespace(text),
        source_structure=source_structure,
        course_id=match.get("course_id"),
        course_shortname=str(match.get("course_shortname") or "") or None,
        extra_metadata={
            "moodle_resource_id": wanted,
            "activity_name": match.get("activity_name", ""),
            "activity_id": match.get("activity_id"),
            "course_module_id": match.get("course_module_id"),
            "source_extraction": match.get("source_extraction"),
        },
    )


def ingest_uploaded_file(
    payload: bytes,
    *,
    filename: str,
    title: str,
    course_id: int | None = None,
    course_shortname: str | None = None,
) -> dict[str, Any]:
    safe_name = sanitize_filename(filename)
    suffix = Path(safe_name).suffix.lower()

    if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
        raise UnsupportedFileError(
            f"Unsupported file type: {suffix or 'unknown'}. "
            "Upload TXT, HTML, or a text-native PDF."
        )

    if suffix == ".txt":
        return ingest_txt(
            payload,
            title=title,
            original_filename=safe_name,
            course_id=course_id,
            course_shortname=course_shortname,
        )

    if suffix in {".html", ".htm"}:
        return ingest_html(
            payload,
            title=title,
            original_filename=safe_name,
            course_id=course_id,
            course_shortname=course_shortname,
        )

    return ingest_text_pdf(
        payload,
        title=title,
        original_filename=safe_name,
        course_id=course_id,
        course_shortname=course_shortname,
    )
