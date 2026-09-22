"""Normalize Moodle competency-framework data into searchable records."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.html_clean import (
    combine_text,
    html_to_text,
    normalize_whitespace,
)


KEY_PATTERN = re.compile(r"[^a-z0-9]+")


def canonical_key(value: str) -> str:
    """Convert a CSV column name into a predictable key."""

    return KEY_PATTERN.sub(
        "_",
        value.strip().lower(),
    ).strip("_")


def canonical_row(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize all column names in one CSV row."""

    return {
        canonical_key(str(key)): value
        for key, value in row.items()
        if key is not None
    }


def first_value(
    row: Mapping[str, Any],
    *keys: str,
) -> Any:
    """Return the first non-empty value matching the supplied keys."""

    for key in keys:
        value = row.get(canonical_key(key))

        if value is not None and str(value).strip():
            return value

    return None


def optional_integer(value: Any) -> int | None:
    """Convert a value to an integer when possible."""

    if value is None or not str(value).strip():
        return None

    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def read_csv_rows(
    path: Path,
) -> list[dict[str, Any]]:
    """Read a UTF-8 CSV and normalize its column names."""

    if not path.exists():
        raise FileNotFoundError(
            f"Required CSV does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return [
            canonical_row(row)
            for row in csv.DictReader(handle)
        ]


