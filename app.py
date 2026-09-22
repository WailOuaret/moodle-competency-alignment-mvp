"""Teacher-facing Streamlit entry point.

Launch from the project root:

    streamlit run app.py

This interface does not modify frozen research experiment files.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from moodle_competency.teacher_app_pages import (
    render_analyze_resource,
    render_competency_resources,
    render_research_results,
    render_review_history,
    render_review_suggestions,
)


st.set_page_config(
    page_title="Learning Resource → Competencies",
    layout="wide",
)


def _page_analyze_resource() -> None:
    render_analyze_resource(st)


def _page_review_suggestions() -> None:
    render_review_suggestions(st)


def _page_competency_resources() -> None:
    render_competency_resources(st)


def _page_review_history() -> None:
    render_review_history(st)


def _page_research_results() -> None:
    render_research_results(st)


pg = st.navigation(
    [
        st.Page(
            _page_analyze_resource,
            title="Analyze Resource",
            default=True,
        ),
        st.Page(
            _page_review_suggestions,
            title="Review Suggestions",
        ),
        st.Page(
            _page_competency_resources,
            title="Competency → Resources",
        ),
        st.Page(
            _page_review_history,
            title="Review History / Progress",
        ),
        st.Page(
            _page_research_results,
            title="Research Results",
        ),
    ]
)
pg.run()
