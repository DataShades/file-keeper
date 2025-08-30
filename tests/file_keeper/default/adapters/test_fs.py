from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.fs as fs

from . import standard

Settings = fs.Settings
Storage = fs.FsStorage


@pytest.fixture
def storage(tmp_path: Path, storage_settings: dict[str, Any]):
    settings = {"name": "test", "path": str(tmp_path)}
    settings.update(storage_settings)

    return Storage(settings)


class TestSettings:
    def test_initialize(self, storage: Storage, tmp_path: Path, faker: Faker):
        """Initialize flag controls path creation."""
        subpath = faker.file_path(absolute=False, extension="")
        path = os.path.join(tmp_path, subpath)

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            storage.SettingsFactory(path=path)

        storage.SettingsFactory(path=path, initialize=True)
        assert os.path.exists(path)

        # if path exists, settings do not require `initialize` flag
        storage.SettingsFactory(path=path)


@pytest.mark.xfail
class TestUploaderMultipart(standard.MultiparterWithUploaded):
    def test_refresh(self, faker: Faker, storage: fs.FsStorage):
        """`multipart_refresh` synchronized filesize."""
        content = faker.binary(10)
        data = storage.multipart_start(fk.types.Location(faker.file_name()), size=len(content))
        with open(os.path.join(storage.settings.path, data.location), "wb") as dest:
            dest.write(content)

        data = storage.multipart_refresh(data)
        assert data.storage_data["uploaded"] == len(content)

    def test_update_with_position(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` can override existing parts."""
        content = b"hello world"
        data = storage.multipart_start(fk.types.Location(faker.file_name()), size=len(content))

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(content),
        )

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(b"LLO W"),
            position=2,
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == len(content)

        assert storage.content(fk.FileData(data.location)) == b"heLLO World"


class TestStorage(standard.Standard): ...
