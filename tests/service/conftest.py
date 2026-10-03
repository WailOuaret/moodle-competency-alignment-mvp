"""Fixtures for the service tests. No network access, no live model."""

from __future__ import annotations

import socket
from typing import Any, Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from moodle_competency.runtime_analysis import MockAlignmentBackend

from service.config import Settings
from service.main import create_app
from service_support import TOKEN


@pytest.fixture(autouse=True)
def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that tries to open a network connection.

    The TestClient talks to the app in-process, so a connection can only come
    from a code path that would reach a real model or host.
    """

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("network access is not allowed in service tests")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


@pytest.fixture
def make_client() -> Iterator[Callable[..., TestClient]]:
    """Build a client around an app with an injected backend or handler.

    ``raise_server_exceptions`` is off so a 500 can be asserted on instead of
    being re-raised into the test.
    """

    clients: list[TestClient] = []

    def factory(
        handler: Callable[..., Any] | None = None,
        *,
        backend: Any | None = None,
        **settings_changes: Any,
    ) -> TestClient:
        settings_changes.setdefault("service_token", TOKEN)
        settings = Settings(backend="mock", **settings_changes)
        backend_factory = None

        if backend is not None:
            backend_factory = lambda _settings: backend  # noqa: E731
        elif handler is not None:
            backend_factory = (  # noqa: E731
                lambda _settings: MockAlignmentBackend(handler)
            )

        client = TestClient(
            create_app(settings, backend_factory=backend_factory),
            raise_server_exceptions=False,
        )
        clients.append(client)
        return client

    yield factory

    for client in clients:
        client.close()


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    """A client using the default deterministic mock backend."""

    return make_client()