def normalize_frameworks(
    framework_rows: Iterable[Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Index competency frameworks by Moodle framework ID."""

    frameworks: dict[int, dict[str, Any]] = {}

    for raw_row in framework_rows:
        row = canonical_row(raw_row)

        framework_id = optional_integer(
            first_value(
                row,
                "framework_id",
                "competency_framework_id",
                "competencyframeworkid",
                "id",
            )
        )

        if framework_id is None:
            continue

        frameworks[framework_id] = {
            "framework_id": framework_id,
            "framework_idnumber": normalize_whitespace(
                first_value(
                    row,
                    "framework_idnumber",
                    "idnumber",
                )
            ),
            "framework_shortname": normalize_whitespace(
                first_value(
                    row,
                    "framework_shortname",
                    "shortname",
                    "name",
                )
            ),
            "framework_description": html_to_text(
                first_value(
                    row,
                    "framework_description",
                    "description",
                )
            ),
            "scale_id": optional_integer(
                first_value(
                    row,
                    "scale_id",
                    "scaleid",
                )
            ),
            "visible": optional_integer(
                first_value(row, "visible")
            ),
        }

    return frameworks


def normalize_competencies(
    *,
    competency_rows: Iterable[Mapping[str, Any]],
    frameworks: Mapping[int, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize Moodle competency rows and resolve their hierarchy."""

    prepared_rows: list[dict[str, Any]] = []

    for raw_row in competency_rows:
        row = canonical_row(raw_row)

        competency_id = optional_integer(
            first_value(
                row,
                "competency_id",
                "id",
            )
        )

        if competency_id is None:
            continue

        framework_id = optional_integer(
            first_value(
                row,
                "framework_id",
                "competency_framework_id",
                "competencyframeworkid",
            )
        )

        parent_id = optional_integer(
            first_value(
                row,
                "parent_competency_id",
                "parent_id",
                "parentid",
                "parent",
            )
        )

        if parent_id == 0:
            parent_id = None

        prepared_rows.append(
            {
                "competency_id": competency_id,
                "framework_id": framework_id,
                "parent_competency_id": parent_id,
                "idnumber": normalize_whitespace(
                    first_value(row, "idnumber")
                ),
                "shortname": normalize_whitespace(
                    first_value(
                        row,
                        "shortname",
                        "name",
                    )
                ),
                "description_raw": (
                    str(
                        first_value(
                            row,
                            "description",
                            "description_raw",
                        )
                        or ""
                    )
                ),
                "sortorder": optional_integer(
                    first_value(
                        row,
                        "sortorder",
                        "sort_order",
                    )
                ),
                "path_raw": normalize_whitespace(
                    first_value(row, "path")
                ),
                "description_format": optional_integer(
                    first_value(
                        row,
                        "descriptionformat",
                        "description_format",
                    )
                ),
                "rule_type": normalize_whitespace(
                    first_value(
                        row,
                        "ruletype",
                        "rule_type",
                    )
                ),
                "rule_outcome": optional_integer(
                    first_value(
                        row,
                        "ruleoutcome",
                        "rule_outcome",
                    )
                ),
                "time_created": optional_integer(
                    first_value(
                        row,
                        "timecreated",
                        "time_created",
                    )
                ),
                "time_modified": optional_integer(
                    first_value(
                        row,
                        "timemodified",
                        "time_modified",
                    )
                ),
            }
        )

    by_id = {
        row["competency_id"]: row
        for row in prepared_rows
    }

    resources: list[dict[str, Any]] = []

    for row in prepared_rows:
        competency_id = row["competency_id"]
        parent_id = row["parent_competency_id"]

        ancestor_rows: list[dict[str, Any]] = []
        visited: set[int] = {competency_id}
        hierarchy_cycle = False
        missing_parent_reference = False

        current_parent_id = parent_id

        while current_parent_id is not None:
            if current_parent_id in visited:
                hierarchy_cycle = True
                break

            visited.add(current_parent_id)

            parent = by_id.get(current_parent_id)

            if parent is None:
                missing_parent_reference = True
                break

            ancestor_rows.append(parent)
            current_parent_id = parent[
                "parent_competency_id"
            ]

        ancestor_rows.reverse()

        parent = (
            by_id.get(parent_id)
            if parent_id is not None
            else None
        )

        framework_id = row["framework_id"]
        framework = (
            frameworks.get(framework_id, {})
            if framework_id is not None
            else {}
        )

        idnumber = row["idnumber"]
        shortname = row["shortname"]
        description_text = html_to_text(
            row["description_raw"]
        )

        hierarchy_idnumbers = [
            ancestor["idnumber"]
            for ancestor in ancestor_rows
            if ancestor["idnumber"]
        ] + ([idnumber] if idnumber else [])

        hierarchy_labels = [
            ancestor["shortname"]
            for ancestor in ancestor_rows
            if ancestor["shortname"]
        ] + ([shortname] if shortname else [])

        ancestor_context = " > ".join(
            hierarchy_labels[:-1]
        )

        full_text = combine_text(
            idnumber,
            shortname,
            description_text,
        )

        search_text = combine_text(
            framework.get("framework_shortname"),
            ancestor_context,
            full_text,
        )

        resources.append(
            {
                "competency_id": competency_id,
                "idnumber": idnumber,
                "shortname": shortname,
                "description_raw": row[
                    "description_raw"
                ],
                "description_text": description_text,
                "full_text": full_text,
                "search_text": search_text,
                "framework_id": framework_id,
                "framework_idnumber": framework.get(
                    "framework_idnumber",
                    "",
                ),
                "framework_shortname": framework.get(
                    "framework_shortname",
                    "",
                ),
                "parent_competency_id": parent_id,
                "parent_idnumber": (
                    parent["idnumber"]
                    if parent
                    else ""
                ),
                "parent_shortname": (
                    parent["shortname"]
                    if parent
                    else ""
                ),
                "depth": len(ancestor_rows),
                "hierarchy_idnumbers":
                    hierarchy_idnumbers,
                "hierarchy_labels":
                    hierarchy_labels,
                "sortorder": row["sortorder"],
                "source_extraction":
                    "postgresql_read_only",
                "normalization_version": "1.0",
                "metadata": {
                    "path_raw": row["path_raw"],
                    "description_format":
                        row["description_format"],
                    "rule_type": row["rule_type"],
                    "rule_outcome":
                        row["rule_outcome"],
                    "time_created":
                        row["time_created"],
                    "time_modified":
                        row["time_modified"],
                    "hierarchy_cycle":
                        hierarchy_cycle,
                    "missing_parent_reference":
                        missing_parent_reference,
                },
            }
        )

    return sorted(
        resources,
        key=lambda record: (
            record["framework_id"] or 0,
            record["idnumber"],
            record["competency_id"],
        ),
    )


def validate_competencies(
    competencies: Sequence[Mapping[str, Any]],
    *,
    expected_count: int | None = None,
    expected_idnumbers: set[str] | None = None,
) -> dict[str, Any]:
    """Validate identifiers, text, hierarchy and framework membership."""

    competency_ids = [
        record.get("competency_id")
        for record in competencies
    ]

    idnumbers = [
        str(record.get("idnumber", "")).strip()
        for record in competencies
    ]

    id_counter = Counter(competency_ids)
    idnumber_counter = Counter(idnumbers)

    duplicate_ids = sorted(
        competency_id
        for competency_id, count in id_counter.items()
        if competency_id is not None and count > 1
    )

    duplicate_idnumbers = sorted(
        idnumber
        for idnumber, count in idnumber_counter.items()
        if idnumber and count > 1
    )

    missing_competency_ids = [
        index
        for index, record in enumerate(competencies)
        if record.get("competency_id") is None
    ]

    missing_idnumbers = [
        record.get("competency_id")
        for record in competencies
        if not str(
            record.get("idnumber", "")
        ).strip()
    ]

    empty_full_text = [
        record.get("idnumber")
        or record.get("competency_id")
        for record in competencies
        if not str(
            record.get("full_text", "")
        ).strip()
    ]

    hierarchy_cycles = [
        record.get("idnumber")
        or record.get("competency_id")
        for record in competencies
        if record.get("metadata", {}).get(
            "hierarchy_cycle"
        )
    ]

    missing_parent_references = [
        record.get("idnumber")
        or record.get("competency_id")
        for record in competencies
        if record.get("metadata", {}).get(
            "missing_parent_reference"
        )
    ]

    framework_ids = {
        record.get("framework_id")
        for record in competencies
        if record.get("framework_id") is not None
    }

    depth_counts = Counter(
        int(record.get("depth", 0))
        for record in competencies
    )

    top_level_count = sum(
        record.get("parent_competency_id") is None
        for record in competencies
    )

    actual_idnumbers = {
        idnumber
        for idnumber in idnumbers
        if idnumber
    }

    missing_expected_idnumbers: list[str] = []
    unexpected_idnumbers: list[str] = []

    if expected_idnumbers is not None:
        missing_expected_idnumbers = sorted(
            expected_idnumbers - actual_idnumbers
        )

        unexpected_idnumbers = sorted(
            actual_idnumbers - expected_idnumbers
        )

    count_matches = (
        expected_count is None
        or len(competencies) == expected_count
    )

    passed = (
        count_matches
        and not missing_competency_ids
        and not missing_idnumbers
        and not empty_full_text
        and not duplicate_ids
        and not duplicate_idnumbers
        and not hierarchy_cycles
        and not missing_parent_references
        and not missing_expected_idnumbers
        and not unexpected_idnumbers
        and len(framework_ids) == 1
    )

    return {
        "total_competencies": len(competencies),
        "expected_count": expected_count,
        "framework_count": len(framework_ids),
        "framework_ids": sorted(framework_ids),
        "top_level_competencies": top_level_count,
        "competencies_by_depth": {
            str(depth): count
            for depth, count in sorted(
                depth_counts.items()
            )
        },
        "missing_competency_ids":
            missing_competency_ids,
        "missing_idnumbers": missing_idnumbers,
        "empty_full_text": empty_full_text,
        "duplicate_competency_ids":
            duplicate_ids,
        "duplicate_idnumbers":
            duplicate_idnumbers,
        "hierarchy_cycles":
            hierarchy_cycles,
        "missing_parent_references":
            missing_parent_references,
        "missing_expected_idnumbers":
            missing_expected_idnumbers,
        "unexpected_idnumbers":
            unexpected_idnumbers,
        "passed": passed,
    }


def write_jsonl(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
) -> Path:
    """Write competency records as UTF-8 JSON Lines."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(
                    dict(record),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    return output_path.resolve()
