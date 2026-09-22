"""Section M — the evidence-usefulness pilot, one case at a time.

Each case is shown in the condition the saved design assigned it:

``A`` the evidence quote is hidden until you ask for it (and whether you asked
      is recorded);
``B`` the evidence quote is shown with the suggestion.

The page times your decision from the moment a case is displayed. It records
only what you enter; it never fills in a decision, a confidence or a comment.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st  # noqa: E402

from _shared import (  # noqa: E402
    PROJECT_ROOT,
    page_header,
    reviewer_input,
    sidebar_context,
)
from moodle_competency.teacher_study import (  # noqa: E402
    CONDITION_WITH_EVIDENCE,
    CONDITION_WITHOUT_EVIDENCE,
    TeacherStudyError,
    load_study_cases,
    load_study_responses,
    summarize_responses,
    upsert_response,
    validate_response,
    write_study_responses,
)

st.set_page_config(
    page_title="Evidence Usefulness Pilot",
    page_icon="🧪",
    layout="wide",
)

STUDY_DIR = PROJECT_ROOT / "data" / "studies"
CASES_PATH = STUDY_DIR / "teacher_study_cases.csv"
RESPONSES_PATH = STUDY_DIR / "teacher_study_responses.csv"

page_header(
    "Evidence usefulness pilot",
    "Does seeing the exact evidence quote change your judgement?",
)

cases = load_study_cases(CASES_PATH)

if not cases:
    st.info(
        "No study design exists yet. Create one with:\n\n"
        "```bash\npython scripts/27_prepare_teacher_study.py\n```",
        icon="🧪",
    )
    st.stop()

reviewer_name, reviewer_role = reviewer_input("pilot")

st.markdown(
    """
You will see a suggested competency for one piece of course material at a time.
Some cases show you the evidence quote the model used; others hide it until you
choose to look. **Both are fine** — answer as you naturally would.

