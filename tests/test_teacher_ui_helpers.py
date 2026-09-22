"""Teacher UI helper and review persistence tests. No live models."""

from __future__ import annotations

from pathlib import Path

from moodle_competency.runtime_analysis import load_competencies
from moodle_competency.teacher_reviews import (
    InvalidReviewError,
    persist_runtime_review,
    review_kind_label,
    review_progress,
    runtime_decision_status,
)
from moodle_competency.teacher_ui import (
    competency_resource_index,
    configured_backend_choices,
    filter_suggestion_rows,
    format_backend_model,
    highlight_quote,
    history_summary,
    load_research_results,
    review_history_table_rows,
)
import pytest


def _catalogue() -> list[str]:
    return [str(item["idnumber"]) for item in load_competencies()]


def _review_kwargs(tmp_path: Path, **overrides):
    payload = {
        "analysis_id": "an_test",
        "runtime_resource_id": "runtime:paste:abc",
        "competency_id": "GI_C1_2",
        "decision": "ACCEPT",
        "reviewer_name": "Wail Ouaret",
        "reviewer_role": "researcher",
        "catalogue_ids": _catalogue(),
        "backend": "mock",
        "model": "mock-model",
        "path": tmp_path / "teacher_reviews.csv",
    }
    payload.update(overrides)
    return payload


def test_teacher_accept_persistence(tmp_path: Path) -> None:
    row = persist_runtime_review(**_review_kwargs(tmp_path, decision="ACCEPT"))
    assert row["decision"] == "ACCEPT"
    assert row["reviewer_role"] == "researcher"
    assert runtime_decision_status(
        [row],
        analysis_id="an_test",
        runtime_resource_id="runtime:paste:abc",
        competency_id="GI_C1_2",
    ) == "accept"


def test_teacher_reject_persistence(tmp_path: Path) -> None:
    row = persist_runtime_review(**_review_kwargs(tmp_path, decision="REJECT"))
    assert row["decision"] == "REJECT"


def test_teacher_modify_persistence(tmp_path: Path) -> None:
    row = persist_runtime_review(
        **_review_kwargs(
            tmp_path,
            decision="MODIFY",
            replacement_competency_id="GI_C1_3",
        )
    )
    assert row["decision"] == "MODIFY"
    assert row["replacement_competency_id"] == "GI_C1_3"


def test_invalid_modify_competency_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidReviewError, match="Invalid MODIFY"):
        persist_runtime_review(
            **_review_kwargs(
                tmp_path,
                decision="MODIFY",
                replacement_competency_id="NOT_A_COMPETENCY",
            )
        )


def test_reviewer_role_persistence(tmp_path: Path) -> None:
    row = persist_runtime_review(
        **_review_kwargs(tmp_path, reviewer_role="supervisor")
    )
    assert row["reviewer_role"] == "supervisor"
    assert review_kind_label("researcher") == "researcher review"
    assert review_kind_label("teacher") == "teacher review"
    progress = review_progress([row])
    assert progress["supervisor_review_count"] == 1
    assert progress["teacher_review_count"] == 0


def test_highlight_quote_keeps_context() -> None:
    fragment = "Testing and verification are performed throughout development."
    html = highlight_quote(fragment, "verification are performed")
    assert "<mark>verification are performed</mark>" in html
    assert "Testing and" in html
    assert "throughout development." in html
    assert "&lt;script&gt;" in highlight_quote("<script>x</script>", "")


def test_filter_and_competency_resources(tmp_path: Path) -> None:
    analyses = [
        {
            "analysis_id": "an_1",
            "backend": "mock",
            "model": "mock-model",
            "runtime_resource_id": "runtime:paste:abc",
            "suggestion_cards": [
                {
                    "competency_id": "GI_C1_2",
                    "runtime_resource_id": "runtime:paste:abc",
                    "title": "Resource A",
                    "course_shortname": "MVP-SW",
                    "support_count": 1,
                    "evidence_quotes": ["verification"],
                    "suggested_confidence": 0.91,
                }
            ],
        }
    ]
    reviews = [
        persist_runtime_review(
            analysis_id="an_1",
            runtime_resource_id="runtime:paste:abc",
            competency_id="GI_C1_2",
            decision="ACCEPT",
            reviewer_name="Wail Ouaret",
            reviewer_role="researcher",
            catalogue_ids=_catalogue(),
            path=tmp_path / "teacher_reviews.csv",
        )
    ]
    pending = filter_suggestion_rows(
        analyses,
        [],
        status="pending",
        competency_id="GI_C1_2",
    )
    accepted = filter_suggestion_rows(
        analyses,
        reviews,
        status="accepted",
    )
    assert pending[0]["review_status"] == "pending"
    assert accepted[0]["review_status"] == "accept"
    grouped = competency_resource_index(
        analyses,
        reviews,
        competency_id="GI_C1_2",
    )
    assert grouped["model_suggestions"]
    assert grouped["human_validated"]
    validated = grouped["human_validated"][0]
    assert validated["decision"] == "ACCEPT"
    assert validated["reviewer_name"] == "Wail Ouaret"
    assert validated["reviewer_role"] == "researcher"
    assert validated["review_kind"] == "researcher review"
    assert validated["backend_label"] == "Mock — mock-model"
    assert validated["analysis_id"] == "an_1"
    grouped_pending = competency_resource_index(
        analyses,
        [],
        competency_id="GI_C1_2",
    )
    assert grouped_pending["human_validated"] == []


