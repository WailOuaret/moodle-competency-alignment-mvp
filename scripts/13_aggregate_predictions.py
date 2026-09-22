"""Aggregate fragment Gemini predictions to resource-level records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.aggregation import (
    IncompletePredictionsError,
    aggregate_fragment_predictions,
    completeness_report,
    write_resource_predictions,
)
from moodle_competency.annotation import load_jsonl


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAGMENTS = PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
RESOURCES = PROJECT_ROOT / "data" / "processed" / "resources.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
PREDICTIONS = PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl"
OUTPUT = PROJECT_ROOT / "data" / "processed" / "resource_predictions.jsonl"
MANIFEST = (
    PROJECT_ROOT / "data" / "processed" / "resource_predictions_manifest.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate constrained Gemini fragment predictions. "
            "Refuses a FINAL write while Gemini is incomplete."
        )
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Report completeness only; do not write outputs.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help=(
            "Write a PARTIAL development artefact. "
            "Never treat it as a final research result."
        ),
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        fragments = load_jsonl(FRAGMENTS)
        resources = load_jsonl(RESOURCES)
        competencies = load_jsonl(COMPETENCIES)
        predictions = load_jsonl(PREDICTIONS)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    coverage = completeness_report(
        fragments=fragments,
        predictions=predictions,
    )
    print("=== RESOURCE AGGREGATION ===")
    print(f"Expected fragments: {coverage['expected_fragments']}")
    print(
        "Available predicted fragments: "
        f"{coverage['available_predicted_fragments']}"
    )
    print(f"Missing fragments: {len(coverage['missing_fragment_ids'])}")
    print(
        "Status: COMPLETE"
        if coverage["complete"]
        else "Status: PARTIAL / NOT FINAL"
    )

    if arguments.inspect:
        if coverage["missing_fragment_ids"]:
            print("Missing IDs:")
            for fragment_id in coverage["missing_fragment_ids"]:
                print(f"- {fragment_id}")
        return 0 if coverage["complete"] else 1

    try:
        records, manifest = aggregate_fragment_predictions(
            fragments=fragments,
            resources=resources,
            competencies=competencies,
            predictions=predictions,
            allow_partial=arguments.allow_partial,
        )
    except IncompletePredictionsError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("Use --inspect or --allow-partial for development.")
        return 1

    if not manifest["final"] and arguments.allow_partial:
        output = OUTPUT.with_name(
            "resource_predictions.partial.jsonl"
        )
        manifest_path = MANIFEST.with_name(
            "resource_predictions_manifest.partial.json"
        )
    else:
        output = OUTPUT
        manifest_path = MANIFEST

    write_resource_predictions(
        records,
        output,
        manifest,
        manifest_path,
    )
    print(f"Wrote: {output}")
    print(f"Manifest: {manifest_path}")
    print(json.dumps({"final": manifest["final"]}, indent=2))
    return 0 if manifest["final"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
