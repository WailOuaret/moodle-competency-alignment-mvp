"""The service must feed the engine exactly what the frozen pipeline fed it.

These tests read the frozen experiment files. They never write to them. If the
adapter ever changed how a catalogue or a Page is prepared, retrieval would
change silently, so the derived records are compared with the frozen ones.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from moodle_competency.retrieval import retrieve_candidates
from moodle_competency.runtime_analysis import fragment_runtime_resource
from moodle_competency.settings import PROJECT_ROOT

from service.alignment_adapter import prepare_catalogue, prepare_resource
from service.schemas import CompetencyIn, ResourceIn


DATA = Path(PROJECT_ROOT) / "data"

pytestmark = [
    pytest.mark.frozen_data,
    pytest.mark.skipif(
        not (DATA / "processed" / "competencies.jsonl").exists()
        or not (DATA / "interim" / "bm25_candidates.jsonl").exists(),
        reason="frozen experimental files are absent",
    ),
]

DERIVED_FIELDS = (
    "shortname",
    "description_text",
    "parent_idnumber",
    "parent_shortname",
    "depth",
    "hierarchy_idnumbers",
    "hierarchy_labels",
    "full_text",
    "search_text",
    "framework_idnumber",
    "framework_shortname",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def frozen_competencies() -> list[dict[str, Any]]:
    return read_jsonl(DATA / "processed" / "competencies.jsonl")


@pytest.fixture(scope="module")
def prepared(frozen_competencies):
    """The frozen catalogue as Moodle would send it: flat, without hierarchy."""

    flat = [
        CompetencyIn(
            idnumber=item["idnumber"],
            shortname=item["shortname"],
            description_text=item["description_text"],
            parent_idnumber=item["parent_idnumber"] or None,
            framework_idnumber=item["framework_idnumber"],
            framework_shortname=item["framework_shortname"],
        )
        for item in frozen_competencies
    ]
    return prepare_catalogue(flat)


def test_flat_catalogue_is_enriched_into_the_frozen_records(
    frozen_competencies,
    prepared,
) -> None:
    mine = {item["idnumber"]: item for item in prepared.records}

    assert set(mine) == {item["idnumber"] for item in frozen_competencies}

    for frozen in frozen_competencies:
        for field in DERIVED_FIELDS:
            assert mine[frozen["idnumber"]][field] == frozen[field], (
                frozen["idnumber"],
                field,
            )


def frozen_page_resource(record: dict[str, Any]) -> ResourceIn:
    return ResourceIn(
        resource_id=record["resource_id"],
        resource_type="page",
        course_id=record["course_id"],
        course_module_id=record["course_module_id"],
        title=record["title"],
        text=record["text"],
        search_text=record["search_text"],
        course_shortname=record["course_shortname"],
        course_fullname=record["course_fullname"],
        section_name=record["section_name"],
        activity_name=record["activity_name"],
    )


@pytest.fixture(scope="module")
def frozen_pages() -> list[dict[str, Any]]:
    resources = read_jsonl(DATA / "processed" / "resources.jsonl")
    return [item for item in resources if item["resource_type"] == "page"]


def test_page_fragments_match_the_frozen_fragments(frozen_pages) -> None:
    frozen_fragments = read_jsonl(DATA / "processed" / "fragments.jsonl")

    assert frozen_pages

    for page in frozen_pages:
        fragments = fragment_runtime_resource(
            prepare_resource(frozen_page_resource(page))
        )
        expected = [
            (item["fragment_id"], item["text"])
            for item in frozen_fragments
            if item["resource_id"] == page["resource_id"]
        ]

        assert [(item["fragment_id"], item["text"]) for item in fragments] == expected


def test_bm25_candidates_match_the_frozen_candidates(frozen_pages, prepared) -> None:
    frozen_sets = {
        item["fragment_id"]: item
        for item in read_jsonl(DATA / "interim" / "bm25_candidates.jsonl")
    }
    compared = 0

    for page in frozen_pages:
        fragments = fragment_runtime_resource(
            prepare_resource(frozen_page_resource(page))
        )
        candidate_sets = retrieve_candidates(
            fragments=fragments,
            competencies=prepared.records,
            top_k=5,
        )

        for candidate_set in candidate_sets:
            frozen = frozen_sets[candidate_set["fragment_id"]]

            assert [
                (c["rank"], c["idnumber"], c["bm25_score"])
                for c in candidate_set["candidates"]
            ] == [
                (c["rank"], c["idnumber"], c["bm25_score"])
                for c in frozen["candidates"]
            ], candidate_set["fragment_id"]
            assert candidate_set["all_scores_zero"] == frozen["all_scores_zero"]
            compared += 1

    assert compared >= 2
