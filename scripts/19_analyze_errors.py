"""Run fragment-level error analysis after gold is complete.

Reads human evidence review when pedagogical ratings are complete.
Does not invent ratings or change gold / Gemini files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.annotation import (
    load_jsonl,
    parse_boolean,
    read_csv,
    write_csv,
    write_json,
)
from moodle_competency.error_analysis import (
    ERROR_TABLE_COLUMNS,
    EXAMPLE_COLUMNS,
    build_error_examples,
    build_error_table_row,
    classify_fragment,
    evidence_by_competency_for_fragment,
    group_evidence_reviews,
    summarize_error_rows,
    summarize_evidence_quality,
)
from moodle_competency.evaluation import (
    HumanGateClosedError,
    gold_sets_from_rows,
    predicted_sets_from_gemini,
    ranked_candidates_from_bm25,
    require_complete_gold,
)
from moodle_competency.evidence_review import pedagogical_ratings_complete


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
CANDIDATES = PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl"
PREDICTIONS = PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl"
EVIDENCE = PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv"
TABLE = PROJECT_ROOT / "reports" / "tables" / "error_analysis.csv"
EXAMPLES = PROJECT_ROOT / "reports" / "tables" / "error_examples.csv"
SUMMARY = PROJECT_ROOT / "reports" / "metrics" / "error_summary.json"

EXPECTED_CORE = {
    "fragments": 35,
    "retrieval_failure": 1,
    "llm_missed_gold_label": 0,
    "incorrect_abstention": 0,
    "ambiguous_gold": 1,
    "evidence_rows": 83,
    "rating_2": 65,
    "rating_1": 16,
    "rating_0": 2,
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify retrieval vs LLM errors, and evidence quality "
            "when Human Gate 2 is complete."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Require complete gold, then stop without writing.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        rows = read_csv(GOLD)
        require_complete_gold(rows)
        candidates = load_jsonl(CANDIDATES)
        predictions = load_jsonl(PREDICTIONS)
    except HumanGateClosedError as error:
        print(str(error))
        print(
            "Human Gate 1 is not open: manual gold annotations "
            "are incomplete."
        )
        return 2
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    evidence_rows: list[dict[str, str]] = []
    pedagogical_complete = False

    if EVIDENCE.exists():
        evidence_rows = read_csv(EVIDENCE)
        pedagogical_complete = pedagogical_ratings_complete(evidence_rows)

    if arguments.dry_run:
        print("Gold is complete. Dry-run: no error table written.")
        print(
            "Pedagogical evidence: "
            + ("COMPLETE" if pedagogical_complete else "UNAVAILABLE")
        )
        return 0

    grouped = group_evidence_reviews(evidence_rows) if evidence_rows else {}
    gold_sets = gold_sets_from_rows(rows)
    predicted_sets = predicted_sets_from_gemini(rows, predictions)
    ranked = ranked_candidates_from_bm25(rows, candidates)
    classified_rows: list[dict] = []
    table_rows: list[dict[str, str]] = []
    fragments_by_id: dict[str, dict[str, str]] = {}

    print("=== ERROR ANALYSIS ===")
    print(f"Evidence rows: {len(evidence_rows)}")
    print(
        "Pedagogical evidence flags: "
        + ("ENABLED" if pedagogical_complete else "UNAVAILABLE")
    )

    if evidence_rows and not pedagogical_complete:
        print(
            "Human Gate 2 is incomplete. Ordinary prediction categories "
            "still run. Pedagogical evidence flags are not applied. "
            "Blank ratings are not treated as 0 or 2."
        )

    for row, gold, predicted, names in zip(
        rows,
        gold_sets,
        predicted_sets,
        ranked,
        strict=True,
    ):
        fragment_id = str(row.get("fragment_id", "")).strip()
        no_competency, _errors = parse_boolean(
            row.get("no_competency"),
            "no_competency",
        )
        ambiguous, _amb_errors = parse_boolean(
            row.get("ambiguous"),
            "ambiguous",
        )
        evidence_by_competency = evidence_by_competency_for_fragment(
            grouped,
            fragment_id,
        )
        classified = classify_fragment(
            fragment_id=fragment_id,
            gold_ids=gold,
            no_competency=no_competency is True,
            ambiguous_gold=ambiguous is True,
            ranked_candidates=names,
            predicted_ids=predicted,
            abstain=not predicted,
            evidence_by_competency=evidence_by_competency or None,
            pedagogical_complete=pedagogical_complete,
        )
        classified_rows.append(classified)
        fragments_by_id[fragment_id] = row
        table_rows.append(
            build_error_table_row(
                classified,
                resource_id=str(row.get("resource_id", "") or ""),
                resource_type=str(row.get("resource_type", "") or ""),
                course_shortname=str(row.get("course_shortname", "") or ""),
            )
        )

    summary = summarize_error_rows(table_rows)
    summary["evidence_quality"] = summarize_evidence_quality(
        evidence_rows=evidence_rows,
        analysis_rows=table_rows,
        grouped=grouped,
        pedagogical_complete=pedagogical_complete,
    )
    summary["join_key"] = "fragment_id+competency_id"
    counts = summary["overlapping_flag_counts"]
    mismatches: list[str] = []

    if summary["fragments"] != EXPECTED_CORE["fragments"]:
        mismatches.append(
            f"fragments {summary['fragments']} != {EXPECTED_CORE['fragments']}"
        )

    for key in (
        "retrieval_failure",
        "llm_missed_gold_label",
        "incorrect_abstention",
        "ambiguous_gold",
    ):
        got = counts.get(key, 0)
        expected = EXPECTED_CORE[key]

        if got != expected:
            mismatches.append(f"{key} {got} != {expected}")

    if pedagogical_complete:
        quality = summary["evidence_quality"]

        if quality["evidence_rows"] != EXPECTED_CORE["evidence_rows"]:
            mismatches.append(
                "evidence_rows "
                f"{quality['evidence_rows']} != {EXPECTED_CORE['evidence_rows']}"
            )

        if quality["clear_quote_count"] != EXPECTED_CORE["rating_2"]:
            mismatches.append(
                "rating 2 "
                f"{quality['clear_quote_count']} != {EXPECTED_CORE['rating_2']}"
            )

        if quality["partial_quote_count"] != EXPECTED_CORE["rating_1"]:
            mismatches.append(
                "rating 1 "
                f"{quality['partial_quote_count']} != {EXPECTED_CORE['rating_1']}"
            )

        if quality["unsupported_quote_count"] != EXPECTED_CORE["rating_0"]:
            mismatches.append(
                "rating 0 "
                f"{quality['unsupported_quote_count']} != {EXPECTED_CORE['rating_0']}"
            )

    if mismatches:
        print("STOP: unexpected counts relative to frozen core facts:")
        for item in mismatches:
            print(f"- {item}")
        print("Historical metric files were not rewritten.")
        return 4

    write_csv(table_rows, TABLE, ERROR_TABLE_COLUMNS)
    examples = build_error_examples(
        table_rows,
        fragments_by_id=fragments_by_id,
        grouped_reviews=grouped,
    )
    write_csv(examples, EXAMPLES, EXAMPLE_COLUMNS)
    write_json(summary, SUMMARY)
    print(json.dumps(summary, indent=2))
    print(f"Wrote {TABLE}")
    print(f"Wrote {EXAMPLES}")
    print(f"Wrote {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
