"""Post-hoc hierarchy warnings and optional child-preference ablation.

Does not call Gemini or Ollama.
Does not overwrite frozen Gemini, gold, BM25, or resource-level metric files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.aggregation import aggregate_fragment_predictions
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
from moodle_competency.graph_checks import (
    ABLATION_COMPARISON_COLUMNS,
    EXAMPLE_COLUMNS,
    EXPERIMENT_NAME,
    FRAGMENT_EVAL_COLUMNS,
    GRAPH_RULE_VERSION,
    RESOURCE_ABLATION_COLUMNS,
    RESOURCE_WARNING_COLUMNS,
    WARNING_COLUMNS,
    build_graph_examples,
    build_hierarchy_index,
    collect_fragment_warnings,
    collect_resource_warnings,
    count_removed_true_reference_labels,
    evaluate_fragment_predictions,
    fragment_ablation_comparison_rows,
    fragment_context_from_rows,
    fragment_eval_table_rows,
    metrics_without_rows,
    render_graph_report,
    require_valid_hierarchy,
    resource_ablation_comparison_rows,
    resource_warning_table_rows,
    simulate_child_preference,
    summarize_fragment_warnings,
    summarize_resource_warnings,
    utc_timestamp,
    validate_hierarchy,
    warning_table_rows,
)
from moodle_competency.llm_validation import write_jsonl
from moodle_competency.resource_evaluation import (
    RESOURCE_TABLE_COLUMNS,
    evaluate_resource_level,
    metrics_payload,
    resource_table_rows,
)
from moodle_competency.reproducibility import file_sha256


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
FRAGMENTS = PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
RESOURCES = PROJECT_ROOT / "data" / "processed" / "resources.jsonl"
GEMINI = PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl"
RESOURCE_PREDS = (
    PROJECT_ROOT / "data" / "processed" / "resource_predictions.jsonl"
)
RESOURCE_REF = PROJECT_ROOT / "data" / "processed" / "resource_reference.jsonl"
LLM_METRICS = (
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json"
)
MACRO_VIEWS = PROJECT_ROOT / "reports" / "metrics" / "macro_label_views.json"
RESOURCE_METRICS = (
    PROJECT_ROOT / "reports" / "metrics" / "resource_level_metrics.json"
)

WARN_JSONL = PROJECT_ROOT / "data" / "processed" / "graph_warnings.jsonl"
WARN_CSV = PROJECT_ROOT / "reports" / "tables" / "graph_warnings.csv"
WARN_SUMMARY = PROJECT_ROOT / "reports" / "metrics" / "graph_check_summary.json"
RES_WARN_CSV = PROJECT_ROOT / "reports" / "tables" / "resource_graph_warnings.csv"
RES_WARN_SUMMARY = (
    PROJECT_ROOT / "reports" / "metrics" / "resource_graph_check_summary.json"
)

SIM_PREDS = (
    PROJECT_ROOT
    / "data"
    / "experiments"
    / "graph_child_preference_predictions.jsonl"
)
SIM_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "experiments"
    / "graph_child_preference_manifest.json"
)
SIM_FRAG_METRICS = (
    PROJECT_ROOT
    / "reports"
    / "metrics"
    / "graph_child_preference_fragment_metrics.json"
)
SIM_FRAG_TABLE = (
    PROJECT_ROOT
    / "reports"
    / "tables"
    / "graph_child_preference_fragment_evaluation.csv"
)
FRAG_COMPARE = (
    PROJECT_ROOT / "reports" / "tables" / "graph_ablation_comparison.csv"
)
SIM_RES_PREDS = (
    PROJECT_ROOT
    / "data"
    / "experiments"
    / "graph_child_preference_resource_predictions.jsonl"
)
SIM_RES_METRICS = (
    PROJECT_ROOT
    / "reports"
    / "metrics"
    / "graph_child_preference_resource_metrics.json"
)
SIM_RES_TABLE = (
    PROJECT_ROOT
    / "reports"
    / "tables"
    / "graph_child_preference_resource_evaluation.csv"
)
RES_COMPARE = (
    PROJECT_ROOT
    / "reports"
    / "tables"
    / "graph_resource_ablation_comparison.csv"
)
EXAMPLES = PROJECT_ROOT / "reports" / "tables" / "graph_examples.csv"
REPORT = PROJECT_ROOT / "reports" / "MINIMAL_GRAPH_HIERARCHY_ANALYSIS.md"

LIVE_HIERARCHY = {
    "competency_count": 13,
    "root_count": 3,
    "child_count": 10,
}

PROTECTED_PATHS = (
    PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv",
    PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
    PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json",
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json",
    PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv",
    PROJECT_ROOT / "reports" / "metrics" / "resource_level_metrics.json",
    PROJECT_ROOT
    / "data"
    / "experiments"
    / "ollama_constrained_validated.jsonl",
    PROJECT_ROOT
    / "data"
    / "experiments"
    / "ollama_constrained_responses.jsonl",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Post-hoc hierarchy warnings. Optional child-preference "
            "ablation writes a separate simulated prediction set."
        )
    )
    parser.add_argument(
        "--simulate-child-preference",
        action="store_true",
        help=(
            "Write a separate simulated prediction set that removes "
            "redundant parents. Does not overwrite Gemini."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate hierarchy and count warnings without writing.",
    )
    return parser.parse_args()


def snapshot(paths: tuple[Path, ...]) -> dict[str, str | None]:
    return {str(path): file_sha256(path) for path in paths}


def original_fragment_metrics(
    parent_child_count: int,
) -> dict:
    llm = json.loads(LLM_METRICS.read_text(encoding="utf-8"))
    views = json.loads(MACRO_VIEWS.read_text(encoding="utf-8"))
    gemini = views["bm25_top5_constrained_gemini"]
    return {
        "micro_precision": llm["micro_precision"],
        "micro_recall": llm["micro_recall"],
        "micro_f1": llm["micro_f1"],
        "macro_all_13": dict(gemini["macro_all_13"]),
        "macro_gold_supported_labels": dict(
            gemini["macro_gold_supported_labels"]
        ),
        "exact_set_match": llm["exact_set_match"],
        "coverage": llm["coverage"],
        "abstention_rate": llm["abstention_rate"],
        "average_predicted_labels": llm["average_predicted_labels"],
        "parent_child_redundancy_count": parent_child_count,
    }


def original_resource_metrics() -> dict:
    return json.loads(RESOURCE_METRICS.read_text(encoding="utf-8"))


def live_hierarchy_errors(validation: dict) -> list[str]:
    errors: list[str] = []

    for key, expected in LIVE_HIERARCHY.items():
        actual = int(validation.get(key) or 0)

        if actual != expected:
            errors.append(f"{key}: {actual} (expected {expected})")

    return errors


def main() -> int:
    arguments = parse_arguments()
    before = snapshot(PROTECTED_PATHS)

    try:
        gold_rows = read_csv(GOLD)
        require_complete_gold(gold_rows)
        competencies = load_jsonl(COMPETENCIES)
        predictions = load_jsonl(GEMINI)
        resource_predictions = load_jsonl(RESOURCE_PREDS)
    except HumanGateClosedError as error:
        print(str(error))
        return 2
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("=== MINIMAL HIERARCHY / GRAPH ANALYSIS ===")
    print("Post-hoc ablation. Frozen Gemini predictions are not modified.")

    index = build_hierarchy_index(competencies)
    hierarchy = validate_hierarchy(competencies, index)

    try:
        require_valid_hierarchy(hierarchy)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 4

    live_errors = live_hierarchy_errors(hierarchy)

    if live_errors:
        print("STOP: live hierarchy counts unexpected.", file=sys.stderr)

        for item in live_errors:
            print(f"  {item}", file=sys.stderr)

        return 4

    context = fragment_context_from_rows(gold_rows)
    fragment_warnings = collect_fragment_warnings(
        predictions,
        index,
        context_by_fragment=context,
    )
    resource_warnings = collect_resource_warnings(
        resource_predictions,
        index,
    )
    fragment_summary = summarize_fragment_warnings(
        fragment_warnings,
        fragments_checked=len(predictions),
        context_by_fragment=context,
    )
    resource_summary = summarize_resource_warnings(
        resource_warnings,
        resources_checked=len(resource_predictions),
        predictions=resource_predictions,
        index=index,
    )

    print(
        "Fragment parent-child redundancy: "
        f"{fragment_summary['fragments_with_parent_child_redundancy']}/"
        f"{fragment_summary['fragments_checked']}"
    )
    print(
        "Resource parent-child redundancy: "
        f"{resource_summary['resources_with_parent_child_redundancy']}/"
        f"{resource_summary['resources_checked']}"
    )

    if arguments.dry_run:
        print("Dry-run: no files written.")
        return 0

    write_jsonl(fragment_warnings, WARN_JSONL)
    write_csv(warning_table_rows(fragment_warnings), WARN_CSV, WARNING_COLUMNS)
    write_json(fragment_summary, WARN_SUMMARY)
    write_csv(
        resource_warning_table_rows(resource_warnings),
        RES_WARN_CSV,
        RESOURCE_WARNING_COLUMNS,
    )
    write_json(resource_summary, RES_WARN_SUMMARY)

    if not arguments.simulate_child_preference:
        after = snapshot(PROTECTED_PATHS)
        mutated = [
            path for path, digest in before.items() if after.get(path) != digest
        ]

        if mutated:
            print("ERROR: protected files changed:", file=sys.stderr)

            for path in mutated:
                print(f"  {path}", file=sys.stderr)

            return 6

        print("Wrote hierarchy warnings. Simulated ablation not requested.")
        return 0

    simulated, sim_stats = simulate_child_preference(predictions, index)
    removed_gold = count_removed_true_reference_labels(
        gold_rows,
        predictions,
        simulated,
    )
    simulated_fragment = evaluate_fragment_predictions(
        gold_rows,
        simulated,
        competencies,
        parent_child_redundancy_count=0,
    )
    original_fragment = original_fragment_metrics(
        fragment_summary["fragments_with_parent_child_redundancy"]
    )
    original_resource = original_resource_metrics()

    fragments = load_jsonl(FRAGMENTS)
    resources = load_jsonl(RESOURCES)
    simulated_resources, _agg_manifest = aggregate_fragment_predictions(
        fragments=fragments,
        resources=resources,
        competencies=competencies,
        predictions=simulated,
        allow_partial=False,
    )
    reference_records = load_jsonl(RESOURCE_REF)
    simulated_resource_eval = evaluate_resource_level(
        reference_records=reference_records,
        predictions=simulated_resources,
        competencies=competencies,
    )
    examples = build_graph_examples(
        gold_rows=gold_rows,
        original=predictions,
        simulated=simulated,
        warnings=fragment_warnings,
        index=index,
    )

    write_jsonl(simulated, SIM_PREDS)
    write_json(
        {
            "experiment_name": EXPERIMENT_NAME,
            "source_prediction_hash": file_sha256(GEMINI),
            "competency_catalogue_hash": file_sha256(COMPETENCIES),
            "rule_version": GRAPH_RULE_VERSION,
            "timestamp": utc_timestamp(),
            "removed_parent_count": sim_stats["removed_parent_count"],
            "affected_fragment_count": sim_stats["affected_fragment_count"],
            "removed_true_reference_labels": removed_gold[
                "removed_true_reference_labels"
            ],
            "original_predictions_modified": False,
            "note": (
                "Post-hoc hierarchy ablation. Frozen Gemini predictions "
                "were not overwritten."
            ),
        },
        SIM_MANIFEST,
    )
    write_json(metrics_without_rows(simulated_fragment), SIM_FRAG_METRICS)
    write_csv(
        fragment_eval_table_rows(simulated_fragment),
        SIM_FRAG_TABLE,
        FRAGMENT_EVAL_COLUMNS,
    )
    write_csv(
        fragment_ablation_comparison_rows(
            original_fragment,
            simulated_fragment,
        ),
        FRAG_COMPARE,
        ABLATION_COMPARISON_COLUMNS,
    )
    write_jsonl(simulated_resources, SIM_RES_PREDS)
    write_json(metrics_payload(simulated_resource_eval), SIM_RES_METRICS)
    write_csv(
        resource_table_rows(simulated_resource_eval),
        SIM_RES_TABLE,
        RESOURCE_TABLE_COLUMNS,
    )
    write_csv(
        resource_ablation_comparison_rows(
            original_resource,
            simulated_resource_eval,
        ),
        RES_COMPARE,
        RESOURCE_ABLATION_COLUMNS,
    )
    write_csv(examples, EXAMPLES, EXAMPLE_COLUMNS)
    REPORT.write_text(
        render_graph_report(
            hierarchy=hierarchy,
            fragment_summary=fragment_summary,
            resource_summary=resource_summary,
            original_fragment=original_fragment,
            simulated_fragment=simulated_fragment,
            original_resource=original_resource,
            simulated_resource=simulated_resource_eval,
            simulation_stats=sim_stats,
            removed_gold=removed_gold,
            examples=examples,
        ),
        encoding="utf-8",
    )

    after = snapshot(PROTECTED_PATHS)
    mutated = [
        path for path, digest in before.items() if after.get(path) != digest
    ]

    if mutated:
        print("ERROR: protected files changed:", file=sys.stderr)

        for path in mutated:
            print(f"  {path}", file=sys.stderr)

        return 6

    print(f"Wrote {WARN_JSONL}")
    print(f"Wrote {SIM_PREDS}")
    print(f"Wrote {REPORT}")
    print(
        "Removed parents: "
        f"{sim_stats['removed_parent_count']}; "
        "removed true reference labels: "
        f"{removed_gold['removed_true_reference_labels']}"
    )
    print("Protected files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
