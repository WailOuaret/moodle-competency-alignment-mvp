"""Streamlit page renderers for the teacher runtime interface."""

from __future__ import annotations

from typing import Any

from moodle_competency.resource_ingestion import (
    EmptyResourceError,
    MoodleResourceUnavailableError,
    PdfTextUnavailableError,
    ResourceIngestionError,
    UnsupportedFileError,
    ingest_existing_moodle_resource,
    ingest_pasted_text,
    ingest_uploaded_file,
)
from moodle_competency.runtime_analysis import (
    ANALYSIS_STAGES,
    BackendUnavailableError,
    NoUsableFragmentsError,
    analyze_runtime_resource,
    create_runtime_backend,
    load_competencies,
)
from moodle_competency.runtime_storage import ensure_runtime_dirs
from moodle_competency.teacher_reviews import (
    InvalidReviewError,
    persist_runtime_review,
)
from moodle_competency.teacher_ui import (
    ANALYZE_EXPLANATION,
    competency_resource_index,
    configured_backend_choices,
    filter_suggestion_rows,
    format_backend_model,
    format_bm25_ranks,
    highlight_quote,
    history_summary,
    load_research_results,
    load_ui_state,
    moodle_course_options,
    moodle_resource_options,
    review_history_table_rows,
    review_label_for_role,
)


def _review_form(
    st: Any,
    *,
    analysis: dict[str, Any],
    card: dict[str, Any],
    catalogue_ids: list[str],
    paths,
) -> None:
    key = f"{analysis['analysis_id']}|{card['competency_id']}"
    decision = st.radio(
        "Review decision",
        ["ACCEPT", "REJECT", "MODIFY"],
        index=None,
        horizontal=True,
        key=f"decision_{key}",
    )
    replacement = None

    if decision == "MODIFY":
        replacement = st.selectbox(
            "Replacement competency",
            catalogue_ids,
            key=f"replace_{key}",
        )

    comment = st.text_area("Comment", key=f"comment_{key}")
    reviewer_name = st.text_input(
        "Reviewer name",
        key=f"name_{key}",
    )
    reviewer_role = st.selectbox(
        "Reviewer role",
        ["researcher", "teacher", "supervisor"],
        key=f"role_{key}",
        help=(
            "Use researcher if Wail is testing. "
            "Only actual teachers should choose teacher."
        ),
    )
    st.caption(review_label_for_role(reviewer_role))

    if st.button("Save decision", key=f"save_{key}"):
        if decision not in {"ACCEPT", "REJECT", "MODIFY"}:
            st.error("Select ACCEPT, REJECT, or MODIFY.")
            return

        try:
            persist_runtime_review(
                analysis_id=str(analysis["analysis_id"]),
                runtime_resource_id=str(card["runtime_resource_id"]),
                competency_id=str(card["competency_id"]),
                decision=decision,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
                catalogue_ids=catalogue_ids,
                replacement_competency_id=replacement,
                comment=comment,
                backend=str(analysis.get("backend") or ""),
                model=str(analysis.get("model") or ""),
                original_prediction=bool(card.get("original_prediction")),
                reconciled_prediction=bool(card.get("reconciled_prediction")),
                path=paths.reviews,
            )
            st.success(f"Saved {review_label_for_role(reviewer_role)}.")
        except InvalidReviewError as exc:
            st.error(str(exc))


def render_competency_card(
    st: Any,
    card: dict[str, Any],
    *,
    analysis: dict[str, Any] | None = None,
    catalogue_ids: list[str] | None = None,
    paths=None,
    show_decision: bool = False,
    show_reconciled: bool = True,
) -> None:
    st.markdown("---")
    st.subheader(str(card.get("competency_id")))
    st.write(card.get("english_label") or card.get("competency_name"))
    st.caption(card.get("competency_description") or "")
    confidence = card.get("suggested_confidence")
    st.write(
        f"Suggested confidence: {confidence if confidence is not None else 'n/a'}"
    )
    st.write(f"Supporting fragments: {card.get('support_count', 0)}")
    st.write(
        "BM25 candidate ranks: "
        + format_bm25_ranks(card.get("bm25_ranks") or [])
    )
    st.write("Post-processing hierarchy check")
    st.write(f"Hierarchy: {card.get('hierarchy_label') or 'No warning'}")

    if show_reconciled:
        original = ", ".join(card.get("original_labels") or [card["competency_id"]])
        reconciled = ", ".join(card.get("reconciled_labels") or []) or "(none)"
        st.write(f"Original: {original}")
        st.write(f"Hierarchy-reconciled: {reconciled}")

        if card.get("original_prediction") and not card.get(
            "reconciled_prediction"
        ):
            st.warning(
                "Broad parent removed because a directly related child "
                "competency was also predicted."
            )

    st.write("Supporting evidence:")

    for support in card.get("supporting_fragments") or []:
        st.markdown(f"**{support.get('fragment_id')}**")
        quotes = support.get("quotes") or card.get("evidence_quotes") or []
        fragment_text = str(support.get("fragment_text") or "")

        if quotes:
            st.markdown(
                highlight_quote(fragment_text, quotes[0]),
                unsafe_allow_html=True,
            )
            for quote in quotes:
                st.code(quote)
        else:
            st.write(fragment_text)

    if show_decision and analysis is not None and catalogue_ids is not None:
        _review_form(
            st,
            analysis=analysis,
            card=card,
            catalogue_ids=catalogue_ids,
            paths=paths,
        )


