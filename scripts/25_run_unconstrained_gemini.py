"""Run the OPTIONAL all-13 unconstrained Gemini experiment (Section K).

*** THIS SCRIPT SPENDS API QUOTA. ***

It refuses to run unless the researcher authorizes it explicitly, by passing
the exact confirmation phrase:

    python scripts/25_run_unconstrained_gemini.py \\
        --i-authorize-the-unconstrained-experiment

A dry run needs no authorization and makes no request:

    python scripts/25_run_unconstrained_gemini.py --dry-run

Everything is written under ``data/experiments/``. The constrained responses in
``data/interim/`` are never read for writing, never resumed from and never
overwritten. There is no ``--restart``: the constrained run's prohibition on
regenerating history applies here too, so an existing output file is left alone
unless ``--force`` is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from moodle_competency.annotation import load_jsonl, write_json
from moodle_competency.gemini_alignment import (
    GeminiAlignmentClient,
    GeminiAlignmentError,
    GeminiQuotaExhaustedError,
)
from moodle_competency.llm_validation import (
    validate_response_collection,
    write_jsonl,
)
from moodle_competency.unconstrained_llm import experiment_manifest


PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXPERIMENTS = PROJECT_ROOT / "data" / "experiments"
TASKS_IN = EXPERIMENTS / "unconstrained_llm_tasks.jsonl"
RESPONSES_OUT = EXPERIMENTS / "unconstrained_gemini_responses.jsonl"
VALIDATED_OUT = EXPERIMENTS / "unconstrained_gemini_validated.jsonl"
RAW_OUT = EXPERIMENTS / "unconstrained_gemini_raw_attempts.jsonl"
MANIFEST_OUT = EXPERIMENTS / "unconstrained_gemini_run_manifest.json"

DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_TEMPERATURE = 0.0

AUTHORIZATION_FLAG = "--i-authorize-the-unconstrained-experiment"

#: Constrained artefacts. This script must never modify any of them.
PROTECTED_PATHS = (
    PROJECT_ROOT / "data" / "interim" / "llm_tasks.jsonl",
    PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_responses.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
    PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv",
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json",
    PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json",
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
        description=(
            "Run the optional all-13 unconstrained Gemini experiment. "
            "Spends API quota; requires explicit authorization."
        ),
    )
    parser.add_argument(
        "--i-authorize-the-unconstrained-experiment",
        dest="authorized",
        action="store_true",
        help="Explicit researcher authorization to spend API quota.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be sent and exit without making any request.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Send at most this many tasks (for a cautious first run).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing unconstrained output files.",
    )
    return parser.parse_args()


def describe_plan(tasks: list[dict], args: argparse.Namespace) -> None:
    selected = tasks if args.limit is None else tasks[: args.limit]

    print("Unconstrained all-13 Gemini experiment — PLAN")
    print(f"  tasks available : {len(tasks)}")
    print(f"  tasks to send   : {len(selected)}")
    print(f"  model           : {args.model}")
    print(f"  temperature     : {args.temperature}")
    print(f"  candidate space : all 13 framework competencies")
    print(f"  outputs         : {EXPERIMENTS.relative_to(PROJECT_ROOT)}/")
    print()
    print("  Constrained artefacts are never read for writing or overwritten.")


def main() -> int:
    args = parse_arguments()

    if not TASKS_IN.exists():
        print(
            f"Missing {TASKS_IN}.\nBuild it first:\n"
            "  python scripts/24_build_unconstrained_tasks.py",
            file=sys.stderr,
        )
        return 2

    tasks = load_jsonl(TASKS_IN)

    if not tasks:
        print(f"{TASKS_IN} is empty.", file=sys.stderr)
        return 2

    if args.dry_run:
        describe_plan(tasks, args)
        print()
        print("DRY RUN. No request was made and no file was written.")
        return 0

    if not args.authorized:
        print(
            "REFUSED: this experiment is optional and spends API quota.\n\n"
            "It will not run without explicit researcher authorization.\n"
            "To authorize it, re-run with:\n\n"
            f"  python scripts/25_run_unconstrained_gemini.py {AUTHORIZATION_FLAG}\n\n"
            "To see what it would do without sending anything:\n\n"
            "  python scripts/25_run_unconstrained_gemini.py --dry-run",
            file=sys.stderr,
        )
        return 3

    existing = [path for path in (RESPONSES_OUT, VALIDATED_OUT) if path.exists()]

    if existing and not args.force:
        print(
            "Unconstrained output already exists:",
            file=sys.stderr,
        )

        for path in existing:
            print(f"  {path}", file=sys.stderr)

        print(
            "\nRefusing to regenerate it. Pass --force only if you intend to "
            "discard the previous unconstrained run.",
            file=sys.stderr,
        )
        return 4

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY is empty. Set it in the environment; never "
            "pass a key on the command line and never commit one.",
            file=sys.stderr,
        )
        return 5

    before = snapshot_protected()
    selected = tasks if args.limit is None else tasks[: args.limit]

    describe_plan(tasks, args)
    print()
    print("AUTHORIZED. Starting.")

    responses: list[dict] = []
    raw_attempts: list[dict] = []
    failures: list[dict] = []
    started = datetime.now(timezone.utc)

    with GeminiAlignmentClient(api_key=api_key, model=args.model) as client:
        for index, task in enumerate(selected, start=1):
            fragment_id = str(task.get("fragment_id", "")).strip()
            print(f"  [{index}/{len(selected)}] {fragment_id}", flush=True)

            try:
                parsed, raw, usage = client.align(task)
            except GeminiQuotaExhaustedError as error:
                print(
                    f"\nDaily quota exhausted at task {index}: {error}\n"
                    "Stopping. Completed responses are written below and the "
                    "run can be continued later with --force.",
                    file=sys.stderr,
                )
                failures.append({"fragment_id": fragment_id, "error": str(error)})
                break
            except GeminiAlignmentError as error:
                print(f"    FAILED: {error}", file=sys.stderr)
                failures.append({"fragment_id": fragment_id, "error": str(error)})
                continue

            responses.append(parsed)
            raw_attempts.append(
                {
                    "fragment_id": fragment_id,
                    "raw": raw,
                    "usage": {
                        "prompt_tokens": getattr(usage, "prompt_tokens", None),
                        "response_tokens": getattr(usage, "response_tokens", None),
                        "total_tokens": getattr(usage, "total_tokens", None),
                    },
                }
            )

    validated, validation_summary = validate_response_collection(
        tasks=selected,
        responses=responses,
    )

    EXPERIMENTS.mkdir(parents=True, exist_ok=True)
    write_jsonl(responses, RESPONSES_OUT)
    write_jsonl(validated, VALIDATED_OUT)
    write_jsonl(raw_attempts, RAW_OUT)

    manifest = experiment_manifest(
        tasks=selected,
        model_name=args.model,
        temperature=args.temperature,
    )
    manifest.update(
        {
            "run_started_utc": started.isoformat(),
            "run_finished_utc": datetime.now(timezone.utc).isoformat(),
            "authorized_by_flag": AUTHORIZATION_FLAG,
            "responses_received": len(responses),
            "responses_requested": len(selected),
            "failures": failures,
            "validation_summary": validation_summary,
        }
    )
    write_json(manifest, MANIFEST_OUT)

    after = snapshot_protected()
    mutated = [path for path in before if before[path] != after[path]]

    if mutated:
        print("Protected files changed. This is a bug:", file=sys.stderr)

        for path in mutated:
            print(f"  {path}", file=sys.stderr)

        return 8

    print()
    print(f"Wrote {RESPONSES_OUT}")
    print(f"Wrote {VALIDATED_OUT}")
    print(f"Wrote {RAW_OUT}")
    print(f"Wrote {MANIFEST_OUT}")
    print()
    print(f"Responses: {len(responses)} / {len(selected)}")
    print(f"Failures:  {len(failures)}")
    print(f"Validation: {json.dumps(validation_summary)[:400]}")
    print("Constrained outputs unchanged.")

    return 0 if not failures else 9


if __name__ == "__main__":
    raise SystemExit(main())
