"""View 4 — Function B: one competency to the resources that support it.

This is the inverse direction the supervisors asked for: starting from a
competency in the framework, which learning resources cover it, and on what
evidence. Read-only.
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
    hierarchy_caption,
    page_header,
    render_evidence,
    reviews,
    sidebar_context,
)

st.set_page_config(
    page_title="Competency → Resources",
    page_icon="🎯",
    layout="wide",
)

data = corpus()
stored_reviews = reviews()

page_header(
    "Competency → resources",
    "Function B · which learning resources cover a given competency",
)

competency_options = data.competency_ids_hierarchical()

competency_id = st.selectbox(
    "Competency",
    options=competency_options,
    format_func=data.competency_label,
)

entry = data.competency_resources(competency_id)
hierarchy = data.hierarchy_context(competency_id)

st.divider()

st.subheader(f"`{competency_id}` — {data.competency_shortname(competency_id)}")
st.caption(data.competency_description(competency_id))
st.caption(f"🌳 {hierarchy_caption(hierarchy)}")

resources = entry.get("resources", []) or []

col1, col2, col3 = st.columns(3)
col1.metric("Matching resources", entry.get("match_count", len(resources)))
col2.metric(
    "Courses covered",
    len({r.get("course_shortname") for r in resources}),
)
col3.metric(
    "Total supporting fragments",
    sum(int(r.get("support_count", 0) or 0) for r in resources),
)

if hierarchy["is_parent"]:
    st.info(
        "This is a **top-level parent** competency. In the human-reviewed "
        "reference, all 38 labels were assigned at child level, so a parent "
        "prediction here is usually redundant with one of its children. "
        "The graph check flags exactly this pattern.",
        icon="🌳",
    )

if not resources:
    st.warning("No resource is currently predicted for this competency.")
    st.stop()

st.markdown("### Supporting resources")

for resource in resources:
    resource_id = resource.get("resource_id", "")
    decision = current_decision(stored_reviews, resource_id, competency_id)

    with st.container(border=True):
        head_left, head_right = st.columns([3, 1])

        with head_left:
            st.markdown(f"#### {resource.get('resource_title', resource_id)}")
            st.caption(
                f"`{resource_id}` · type `{resource.get('resource_type')}` · "
                f"course {resource.get('course_shortname')}"
            )

        with head_right:
            st.markdown(f"**{decision_badge(decision)}**")

        stat1, stat2 = st.columns(2)
        stat1.metric(
            "Max confidence", format_confidence(resource.get("max_confidence"))
        )
        stat2.metric("Supporting fragments", resource.get("support_count", 0))

        fragment_ids = resource.get("fragment_ids", []) or []

        if fragment_ids:
            st.caption(
                "Supporting fragments: "
                + ", ".join(f"`{value}`" for value in fragment_ids)
            )

        ratings: list[str] = []

        for fragment_id in fragment_ids:
            ratings.extend(data.evidence_ratings(fragment_id, competency_id))

        st.markdown("**Evidence**")
        render_evidence(resource.get("evidence", []) or [], ratings)

        with st.expander("Fragment text"):
            for fragment_id in fragment_ids:
                fragment = data.fragments_by_id.get(fragment_id, {})
                st.markdown(f"`{fragment_id}`")
                st.text(fragment.get("text", ""))

sidebar_context()
