"""View 3 — the teacher records accept / reject / modify / add decisions.

This is the only page in the interface that writes. It writes exactly one
file, ``data/reviews/corpus_teacher_reviews.csv``, atomically, after taking a
timestamped backup of the previous version.

It never pre-fills a decision, never suggests one, and never writes to Moodle,
to the human-reviewed reference, to the Gemini output, to the evidence review,
or to any metric file.
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
    current_decision,
    decision_badge,
    format_confidence,
    format_ranks,
    hierarchy_caption,
    page_header,
    paths,
    render_evidence,
    render_graph_warnings,
    reviewer_input,
    reviews,
    sidebar_context,
)
from moodle_competency.corpus_app import (  # noqa: E402
    CorpusReviewError,
    save_review,
    utc_today,
    validate_review,
)

st.set_page_config(page_title="Teacher Review", page_icon="✍️", layout="wide")

data = corpus()
stored_reviews = reviews()
review_paths = paths()

page_header(
    "Teacher review",
    "Accept, reject or modify each suggested resource-competency alignment",
)

reviewer_name, reviewer_role = reviewer_input("teacher_review")

if reviewer_role == "researcher":
    st.info(
        "Recorded as a **researcher** review. Researcher decisions are reported "
        "separately from teacher validation and are never presented as teacher "
        "validation results.",
        icon="ℹ️",
    )

mappings = data.reviewable_mappings()

# -- filters ---------------------------------------------------------------

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    course_filter = st.selectbox(
        "Course",
        options=["All", *sorted({m["course_shortname"] for m in mappings})],
    )

with filter_col2:
    type_filter = st.selectbox(
        "Resource type",
        options=["All", *sorted({m["resource_type"] for m in mappings})],
    )

with filter_col3:
    status_filter = st.selectbox(
        "Decision status",
        options=["All", "Pending only", "Reviewed only"],
    )


def visible(mapping: dict) -> bool:
    if course_filter != "All" and mapping["course_shortname"] != course_filter:
        return False

    if type_filter != "All" and mapping["resource_type"] != type_filter:
        return False

    decision = current_decision(
        stored_reviews, mapping["resource_id"], mapping["competency_id"]
    )

    if status_filter == "Pending only" and decision != "pending":
        return False

    if status_filter == "Reviewed only" and decision == "pending":
        return False

    return True


shown = [mapping for mapping in mappings if visible(mapping)]

reviewed_total = sum(
    1
    for mapping in mappings
    if current_decision(
        stored_reviews, mapping["resource_id"], mapping["competency_id"]
    )
    != "pending"
)

st.caption(
    f"Showing **{len(shown)}** of **{len(mappings)}** predicted "
    f"resource-competency mappings · {reviewed_total} reviewed so far."
)

if not shown:
    st.info("No mapping matches the current filters.")
    st.stop()

st.divider()

competency_options = data.competency_ids_hierarchical()

for mapping in shown:
    resource_id = mapping["resource_id"]
    competency_id = mapping["competency_id"]
    decision = current_decision(stored_reviews, resource_id, competency_id)

    with st.container(border=True):
        head_left, head_right = st.columns([3, 1])

        with head_left:
            st.markdown(
                f"#### {mapping['resource_title']} → `{competency_id}`"
            )
            st.caption(
                f"`{resource_id}` · {mapping['resource_type']} · "
                f"{mapping['course_shortname']}"
            )

        with head_right:
            st.markdown(f"**{decision_badge(decision)}**")

        st.markdown(f"**{competency_id}** — {mapping['competency_shortname']}")
        st.caption(mapping["competency_description"])
        st.caption(f"🌳 {hierarchy_caption(mapping['hierarchy'])}")

        stat1, stat2, stat3 = st.columns(3)
        stat1.metric("Max confidence", format_confidence(mapping["max_confidence"]))
        stat2.metric("BM25 rank(s)", format_ranks(mapping["bm25_ranks"]))
        stat3.metric("Supporting fragments", mapping["support_count"] or 0)

        render_graph_warnings(mapping["graph_warnings"])

        st.markdown("**Evidence**")
        render_evidence(mapping["evidence"], mapping["evidence_ratings"])

        with st.expander("Fragment text"):
            for fragment_id in mapping["fragment_ids"]:
                fragment = data.fragments_by_id.get(fragment_id, {})
                st.markdown(f"`{fragment_id}`")
                st.text(fragment.get("text", ""))

        # -- decision form -------------------------------------------------

        with st.form(key=f"form_{mapping['review_id']}"):
            st.markdown("**Your decision**")

            chosen = st.radio(
                "Decision",
                options=["accept", "reject", "modify"],
                index=None,
                horizontal=True,
                format_func=str.upper,
                key=f"decision_{mapping['review_id']}",
                help=(
                    "ACCEPT: the competency fits this resource. "
                    "REJECT: it does not. "
                    "MODIFY: replace it with one or more other competencies."
                ),
            )

            replacements = st.multiselect(
                "Replacement competencies (MODIFY only)",
                options=competency_options,
                format_func=data.competency_label,
                key=f"replace_{mapping['review_id']}",
            )

            relevance = st.select_slider(
                "Was the evidence quote useful to you?",
                options=["", "0", "1", "2"],
                value="",
                format_func=lambda value: {
                    "": "not answered",
                    "0": "0 — did not justify it",
                    "1": "1 — partly",
                    "2": "2 — clearly justified it",
                }[value],
                key=f"relevance_{mapping['review_id']}",
            )

            comment = st.text_area(
                "Comment (optional)",
                key=f"comment_{mapping['review_id']}",
                placeholder="Why did you decide this?",
            )

            submitted = st.form_submit_button("Save this decision", type="primary")

        if submitted:
            if chosen is None:
                st.error("Choose ACCEPT, REJECT or MODIFY before saving.")
            else:
                try:
                    row = validate_review(
                        resource_id=resource_id,
                        competency_id=competency_id,
                        decision=chosen,
                        reviewer=reviewer_name,
                        review_date=utc_today(),
                        modified_competency_ids=replacements,
                        evidence_relevance=relevance,
                        valid_competency_ids=competency_options,
                        valid_resource_ids=list(data.resources_by_id),
                    )
                    row["fragment_ids"] = ";".join(mapping["fragment_ids"])
                    row["comment"] = comment.strip()

                    result = save_review(
                        path=review_paths.corpus_reviews,
                        backup_dir=review_paths.corpus_review_backups,
                        new_review=row,
                    )
                except CorpusReviewError as error:
                    st.error(str(error))
                else:
                    saved_to = Path(result["path"]).relative_to(PROJECT_ROOT)
                    st.success(
                        f"Saved **{chosen.upper()}** for `{competency_id}` → "
                        f"`{saved_to}` ({result['review_count']} review(s) stored)."
                    )
                    st.rerun()

st.divider()

# -- add a missing competency ---------------------------------------------

st.subheader("Add a competency the model missed")
st.caption(
    "Use this when a resource teaches or assesses a competency that never "
    "appeared among its suggestions. It is stored with decision `add` and "
    "counted separately from the reviewed suggestions."
)

with st.form(key="form_add_missing"):
    add_col1, add_col2 = st.columns(2)

    with add_col1:
        add_resource = st.selectbox(
            "Resource",
            options=sorted(data.resources_by_id),
            format_func=lambda value: (
                f"{value} — {data.resources_by_id[value].get('title', '')}"
            ),
        )

    with add_col2:
        add_competency = st.selectbox(
            "Missing competency",
            options=competency_options,
            format_func=data.competency_label,
        )

    add_comment = st.text_area("Comment (optional)", key="add_comment")
    add_submitted = st.form_submit_button("Save added competency", type="primary")

if add_submitted:
    try:
        row = validate_review(
            resource_id=add_resource,
            competency_id=add_competency,
            decision="add",
            reviewer=reviewer_name,
            review_date=utc_today(),
            valid_competency_ids=competency_options,
            valid_resource_ids=list(data.resources_by_id),
        )
        row["comment"] = add_comment.strip()

        result = save_review(
            path=review_paths.corpus_reviews,
            backup_dir=review_paths.corpus_review_backups,
            new_review=row,
        )
    except CorpusReviewError as error:
        st.error(str(error))
    else:
        st.success(
            f"Added `{add_competency}` for `{add_resource}` "
            f"({result['review_count']} review(s) stored)."
        )
        st.rerun()

sidebar_context()
