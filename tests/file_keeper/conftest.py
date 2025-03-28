from __future__ import annotations

from typing import Any, cast

import pytest


@pytest.fixture()
def storage_settings(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Collect storage settings from test markers."""
    settings: dict[str, Any] = {}
    marks = cast(Any, request.node.iter_markers("fk_storage_option"))
    for mark in marks:
        settings[mark.args[0]] = mark.args[1]

    return settings
