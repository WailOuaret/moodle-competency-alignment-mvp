"""Build AI-assisted annotation drafts from fragments and the catalogue.

Never reads BM25, Gemini, LLM tasks, or independent gold.
Never writes data/gold/manual_fragment_annotations.csv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from moodle_competency.ai_assisted_annotation import (
    assert_allowed_source_paths,
    build_draft_rows,
    draft_summary,
    write_drafts,
)
from moodle_competency.ai_assisted_draft_suggestions import draft_suggestions
from moodle_competency.annotation import load_jsonl, read_csv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAGMENTS = PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
RESOURCES = PROJECT_ROOT / "data" / "processed" / "resources.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
CATALOGUE = (
    PROJECT_ROOT / "data" / "gold" / "annotation_competency_catalogue.csv"
)
OUTPUT = (
    PROJECT_ROOT / "data" / "reviews" / "ai_assisted_annotation_drafts.csv"
)
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"


def main() -> int:
    sources = [FRAGMENTS, RESOURCES, COMPETENCIES, CATALOGUE]
    assert_allowed_source_paths(sources)

    fragments = load_jsonl(FRAGMENTS)
    resources = load_jsonl(RESOURCES)
    competencies = load_jsonl(COMPETENCIES)
    catalogue = read_csv(CATALOGUE)

    if len(resources) < 1 or len(competencies) < 1:
        print("ERROR: resources or competencies are empty.", file=sys.stderr)
        return 1

    gold_before = GOLD.read_bytes() if GOLD.exists() else None
    rows = build_draft_rows(
        fragments=fragments,
        catalogue=catalogue,
        suggestions_by_id=draft_suggestions(),
    )
    write_drafts(rows, OUTPUT)
    gold_after = GOLD.read_bytes() if GOLD.exists() else None

    if gold_before != gold_after:
        print("ERROR: independent gold CSV changed.", file=sys.stderr)
        return 1

    summary = draft_summary(rows)
    print("=== AI-ASSISTED ANNOTATION DRAFTS ===")
    print("These are Cursor drafts, not independent manual gold.")
    print(f"Total fragments: {summary['total']}")
    print(f"Draft suggestions: {summary['total']}")
    print(f"Suggested NONE: {summary['none']}")
    print(f"Suggested single-label: {summary['single']}")
    print(f"Suggested multi-label: {summary['multi']}")
    print(f"Suggested ambiguous: {summary['ambiguous']}")
    print(f"Wrote: {OUTPUT}")
    print(json.dumps({"review_status": "pending"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
