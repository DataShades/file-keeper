from __future__ import annotations

import os
import uuid
from datetime import datetime
from io import BytesIO

import pytest
from faker import Faker

from file_keeper import (
    Capability,
    FileData,
    Manager,
    MultipartData,
    Reader,
    Storage,
    Uploader,
    exc,
    make_upload,
)


class TestUploader:
    @pytest.fixture()
    def uploader(self):
        return Uploader(Storage({}))

    def test_abstract_methods(self, uploader: Uploader, faker: Faker):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            uploader.upload(faker.file_name(), make_upload(b""), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_start(faker.file_name(), MultipartData(), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_refresh(MultipartData(), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_update(MultipartData(), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_complete(MultipartData(), {})


class TestManager:
    @pytest.fixture()
    def manager(self):
        return Manager(Storage({}))

    def test_abstract_methods(self, manager: Manager):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            manager.remove(FileData(""), {})


class TestReader:
    @pytest.fixture()
    def reader(self):
        return Reader(Storage({}))

    def test_abstract_methods(self, reader: Reader):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            reader.stream(FileData(""), {})


class RemovingManager(Manager):
    capabilities = Capability.REMOVE


class StreamingReader(Reader):
    capabilities = Capability.STREAM


class SimpleUploader(Uploader):
    capabilities = Capability.CREATE


class FakeStorage(Storage):
    def make_reader(self):
        return StreamingReader(self)

    def make_uploader(self):
        return SimpleUploader(self)

    def make_manager(self):
        return RemovingManager(self)


class TestStorage:
    def test_inherited_capabilities(self):
        """Storage combine capabilities of its services."""
        storage = FakeStorage({})
        assert storage.capabilities == (
            Capability.REMOVE | Capability.STREAM | Capability.CREATE
        )

    def test_supports(self):
        """Storage can tell whether it supports certain capabilities."""
        storage = FakeStorage({})

        assert storage.supports(Capability.CREATE)
        assert storage.supports(Capability.REMOVE | Capability.STREAM)

        assert not storage.supports(Capability.MULTIPART)
        assert not storage.supports(Capability.REMOVE | Capability.MULTIPART)

    def test_not_supported_methods(self, faker: Faker):
        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).upload(
                faker.file_name(),
                make_upload(b""),
            )

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).stream(FileData(""))

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).remove(FileData(""))

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).copy(
                FileData(""),
                Storage({}),
                "",
            )

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).move(
                FileData(""),
                Storage({}),
                "",
            )

    def test_upload_checks_max_size(self, faker: Faker):
        """Storage raises an error if upload exceeds max size."""
        storage = FakeStorage({"max_size": 10})
        with pytest.raises(exc.LargeUploadError):
            storage.upload(faker.file_name(), make_upload(BytesIO(faker.binary(20))))

    def test_not_implemented_methods(self, faker: Faker):
        """Storage raises an error if upload is not implemented."""
        storage = FakeStorage({})
        with pytest.raises(NotImplementedError):
            storage.upload(faker.file_name(), make_upload(b""))

        with pytest.raises(NotImplementedError):
            storage.remove(FileData(""))

        with pytest.raises(NotImplementedError):
            storage.copy(FileData(""), storage, "")

        with pytest.raises(NotImplementedError):
            storage.move(FileData(""), storage, "")

    def test_prepare_location_uuid(self, faker: Faker):
        """`uuid`(default) name strategy produces valid UUID."""
        storage = FakeStorage({})

        storage.settings.location_strategy = "uuid"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        assert uuid.UUID(result)

    def test_prepare_location_uuid_prefix(self, faker: Faker):
        """`uuid_prefix` name strategy produces valid UUID."""
        storage = FakeStorage({})

        storage.settings.location_strategy = "uuid_prefix"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)
        assert result.endswith(name)
        assert uuid.UUID(result[: -len(name)])

    def test_prepare_location_uuid_with_extension(self, faker: Faker):
        """`uuid_with_extension` name strategy produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_strategy = "uuid_with_extension"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        assert result.endswith(extension)
        assert uuid.UUID(result[: -len(extension) - 1])

    def test_prepare_location_datetime_prefix(
        self,
        faker: Faker,
    ):
        """`datetime_prefix` name strategy produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_strategy = "datetime_prefix"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        assert result[-len(name) :] == name

        assert datetime.fromisoformat(result[: -len(name)])

    def test_prepare_location_datetime_with_extension(
        self,
        faker: Faker,
    ):
        """`datetime_with_extension` name strategy produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_strategy = "datetime_with_extension"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        ext = os.path.splitext(name)[1]
        assert result[-len(ext) :] == ext

        assert datetime.fromisoformat(result[: -len(ext)])

    def test_prepare_location_with_wrong_strategy(self):
        """`datetime_with_extension` name strategy produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_strategy = "wrong_strategy"
        with pytest.raises(exc.LocationStrategyError):
            storage.prepare_location("test")
