"""Tests for project configuration loading."""

from pathlib import Path

import pytest

from moodle_competency.settings import load_settings


VALID_ENV = """
MOODLE_BASE_URL=http://localhost:8000/
MOODLE_TOKEN=
MOODLE_SERVICE_SHORTNAME=moodle_competency_mvp
MOODLE_SW_COURSE_ID=2
MOODLE_DATA_COURSE_ID=3
MOODLE_SW_SHORTNAME=MVP-SW
MOODLE_DATA_SHORTNAME=MVP-DATA
COMPETENCY_FRAMEWORK_IDNUMBER=UTC_GI_MVP_2026
"""


def create_env_file(
    directory: Path,
    content: str = VALID_ENV,
) -> Path:
    env_file = directory / ".env"
    env_file.write_text(
        content.strip() + "\n",
        encoding="utf-8",
    )
    return env_file


def test_load_settings(tmp_path: Path) -> None:
    env_file = create_env_file(tmp_path)

    settings = load_settings(
        env_file,
        override=True,
    )

    assert settings.moodle_base_url == "http://localhost:8000"
    assert settings.rest_endpoint.endswith(
        "/webservice/rest/server.php"
    )
    assert settings.course_ids == (2, 3)
    assert settings.moodle_token is None
    assert (
        settings.competency_framework_idnumber
        == "UTC_GI_MVP_2026"
    )


def test_require_token_raises_when_missing(
    tmp_path: Path,
) -> None:
    env_file = create_env_file(tmp_path)

    settings = load_settings(
        env_file,
        override=True,
    )

    with pytest.raises(
        RuntimeError,
        match="MOODLE_TOKEN is not configured",
    ):
        settings.require_token()


def test_invalid_course_id_is_rejected(
    tmp_path: Path,
) -> None:
    invalid_env = VALID_ENV.replace(
        "MOODLE_SW_COURSE_ID=2",
        "MOODLE_SW_COURSE_ID=invalid",
    )

    env_file = create_env_file(
        tmp_path,
        invalid_env,
    )

    with pytest.raises(
        ValueError,
        match="MOODLE_SW_COURSE_ID must be an integer",
    ):
        load_settings(
            env_file,
            override=True,
        )
