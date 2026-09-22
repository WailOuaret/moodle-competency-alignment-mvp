"""Section O — a minimal view of what teachers have actually validated.

Deliberately small: both directions of the validated mapping, simple counts,
unmapped resources and uncovered competencies. Nothing else. No
recommendations, no learning paths, no taught-versus-assessed analytics.

An unreviewed prediction is not coverage, so this page shows nothing until a
human decision exists.
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
    page_header,
    paths,
    reviews,
    sidebar_context,
)
from moodle_competency.coverage import build_coverage  # noqa: E402

st.set_page_config(page_title="Validated Coverage", page_icon="🗺️", layout="wide")

data = corpus()
stored_reviews = reviews()
review_paths = paths()

page_header(
    "Validated coverage",
    "What teachers have confirmed — not what the model proposed",
)

coverage = build_coverage(
    stored_reviews,
    data.resources,
    data.competency_ids_hierarchical(),
)

st.info(
    coverage["definition_note"],
    icon="✅",
)

if coverage["status"] == "WAITING_FOR_HUMAN":
    st.warning(
        "No validated mapping exists yet, so there is nothing to show. "
        "Coverage is deliberately **not** filled in from the model's "
        "predictions — an unreviewed suggestion is not coverage.\n\n"
        "Record decisions on the **2 Teacher Review** page first.",
        icon="⏳",
    )
    st.caption(coverage["scope_note"])
    sidebar_context()
    st.stop()

# -- headline --------------------------------------------------------------

col1, col2, col3 = st.columns(3)
col1.metric("Validated mappings", coverage["validated_mapping_count"])
col2.metric(
    "Resources with coverage",
    f"{coverage['mapped_resource_count']} / {coverage['resource_count']}",
)
col3.metric(
    "Competencies covered",
    f"{coverage['covered_competency_count']} / {coverage['competency_count']}",
)

st.divider()

# -- competency -> resources ----------------------------------------------

st.subheader("Competency → validated resources")

for competency_id, resource_ids in coverage["competency_to_resources"].items():
    shortname = data.competency_shortname(competency_id)

    if resource_ids:
        with st.expander(
            f"`{competency_id}` — {shortname} · {len(resource_ids)} resource(s)"
        ):
            for resource_id in resource_ids:
                resource = data.resources_by_id.get(resource_id, {})
                st.markdown(
                    f"- `{resource_id}` — {resource.get('title', '')} "
                    f"({resource.get('course_shortname', '')}, "
                    f"{resource.get('resource_type', '')})"
                )
    else:
        st.markdown(f"`{competency_id}` — {shortname} · **no validated resource**")

st.divider()

# -- resource -> competencies ---------------------------------------------

st.subheader("Resource → validated competencies")

for resource_id, competency_ids in coverage["resource_to_competencies"].items():
    resource = data.resources_by_id.get(resource_id, {})
    title = resource.get("title", resource_id)

    if competency_ids:
        st.markdown(
            f"**`{resource_id}`** — {title} → "
            + ", ".join(f"`{value}`" for value in competency_ids)
        )
    else:
        st.markdown(f"`{resource_id}` — {title} → *no validated competency*")

st.divider()

# -- counts ----------------------------------------------------------------

count_col1, count_col2 = st.columns(2)

with count_col1:
    st.subheader("Validated mappings by course")

    for course, count in coverage["validated_by_course"].items():
        st.markdown(f"- **{course}** — {count}")

with count_col2:
    st.subheader("Validated mappings by section")

    for section, count in coverage["validated_by_section"].items():
        st.markdown(f"- **{section}** — {count}")

st.divider()

# -- gaps ------------------------------------------------------------------

gap_col1, gap_col2 = st.columns(2)

with gap_col1:
    st.subheader("Resources with no validated competency")

    unmapped = coverage["unmapped_resources"]

    if not unmapped:
        st.success("Every resource has at least one validated competency.")
    else:
        for resource_id in unmapped:
            resource = data.resources_by_id.get(resource_id, {})
            st.markdown(f"- `{resource_id}` — {resource.get('title', '')}")

with gap_col2:
    st.subheader("Competencies with no validated resource")

    uncovered = coverage["competencies_without_validated_resources"]

    if not uncovered:
        st.success("Every competency has at least one validated resource.")
    else:
        for competency_id in uncovered:
            st.markdown(
                f"- `{competency_id}` — {data.competency_shortname(competency_id)}"
            )

st.divider()
st.caption(coverage["scope_note"])
st.caption(
    f"Source: `{review_paths.corpus_reviews.relative_to(PROJECT_ROOT)}`"
)

sidebar_context()
