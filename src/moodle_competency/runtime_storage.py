"""Persist runtime analyses separately from the frozen research experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.annotation import write_json
from moodle_competency.reproducibility import file_sha256
from moodle_competency.settings import PROJECT_ROOT


RUNTIME_SUBDIRS = (
    "uploads",
    "resources",
    "fragments",
    "retrieval",
    "model_responses",
    "analyses",
    "manifests",
)

FROZEN_RELATIVE_PATHS = (
    "data/gold/manual_fragment_annotations.csv",
    "data/interim/bm25_candidates.jsonl",
    "data/interim/gemini_responses.jsonl",
    "data/interim/gemini_validated.jsonl",
    "data/processed/fragments.jsonl",
    "data/processed/resource_predictions.jsonl",
    "reports/metrics/bm25_metrics.json",
    "reports/metrics/constrained_llm_metrics.json",
    "reports/metrics/resource_level_metrics.json",
    "data/reviews/evidence_review.csv",
    "data/experiments/graph_child_preference_predictions.jsonl",
    "data/experiments/ollama_constrained_responses.jsonl",
    "data/experiments/ollama_constrained_validated.jsonl",
    "data/experiments/ollama_constrained_raw_attempts.jsonl",
    "data/experiments/ollama_constrained_manifest.json",
)

SECRET_KEY_MARKERS = (
    "api_key",
    "apikey",
    "x-goog-api-key",
    "moodle_token",
    "token",
    "password",
    "secret",
    "userprivateaccesskey",
    "gemini_api_key",
    "authorization",
)

SECRET_VALUE_MARKERS = (
    "GEMINI_API_KEY",
    "MOODLE_TOKEN",
    "userprivateaccesskey",
)


class FrozenResearchFileError(RuntimeError):
    """Raised when a write would touch a frozen experimental artefact."""


class SecretInManifestError(ValueError):
    """Raised when a runtime manifest would store a secret."""


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    root: Path

    @property
    def runtime(self) -> Path:
        return self.root / "data" / "runtime"

    @property
    def uploads(self) -> Path:
        return self.runtime / "uploads"

    @property
    def resources(self) -> Path:
        return self.runtime / "resources"

    @property
    def fragments(self) -> Path:
        return self.runtime / "fragments"

    @property
    def retrieval(self) -> Path:
        return self.runtime / "retrieval"

    @property
    def model_responses(self) -> Path:
        return self.runtime / "model_responses"

    @property
    def analyses(self) -> Path:
        return self.runtime / "analyses"

    @property
    def manifests(self) -> Path:
        return self.runtime / "manifests"

    @property
    def reviews(self) -> Path:
        return self.root / "data" / "reviews" / "teacher_reviews.csv"


def runtime_paths(project_root: Path | None = None) -> RuntimePaths:
    return RuntimePaths(root=Path(project_root or PROJECT_ROOT))


def ensure_runtime_dirs(paths: RuntimePaths | None = None) -> RuntimePaths:
    resolved = paths or runtime_paths()

    for name in RUNTIME_SUBDIRS:
        (resolved.runtime / name).mkdir(parents=True, exist_ok=True)

    resolved.reviews.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def frozen_file_hashes(project_root: Path | None = None) -> dict[str, str | None]:
    root = Path(project_root or PROJECT_ROOT)
    return {
        relative: file_sha256(root / relative)
        for relative in FROZEN_RELATIVE_PATHS
    }


def is_frozen_path(path: Path, project_root: Path | None = None) -> bool:
    root = Path(project_root or PROJECT_ROOT).resolve()
    resolved = Path(path).resolve()

    for relative in FROZEN_RELATIVE_PATHS:
        frozen = (root / relative).resolve()

        if resolved == frozen:
            return True

    return False


def assert_not_frozen_write(
    path: Path,
    project_root: Path | None = None,
) -> None:
    if is_frozen_path(path, project_root):
        raise FrozenResearchFileError(
            f"Refusing to write frozen research file: {path}"
        )


def _contains_secret_key(key: str) -> bool:
    lowered = key.casefold().replace("-", "_")

    if lowered in {
        "token",
        "password",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "moodle_token",
        "gemini_api_key",
        "userprivateaccesskey",
        "x_goog_api_key",
    }:
        return True

    return (
        lowered.endswith("_token")
        or lowered.endswith("_password")
        or lowered.endswith("_secret")
        or lowered.endswith("_api_key")
        or lowered.endswith("apikey")
    )


def collect_secret_violations(payload: Any, prefix: str = "") -> list[str]:
    found: list[str] = []

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            location = f"{prefix}.{key}" if prefix else str(key)

            if _contains_secret_key(str(key)):
                found.append(location)

            found.extend(collect_secret_violations(value, location))
    elif isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            found.extend(
                collect_secret_violations(
                    item,
                    f"{prefix}[{index}]",
                )
            )
    elif isinstance(payload, str):
        for marker in SECRET_VALUE_MARKERS:
            if marker in payload:
                found.append(prefix or "<string>")

    return found


def redact_secrets(payload: Any) -> Any:
    """Replace secret-bearing keys. Never store API keys or tokens."""

    if isinstance(payload, Mapping):
        redacted: dict[str, Any] = {}

        for key, value in payload.items():
            if _contains_secret_key(str(key)):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = redact_secrets(value)

        return redacted

    if isinstance(payload, list):
        return [redact_secrets(item) for item in payload]

    if isinstance(payload, tuple):
        return [redact_secrets(item) for item in payload]

    return payload


def assert_no_secrets(payload: Mapping[str, Any]) -> None:
    violations = collect_secret_violations(payload)

    if violations:
        raise SecretInManifestError(
            "Runtime manifest must not contain secrets: "
            + ", ".join(violations[:8])
        )


def write_json_safe(
    payload: Mapping[str, Any],
    output_path: Path,
    *,
    project_root: Path | None = None,
) -> Path:
    assert_not_frozen_write(output_path, project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return write_json(payload, output_path)


def write_jsonl_safe(
    records: Sequence[Mapping[str, Any]],
    output_path: Path,
    *,
    project_root: Path | None = None,
) -> Path:
    assert_not_frozen_write(output_path, project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return output_path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))

    return records


def save_runtime_resource(
    resource: Mapping[str, Any],
    paths: RuntimePaths,
) -> Path:
    resource_id = str(resource["runtime_resource_id"])
    target = paths.resources / f"{_safe_id(resource_id)}.json"
    return write_json_safe(resource, target, project_root=paths.root)


def save_analysis_artefacts(
    *,
    analysis_id: str,
    resource: Mapping[str, Any],
    fragments: Sequence[Mapping[str, Any]],
    retrieval: Sequence[Mapping[str, Any]],
    raw_responses: Sequence[Mapping[str, Any]],
    validated_responses: Sequence[Mapping[str, Any]],
    analysis: Mapping[str, Any],
    manifest: Mapping[str, Any],
    paths: RuntimePaths | None = None,
) -> dict[str, Path]:
    resolved = ensure_runtime_dirs(paths)
    assert_no_secrets(manifest)
    safe_id = _safe_id(analysis_id)

    written = {
        "resource": save_runtime_resource(resource, resolved),
        "fragments": write_jsonl_safe(
            fragments,
            resolved.fragments / f"{safe_id}.jsonl",
            project_root=resolved.root,
        ),
        "retrieval": write_jsonl_safe(
            retrieval,
            resolved.retrieval / f"{safe_id}.jsonl",
            project_root=resolved.root,
        ),
        "raw_responses": write_jsonl_safe(
            raw_responses,
            resolved.model_responses / f"{safe_id}_raw.jsonl",
            project_root=resolved.root,
        ),
        "validated_responses": write_jsonl_safe(
            validated_responses,
            resolved.model_responses / f"{safe_id}_validated.jsonl",
            project_root=resolved.root,
        ),
        "analysis": write_json_safe(
            analysis,
            resolved.analyses / f"{safe_id}.json",
            project_root=resolved.root,
        ),
        "manifest": write_json_safe(
            manifest,
            resolved.manifests / f"{safe_id}.json",
            project_root=resolved.root,
        ),
    }
    return written


def list_analysis_ids(paths: RuntimePaths | None = None) -> list[str]:
    resolved = ensure_runtime_dirs(paths)
    return sorted(
        path.stem
        for path in resolved.analyses.glob("*.json")
    )


def load_analysis(
    analysis_id: str,
    paths: RuntimePaths | None = None,
) -> dict[str, Any]:
    resolved = paths or runtime_paths()
    return load_json(
        resolved.analyses / f"{_safe_id(analysis_id)}.json"
    )


def load_all_analyses(
    paths: RuntimePaths | None = None,
) -> list[dict[str, Any]]:
    resolved = ensure_runtime_dirs(paths)
    analyses = [
        load_json(path)
        for path in sorted(resolved.analyses.glob("*.json"))
    ]
    return analyses


def _safe_id(value: str) -> str:
    return str(value).replace("/", "_").replace(":", "_")