def render_analyze_resource(st: Any) -> None:
    st.title("Learning Resource → Competencies")
    st.write(ANALYZE_EXPLANATION)
    ensure_runtime_dirs()
    state = load_ui_state()
    paths = state["paths"]

    mode = st.radio(
        "Input mode",
        ["Existing Moodle resource", "Upload / paste resource"],
    )
    backends = configured_backend_choices(include_ollama_probe=True)
    available = [item for item in backends if item.get("available")]

    if not available:
        st.warning(
            "No model backend is currently available. "
            "Configure Gemini or start Ollama before analyzing."
        )

    backend_labels = []

    for item in backends:
        label = item["backend"].title()

        if item.get("model"):
            label = f"{label} ({item['model']})"

        if not item.get("available"):
            label = f"{label} — unavailable"

        backend_labels.append(label)

    backend_choice = st.selectbox(
        "Backend",
        options=list(range(len(backends))),
        format_func=lambda index: backend_labels[index],
    )
    selected_backend = backends[backend_choice]
    resource = None
    resource_id = None

    if mode == "Existing Moodle resource":
        if not state["moodle_resources"]:
            st.error("Moodle unavailable: extracted resource catalogue was not found.")
        else:
            courses = moodle_course_options(state["moodle_resources"])
            course = st.selectbox("Course", courses)
            resources = moodle_resource_options(
                course,
                state["moodle_resources"],
            )
            labels = [
                f"{item['title']} ({item['resource_type']})"
                for item in resources
            ]
            selected = st.selectbox(
                "Resource",
                options=list(range(len(resources))),
                format_func=lambda index: labels[index],
            ) if resources else None

            if selected is not None:
                resource_id = resources[selected]["resource_id"]
    else:
        title = st.text_input("Title")
        course = st.text_input("Optional course")
        uploaded = st.file_uploader(
            "TXT / HTML / PDF uploader",
            type=["txt", "html", "htm", "pdf"],
        )
        pasted = st.text_area("Paste text")
        course = course.strip() or None
        title = title.strip()

    if st.button("ANALYZE COMPETENCIES"):
        if not selected_backend.get("available"):
            st.error(
                selected_backend.get("message")
                or f"{selected_backend['backend'].title()} backend unavailable."
            )
            return

        try:
            if mode == "Existing Moodle resource":
                if not state["moodle_resources"]:
                    raise MoodleResourceUnavailableError(
                        "Moodle unavailable."
                    )

                resource = ingest_existing_moodle_resource(
                    resource_id,
                    resources=state["moodle_resources"],
                )
            elif uploaded is not None:
                resource = ingest_uploaded_file(
                    uploaded.getvalue(),
                    filename=uploaded.name,
                    title=title or uploaded.name,
                    course_shortname=course,
                )
            else:
                resource = ingest_pasted_text(
                    pasted,
                    title=title or "Pasted resource",
                    course_shortname=course,
                )
        except PdfTextUnavailableError as exc:
            st.error(str(exc))
            return
        except (
            EmptyResourceError,
            UnsupportedFileError,
            MoodleResourceUnavailableError,
            ResourceIngestionError,
        ) as exc:
            st.error(str(exc))
            return

        progress = st.progress(0, text=ANALYSIS_STAGES[0])
        status = st.empty()

        def on_progress(index: int, label: str) -> None:
            progress.progress(index / len(ANALYSIS_STAGES), text=label)
            status.write(f"{index}. {label}")

        try:
            backend = create_runtime_backend(
                str(selected_backend["backend"]),
                model=selected_backend.get("model"),
            )
            analysis = analyze_runtime_resource(
                resource,
                backend=backend,
                persist=True,
                paths=paths,
                progress=on_progress,
            )
        except BackendUnavailableError as exc:
            st.error(str(exc))
            return
        except NoUsableFragmentsError as exc:
            st.error(str(exc))
            return

        st.session_state["last_analysis_id"] = analysis["analysis_id"]
        st.success("Analysis complete.")
        _render_analysis_result(
            st,
            analysis,
            catalogue_ids=state["catalogue_ids"],
            paths=paths,
        )


