"""Service configuration, read from the environment.

Model-provider secrets (``GEMINI_API_KEY``, ``OLLAMA_HOST``) are deliberately not
part of these settings. The research engine reads them itself, and they never
leave this process.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = REPOSITORY_ROOT / ".env"

# Only these variables are taken from an env file. The repository .env also
# holds Moodle database credentials and a Moodle web-service token for the
# research scripts. The service must never receive those, so everything outside
# this list is ignored.
ENV_FILE_PREFIXES = ("ALIGNMENT_",)
ENV_FILE_NAMES = frozenset(
    {"GEMINI_API_KEY", "GEMINI_MODEL", "OLLAMA_HOST", "OLLAMA_MODEL"}
)

BACKENDS = ("gemini", "ollama", "mock")
DEFAULT_BACKEND = "gemini"

# A short shared secret is easy to guess, so a configured token must be long.
MIN_TOKEN_LENGTH = 16

DEFAULT_MAX_BODY_BYTES = 2_000_000
MIN_MAX_BODY_BYTES = 1_000
MAX_MAX_BODY_BYTES = 50_000_000

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


class ConfigurationError(ValueError):
    """Raised when the environment holds an unusable service setting."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated service settings."""

    # repr=False: the token must never reach a log line through a dataclass repr.
    service_token: str | None = field(default=None, repr=False)
    backend: str = DEFAULT_BACKEND
    model: str | None = None
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    enable_docs: bool = False
    log_level: str = "INFO"

    @property
    def token_configured(self) -> bool:
        return bool(self.service_token)


def _integer(
    environ: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = environ.get(name, "").strip()

    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc

    if not minimum <= value <= maximum:
        raise ConfigurationError(
            f"{name} must be between {minimum} and {maximum}."
        )

    return value


def import_env_file(path: Path) -> None:
    """Copy the allow-listed variables of ``path`` into the process environment.

    Variables that are already set win, so the shell can override the file.
    """

    for name, value in dotenv_values(path).items():
        allowed = name.startswith(ENV_FILE_PREFIXES) or name in ENV_FILE_NAMES

        if allowed and value is not None and name not in os.environ:
            os.environ[name] = value


def load_settings(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: Path | None = None,
) -> Settings:
    """Build settings from ``environ``.

    With no ``environ`` the process environment is used, after importing the
    allow-listed variables of the ``.env`` file (see ``import_env_file``).
    Passing ``environ`` explicitly never touches the file system, which keeps
    tests hermetic.
    """

    if environ is None:
        configured_file = os.environ.get("ALIGNMENT_ENV_FILE", "").strip()
        path = env_file or (
            Path(configured_file) if configured_file else DEFAULT_ENV_FILE
        )

        if path.exists():
            import_env_file(path)

        environ = os.environ

    token = environ.get("ALIGNMENT_SERVICE_TOKEN", "").strip() or None

    if token is not None and len(token) < MIN_TOKEN_LENGTH:
        raise ConfigurationError(
            "ALIGNMENT_SERVICE_TOKEN must be at least "
            f"{MIN_TOKEN_LENGTH} characters."
        )

    backend = (
        environ.get("ALIGNMENT_BACKEND", "").strip().casefold()
        or DEFAULT_BACKEND
    )

    if backend not in BACKENDS:
        raise ConfigurationError(
            "ALIGNMENT_BACKEND must be one of: " + ", ".join(BACKENDS) + "."
        )

    return Settings(
        service_token=token,
        backend=backend,
        model=environ.get("ALIGNMENT_MODEL", "").strip() or None,
        max_body_bytes=_integer(
            environ,
            "ALIGNMENT_MAX_BODY_BYTES",
            DEFAULT_MAX_BODY_BYTES,
            minimum=MIN_MAX_BODY_BYTES,
            maximum=MAX_MAX_BODY_BYTES,
        ),
        enable_docs=(
            environ.get("ALIGNMENT_ENABLE_DOCS", "").strip().casefold()
            in _TRUE_VALUES
        ),
        log_level=(
            environ.get("ALIGNMENT_LOG_LEVEL", "").strip().upper() or "INFO"
        ),
    )
