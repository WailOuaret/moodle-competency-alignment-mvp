"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated configuration for the Moodle alignment project."""

    moodle_base_url: str
    moodle_token: str | None
    moodle_service_shortname: str

    moodle_sw_course_id: int
    moodle_data_course_id: int

    moodle_sw_shortname: str
    moodle_data_shortname: str

    competency_framework_idnumber: str

    @property
    def rest_endpoint(self) -> str:
        """Return the Moodle REST server endpoint."""

        return (
            f"{self.moodle_base_url}"
            "/webservice/rest/server.php"
        )

    @property
    def course_ids(self) -> tuple[int, int]:
        """Return the two MVP course IDs."""

        return (
            self.moodle_sw_course_id,
            self.moodle_data_course_id,
        )

    def require_token(self) -> str:
        """Return the configured Moodle token or raise a clear error."""

        if not self.moodle_token:
            raise RuntimeError(
                "MOODLE_TOKEN is not configured. "
                "Add it to the local .env file before calling Moodle REST."
            )

        return self.moodle_token


def _required_text(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise ValueError(
            f"Required environment variable {name} is empty."
        )

    return value


def _positive_integer(name: str) -> int:
    raw_value = _required_text(name)

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an integer, received {raw_value!r}."
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be greater than zero, received {value}."
        )

    return value


def _validate_base_url(raw_url: str) -> str:
    base_url = raw_url.rstrip("/")
    parsed = urlparse(base_url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            "MOODLE_BASE_URL must start with http:// or https://."
        )

    if not parsed.netloc:
        raise ValueError(
            "MOODLE_BASE_URL must contain a valid host."
        )

    return base_url


def load_settings(
    env_file: str | Path = DEFAULT_ENV_FILE,
    *,
    override: bool = False,
) -> Settings:
    """Load and validate configuration from a dotenv file."""

    env_path = Path(env_file)

    if env_path.exists():
        load_dotenv(
            dotenv_path=env_path,
            override=override,
        )

    token = os.getenv("MOODLE_TOKEN", "").strip() or None

    return Settings(
        moodle_base_url=_validate_base_url(
            _required_text("MOODLE_BASE_URL")
        ),
        moodle_token=token,
        moodle_service_shortname=_required_text(
            "MOODLE_SERVICE_SHORTNAME"
        ),
        moodle_sw_course_id=_positive_integer(
            "MOODLE_SW_COURSE_ID"
        ),
        moodle_data_course_id=_positive_integer(
            "MOODLE_DATA_COURSE_ID"
        ),
        moodle_sw_shortname=_required_text(
            "MOODLE_SW_SHORTNAME"
        ),
        moodle_data_shortname=_required_text(
            "MOODLE_DATA_SHORTNAME"
        ),
        competency_framework_idnumber=_required_text(
            "COMPETENCY_FRAMEWORK_IDNUMBER"
        ),
    )
