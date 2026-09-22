from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "utc_gi_mvp_moodle.csv"
)

TEMPLATE_PATH = (
    PROJECT_ROOT
    / "data"
    / "templates"
    / "moodle_5_2_framework_template.csv"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "moodle_csv_validation_report.txt"
)

EXPECTED_FRAMEWORK_ID = "UTC_GI_MVP_2026"

EXPECTED_COMPETENCY_IDS = {
    "GI_C1",
    "GI_C1_1",
    "GI_C1_2",
    "GI_C1_3",
    "GI_C1_4",
    "GI_C2",
    "GI_C2_1",
    "GI_C2_2",
    "GI_C2_3",
    "GI_C3",
    "GI_C3_1",
    "GI_C3_2",
    "GI_C3_3",
}

EXPECTED_ROOT_IDS = {
    "GI_C1",
    "GI_C2",
    "GI_C3",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")

        rows = list(reader)

    return reader.fieldnames, rows


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []

    header, rows = read_csv(CSV_PATH)
    template_header, template_rows = read_csv(TEMPLATE_PATH)

    if header != template_header:
        errors.append(
            "Generated CSV header does not exactly match "
            "the Moodle-exported template."
        )

    if len(header) != 14:
        errors.append(
            f"Expected 14 columns, found {len(header)}."
        )

    if len(rows) != 14:
        errors.append(
            f"Expected 14 data rows, found {len(rows)}."
        )

    framework_rows = [
        row
        for row in rows
        if row.get("Is framework", "").strip() == "1"
    ]

    competency_rows = [
        row
        for row in rows
        if row.get("Is framework", "").strip() != "1"
    ]

    if len(framework_rows) != 1:
        errors.append(
            f"Expected one framework row, found {len(framework_rows)}."
        )

    if len(competency_rows) != 13:
        errors.append(
            f"Expected 13 competency rows, found {len(competency_rows)}."
        )

    all_ids = [
        row.get("ID number", "").strip()
        for row in rows
    ]

    empty_ids = [
        index
        for index, value in enumerate(all_ids, start=1)
        if not value
    ]

    if empty_ids:
        errors.append(
            f"Rows with empty ID numbers: {empty_ids}"
        )

    duplicate_ids = sorted(
        {
            value
            for value in all_ids
            if all_ids.count(value) > 1
        }
    )

    if duplicate_ids:
        errors.append(
            f"Duplicate ID numbers: {duplicate_ids}"
        )

    if framework_rows:
        framework = framework_rows[0]

        if framework.get("ID number", "").strip() != EXPECTED_FRAMEWORK_ID:
            errors.append(
                "Unexpected framework ID: "
                f"{framework.get('ID number', '')!r}"
            )

        if framework.get("Parent ID number", "").strip():
            errors.append(
                "Framework row must not have a parent ID."
            )

        if not framework.get("Scale values", "").strip():
            errors.append(
                "Framework row has no scale values."
            )

        scale_configuration = framework.get(
            "Scale configuration",
            "",
        ).strip()

        if not scale_configuration:
            errors.append(
                "Framework row has no scale configuration."
            )
        else:
            try:
                parsed_scale = json.loads(scale_configuration)
            except json.JSONDecodeError as error:
                errors.append(
                    f"Scale configuration is invalid JSON: {error}"
                )
            else:
                if not isinstance(parsed_scale, list):
                    errors.append(
                        "Scale configuration must be a JSON list."
                    )

        taxonomy = framework.get("Taxonomy", "").strip()

        if not taxonomy:
            errors.append(
                "Framework taxonomy is empty."
            )

    competency_ids = {
        row.get("ID number", "").strip()
        for row in competency_rows
    }

    missing_competencies = sorted(
        EXPECTED_COMPETENCY_IDS - competency_ids
    )

    unexpected_competencies = sorted(
        competency_ids - EXPECTED_COMPETENCY_IDS
    )

    if missing_competencies:
        errors.append(
            f"Missing competency IDs: {missing_competencies}"
        )

    if unexpected_competencies:
        errors.append(
            f"Unexpected competency IDs: {unexpected_competencies}"
        )

    row_position = {
        row.get("ID number", "").strip(): position
        for position, row in enumerate(rows)
    }

    detected_roots: set[str] = set()

    for row in competency_rows:
        competency_id = row.get("ID number", "").strip()
        parent_id = row.get("Parent ID number", "").strip()

        if not row.get("Short name", "").strip():
            errors.append(
                f"{competency_id}: short name is empty."
            )

        if not row.get("Description", "").strip():
            errors.append(
                f"{competency_id}: description is empty."
            )

        if row.get("Description format", "").strip() != "1":
            errors.append(
                f"{competency_id}: description format is not 1."
            )

        if row.get("Scale values", "").strip():
            errors.append(
                f"{competency_id}: should inherit scale values "
                "from the framework."
            )

        if row.get("Scale configuration", "").strip():
            errors.append(
                f"{competency_id}: should inherit scale configuration "
                "from the framework."
            )

        if parent_id:
            if parent_id not in competency_ids:
                errors.append(
                    f"{competency_id}: parent {parent_id} "
                    "does not exist."
                )
            elif row_position[parent_id] >= row_position[competency_id]:
                errors.append(
                    f"{competency_id}: parent {parent_id} "
                    "must appear before its child."
                )
        else:
            detected_roots.add(competency_id)

    if detected_roots != EXPECTED_ROOT_IDS:
        errors.append(
            "Unexpected root competency IDs. "
            f"Expected {sorted(EXPECTED_ROOT_IDS)}, "
            f"found {sorted(detected_roots)}."
        )

    parent_child_pairs = [
        (
            row.get("Parent ID number", "").strip(),
            row.get("ID number", "").strip(),
        )
        for row in competency_rows
        if row.get("Parent ID number", "").strip()
    ]

    report_lines = [
        "=== MOODLE COMPETENCY CSV VALIDATION ===",
        f"File: {CSV_PATH}",
        f"Columns: {len(header)}",
        f"Total data rows: {len(rows)}",
        f"Framework rows: {len(framework_rows)}",
        f"Competency rows: {len(competency_rows)}",
        f"Root competencies: {len(detected_roots)}",
        f"Child competencies: {len(parent_child_pairs)}",
        f"Root IDs: {', '.join(sorted(detected_roots))}",
        "",
        "Parent-child relationships:",
    ]

    for parent_id, child_id in parent_child_pairs:
        report_lines.append(
            f"- {parent_id} -> {child_id}"
        )

    if warnings:
        report_lines.extend(
            [
                "",
                "Warnings:",
                *[f"- {warning}" for warning in warnings],
            ]
        )

    if errors:
        report_lines.extend(
            [
                "",
                "Errors:",
                *[f"- {error}" for error in errors],
                "",
                "Status: FAILED",
            ]
        )
    else:
        report_lines.extend(
            [
                "",
                "Header matches Moodle template: YES",
                "All IDs unique: YES",
                "All parents exist: YES",
                "All parents precede children: YES",
                "Framework scale configuration present: YES",
                "Status: PASSED",
            ]
        )

    REPORT_PATH.write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(report_lines))

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