def _render_analysis_result(
    st: Any,
    analysis: dict[str, Any],
    *,
    catalogue_ids: list[str],
    paths,
) -> None:
    st.markdown("## Analysis result")
    st.write(f"Resource title: {analysis.get('title')}")
    st.write(
        f"Source: {analysis.get('source_type')} "
        f"({analysis.get('source_reference')})"
    )
    st.write(f"Backend: {analysis.get('backend')}")
    st.write(f"Model: {analysis.get('model')}")
    st.write(f"Number of fragments: {analysis.get('fragment_count')}")
    st.write(
        f"Number of competency suggestions: {analysis.get('suggestion_count')}"
    )
    st.write(f"Analysis ID: {analysis.get('analysis_id')}")
    st.caption(analysis.get("hierarchy_check_label"))

    if not analysis.get("suggestion_cards"):
        st.info("No competency predicted for this resource.")
        return

    show_reconciled = st.checkbox(
        "Show hierarchy-reconciled view",
        value=True,
        key=f"reconciled_{analysis['analysis_id']}",
    )

    for card in analysis.get("suggestion_cards") or []:
        if show_reconciled and not card.get("reconciled_prediction"):
            with st.expander(
                f"{card['competency_id']} (removed in reconciled view)"
            ):
                render_competency_card(
                    st,
                    card,
                    analysis=analysis,
                    catalogue_ids=catalogue_ids,
                    paths=paths,
                    show_decision=True,
                    show_reconciled=True,
                )
            continue

        render_competency_card(
            st,
            card,
            analysis=analysis,
            catalogue_ids=catalogue_ids,
            paths=paths,
            show_decision=True,
            show_reconciled=show_reconciled,
        )


def render_review_suggestions(st: Any) -> None:
    st.title("Review Suggestions")
    st.write(
        "Pending model suggestions can be reviewed without rerunning the model."
    )
    state = load_ui_state()
    analyses = state["analyses"]
    reviews = state["reviews"]
    courses = sorted(
        {
            str(card.get("course_shortname") or "")
            for analysis in analyses
            for card in analysis.get("suggestion_cards") or []
            if card.get("course_shortname")
        }
    )
    resources = sorted(
        {
            str(card.get("runtime_resource_id") or "")
            for analysis in analyses
            for card in analysis.get("suggestion_cards") or []
        }
    )
    competencies = sorted(
        {
            str(card.get("competency_id") or "")
            for analysis in analyses
            for card in analysis.get("suggestion_cards") or []
        }
    )
    backends = sorted(
        {
            str(analysis.get("backend") or "")
            for analysis in analyses
            if analysis.get("backend")
        }
    )
    course = st.selectbox("Course", ["(all)"] + courses)
    resource = st.selectbox("Resource", ["(all)"] + resources)
    status = st.selectbox(
        "Status",
        ["pending", "accepted", "rejected", "modified", "all"],
    )
    competency = st.selectbox("Competency", ["(all)"] + competencies)
    backend = st.selectbox("Backend", ["(all)"] + backends)
    rows = filter_suggestion_rows(
        analyses,
        reviews,
        course=None if course == "(all)" else course,
        resource_id=None if resource == "(all)" else resource,
        status=status,
        competency_id=None if competency == "(all)" else competency,
        backend=None if backend == "(all)" else backend,
    )
    st.write(f"{len(rows)} suggestion(s)")

    for row in rows:
        analysis = next(
            item
            for item in analyses
            if item.get("analysis_id") == row["analysis_id"]
        )
        st.caption(f"Status: {row['review_status']}")
        render_competency_card(
            st,
            row,
            analysis=analysis,
            catalogue_ids=state["catalogue_ids"],
            paths=state["paths"],
            show_decision=True,
        )


