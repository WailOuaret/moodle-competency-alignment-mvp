from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_PATH = (
    PROJECT_ROOT
    / "data"
    / "templates"
    / "moodle_5_2_framework_template.csv"
)

SUBSET_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "competencies_subset.jsonl"
)

SELECTED_IDS_PATH = (
    PROJECT_ROOT
    / "configs"
    / "selected_competency_ids.txt"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "utc_gi_mvp_moodle.csv"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "moodle_csv_generation_report.txt"
)


def read_template() -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Read Moodle's exported CSV and locate its two template rows."""

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Moodle CSV template was not found: {TEMPLATE_PATH}"
        )

    with TEMPLATE_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError("The Moodle template has no CSV header.")

        fieldnames = reader.fieldnames
        rows = list(reader)

    framework_rows = [
        row for row in rows
        if row.get("Is framework", "").strip() == "1"
    ]

    competency_rows = [
        row for row in rows
        if row.get("Is framework", "").strip() != "1"
    ]

    if len(framework_rows) != 1:
        raise ValueError(
            "Expected exactly one framework record in the template."
        )

    if not competency_rows:
        raise ValueError(
            "The template does not contain a competency record."
        )

    return fieldnames, framework_rows[0], competency_rows[0]


def read_selected_ids() -> list[str]:
    """Read the selected competency IDs while preserving their order."""

    if not SELECTED_IDS_PATH.exists():
        raise FileNotFoundError(
            f"Selected-ID file was not found: {SELECTED_IDS_PATH}"
        )

    selected_ids = [
        line.strip()
        for line in SELECTED_IDS_PATH.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    if not selected_ids:
        raise ValueError("No selected competency IDs were found.")

    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("The selected-ID file contains duplicates.")

    return selected_ids


def read_competencies() -> dict[str, dict[str, Any]]:
    """Read the selected UTC competency JSONL records."""

    if not SUBSET_PATH.exists():
        raise FileNotFoundError(
            f"Competency subset was not found: {SUBSET_PATH}"
        )

    competencies: dict[str, dict[str, Any]] = {}

    with SUBSET_PATH.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error}"
                ) from error

            competency_id = str(
                record.get("competency_id", "")
            ).strip()

            if not competency_id:
                raise ValueError(
                    f"Missing competency_id on line {line_number}."
                )

            if competency_id in competencies:
                raise ValueError(
                    f"Duplicate competency ID: {competency_id}"
                )

            competencies[competency_id] = record

    return competencies


def build_description(record: dict[str, Any]) -> str:
    """Create a traceable bilingual Moodle HTML description."""

    description_fr = html.escape(
        str(record.get("description", "")).strip()
    )

    label_en = html.escape(
        str(record.get("label_en", "")).strip()
    )

    competency_id = html.escape(
        str(record.get("competency_id", "")).strip()
    )

    uri = html.escape(
        str(record.get("uri", "")).strip()
    )

    sections = []

    if description_fr:
        sections.append(f"<p>{description_fr}</p>")

    if label_en:
        sections.append(
            f"<p><strong>English label:</strong> {label_en}</p>"
        )

    sections.append(
        f"<p><strong>UTC competency ID:</strong> {competency_id}</p>"
    )

    if uri:
        sections.append(
            f"<p><strong>Source URI:</strong> {uri}</p>"
        )

    return "".join(sections)


def get_selected_parent(
    record: dict[str, Any],
    selected_id_set: set[str],
) -> str:
    """Return the selected parent ID, or an empty string for root nodes."""

    neighbors = record.get("neighbors", {})
    parent_ids = neighbors.get("parent", [])

    if not isinstance(parent_ids, list):
        raise ValueError(
            f"Invalid parent list for {record['competency_id']}."
        )

    selected_parents = [
        str(parent_id)
        for parent_id in parent_ids
        if str(parent_id) in selected_id_set
    ]

    if len(selected_parents) > 1:
        raise ValueError(
            f"{record['competency_id']} has multiple selected parents: "
            f"{selected_parents}"
        )

    return selected_parents[0] if selected_parents else ""


def main() -> None:
    fieldnames, framework_template, competency_template = read_template()
    selected_ids = read_selected_ids()
    competencies = read_competencies()

    selected_id_set = set(selected_ids)

    missing_ids = [
        competency_id
        for competency_id in selected_ids
        if competency_id not in competencies
    ]

    unexpected_ids = [
        competency_id
        for competency_id in competencies
        if competency_id not in selected_id_set
    ]

    if missing_ids:
        raise ValueError(
            f"Selected IDs missing from the subset: {missing_ids}"
        )

    if unexpected_ids:
        raise ValueError(
            f"Unexpected IDs in the subset: {unexpected_ids}"
        )

    output_rows: list[dict[str, str]] = []

    # Reuse the exact Moodle-generated framework defaults,
    # especially the scale configuration and taxonomy.
    framework_row = framework_template.copy()

    framework_row.update(
        {
            "Parent ID number": "",
            "ID number": "UTC_GI_MVP_2026",
            "Short name": "UTC GI Competency Framework - MVP",
            "Description": (
                "<p>Reduced UTC Computer Science competency framework "
                "prepared for the Moodle competency-alignment MVP.</p>"
                "<p>The framework contains 13 selected competencies "
                "from the GI_C1, GI_C2 and GI_C3 branches.</p>"
            ),
            "Description format": "1",
            "Rule type (optional)": "",
            "Rule outcome (optional)": "",
            "Rule config (optional)": "",
            "Cross-referenced competency ID numbers": "",
            "Exported ID (optional)": "",
            "Is framework": "1",
        }
    )

    output_rows.append(framework_row)

    for competency_id in selected_ids:
        record = competencies[competency_id]

        label_fr = str(
            record.get("label_fr")
            or record.get("label")
            or competency_id
        ).strip()

        parent_id = get_selected_parent(
            record,
            selected_id_set,
        )

        # Reuse Moodle's exported competency defaults.
        competency_row = competency_template.copy()

        competency_row.update(
            {
                "Parent ID number": parent_id,
                "ID number": competency_id,
                "Short name": label_fr,
                "Description": build_description(record),
                "Description format": "1",

                # Competencies inherit the framework scale.
                "Scale values": "",
                "Scale configuration": "",

                "Cross-referenced competency ID numbers": "",
                "Exported ID (optional)": "",
                "Is framework": "",
                "Taxonomy": "",
            }
        )

        output_rows.append(competency_row)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="raise",
        )

        writer.writeheader()
        writer.writerows(output_rows)

    root_ids = [
        competency_id
        for competency_id in selected_ids
        if not get_selected_parent(
            competencies[competency_id],
            selected_id_set,
        )
    ]

    child_count = len(selected_ids) - len(root_ids)

    report_lines = [
        "=== MOODLE COMPETENCY CSV GENERATION ===",
        f"Template: {TEMPLATE_PATH}",
        f"Source subset: {SUBSET_PATH}",
        f"Output: {OUTPUT_PATH}",
        f"CSV columns: {len(fieldnames)}",
        f"Framework records: 1",
        f"Competency records: {len(selected_ids)}",
        f"Root competencies: {len(root_ids)}",
        f"Child competencies: {child_count}",
        f"Total data rows: {len(output_rows)}",
        f"Root IDs: {', '.join(root_ids)}",
        "Status: SUCCESS",
    ]

    REPORT_PATH.write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
