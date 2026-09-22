"""Summarize evidence review after human pedagogical ratings."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from moodle_competency.annotation import read_csv, write_json
from moodle_competency.evidence_review import summarize_evidence_review


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEW = PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv"
OUTPUT = PROJECT_ROOT / "reports" / "metrics" / "evidence_review_summary.json"


def main() -> int:
    path = REVIEW

    if not path.exists():
        print(
            f"ERROR: {path} does not exist. Prepare the review sheet first.",
            file=sys.stderr,
        )
        return 1

    rows = read_csv(path)
    summary = summarize_evidence_review(rows)
    print("=== EVIDENCE REVIEW SUMMARY ===")
    print(json.dumps(summary, indent=2))

    if summary.get("status") != "COMPLETE":
        print(
            "Pedagogical summaries are not final. "
            "Mechanical validity may still be reported."
        )
        return 2

    write_json(summary, OUTPUT)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
