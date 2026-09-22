"""Runtime storage tests. Writes stay under a temporary runtime tree."""

from __future__ import annotations

from pathlib import Path

import pytest

from moodle_competency.runtime_storage import (
    FrozenResearchFileError,
    SecretInManifestError,
    assert_no_secrets,
    assert_not_frozen_write,
    collect_secret_violations,
    ensure_runtime_dirs,
    frozen_file_hashes,
    redact_secrets,
    runtime_paths,
    save_analysis_artefacts,
)
from moodle_competency.settings import PROJECT_ROOT


def test_runtime_dirs_created(tmp_path: Path) -> None:
    paths = ensure_runtime_dirs(runtime_paths(tmp_path))

    assert (paths.runtime / "uploads").is_dir()
    assert (paths.runtime / "manifests").is_dir()
    assert (paths.runtime / "model_responses").is_dir()


def test_runtime_manifest_and_no_secrets(tmp_path: Path) -> None:
    paths = ensure_runtime_dirs(runtime_paths(tmp_path))
    manifest = {
        "analysis_id": "an_test",
        "backend": "mock",
        "model": "mock-model",
        "temperature": 0,
    }
    written = save_analysis_artefacts(
        analysis_id="an_test",
        resource={"runtime_resource_id": "runtime:paste:abc", "title": "T"},
        fragments=[{"fragment_id": "runtime:paste:abc#f001"}],
        retrieval=[],
        raw_responses=[{"fragment_id": "runtime:paste:abc#f001"}],
        validated_responses=[{"fragment_id": "runtime:paste:abc#f001", "valid": True}],
        analysis={"analysis_id": "an_test"},
        manifest=manifest,
        paths=paths,
    )

    assert written["manifest"].exists()
    assert "data/runtime/manifests" in str(written["manifest"])
    assert_no_secrets(manifest)


def test_secret_values_rejected() -> None:
    with pytest.raises(SecretInManifestError):
        assert_no_secrets({"GEMINI_API_KEY": "abc"})

    payload = {"headers": {"x-goog-api-key": "secret-value"}}
    redacted = redact_secrets(payload)
    assert redacted["headers"]["x-goog-api-key"] == "[REDACTED]"
    assert collect_secret_violations({"note": "GEMINI_API_KEY=abc"})


def test_refuses_frozen_write(tmp_path: Path) -> None:
    frozen = PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl"

    with pytest.raises(FrozenResearchFileError):
        assert_not_frozen_write(frozen, PROJECT_ROOT)


def test_frozen_hashes_helper_covers_protected_files() -> None:
    hashes = frozen_file_hashes(PROJECT_ROOT)

    assert "data/gold/manual_fragment_annotations.csv" in hashes
    assert "data/interim/gemini_validated.jsonl" in hashes
    assert "data/reviews/evidence_review.csv" in hashes
    assert "data/experiments/graph_child_preference_predictions.jsonl" in hashes
