from __future__ import annotations

import dataclasses
import zipfile
from collections.abc import Iterable
from typing import Any

from typing_extensions import override

import file_keeper as fk

REMOVE_MARKER = b"FILE_KEEPER REMOVED"


def _exists(info: zipfile.ZipInfo):
    return info.comment != REMOVE_MARKER


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for a ZIP storage."""

    _required_options = ["path"]


class Uploader(fk.Uploader):
    """Service responsible for writing data into a zip storage."""

    capabilities = fk.Capability.CREATE

    @override
    def upload(self, location: fk.Location, upload: fk.Upload, extras: dict[str, Any]):
        reader = fk.HashingReader(upload.stream)
        with zipfile.ZipFile(self.storage.settings.path, "a") as z:
            try:
                info = z.getinfo(location)
            except KeyError:
                pass
            else:
                if not self.storage.settings.override_existing and _exists(info):
                    raise fk.exc.ExistingFileError(self.storage, location)

            z.writestr(location, reader.read())

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            hash=reader.get_hash(),
        )


class Reader(fk.Reader):
    """Service responsible for reading data from the zip storage."""

    capabilities = fk.Capability.STREAM

    @override
    def stream(
        self,
        data: fk.FileData,
        extras: dict[str, Any],
    ):
        with zipfile.ZipFile(self.storage.settings.path, "r") as z:
            try:
                info = z.getinfo(data.location)
            except KeyError as err:
                raise fk.exc.MissingFileError(self.storage, data.location) from err

            if not _exists(info):
                raise fk.exc.MissingFileError(self.storage, data.location)

            return [z.read(info)]


class Manager(fk.Manager):
    """Service responsible for managing data in the zip storage."""

    capabilities = fk.Capability.REMOVE | fk.Capability.SCAN | fk.Capability.EXISTS

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]):
        with zipfile.ZipFile(self.storage.settings.path, "a") as z:
            try:
                info = z.getinfo(data.location)
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
        with zipfile.ZipFile(self.storage.settings.path, "a") as z:
            try:
                return _exists(z.getinfo(data.location))
            except KeyError:
                return False

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        with zipfile.ZipFile(self.storage.settings.path, "a") as z:
            yield from (info.filename for info in z.infolist() if _exists(info))


class ZipStorage(fk.Storage):
    """Storage implementation using a ZIP file."""

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
