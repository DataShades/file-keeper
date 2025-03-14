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


@pytest.fixture()
def storage(tmp_path: Path, request: pytest.FixtureRequest):
    settings = {"name": "test", "path": str(tmp_path)}
    marks: Any = request.node.iter_markers("fk_storage_option")
    for mark in marks:
        settings[mark.args[0]] = mark.args[1]

    return Storage(settings)


class TestSettings:
    def test_creation(self):
        """Test how settings initialized with and without required option."""
        with pytest.raises(fk.exc.MissingStorageConfigurationError):
            Settings()

        Settings(path="test")


class TestUploaderUpload(standard.Uploader):
    @pytest.mark.fk_storage_option("recursive", True)
    def test_sub_directory_allowed(self, storage: fk.Storage, faker: Faker):
        """Can upload into nested dirs when `recursive` enabled."""
        path = faker.file_path(absolute=False)
        result = storage.upload(path, fk.make_upload(b""))
        assert result.location == path

    def test_sub_directory_not_allowed(self, storage: fk.Storage, faker: Faker):
        """Cannot upload into nested dirs by default."""
        with pytest.raises(fk.exc.LocationError):
            storage.upload(faker.file_path(absolute=False), fk.make_upload(b""))

    @pytest.mark.fk_storage_option("recursive", True)
    def test_absolute_sub_path_sanitized(self, storage: fk.Storage, faker: Faker):
        """Cannot upload to absolute path."""
        path = faker.file_path(absolute=True)
        result = storage.upload(path, fk.make_upload(b""))
        assert result.location == path.lstrip("/")

    @pytest.mark.fk_storage_option("recursive", True)
    def test_parent_sub_path_sanitized(self, storage: fk.Storage, faker: Faker):
        """Cannot upload to parent dir."""
        path = faker.file_path(absolute=False)
        result = storage.upload(f"../../{path}", fk.make_upload(b""))
        assert result.location == path


class TestUploaderMultipart(standard.Multiparter, standard.MultiparterWithUploaded):
    def test_refresh(self, faker: Faker, storage: fs.FsStorage):
        """`multipart_refresh` synchronized filesize."""
        content = faker.binary(10)
        data = storage.multipart_start(
            faker.file_name(),
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
            faker.file_name(),
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
    @pytest.mark.fk_storage_option("supported_types", ["text"])
    def test_compose_with_wrong_final_type(self, storage: fs.FsStorage, faker: Faker):
        """If source files produce unsupported composed type, it is removed."""
        first = storage.upload(faker.file_name(), fk.make_upload(b'{"hello":'))
        second = storage.upload(faker.file_name(), fk.make_upload(b'"world"}'))

        location = faker.file_name()
        with pytest.raises(fk.exc.WrongUploadTypeError):
            storage.compose(location, storage, first, second)

        assert not os.path.exists(os.path.join(storage.settings.path, location))

    @pytest.mark.fk_storage_option("max_size", 10)
    def test_compose_with_immense_size(self, storage: fs.FsStorage, faker: Faker):
        """If source files produce too big result it is removed."""
        content = faker.binary(storage.settings.max_size - 1)
        first = storage.upload(faker.file_name(), fk.make_upload(content))
        second = storage.upload(faker.file_name(), fk.make_upload(content))

        location = faker.file_name()
        with pytest.raises(fk.exc.LargeUploadError):
            storage.compose(location, storage, first, second)

        assert not os.path.exists(os.path.join(storage.settings.path, location))


class TestManagerAppend(standard.Appender):
    @pytest.mark.fk_storage_option("supported_types", ["text"])
    def test_append_with_wrong_final_type(self, storage: fs.FsStorage, faker: Faker):
        """If source files produce unsupported composed type, it is removed."""
        data = storage.upload(faker.file_name(), fk.make_upload(b'{"hello":'))
        with pytest.raises(fk.exc.WrongUploadTypeError):
            storage.append(data, fk.make_upload(b'"world"}'))

        assert not os.path.exists(os.path.join(storage.settings.path, data.location))


class TestManagerCopy(standard.Copier):
    pass


class TestManagerMove(standard.Mover):
    pass


class TestManagerExists(standard.Exister):
    pass


class TestManagerRemove(standard.Remover):
    pass


class TestManagerScan(standard.Scanner):
    def test_scan(self, storage: fs.FsStorage, faker: Faker):
        first = storage.upload(faker.file_name(), fk.make_upload(b""))
        second = storage.upload(faker.file_name(), fk.make_upload(b""))

        relpath = faker.file_path(absolute=False)
        nested_path = os.path.join(storage.settings.path, relpath)
        os.makedirs(os.path.dirname(nested_path))
        with open(nested_path, "wb"):
            pass

        discovered = set(storage.scan())

        assert discovered == {first.location, second.location}

    @pytest.mark.fk_storage_option("recursive", True)
    def test_scan_recursive(self, storage: fs.FsStorage, faker: Faker):
        first = storage.upload(faker.file_name(), fk.make_upload(b""))
        second = storage.upload(faker.file_name(), fk.make_upload(b""))

        relpath = faker.file_path(absolute=False)
        nested_path = os.path.join(storage.settings.path, relpath)
        os.makedirs(os.path.dirname(nested_path))
        with open(nested_path, "wb"):
            pass

        discovered = set(storage.scan())

        assert discovered == {first.location, second.location, relpath}


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
