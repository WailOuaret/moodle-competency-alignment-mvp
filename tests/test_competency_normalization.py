"""Tests for competency-framework normalization."""

from moodle_competency.competency_normalization import (
    normalize_competencies,
    normalize_frameworks,
    validate_competencies,
)


def test_normalize_competency_hierarchy() -> None:
    frameworks = normalize_frameworks(
        [
            {
                "id": "5",
                "idnumber": "TEST_FRAMEWORK",
                "shortname": "Test Framework",
            }
        ]
    )

    competencies = normalize_competencies(
        competency_rows=[
            {
                "id": "10",
                "competencyframeworkid": "5",
                "parentid": "0",
                "idnumber": "C1",
                "shortname": "Software Design",
                "description": (
                    "<p>Design software systems.</p>"
                ),
                "sortorder": "1",
            },
            {
                "id": "11",
                "competencyframeworkid": "5",
                "parentid": "10",
                "idnumber": "C1_1",
                "shortname": "Architecture",
                "description": (
                    "<p>Choose an architecture.</p>"
                ),
                "sortorder": "2",
            },
        ],
        frameworks=frameworks,
    )

    child = next(
        record
        for record in competencies
        if record["idnumber"] == "C1_1"
    )

    assert child["parent_competency_id"] == 10
    assert child["parent_idnumber"] == "C1"
    assert child["depth"] == 1
    assert child["hierarchy_idnumbers"] == [
        "C1",
        "C1_1",
    ]
    assert "Software Design" in child["search_text"]
    assert "Choose an architecture" in child[
        "description_text"
    ]

    validation = validate_competencies(
        competencies,
        expected_count=2,
        expected_idnumbers={"C1", "C1_1"},
    )

    assert validation["passed"] is True


def test_duplicate_idnumber_is_rejected() -> None:
    frameworks = normalize_frameworks(
        [
            {
                "id": "5",
                "idnumber": "TEST_FRAMEWORK",
                "shortname": "Test Framework",
            }
        ]
    )

    competencies = normalize_competencies(
        competency_rows=[
            {
                "id": "10",
                "competencyframeworkid": "5",
                "parentid": "0",
                "idnumber": "C1",
                "shortname": "First",
                "description": "First description",
            },
            {
                "id": "11",
                "competencyframeworkid": "5",
                "parentid": "0",
                "idnumber": "C1",
                "shortname": "Second",
                "description": "Second description",
            },
        ],
        frameworks=frameworks,
    )

    validation = validate_competencies(
        competencies
    )

    assert validation["passed"] is False
    assert validation["duplicate_idnumbers"] == [
        "C1"
    ]