def test_history_and_research_results() -> None:
    analyses = [
        {
            "analysis_id": "an_1",
            "runtime_resource_id": "runtime:paste:abc",
            "suggestion_cards": [{"competency_id": "GI_C1_2"}],
        }
    ]
    summary = history_summary(analyses, [])
    assert summary["analyses_run"] == 1
    assert summary["suggestions_generated"] == 1
    assert summary["teacher_review_count"] == 0
    assert "not teacher-study" in summary["note"]

    results = load_research_results()
    assert results["fragment_original"]["precision"] == 0.7255
    assert results["fragment_original"]["f1"] == 0.8315
    assert results["resource_original"]["f1"] == 0.7931
    assert results["hierarchy_ablation"]["label"] == "POST-HOC ABLATION"
    assert results["hierarchy_ablation"]["fragment_f1_reconciled"] == 0.9367
    assert results["hierarchy_ablation"]["resource_f1_reconciled"] == 0.9388
    assert results["evidence"]["clear_rate"] == 0.7831


def test_backends_without_ollama_probe() -> None:
    backends = configured_backend_choices(include_ollama_probe=False)
    ollama = next(item for item in backends if item["backend"] == "ollama")
    assert ollama["available"] is False
    assert ollama["message"] == "Ollama backend unavailable."


def test_backend_model_label() -> None:
    assert format_backend_model("gemini", "gemini-3.5-flash") == (
        "Gemini — gemini-3.5-flash"
    )
    assert format_backend_model("ollama", "mistral:latest") == (
        "Ollama — mistral:latest"
    )


def test_multi_backend_suggestions_stay_separate() -> None:
    analyses = [
        {
            "analysis_id": "an_gemini",
            "backend": "gemini",
            "model": "gemini-3.5-flash",
            "suggestion_cards": [
                {
                    "competency_id": "GI_C1_2",
                    "runtime_resource_id": "runtime:paste:abc",
                    "title": "Same resource",
                    "support_count": 1,
                    "evidence_quotes": ["verification"],
                }
            ],
        },
        {
            "analysis_id": "an_ollama",
            "backend": "ollama",
            "model": "mistral:latest",
            "suggestion_cards": [
                {
                    "competency_id": "GI_C1_2",
                    "runtime_resource_id": "runtime:paste:abc",
                    "title": "Same resource",
                    "support_count": 1,
                    "evidence_quotes": ["verification"],
                }
            ],
        },
    ]
    grouped = competency_resource_index(
        analyses,
        [],
        competency_id="GI_C1_2",
    )
    suggestions = grouped["model_suggestions"]
    assert len(suggestions) == 2
    assert suggestions[0]["analysis_id"] == "an_gemini"
    assert suggestions[1]["analysis_id"] == "an_ollama"
    assert suggestions[0]["backend_label"] == "Gemini — gemini-3.5-flash"
    assert suggestions[1]["backend_label"] == "Ollama — mistral:latest"
    assert grouped["human_validated"] == []


def test_review_history_table_rows() -> None:
    reviews = [
        {
            "analysis_id": "an_1",
            "runtime_resource_id": "runtime:paste:abc",
            "competency_id": "GI_C1_2",
            "decision": "ACCEPT",
            "reviewer_name": "Wail Ouaret",
            "reviewer_role": "researcher",
            "backend": "gemini",
            "model": "gemini-3.5-flash",
            "review_date": "2026-09-18",
        }
    ]
    analyses = [
        {
            "analysis_id": "an_1",
            "title": "Verification notes",
            "runtime_resource_id": "runtime:paste:abc",
        }
    ]
    rows = review_history_table_rows(reviews, analyses)
    assert rows[0]["analysis ID"] == "an_1"
    assert rows[0]["resource"] == "Verification notes"
    assert rows[0]["competency"] == "GI_C1_2"
    assert rows[0]["decision"] == "ACCEPT"
    assert rows[0]["reviewer"] == "Wail Ouaret"
    assert rows[0]["role"] == "researcher"
    assert rows[0]["backend"] == "gemini"
    assert rows[0]["model"] == "gemini-3.5-flash"
    assert rows[0]["date"] == "2026-09-18"
