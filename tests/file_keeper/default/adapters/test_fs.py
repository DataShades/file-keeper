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
    def test_creation(self, tmp_path: Path):
        """Test how settings initialized with and without required option."""
        with pytest.raises(fk.exc.MissingStorageConfigurationError):
            Settings()

        Settings(path=str(tmp_path))


class TestUploaderUpload(standard.Uploader):
    pass


class TestUploaderMultipart(standard.Multiparter, standard.MultiparterWithUploaded):
    def test_refresh(self, faker: Faker, storage: fs.FsStorage):
        """`multipart_refresh` synchronized filesize."""
        content = faker.binary(10)
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(size=len(content)),
        )
        with open(os.path.join(storage.settings.path, data.location), "wb") as dest:
            dest.write(content)

        data = storage.multipart_refresh(data)
        assert data.storage_data["uploaded"] == len(content)

    def test_update_with_position(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` can override existing parts."""
        content = b"hello world"
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(size=len(content)),
        )

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


class TestStorage:
    def test_missing_path(self, tmp_path: Path, faker: Faker):
        path = faker.file_path(absolute=False, extension="")

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            fs.FsStorage(
                {"path": os.path.join(tmp_path, path)},
            )

    def test_missing_path_created(self, tmp_path: Path, faker: Faker):
        subpath = faker.file_path(absolute=False, extension="")
        path = os.path.join(tmp_path, subpath)

        fs.FsStorage({"path": path, "create_path": True})
        assert os.path.exists(path)
