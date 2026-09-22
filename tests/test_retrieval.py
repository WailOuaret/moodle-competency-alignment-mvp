"""Tests for BM25 competency candidate retrieval."""

from moodle_competency.retrieval import (
    BM25CompetencyRetriever,
    retrieve_candidates,
    tokenize,
    validate_candidate_sets,
)


COMPETENCIES = [
    {
        "competency_id": 1,
        "idnumber": "C1",
        "shortname": "Software architecture",
        "description_text": (
            "Design modular software architecture "
            "and distributed systems."
        ),
        "search_text": (
            "Software architecture distributed systems"
        ),
        "depth": 1,
    },
    {
        "competency_id": 2,
        "idnumber": "C2",
        "shortname": "Database design",
        "description_text": (
            "Design relational databases using "
            "normalization and SQL."
        ),
        "search_text": (
            "Database design relational SQL normalization"
        ),
        "depth": 1,
    },
    {
        "competency_id": 3,
        "idnumber": "C3",
        "shortname": "Machine learning",
        "description_text": (
            "Build and evaluate machine-learning models."
        ),
        "search_text": (
            "Machine learning model evaluation"
        ),
        "depth": 1,
    },
]


def test_tokenize_normalizes_case() -> None:
    assert tokenize(
        "SQL Database-Design"
    ) == [
        "sql",
        "database-design",
    ]


def test_database_fragment_ranks_database_first() -> None:
    retriever = BM25CompetencyRetriever(
        COMPETENCIES
    )

    result = retriever.retrieve(
        {
            "fragment_id": "page:1#f001",
            "resource_id": "page:1",
            "title": "Database normalization",
            "text": (
                "Use SQL keys and normalization "
                "to design a relational database."
            ),
            "search_text": (
                "Database normalization SQL relational keys"
            ),
        },
        top_k=3,
    )

    assert len(result["candidates"]) == 3
    assert (
        result["candidates"][0]["idnumber"]
        == "C2"
    )
    assert result["candidates"][0]["rank"] == 1


def test_candidate_validation_passes() -> None:
    fragments = [
        {
            "fragment_id": "page:1#f001",
            "resource_id": "page:1",
            "title": "Database design",
            "text": "Use SQL and normalization.",
            "search_text": (
                "Database design SQL normalization"
            ),
        },
        {
            "fragment_id": "page:2#f001",
            "resource_id": "page:2",
            "title": "Architecture",
            "text": (
                "Design a distributed modular system."
            ),
            "search_text": (
                "Software architecture distributed modular"
            ),
        },
    ]

    candidate_sets = retrieve_candidates(
        fragments=fragments,
        competencies=COMPETENCIES,
        top_k=2,
    )

    validation = validate_candidate_sets(
        fragments=fragments,
        competencies=COMPETENCIES,
        candidate_sets=candidate_sets,
        top_k=2,
    )

    assert validation["passed"] is True
    assert validation["candidate_sets"] == 2
    assert (
        validation[
            "expected_candidates_per_fragment"
        ]
        == 2
    )
