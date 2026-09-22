"""Shared bootstrap and rendering helpers for the frozen-corpus teacher app.

This module is deliberately not a Streamlit page. It sits beside ``Home.py``
rather than inside ``app/pages/`` so Streamlit does not list it in the sidebar.

All heavy lifting lives in ``moodle_competency.corpus_app``; this file only
resolves paths, caches the load, and formats values for display.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st  # noqa: E402

from moodle_competency.corpus_app import (  # noqa: E402
    CorpusData,
    CorpusPaths,
    decision_for,
    load_corpus_reviews,
)

DECISION_BADGE = {
    "accept": "✅ ACCEPTED",
    "reject": "❌ REJECTED",
    "modify": "✏️ MODIFIED",
    "add": "➕ ADDED",
    "pending": "⏳ pending",
}

RATING_LABEL = {
    "0": "0 — does not justify the competency",
    "1": "1 — partially relevant / ambiguous",
    "2": "2 — clearly supports the competency",
}

READ_ONLY_NOTE = (
    "This interface never writes to Moodle, to the human-reviewed reference, "
    "to the Gemini output, to the evidence review, or to any metric file. "
    "The only file it writes is the teacher review CSV."
)


def paths() -> CorpusPaths:
    return CorpusPaths(PROJECT_ROOT)


@st.cache_data(show_spinner=False)
def _load_corpus_cached(root: str) -> CorpusData:
    return CorpusData.load(Path(root))


def corpus() -> CorpusData:
    """The frozen research corpus, cached across reruns."""

    return _load_corpus_cached(str(PROJECT_ROOT))


def reviews() -> list[dict[str, str]]:
    """Stored teacher reviews, read fresh so a save is visible immediately."""

    return load_corpus_reviews(paths().corpus_reviews)


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)

    if subtitle:
        st.caption(subtitle)


def sidebar_context() -> None:
    """Identical sidebar footer on every page: scope and safety statement."""

    with st.sidebar:
        st.divider()
        st.caption(
            "**Frozen research corpus** — 20 resources · 35 fragments · "
            "13 UTC GI competencies · 2 courses."
        )
        st.caption(READ_ONLY_NOTE)


def reviewer_input(key: str) -> tuple[str, str]:
    """Reviewer name and role, remembered across pages in the session."""

    with st.sidebar:
        st.subheader("Reviewer")
        name = st.text_input(
            "Your name",
            value=st.session_state.get("reviewer_name", ""),
            key=f"reviewer_name_{key}",
            help="Required. Reviews are never stored anonymously.",
        )
        role = st.selectbox(
            "Your role",
            options=["teacher", "supervisor", "researcher"],
            index=["teacher", "supervisor", "researcher"].index(
                st.session_state.get("reviewer_role", "teacher")
            ),
            key=f"reviewer_role_{key}",
            help=(
                "Recorded honestly. A researcher review is not teacher "
                "validation and is reported separately."
            ),
        )

    st.session_state["reviewer_name"] = name
    st.session_state["reviewer_role"] = role
    return name, role


def format_confidence(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def format_rank(value: Any) -> str:
    return "not retrieved" if value is None else f"#{value}"


def format_ranks(values: Sequence[Any]) -> str:
    if not values:
        return "—"

    return ", ".join(format_rank(value) for value in values)


def decision_badge(decision: str) -> str:
    return DECISION_BADGE.get(decision, DECISION_BADGE["pending"])


def current_decision(
    stored_reviews: Sequence[Mapping[str, Any]],
    resource_id: str,
    competency_id: str,
) -> str:
    return decision_for(stored_reviews, resource_id, competency_id)


def hierarchy_caption(hierarchy: Mapping[str, Any]) -> str:
    """One line of framework context for a competency."""

    if hierarchy.get("is_parent"):
        children = ", ".join(hierarchy.get("child_ids", []))
        return f"Top-level parent competency. Children: {children or 'none'}."

    parent_id = hierarchy.get("parent_id") or ""

    if parent_id:
        parent_name = hierarchy.get("parent_shortname") or ""
        return f"Child competency. Parent: {parent_id} — {parent_name}"

    return "No hierarchy relation recorded in the framework."


def render_evidence(quotes: Sequence[str], ratings: Sequence[str] = ()) -> None:
    """Show exact evidence quotes, plus any human pedagogical rating."""

    if not quotes:
        st.caption("No evidence quote recorded.")
        return

    for index, quote in enumerate(quotes):
        st.markdown(f"> {quote}")

        if index < len(ratings):
            st.caption(f"Human evidence rating: {RATING_LABEL.get(ratings[index], ratings[index])}")

    st.caption(
        "Every quote above was validated as an exact substring of the "
        "fragment text at pipeline time."
    )


def render_graph_warnings(warnings: Sequence[str]) -> None:
    for warning in warnings:
        st.warning(warning, icon="⚠️")


def resource_label(resource: Mapping[str, Any]) -> str:
    resource_id = resource.get("resource_id", "")
    title = resource.get("title", "")
    return f"{resource_id} — {title}" if title else str(resource_id)


def missing_file_notice(label: str, path: Path) -> None:
    st.info(
        f"{label} is not present yet (`{path.relative_to(PROJECT_ROOT)}`). "
        "Nothing is inferred in its place."
    )
