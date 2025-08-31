"""Memory adapter."""

from __future__ import annotations

import dataclasses
import logging
import os
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
        filepath = self.storage.full_path(location)
        reader = upload.hashing_reader()
        if filepath in self.storage.settings.bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        self.storage.settings.bucket[filepath] = reader.read()

        return fk.FileData(location, upload.size, upload.content_type, hash=reader.get_hash())

    @override
    def resumable_start(self, location: fk.Location, size: int, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        self.storage.settings.bucket[filepath] = b""

        return fk.FileData.from_dict(
            extras, size=size, location=location, storage_data={"resumable": True, "memory": {"uploaded": 0}}
        )

    @override
    def resumable_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)
        bucket = self.storage.settings.bucket

        if filepath not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        result = fk.FileData.from_object(data)
        result.storage_data["memory"]["uploaded"] = len(bucket[filepath])

        if result.size == result.storage_data["memory"]["uploaded"]:
            reader = fk.HashingReader(BytesIO(bucket[filepath]))
            reader.exhaust()

            hash = reader.get_hash()
            result = fk.FileData.from_object(result, hash=hash)

            result.storage_data.pop("memory")
            result.storage_data.pop("resumable")

        return result

    @override
    def resumable_resume(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        bucket = self.storage.settings.bucket

        if filepath not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        expected_size = upload.size + len(bucket[filepath])
        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        result = fk.FileData.from_object(data)

        bucket[filepath] += upload.stream.read()
        result.storage_data["memory"]["uploaded"] = expected_size

        size = len(bucket[filepath])
        if result.size == size:
            reader = fk.HashingReader(BytesIO(bucket[filepath]))
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
        filepath = self.storage.full_path(data.location)

        bucket = self.storage.settings.bucket
        result = bucket.pop(filepath, None)
        return result is not None

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)

        bucket = self.storage.settings.bucket
        return filepath in bucket

    @override
    def compose(self, location: fk.Location, datas: Iterable[fk.FileData], extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)

        bucket = self.storage.settings.bucket
        if filepath in bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        result = b""
        for data in datas:
            part_path = self.storage.full_path(data.location)
            if part_path not in bucket:
                raise fk.exc.MissingFileError(self.storage, data.location)
            result += bucket[part_path]

        bucket[filepath] = result

        return self.analyze(location, extras)

    @override
    def append(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        bucket = self.storage.settings.bucket
        if filepath not in bucket:
            raise fk.exc.MissingFileError(self.storage, data.location)

        bucket[filepath] += upload.stream.read()
        return self.analyze(data.location, extras)

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)

        bucket = self.storage.settings.bucket
        if filepath in bucket and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        sourcepath = self.storage.full_path(data.location)
        if sourcepath not in bucket:
            raise fk.exc.MissingFileError(self.storage, location)

        bucket[filepath] = bucket[sourcepath]
        return self.analyze(location, extras)

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        result = self.copy(location, data, extras)
        self.remove(data, extras)
        return result

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        # create a copy of keys to avoid "dictionary changed size during
        # iteration" error
        keys = list(self.storage.settings.bucket)
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"
        for key in keys:
            if key.startswith(path):
                yield os.path.relpath(key, path)

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)

        try:
            content = self.storage.settings.bucket[filepath]
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
        filepath = self.storage.full_path(data.location)

        try:
            return [self.storage.settings.bucket[filepath]]
        except KeyError as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err

    @override
    def range(self, data: fk.FileData, start: int, end: int | None, extras: dict[str, Any]) -> Iterable[bytes]:
        filepath = self.storage.full_path(data.location)
        try:
            return [self.storage.settings.bucket[filepath][start:end]]
        except KeyError as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err


class MemoryStorage(fk.Storage):
    """Storage files in-memory.

    This storage adapter keeps files in memory using a dictionary. It is
    mainly useful for testing purposes. It is not recommended to use it in
    production as all files will be lost when the application stops.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:memory",
        "override_existing": False,
    }
    storage = fk.make_storage("memory", settings)
    ```

    Note:
    * The `override_existing` setting controls whether existing files can be
      overridden. If set to `False`, attempting to upload a file to a location
      that already exists will raise an `ExistingFileError`.
    * The `bucket` setting is a dictionary that holds the uploaded files in
        memory. It is automatically initialized as an empty dictionary if not
        provided.
    * This storage adapter does not support persistence. All files are lost
      when the application stops.
    """

    settings: Settings

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader
    ManagerFactory = Manager
