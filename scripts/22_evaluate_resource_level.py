"""Evaluate existing Gemini resource predictions against derived resource gold.

Does not call Gemini or Ollama.
Does not read activity-level Moodle competency links.
Does not modify fragment gold, Gemini, BM25, or evidence-review files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from moodle_competency.annotation import (
    load_jsonl,
    read_csv,
    write_csv,
    write_json,
)
from moodle_competency.evaluation import (
    HumanGateClosedError,
    require_complete_gold,
)
from moodle_competency.llm_validation import write_jsonl
from moodle_competency.resource_evaluation import (
    EXAMPLE_COLUMNS,
    PER_COMPETENCY_COLUMNS,
    RESOURCE_TABLE_COLUMNS,
    ResourceReferenceValidationError,
    build_resource_error_examples,
    build_resource_reference,
    evaluate_resource_level,
    inspect_sanity_mismatches,
    metrics_payload,
    per_competency_table_rows,
    render_resource_level_report,
    require_valid_resource_reference,
    resource_table_rows,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
RESOURCES = PROJECT_ROOT / "data" / "processed" / "resources.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
PREDICTIONS = PROJECT_ROOT / "data" / "processed" / "resource_predictions.jsonl"
FRAGMENT_METRICS = (
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json"
)
REFERENCE_OUT = PROJECT_ROOT / "data" / "processed" / "resource_reference.jsonl"
METRICS_OUT = PROJECT_ROOT / "reports" / "metrics" / "resource_level_metrics.json"
TABLE_OUT = PROJECT_ROOT / "reports" / "tables" / "resource_level_evaluation.csv"
PER_LABEL_OUT = (
    PROJECT_ROOT / "reports" / "tables" / "resource_level_per_competency.csv"
)
EXAMPLES_OUT = (
    PROJECT_ROOT / "reports" / "tables" / "resource_level_error_examples.csv"
)
REPORT_OUT = PROJECT_ROOT / "reports" / "RESOURCE_LEVEL_EVALUATION.md"

LIVE_COUNTS = {
    "resources": 20,
    "pages": 8,
    "quiz_questions": 12,
    "fragments": 35,
}

# Approximate expected values for the frozen live corpus only.
# Not used to compute metrics.
LIVE_SANITY = {
    "resource_count": 20,
    "micro_precision": 0.6764705882,
    "micro_recall": 0.9583333333,
    "micro_f1": 0.7931034483,
    "exact_set_match": 0.45,
    "average_absolute_label_count_error": 0.50,
    "macro_all_13": {
        "precision": 0.7051,
        "recall": 0.7308,
        "f1": 0.7026,
    },
    "macro_gold_supported_labels": {
        "precision": 0.9167,
        "recall": 0.9500,
        "f1": 0.9133,
    },
}

PROTECTED_PATHS = (
    PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv",
    PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
    PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json",
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json",
    PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv",
    PROJECT_ROOT
    / "data"
    / "experiments"
    / "ollama_constrained_validated.jsonl",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate existing resource-level Gemini predictions "
            "against a derived fragment-union reference."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate reference construction without writing outputs.",
    )
    return parser.parse_args()


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def snapshot_protected() -> dict[str, str | None]:
    return {str(path): file_sha256(path) for path in PROTECTED_PATHS}


def live_count_errors(validation: dict) -> list[str]:
    errors: list[str] = []
    expected = (
        ("resource_count", LIVE_COUNTS["resources"]),
        ("page_count", LIVE_COUNTS["pages"]),
        ("quiz_question_count", LIVE_COUNTS["quiz_questions"]),
        ("fragment_count", LIVE_COUNTS["fragments"]),
        ("gold_fragment_count", LIVE_COUNTS["fragments"]),
    )

    for key, target in expected:
        actual = int(validation.get(key) or 0)

        if actual != target:
            errors.append(f"{key}: {actual} (expected {target})")

    if validation.get("fragments_used_exactly_once") is not True:
        errors.append("fragments were not used exactly once")

    if validation.get("used_manual_moodle_links") is True:
        errors.append("manual_moodle_links.csv must not be used")

    return errors


def main() -> int:
    arguments = parse_arguments()
    before = snapshot_protected()

    try:
        gold_rows = read_csv(GOLD)
        require_complete_gold(gold_rows)
        resources = load_jsonl(RESOURCES)
        competencies = load_jsonl(COMPETENCIES)
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

    print("=== RESOURCE-LEVEL EVALUATION ===")
    print("Using existing Gemini resource predictions. No new model calls.")

    reference_records, validation = build_resource_reference(
        gold_rows=gold_rows,
        resources=resources,
        competencies=competencies,
    )

    print(
        "Derived reference: "
        f"{validation['resource_count']} resources, "
        f"{validation['page_count']} pages, "
        f"{validation['quiz_question_count']} quiz questions, "
        f"{validation['fragment_count']} fragments"
    )

    try:
        require_valid_resource_reference(validation)
    except ResourceReferenceValidationError as error:
        print(str(error), file=sys.stderr)
        print("STOP: derived resource reference is invalid.")
        print("Final metric files were not written.")
        return 4

    count_errors = live_count_errors(validation)

    if count_errors:
        print("STOP: live corpus validation failed.", file=sys.stderr)

        for item in count_errors:
            print(f"  {item}", file=sys.stderr)

        print("Final metric files were not written.")
        return 4

    if arguments.dry_run:
        print("Dry-run: reference construction valid. No files written.")
        return 0

    try:
        evaluation = evaluate_resource_level(
            reference_records=reference_records,
            predictions=predictions,
            competencies=competencies,
        )
    except ResourceReferenceValidationError as error:
        print(str(error), file=sys.stderr)
        print("STOP: resource prediction alignment failed.")
        print("Final metric files were not written.")
        return 4

    mismatches = inspect_sanity_mismatches(evaluation, LIVE_SANITY)

    if mismatches:
        print(
            "STOP: measured resource-level metrics differ from "
            "expected sanity values. Inspect resource-reference "
            "construction. Metric files were not written.",
            file=sys.stderr,
        )

        for item in mismatches:
            print(f"  {item}", file=sys.stderr)

        return 5

    fragment_metrics: dict = {}

    if FRAGMENT_METRICS.exists():
        fragment_metrics = json.loads(
            FRAGMENT_METRICS.read_text(encoding="utf-8")
        )

    write_jsonl(reference_records, REFERENCE_OUT)
    write_json(metrics_payload(evaluation), METRICS_OUT)
    write_csv(
        resource_table_rows(evaluation),
        TABLE_OUT,
        RESOURCE_TABLE_COLUMNS,
    )
    write_csv(
        per_competency_table_rows(evaluation),
        PER_LABEL_OUT,
        PER_COMPETENCY_COLUMNS,
    )
    write_csv(
        build_resource_error_examples(evaluation),
        EXAMPLES_OUT,
        EXAMPLE_COLUMNS,
    )
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(
        render_resource_level_report(
            evaluation=evaluation,
            validation=validation,
            fragment_metrics=fragment_metrics,
        ),
        encoding="utf-8",
    )

    after = snapshot_protected()
    mutated = [
        path for path, digest in before.items() if after.get(path) != digest
    ]

    if mutated:
        print("ERROR: protected files changed:", file=sys.stderr)

        for path in mutated:
            print(f"  {path}", file=sys.stderr)

        return 6

    print(f"Wrote {REFERENCE_OUT}")
    print(f"Wrote {METRICS_OUT}")
    print(f"Wrote {TABLE_OUT}")
    print(f"Wrote {PER_LABEL_OUT}")
    print(f"Wrote {EXAMPLES_OUT}")
    print(f"Wrote {REPORT_OUT}")
    print(
        "micro P/R/F1 = "
        f"{evaluation['micro_precision']:.10f} / "
        f"{evaluation['micro_recall']:.10f} / "
        f"{evaluation['micro_f1']:.10f}"
    )
    print(
        "exact-set = "
        f"{evaluation['exact_set_match']:.10f}; "
        "label-count error = "
        f"{evaluation['average_absolute_label_count_error']:.10f}"
    )
    print("Protected files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
