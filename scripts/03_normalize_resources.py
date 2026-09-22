"""Build a unified dataset of Moodle Pages and Quiz questions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from moodle_competency.normalization import (
    build_course_lookup,
    build_module_indexes,
    load_json,
    normalize_pages,
    normalize_quiz_questions,
    read_quiz_rows,
    validate_resources,
    write_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "data" / "raw" / "api"
SQL_DIR = PROJECT_ROOT / "data" / "raw" / "sql"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def main() -> int:
    required_paths = [
        API_DIR / "courses.json",
        API_DIR / "course_contents_MVP-SW.json",
        API_DIR / "course_contents_MVP-DATA.json",
        API_DIR / "pages_by_courses.json",
        SQL_DIR / "quiz_questions_answers.csv",
    ]

    missing = [
        path
        for path in required_paths
        if not path.exists()
    ]

    if missing:
        print(
            "ERROR: Required input files are missing:",
            file=sys.stderr,
        )

        for path in missing:
            print(f"- {path}", file=sys.stderr)

        return 1

    courses_response = load_json(
        API_DIR / "courses.json"
    )
    courses = build_course_lookup(
        courses_response
    )

    shortname_to_id = {
        course["shortname"]: course_id
        for course_id, course in courses.items()
    }

    course_contents = {
        shortname_to_id["MVP-SW"]: load_json(
            API_DIR / "course_contents_MVP-SW.json"
        ),
        shortname_to_id["MVP-DATA"]: load_json(
            API_DIR / "course_contents_MVP-DATA.json"
        ),
    }

    (
        modules_by_cmid,
        modules_by_instance,
    ) = build_module_indexes(course_contents)

    pages = normalize_pages(
        pages_response=load_json(
            API_DIR / "pages_by_courses.json"
        ),
        courses=courses,
        modules_by_cmid=modules_by_cmid,
        modules_by_instance=modules_by_instance,
    )

    quiz_questions = normalize_quiz_questions(
        rows=read_quiz_rows(
            SQL_DIR / "quiz_questions_answers.csv"
        ),
        courses=courses,
        modules_by_cmid=modules_by_cmid,
        modules_by_instance=modules_by_instance,
    )

    resources = sorted(
        pages + quiz_questions,
        key=lambda resource: (
            resource["course_id"],
            resource["resource_type"],
            resource["activity_id"],
            resource["source_item_id"],
        ),
    )

    validation = validate_resources(resources)

    output_path = (
        PROCESSED_DIR / "resources.jsonl"
    )

    manifest_path = (
        PROCESSED_DIR
        / "resources_manifest.json"
    )

    write_jsonl(resources, output_path)

    manifest_path.write_text(
        json.dumps(
            validation,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("=== RESOURCE NORMALIZATION ===")
    print(
        f"Total resources: "
        f"{validation['total_resources']}"
    )

    print("\nResources by type:")
    for name, count in sorted(
        validation["resource_types"].items()
    ):
        print(f"- {name}: {count}")

    print("\nResources by course:")
    for name, count in sorted(
        validation[
            "resources_per_course"
        ].items()
    ):
        print(f"- {name}: {count}")

    print(
        "\nEmpty text resources: "
        f"{len(validation['empty_text_resources'])}"
    )
    print(
        "Missing course-module IDs: "
        f"{len(validation['missing_course_module_resources'])}"
    )
    print(
        "Duplicate resource IDs: "
        f"{validation['duplicate_resource_ids']}"
    )
    print(
        "Invalid Quiz answer structures: "
        f"{len(validation['invalid_quiz_answer_resources'])}"
    )

    print(f"\nDataset: {output_path}")
    print(f"Manifest: {manifest_path}")

    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
