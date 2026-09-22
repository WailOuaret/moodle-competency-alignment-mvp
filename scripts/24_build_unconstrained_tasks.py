"""Build the optional all-13 unconstrained alignment tasks (Section K).

Builds one task per fragment whose candidate space is the whole 13-competency
framework rather than a BM25 Top-5 subset, and audits that the two conditions
differ in nothing else.

This script makes no API call. It only writes task files under
``data/experiments/``, and never touches a constrained artefact.

    python scripts/24_build_unconstrained_tasks.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl, write_json
from moodle_competency.llm_validation import write_jsonl
from moodle_competency.unconstrained_llm import (
    EXPECTED_CANDIDATE_COUNT,
    UnconstrainedTaskError,
    build_unconstrained_tasks,
    compare_conditions,
    experiment_manifest,
    validate_unconstrained_tasks,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

FRAGMENTS = PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
CONSTRAINED_TASKS = PROJECT_ROOT / "data" / "interim" / "llm_tasks.jsonl"

EXPERIMENTS = PROJECT_ROOT / "data" / "experiments"
TASKS_OUT = EXPERIMENTS / "unconstrained_llm_tasks.jsonl"
MANIFEST_OUT = EXPERIMENTS / "unconstrained_llm_tasks_manifest.json"

DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_TEMPERATURE = 0.0

PROTECTED_PATHS = (
    PROJECT_ROOT / "data" / "processed" / "fragments.jsonl",
    PROJECT_ROOT / "data" / "processed" / "competencies.jsonl",
    PROJECT_ROOT / "data" / "interim" / "llm_tasks.jsonl",
    PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_responses.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
    PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv",
)


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)

    return digest.hexdigest()


def snapshot_protected() -> dict[str, str | None]:
    return {str(path): file_sha256(path) for path in PROTECTED_PATHS}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the optional all-13 unconstrained alignment tasks.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing unconstrained task file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    for path in (FRAGMENTS, COMPETENCIES):
        if not path.exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 2

    if TASKS_OUT.exists() and not args.force:
        print(
            f"{TASKS_OUT} already exists. Pass --force to rebuild it.",
            file=sys.stderr,
        )
        return 3

    before = snapshot_protected()

    fragments = load_jsonl(FRAGMENTS)
    competencies = load_jsonl(COMPETENCIES)

    if len(competencies) != EXPECTED_CANDIDATE_COUNT:
        print(
            f"Expected {EXPECTED_CANDIDATE_COUNT} competencies, "
            f"found {len(competencies)}. Refusing to build.",
            file=sys.stderr,
        )
        return 4

    try:
        tasks = build_unconstrained_tasks(
            fragments=fragments,
            competencies=competencies,
        )
    except UnconstrainedTaskError as error:
        print(f"Could not build tasks: {error}", file=sys.stderr)
        return 5

    validation = validate_unconstrained_tasks(
        tasks,
        expected_fragment_ids=[
            str(fragment.get("fragment_id", "")).strip() for fragment in fragments
        ],
    )

    if validation["status"] != "PASSED":
        print("Task validation FAILED:", file=sys.stderr)

        for error in validation["errors"]:
            print(f"  {error}", file=sys.stderr)

        return 6

    comparison = None

    if CONSTRAINED_TASKS.exists():
        comparison = compare_conditions(
            constrained_tasks=load_jsonl(CONSTRAINED_TASKS),
            unconstrained_tasks=tasks,
        )

        if comparison["status"] != "PASSED":
            print(
                "The two conditions differ in more than the candidate space:",
                file=sys.stderr,
            )

            for error in comparison["errors"]:
                print(f"  {error}", file=sys.stderr)

            return 7
    else:
        print(
            f"Note: {CONSTRAINED_TASKS} is absent, so the two conditions could "
            "not be compared.",
        )

    EXPERIMENTS.mkdir(parents=True, exist_ok=True)
    write_jsonl(tasks, TASKS_OUT)

    manifest = experiment_manifest(
        tasks=tasks,
        model_name=args.model,
        temperature=args.temperature,
        validation=validation,
        comparison=comparison,
    )
    manifest["source_files"] = {
        "fragments.jsonl": file_sha256(FRAGMENTS),
        "competencies.jsonl": file_sha256(COMPETENCIES),
        "llm_tasks.jsonl": file_sha256(CONSTRAINED_TASKS),
    }
    write_json(manifest, MANIFEST_OUT)

    after = snapshot_protected()
    mutated = [path for path in before if before[path] != after[path]]

    if mutated:
        print("Protected files changed. This is a bug:", file=sys.stderr)

        for path in mutated:
            print(f"  {path}", file=sys.stderr)

        return 8

    print(f"Wrote {TASKS_OUT}")
    print(f"Wrote {MANIFEST_OUT}")
    print()
    print(f"Tasks built: {len(tasks)}")
    print(f"Candidates per task: {manifest['candidate_counts_observed']}")
    print(f"Task validation: {validation['status']}")

    if comparison:
        print(f"Condition comparison: {comparison['status']}")
        print(
            f"  shared fragments: {comparison['shared_fragment_count']}; "
            f"fragment-text mismatches: {len(comparison['fragment_text_mismatches'])}; "
            f"instruction mismatches: {len(comparison['instruction_mismatches'])}"
        )
        print(f"  intended difference: {comparison['intended_difference']}")
        print(f"  presentation difference: {comparison['presentation_difference']}")

    print()
    print("NO API CALL WAS MADE. This step only built task files.")
    print(
        "The live run is optional and spends API quota. It requires explicit "
        "researcher authorization; see scripts/25_run_unconstrained_gemini.py."
    )
    print("Protected files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
