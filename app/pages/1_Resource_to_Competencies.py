"""View 2 — Function A: one resource to its predicted competencies.

Read-only. Every field shown here comes from a frozen pipeline file; nothing
on this page is computed for display beyond formatting.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st  # noqa: E402

from _shared import (  # noqa: E402
    corpus,
    current_decision,
    decision_badge,
    format_confidence,
    format_rank,
    hierarchy_caption,
    page_header,
    render_evidence,
    render_graph_warnings,
    resource_label,
    reviews,
    sidebar_context,
)

st.set_page_config(
    page_title="Resource → Competencies",
    page_icon="📄",
    layout="wide",
)

data = corpus()
stored_reviews = reviews()

page_header(
    "Resource → competencies",
    "Function A · what the pipeline proposed for each resource, and why",
)

courses = [c["course_shortname"] for c in data.courses()]

left, right = st.columns([1, 2])

with left:
    course = st.selectbox("Course", options=courses)

resources = data.resources_for_course(course)

with right:
    resource = st.selectbox(
        "Resource",
        options=resources,
        format_func=resource_label,
    )

if resource is None:
    st.info("No resource selected.")
    st.stop()

resource_id = resource["resource_id"]

st.divider()

st.subheader(resource.get("title", resource_id))
st.caption(
    f"`{resource_id}` · type `{resource.get('resource_type')}` · "
    f"course {course} · activity *{resource.get('activity_name', '')}*"
)

reference = data.reference_by_resource.get(resource_id, {})

if reference:
    reference_ids = reference.get("reference_competency_ids", []) or []
    st.info(
        "**Human-reviewed reference for this resource:** "
        + (", ".join(f"`{value}`" for value in reference_ids) or "none")
        + "  \nDerived by taking the union of the human-reviewed labels of this "
        "resource's fragments. It is shown for orientation and is not a "
        "second, independent annotation.",
        icon="📌",
    )

prediction = data.predictions_by_resource.get(resource_id, {})
predicted = prediction.get("predicted_competencies", []) or []

if not predicted:
    st.warning("The pipeline predicted no competency for this resource.")

# -- resource-level suggestions -------------------------------------------

for entry in predicted:
    competency_id = entry.get("competency_id", "")
    shortname = data.competency_shortname(competency_id)
    decision = current_decision(stored_reviews, resource_id, competency_id)

    with st.container(border=True):
        head_left, head_right = st.columns([3, 1])

        with head_left:
            st.markdown(f"### `{competency_id}` — {shortname}")

        with head_right:
            st.markdown(f"**{decision_badge(decision)}**")

        st.caption(data.competency_description(competency_id))

        hierarchy = data.hierarchy_context(competency_id)
        st.caption(f"🌳 {hierarchy_caption(hierarchy)}")

        stat1, stat2, stat3 = st.columns(3)
        stat1.metric("Max confidence", format_confidence(entry.get("max_confidence")))
        stat2.metric("Mean confidence", format_confidence(entry.get("mean_confidence")))
        stat3.metric("Supporting fragments", entry.get("support_count", 0))

        fragment_ids = entry.get("fragment_ids", []) or []
        warnings: list[str] = []

        for fragment_id in fragment_ids:
            warnings.extend(data.graph_warning_labels(fragment_id, competency_id))

        render_graph_warnings(sorted(set(warnings)))

        st.markdown("**Supporting fragments and evidence**")

        for fragment_id in fragment_ids:
            fragment = data.fragments_by_id.get(fragment_id, {})
            rank = data.bm25_rank(fragment_id, competency_id)

            st.markdown(
                f"`{fragment_id}` · BM25 rank {format_rank(rank)}"
            )

            with st.expander("Fragment text"):
                st.text(fragment.get("text", ""))

            fragment_rows = [
                row
                for row in data.fragment_predictions(fragment_id)
                if row["competency_id"] == competency_id
            ]

            for row in fragment_rows:
                if row.get("reason"):
                    st.caption(f"Model reason: {row['reason']}")

                render_evidence(
                    row.get("evidence", []),
                    data.evidence_ratings(fragment_id, competency_id),
                )

st.divider()

# -- fragment-level detail -------------------------------------------------

st.subheader("Fragment-level detail")
st.caption(
    "The model works at fragment level; the cards above are the aggregation of "
    "these fragment decisions up to the resource."
)

for fragment in data.fragments_for_resource(resource_id):
    fragment_id = fragment["fragment_id"]
    rows = data.fragment_predictions(fragment_id)

    with st.expander(
        f"`{fragment_id}` · {len(rows)} predicted competency(ies)"
    ):
        st.text(fragment.get("text", ""))

        st.markdown("**BM25 Top-5 candidate set**")

        for candidate in data.bm25_candidates_for_fragment(fragment_id):
            candidate_id = candidate.get("idnumber", "")
            chosen = any(row["competency_id"] == candidate_id for row in rows)
            marker = "✔️ selected" if chosen else "— not selected"
            st.markdown(
                f"{candidate.get('rank')}. `{candidate_id}` "
                f"(score {candidate.get('bm25_score')}) {marker}"
            )

        if data.fragment_abstained(fragment_id):
            st.warning("The model abstained on this fragment.")

        for row in rows:
            st.markdown(
                f"**`{row['competency_id']}`** — {row['competency_shortname']} "
                f"· confidence {format_confidence(row['confidence'])} "
                f"· BM25 {format_rank(row['bm25_rank'])}"
            )
            render_evidence(
                row.get("evidence", []),
                data.evidence_ratings(fragment_id, row["competency_id"]),
            )

sidebar_context()
