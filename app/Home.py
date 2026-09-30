"""View 1 — course and resource browser over the frozen research corpus.

Launch from the project root:

    streamlit run app/Home.py

This is the teacher validation interface for the frozen research corpus.
It is distinct from the runtime app at ``app.py``, which analyses a new
resource. See docs/TEACHER_INTERFACE_GUIDE.md.
"""

from __future__ import annotations

import streamlit as st

from _shared import (
    corpus,
    page_header,
    resource_label,
    sidebar_context,
)

st.set_page_config(
    page_title="Resource → Competency alignment",
    page_icon="🎓",
    layout="wide",
)

data = corpus()

page_header(
    "Learning resource → competency alignment",
    "Moodle MVP · UTC GI competency framework · human validation interface",
)

st.markdown(
    """
This interface lets a teacher inspect and validate the competency alignments
the pipeline produced for a fixed set of Moodle learning resources.

**What the pipeline did.** Each resource was extracted from Moodle, normalized,
and split into fragments. For every fragment, BM25 retrieved the five most
similar competencies, and a constrained language model chose at most three of
those five, each justified by a quote taken verbatim from the fragment.

**What is asked of you.** On the *Teacher Review* page, accept, reject or
modify each suggested resource-competency alignment. Nothing is decided for
you, and no decision is pre-filled.
"""
)

st.divider()

# -- corpus summary --------------------------------------------------------

courses = data.courses()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Courses", len(courses))
col2.metric("Resources", len(data.resources))
col3.metric("Fragments", len(data.fragments))
col4.metric("Competencies", len(data.competencies))

st.caption(
    "Quiz questions are kept as independent resources rather than collapsed "
    "into their parent quiz, so a question can carry its own competency."
)

# -- competency framework --------------------------------------------------

with st.expander("The 13-competency UTC GI framework used here"):
    for competency_id in data.competency_ids_hierarchical():
        hierarchy = data.hierarchy_context(competency_id)
        shortname = data.competency_shortname(competency_id)

        if hierarchy["is_parent"]:
            st.markdown(f"**{competency_id}** — {shortname}")
        else:
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ `{competency_id}` — {shortname}")

    st.caption(
        "Three parent competencies and ten children. The framework contains no "
        "prerequisite or related-to relations, so none are used anywhere in "
        "this interface."
    )

st.divider()

# -- course browser --------------------------------------------------------

st.subheader("Browse a course")

course_names = [c["course_shortname"] for c in courses]

if not course_names:
    st.error("No courses found in the corpus.")
    st.stop()

selected_course = st.selectbox(
    "Course",
    options=course_names,
    format_func=lambda name: next(
        (
            f"{c['course_shortname']} — {c['course_fullname']}"
            for c in courses
            if c["course_shortname"] == name
        ),
        name,
    ),
)

course = next(c for c in courses if c["course_shortname"] == selected_course)

meta1, meta2, meta3 = st.columns(3)
meta1.metric("Resources", course["resource_count"])
meta2.metric("Pages", course["page_count"])
meta3.metric("Quiz questions", course["quiz_question_count"])

resources = data.resources_for_course(selected_course)

st.markdown(f"### Resources in {selected_course}")

for resource in resources:
    resource_id = resource["resource_id"]
    fragments = data.fragments_for_resource(resource_id)
    prediction = data.predictions_by_resource.get(resource_id, {})
    predicted = prediction.get("predicted_competencies", []) or []

    type_icon = "📄" if resource.get("resource_type") == "page" else "❓"
    header = (
        f"{type_icon} {resource_label(resource)} "
        f"· {len(fragments)} fragment(s) · {len(predicted)} predicted competency(ies)"
    )

    with st.expander(header):
        st.caption(
            f"Type `{resource.get('resource_type')}` · "
            f"activity *{resource.get('activity_name', '')}* · "
            f"section *{resource.get('section_name', '')}*"
        )

        if predicted:
            st.markdown(
                "**Predicted competencies:** "
                + ", ".join(
                    f"`{entry.get('competency_id')}`" for entry in predicted
                )
            )
        else:
            st.markdown("**Predicted competencies:** none")

        reference = data.reference_by_resource.get(resource_id, {})

        if reference:
            reference_ids = reference.get("reference_competency_ids", []) or []
            st.markdown(
                "**Human-reviewed reference (derived for this resource):** "
                + (
                    ", ".join(f"`{value}`" for value in reference_ids)
                    if reference_ids
                    else "none"
                )
            )

        st.markdown("**Fragments**")

        for fragment in fragments:
            st.markdown(f"`{fragment['fragment_id']}` ({fragment['fragment_type']})")
            st.text(fragment.get("text", ""))

st.divider()
st.caption(
    "Next: open **1 Resource to Competencies** to see each suggestion with its "
    "evidence, or **2 Teacher Review** to record decisions."
)

sidebar_context()
