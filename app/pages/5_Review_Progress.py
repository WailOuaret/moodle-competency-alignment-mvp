"""View 5 — how much of the teacher review is done.

Read-only. Counts come from the stored review file; nothing is inferred and no
rate is shown for a population that has not been reviewed.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st  # noqa: E402

from _shared import (  # noqa: E402
    PROJECT_ROOT,
    corpus,
    decision_badge,
    page_header,
    paths,
    reviews,
    sidebar_context,
)
from moodle_competency.corpus_app import review_progress  # noqa: E402

st.set_page_config(page_title="Review Progress", page_icon="📊", layout="wide")

data = corpus()
stored_reviews = reviews()
review_paths = paths()

page_header("Review progress", "How much of the teacher validation is complete")

mappings = data.reviewable_mappings()
progress = review_progress(mappings, stored_reviews)

# -- headline --------------------------------------------------------------

col1, col2, col3 = st.columns(3)
col1.metric("Reviewable mappings", progress["total_mappings"])
col2.metric("Reviewed", progress["reviewed"])
col3.metric("Pending", progress["pending"])

fraction = progress["reviewed_fraction"]

if fraction is None:
    st.info("There is nothing to review.")
    st.stop()

st.progress(fraction, text=f"{fraction:.1%} reviewed")

if progress["reviewed"] == 0:
    st.warning(
        "No teacher decision has been recorded yet. Acceptance, edit and "
        "rejection rates are deliberately not shown, because there is nothing "
        "real to compute them from.",
        icon="⏳",
    )

st.divider()

# -- decisions -------------------------------------------------------------

st.subheader("Decisions recorded")

dec1, dec2, dec3, dec4 = st.columns(4)
dec1.metric(decision_badge("accept"), progress["accepted"])
dec2.metric(decision_badge("reject"), progress["rejected"])
dec3.metric(decision_badge("modify"), progress["modified"])
dec4.metric(decision_badge("add"), progress["added"])

st.caption(
    "`added` mappings were never predicted by the model, so they sit outside "
    "the reviewed-percentage denominator above."
)

if progress["reviewed"] > 0:
    reviewed = progress["reviewed"]
    st.markdown("**Rates among reviewed suggestions**")

    rate1, rate2, rate3 = st.columns(3)
    rate1.metric("Acceptance", f"{progress['accepted'] / reviewed:.1%}")
    rate2.metric("Edit", f"{progress['modified'] / reviewed:.1%}")
    rate3.metric("Rejection", f"{progress['rejected'] / reviewed:.1%}")

    st.caption(
        f"Denominator is the {reviewed} reviewed suggestion(s), not the "
        f"{progress['total_mappings']} predicted mappings."
    )

st.divider()

# -- breakdowns ------------------------------------------------------------

break1, break2 = st.columns(2)

with break1:
    st.subheader("Per course")

    for name, entry in progress["per_course"].items():
        share = entry["reviewed"] / entry["total"] if entry["total"] else 0.0
        st.markdown(
            f"**{name}** — {entry['reviewed']} / {entry['total']} reviewed"
        )
        st.progress(share)

with break2:
    st.subheader("Per resource type")

    for name, entry in progress["per_resource_type"].items():
        share = entry["reviewed"] / entry["total"] if entry["total"] else 0.0
        st.markdown(
            f"**{name}** — {entry['reviewed']} / {entry['total']} reviewed"
        )
        st.progress(share)

st.divider()

# -- reviewers -------------------------------------------------------------

st.subheader("Who reviewed")

if not stored_reviews:
    st.caption("No reviewer has recorded a decision yet.")
else:
    by_reviewer: dict[str, int] = {}

    for review in stored_reviews:
        name = review.get("reviewer", "").strip() or "unrecorded"
        by_reviewer[name] = by_reviewer.get(name, 0) + 1

    for name in sorted(by_reviewer):
        st.markdown(f"- **{name}** — {by_reviewer[name]} decision(s)")

    st.caption(
        "Role is recorded per reviewer in the study and summary scripts. A "
        "researcher review is never reported as teacher validation."
    )

st.divider()

# -- pending list ----------------------------------------------------------

with st.expander("Which mappings are still pending?"):
    from _shared import current_decision

    pending = [
        mapping
        for mapping in mappings
        if current_decision(
            stored_reviews, mapping["resource_id"], mapping["competency_id"]
        )
        == "pending"
    ]

    if not pending:
        st.success("Nothing is pending.")
    else:
        for mapping in pending:
            st.markdown(
                f"- `{mapping['resource_id']}` → `{mapping['competency_id']}` "
                f"({mapping['course_shortname']}, {mapping['resource_type']})"
            )

st.caption(
    f"Review file: `{review_paths.corpus_reviews.relative_to(PROJECT_ROOT)}` "
    + ("(not created yet)" if not review_paths.corpus_reviews.exists() else "")
)

sidebar_context()
