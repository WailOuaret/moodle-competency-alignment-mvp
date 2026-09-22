"""View 6 — the measured research results, strictly read-only.

Every number on this page is read from a frozen metric file under
``reports/metrics/``. This page has no write path of any kind: it cannot
create, edit or delete a metric file.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st  # noqa: E402

from _shared import corpus, page_header, sidebar_context  # noqa: E402
from moodle_competency.corpus_app import load_measured_results  # noqa: E402
from _shared import PROJECT_ROOT  # noqa: E402

st.set_page_config(page_title="Experiment Results", page_icon="📈", layout="wide")

data = corpus()
results = load_measured_results(PROJECT_ROOT)

page_header(
    "Measured results",
    "Read-only view of the frozen experiment metrics",
)

st.info(
    "This page only reads `reports/metrics/*.json`. It never writes a metric "
    "file, and the interface cannot change a measured result.",
    icon="🔒",
)


def fmt(value, digits: int = 4) -> str:
    if value is None:
        return "—"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def missing(name: str) -> None:
    st.caption(f"`{name}` is not present. Nothing is shown in its place.")


# -- BM25 ------------------------------------------------------------------

st.subheader("1 · BM25 retrieval baseline")

bm25 = results["bm25"]

if bm25 is None:
    missing("bm25_metrics.json")
else:
    recall1, recall2, recall3 = st.columns(3)
    recall1.metric("Recall@1", fmt(bm25.get("recall_at_1")))
    recall2.metric("Recall@3", fmt(bm25.get("recall_at_3")))
    recall3.metric("Recall@5", fmt(bm25.get("recall_at_5")))

    hit1, hit2, hit3, mrr = st.columns(4)
    hit1.metric("Hit@1", fmt(bm25.get("hit_at_1")))
    hit2.metric("Hit@3", fmt(bm25.get("hit_at_3")))
    hit3.metric("Hit@5", fmt(bm25.get("hit_at_5")))
    mrr.metric("MRR", fmt(bm25.get("mrr")))

    micro = bm25.get("top1_micro", {}) or {}
    macro = bm25.get("top1_macro", {}) or {}

    st.markdown("**Top-1 as a standalone classifier**")
    top1, top2, top3 = st.columns(3)
    top1.metric("Micro precision", fmt(micro.get("precision")))
    top2.metric("Micro recall", fmt(micro.get("recall")))
    top3.metric("Micro F1", fmt(micro.get("f1")))

    st.caption(
        f"Macro (all 13 labels) P/R/F1: {fmt(macro.get('precision'))} / "
        f"{fmt(macro.get('recall'))} / {fmt(macro.get('f1'))}. "
        "Recall@K is label-level over the reference labels; Hit@K and MRR are "
        "fragment-level."
    )

st.divider()

# -- constrained Gemini ----------------------------------------------------

st.subheader("2 · BM25 Top-5 + constrained language model")

llm = results["constrained_llm"]

if llm is None:
    missing("constrained_llm_metrics.json")
else:
    mic1, mic2, mic3 = st.columns(3)
    mic1.metric("Micro precision", fmt(llm.get("micro_precision")))
    mic2.metric("Micro recall", fmt(llm.get("micro_recall")))
    mic3.metric("Micro F1", fmt(llm.get("micro_f1")))

    mac1, mac2, mac3 = st.columns(3)
    mac1.metric("Macro precision", fmt(llm.get("macro_precision")))
    mac2.metric("Macro recall", fmt(llm.get("macro_recall")))
    mac3.metric("Macro F1", fmt(llm.get("macro_f1")))

    ext1, ext2, ext3, ext4 = st.columns(4)
    ext1.metric("Exact-set match", fmt(llm.get("exact_set_match")))
    ext2.metric("Coverage", fmt(llm.get("coverage"), 2))
    ext3.metric("Abstention rate", fmt(llm.get("abstention_rate"), 2))
    ext4.metric("Avg labels/fragment", fmt(llm.get("average_predicted_labels")))

    st.caption(
        "Macro above is the full 13-label universe. Abstention rate is 0.0 and "
        "cannot be judged fairly, because the reference set contains no NONE "
        "fragments."
    )

st.divider()

# -- comparison ------------------------------------------------------------

st.subheader("3 · The measured trade-off")

if bm25 is None or llm is None:
    missing("both metric files")
else:
    micro = bm25.get("top1_micro", {}) or {}

    rows = [
        ("Micro precision", micro.get("precision"), llm.get("micro_precision")),
        ("Micro recall", micro.get("recall"), llm.get("micro_recall")),
        ("Micro F1", micro.get("f1"), llm.get("micro_f1")),
    ]

    st.table(
        {
            "Metric": [row[0] for row in rows],
            "BM25 Top-1": [fmt(row[1]) for row in rows],
            "BM25 Top-5 + LLM": [fmt(row[2]) for row in rows],
            "Δ": [
                fmt((row[2] or 0) - (row[1] or 0))
                if row[1] is not None and row[2] is not None
                else "—"
                for row in rows
            ],
        }
    )

    st.markdown(
        """
The constrained model trades a small amount of precision for a large gain in
recall, and improves F1 overall. It is **not** uniformly better: BM25 Top-1 has
slightly higher micro precision.

