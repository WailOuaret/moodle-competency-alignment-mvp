"""Create the normalized competency dataset used by retrieval."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from moodle_competency.competency_normalization import (
    normalize_competencies,
    normalize_frameworks,
    read_csv_rows,
    validate_competencies,
    write_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

COMPETENCIES_CSV = (
    PROJECT_ROOT
    / "reports"
    / "sql_raw"
    / "competencies.csv"
)

FRAMEWORK_CSV = (
    PROJECT_ROOT
    / "reports"
    / "sql_raw"
    / "competency_framework.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "competencies.jsonl"
)

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "competencies_manifest.json"
)


EXPECTED_IDNUMBERS = {
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


def main() -> int:
    missing_files = [
        path
        for path in (
            COMPETENCIES_CSV,
            FRAMEWORK_CSV,
        )
        if not path.exists()
    ]

    if missing_files:
        print(
            "ERROR: Required competency files are missing:",
            file=sys.stderr,
        )

        for path in missing_files:
            print(f"- {path}", file=sys.stderr)

        return 1

    try:
        framework_rows = read_csv_rows(
            FRAMEWORK_CSV
        )

        competency_rows = read_csv_rows(
            COMPETENCIES_CSV
        )

        frameworks = normalize_frameworks(
            framework_rows
        )

        competencies = normalize_competencies(
            competency_rows=competency_rows,
            frameworks=frameworks,
        )

        validation = validate_competencies(
            competencies,
            expected_count=13,
            expected_idnumbers=EXPECTED_IDNUMBERS,
        )

        write_jsonl(
            competencies,
            OUTPUT_PATH,
        )

        manifest = {
            "input_files": {
                "competencies_csv": str(
                    COMPETENCIES_CSV.relative_to(
                        PROJECT_ROOT
                    )
                ),
                "framework_csv": str(
                    FRAMEWORK_CSV.relative_to(
                        PROJECT_ROOT
                    )
                ),
            },
            "output_file": str(
                OUTPUT_PATH.relative_to(PROJECT_ROOT)
            ),
            "source_rows": {
                "framework_rows":
                    len(framework_rows),
                "competency_rows":
                    len(competency_rows),
            },
            "validation": validation,
        }

        MANIFEST_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        MANIFEST_PATH.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    print("=== COMPETENCY NORMALIZATION ===")
    print(
        "Source competency rows: "
        f"{len(competency_rows)}"
    )
    print(
        "Total competencies: "
        f"{validation['total_competencies']}"
    )
    print(
        "Frameworks represented: "
        f"{validation['framework_count']}"
    )
    print(
        "Top-level competencies: "
        f"{validation['top_level_competencies']}"
    )

    print("\nCompetencies by depth:")
    for depth, count in validation[
        "competencies_by_depth"
    ].items():
        print(f"- Depth {depth}: {count}")

    print(
        "\nMissing competency IDs: "
        f"{len(validation['missing_competency_ids'])}"
    )
    print(
        "Missing idnumbers: "
        f"{len(validation['missing_idnumbers'])}"
    )
    print(
        "Empty searchable texts: "
        f"{len(validation['empty_full_text'])}"
    )
    print(
        "Duplicate competency IDs: "
        f"{len(validation['duplicate_competency_ids'])}"
    )
    print(
        "Duplicate idnumbers: "
        f"{len(validation['duplicate_idnumbers'])}"
    )
    print(
        "Hierarchy cycles: "
        f"{len(validation['hierarchy_cycles'])}"
    )
    print(
        "Missing parent references: "
        f"{len(validation['missing_parent_references'])}"
    )
    print(
        "Missing expected idnumbers: "
        f"{len(validation['missing_expected_idnumbers'])}"
    )
    print(
        "Unexpected idnumbers: "
        f"{len(validation['unexpected_idnumbers'])}"
    )

    print(f"\nDataset: {OUTPUT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")

    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
