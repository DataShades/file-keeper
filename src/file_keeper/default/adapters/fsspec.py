"""Fsspec adapter."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Iterable
from typing import Any, cast

import fsspec
import magic
from typing_extensions import override

import file_keeper as fk


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Fsspec storage settings."""

    params: dict[str, Any] = cast("dict[str, Any]", dataclasses.field(default_factory=dict))
    """Parameters for fsspec protocol initialization."""
    protocol: str = ""
    """Name of fsspec filesystem protocol."""
    fs: fsspec.AbstractFileSystem = None  # pyright: ignore[reportAssignmentType]
    """Existing fsspec filesystem."""

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        if not self.fs:
            if not self.protocol:
                raise fk.exc.MissingStorageConfigurationError(self.name, "protocol")

            try:
                self.fs = fsspec.filesystem(self.protocol, **self.params)
            except ValueError as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    str(err),
                ) from err


class Uploader(fk.Uploader):
    """FsSpec uploader."""

    storage: FsSpecStorage
    capabilities: fk.Capability = fk.Capability.CREATE

    @override
    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        fs = self.storage.settings.fs
        filepath = self.storage.full_path(location)

        if not self.storage.settings.override_existing and fs.exists(filepath):
            raise fk.exc.ExistingFileError(self.storage, location)

        with fs.open(filepath, "wb") as fobj:
            reader = upload.hashing_reader()
            for chunk in reader:
                fobj.write(chunk)  # pyright: ignore[reportArgumentType]

        return fk.FileData(
            location=location,
            size=reader.position,
            content_type=upload.content_type,
            hash=reader.get_hash(),
        )


class Reader(fk.Reader):
    """FsSpec reader."""

    storage: FsSpecStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        fs = self.storage.settings.fs
        filepath = self.storage.full_path(data.location)

        try:
            with fs.open(filepath, "rb") as src:  # pyright: ignore[reportUnknownVariableType]
                yield from src  # pyright: ignore[reportReturnType]

        except FileNotFoundError as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err


class Manager(fk.Manager):
    """FsSpec manager."""

    storage: FsSpecStorage
    capabilities: fk.Capability = (
        fk.Capability.REMOVE
        | fk.Capability.SCAN
        | fk.Capability.EXISTS
        | fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.ANALYZE
    )

    @override
    def copy(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        fs = self.storage.settings.fs

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(fk.FileData(location), extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        src_location = self.storage.full_path(data.location)
        dest_location = self.storage.full_path(location)

        fs.cp(src_location, dest_location)

        return fk.FileData.from_object(data, location=location)

    @override
    def move(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        fs = self.storage.settings.fs

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(fk.FileData(location), extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        src_location = self.storage.full_path(data.location)
        dest_location = self.storage.full_path(location)

        fs.mv(src_location, dest_location)

        return fk.FileData.from_object(data, location=location)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)

        fs = self.storage.settings.fs
        return fs.exists(filepath)

    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        fs = self.storage.settings.fs
        if not fs.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, location)

        src = fs.open(filepath, "rb")  # pyright: ignore[reportUnknownVariableType]
        with src:
            reader = fk.HashingReader(fk.IterableBytesReader(src))  # pyright: ignore[reportArgumentType]
            content_type = magic.from_buffer(next(reader, b""), True)
            reader.exhaust()

        return fk.FileData(location, size=reader.position, content_type=content_type, hash=reader.get_hash())

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        fs = self.storage.settings.fs

        if not fs.exists(filepath):
            return False

        fs.rm(filepath)
        return True

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        fs = self.storage.settings.fs

        for name in self._scan(fs, path):
            yield os.path.relpath(name, path)

    def _scan(self, fs: fsspec.AbstractFileSystem, path: str) -> Iterable[str]:
        for entry in fs.ls(path, detail=True):  # pyright: ignore[reportUnknownVariableType]
            if entry["type"] == "file":
                yield entry["name"]
            elif entry["type"] == "directory":
                yield from self._scan(fs, entry["name"])


class FsSpecStorage(fk.Storage):
    """Fsspec storage.

    This storage uses [fsspec](https://filesystem-spec.readthedocs.io/en/latest/)
    to provide a unified interface for various filesystems, including local
    filesystems, cloud storage services (like Amazon S3, Google Cloud Storage,
    Azure Blob Storage), and more.

    The `protocol` parameter specifies the filesystem type (e.g., `s3`, `gcs`,
    `file`, etc.), while the `params` dictionary allows you to pass additional
    configuration options required by the chosen filesystem. For example,
    when using S3, you might need to provide access keys and region information.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:fsspec",
        "protocol": "local",
        "path": "/tmp/file-keeper",
        "params": {"auto_mkdir": True},
    }

    storage = fk.make_storage("fsspec", settings)
    ```

    Note:
    * Ensure that the necessary dependencies for the chosen filesystem are
      installed. For example, to use S3, you might need to install `s3fs`.
    * The `path` setting in the base `fk.Settings` class is used as a base path
        for relative file operations. Ensure that your `location` values are
        relative to this base path.

    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader

    @override
    def compute_capabilities(self) -> fk.Capability:
        return super().compute_capabilities()
