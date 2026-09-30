"""Normalized resource and competency contract for LMS connectors.

This module does not read or write frozen experiment files. Connectors may
call ``validate_resource_record`` before handing a record to fragmentation.
"""

from __future__ import annotations

from typing import Any, Mapping


REQUIRED_RESOURCE_FIELDS = (
    "resource_id",
    "resource_type",
    "title",
    "text",
)

RETRIEVAL_FIELDS = (
    "course_fullname",
    "section_name",
    "activity_name",
    "title",
    "search_text",
    "text",
)

PROVENANCE_FIELDS = (
    "course_id",
    "course_shortname",
    "course_fullname",
    "course_module_id",
    "section_id",
    "section_number",
    "section_name",
    "activity_id",
    "activity_name",
    "source_item_id",
    "source_extraction",
    "metadata",
)

REQUIRED_COMPETENCY_FIELDS = (
    "idnumber",
    "shortname",
    "description_text",
)

# Types the frozen experiment actually evaluated.
EVALUATED_RESOURCE_TYPES = frozenset({"page", "quiz_question"})

# Types the runtime UI can ingest without a new LMS connector.
RUNTIME_RESOURCE_TYPES = frozenset(
    {
        "page",
        "quiz_question",
        "pasted_text",
        "uploaded_txt",
        "uploaded_html",
        "uploaded_pdf",
    }
)

# Adapter-ready types. Fragmentation already chunks unknown types as
# resource_chunk. They are not part of the frozen 35-fragment experiment.
ADAPTER_RESOURCE_TYPES = frozenset({"assignment"})


class ResourceContractError(ValueError):
    """Raised when a connector record cannot enter the alignment engine."""


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def validate_resource_record(
    record: Mapping[str, Any],
) -> list[str]:
    """Return human-readable contract errors. Empty list means usable."""

    errors: list[str] = []

    if not isinstance(record, Mapping):
        return ["resource record must be a mapping"]

    for field in REQUIRED_RESOURCE_FIELDS:
        if not _text(record.get(field)):
            errors.append(f"missing required field: {field}")

    resource_id = _text(record.get("resource_id"))
    if resource_id and any(char.isspace() for char in resource_id):
        errors.append("resource_id must not contain whitespace")

    if "search_text" in record and record.get("search_text") is not None:
        if not isinstance(record.get("search_text"), str):
            errors.append("search_text must be a string when present")

    metadata = record.get("metadata", {})
    if metadata is not None and not isinstance(metadata, Mapping):
        errors.append("metadata must be a mapping when present")

    return errors


def assert_resource_record(record: Mapping[str, Any]) -> None:
    errors = validate_resource_record(record)
    if errors:
        raise ResourceContractError("; ".join(errors))


def validate_competency_record(
    record: Mapping[str, Any],
) -> list[str]:
    """Return errors for one normalized competency profile."""

    errors: list[str] = []

    if not isinstance(record, Mapping):
        return ["competency record must be a mapping"]

    for field in REQUIRED_COMPETENCY_FIELDS:
        if not _text(record.get(field)):
            errors.append(f"missing required field: {field}")

    parent = record.get("parent_idnumber")
    idnumber = _text(record.get("idnumber"))
    if parent is not None and _text(parent) == idnumber and idnumber:
        errors.append("parent_idnumber must not equal idnumber")

    return errors
