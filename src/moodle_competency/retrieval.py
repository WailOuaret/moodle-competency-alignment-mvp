"""BM25 candidate retrieval for Moodle competency alignment."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

from rank_bm25 import BM25Okapi


TOKEN_PATTERN = re.compile(
    r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[_'-][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)*",
    flags=re.UNICODE,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load objects from a UTF-8 JSON Lines file."""

    if not path.exists():
        raise FileNotFoundError(
            f"JSONL file does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}."
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Line {line_number} of {path} is not a JSON object."
                )

            records.append(record)

    return records


def tokenize(text: str | None) -> list[str]:
    """Tokenize text for the small English/French competency corpus."""

    if text is None:
        return []

    return [
        token.casefold()
        for token in TOKEN_PATTERN.findall(str(text))
    ]


def build_competency_document(
    competency: Mapping[str, Any],
) -> str:
    """Return the searchable competency profile."""

    fields = [
        competency.get("framework_shortname", ""),
        competency.get("parent_shortname", ""),
        competency.get("idnumber", ""),
        competency.get("shortname", ""),
        competency.get("description_text", ""),
        competency.get("search_text", ""),
    ]

    unique_parts: list[str] = []
    seen: set[str] = set()

    for field in fields:
        value = str(field or "").strip()

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        unique_parts.append(value)

    return "\n".join(unique_parts)


def build_fragment_query(
    fragment: Mapping[str, Any],
) -> str:
    """Return the text used as the BM25 query."""

    fields = [
        fragment.get("course_fullname", ""),
        fragment.get("section_name", ""),
        fragment.get("activity_name", ""),
        fragment.get("title", ""),
        fragment.get("search_text", ""),
        fragment.get("text", ""),
    ]

    unique_parts: list[str] = []
    seen: set[str] = set()

    for field in fields:
        value = str(field or "").strip()

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        unique_parts.append(value)

    return "\n".join(unique_parts)


