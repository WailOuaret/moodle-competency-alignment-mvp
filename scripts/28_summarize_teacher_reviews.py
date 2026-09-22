"""Summarize real teacher / researcher review decisions (Section N).

Reads the frozen-corpus review file and the separate runtime review log, and
writes a summary. It reports rates only when real decisions exist; with none,
every rate is null and the status is WAITING_FOR_HUMAN.

This script invents nothing. It does not create a decision, does not default a
blank field, and does not count a researcher decision as teacher validation.

    python scripts/28_summarize_teacher_reviews.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from moodle_competency.annotation import read_csv, write_csv, write_json
from moodle_competency.corpus_app import CorpusData, CorpusPaths
from moodle_competency.teacher_review_summary import (
    SUMMARY_TABLE_COLUMNS,
    summarize_teacher_reviews,
    summary_table_rows,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CORPUS_REVIEWS = PROJECT_ROOT / "data" / "reviews" / "corpus_teacher_reviews.csv"
RUNTIME_REVIEWS = PROJECT_ROOT / "data" / "reviews" / "teacher_reviews.csv"

METRICS_OUT = PROJECT_ROOT / "reports" / "metrics" / "teacher_review_summary.json"
TABLE_OUT = PROJECT_ROOT / "reports" / "tables" / "teacher_review_summary.csv"

PROTECTED_PATHS = (
    PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
    PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv",
    PROJECT_ROOT / "data" / "reviews" / "teacher_reviews.csv",
    PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json",
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json",
)


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)

    return digest.hexdigest()


def snapshot_protected() -> dict[str, str | None]:
    return {str(path): file_sha256(path) for path in PROTECTED_PATHS}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize teacher review decisions on the research corpus.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Write the outputs without printing the summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    before = snapshot_protected()

    data = CorpusData.load(PROJECT_ROOT)
    mappings = data.reviewable_mappings()

    corpus_reviews = read_csv(CORPUS_REVIEWS) if CORPUS_REVIEWS.exists() else []
    runtime_reviews = read_csv(RUNTIME_REVIEWS) if RUNTIME_REVIEWS.exists() else []

    summary = summarize_teacher_reviews(
        corpus_reviews,
        mappings,
        runtime_reviews=runtime_reviews,
    )

    summary["source_files"] = {
        "corpus_teacher_reviews.csv": file_sha256(CORPUS_REVIEWS),
        "teacher_reviews.csv": file_sha256(RUNTIME_REVIEWS),
    }
    summary["review_file_note"] = (
        "corpus_teacher_reviews.csv holds decisions about the frozen research "
        "corpus. teacher_reviews.csv is the separate runtime app's log and is "
        "reported separately, not merged."
    )

    write_json(summary, METRICS_OUT)
    write_csv(summary_table_rows(summary), TABLE_OUT, SUMMARY_TABLE_COLUMNS)

    after = snapshot_protected()
    mutated = [path for path in before if before[path] != after[path]]

    if mutated:
        print("Protected files changed. This is a bug:", file=sys.stderr)

        for path in mutated:
            print(f"  {path}", file=sys.stderr)

        return 6

    if args.quiet:
        return 0

    print(f"Wrote {METRICS_OUT}")
    print(f"Wrote {TABLE_OUT}")
    print()
    print(f"Status: {summary['status']}")

    if summary["message"]:
        print(f"  {summary['message']}")

    print(
        f"Reviewable mappings: {summary['reviewable_mappings']} · "
        f"reviewed {summary['reviewed']} · pending {summary['pending']}"
    )
    print(
        f"Decisions: accept {summary['accepted']} · reject {summary['rejected']} · "
        f"modify {summary['modified']} · add {summary['added']}"
    )

    if summary["rate_denominator"]:
        print(
            f"Rates over {summary['rate_denominator']} reviewed suggestion(s): "
            f"acceptance {summary['acceptance_rate']:.4f} · "
            f"edit {summary['edit_rate']:.4f} · "
            f"rejection {summary['rejection_rate']:.4f}"
        )
    else:
        print(
            "Rates: not reported. No suggestion has been reviewed, so "
            "acceptance / edit / rejection rates would have no denominator."
        )

    print(
        "Evidence relevance: "
        f"{json.dumps(summary['evidence_relevance_distribution'])} "
        f"(unanswered {summary['evidence_relevance_unanswered']})"
    )
    print(f"Reviewer roles: {json.dumps(summary['reviewer_roles']) or '{}'}")
    print(
        "Teacher/supervisor validation performed: "
        f"{summary['teacher_or_supervisor_validation_performed']}"
    )
    print(
        f"Runtime app reviews (separate): {summary['runtime_review_count']} "
        f"{json.dumps(summary['runtime_reviewer_roles'])}"
    )
    print("Protected files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