def render_competency_resources(st: Any) -> None:
    st.title("Competency → Resources")
    st.write(
        "Model suggestions are shown separately from human-validated mappings. "
        "Unreviewed predictions are not described as validated."
    )
    state = load_ui_state()
    competencies = load_competencies()
    labels = [
        f"{item.get('idnumber')} — {item.get('shortname')}"
        for item in competencies
    ]
    selected = st.selectbox("Competency", options=list(range(len(labels))), format_func=lambda i: labels[i])
    competency_id = str(competencies[selected]["idnumber"])
    grouped = competency_resource_index(
        state["analyses"],
        state["reviews"],
        competency_id=competency_id,
    )
    st.subheader("MODEL SUGGESTIONS")

    if not grouped["model_suggestions"]:
        st.info("No model suggestions for this competency yet.")
    else:
        current_analysis = None

        for row in grouped["model_suggestions"]:
            analysis_id = str(row.get("analysis_id") or "")

            if analysis_id != current_analysis:
                current_analysis = analysis_id
                st.markdown(f"**Analysis** `{analysis_id}`")
                st.caption(str(row.get("backend_label") or format_backend_model(
                    row.get("backend"),
                    row.get("model"),
                )))

            st.markdown(
                f"**{row.get('title')}**  \n"
                f"Course: {row.get('course_shortname') or 'n/a'}  \n"
                f"Backend / model: {row.get('backend_label') or format_backend_model(row.get('backend'), row.get('model'))}  \n"
                f"Supporting fragments: {row.get('support_count')}  \n"
                f"Confidence: {row.get('suggested_confidence')}  \n"
                f"Review status: {row.get('review_status')}"
            )
            for quote in row.get("evidence_quotes") or []:
                st.code(quote)

    st.subheader("VALIDATED")

    if not grouped["human_validated"]:
        st.info("No human-validated mappings yet.")
    else:
        for row in grouped["human_validated"]:
            decision = str(row.get("decision") or row.get("review_status") or "").upper()
            st.markdown(
                f"**{row.get('title')} — {decision}**  \n"
                f"Reviewer: {row.get('reviewer_name') or 'n/a'}  \n"
                f"Role: {row.get('review_kind') or review_label_for_role(str(row.get('reviewer_role') or ''))}  \n"
                f"Backend / model: {row.get('backend_label') or format_backend_model(row.get('backend'), row.get('model'))}  \n"
                f"Analysis ID: `{row.get('analysis_id')}`"
            )


def render_review_history(st: Any) -> None:
    st.title("Review History / Progress")
    state = load_ui_state()
    summary = history_summary(state["analyses"], state["reviews"])
    st.write(f"Analyses run: {summary['analyses_run']}")
    st.write(f"Resources analyzed: {summary['resources_analyzed']}")
    st.write(f"Suggestions generated: {summary['suggestions_generated']}")
    st.write(f"Pending: {summary['pending']}")
    st.write(f"Accepted: {summary['accepted']}")
    st.write(f"Rejected: {summary['rejected']}")
    st.write(f"Modified: {summary['modified']}")
    st.subheader("Reviewer breakdown")
    st.write(f"Researcher reviews: {summary['researcher_review_count']}")
    st.write(f"Teacher reviews: {summary['teacher_review_count']}")
    st.write(f"Supervisor reviews: {summary['supervisor_review_count']}")
    st.info("Researcher and supervisor reviews are not teacher-study results.")

    rows = review_history_table_rows(state["reviews"], state["analyses"])
    st.subheader("Individual reviews")

    if not rows:
        st.info("No saved reviews yet.")
    else:
        st.dataframe(rows, hide_index=True, use_container_width=True)


def render_research_results(st: Any) -> None:
    st.title("Research Results")
    st.caption("Values are read from existing metric files. They are not recalculated.")
    results = load_research_results()
    fragment = results["fragment_original"]
    resource = results["resource_original"]
    evidence = results["evidence"]
    hierarchy = results["hierarchy_ablation"]

    st.subheader("Fragment-level original Gemini")
    fragment_cols = st.columns(3)
    fragment_cols[0].metric("Precision", fragment["precision"])
    fragment_cols[1].metric("Recall", fragment["recall"])
    fragment_cols[2].metric("F1", fragment["f1"])

    st.subheader("Resource-level original")
    resource_cols = st.columns(3)
    resource_cols[0].metric("Precision", resource["precision"])
    resource_cols[1].metric("Recall", resource["recall"])
    resource_cols[2].metric("F1", resource["f1"])

    st.subheader("Evidence")
    st.write(
        f"mechanically exact 100% ({evidence.get('mechanically_exact')}/"
        f"{evidence.get('total')})"
    )
    clear = evidence.get("clear_rate")
    partial = evidence.get("partial_rate")
    unsupported = evidence.get("unsupported_rate")
    evidence_cols = st.columns(3)
    evidence_cols[0].write(
        f"clear support {clear:.1%}" if clear is not None else ""
    )
    evidence_cols[1].write(
        f"partial {partial:.1%}" if partial is not None else ""
    )
    evidence_cols[2].write(
        f"unsupported {unsupported:.1%}" if unsupported is not None else ""
    )

    st.subheader("Post-hoc hierarchy result")
    st.warning(hierarchy["label"])
    st.write(
        "Fragment F1: "
        f"{hierarchy['fragment_f1_original']} → "
        f"{hierarchy['fragment_f1_reconciled']}"
    )
    st.write(
        "Resource F1: "
        f"{hierarchy['resource_f1_original']} → "
        f"{hierarchy['resource_f1_reconciled']}"
    )
    st.caption(hierarchy["note"])
