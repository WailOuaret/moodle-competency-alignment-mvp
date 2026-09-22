"""Build constrained LLM tasks from BM25 candidate sets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from moodle_competency.llm_tasks import (
    build_alignment_tasks,
    load_jsonl,
    validate_alignment_tasks,
    write_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CANDIDATES_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "bm25_candidates.jsonl"
)

COMPETENCIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "competencies.jsonl"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "llm_tasks.jsonl"
)

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "llm_tasks_manifest.json"
)


def main() -> int:
    try:
        candidate_sets = load_jsonl(
            CANDIDATES_PATH
        )

        competencies = load_jsonl(
            COMPETENCIES_PATH
        )

        tasks = build_alignment_tasks(
            candidate_sets=candidate_sets,
            competencies=competencies,
        )

        validation = validate_alignment_tasks(
            candidate_sets=candidate_sets,
            competencies=competencies,
            tasks=tasks,
            expected_candidate_count=5,
        )

        output_path = write_jsonl(
            tasks,
            OUTPUT_PATH,
        )

        manifest = {
            "input_files": {
                "bm25_candidates": str(
                    CANDIDATES_PATH.relative_to(
                        PROJECT_ROOT
                    )
                ),
                "competencies": str(
                    COMPETENCIES_PATH.relative_to(
                        PROJECT_ROOT
                    )
                ),
            },
            "output_file": str(
                OUTPUT_PATH.relative_to(
                    PROJECT_ROOT
                )
            ),
            "task_version": "1.0",
            "constraints": {
                "candidate_count": 5,
                "maximum_selections": 3,
                "abstention_allowed": True,
                "exact_evidence_required": True,
                "json_only": True,
            },
            "validation": validation,
        }

        MANIFEST_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        MANIFEST_PATH.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    print("=== CONSTRAINED LLM TASK GENERATION ===")
    print(
        "Source candidate sets: "
        f"{validation['source_candidate_sets']}"
    )
    print(
        "Source competencies: "
        f"{validation['source_competencies']}"
    )
    print(
        "Alignment tasks: "
        f"{validation['alignment_tasks']}"
    )
    print(
        "Candidates per task: "
        f"{validation['expected_candidates_per_task']}"
    )

    print(
        "\nMissing fragments: "
        f"{len(validation['missing_fragments'])}"
    )
    print(
        "Duplicate task IDs: "
        f"{len(validation['duplicate_task_ids'])}"
    )
    print(
        "Invalid candidate counts: "
        f"{len(validation['invalid_candidate_counts'])}"
    )
    print(
        "Unknown allowed IDs: "
        f"{len(validation['unknown_allowed_ids'])}"
    )
    print(
        "Inconsistent allowed IDs: "
        f"{len(validation['inconsistent_allowed_ids'])}"
    )
    print(
        "Empty prompts: "
        f"{len(validation['empty_prompts'])}"
    )
    print(
        "Incomplete candidate profiles: "
        f"{len(validation['incomplete_candidate_profiles'])}"
    )

    print(f"\nDataset: {output_path}")
    print(f"Manifest: {MANIFEST_PATH}")

    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
