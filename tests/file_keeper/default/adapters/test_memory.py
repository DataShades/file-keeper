from __future__ import annotations

from typing import Any

import pytest
from faker import Faker

import file_keeper.default.adapters.memory as memory

from . import standard

Settings = memory.Settings
Storage = memory.MemoryStorage


@pytest.fixture
def storage(faker: Faker, storage_settings: dict[str, Any]):
    settings = {
        "name": "test",
        "path": faker.file_path(extension=[]),
    }
    settings.update(storage_settings)

    return Storage(settings)


class TestStorage(standard.Standard): ...
