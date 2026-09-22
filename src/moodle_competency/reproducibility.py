"""Build a reproducibility manifest without secrets."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from moodle_competency.annotation import write_json


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def git_commit_hash(project_root: Path) -> str | None:
    git_dir = project_root / ".git"

    if not git_dir.exists():
        return None

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    return result.stdout.strip() or None


def installed_versions(names: tuple[str, ...]) -> dict[str, str]:
    versions: dict[str, str] = {}

    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"

    return versions


def jsonl_count(path: Path) -> int | None:
    if not path.exists():
        return None

    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def build_reproducibility_manifest(
    project_root: Path,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect environment and dataset counts. Never reads .env."""

    processed = project_root / "data" / "processed"
    interim = project_root / "data" / "interim"
    gold = project_root / "data" / "gold"

    manifest: dict[str, Any] = {
        "python_version": platform.python_version(),
        "package_version": "0.1.0",
        "dependency_versions": installed_versions(
            (
                "rank-bm25",
                "scikit-learn",
                "google-genai",
                "requests",
                "beautifulsoup4",
                "pytest",
                "pypdf",
                "streamlit",
                "matplotlib",
            )
        ),
        "moodle_version": None,
        "model_id": "gemini-3.5-flash",
        "temperature": 0,
        "prompt_version": "1.0",
        "schema_version": "1.0",
        "candidate_count": 5,
        "max_selections": 3,
        "resource_count": jsonl_count(processed / "resources.jsonl"),
        "fragment_count": jsonl_count(processed / "fragments.jsonl"),
        "competency_count": jsonl_count(
            processed / "competencies.jsonl"
        ),
        "gold_annotation_count": None,
        "reference_annotation_row_count": None,
        "reference_annotation_complete_count": None,
        "reference_label_count": None,
        "multi_label_fragment_count": None,
        "ambiguous_fragment_count": None,
        "none_fragment_count": None,
        "validated_gemini_count": jsonl_count(
            interim / "gemini_validated.jsonl"
        ),
        "timestamp": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "git_commit": git_commit_hash(project_root),
        "hashes": {
            "resources.jsonl": file_sha256(
                processed / "resources.jsonl"
            ),
            "fragments.jsonl": file_sha256(
                processed / "fragments.jsonl"
            ),
            "competencies.jsonl": file_sha256(
                processed / "competencies.jsonl"
            ),
            "bm25_candidates.jsonl": file_sha256(
                interim / "bm25_candidates.jsonl"
            ),
            "llm_tasks.jsonl": file_sha256(
                interim / "llm_tasks.jsonl"
            ),
            "gemini_validated.jsonl": file_sha256(
                interim / "gemini_validated.jsonl"
            ),
            "manual_fragment_annotations.csv": file_sha256(
                gold / "manual_fragment_annotations.csv"
            ),
            "resource_predictions.jsonl": file_sha256(
                processed / "resource_predictions.jsonl"
            ),
            "competency_resource_index.jsonl": file_sha256(
                processed / "competency_resource_index.jsonl"
            ),
            "bm25_metrics.json": file_sha256(
                project_root / "reports" / "metrics" / "bm25_metrics.json"
            ),
            "constrained_llm_metrics.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "constrained_llm_metrics.json"
            ),
            "model_comparison.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "model_comparison.csv"
            ),
            "evidence_review.csv": file_sha256(
                project_root / "data" / "reviews" / "evidence_review.csv"
            ),
            "error_analysis.csv": file_sha256(
                project_root / "reports" / "tables" / "error_analysis.csv"
            ),
            "error_summary.json": file_sha256(
                project_root / "reports" / "metrics" / "error_summary.json"
            ),
            "error_examples.csv": file_sha256(
                project_root / "reports" / "tables" / "error_examples.csv"
            ),
            "evidence_review_summary.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "evidence_review_summary.json"
            ),
            "EVIDENCE_AWARE_ERROR_ANALYSIS.md": file_sha256(
                project_root
                / "reports"
                / "EVIDENCE_AWARE_ERROR_ANALYSIS.md"
            ),
            "resource_reference.jsonl": file_sha256(
                processed / "resource_reference.jsonl"
            ),
            "resource_level_metrics.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "resource_level_metrics.json"
            ),
            "resource_level_evaluation.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "resource_level_evaluation.csv"
            ),
            "resource_level_per_competency.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "resource_level_per_competency.csv"
            ),
            "resource_level_error_examples.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "resource_level_error_examples.csv"
            ),
            "RESOURCE_LEVEL_EVALUATION.md": file_sha256(
                project_root
                / "reports"
                / "RESOURCE_LEVEL_EVALUATION.md"
            ),
            "macro_label_views.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "macro_label_views.json"
            ),
            "system_delta_summary.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "system_delta_summary.csv"
            ),
            "graph_warnings.jsonl": file_sha256(
                processed / "graph_warnings.jsonl"
            ),
            "graph_warnings.csv": file_sha256(
                project_root / "reports" / "tables" / "graph_warnings.csv"
            ),
            "graph_check_summary.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "graph_check_summary.json"
            ),
            "graph_child_preference_predictions.jsonl": file_sha256(
                project_root
                / "data"
                / "experiments"
                / "graph_child_preference_predictions.jsonl"
            ),
            "graph_child_preference_manifest.json": file_sha256(
                project_root
                / "data"
                / "experiments"
                / "graph_child_preference_manifest.json"
            ),
            "graph_child_preference_fragment_metrics.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "graph_child_preference_fragment_metrics.json"
            ),
            "graph_child_preference_resource_predictions.jsonl": file_sha256(
                project_root
                / "data"
                / "experiments"
                / "graph_child_preference_resource_predictions.jsonl"
            ),
            "graph_child_preference_resource_metrics.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "graph_child_preference_resource_metrics.json"
            ),
            "MINIMAL_GRAPH_HIERARCHY_ANALYSIS.md": file_sha256(
                project_root
                / "reports"
                / "MINIMAL_GRAPH_HIERARCHY_ANALYSIS.md"
            ),
            "teacher_reviews.csv": file_sha256(
                project_root / "data" / "reviews" / "teacher_reviews.csv"
            ),
            "resource_ingestion.py": file_sha256(
                project_root
                / "src"
                / "moodle_competency"
                / "resource_ingestion.py"
            ),
            "runtime_analysis.py": file_sha256(
                project_root
                / "src"
                / "moodle_competency"
                / "runtime_analysis.py"
            ),
            "runtime_storage.py": file_sha256(
                project_root
                / "src"
                / "moodle_competency"
                / "runtime_storage.py"
            ),
            "teacher_ui.py": file_sha256(
                project_root / "src" / "moodle_competency" / "teacher_ui.py"
            ),
            "teacher_app_pages.py": file_sha256(
                project_root
                / "src"
                / "moodle_competency"
                / "teacher_app_pages.py"
            ),
            "app.py": file_sha256(project_root / "app.py"),
            "TEACHER_RUNTIME_WORKFLOW.md": file_sha256(
                project_root / "docs" / "TEACHER_RUNTIME_WORKFLOW.md"
            ),
            "TEACHER_DEMO_GUIDE.md": file_sha256(
                project_root / "docs" / "TEACHER_DEMO_GUIDE.md"
            ),
            "ollama_constrained_validated.jsonl": file_sha256(
                project_root
                / "data"
                / "experiments"
                / "ollama_constrained_validated.jsonl"
            ),
            "ollama_constrained_metrics.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "ollama_constrained_metrics.json"
            ),
            "human_validation_summary.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "human_validation_summary.json"
            ),
            "HUMAN_VALIDATION_SUMMARY.md": file_sha256(
                project_root
                / "reports"
                / "HUMAN_VALIDATION_SUMMARY.md"
            ),
            "human_validation_reviews.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "human_validation_reviews.csv"
            ),
            "final_results_summary.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "final_results_summary.csv"
            ),
            "final_key_examples.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "final_key_examples.csv"
            ),
            "FINAL_INTERNSHIP_REPORT.md": file_sha256(
                project_root
                / "reports"
                / "FINAL_INTERNSHIP_REPORT.md"
            ),
            "FINAL_PROJECT_AUDIT.md": file_sha256(
                project_root / "reports" / "FINAL_PROJECT_AUDIT.md"
            ),
            "bm25_recall_at_k.png": file_sha256(
                project_root / "reports" / "figures" / "bm25_recall_at_k.png"
            ),
            "fragment_system_comparison.png": file_sha256(
                project_root
                / "reports"
                / "figures"
                / "fragment_system_comparison.png"
            ),
            "resource_system_comparison.png": file_sha256(
                project_root
                / "reports"
                / "figures"
                / "resource_system_comparison.png"
            ),
            "evidence_quality.png": file_sha256(
                project_root / "reports" / "figures" / "evidence_quality.png"
            ),
            "error_categories.png": file_sha256(
                project_root / "reports" / "figures" / "error_categories.png"
            ),
            "human_validation_summary.py": file_sha256(
                project_root
                / "src"
                / "moodle_competency"
                / "human_validation_summary.py"
            ),
            # Frozen-corpus teacher interface (Section L). The review file is
            # separate from the runtime app's teacher_reviews.csv above.
            "corpus_teacher_reviews.csv": file_sha256(
                project_root / "data" / "reviews" / "corpus_teacher_reviews.csv"
            ),
            "teacher_review_summary.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "teacher_review_summary.json"
            ),
            "teacher_review_summary.csv": file_sha256(
                project_root
                / "reports"
                / "tables"
                / "teacher_review_summary.csv"
            ),
            "corpus_app.py": file_sha256(
                project_root / "src" / "moodle_competency" / "corpus_app.py"
            ),
            "teacher_review_summary.py": file_sha256(
                project_root
                / "src"
                / "moodle_competency"
                / "teacher_review_summary.py"
            ),
            "coverage.py": file_sha256(
                project_root / "src" / "moodle_competency" / "coverage.py"
            ),
            "TEACHER_INTERFACE_GUIDE.md": file_sha256(
                project_root / "docs" / "TEACHER_INTERFACE_GUIDE.md"
            ),
            # Evidence-usefulness pilot (Section M).
            "teacher_study.py": file_sha256(
                project_root / "src" / "moodle_competency" / "teacher_study.py"
            ),
            "teacher_study_cases.csv": file_sha256(
                project_root / "data" / "studies" / "teacher_study_cases.csv"
            ),
            "teacher_study_manifest.json": file_sha256(
                project_root / "data" / "studies" / "teacher_study_manifest.json"
            ),
            "teacher_study_responses.csv": file_sha256(
                project_root / "data" / "studies" / "teacher_study_responses.csv"
            ),
            # Optional unconstrained all-13 comparison (Section K). These stay
            # None until the experiment is explicitly authorized and run.
            "unconstrained_llm.py": file_sha256(
                project_root
                / "src"
                / "moodle_competency"
                / "unconstrained_llm.py"
            ),
            "unconstrained_llm_tasks.jsonl": file_sha256(
                project_root
                / "data"
                / "experiments"
                / "unconstrained_llm_tasks.jsonl"
            ),
            "unconstrained_llm_tasks_manifest.json": file_sha256(
                project_root
                / "data"
                / "experiments"
                / "unconstrained_llm_tasks_manifest.json"
            ),
            "unconstrained_gemini_validated.jsonl": file_sha256(
                project_root
                / "data"
                / "experiments"
                / "unconstrained_gemini_validated.jsonl"
            ),
            "unconstrained_llm_metrics.json": file_sha256(
                project_root
                / "reports"
                / "metrics"
                / "unconstrained_llm_metrics.json"
            ),
        },
        "contains_secrets": False,
    }

    site_info = project_root / "reports" / "site_info.json"

    if site_info.exists():
        try:
            payload = json.loads(
                site_info.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError:
            payload = {}

        release = payload.get("release")

        if isinstance(release, str) and release.strip():
            manifest["moodle_version"] = release.strip()

    gold_path = gold / "manual_fragment_annotations.csv"

    if gold_path.exists():
        from moodle_competency.annotation import (
            parse_boolean,
            parse_competency_ids,
            read_csv,
        )
        from moodle_competency.annotation_session import (
            is_row_complete,
        )

        rows = read_csv(gold_path)
        complete_count = sum(1 for row in rows if is_row_complete(row))
        label_count = 0
        multi_label_count = 0
        ambiguous_count = 0
        none_count = 0

        for row in rows:
            ids, _errors = parse_competency_ids(
                row.get("gold_competency_ids")
            )
            label_count += len(ids)

            if len(ids) > 1:
                multi_label_count += 1

            no_competency, _nc_errors = parse_boolean(
                row.get("no_competency"),
                "no_competency",
            )

            if no_competency is True:
                none_count += 1

            ambiguous, _amb_errors = parse_boolean(
                row.get("ambiguous"),
                "ambiguous",
            )

            if ambiguous is True:
                ambiguous_count += 1

        # Unambiguous names. Legacy keys remain, but gold_annotation_count
        # is no longer left null: it equals the complete-row count.
        manifest["reference_annotation_row_count"] = len(rows)
        manifest["reference_annotation_complete_count"] = complete_count
        manifest["reference_label_count"] = label_count
        manifest["multi_label_fragment_count"] = multi_label_count
        manifest["ambiguous_fragment_count"] = ambiguous_count
        manifest["none_fragment_count"] = none_count
        manifest["gold_annotation_row_count"] = len(rows)
        manifest["gold_annotation_complete_count"] = complete_count
        manifest["gold_annotation_count"] = complete_count

    if extra:
        manifest.update(dict(extra))

    return manifest


def write_reproducibility_manifest(
    project_root: Path,
    output_path: Path | None = None,
) -> Path:
    target = output_path or (
        project_root
        / "reports"
        / "reproducibility_manifest.json"
    )
    manifest = build_reproducibility_manifest(project_root)
    write_json(manifest, target)
    return target