Please decide reasonably promptly: the time you take is part of what is being
measured. There is no right answer and nothing is graded.
"""
)

if reviewer_role == "researcher":
    st.info(
        "You are recorded as a **researcher**. With no teacher or supervisor "
        "taking part, the result is labelled a *researcher pilot* rather than a "
        "teacher study.",
        icon="ℹ️",
    )

responses = load_study_responses(RESPONSES_PATH)
answered = {
    (r.get("case_id", ""), r.get("reviewer", "")) for r in responses
}

remaining = [
    case
    for case in cases
    if (case.get("case_id", ""), reviewer_name) not in answered
]

col1, col2, col3 = st.columns(3)
col1.metric("Cases in design", len(cases))
col2.metric("You have answered", len(cases) - len(remaining))
col3.metric("Remaining", len(remaining))

st.progress((len(cases) - len(remaining)) / len(cases))

st.divider()

if not reviewer_name.strip():
    st.warning(
        "Enter your name in the sidebar before starting. Responses are never "
        "stored anonymously.",
        icon="✍️",
    )
    st.stop()

if not remaining:
    st.success("You have answered every case. Thank you.", icon="✅")

    summary = summarize_responses(responses, cases)

    st.subheader("Descriptive summary so far")
    st.caption(
        f"Label: **{summary['study_label']}** · "
        f"{summary['response_count']} response(s) from "
        f"{len(summary['reviewers'])} reviewer(s)."
    )

    for condition in (CONDITION_WITHOUT_EVIDENCE, CONDITION_WITH_EVIDENCE):
        block = summary["by_condition"][condition]
        name = (
            "A — evidence hidden initially"
            if condition == CONDITION_WITHOUT_EVIDENCE
            else "B — evidence shown"
        )

        st.markdown(f"**Condition {name}** · n = {block['n']}")

        if block["n"]:
            stat1, stat2, stat3 = st.columns(3)
            stat1.metric(
                "Median seconds",
                f"{block['median_elapsed_seconds']:.1f}"
                if block["median_elapsed_seconds"] is not None
                else "—",
            )
            stat2.metric(
                "Median confidence",
                f"{block['median_confidence']:.1f}"
                if block["median_confidence"] is not None
                else "—",
            )
            stat3.metric("Acceptance", f"{block['acceptance_rate']:.0%}")

    st.caption(
        "Descriptive only. No significance test is computed: the sample size "
        "and design do not support an inferential claim."
    )

    sidebar_context()
    st.stop()

# -- present the next case -------------------------------------------------

case = remaining[0]
case_id = case["case_id"]
condition = case["condition"].upper()
timer_key = f"pilot_start_{case_id}_{reviewer_name}"
reveal_key = f"pilot_revealed_{case_id}_{reviewer_name}"

if timer_key not in st.session_state:
    st.session_state[timer_key] = datetime.now(timezone.utc)

st.session_state.setdefault(reveal_key, False)

st.subheader(f"Case {len(cases) - len(remaining) + 1} of {len(cases)}")
st.caption(
    f"Condition **{condition}** · "
    + (
        "the evidence quote is hidden until you ask for it"
        if condition == CONDITION_WITHOUT_EVIDENCE
        else "the evidence quote is shown below"
    )
)

with st.container(border=True):
    st.markdown("#### Course material")
    st.text(case.get("fragment_text", ""))

    st.markdown("#### Suggested competency")
    st.markdown(
        f"**`{case.get('competency_id')}`** — {case.get('competency_shortname', '')}"
    )

    st.markdown("#### Evidence")

    evidence_quote = case.get("evidence_quote", "")

    if condition == CONDITION_WITH_EVIDENCE:
        st.markdown(f"> {evidence_quote}")
        evidence_shown = True
        evidence_opened = True
    else:
        if st.session_state[reveal_key]:
            st.markdown(f"> {evidence_quote}")
            st.caption("You chose to see the evidence. That choice is recorded.")
        else:
            st.caption("The evidence quote is hidden for this case.")

            if st.button("Show me the evidence quote", key=f"reveal_btn_{case_id}"):
                st.session_state[reveal_key] = True
                st.rerun()

        evidence_shown = bool(st.session_state[reveal_key])
        evidence_opened = bool(st.session_state[reveal_key])

# -- record the decision ---------------------------------------------------

with st.form(key=f"pilot_form_{case_id}"):
    st.markdown("#### Your judgement")

    decision = st.radio(
        "Does this competency fit this material?",
        options=["accept", "reject", "modify"],
        index=None,
        horizontal=True,
        format_func={
            "accept": "ACCEPT — it fits",
            "reject": "REJECT — it does not",
            "modify": "MODIFY — another competency fits better",
        }.get,
    )

    confidence = st.slider(
        "How confident are you in that judgement?",
        min_value=1,
        max_value=5,
        value=3,
        help="1 = not at all confident, 5 = completely confident.",
    )

    comment = st.text_area("Comment (optional)")

    submitted = st.form_submit_button("Save and continue", type="primary")

if submitted:
    if decision is None:
        st.error("Choose ACCEPT, REJECT or MODIFY before saving.")
    else:
        started = st.session_state[timer_key]
        ended = datetime.now(timezone.utc)

        try:
            response = validate_response(
                case_id=case_id,
                condition=condition,
                reviewer=reviewer_name,
                reviewer_role=reviewer_role,
                decision=decision,
                confidence=confidence,
                evidence_shown=evidence_shown,
                evidence_opened=evidence_opened,
                start_timestamp=started.isoformat(),
                end_timestamp=ended.isoformat(),
                comment=comment,
                valid_case_ids=[c["case_id"] for c in cases],
            )
        except TeacherStudyError as error:
            st.error(str(error))
        else:
            write_study_responses(
                upsert_response(responses, response), RESPONSES_PATH
            )

            st.session_state.pop(timer_key, None)
            st.session_state.pop(reveal_key, None)

            st.success(
                f"Recorded in {float(response['elapsed_seconds']):.1f} s. "
                "Loading the next case."
            )
            st.rerun()

st.divider()
st.caption(
    f"Design: `{CASES_PATH.relative_to(PROJECT_ROOT)}` · "
    f"responses: `{RESPONSES_PATH.relative_to(PROJECT_ROOT)}`. "
    "Exploratory usability exercise on a small stratified sample — not a "
    "controlled study of Moodle teachers."
)

sidebar_context()
