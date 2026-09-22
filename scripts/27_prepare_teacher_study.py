"""Prepare the Section M evidence-usefulness pilot design.

Builds a small stratified sample of (fragment, predicted competency) cases and
assigns each to condition A (evidence hidden initially) or B (evidence shown),
using a fixed seed so the design is reproducible.

This script only designs the study. It records no human response, invents no
decision, and calls no model. Responses are collected later through
``app/pages/7_Evidence_Usefulness_Pilot.py``.

    python scripts/27_prepare_teacher_study.py
    python scripts/27_prepare_teacher_study.py --sample-size 12 --seed 20260918
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl, read_csv, stripped_text
from moodle_competency.teacher_study import (
    CONDITIONS,
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_SEED,
    STRATA,
    TeacherStudyError,
    build_study_design,
    write_study_cases,
    write_study_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ERROR_TABLE = PROJECT_ROOT / "reports" / "tables" / "error_analysis.csv"
EVIDENCE_REVIEW = PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"

STUDY_DIR = PROJECT_ROOT / "data" / "studies"
CASES_OUT = STUDY_DIR / "teacher_study_cases.csv"
MANIFEST_OUT = STUDY_DIR / "teacher_study_manifest.json"
RESPONSES_OUT = STUDY_DIR / "teacher_study_responses.csv"

PROTECTED_PATHS = (
    PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv",
    PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
    PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv",
    PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json",
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json",
    PROJECT_ROOT / "reports" / "tables" / "error_analysis.csv",
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
        description="Prepare the reproducible evidence-usefulness pilot design.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of cases to sample (default {DEFAULT_SAMPLE_SIZE}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Randomization seed (default {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite an existing design. Refused by default once responses "
            "exist, because that would invalidate them."
        ),
    )
    return parser.parse_args()


def competency_shortnames() -> dict[str, str]:
    if not COMPETENCIES.exists():
        return {}

    return {
        stripped_text(record.get("idnumber")): stripped_text(record.get("shortname"))
        for record in load_jsonl(COMPETENCIES)
    }


def main() -> int:
    args = parse_arguments()

    for path in (ERROR_TABLE, EVIDENCE_REVIEW):
        if not path.exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 2

    if RESPONSES_OUT.exists() and not args.force:
        print(
            f"Responses already exist at {RESPONSES_OUT}.\n"
            "Re-designing the study would orphan them. Pass --force only if "
            "you intend to discard the existing design.",
            file=sys.stderr,
        )
        return 3

    if CASES_OUT.exists() and not args.force:
        print(
            f"A design already exists at {CASES_OUT}. Pass --force to replace it.",
            file=sys.stderr,
        )
        return 3

    before = snapshot_protected()

    error_rows = read_csv(ERROR_TABLE)
    evidence_rows = read_csv(EVIDENCE_REVIEW)

    rated = [
        row for row in evidence_rows if stripped_text(row.get("pedagogical_rating"))
    ]

    if len(rated) < len(evidence_rows):
        print(
            f"Note: {len(evidence_rows) - len(rated)} evidence row(s) carry no "
            "pedagogical rating. The pilot design does not require them.",
        )

    try:
        design = build_study_design(
            error_rows,
            evidence_rows,
            sample_size=args.sample_size,
            seed=args.seed,
            competency_shortnames=competency_shortnames(),
        )
    except TeacherStudyError as error:
        print(f"Could not build the study design: {error}", file=sys.stderr)
        return 4

    cases = design["cases"]
    manifest = design["manifest"]

    if not cases:
        print("No eligible case was found. Nothing was written.", file=sys.stderr)
        return 5

    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    write_study_cases(cases, CASES_OUT)
    manifest["source_files"] = {
        "error_analysis.csv": file_sha256(ERROR_TABLE),
        "evidence_review.csv": file_sha256(EVIDENCE_REVIEW),
    }
    write_study_manifest(manifest, MANIFEST_OUT)

    after = snapshot_protected()
    mutated = [path for path in before if before[path] != after[path]]

    if mutated:
        print("Protected files changed. This is a bug:", file=sys.stderr)

        for path in mutated:
            print(f"  {path}", file=sys.stderr)

        return 6

    print(f"Wrote {CASES_OUT}")
    print(f"Wrote {MANIFEST_OUT}")
    print()
    print(f"Sampled {len(cases)} of {manifest['candidate_case_count']} candidate cases")
    print(f"Seed: {args.seed} (rerunning with this seed reproduces the design)")
    print(f"Conditions: {json.dumps(manifest['condition_counts'])}")
    print(f"Strata:     {json.dumps(manifest['stratum_counts'])}")
    print(f"Courses:    {json.dumps(manifest['course_counts'])}")
    print(f"Types:      {json.dumps(manifest['resource_type_counts'])}")
    print()
    print(
        f"Condition {CONDITIONS[0]} hides the evidence quote behind an explicit "
        f"action; condition {CONDITIONS[1]} shows it alongside the suggestion."
    )
    print(f"Strata used, in priority order: {', '.join(STRATA)}")
    print()
    print("No human response was recorded. Collect responses with:")
    print("  streamlit run app/Home.py   →  7 Evidence Usefulness Pilot")
    print("Protected files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
