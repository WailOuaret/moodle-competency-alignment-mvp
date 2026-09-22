"""Retrieve Top-K competency candidates for every Moodle fragment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.retrieval import (
    load_jsonl,
    retrieve_candidates,
    validate_candidate_sets,
    write_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FRAGMENTS = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fragments.jsonl"
)

DEFAULT_COMPETENCIES = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "competencies.jsonl"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "bm25_candidates.jsonl"
)

DEFAULT_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "bm25_candidates_manifest.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve ranked BM25 competency candidates "
            "for every Moodle fragment."
        )
    )

    parser.add_argument(
        "--fragments",
        type=Path,
        default=DEFAULT_FRAGMENTS,
    )

    parser.add_argument(
        "--competencies",
        type=Path,
        default=DEFAULT_COMPETENCIES,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        fragments = load_jsonl(
            arguments.fragments.resolve()
        )

        competencies = load_jsonl(
            arguments.competencies.resolve()
        )

        candidate_sets = retrieve_candidates(
            fragments=fragments,
            competencies=competencies,
            top_k=arguments.top_k,
        )

        validation = validate_candidate_sets(
            fragments=fragments,
            competencies=competencies,
            candidate_sets=candidate_sets,
            top_k=arguments.top_k,
        )

        output_path = write_jsonl(
            candidate_sets,
            arguments.output.resolve(),
        )

        manifest_path = arguments.manifest.resolve()
        manifest_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest = {
            "input_files": {
                "fragments": str(
                    arguments.fragments.resolve()
                ),
                "competencies": str(
                    arguments.competencies.resolve()
                ),
            },
            "output_file": str(output_path),
            "retrieval_method": "BM25Okapi",
            "retrieval_version": "1.0",
            "configuration": {
                "top_k": arguments.top_k,
            },
            "validation": validation,
        }

        manifest_path.write_text(
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
        TypeError,
        ValueError,
    ) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    print("=== BM25 CANDIDATE RETRIEVAL ===")
    print(
        f"Source fragments: "
        f"{validation['source_fragments']}"
    )
    print(
        f"Competencies: "
        f"{validation['competency_corpus_size']}"
    )
    print(
        f"Candidate sets: "
        f"{validation['candidate_sets']}"
    )
    print(
        f"Top-K: "
        f"{validation['configured_top_k']}"
    )

    counts = validation[
        "candidate_count_statistics"
    ]

    print("\nCandidates per fragment:")
    print(f"- Minimum: {counts['minimum']}")
    print(f"- Maximum: {counts['maximum']}")
    print(f"- Average: {counts['average']}")

    scores = validation[
        "top_score_statistics"
    ]

    print("\nTop-score statistics:")
    print(f"- Minimum: {scores['minimum']}")
    print(f"- Maximum: {scores['maximum']}")
    print(f"- Average: {scores['average']}")

    print(
        "\nFragments with all Top-K scores equal to zero: "
        f"{len(validation['all_scores_zero_fragments'])}"
    )
    print(
        "Missing fragments: "
        f"{len(validation['missing_fragments'])}"
    )
    print(
        "Invalid candidate counts: "
        f"{len(validation['invalid_candidate_counts'])}"
    )
    print(
        "Invalid ranks: "
        f"{len(validation['invalid_ranks'])}"
    )
    print(
        "Duplicate candidates: "
        f"{len(validation['duplicate_candidates'])}"
    )
    print(
        "Unknown competencies: "
        f"{len(validation['unknown_competencies'])}"
    )
    print(
        "Unsorted score lists: "
        f"{len(validation['unsorted_scores'])}"
    )

    print(f"\nDataset: {output_path}")
    print(f"Manifest: {manifest_path}")

    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
