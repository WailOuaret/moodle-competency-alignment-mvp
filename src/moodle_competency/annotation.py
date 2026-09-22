"""Blinded fragment-level manual annotation for competency alignment."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "1.0"
COMPETENCY_ID_SEPARATOR = ";"
DATE_FORMAT = "%Y-%m-%d"

ANNOTATION_COLUMNS = (
    "fragment_id",
    "resource_id",
    "course_id",
    "course_shortname",
    "resource_type",
    "activity_name",
    "resource_title",
    "fragment_text",
    "gold_competency_ids",
    "gold_evidence",
    "no_competency",
    "ambiguous",
    "ambiguity_reason",
    "comment",
    "annotator",
    "annotation_date",
)

CATALOGUE_COLUMNS = (
    "idnumber",
    "shortname",
    "description",
    "parent_idnumber",
    "hierarchy_path",
    "depth",
)

HUMAN_FIELDS = (
    "gold_competency_ids",
    "gold_evidence",
    "no_competency",
    "ambiguous",
    "ambiguity_reason",
    "comment",
    "annotator",
    "annotation_date",
)

TRUE_VALUES = {"true", "1", "yes"}
FALSE_VALUES = {"false", "0", "no"}

FORBIDDEN_SOURCE_NAMES = (
    "bm25_candidates.jsonl",
    "llm_tasks.jsonl",
    "gemini_responses.jsonl",
    "gemini_validated.jsonl",
    "manual_moodle_links.csv",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSON objects from a UTF-8 JSON Lines file."""

    if not path.exists():
        raise FileNotFoundError(
            f"JSONL file does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} "
                    f"of {path}."
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Line {line_number} of {path} "
                    "is not a JSON object."
                )

            records.append(record)

    return records


def write_csv(
    records: Sequence[Mapping[str, Any]],
    output_path: Path,
    fieldnames: Sequence[str],
) -> Path:
    """Write UTF-8 CSV records without changing human values."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()

        for record in records:
            writer.writerow(
                {
                    field: record.get(field, "")
                    for field in fieldnames
                }
            )

    return output_path.resolve()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV as a list of string-valued rows."""

    if not path.exists():
        raise FileNotFoundError(
            f"CSV file does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError(
                f"CSV file has no header: {path}"
            )

        rows: list[dict[str, str]] = []

        for row in reader:
            rows.append(
                {
                    str(key): (
                        "" if value is None else str(value)
                    )
                    for key, value in row.items()
                    if key is not None
                }
            )

    return rows


