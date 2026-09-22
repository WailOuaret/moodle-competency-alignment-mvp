from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from moodle_competency.teacher_app_pages import render_review_history

st.set_page_config(page_title="Review History / Progress", layout="wide")
render_review_history(st)
