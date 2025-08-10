from __future__ import annotations
from typing import Any
import pytest

import file_keeper.default.adapters.null as null


Settings = null.Settings
Storage = null.NullStorage


@pytest.fixture
def storage(storage_settings: dict[str, Any]):
    settings = {}
    settings.update(storage_settings)

    return Storage(settings)
