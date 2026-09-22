"""Tests for the reusable Moodle REST client."""

from __future__ import annotations

from typing import Any

import pytest

from moodle_competency.moodle_client import (
    MoodleAPIError,
    MoodleClient,
)
from moodle_competency.settings import Settings


class FakeResponse:
    """Minimal requests.Response replacement for unit tests."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.text = str(payload)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


class FakeSession:
    """Record REST calls and return prepared responses."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def post(
        self,
        url: str,
        *,
        data: dict[str, Any],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "data": data,
                "timeout": timeout,
            }
        )

        if not self.responses:
            raise AssertionError("No fake response remains.")

        return FakeResponse(self.responses.pop(0))

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def settings() -> Settings:
    return Settings(
        moodle_base_url="http://localhost:8000",
        moodle_token="test-token",
        moodle_service_shortname="moodle_competency_mvp",
        moodle_sw_course_id=2,
        moodle_data_course_id=3,
        moodle_sw_shortname="MVP-SW",
        moodle_data_shortname="MVP-DATA",
        competency_framework_idnumber="UTC_GI_MVP_2026",
    )


def test_get_site_info(settings: Settings) -> None:
    session = FakeSession(
        [{"sitename": "COMP-MVP", "username": "api_mvp"}]
    )
    client = MoodleClient(settings, session=session)

    result = client.get_site_info()

    assert result["username"] == "api_mvp"
    assert session.calls[0]["data"]["wstoken"] == "test-token"
    assert (
        session.calls[0]["data"]["wsfunction"]
        == "core_webservice_get_site_info"
    )


def test_get_course_by_shortname(settings: Settings) -> None:
    session = FakeSession(
        [
            {
                "courses": [
                    {
                        "id": 2,
                        "shortname": "MVP-SW",
                        "fullname": "Software Engineering",
                    }
                ],
                "warnings": [],
            }
        ]
    )

    client = MoodleClient(settings, session=session)
    course = client.get_course_by_shortname("MVP-SW")

    assert course["id"] == 2
    assert session.calls[0]["data"]["field"] == "shortname"
    assert session.calls[0]["data"]["value"] == "MVP-SW"


def test_course_array_parameters(settings: Settings) -> None:
    session = FakeSession(
        [{"pages": [], "warnings": []}]
    )
    client = MoodleClient(settings, session=session)

    client.get_pages_by_courses([2, 3])

    sent_data = session.calls[0]["data"]

    assert sent_data["courseids[0]"] == 2
    assert sent_data["courseids[1]"] == 3
    assert (
        sent_data["wsfunction"]
        == "mod_page_get_pages_by_courses"
    )


def test_moodle_api_error(settings: Settings) -> None:
    session = FakeSession(
        [
            {
                "exception": "core\\exception\\moodle_exception",
                "errorcode": "invalidtoken",
                "message": "Invalid token",
            }
        ]
    )

    client = MoodleClient(settings, session=session)

    with pytest.raises(
        MoodleAPIError,
        match="Invalid token",
    ):
        client.get_site_info()
