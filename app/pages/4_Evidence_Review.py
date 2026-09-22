"""View — the closed pedagogical evidence review (Human Gate 2), read-only.

The 83 ratings on this page were produced by a human reviewer in the terminal
helper ``scripts/review_evidence_pedagogically.py``. This page displays them
and never writes to ``data/reviews/evidence_review.csv``.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st  # noqa: E402

from _shared import (  # noqa: E402
    PROJECT_ROOT,
    RATING_LABEL,
    corpus,
    missing_file_notice,
    page_header,
    paths,
    sidebar_context,
)

st.set_page_config(page_title="Evidence Review", page_icon="🔍", layout="wide")

data = corpus()
review_paths = paths()

page_header(
    "Evidence review",
    "Human Gate 2 · is each exact quote pedagogically sufficient?",
)

rows = data.evidence_reviews

if not rows:
    missing_file_notice("The evidence review", review_paths.evidence_review)
    st.stop()

st.markdown(
    """
Every competency the model selected had to be justified by a quote copied
**verbatim** from the fragment. A validator checked that mechanically, and
100 % of the quotes passed.

Mechanical exactness is not the same as pedagogical sufficiency: a quote can be
a real substring and still fail to justify the competency. A human reviewer
therefore rated each quote on a three-point scale.
"""
)

ratings = [row.get("pedagogical_rating", "").strip() for row in rows]
rated = [value for value in ratings if value]
counts = Counter(rated)
mechanical_valid = sum(
    1 for row in rows if row.get("mechanically_valid", "").strip().lower() == "true"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Evidence quotes", len(rows))
col2.metric("Mechanically valid", f"{mechanical_valid}/{len(rows)}")
col3.metric("Human-rated", f"{len(rated)}/{len(rows)}")
col4.metric(
    "Clearly supports (2)",
    f"{counts.get('2', 0)} ({counts.get('2', 0) / len(rows):.1%})" if rows else "—",
)

if len(rated) < len(rows):
    st.warning(
        f"{len(rows) - len(rated)} quote(s) are still unrated. Human Gate 2 is "
        "open. Run `python scripts/review_evidence_pedagogically.py` to "
        "continue. Nothing is rated automatically.",
        icon="⏳",
    )
else:
    st.success("Human Gate 2 is complete: every quote carries a human rating.", icon="✅")

st.divider()

# -- distribution ----------------------------------------------------------

st.subheader("Rating distribution")

for value in ("2", "1", "0"):
    count = counts.get(value, 0)
    share = count / len(rows) if rows else 0.0
    st.markdown(f"**{RATING_LABEL[value]}** — {count} quote(s), {share:.1%}")
    st.progress(share)

reviewers = sorted({row.get("reviewer", "").strip() for row in rows if row.get("reviewer")})
dates = sorted({row.get("review_date", "").strip() for row in rows if row.get("review_date")})

st.caption(
    f"Reviewer(s): {', '.join(reviewers) or 'unrecorded'} · "
    f"date(s): {', '.join(dates) or 'unrecorded'}. "
    "There is one rater, so no inter-rater agreement is measured."
)

st.divider()

# -- browse ----------------------------------------------------------------

st.subheader("Browse the rated quotes")

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    rating_filter = st.selectbox(
        "Rating",
        options=["All", "2", "1", "0", "unrated"],
        format_func=lambda value: RATING_LABEL.get(value, value),
    )

with filter_col2:
    competency_filter = st.selectbox(
        "Competency",
        options=["All", *sorted({row.get("competency_id", "") for row in rows})],
    )


def visible(row: dict) -> bool:
    rating = row.get("pedagogical_rating", "").strip()

    if rating_filter == "unrated" and rating:
        return False

    if rating_filter not in {"All", "unrated"} and rating != rating_filter:
        return False

    if competency_filter != "All" and row.get("competency_id") != competency_filter:
        return False

    return True


shown = [row for row in rows if visible(row)]
st.caption(f"Showing {len(shown)} of {len(rows)} quotes.")

for row in shown:
    rating = row.get("pedagogical_rating", "").strip()
    label = RATING_LABEL.get(rating, "unrated")

    with st.expander(
        f"`{row.get('fragment_id')}` → `{row.get('competency_id')}` · {label}"
    ):
        st.caption(
            f"Resource `{row.get('resource_id')}` · "
            f"{row.get('competency_shortname', '')}"
        )

        st.markdown("**Evidence quote**")
        st.markdown(f"> {row.get('evidence_quote', '')}")

        st.caption(
            f"Mechanically valid: `{row.get('mechanically_valid')}` · "
            f"offsets {row.get('evidence_start')}–{row.get('evidence_end')} · "
            f"offset_valid `{row.get('offset_valid')}`"
        )

        if row.get("comment", "").strip():
            st.info(f"Reviewer comment: {row['comment']}", icon="💬")

        st.markdown("**Fragment text**")
        st.text(row.get("fragment_text", ""))

st.divider()
st.caption(
    f"Source: `{review_paths.evidence_review.relative_to(PROJECT_ROOT)}` · "
    "this page is read-only."
)

sidebar_context()
