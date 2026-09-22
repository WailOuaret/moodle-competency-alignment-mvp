"""Generate final result figures from existing metric JSON files."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load(relative: str) -> dict:
    path = PROJECT_ROOT / relative
    return json.loads(path.read_text(encoding="utf-8"))


def _save(fig, name: str) -> Path:
    output = PROJECT_ROOT / "reports" / "figures" / name
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output


def main() -> int:
    bm25 = _load("reports/metrics/bm25_metrics.json")
    gemini = _load("reports/metrics/constrained_llm_metrics.json")
    resource = _load("reports/metrics/resource_level_metrics.json")
    graph_f = _load("reports/metrics/graph_child_preference_fragment_metrics.json")
    graph_r = _load("reports/metrics/graph_child_preference_resource_metrics.json")
    evidence = _load("reports/metrics/evidence_review_summary.json")
    errors = _load("reports/metrics/error_summary.json")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    labels = ["Recall@1", "Recall@3", "Recall@5"]
    values = [
        bm25["recall_at_1"],
        bm25["recall_at_3"],
        bm25["recall_at_5"],
    ]
    bars = ax.bar(labels, values, color="#3C6E9C")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Recall")
    ax.set_title("BM25 candidate retrieval (label-level Recall@K)")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value:.3f}",
            ha="center",
        )
    _save(fig, "bm25_recall_at_k.png")

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    labels = [
        "BM25 Top-1 F1",
        "Gemini constrained F1",
        "Post-hoc hierarchy F1",
    ]
    values = [
        bm25["top1_micro"]["f1"],
        gemini["micro_f1"],
        graph_f["micro_f1"],
    ]
    colors = ["#7A8B99", "#3C6E9C", "#C47A2C"]
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Micro F1")
    ax.set_title("Fragment-level system comparison")
    ax.annotate(
        "Hierarchy F1 is a post-hoc ablation, not original Gemini.",
        xy=(0, -0.18),
        xycoords="axes fraction",
        fontsize=8,
    )
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value:.3f}",
            ha="center",
        )
    _save(fig, "fragment_system_comparison.png")

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    labels = [
        "Original resource F1",
        "Post-hoc hierarchy resource F1",
    ]
    values = [
        resource["micro_f1"],
        graph_r["micro_f1"],
    ]
    bars = ax.bar(labels, values, color=["#3C6E9C", "#C47A2C"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Micro F1")
    ax.set_title("Resource-level system comparison")
    ax.annotate(
        "Hierarchy result is post-hoc. Original Gemini is unchanged.",
        xy=(0, -0.18),
        xycoords="axes fraction",
        fontsize=8,
    )
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value:.3f}",
            ha="center",
        )
    _save(fig, "resource_system_comparison.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    labels = ["Clear (2)", "Partial (1)", "Unsupported (0)"]
    values = [
        evidence["pedagogical_rating_counts"]["2"],
        evidence["pedagogical_rating_counts"]["1"],
        evidence["pedagogical_rating_counts"]["0"],
    ]
    bars = ax.bar(labels, values, color=["#2E7D4F", "#C47A2C", "#A33B3B"])
    ax.set_ylabel("Evidence quotes (n = 83)")
    ax.set_title("Pedagogical evidence quality")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.8,
            str(value),
            ha="center",
        )
    _save(fig, "evidence_quality.png")

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    flags = errors["overlapping_flag_counts"]
    labels = [
        "correct_prediction",
        "llm_wrong_selection",
        "overprediction",
        "parent_child_redundancy",
        "retrieval_failure",
        "underprediction",
        "ambiguous_gold",
    ]
    values = [flags[name] for name in labels]
    ax.barh(labels[::-1], values[::-1], color="#3C6E9C")
    ax.set_xlabel("Fragment count (flags may overlap)")
    ax.set_title("Main overlapping error flags")
    _save(fig, "error_categories.png")

    print("Wrote reports/figures/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
