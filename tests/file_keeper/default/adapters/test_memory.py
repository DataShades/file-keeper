from __future__ import annotations

from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.memory as memory

from . import standard

Settings = memory.Settings
Storage = memory.MemoryStorage


@pytest.fixture
def storage(storage_settings: dict[str, Any]):
    settings = {"name": "test"}
    settings.update(storage_settings)

    return Storage(settings)


class TestUploaderMultipart(standard.MultiparterWithUploaded):
    def test_refresh(self, faker: Faker, storage: memory.MemoryStorage):
        """`multipart_refresh` synchronized filesize."""
        content = faker.binary(10)
        data = storage.multipart_start(
            fk.FileData(fk.Location(faker.file_name()), size=len(content)),
        )

        storage.settings.bucket[data.location] = content

        data = storage.multipart_refresh(data)
        assert data.storage_data["uploaded"] == len(content)


class TestStorage(standard.Standard): ...
