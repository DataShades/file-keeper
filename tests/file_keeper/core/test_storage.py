from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

import pytest
from faker import Faker
from typing_extensions import override

import file_keeper as fk
from file_keeper import (
    Capability,
    FileData,
    Manager,
    Reader,
    Settings,
    Storage,
    Uploader,
    exc,
    make_upload,
)


class TestSettings:
    def test_configure(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.DEBUG):
            Settings.from_dict({})
            assert not caplog.records

            settings = Settings.from_dict({"name": "test", "hello": "world"})
            assert len(caplog.records) == 1

            record = caplog.records[0]

            assert record.message == "Storage test received unknow settings: {'hello': 'world'}"
            assert record.levelname == "WARNING"

            assert settings._extra_settings == {"hello": "world"}  # pyright: ignore[reportPrivateUsage]


class TestUploader:
    @pytest.fixture
    def uploader(self):
        return Uploader(Storage({}))

    def test_abstract_methods(self, uploader: Uploader, faker: Faker):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            uploader.upload(fk.types.Location(faker.file_name()), make_upload(b""), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_start(fk.types.Location(faker.file_name()), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_refresh(FileData(fk.Location("")), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_update(FileData(fk.Location("")), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_complete(FileData(fk.Location("")), {})


class TestManager:
    @pytest.fixture
    def manager(self):
        return Manager(Storage({}))

    def test_abstract_methods(self, manager: Manager):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            manager.remove(FileData(fk.types.Location("")), {})


class TestReader:
    @pytest.fixture
    def reader(self):
        return Reader(Storage({}))

    def test_abstract_methods(self, reader: Reader):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            reader.stream(FileData(fk.types.Location("")), {})


class RemovingManager(Manager):
    capabilities: Capability = Capability.REMOVE


class StreamingReader(Reader):
    capabilities: Capability = Capability.STREAM


class SimpleUploader(Uploader):
    capabilities: Capability = Capability.CREATE


class FakeStorage(Storage):
    @override
    def make_reader(self):
        return StreamingReader(self)

    @override
    def make_uploader(self):
        return SimpleUploader(self)

    @override
    def make_manager(self):
        return RemovingManager(self)


class TestStorage:
    def test_inherited_capabilities(self):
        """Storage combine capabilities of its services."""
        storage = FakeStorage({})
        assert storage.capabilities == (Capability.REMOVE | Capability.STREAM | Capability.CREATE)

    def test_disabled_capabilities(self):
        """Existing capabilities can be Ignored."""
        storage = FakeStorage({"disabled_capabilities": ["CREATE", "REMOVE"]})
        assert storage.capabilities == (Capability.STREAM)

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
                fk.types.Location(faker.file_name()),
                make_upload(b""),
            )

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).stream(FileData(fk.types.Location("")))

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).remove(FileData(fk.types.Location("")))

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).copy(
                fk.types.Location(""),
                FileData(fk.types.Location("")),
            )

        with pytest.raises(exc.UnsupportedOperationError):
            Storage({}).move(
                fk.types.Location(""),
                FileData(fk.types.Location("")),
            )

    def test_not_implemented_methods(self, faker: Faker):
        """Storage raises an error if upload is not implemented."""
        storage = FakeStorage({})
        with pytest.raises(NotImplementedError):
            storage.upload(fk.types.Location(faker.file_name()), make_upload(b""))

        with pytest.raises(NotImplementedError):
            storage.remove(FileData(fk.types.Location("")))

        with pytest.raises(exc.UnsupportedOperationError):
            storage.copy(
                fk.types.Location(""),
                FileData(fk.types.Location("")),
            )

        with pytest.raises(exc.UnsupportedOperationError):
            storage.move(
                fk.types.Location(""),
                FileData(fk.types.Location("")),
            )

    def test_prepare_location_uuid(self, faker: Faker):
        """`uuid`(default) name transformer produces valid UUID."""
        storage = FakeStorage({})

        storage.settings.location_transformers = ["uuid"]
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        assert uuid.UUID(result)

    def test_prepare_location_uuid_prefix(self, faker: Faker):
        """`uuid_prefix` name transformer produces valid UUID."""
        storage = FakeStorage({})

        storage.settings.location_transformers = ["uuid_prefix"]
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)
        assert result.endswith(name)
        assert uuid.UUID(result[: -len(name)])

    def test_prepare_location_uuid_with_extension(self, faker: Faker):
        """`uuid_with_extension` name transformer produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_transformers = ["uuid_with_extension"]
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        assert result.endswith(extension)
        assert uuid.UUID(result[: -len(extension) - 1])

    def test_prepare_location_datetime_prefix(
        self,
        faker: Faker,
    ):
        """`datetime_prefix` name transformer produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_transformers = ["datetime_prefix"]
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        assert result[-len(name) :] == name

        assert datetime.fromisoformat(result[: -len(name)])

    def test_prepare_location_datetime_with_extension(
        self,
        faker: Faker,
    ):
        """`datetime_with_extension` name transformer produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_transformers = ["datetime_with_extension"]
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.prepare_location(name)

        ext = os.path.splitext(name)[1]
        assert result[-len(ext) :] == ext

        assert datetime.fromisoformat(result[: -len(ext)])

    def test_prepare_location_with_wrong_transformer(self):
        """`datetime_with_extension` name transformer produces valid UUID."""
        storage = FakeStorage({})
        storage.settings.location_transformers = ["wrong"]
        with pytest.raises(exc.LocationTransformerError):
            storage.prepare_location("test")
