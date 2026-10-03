"""The service tests must stay offline, and importing the service must be inert."""

from __future__ import annotations

import logging
import socket

import pytest

from service.config import Settings
from service_support import TOKEN


def test_network_connections_are_blocked_during_service_tests() -> None:
    with pytest.raises(AssertionError, match="network access is not allowed"):
        socket.create_connection(("127.0.0.1", 9), timeout=0.1)


def test_importing_the_module_does_not_create_the_application() -> None:
    import service.main as main

    assert "app" not in vars(main)


def test_app_is_created_on_first_access_and_then_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import service.main as main

    loads: list[int] = []

    def fake_load_settings() -> Settings:
        loads.append(1)
        return Settings(service_token=TOKEN, backend="mock")

    monkeypatch.setattr(main, "_application", None)
    monkeypatch.setattr(main, "load_settings", fake_load_settings)

    first = main.app

    assert main.app is first
    assert loads == [1]


def test_creating_applications_adds_one_log_handler_not_one_per_app(
    make_client,
) -> None:
    make_client()
    make_client()

    assert len(logging.getLogger("service").handlers) == 1


def test_unknown_module_attribute_still_raises() -> None:
    import service.main as main

    with pytest.raises(AttributeError):
        main.not_an_attribute  # noqa: B018
