from __future__ import annotations

import hashlib
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.fs as fs


@pytest.fixture()
def storage(tmp_path: Path, request: pytest.FixtureRequest):
    settings = {"name": "test", "path": str(tmp_path)}
    marks: Any = request.node.iter_markers("fk_storage_option")
    for mark in marks:
        settings[mark.args[0]] = mark.args[1]

    return fs.FsStorage(settings)


class TestSettings:
    def test_creation(self):
        """Test how settings initialized with and without required option."""
        with pytest.raises(fk.exc.MissingStorageConfigurationError):
            fs.Settings()

        fs.Settings(path="test")


class TestUploader:
    def test_capabilities(self, storage: fk.Storage):
        assert storage.supports(fk.Capability.CREATE)
        assert storage.supports(fk.Capability.MULTIPART)

    def test_empty_upload(self, storage: fk.Storage, faker: Faker):
        """Empty file can be created."""
        filename = faker.file_name()
        result = storage.upload(filename, fk.make_upload(b""))

        assert result.size == 0

        filepath = os.path.join(storage.settings.path, result.location)
        assert os.path.exists(filepath)
        assert storage.content(result) == b""

    def test_content(self, storage: fk.Storage, faker: Faker):
        """Content matches the uploaded data"""
        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(BytesIO(content)))

        assert result.size == 100
        assert storage.content(result) == content

    def test_hash(self, storage: fk.Storage, faker: Faker):
        """Hash computed using full content."""
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert result.hash == hashlib.md5().hexdigest()

        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(BytesIO(content)))
        assert result.hash == hashlib.md5(content).hexdigest()

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


class TestMultipartUploader:
    def test_initialization_large(self, storage: fk.Storage, faker: Faker):
        storage.settings.max_size = 5
        with pytest.raises(fk.exc.LargeUploadError):
            storage.multipart_start(faker.file_name(), fk.MultipartData(size=10))

    def test_initialization(self, storage: fk.Storage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=len(content)),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 0

    def test_update(self, storage: fk.Storage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=len(content)),
        )

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(BytesIO(content[:5])),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 5

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(BytesIO(content[:5])),
            position=3,
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 8

        with pytest.raises(fk.exc.UploadOutOfBoundError):
            storage.multipart_update(data, upload=fk.make_upload(BytesIO(content)))

        missing_size = data.size - data.storage_data["uploaded"]
        data = storage.multipart_update(
            data,
            upload=fk.make_upload(BytesIO(content[-missing_size:])),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == len(content)

    def test_complete(self, storage: fk.Storage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(content_type="text/plain", size=len(content)),
        )

        with pytest.raises(fk.exc.UploadSizeMismatchError):
            storage.multipart_complete(data)

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(BytesIO(content)),
        )
        data = storage.multipart_complete(data)
        assert data.size == len(content)
        assert data.hash == hashlib.md5(content).hexdigest()

    def test_show(self, storage: fk.Storage, faker: Faker):
        content = b"hello world"

        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(content_type="text/plain", size=len(content)),
        )
        assert storage.multipart_refresh(data) == data

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(BytesIO(content)),
        )
        assert storage.multipart_refresh(data) == data

        storage.multipart_complete(data)
        assert storage.multipart_refresh(data) == data


class TestManager:
    def test_removal(self, storage: fk.Storage, faker: Faker):
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        filepath = os.path.join(storage.settings.path, result.location)
        assert os.path.exists(filepath)

        assert storage.remove(result)
        assert not os.path.exists(filepath)

    def test_removal_missing(self, storage: fk.Storage, faker: Faker):
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert storage.remove(result)
        assert not storage.remove(result)


class TestReader:
    def test_stream(self, storage: fk.Storage, faker: Faker):
        data = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(BytesIO(data)))

        stream = storage.stream(result)

        assert b"".join(stream) == data

    def test_content(self, storage: fk.Storage, faker: Faker):
        data = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(BytesIO(data)))

        content = storage.content(result)

        assert content == data

    def test_missing(self, storage: fk.Storage, faker: Faker):
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        result.location += str(faker.uuid4())

        with pytest.raises(fk.exc.MissingFileError):
            storage.stream(result)

        with pytest.raises(fk.exc.MissingFileError):
            storage.content(result)


class TestStorage:
    def test_missing_path(self, tmp_path: Path):
        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            fs.FsStorage(
                {"path": os.path.join(str(tmp_path), "not-real")},
            )

    def test_missing_path_created(self, tmp_path: Path):
        path = os.path.join(str(tmp_path), "not-real")
        assert not os.path.exists(path)

        fs.FsStorage({"path": path, "create_path": True})
        assert os.path.exists(path)