def write_json(payload: Mapping[str, Any], output_path: Path) -> Path:
    """Write a UTF-8 JSON object with stable key order."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_path.resolve()


def text_value(record: Mapping[str, Any], *keys: str) -> str:
    """Return the first present value as a string."""

    for key in keys:
        if key not in record:
            continue

        value = record.get(key)

        if value is None:
            continue

        return str(value)

    return ""


def stripped_text(value: Any) -> str:
    """Convert a value to stripped text."""

    if value is None:
        return ""

    return str(value).strip()


def parse_boolean(
    raw: Any,
    field_name: str,
) -> tuple[bool | None, list[str]]:
    """Parse an explicit boolean, treating blank as undecided."""

    text = stripped_text(raw)

    if not text:
        return None, []

    lowered = text.lower()

    if lowered in TRUE_VALUES:
        return True, []

    if lowered in FALSE_VALUES:
        return False, []

    return None, [
        f"{field_name} must be true or false."
    ]


def parse_competency_ids(
    raw: Any,
) -> tuple[list[str], list[str]]:
    """Parse semicolon-separated competency IDs."""

    text = stripped_text(raw)
    errors: list[str] = []

    if not text:
        return [], errors

    parsed: list[str] = []

    for token in text.split(COMPETENCY_ID_SEPARATOR):
        competency_id = token.strip()

        if not competency_id:
            errors.append(
                "gold_competency_ids contains an empty token."
            )
            continue

        parsed.append(competency_id)

    duplicate_ids = sorted(
        competency_id
        for competency_id, count in Counter(parsed).items()
        if count > 1
    )

    if duplicate_ids:
        errors.append(
            "Duplicate competency IDs: "
            + ", ".join(duplicate_ids)
        )

    return parsed, errors


def parse_evidence(
    raw: Any,
) -> tuple[list[str], list[str]]:
    """Parse optional JSON-array evidence quotes."""

    text = stripped_text(raw)
    errors: list[str] = []

    if not text:
        return [], errors

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [], [
            "gold_evidence must be a JSON array of "
            'strings, for example ["exact quote"].'
        ]

    if not isinstance(parsed, list):
        return [], [
            "gold_evidence must be a JSON array of strings."
        ]

    quotes: list[str] = []

    for index, item in enumerate(parsed, start=1):
        if not isinstance(item, str):
            errors.append(
                f"gold_evidence item {index} must be a string."
            )
            continue

        if not item.strip():
            errors.append(
                f"gold_evidence item {index} is empty."
            )
            continue

        quotes.append(item)

    return quotes, errors


def parse_annotation_date(
    raw: Any,
) -> tuple[str | None, list[str]]:
    """Parse a required YYYY-MM-DD date when present."""

    text = stripped_text(raw)

    if not text:
        return None, []

    try:
        datetime.strptime(text, DATE_FORMAT)
    except ValueError:
        return None, [
            "annotation_date must use YYYY-MM-DD."
        ]

    return text, []


def build_resource_lookup(
    resources: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    """Index resources by resource_id."""

    lookup: dict[str, Mapping[str, Any]] = {}

    for resource in resources:
        resource_id = stripped_text(
            resource.get("resource_id")
        )

        if resource_id:
            lookup[resource_id] = resource

    return lookup


def build_competency_lookup(
    competencies: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    """Index competencies by idnumber."""

    lookup: dict[str, Mapping[str, Any]] = {}

    for competency in competencies:
        idnumber = stripped_text(
            competency.get("idnumber")
        )

        if idnumber:
            lookup[idnumber] = competency

    return lookup


def build_hierarchy_path(
    competency: Mapping[str, Any],
) -> str:
    """Build a stable hierarchy path from idnumbers."""

    hierarchy = competency.get("hierarchy_idnumbers")

    if isinstance(hierarchy, list) and hierarchy:
        parts = [
            stripped_text(part)
            for part in hierarchy
            if stripped_text(part)
        ]

        if parts:
            return " > ".join(parts)

    idnumber = stripped_text(competency.get("idnumber"))
    parent = stripped_text(
        competency.get("parent_idnumber")
    )

    if parent and idnumber:
        return f"{parent} > {idnumber}"

    return idnumber


def build_competency_catalogue(
    competencies: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Build the independent human-annotation catalogue."""

    catalogue: list[dict[str, str]] = []

    for competency in competencies:
        idnumber = stripped_text(
            competency.get("idnumber")
        )

        if not idnumber:
            continue

        depth = competency.get("depth")

        catalogue.append(
            {
                "idnumber": idnumber,
                "shortname": text_value(
                    competency,
                    "shortname",
                ),
                "description": text_value(
                    competency,
                    "description_text",
                    "description",
                ),
                "parent_idnumber": text_value(
                    competency,
                    "parent_idnumber",
                ),
                "hierarchy_path": build_hierarchy_path(
                    competency
                ),
                "depth": (
                    "" if depth is None else str(depth)
                ),
            }
        )

    return catalogue


