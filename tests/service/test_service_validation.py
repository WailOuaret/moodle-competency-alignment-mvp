"""Request validation: the contract, the resource and the competency catalogue."""

from __future__ import annotations

import copy

import pytest

from service_support import AUTH, CATALOGUE, build_payload, with_resource


def post(client, payload, headers=AUTH):
    return client.post("/v1/analyses", json=payload, headers=headers)


def error_of(http_response) -> dict:
    return http_response.json()["error"]


def catalogue_with(index: int, **changes) -> dict:
    payload = build_payload()
    payload["competencies"][index].update(changes)
    return payload


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #


def test_unknown_fields_are_rejected(client) -> None:
    payload = build_payload()
    payload["resource"]["student_name"] = "Not Allowed"

    result = post(client, payload)

    assert result.status_code == 422
    assert error_of(result)["code"] == "invalid_request"
    assert "resource.student_name" in {d["loc"] for d in error_of(result)["details"]}
    assert "Not Allowed" not in result.text


def test_missing_required_fields_are_located(client) -> None:
    payload = build_payload()
    del payload["resource"]["title"]

    result = post(client, payload)

    assert result.status_code == 422
    assert "resource.title" in {d["loc"] for d in error_of(result)["details"]}


def test_validation_errors_never_echo_submitted_values(client) -> None:
    payload = with_resource(
        resource_id="bad id with whitespace SUBMITTED-MARKER",
        text="SUBMITTED-MARKER resource content",
    )

    result = post(client, payload)

    assert result.status_code == 422
    assert "SUBMITTED-MARKER" not in result.text


def test_malformed_json_is_reported_after_authentication(client) -> None:
    result = client.post(
        "/v1/analyses",
        content=b"{not json",
        headers={**AUTH, "Content-Type": "application/json"},
    )

    assert result.status_code == 422
    assert error_of(result)["code"] == "invalid_request"


def test_unsupported_schema_version(client) -> None:
    payload = build_payload(schema_version="2.0")

    result = post(client, payload)

    assert result.status_code == 422
    assert error_of(result)["code"] == "unsupported_schema_version"


@pytest.mark.parametrize("resource_type", ["quiz_question", "assignment", "pdf", "transcript"])
def test_adapter_resource_types_use_the_same_analysis(client, resource_type: str) -> None:
    result = post(client, with_resource(resource_type=resource_type))

    assert result.status_code == 200
    assert result.json()["status"] == "completed"


@pytest.mark.parametrize("resource_type", ["scorm", "h5p", "forum_post"])
def test_undeclared_resource_types_are_refused(client, resource_type: str) -> None:
    result = post(client, with_resource(resource_type=resource_type))

    assert result.status_code == 422
    assert error_of(result)["code"] == "unsupported_resource_type"


def test_only_the_evaluated_top_k_is_accepted(client) -> None:
    refused = build_payload()
    refused["config"]["top_k"] = 10
    omitted = build_payload()
    del omitted["config"]["top_k"]
    no_config = build_payload()
    del no_config["config"]

    assert post(client, refused).status_code == 422
    assert error_of(post(client, refused))["code"] == "unsupported_config"
    assert post(client, omitted).status_code == 200
    assert post(client, no_config).status_code == 200


@pytest.mark.parametrize("value", [0, 11, -1])
def test_max_suggestions_is_bounded(client, value: int) -> None:
    payload = build_payload()
    payload["config"]["max_suggestions"] = value

    assert post(client, payload).status_code == 422


# --------------------------------------------------------------------------- #
# Resource
# --------------------------------------------------------------------------- #


def test_blank_text_is_refused(client) -> None:
    assert post(client, with_resource(text="   \n\n  ")).status_code == 422


def test_text_with_no_searchable_words_is_refused(client) -> None:
    result = post(client, with_resource(title="...", text="!!! ??? ---"))

    assert result.status_code == 422
    assert error_of(result)["code"] == "invalid_resource"


def test_resource_id_may_not_contain_whitespace(client) -> None:
    assert post(client, with_resource(resource_id="moodle page 42")).status_code == 422


def test_integer_identifiers_are_accepted_as_text(client) -> None:
    result = post(client, with_resource(course_id=5, course_module_id=91))

    assert result.status_code == 200


def test_boolean_identifier_is_refused(client) -> None:
    assert post(client, with_resource(course_id=True)).status_code == 422


def test_oversized_body_is_refused_before_parsing(make_client) -> None:
    client = make_client(max_body_bytes=1_000)

    result = post(client, with_resource(text="word " * 2_000))

    assert result.status_code == 413
    assert error_of(result)["code"] == "payload_too_large"


# --------------------------------------------------------------------------- #
# Competency catalogue
# --------------------------------------------------------------------------- #


def test_catalogue_must_not_be_empty(client) -> None:
    assert post(client, build_payload(competencies=[])).status_code == 422


def test_duplicate_idnumbers_are_refused(client) -> None:
    payload = build_payload()
    payload["competencies"].append(copy.deepcopy(CATALOGUE[0]))

    result = post(client, payload)

    assert result.status_code == 422
    assert error_of(result)["code"] == "invalid_competency_catalogue"
    assert "SE-1" in " ".join(d["message"] for d in error_of(result)["details"])


def test_competency_without_description_is_refused(client) -> None:
    result = post(client, catalogue_with(2, description_text="   "))

    assert result.status_code == 422


def test_competency_that_is_its_own_parent_is_refused(client) -> None:
    result = post(client, catalogue_with(0, parent_idnumber="SE-1"))

    assert result.status_code == 422
    assert error_of(result)["code"] == "invalid_competency_catalogue"


def test_parent_missing_from_the_catalogue_is_refused(client) -> None:
    result = post(client, catalogue_with(1, parent_idnumber="NO-SUCH-PARENT"))

    assert result.status_code == 422
    assert error_of(result)["code"] == "invalid_competency_catalogue"
    assert "NO-SUCH-PARENT" in " ".join(d["message"] for d in error_of(result)["details"])


def test_hierarchy_cycle_is_refused(client) -> None:
    payload = build_payload()
    payload["competencies"][0]["parent_idnumber"] = "SE-1.1"

    result = post(client, payload)

    assert result.status_code == 422
    assert "cycle" in " ".join(d["message"] for d in error_of(result)["details"]).lower()


def test_competencies_from_two_frameworks_are_not_combined(client) -> None:
    result = post(client, catalogue_with(3, framework_idnumber="OTHER-FRAMEWORK"))

    assert result.status_code == 422
    assert error_of(result)["code"] == "invalid_competency_catalogue"
    assert "framework" in " ".join(d["message"] for d in error_of(result)["details"]).lower()


def test_catalogue_errors_name_the_competency_without_echoing_text(client) -> None:
    payload = catalogue_with(2, description_text="   ")
    payload["competencies"][0]["description_text"] = "CATALOGUE-MARKER-TEXT"
    payload["competencies"][1]["parent_idnumber"] = "NO-SUCH-PARENT"

    result = post(client, payload)

    assert result.status_code == 422
    assert "CATALOGUE-MARKER-TEXT" not in result.text
