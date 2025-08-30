"""Memory adapter."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterable, MutableMapping
from io import BytesIO
from typing import Any, cast

import magic
from typing_extensions import override

import file_keeper as fk

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for memory storage."""

    bucket: MutableMapping[str, bytes] = cast("dict[str, bytes]", dataclasses.field(default_factory=dict))
    """Container for uploaded objects."""


class Uploader(fk.Uploader):
    """Memory uploader."""

    storage: MemoryStorage
    capabilities: fk.Capability = fk.Capability.CREATE | fk.Capability.RESUMABLE

    @override
    def upload(self, location: fk.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        reader = upload.hashing_reader()
        if location in self.storage.settings.bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        self.storage.settings.bucket[location] = reader.read()

        return fk.FileData(location, upload.size, upload.content_type, hash=reader.get_hash())

    @override
    def resumable_start(self, location: fk.Location, size: int, extras: dict[str, Any]) -> fk.FileData:
        self.storage.settings.bucket[location] = b""

        result = fk.FileData.from_dict(
            extras, size=size, location=location, storage_data={"resumable": True, "memory": {"uploaded": 0}}
        )

        return result

    @override
    def resumable_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket

        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        result = fk.FileData.from_object(data)
        result.storage_data["memory"]["uploaded"] = len(bucket[data.location])

        if result.size == result.storage_data["memory"]["uploaded"]:
            reader = fk.HashingReader(BytesIO(bucket[result.location]))
            reader.exhaust()

            hash = reader.get_hash()
            result = fk.FileData.from_object(result, hash=hash)

            result.storage_data.pop("memory")
            result.storage_data.pop("resumable")

        return result

    @override
    def resumable_resume(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket

        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        expected_size = upload.size + len(bucket[data.location])
        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        result = fk.FileData.from_object(data)

        bucket[result.location] += upload.stream.read()
        result.storage_data["memory"]["uploaded"] = expected_size

        size = len(bucket[result.location])
        if result.size == size:
            reader = fk.HashingReader(BytesIO(bucket[result.location]))
            reader.exhaust()

            hash = reader.get_hash()
            result = fk.FileData.from_object(result, hash=hash)

            result.storage_data.pop("memory")
            result.storage_data.pop("resumable")

        return result

    @override
    def resumable_remove(self, data: fk.FileData, extras: dict[str, Any]):
        return self.storage.remove(data, **extras)


class Manager(fk.Manager):
    """Memory manager."""

    storage: MemoryStorage
    capabilities: fk.Capability = (
        fk.Capability.ANALYZE
        | fk.Capability.SCAN
        | fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.APPEND
        | fk.Capability.COMPOSE
        | fk.Capability.EXISTS
        | fk.Capability.REMOVE
    )

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        bucket = self.storage.settings.bucket
        result = bucket.pop(data.location, None)
        return result is not None

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        bucket = self.storage.settings.bucket
        return data.location in bucket

    @override
    def compose(self, location: fk.Location, datas: Iterable[fk.FileData], extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket
        if location in bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        result = b""
        for data in datas:
            if data.location not in bucket:
                raise fk.exc.MissingFileError(self.storage, data.location)
            result += bucket[data.location]

        bucket[location] = result

        return self.analyze(location, extras)

    @override
    def append(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket
        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        bucket[data.location] += upload.stream.read()
        return self.analyze(data.location, extras)

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket
        if location in bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, location)

        bucket[location] = bucket[data.location]
        return self.analyze(location, extras)

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket
        if location in bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, location)

        bucket[location] = bucket.pop(data.location)
        return fk.FileData.from_object(data, location=location)

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        # create a copy of keys to avoid "dictionary changed size during
        # iteration" error
        yield from list(self.storage.settings.bucket)

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        try:
            content = self.storage.settings.bucket[location]
        except KeyError as err:
            raise fk.exc.MissingFileError(self.storage, location) from err

        reader = fk.HashingReader(BytesIO(content))
        content_type = magic.from_buffer(next(reader, b""), True)

        return fk.FileData(location, len(content), content_type, reader.get_hash())


class Reader(fk.Reader):
    """Memory reader."""

    storage: MemoryStorage
    capabilities: fk.Capability = fk.Capability.READER_CAPABILITIES

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        try:
            return [self.storage.settings.bucket[data.location]]
        except KeyError as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err

    @override
    def range(self, data: fk.FileData, start: int, end: int | None, extras: dict[str, Any]) -> Iterable[bytes]:
        try:
            return [self.storage.settings.bucket[data.location][start:end]]
        except KeyError as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err


class MemoryStorage(fk.Storage):
    """Storage files in-memory."""

    settings: Settings

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader
    ManagerFactory = Manager