class BM25CompetencyRetriever:
    """Retrieve ranked competency candidates for text fragments."""

    def __init__(
        self,
        competencies: Sequence[Mapping[str, Any]],
    ) -> None:
        if not competencies:
            raise ValueError(
                "At least one competency is required."
            )

        self.competencies = [
            dict(competency)
            for competency in competencies
        ]

        self.documents = [
            build_competency_document(competency)
            for competency in self.competencies
        ]

        self.tokenized_documents = [
            tokenize(document)
            for document in self.documents
        ]

        empty_documents = [
            self.competencies[index].get("idnumber")
            for index, tokens in enumerate(
                self.tokenized_documents
            )
            if not tokens
        ]

        if empty_documents:
            raise ValueError(
                "Competencies contain empty retrieval profiles: "
                + ", ".join(map(str, empty_documents))
            )

        self.index = BM25Okapi(
            self.tokenized_documents
        )

    def retrieve(
        self,
        fragment: Mapping[str, Any],
        *,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Retrieve the top-k competencies for one fragment."""

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        query_text = build_fragment_query(fragment)
        query_tokens = tokenize(query_text)

        if not query_tokens:
            raise ValueError(
                "Fragment has no usable BM25 query tokens: "
                f"{fragment.get('fragment_id')}"
            )

        raw_scores = self.index.get_scores(
            query_tokens
        )

        ranked_indexes = sorted(
            range(len(self.competencies)),
            key=lambda index: (
                -float(raw_scores[index]),
                str(
                    self.competencies[index].get(
                        "idnumber",
                        "",
                    )
                ),
            ),
        )[: min(top_k, len(self.competencies))]

        candidates: list[dict[str, Any]] = []

        for rank, index in enumerate(
            ranked_indexes,
            start=1,
        ):
            competency = self.competencies[index]
            score = float(raw_scores[index])

            candidates.append(
                {
                    "rank": rank,
                    "competency_id":
                        competency.get(
                            "competency_id"
                        ),
                    "idnumber":
                        competency.get(
                            "idnumber",
                            "",
                        ),
                    "shortname":
                        competency.get(
                            "shortname",
                            "",
                        ),
                    "parent_competency_id":
                        competency.get(
                            "parent_competency_id"
                        ),
                    "parent_idnumber":
                        competency.get(
                            "parent_idnumber",
                            "",
                        ),
                    "depth":
                        competency.get(
                            "depth"
                        ),
                    "bm25_score": round(
                        score,
                        8,
                    ),
                }
            )

        top_score = (
            candidates[0]["bm25_score"]
            if candidates
            else 0.0
        )

        return {
            "fragment_id": fragment.get(
                "fragment_id"
            ),
            "resource_id": fragment.get(
                "resource_id"
            ),
            "resource_type": fragment.get(
                "resource_type"
            ),
            "fragment_type": fragment.get(
                "fragment_type"
            ),
            "course_id": fragment.get(
                "course_id"
            ),
            "course_shortname": fragment.get(
                "course_shortname",
                "",
            ),
            "course_module_id": fragment.get(
                "course_module_id"
            ),
            "activity_id": fragment.get(
                "activity_id"
            ),
            "activity_name": fragment.get(
                "activity_name",
                "",
            ),
            "title": fragment.get(
                "title",
                "",
            ),
            "fragment_text": fragment.get(
                "text",
                "",
            ),
            "query_text": query_text,
            "query_token_count": len(
                query_tokens
            ),
            "candidate_count": len(
                candidates
            ),
            "top_bm25_score": top_score,
            "all_scores_zero": all(
                candidate["bm25_score"] == 0
                for candidate in candidates
            ),
            "candidates": candidates,
            "retrieval_method": "bm25_okapi",
            "retrieval_version": "1.0",
        }


def retrieve_candidates(
    *,
    fragments: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve candidates for all fragments."""

    retriever = BM25CompetencyRetriever(
        competencies
    )

    return [
        retriever.retrieve(
            fragment,
            top_k=top_k,
        )
        for fragment in fragments
    ]


def validate_candidate_sets(
    *,
    fragments: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
    candidate_sets: Sequence[Mapping[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    """Validate BM25 output structure and ranking consistency."""

    expected_candidate_count = min(
        top_k,
        len(competencies),
    )

    fragment_ids = {
        str(fragment.get("fragment_id", "")).strip()
        for fragment in fragments
        if str(
            fragment.get("fragment_id", "")
        ).strip()
    }

    candidate_fragment_ids = [
        str(
            candidate_set.get(
                "fragment_id",
                "",
            )
        ).strip()
        for candidate_set in candidate_sets
    ]

    candidate_fragment_id_set = {
        fragment_id
        for fragment_id in candidate_fragment_ids
        if fragment_id
    }

    valid_competency_idnumbers = {
        str(
            competency.get(
                "idnumber",
                "",
            )
        ).strip()
        for competency in competencies
        if str(
            competency.get(
                "idnumber",
                "",
            )
        ).strip()
    }

    duplicate_fragment_ids = sorted(
        fragment_id
        for fragment_id, count in Counter(
            candidate_fragment_ids
        ).items()
        if fragment_id and count > 1
    )

    missing_fragments = sorted(
        fragment_ids
        - candidate_fragment_id_set
    )

    unknown_fragments = sorted(
        candidate_fragment_id_set
        - fragment_ids
    )

    invalid_candidate_counts: list[str] = []
    invalid_ranks: list[str] = []
    duplicate_candidates: list[str] = []
    unknown_competencies: list[str] = []
    invalid_scores: list[str] = []
    unsorted_scores: list[str] = []

    zero_score_fragment_ids: list[str] = []
    top_scores: list[float] = []

    for candidate_set in candidate_sets:
        fragment_id = str(
            candidate_set.get(
                "fragment_id",
                "",
            )
        )

        candidates = list(
            candidate_set.get(
                "candidates",
                []
            )
        )

        if len(candidates) != expected_candidate_count:
            invalid_candidate_counts.append(
                fragment_id
            )

        ranks = [
            candidate.get("rank")
            for candidate in candidates
        ]

        if ranks != list(
            range(1, len(candidates) + 1)
        ):
            invalid_ranks.append(
                fragment_id
            )

        idnumbers = [
            str(
                candidate.get(
                    "idnumber",
                    "",
                )
            ).strip()
            for candidate in candidates
        ]

        if len(idnumbers) != len(set(idnumbers)):
            duplicate_candidates.append(
                fragment_id
            )

        for idnumber in idnumbers:
            if (
                idnumber
                not in valid_competency_idnumbers
            ):
                unknown_competencies.append(
                    f"{fragment_id}:{idnumber}"
                )

        scores: list[float] = []

        for candidate in candidates:
            score = candidate.get(
                "bm25_score"
            )

            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                invalid_scores.append(
                    fragment_id
                )
                continue

            if not math.isfinite(
                numeric_score
            ):
                invalid_scores.append(
                    fragment_id
                )

            scores.append(
                numeric_score
            )

        if any(
            scores[index] < scores[index + 1]
            for index in range(
                len(scores) - 1
            )
        ):
            unsorted_scores.append(
                fragment_id
            )

        if scores:
            top_scores.append(scores[0])

        if candidates and all(
            float(
                candidate.get(
                    "bm25_score",
                    0,
                )
            )
            == 0
            for candidate in candidates
        ):
            zero_score_fragment_ids.append(
                fragment_id
            )

    candidate_counts = [
        int(
            candidate_set.get(
                "candidate_count",
                0,
            )
        )
        for candidate_set in candidate_sets
    ]

    passed = (
        len(candidate_sets) == len(fragments)
        and not duplicate_fragment_ids
        and not missing_fragments
        and not unknown_fragments
        and not invalid_candidate_counts
        and not invalid_ranks
        and not duplicate_candidates
        and not unknown_competencies
        and not invalid_scores
        and not unsorted_scores
    )

    return {
        "source_fragments":
            len(fragments),
        "competency_corpus_size":
            len(competencies),
        "candidate_sets":
            len(candidate_sets),
        "configured_top_k":
            top_k,
        "expected_candidates_per_fragment":
            expected_candidate_count,
        "candidate_count_statistics": {
            "minimum": (
                min(candidate_counts)
                if candidate_counts
                else 0
            ),
            "maximum": (
                max(candidate_counts)
                if candidate_counts
                else 0
            ),
            "average": (
                round(
                    mean(candidate_counts),
                    3,
                )
                if candidate_counts
                else 0
            ),
        },
        "top_score_statistics": {
            "minimum": (
                round(min(top_scores), 8)
                if top_scores
                else 0
            ),
            "maximum": (
                round(max(top_scores), 8)
                if top_scores
                else 0
            ),
            "average": (
                round(mean(top_scores), 8)
                if top_scores
                else 0
            ),
        },
        "all_scores_zero_fragments":
            zero_score_fragment_ids,
        "duplicate_fragment_ids":
            duplicate_fragment_ids,
        "missing_fragments":
            missing_fragments,
        "unknown_fragments":
            unknown_fragments,
        "invalid_candidate_counts":
            invalid_candidate_counts,
        "invalid_ranks":
            invalid_ranks,
        "duplicate_candidates":
            duplicate_candidates,
        "unknown_competencies":
            unknown_competencies,
        "invalid_scores":
            sorted(set(invalid_scores)),
        "unsorted_scores":
            unsorted_scores,
        "passed": passed,
    }


def write_jsonl(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
) -> Path:
    """Write records as UTF-8 JSON Lines."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(
                    dict(record),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    return output_path.resolve()
