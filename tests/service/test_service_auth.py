"""Bearer-token authentication of the analysis endpoint."""

from __future__ import annotations

import pytest

from service_support import AUTH, TOKEN, build_payload


def post(client, headers=None, **kwargs):
    return client.post(
        "/v1/analyses",
        json=build_payload(),
        headers=headers,
        **kwargs,
    )


def test_missing_credentials_are_rejected(client) -> None:
    response = post(client)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_missing"
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    [
        "Bearer an-entirely-wrong-token-value",
        f"Bearer {TOKEN}x",
        f"Bearer {TOKEN[:-1]}",
        "Basic dXNlcjpwYXNzd29yZA==",
        "Token " + TOKEN,
        "Bearer",
        "Bearer    ",
    ],
)
def test_invalid_credentials_are_rejected(client, header: str) -> None:
    response = post(client, headers={"Authorization": header})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_invalid"
    assert response.headers["www-authenticate"] == "Bearer"


def test_valid_token_is_accepted(client) -> None:
    assert post(client, headers=AUTH).status_code == 200


def test_scheme_is_case_insensitive(client) -> None:
    response = post(client, headers={"Authorization": f"bearer {TOKEN}"})

    assert response.status_code == 200


def test_authentication_comes_before_body_parsing(client) -> None:
    response = client.post(
        "/v1/analyses",
        content=b"{this is not json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401


def test_unconfigured_service_fails_closed(make_client) -> None:
    response = post(make_client(service_token=None), headers=AUTH)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_not_configured"


def test_token_is_compared_in_constant_time(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    import service.auth as auth_module

    calls: list[tuple[int, int]] = []
    original = auth_module.hmac.compare_digest

    def spy(left, right):
        calls.append((len(left), len(right)))
        return original(left, right)

    monkeypatch.setattr(auth_module.hmac, "compare_digest", spy)
    post(client, headers={"Authorization": "Bearer short"})
    post(client, headers=AUTH)

    # Both calls compare fixed-length digests, so length does not leak.
    assert calls == [(32, 32), (32, 32)]


def test_rejection_never_echoes_the_submitted_credentials(client) -> None:
    response = post(
        client,
        headers={"Authorization": "Bearer submitted-credential-marker"},
    )

    assert "submitted-credential-marker" not in response.text
    assert TOKEN not in response.text
