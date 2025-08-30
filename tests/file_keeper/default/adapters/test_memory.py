from __future__ import annotations

from typing import Any

import pytest

import file_keeper.default.adapters.memory as memory

from . import standard

Settings = memory.Settings
Storage = memory.MemoryStorage


@pytest.fixture
def storage(storage_settings: dict[str, Any]):
    settings = {"name": "test"}
    settings.update(storage_settings)

    return Storage(settings)


class TestStorage(standard.Standard): ...
