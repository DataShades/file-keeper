from __future__ import annotations

from typing import Any, cast
import file_keeper as fk
import pytest


@pytest.fixture
def storage_settings(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Collect storage settings from test markers."""
    settings: dict[str, Any] = {}
    marks = cast(Any, request.node.iter_markers("fk_storage_option"))
    for mark in marks:
        settings[mark.args[0]] = mark.args[1]

    return settings


@pytest.fixture
def expect_storage_capability(request: pytest.FixtureRequest, storage: fk.Storage):
    for mark in request.node.iter_markers("expect_storage_capability"):  # pyright: ignore[reportUnknownVariableType]
        for capability in mark.args:  # pyright: ignore[reportUnknownVariableType]
            if not storage.supports(capability):
                pytest.skip(f"Storage {storage} does not support capability {capability}")
