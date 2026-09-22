"""Build competency -> resources inverse index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl
from moodle_competency.inverse_index import (
    build_competency_resource_index,
    write_competency_resource_index,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
PREDICTIONS = (
    PROJECT_ROOT / "data" / "processed" / "resource_predictions.jsonl"
)
PARTIAL_PREDICTIONS = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "resource_predictions.partial.jsonl"
)
OUTPUT = (
    PROJECT_ROOT / "data" / "processed" / "competency_resource_index.jsonl"
)
MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "resource_predictions_manifest.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Invert resource predictions onto 13 competencies."
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Read a PARTIAL resource_predictions file if present.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    source = PREDICTIONS
    completeness = "complete"

    if not source.exists():
        if arguments.allow_partial and PARTIAL_PREDICTIONS.exists():
            source = PARTIAL_PREDICTIONS
            completeness = "partial"
        else:
            print(
                "ERROR: resource_predictions.jsonl is missing. "
                "Aggregation has not produced a FINAL dataset. "
                "Human/Gemini gates are still closed.",
                file=sys.stderr,
            )
            return 1

    try:
        competencies = load_jsonl(COMPETENCIES)
        predictions = load_jsonl(source)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if MANIFEST.exists() and completeness == "complete":
        # Keep whatever the aggregation manifest recorded.
        completeness = "complete"

    if source.name.endswith("partial.jsonl"):
        completeness = "partial"

    index = build_competency_resource_index(
        competencies=competencies,
        resource_predictions=predictions,
        upstream_completeness=completeness,
    )
    output = OUTPUT

    if completeness != "complete":
        output = OUTPUT.with_name(
            "competency_resource_index.partial.jsonl"
        )

    write_competency_resource_index(index, output)
    print("=== COMPETENCY RESOURCE INDEX ===")
    print(f"Competencies: {len(index)}")
    print(f"Upstream completeness: {completeness}")
    print(f"Wrote: {output}")

    if completeness != "complete":
        print("Status: PARTIAL / NOT FINAL")
        return 1

    print("Status: COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
