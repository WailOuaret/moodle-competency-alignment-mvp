"""Reusable client for the Moodle REST web-service API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import requests

from moodle_competency.settings import Settings


class MoodleAPIError(RuntimeError):
    """Raised when Moodle or the HTTP request returns an error."""


class MoodleClient:
    """Small REST client for the functions used by the MVP."""

    def __init__(
        self,
        settings: Settings,
        *,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.settings = settings
        self.timeout = timeout
        self._session = session or requests.Session()
        self._owns_session = session is None

    def close(self) -> None:
        """Close the internally created HTTP session."""

        if self._owns_session:
            self._session.close()

    def __enter__(self) -> "MoodleClient":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def call(
        self,
        function_name: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> Any:
        """Call one Moodle REST function and return decoded JSON."""

        token = self.settings.require_token()

        payload: dict[str, Any] = {
            "wstoken": token,
            "wsfunction": function_name,
            "moodlewsrestformat": "json",
        }

        if parameters:
            payload.update(parameters)

        try:
            response = self._session.post(
                self.settings.rest_endpoint,
                data=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MoodleAPIError(
                f"HTTP request failed for {function_name}: {exc}"
            ) from exc

        try:
            result = response.json()
        except ValueError as exc:
            preview = response.text[:500]

            raise MoodleAPIError(
                f"Moodle returned invalid JSON for {function_name}. "
                f"Response preview: {preview!r}"
            ) from exc

        if isinstance(result, dict):
            exception = result.get("exception")
            error_code = result.get("errorcode")

            if exception or error_code:
                message = result.get(
                    "message",
                    "Moodle returned an unspecified API error.",
                )

                raise MoodleAPIError(
                    f"{function_name} failed: {message} "
                    f"(error code: {error_code or 'unknown'})"
                )

        return result

    def get_site_info(self) -> dict[str, Any]:
        """Return information about the Moodle site and service user."""

        result = self.call("core_webservice_get_site_info")

        if not isinstance(result, dict):
            raise MoodleAPIError(
                "core_webservice_get_site_info returned an unexpected format."
            )

        return result

    def get_course_by_shortname(
        self,
        shortname: str,
    ) -> dict[str, Any]:
        """Return the unique Moodle course matching a short name."""

        result = self.call(
            "core_course_get_courses_by_field",
            {
                "field": "shortname",
                "value": shortname,
            },
        )

        if not isinstance(result, dict):
            raise MoodleAPIError(
                "core_course_get_courses_by_field returned "
                "an unexpected format."
            )

        courses = result.get("courses", [])

        if len(courses) != 1:
            raise MoodleAPIError(
                f"Expected one course with short name {shortname!r}, "
                f"but Moodle returned {len(courses)}."
            )

        course = courses[0]

        if not isinstance(course, dict):
            raise MoodleAPIError(
                f"Course {shortname!r} has an unexpected format."
            )

        return course

    def get_course_contents(
        self,
        course_id: int,
    ) -> list[dict[str, Any]]:
        """Return sections and course modules for one course."""

        result = self.call(
            "core_course_get_contents",
            {"courseid": course_id},
        )

        if not isinstance(result, list):
            raise MoodleAPIError(
                "core_course_get_contents returned an unexpected format."
            )

        return result

    def get_pages_by_courses(
        self,
        course_ids: Sequence[int],
    ) -> dict[str, Any]:
        """Return Moodle Pages belonging to the given courses."""

        parameters = {
            f"courseids[{index}]": course_id
            for index, course_id in enumerate(course_ids)
        }

        result = self.call(
            "mod_page_get_pages_by_courses",
            parameters,
        )

        if not isinstance(result, dict):
            raise MoodleAPIError(
                "mod_page_get_pages_by_courses returned "
                "an unexpected format."
            )

        return result

    def get_quizzes_by_courses(
        self,
        course_ids: Sequence[int],
    ) -> dict[str, Any]:
        """Return Moodle Quizzes belonging to the given courses."""

        parameters = {
            f"courseids[{index}]": course_id
            for index, course_id in enumerate(course_ids)
        }

        result = self.call(
            "mod_quiz_get_quizzes_by_courses",
            parameters,
        )

        if not isinstance(result, dict):
            raise MoodleAPIError(
                "mod_quiz_get_quizzes_by_courses returned "
                "an unexpected format."
            )

        return result


def write_json(
    value: Any,
    output_path: str | Path,
) -> Path:
    """Write formatted UTF-8 JSON and return the resolved path."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return path.resolve()
