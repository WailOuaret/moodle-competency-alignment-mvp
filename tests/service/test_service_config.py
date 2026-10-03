"""Service settings: defaults, validation and secret handling."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from service.config import ConfigurationError, Settings, load_settings


def test_defaults_require_an_explicit_backend_choice_for_mock() -> None:
    settings = load_settings({})

    assert settings.service_token is None
    assert settings.token_configured is False
    # The default is the real backend. The mock must be asked for by name.
    assert settings.backend == "gemini"
    assert settings.model is None
    assert settings.enable_docs is False
    assert settings.max_body_bytes == 2_000_000


def test_values_are_read_and_normalised() -> None:
    settings = load_settings(
        {
            "ALIGNMENT_SERVICE_TOKEN": "  " + "a" * 20 + "  ",
            "ALIGNMENT_BACKEND": " MOCK ",
            "ALIGNMENT_MODEL": " some-model ",
            "ALIGNMENT_MAX_BODY_BYTES": "5000",
            "ALIGNMENT_ENABLE_DOCS": "Yes",
            "ALIGNMENT_LOG_LEVEL": "debug",
        }
    )

    assert settings.service_token == "a" * 20
    assert settings.backend == "mock"
    assert settings.model == "some-model"
    assert settings.max_body_bytes == 5000
    assert settings.enable_docs is True
    assert settings.log_level == "DEBUG"


def test_short_token_is_rejected_without_echoing_it() -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_settings({"ALIGNMENT_SERVICE_TOKEN": "tooshort"})

    assert "tooshort" not in str(raised.value)


def test_unknown_backend_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        load_settings({"ALIGNMENT_BACKEND": "not-a-backend"})


@pytest.mark.parametrize("value", ["abc", "5", "999999999999"])
def test_body_limit_must_be_a_sensible_integer(value: str) -> None:
    with pytest.raises(ConfigurationError):
        load_settings({"ALIGNMENT_MAX_BODY_BYTES": value})


def test_repr_never_contains_the_token() -> None:
    settings = Settings(service_token="secret-token-value-123456")

    assert "secret-token-value-123456" not in repr(settings)


def test_explicit_environment_never_reads_an_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ALIGNMENT_SERVICE_TOKEN=" + "f" * 24 + "\n")

    assert load_settings({}, env_file=env_file).service_token is None


def test_env_file_never_imports_moodle_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The repository .env also holds Moodle DB credentials; the service must not get them."""

    for name in ("ALIGNMENT_MODEL", "GEMINI_API_KEY", "ALIGNMENT_ENV_FILE"):
        monkeypatch.setenv(name, "placeholder")

    monkeypatch.delenv("ALIGNMENT_MODEL")
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("ALIGNMENT_ENV_FILE")
    sentinel = "FROM-ENV-FILE-SENTINEL"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"DATABASE_PASSWORD={sentinel}",
                f"DATABASE_USER={sentinel}",
                f"MOODLE_TOKEN={sentinel}",
                f"MOODLE_BASE_URL={sentinel}",
                f"ALIGNMENT_MODEL={sentinel}",
                f"GEMINI_API_KEY={sentinel}",
            ]
        )
    )

    settings = load_settings(env_file=env_file)

    # Provider settings the engine needs are imported ...
    assert settings.model == sentinel
    assert os.environ["GEMINI_API_KEY"] == sentinel

    # ... but nothing that grants access to Moodle is.
    for name in ("DATABASE_PASSWORD", "DATABASE_USER", "MOODLE_TOKEN", "MOODLE_BASE_URL"):
        assert os.environ.get(name) != sentinel


def test_env_file_fills_gaps_without_overriding_the_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # setenv-then-delenv makes monkeypatch remove whatever load_dotenv adds.
    for name in ("ALIGNMENT_BACKEND", "ALIGNMENT_MODEL", "ALIGNMENT_ENV_FILE"):
        monkeypatch.setenv(name, "placeholder")

    monkeypatch.delenv("ALIGNMENT_BACKEND")
    monkeypatch.delenv("ALIGNMENT_ENV_FILE")
    monkeypatch.setenv("ALIGNMENT_MODEL", "from-process")
    env_file = tmp_path / ".env"
    env_file.write_text("ALIGNMENT_BACKEND=ollama\nALIGNMENT_MODEL=from-file\n")

    settings = load_settings(env_file=env_file)

    assert settings.backend == "ollama"
    assert settings.model == "from-process"
