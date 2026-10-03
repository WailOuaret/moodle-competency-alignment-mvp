"""Deterministic stand-in for a model backend.

It never calls a model. Its output is passed through the same validators as real
model output, so a run with this backend exercises the whole pipeline except the
model itself. Results are labelled ``backend = "mock"`` in the manifest and must
never be mistaken for model suggestions.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from moodle_competency.runtime_analysis import MockAlignmentBackend


MOCK_MODEL_NAME = "mock-deterministic-1"
MOCK_CONFIDENCE = 0.8
MAX_QUOTE_CHARS = 240

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def first_quote(fragment_text: str) -> str:
    """Return the first sentence of ``fragment_text`` as an exact substring."""

    stripped = fragment_text.strip()
    sentence = _SENTENCE_END.split(stripped, maxsplit=1)[0]
    return sentence[:MAX_QUOTE_CHARS].strip() or stripped[:MAX_QUOTE_CHARS]


def deterministic_handler(task: Mapping[str, Any]) -> dict[str, Any]:
    """Select the best BM25 candidate and quote the start of the fragment."""

    allowed = list(task["allowed_idnumbers"])

    return {
        "fragment_id": task["fragment_id"],
        "selected": [
            {
                "idnumber": allowed[0],
                "evidence": [first_quote(str(task["fragment_text"]))],
                "reason": "Deterministic mock selection. No model was called.",
                "confidence": MOCK_CONFIDENCE,
            }
        ],
        "abstain": False,
        "overall_reason": "Deterministic mock response.",
    }


def create_mock_backend() -> MockAlignmentBackend:
    return MockAlignmentBackend(deterministic_handler, model=MOCK_MODEL_NAME)
