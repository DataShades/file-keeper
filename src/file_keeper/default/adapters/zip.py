"""ZIP adapter."""

from __future__ import annotations

import dataclasses
import os
import zipfile
from collections.abc import Iterable
from typing import Any, Literal

import magic
from typing_extensions import override

import file_keeper as fk

REMOVE_MARKER = b"FILE_KEEPER REMOVED"


def _exists(info: zipfile.ZipInfo):
    """Check if a file exists (i.e., is not marked as removed)."""
    return info.comment != REMOVE_MARKER


def _open(settings: Settings, mode: Literal["a", "r"]):
    """Open the ZIP file."""
    return zipfile.ZipFile(settings.zip_path, "a")


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for a ZIP storage."""

    zip_path: str = ""
    """Path to the ZIP file used for storage."""

    _required_options = ["zip_path"]


class Uploader(fk.Uploader):
    """Service responsible for writing data into a zip storage."""

    storage: ZipStorage
    capabilities = fk.Capability.CREATE

    @override
    def upload(self, location: fk.Location, upload: fk.Upload, extras: dict[str, Any]):
        filepath = self.storage.full_path(location)

        reader = fk.HashingReader(upload.stream)
        with _open(self.storage.settings, "a") as z:
            try:
                info = z.getinfo(filepath)
            except KeyError:
                pass
            else:
                if not self.storage.settings.override_existing and _exists(info):
                    raise fk.exc.ExistingFileError(self.storage, location)

            z.writestr(filepath, reader.read())

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            hash=reader.get_hash(),
        )


class Reader(fk.Reader):
    """Service responsible for reading data from the zip storage."""

    storage: ZipStorage
    capabilities = fk.Capability.STREAM

    @override
    def stream(
        self,
        data: fk.FileData,
        extras: dict[str, Any],
    ):
        filepath = self.storage.full_path(data.location)
        with _open(self.storage.settings, "r") as z:
            try:
                info = z.getinfo(filepath)
            except KeyError as err:
                raise fk.exc.MissingFileError(self.storage, data.location) from err

            if not _exists(info):
                raise fk.exc.MissingFileError(self.storage, data.location)

            return [z.read(info)]


class Manager(fk.Manager):
    """Service responsible for managing data in the zip storage."""

    storage: ZipStorage
    capabilities = fk.Capability.REMOVE | fk.Capability.SCAN | fk.Capability.EXISTS | fk.Capability.ANALYZE

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]):
        filepath = self.storage.full_path(data.location)
        with _open(self.storage.settings, "a") as z:
            try:
                info = z.getinfo(filepath)
            except KeyError:
                return False

            if not _exists(info):
                return False

            info.file_size = 0
            info.comment = REMOVE_MARKER
            z.writestr(info, b"")
        return True

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        with _open(self.storage.settings, "a") as z:
            try:
                return _exists(z.getinfo(filepath))
            except KeyError:
                return False

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"

        with _open(self.storage.settings, "a") as z:
            for info in z.infolist():
                if info.filename.startswith(path) and _exists(info):
                    yield os.path.relpath(info.filename, path)

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        with _open(self.storage.settings, "a") as z:
            try:
                info = z.getinfo(filepath)
            except KeyError as err:
                raise fk.exc.MissingFileError(self.storage, location) from err

            if not _exists(info):
                raise fk.exc.MissingFileError(self.storage, location)

            reader = fk.HashingReader(z.open(info))
            content_type = magic.from_buffer(next(reader, b""), True)
            reader.exhaust()

            return fk.FileData(
                location,
                size=reader.position,
                content_type=content_type,
                hash=reader.get_hash(),
            )


class ZipStorage(fk.Storage):
    """Storage implementation using a ZIP file.

    This storage uses a ZIP file to store files. It supports uploading, reading,
    removing, and scanning files within the ZIP archive.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:zip",
        "path": "/path/to/storage.zip",
        "override_existing": False,  # Optional, defaults to False
    }

    storage = fk.make_storage("zip", settings)
    ```

    Note:
    * The `path` setting specifies the location of the ZIP file.
    * The `override_existing` setting determines whether existing files should be
      overridden during upload. Defaults to `False`.
    * Removed files are truncated and marked within the ZIP archive, and are not
      physically deleted.
    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