def build_blank_annotation_row(
    fragment: Mapping[str, Any],
    resources_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    """Create one blank annotation row from a source fragment."""

    resource_id = text_value(fragment, "resource_id")
    resource = resources_by_id.get(resource_id, {})

    resource_title = text_value(fragment, "title")

    if not resource_title:
        resource_title = text_value(resource, "title")

    activity_name = text_value(fragment, "activity_name")

    if not activity_name:
        activity_name = text_value(
            resource,
            "activity_name",
        )

    course_id = text_value(fragment, "course_id")

    if not course_id:
        course_id = text_value(resource, "course_id")

    course_shortname = text_value(
        fragment,
        "course_shortname",
    )

    if not course_shortname:
        course_shortname = text_value(
            resource,
            "course_shortname",
        )

    resource_type = text_value(fragment, "resource_type")

    if not resource_type:
        resource_type = text_value(
            resource,
            "resource_type",
        )

    return {
        "fragment_id": text_value(
            fragment,
            "fragment_id",
        ),
        "resource_id": resource_id,
        "course_id": course_id,
        "course_shortname": course_shortname,
        "resource_type": resource_type,
        "activity_name": activity_name,
        "resource_title": resource_title,
        "fragment_text": text_value(fragment, "text"),
        "gold_competency_ids": "",
        "gold_evidence": "",
        "no_competency": "",
        "ambiguous": "",
        "ambiguity_reason": "",
        "comment": "",
        "annotator": "",
        "annotation_date": "",
    }


def build_blank_annotation_records(
    fragments: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Build blank annotation rows in source fragment order."""

    resources_by_id = build_resource_lookup(resources)
    records: list[dict[str, str]] = []

    for fragment in fragments:
        fragment_id = stripped_text(
            fragment.get("fragment_id")
        )

        if not fragment_id:
            raise ValueError(
                "A source fragment is missing fragment_id."
            )

        records.append(
            build_blank_annotation_row(
                fragment,
                resources_by_id,
            )
        )

    return records


def count_values(
    records: Sequence[Mapping[str, Any]],
    field: str,
) -> dict[str, int]:
    """Count non-empty field values."""

    counts = Counter(
        stripped_text(record.get(field))
        for record in records
        if stripped_text(record.get(field))
    )
    return dict(sorted(counts.items()))


def utc_timestamp(moment: datetime | None = None) -> str:
    """Return a timezone-aware ISO-8601 timestamp."""

    value = moment or datetime.now(timezone.utc)
    return value.replace(microsecond=0).isoformat()


def build_annotation_manifest(
    *,
    fragments: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
    annotations: Sequence[Mapping[str, Any]],
    fragments_path: Path,
    resources_path: Path,
    competencies_path: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Describe a blinded blank annotation template."""

    return {
        "schema_version": SCHEMA_VERSION,
        "source_fragments_file": str(fragments_path),
        "source_resources_file": str(resources_path),
        "source_competencies_file": str(competencies_path),
        "fragment_count": len(annotations),
        "competency_count": len(competencies),
        "course_counts": count_values(
            annotations,
            "course_shortname",
        ),
        "resource_type_counts": count_values(
            annotations,
            "resource_type",
        ),
        "template_generation_timestamp": utc_timestamp(
            generated_at
        ),
        "annotation_status": "blank_template",
        "competency_id_separator": COMPETENCY_ID_SEPARATOR,
        "evidence_format": (
            "JSON array of exact contiguous substrings "
            "of fragment_text"
        ),
        "date_format": "YYYY-MM-DD",
        "human_fields_left_blank": list(HUMAN_FIELDS),
        "source_fragment_count": len(fragments),
        "blinding_policy": {
            "independent_fragment_gold": True,
            "reads_processed_fragments": True,
            "reads_processed_resources": True,
            "reads_processed_competencies": True,
            "reads_bm25_candidates": False,
            "reads_llm_tasks": False,
            "reads_gemini_predictions": False,
            "uses_moodle_activity_links_as_fragment_gold": False,
            "statement": (
                "Template generation reads only processed "
                "fragments, resources and competencies. "
                "It does not read BM25 candidates, LLM "
                "tasks, Gemini predictions, or Moodle "
                "activity-level mappings, and it does not "
                "pre-populate fragment gold labels."
            ),
        },
    }


def human_fields_are_filled(
    rows: Sequence[Mapping[str, Any]],
) -> bool:
    """Return True when any human decision field is non-empty."""

    for row in rows:
        for field in HUMAN_FIELDS:
            if stripped_text(row.get(field)):
                return True

    return False


def assert_allowed_source_path(path: Path) -> None:
    """Reject known prediction and activity-gold filenames."""

    if path.name in FORBIDDEN_SOURCE_NAMES:
        raise ValueError(
            "Annotation generation cannot read "
            f"{path.name}."
        )


def generate_manual_annotation_outputs(
    *,
    fragments_path: Path,
    resources_path: Path,
    competencies_path: Path,
    annotations_path: Path,
    catalogue_path: Path,
    manifest_path: Path,
    overwrite_filled: bool = False,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Generate the blank annotation template and catalogue."""

    assert_allowed_source_path(fragments_path)
    assert_allowed_source_path(resources_path)
    assert_allowed_source_path(competencies_path)

    fragments = load_jsonl(fragments_path)
    resources = load_jsonl(resources_path)
    competencies = load_jsonl(competencies_path)

    if annotations_path.exists() and not overwrite_filled:
        existing_rows = read_csv(annotations_path)

        if human_fields_are_filled(existing_rows):
            raise ValueError(
                "Refusing to overwrite filled annotations "
                f"at {annotations_path}. Pass overwrite "
                "only if this is intentional."
            )

    annotations = build_blank_annotation_records(
        fragments,
        resources,
    )
    catalogue = build_competency_catalogue(competencies)
    manifest = build_annotation_manifest(
        fragments=fragments,
        competencies=competencies,
        annotations=annotations,
        fragments_path=fragments_path,
        resources_path=resources_path,
        competencies_path=competencies_path,
        generated_at=generated_at,
    )

    write_csv(
        annotations,
        annotations_path,
        ANNOTATION_COLUMNS,
    )
    write_csv(
        catalogue,
        catalogue_path,
        CATALOGUE_COLUMNS,
    )
    write_json(manifest, manifest_path)

    return {
        "annotations": annotations,
        "catalogue": catalogue,
        "manifest": manifest,
        "fragments": fragments,
        "resources": resources,
        "competencies": competencies,
    }


def _prefix_errors(
    prefix: str,
    errors: Iterable[str],
) -> list[str]:
    return [f"{prefix}: {error}" for error in errors]


def validate_catalogue(
    catalogue_rows: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate the independent competency catalogue."""

    errors: list[str] = []
    source_ids = [
        stripped_text(item.get("idnumber"))
        for item in competencies
        if stripped_text(item.get("idnumber"))
    ]
    catalogue_ids = [
        stripped_text(item.get("idnumber"))
        for item in catalogue_rows
    ]

    missing_ids = sorted(
        set(source_ids) - set(catalogue_ids)
    )
    unknown_ids = sorted(
        {
            competency_id
            for competency_id in catalogue_ids
            if competency_id
        }
        - set(source_ids)
    )
    duplicate_ids = sorted(
        competency_id
        for competency_id, count in Counter(
            [
                competency_id
                for competency_id in catalogue_ids
                if competency_id
            ]
        ).items()
        if count > 1
    )
    empty_ids = [
        index
        for index, competency_id in enumerate(
            catalogue_ids,
            start=2,
        )
        if not competency_id
    ]

    if missing_ids:
        errors.append(
            "Catalogue is missing competency IDs: "
            + ", ".join(missing_ids)
        )

    if unknown_ids:
        errors.append(
            "Catalogue contains unknown competency IDs: "
            + ", ".join(unknown_ids)
        )

    if duplicate_ids:
        errors.append(
            "Catalogue contains duplicate competency IDs: "
            + ", ".join(duplicate_ids)
        )

    for row_number in empty_ids:
        errors.append(
            f"Catalogue row {row_number} has an empty "
            "idnumber."
        )

    return {
        "expected_competencies": len(source_ids),
        "catalogue_competencies": len(catalogue_ids),
        "missing_catalogue_competencies": missing_ids,
        "unknown_catalogue_competencies": unknown_ids,
        "duplicate_catalogue_competencies": duplicate_ids,
        "errors": errors,
        "passed": not errors,
    }


def validate_annotation_row(
    *,
    row: Mapping[str, Any],
    fragment: Mapping[str, Any] | None,
    resource: Mapping[str, Any] | None,
    allowed_competency_ids: set[str],
    mode: str,
    row_number: int,
) -> dict[str, Any]:
    """Validate one annotation row against source data and mode rules."""

    fragment_id = stripped_text(row.get("fragment_id"))
    prefix = f"Row {row_number}"

    if fragment_id:
        prefix = f"Row {row_number} ({fragment_id})"

    errors: list[str] = []

    if not fragment_id:
        errors.append(f"{prefix}: fragment_id is empty.")

    if fragment is None:
        if fragment_id:
            errors.append(
                f"{prefix}: unknown fragment_id."
            )
        return {
            "fragment_id": fragment_id,
            "errors": errors,
            "source_text_mismatch": False,
            "incomplete": mode == "final",
        }

    expected_text = text_value(fragment, "text")
    actual_text = text_value(row, "fragment_text")
    source_text_mismatch = actual_text != expected_text

    if source_text_mismatch:
        errors.append(
            f"{prefix}: fragment_text does not match the "
            "source fragment exactly."
        )

    expected_resource_id = text_value(
        fragment,
        "resource_id",
    )
    actual_resource_id = text_value(row, "resource_id")

    if actual_resource_id != expected_resource_id:
        errors.append(
            f"{prefix}: resource_id does not match the "
            "source fragment."
        )

    expected_course_id = text_value(fragment, "course_id")
    actual_course_id = text_value(row, "course_id")

    if actual_course_id != expected_course_id:
        errors.append(
            f"{prefix}: course_id does not match the "
            "source fragment."
        )

    expected_course = text_value(
        fragment,
        "course_shortname",
    )
    actual_course = text_value(row, "course_shortname")

    if actual_course != expected_course:
        errors.append(
            f"{prefix}: course_shortname does not match "
            "the source fragment."
        )

    expected_type = text_value(fragment, "resource_type")
    actual_type = text_value(row, "resource_type")

    if actual_type != expected_type:
        errors.append(
            f"{prefix}: resource_type does not match the "
            "source fragment."
        )

    expected_activity = text_value(
        fragment,
        "activity_name",
    )
    actual_activity = text_value(row, "activity_name")

    if actual_activity != expected_activity:
        errors.append(
            f"{prefix}: activity_name does not match the "
            "source fragment."
        )

    expected_title = text_value(fragment, "title")
    actual_title = text_value(row, "resource_title")

    if actual_title != expected_title:
        errors.append(
            f"{prefix}: resource_title does not match the "
            "source fragment title."
        )

    if (
        expected_resource_id
        and resource is None
    ):
        errors.append(
            f"{prefix}: resource_id is not present in "
            "resources.jsonl."
        )

    competency_ids, competency_errors = (
        parse_competency_ids(
            row.get("gold_competency_ids")
        )
    )
    errors.extend(
        _prefix_errors(prefix, competency_errors)
    )

    unknown_ids = sorted(
        {
            competency_id
            for competency_id in competency_ids
            if competency_id not in allowed_competency_ids
        }
    )

    if unknown_ids:
        errors.append(
            f"{prefix}: unknown competency IDs: "
            + ", ".join(unknown_ids)
        )

    evidence_quotes, evidence_errors = parse_evidence(
        row.get("gold_evidence")
    )
    errors.extend(_prefix_errors(prefix, evidence_errors))

    for index, quote in enumerate(
        evidence_quotes,
        start=1,
    ):
        if quote not in expected_text:
            errors.append(
                f"{prefix}: gold_evidence item {index} is "
                "not an exact contiguous substring of "
                "fragment_text."
            )

    no_competency, no_competency_errors = parse_boolean(
        row.get("no_competency"),
        "no_competency",
    )
    errors.extend(
        _prefix_errors(prefix, no_competency_errors)
    )

    ambiguous, ambiguous_errors = parse_boolean(
        row.get("ambiguous"),
        "ambiguous",
    )
    errors.extend(_prefix_errors(prefix, ambiguous_errors))

    if (
        no_competency is True
        and competency_ids
    ):
        errors.append(
            f"{prefix}: no_competency=true cannot coexist "
            "with gold_competency_ids."
        )

    if ambiguous is True and not stripped_text(
        row.get("ambiguity_reason")
    ):
        errors.append(
            f"{prefix}: ambiguous=true requires "
            "ambiguity_reason."
        )

    annotator = stripped_text(row.get("annotator"))
    annotation_date, date_errors = parse_annotation_date(
        row.get("annotation_date")
    )
    errors.extend(_prefix_errors(prefix, date_errors))

    human_started = human_fields_are_filled([row])
    incomplete = False

    if mode == "final":
        if no_competency is None:
            errors.append(
                f"{prefix}: no_competency must be true or "
                "false in final mode."
            )
            incomplete = True

        if (
            no_competency is False
            and not competency_ids
        ):
            errors.append(
                f"{prefix}: no_competency=false requires "
                "one or more gold competency IDs."
            )
            incomplete = True

        if (
            no_competency is not True
            and not competency_ids
        ):
            incomplete = True

            if no_competency is not False:
                errors.append(
                    f"{prefix}: incomplete decision; "
                    "select competency IDs or set "
                    "no_competency=true."
                )

        if ambiguous is None:
            errors.append(
                f"{prefix}: ambiguous must be true or "
                "false in final mode."
            )
            incomplete = True

        if not annotator:
            errors.append(
                f"{prefix}: annotator is required in "
                "final mode."
            )
            incomplete = True

        if annotation_date is None and not date_errors:
            errors.append(
                f"{prefix}: annotation_date is required "
                "in final mode and must use YYYY-MM-DD."
            )
            incomplete = True

    elif human_started and no_competency is False:
        if not competency_ids:
            errors.append(
                f"{prefix}: no_competency=false requires "
                "one or more gold competency IDs."
            )

    return {
        "fragment_id": fragment_id,
        "errors": errors,
        "source_text_mismatch": source_text_mismatch,
        "incomplete": incomplete,
    }


def validate_annotation_dataset(
    *,
    mode: str,
    annotation_rows: Sequence[Mapping[str, Any]],
    catalogue_rows: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate a complete annotation CSV in template or final mode."""

    if mode not in {"template", "final"}:
        raise ValueError(
            "mode must be 'template' or 'final'."
        )

    fragments_by_id = {
        stripped_text(fragment.get("fragment_id")): fragment
        for fragment in fragments
        if stripped_text(fragment.get("fragment_id"))
    }
    resources_by_id = build_resource_lookup(resources)
    allowed_competency_ids = set(
        build_competency_lookup(competencies)
    )

    expected_ids = [
        stripped_text(fragment.get("fragment_id"))
        for fragment in fragments
        if stripped_text(fragment.get("fragment_id"))
    ]
    actual_ids = [
        stripped_text(row.get("fragment_id"))
        for row in annotation_rows
    ]

    duplicate_fragments = sorted(
        fragment_id
        for fragment_id, count in Counter(
            [
                fragment_id
                for fragment_id in actual_ids
                if fragment_id
            ]
        ).items()
        if count > 1
    )
    missing_fragments = [
        fragment_id
        for fragment_id in expected_ids
        if fragment_id not in set(actual_ids)
    ]
    unknown_fragments = sorted(
        {
            fragment_id
            for fragment_id in actual_ids
            if fragment_id
            and fragment_id not in fragments_by_id
        }
    )

    catalogue_summary = validate_catalogue(
        catalogue_rows,
        competencies,
    )

    errors: list[str] = list(catalogue_summary["errors"])
    source_text_mismatches: list[str] = []
    incomplete_rows: list[str] = []
    invalid_fragment_ids: list[str] = []

    if duplicate_fragments:
        errors.append(
            "Duplicate fragment IDs: "
            + ", ".join(duplicate_fragments)
        )

    if missing_fragments:
        errors.append(
            "Missing fragment IDs: "
            + ", ".join(missing_fragments)
        )

    if unknown_fragments:
        errors.append(
            "Unknown fragment IDs: "
            + ", ".join(unknown_fragments)
        )

    seen_ids: set[str] = set()

    for row_number, row in enumerate(
        annotation_rows,
        start=2,
    ):
        fragment_id = stripped_text(row.get("fragment_id"))
        fragment = fragments_by_id.get(fragment_id)
        resource = resources_by_id.get(
            text_value(row, "resource_id")
        )

        if fragment_id and fragment_id in seen_ids:
            continue

        if fragment_id:
            seen_ids.add(fragment_id)

        row_result = validate_annotation_row(
            row=row,
            fragment=fragment,
            resource=resource,
            allowed_competency_ids=allowed_competency_ids,
            mode=mode,
            row_number=row_number,
        )

        errors.extend(row_result["errors"])

        if row_result["source_text_mismatch"]:
            source_text_mismatches.append(fragment_id)

        if row_result["incomplete"]:
            incomplete_rows.append(fragment_id)

        if row_result["errors"]:
            invalid_fragment_ids.append(fragment_id)

    passed = not errors

    return {
        "mode": mode,
        "schema_version": SCHEMA_VERSION,
        "source_fragments": len(fragments),
        "annotation_rows": len(annotation_rows),
        "expected_competencies": catalogue_summary[
            "expected_competencies"
        ],
        "catalogue_competencies": catalogue_summary[
            "catalogue_competencies"
        ],
        "missing_fragments": missing_fragments,
        "unknown_fragments": unknown_fragments,
        "duplicate_fragments": duplicate_fragments,
        "source_text_mismatches": source_text_mismatches,
        "unknown_catalogue_competencies": catalogue_summary[
            "unknown_catalogue_competencies"
        ],
        "missing_catalogue_competencies": catalogue_summary[
            "missing_catalogue_competencies"
        ],
        "incomplete_rows": incomplete_rows,
        "invalid_fragment_ids": [
            fragment_id
            for fragment_id in invalid_fragment_ids
            if fragment_id
        ],
        "errors": errors,
        "passed": passed,
    }


def load_and_validate_manual_annotations(
    *,
    mode: str,
    annotations_path: Path,
    catalogue_path: Path,
    fragments_path: Path,
    resources_path: Path,
    competencies_path: Path,
) -> dict[str, Any]:
    """Load files from disk and validate the annotation dataset."""

    annotation_rows = read_csv(annotations_path)
    catalogue_rows = read_csv(catalogue_path)
    fragments = load_jsonl(fragments_path)
    resources = load_jsonl(resources_path)
    competencies = load_jsonl(competencies_path)

    return validate_annotation_dataset(
        mode=mode,
        annotation_rows=annotation_rows,
        catalogue_rows=catalogue_rows,
        fragments=fragments,
        resources=resources,
        competencies=competencies,
    )
