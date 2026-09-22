"""Validate blinded fragment-level manual annotations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from moodle_competency.annotation import (
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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the blinded fragment annotation "
            "CSV in template or final mode."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("template", "final"),
        required=True,
        help=(
            "template: blank or in-progress sheet. "
            "final: every fragment must have a human "
            "decision."
        ),
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=ANNOTATIONS_PATH,
        help="Annotation CSV path.",
    )
    parser.add_argument(
        "--catalogue",
        type=Path,
        default=CATALOGUE_PATH,
        help="Competency catalogue CSV path.",
    )
    return parser.parse_args()


def print_summary(validation: dict) -> None:
    mode = validation["mode"]

    if mode == "template":
        print("=== MANUAL ANNOTATION TEMPLATE VALIDATION ===")
    else:
        print("=== MANUAL ANNOTATION FINAL VALIDATION ===")

    print(f"Source fragments: {validation['source_fragments']}")
    print(f"Annotation rows: {validation['annotation_rows']}")
    print(
        "Expected competencies: "
        f"{validation['expected_competencies']}"
    )
    print(
        "Catalogue competencies: "
        f"{validation['catalogue_competencies']}"
    )
    print()
    print(
        "Missing fragments: "
        f"{len(validation['missing_fragments'])}"
    )
    print(
        "Unknown fragments: "
        f"{len(validation['unknown_fragments'])}"
    )
    print(
        "Duplicate fragments: "
        f"{len(validation['duplicate_fragments'])}"
    )
    print(
        "Source-text mismatches: "
        f"{len(validation['source_text_mismatches'])}"
    )
    print(
        "Unknown catalogue competencies: "
        f"{len(validation['unknown_catalogue_competencies'])}"
    )

    if mode == "final":
        print(
            "Incomplete rows: "
            f"{len(validation['incomplete_rows'])}"
        )

    print()
    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    if validation["errors"]:
        print()
        print("Validation errors:")

        for error in validation["errors"]:
            print(f"- {error}")


def main() -> int:
    arguments = parse_arguments()

    try:
        validation = load_and_validate_manual_annotations(
            mode=arguments.mode,
            annotations_path=arguments.annotations.resolve(),
            catalogue_path=arguments.catalogue.resolve(),
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

    print_summary(validation)
    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