The single reference label the system misses is missing from the BM25 Top-5
candidate set, so it is a **retrieval** failure. The model missed no reference
label that retrieval actually offered it.
"""
    )

st.divider()

# -- macro views -----------------------------------------------------------

st.subheader("4 · Two macro views")

macro_views = results["macro_views"]

if macro_views is None:
    missing("macro_label_views.json")
else:
    zero_support = (
        macro_views.get("bm25_top5_constrained_gemini", {}).get(
            "zero_gold_support_label_ids", []
        )
        or []
    )

    st.markdown(
        f"""
Three competencies — {', '.join(f'`{value}`' for value in zero_support)} — have
**zero** reference support but are still predicted. They are the three top-level
parents. That makes a single macro number ambiguous, so both views are reported.
"""
    )

    for system_key, label in (
        ("bm25_top1", "BM25 Top-1"),
        ("bm25_top5_constrained_gemini", "BM25 Top-5 + constrained LLM"),
    ):
        block = macro_views.get(system_key, {})

        if not block:
            continue

        st.markdown(f"**{label}**")
        all13 = block.get("macro_all_13", {})
        supported = block.get("macro_gold_supported_labels", {})

        st.table(
            {
                "View": ["macro_all_13", "macro_gold_supported_labels"],
                "Precision": [fmt(all13.get("precision")), fmt(supported.get("precision"))],
                "Recall": [fmt(all13.get("recall")), fmt(supported.get("recall"))],
                "F1": [fmt(all13.get("f1")), fmt(supported.get("f1"))],
            }
        )

    st.caption(
        "`macro_all_13` penalises predicting an unsupported parent. "
        "`macro_gold_supported_labels` describes performance on the labels the "
        "reference actually contains. Neither replaces the other."
    )

st.divider()

# -- resource level --------------------------------------------------------

st.subheader("5 · Resource-level evaluation")

resource_level = results["resource_level"]

if resource_level is None:
    missing("resource_level_metrics.json")
else:
    res1, res2, res3 = st.columns(3)
    res1.metric("Micro precision", fmt(resource_level.get("micro_precision")))
    res2.metric("Micro recall", fmt(resource_level.get("micro_recall")))
    res3.metric("Micro F1", fmt(resource_level.get("micro_f1")))

    res4, res5, res6 = st.columns(3)
    res4.metric("Exact-set match", fmt(resource_level.get("exact_set_match")))
    res5.metric("Resources", resource_level.get("resource_count", "—"))
    res6.metric(
        "Avg label-count error",
        fmt(resource_level.get("average_absolute_label_count_error"), 2),
    )

    st.caption(resource_level.get("reference_derivation_note", ""))

st.divider()

# -- evidence --------------------------------------------------------------

st.subheader("6 · Evidence quality")

evidence = results["evidence_review"]

if evidence is None:
    missing("evidence_review_summary.json")
else:
    ev1, ev2, ev3, ev4 = st.columns(4)
    ev1.metric("Quotes", evidence.get("rows", "—"))
    ev2.metric("Mechanically valid", fmt(evidence.get("mechanical_validity_rate"), 2))
    ev3.metric("Clearly supports", fmt(evidence.get("pedagogical_clear_rate"), 4))
    ev4.metric("Partial", fmt(evidence.get("pedagogical_partial_rate"), 4))

    st.caption(
        "100 % of quotes are exact substrings, but only "
        f"{fmt(evidence.get('pedagogical_clear_rate'), 3)} were judged to clearly "
        "support their competency. Mechanical validity is not pedagogical "
        "sufficiency."
    )

st.divider()

# -- errors and graph ------------------------------------------------------

st.subheader("7 · Error analysis and hierarchy warnings")

errors = results["error_summary"]
graph = results["graph_check"]

err_col, graph_col = st.columns(2)

with err_col:
    st.markdown("**Error categories**")

    if errors is None:
        missing("error_summary.json")
    else:
        counts = errors.get("category_counts", {}) or {}

        for key in (
            "correct_prediction",
            "overprediction",
            "parent_child_redundancy",
            "llm_wrong_selection",
            "retrieval_failure",
            "underprediction",
            "llm_missed_gold_label",
            "exact_but_weak_evidence",
            "ambiguous_gold",
        ):
            if key in counts:
                st.markdown(f"- `{key}` — **{counts[key]}**")

        st.caption(
            "These flags overlap and are **not** a partition of the 35 "
            "fragments. `llm_missed_gold_label = 0` is what identifies the "
            "single miss as a retrieval failure."
        )

with graph_col:
    st.markdown("**Minimal hierarchy check**")

    if graph is None:
        missing("graph_check_summary.json")
    else:
        st.markdown(
            f"- Fragments checked — **{graph.get('fragments_checked', '—')}**"
        )
        st.markdown(
            "- Parent-child redundancy — "
            f"**{graph.get('fragments_with_parent_child_redundancy', '—')}** fragment(s)"
        )
        st.markdown(
            "- Granularity conflicts — "
            f"**{graph.get('fragments_with_granularity_conflict', '—')}**"
        )
        st.markdown(
            "- Invalid hierarchy references — "
            f"**{graph.get('invalid_hierarchy_references', '—')}**"
        )
        st.markdown(
            f"- Most frequent redundant parent — `{graph.get('most_frequent_redundant_parent', '—')}`"
        )

        st.caption(
            "Warnings only. "
            f"`original_predictions_modified = {graph.get('original_predictions_modified')}` — "
            "the child-preference ablation is a separate post-hoc output and "
            "never overwrote the model's predictions."
        )

sidebar_context()
