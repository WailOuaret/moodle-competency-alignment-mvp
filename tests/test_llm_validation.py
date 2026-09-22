"""Tests for constrained LLM-response validation."""

from moodle_competency.llm_validation import (
    validate_alignment_response,
    validate_response_collection,
)


TASK = {
    "task_id": "alignment:page:1#f001",
    "fragment_id": "page:1#f001",
    "fragment_text": (
        "Students design a modular software architecture."
    ),
    "allowed_idnumbers": [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
    ],
}


def test_valid_selected_response() -> None:
    response = {
        "fragment_id": "page:1#f001",
        "selected": [
            {
                "idnumber": "C1",
                "evidence": [
                    "design a modular software architecture"
                ],
                "reason": (
                    "The fragment explicitly requires "
                    "software architecture design."
                ),
                "confidence": 0.9,
            }
        ],
        "abstain": False,
        "overall_reason": (
            "There is direct textual evidence."
        ),
    }

    result = validate_alignment_response(
        task=TASK,
        response=response,
    )

    assert result["valid"] is True
    assert result["validation_errors"] == []


def test_unknown_competency_is_rejected() -> None:
    response = {
        "fragment_id": "page:1#f001",
        "selected": [
            {
                "idnumber": "INVENTED",
                "evidence": [
                    "software architecture"
                ],
                "reason": "Related evidence.",
                "confidence": 0.8,
            }
        ],
        "abstain": False,
        "overall_reason": "Decision made.",
    }

    result = validate_alignment_response(
        task=TASK,
        response=response,
    )

    assert result["valid"] is False
    assert any(
        "outside the allowed candidate set"
        in error
        for error in result["validation_errors"]
    )


def test_paraphrased_evidence_is_rejected() -> None:
    response = {
        "fragment_id": "page:1#f001",
        "selected": [
            {
                "idnumber": "C1",
                "evidence": [
                    "Learners create an architecture."
                ],
                "reason": "Related meaning.",
                "confidence": 0.7,
            }
        ],
        "abstain": False,
        "overall_reason": "Decision made.",
    }

    result = validate_alignment_response(
        task=TASK,
        response=response,
    )

    assert result["valid"] is False
    assert any(
        "not an exact contiguous substring"
        in error
        for error in result["validation_errors"]
    )


def test_abstention_collection_passes() -> None:
    responses = [
        {
            "fragment_id": "page:1#f001",
            "selected": [],
            "abstain": True,
            "overall_reason": (
                "No supported competency was selected."
            ),
        }
    ]

    validated, summary = (
        validate_response_collection(
            tasks=[TASK],
            responses=responses,
        )
    )

    assert summary["passed"] is True
    assert summary["abstentions"] == 1
    assert validated[0]["valid"] is True
