"""Export human-reviewed AI-assisted annotations.

Never overwrites data/gold/manual_fragment_annotations.csv.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from moodle_competency.ai_assisted_annotation import (
    EXPORT_COLUMNS,
    export_reviewed_rows,
    DraftValidationError,
)
from moodle_competency.annotation import read_csv, write_csv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFTS = (
    PROJECT_ROOT / "data" / "reviews" / "ai_assisted_annotation_drafts.csv"
)
OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "reviews"
    / "human_reviewed_ai_assisted_annotations.csv"
)
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export reviewed AI-assisted annotations. "
            "Does not write independent gold."
        )
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=["ai-assisted"],
        help="Must be ai-assisted. Independent gold is never the target.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    if arguments.target != "ai-assisted":
        print("ERROR: only --target ai-assisted is supported.", file=sys.stderr)
        return 1

    if not DRAFTS.exists():
        print(f"ERROR: {DRAFTS} does not exist.", file=sys.stderr)
        return 1

    gold_before = GOLD.read_bytes() if GOLD.exists() else None
    rows = read_csv(DRAFTS)

    try:
        exported = export_reviewed_rows(rows)
    except DraftValidationError as error:
        print(str(error), file=sys.stderr)
        return 1

    write_csv(exported, OUTPUT, EXPORT_COLUMNS)
    gold_after = GOLD.read_bytes() if GOLD.exists() else None

    if gold_before != gold_after:
        print("ERROR: independent gold CSV changed.", file=sys.stderr)
        return 1

    print("=== AI-ASSISTED EXPORT ===")
    print("Provenance: AI-assisted human review. Not independent gold.")
    print(f"Rows: {len(exported)}")
    print(f"Wrote: {OUTPUT}")
    print(f"Independent gold untouched: {GOLD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
