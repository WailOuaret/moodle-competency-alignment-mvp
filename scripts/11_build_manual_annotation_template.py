"""Generate a blinded blank fragment-level annotation template."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from moodle_competency.annotation import (
    generate_manual_annotation_outputs,
    load_and_validate_manual_annotations,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

FRAGMENTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fragments.jsonl"
)

RESOURCES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "resources.jsonl"
)

COMPETENCIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "competencies.jsonl"
)

ANNOTATIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "manual_fragment_annotations.csv"
)

CATALOGUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "annotation_competency_catalogue.csv"
)

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "manual_annotation_manifest.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a blinded blank fragment annotation "
            "template from processed Moodle resources. "
            "This script never reads BM25 or Gemini files."
        )
    )
    parser.add_argument(
        "--overwrite-filled",
        action="store_true",
        help=(
            "Overwrite an annotation CSV that already "
            "contains human decisions. Default is to "
            "refuse."
        ),
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        generated = generate_manual_annotation_outputs(
            fragments_path=FRAGMENTS_PATH,
            resources_path=RESOURCES_PATH,
            competencies_path=COMPETENCIES_PATH,
            annotations_path=ANNOTATIONS_PATH,
            catalogue_path=CATALOGUE_PATH,
            manifest_path=MANIFEST_PATH,
            overwrite_filled=arguments.overwrite_filled,
        )

        validation = load_and_validate_manual_annotations(
            mode="template",
            annotations_path=ANNOTATIONS_PATH,
            catalogue_path=CATALOGUE_PATH,
            fragments_path=FRAGMENTS_PATH,
            resources_path=RESOURCES_PATH,
            competencies_path=COMPETENCIES_PATH,
        )
    except (
        FileNotFoundError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    manifest = generated["manifest"]
    filled_labels = sum(
        1
        for row in generated["annotations"]
        if row["gold_competency_ids"].strip()
        or row["gold_evidence"].strip()
        or row["no_competency"].strip()
    )

    print("=== BLINDED MANUAL ANNOTATION TEMPLATE ===")
    print(f"Source fragments: {manifest['source_fragment_count']}")
    print(f"Annotation rows: {manifest['fragment_count']}")
    print(f"Competency catalogue: {manifest['competency_count']}")
    print(f"Gold labels automatically filled: {filled_labels}")
    print()
    print("Course counts:")

    for course, count in manifest["course_counts"].items():
        print(f"- {course}: {count}")

    print()
    print("Resource type counts:")

    for resource_type, count in manifest[
        "resource_type_counts"
    ].items():
        print(f"- {resource_type}: {count}")

    print()
    print(f"Annotations: {ANNOTATIONS_PATH}")
    print(f"Catalogue: {CATALOGUE_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    print()
    print(
        "Blinding: BM25, LLM tasks, Gemini outputs and "
        "Moodle activity-level links were not read."
    )
    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    if not validation["passed"]:
        print()
        print("Validation errors:")

        for error in validation["errors"]:
            print(f"- {error}")

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
