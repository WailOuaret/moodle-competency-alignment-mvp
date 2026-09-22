"""Prepare a blank pedagogical evidence-review sheet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from moodle_competency.aggregation import completeness_report
from moodle_competency.annotation import load_jsonl
from moodle_competency.evidence_review import (
    build_evidence_review_rows,
    write_evidence_review,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS = PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl"
FRAGMENTS = PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
OUTPUT = PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an evidence-review CSV. Mechanical validity is "
            "filled; pedagogical_rating stays blank."
        )
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write a sheet from currently available Gemini predictions.",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Count review rows without writing.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        predictions = load_jsonl(PREDICTIONS)
        fragments = load_jsonl(FRAGMENTS)
        competencies = load_jsonl(COMPETENCIES)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    rows = build_evidence_review_rows(
        predictions=predictions,
        fragments=fragments,
        competencies=competencies,
    )
    print("=== EVIDENCE REVIEW PREPARATION ===")
    print(f"Review rows: {len(rows)}")
    print("Pedagogical ratings filled automatically: 0")

    if arguments.inspect:
        return 0

    coverage = completeness_report(
        fragments=fragments,
        predictions=predictions,
    )
    complete = coverage["complete"]

    if not complete and not arguments.allow_partial:
        print(
            "Gemini coverage is incomplete. Refusing to write "
            f"{OUTPUT}. Use --inspect or --allow-partial."
        )
        return 1

    output = OUTPUT if complete else OUTPUT.with_name(
        "evidence_review.partial.csv"
    )
    write_evidence_review(rows, output)
    print(f"Wrote: {output}")
    print("Status: WAITING_FOR_HUMAN pedagogical ratings")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
