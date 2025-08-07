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


class TestUploaderUpload(standard.Uploader):
    pass


class TestUploaderMultipart(standard.Multiparter, standard.MultiparterWithUploaded):
    def test_refresh(self, faker: Faker, storage: memory.MemoryStorage):
        """`multipart_refresh` synchronized filesize."""
        content = faker.binary(10)
        data = storage.multipart_start(
            fk.FileData(fk.Location(faker.file_name()), size=len(content)),
        )

        storage.settings.bucket[data.location] = content

        data = storage.multipart_refresh(data)
        assert data.storage_data["uploaded"] == len(content)


class TestReader(standard.Reader):
    pass


class TestManagerCompose(standard.Composer):
    pass


class TestManagerAppend(standard.Appender):
    pass


class TestManagerCopy(standard.Copier):
    pass


class TestManagerMove(standard.Mover):
    pass


class TestManagerExists(standard.Exister):
    pass


class TestManagerRemove(standard.Remover):
    pass


class TestManagerScan(standard.Scanner):
    pass


class TestManagerAnalyze(standard.Analyzer):
    pass


class TestStorage: ...
