"""Shared test data and model-response builders for the service tests.

Everything here is synthetic. Nothing reads the frozen experiment, so the
service is exercised with a catalogue that is deliberately not the UTC one.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Mapping, Sequence


TOKEN = "unit-test-token-" + "x" * 24
AUTH = {"Authorization": f"Bearer {TOKEN}"}

FRAMEWORK = {"framework_idnumber": "FW-DEMO", "framework_shortname": "Demo framework"}

CATALOGUE: list[dict[str, Any]] = [
    {
        "idnumber": "SE-1",
        "shortname": "Software engineering",
        "description_text": "Design, build, test and deploy software systems.",
        **FRAMEWORK,
    },
    {
        "idnumber": "SE-1.1",
        "shortname": "Software testing",
        "description_text": (
            "Plan and run software verification, unit testing and "
            "integration testing."
        ),
        "parent_idnumber": "SE-1",
        **FRAMEWORK,
    },
    {
        "idnumber": "SE-1.2",
        "shortname": "Deployment",
        "description_text": (
            "Release software to production with continuous delivery "
            "pipelines."
        ),
        "parent_idnumber": "SE-1",
        **FRAMEWORK,
    },
    {
        "idnumber": "DB-1",
        "shortname": "Databases",
        "description_text": (
            "Model data and write SQL queries against relational databases."
        ),
        **FRAMEWORK,
    },
    {
        "idnumber": "DB-1.1",
        "shortname": "SQL queries",
        "description_text": (
            "Write SELECT statements with joins, grouping and aggregation."
        ),
        "parent_idnumber": "DB-1",
        **FRAMEWORK,
    },
]

PAGE_TEXT = (
    "Software testing verifies requirements. Unit testing checks small parts "
    "of a program.\n\nDeployment releases software to production using "
    "delivery pipelines."
)

# Two paragraphs that together exceed the 900-character fragment limit, so the
# engine produces two fragments (#f001 and #f002).
LONG_TESTING_PARAGRAPH = " ".join(
    ["Software testing verifies requirements through unit tests and integration tests."]
    * 7
)
LONG_SQL_PARAGRAPH = " ".join(
    ["Relational databases are queried with SQL SELECT statements and joins."] * 8
)
TWO_FRAGMENT_TEXT = f"{LONG_TESTING_PARAGRAPH}\n\n{LONG_SQL_PARAGRAPH}"

BASE_PAYLOAD: dict[str, Any] = {
    "schema_version": "1.0",
    "resource": {
        "resource_id": "moodle:page:42",
        "resource_type": "page",
        "course_id": "5",
        "course_module_id": "91",
        "title": "Software Development Lifecycle and Deployment",
        "text": PAGE_TEXT,
    },
    "competencies": CATALOGUE,
    "config": {"top_k": 5, "max_suggestions": 3},
}


def build_payload(**changes: Any) -> dict[str, Any]:
    """Return a fresh valid payload, with top-level keys replaced by ``changes``."""

    payload = copy.deepcopy(BASE_PAYLOAD)
    payload.update(copy.deepcopy(changes))
    return payload


def with_resource(**changes: Any) -> dict[str, Any]:
    """Return a valid payload whose ``resource`` has the given fields changed."""

    payload = build_payload()
    payload["resource"].update(changes)
    return payload


# --------------------------------------------------------------------------- #
# Model-response builders. Each returns a handler for MockAlignmentBackend.
# --------------------------------------------------------------------------- #

Handler = Callable[[Mapping[str, Any]], Any]


def quote_of(task: Mapping[str, Any], size: int = 40) -> str:
    return str(task["fragment_text"]).strip()[:size].strip()


def selection(
    idnumber: str,
    quote: str,
    confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "idnumber": idnumber,
        "evidence": [quote],
        "reason": "Exact quotation from the fragment.",
        "confidence": confidence,
    }


def response(
    task: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    *,
    abstain: bool = False,
) -> dict[str, Any]:
    return {
        "fragment_id": task["fragment_id"],
        "selected": [dict(item) for item in selected],
        "abstain": abstain,
        "overall_reason": "Synthetic test response.",
    }


def selecting(*idnumbers: str, confidence: float = 0.9) -> Handler:
    """Select the given competencies, quoting the start of the fragment."""

    def handler(task: Mapping[str, Any]) -> dict[str, Any]:
        quote = quote_of(task)
        return response(
            task,
            [selection(idnumber, quote, confidence) for idnumber in idnumbers],
        )

    return handler


def abstaining() -> Handler:
    return lambda task: response(task, [], abstain=True)
