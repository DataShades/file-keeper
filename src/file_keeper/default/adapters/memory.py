from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterable
from io import BytesIO
from typing import Any, cast

import magic
from typing_extensions import override

import file_keeper as fk

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for Null storage."""

    bucket: dict[str, bytes] = cast("dict[str, bytes]", dataclasses.field(default_factory=dict))


class Uploader(fk.Uploader):
    storage: MemoryStorage
    capabilities: fk.Capability = fk.Capability.UPLOADER_CAPABILITIES

    @override
    def upload(self, location: fk.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        reader = upload.hashing_reader()
        if location in self.storage.settings.bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        self.storage.settings.bucket[location] = reader.read()

        return fk.FileData(location, upload.size, upload.content_type, hash=reader.get_hash())

    @override
    def multipart_start(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        self.storage.settings.bucket[data.location] = b""

        result = fk.FileData.from_object(data)
        result.storage_data["uploaded"] = 0
        return result

    @override
    def multipart_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket

        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        result = fk.FileData.from_object(data)
        result.storage_data["uploaded"] = len(bucket[data.location])
        return result

    @override
    def multipart_update(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        if "upload" not in extras:
            raise fk.exc.MissingExtrasError("upload")

        upload = fk.make_upload(extras["upload"])

        bucket = self.storage.settings.bucket

        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        expected_size = upload.size + len(bucket[data.location])
        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        bucket[data.location] += upload.stream.read()
        data.storage_data["uploaded"] = expected_size
        return data

    @override
    def multipart_complete(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        bucket = self.storage.settings.bucket

        if data.location not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        actual_size = len(bucket[data.location])
        if data.size != actual_size:
            raise fk.exc.UploadSizeMismatchError(actual_size, data.size)

        reader = fk.HashingReader(BytesIO(bucket[data.location]))
        content_type = magic.from_buffer(next(reader, b""), True)
        if data.content_type and content_type != data.content_type:
            raise fk.exc.UploadTypeMismatchError(
                content_type,
                data.content_type,
            )

        reader.exhaust()
        actual_hash = reader.get_hash()

        if data.hash and data.hash != actual_hash:
            raise fk.exc.UploadHashMismatchError(actual_hash, data.hash)

        return fk.FileData(data.location, data.size, data.content_type, actual_hash)


class Manager(fk.Manager):
    storage: MemoryStorage
    capabilities: fk.Capability = fk.Capability.MANAGER_CAPABILITIES

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
        yield from self.storage.settings.bucket

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
