"""Filesystem adapter."""

from __future__ import annotations

import dataclasses
import glob
import logging
import os
import shutil
from collections.abc import Iterable
from io import BytesIO
from typing import IO, Any, ClassVar

import magic
from typing_extensions import override

import file_keeper as fk
from file_keeper.core.utils import SAMPLE_SIZE

log = logging.getLogger(__name__)


# --8<-- [start:storage_cfg]
@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for FS storage."""

    # --8<-- [end:storage_cfg]
    _required_options: ClassVar[list[str]] = ["path"]

    # --8<-- [start:storage_cfg_post_init]
    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        if not os.path.exists(self.path):
            if not self.initialize:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    f"path `{self.path}` does not exist",
                )

            try:
                os.makedirs(self.path)
            except PermissionError as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    f"path `{self.path}` is not writable",
                ) from err

    # --8<-- [end:storage_cfg_post_init]


# --8<-- [start:uploader_def]
class Uploader(fk.Uploader):
    """Filesystem uploader."""

    # --8<-- [end:uploader_def]
    storage: FsStorage

    # --8<-- [start:uploader_capability]
    capabilities: fk.Capability = fk.Capability.CREATE | fk.Capability.RESUMABLE
    # --8<-- [end:uploader_capability]

    # --8<-- [start:uploader_method]
    @override
    def upload(self, location: fk.types.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        # --8<-- [end:uploader_method]
        """Upload file to computed location.

        File location is relative the configured `path`. If `Settings.path` is
        not empty and location leads to the place outside of this path, the
        upload will fail with an exception. But if `Settings.path` is empty, no
        restrictions applied to the final location. Consider using combination
        of `storage.prepare_location` with `settings.location_transformers` to
        sanitize the path, like `safe_relative_path`, if you are using
        filesystem-like storage. For cloud providers or DB storages this should
        not be a problem, as they allow using any characters for the name of
        fileobject.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            LocationError: unallowed usage of subdirectory

        Returns:
            New file data

        """
        # --8<-- [start:uploader_impl_path]
        dest = self.storage.full_path(location)
        # --8<-- [end:uploader_impl_path]

        # --8<-- [start:uploader_impl_check]
        if not self.storage.settings.override_existing and os.path.exists(dest):
            raise fk.exc.ExistingFileError(self.storage, location)
        # --8<-- [end:uploader_impl_check]

        # --8<-- [start:uploader_impl_makedirs]
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # --8<-- [end:uploader_impl_makedirs]

        # --8<-- [start:uploader_impl_write]
        reader = upload.hashing_reader()
        with open(dest, "wb") as fd:
            for chunk in reader:
                fd.write(chunk)
        # --8<-- [end:uploader_impl_write]

        # --8<-- [start:uploader_impl_result]
        return fk.FileData(
            location,
            os.path.getsize(dest),
            upload.content_type,
            reader.get_hash(),
        )

    # --8<-- [end:uploader_impl_result]

    @override
    def resumable_start(self, location: fk.Location, size: int, extras: dict[str, Any]) -> fk.FileData:
        upload = fk.Upload(BytesIO(), location, 0, fk.FileData.content_type)

        tmp_result = self.upload(location, upload, extras)

        return fk.FileData.from_dict(
            extras,
            location=tmp_result.location,
            size=size,
            storage_data={"resumable": True, "uploaded": 0},
        )

    @override
    def resumable_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, data.location)

        result = fk.FileData.from_object(data)
        result.storage_data["uploaded"] = os.path.getsize(filepath)

        if result.storage_data["uploaded"] == result.size:
            result = self._resumable_complete(result)

        return result

    def _resumable_complete(self, data: fk.FileData):
        filepath = self.storage.full_path(data.location)

        with open(filepath, "rb") as src:
            reader = fk.HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            if data.content_type and content_type != data.content_type:
                raise fk.exc.UploadTypeMismatchError(
                    content_type,
                    data.content_type,
                )
            reader.exhaust()

        if data.hash and data.hash != reader.get_hash():
            raise fk.exc.UploadHashMismatchError(reader.get_hash(), data.hash)

        result = fk.FileData.from_object(data, hash=reader.get_hash())
        result.storage_data.pop("uploaded")
        result.storage_data.pop("resumable")
        return result

    @override
    def resumable_resume(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, data.location)

        uploaded = data.storage_data["uploaded"]
        expected_size = uploaded + upload.size

        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        filepath = self.storage.full_path(data.location)
        with open(filepath, "rb+") as dest:
            dest.seek(uploaded)
            for chunk in upload.stream:
                dest.write(chunk)

        result = fk.FileData.from_object(data)
        result.storage_data["uploaded"] = os.path.getsize(filepath)

        if result.storage_data["uploaded"] == result.size:
            result = self._resumable_complete(result)

        return result

    @override
    def resumable_remove(self, data: fk.FileData, extras: dict[str, Any]):
        return self.storage.remove(data, **extras)


# --8<-- [start:reader_impl]
class Reader(fk.Reader):
    """Filesystem reader."""

    storage: FsStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> IO[bytes]:
        filepath = self.storage.full_path(data.location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, data.location)

        return open(filepath, "rb")  # noqa: SIM115


# --8<-- [end:reader_impl]


class Manager(fk.Manager):
    """Filesystem manager."""

    storage: FsStorage
    # --8<-- [start:manager_capabilities]
    capabilities: fk.Capability = (
        fk.Capability.REMOVE
        | fk.Capability.SCAN
        | fk.Capability.EXISTS
        | fk.Capability.ANALYZE
        | fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.COMPOSE
        | fk.Capability.APPEND
    )
    # --8<-- [end:manager_capabilities]

    # --8<-- [start:manager_compose]
    @override
    def compose(self, location: fk.types.Location, datas: Iterable[fk.FileData], extras: dict[str, Any]) -> fk.FileData:
        dest = self.storage.full_path(location)

        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        sources: list[str] = []
        for data in datas:
            src = self.storage.full_path(data.location)

            if not os.path.exists(src):
                raise fk.exc.MissingFileError(self.storage, data.location)

            sources.append(src)

        with open(dest, "wb") as to_fd:
            for src in sources:
                with open(src, "rb") as from_fd:
                    shutil.copyfileobj(from_fd, to_fd)

        return self.analyze(location, extras)

    # --8<-- [end:manager_compose]

    # --8<-- [start:manager_append]
    @override
    def append(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        dest = self.storage.full_path(data.location)
        if not os.path.exists(dest):
            raise fk.exc.MissingFileError(self.storage, data.location)

        with open(dest, "ab") as fd:
            fd.write(upload.stream.read())

        return self.analyze(data.location, extras)

    # --8<-- [end:manager_append]

    # --8<-- [start:manager_copy]
    @override
    def copy(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        src = self.storage.full_path(data.location)
        dest = self.storage.full_path(location)

        if not os.path.exists(src):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, location)

        shutil.copy(src, dest)
        return fk.FileData.from_object(data, location=location)

    # --8<-- [end:manager_copy]

    # --8<-- [start:manager_move]
    @override
    def move(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        src = self.storage.full_path(data.location)
        dest = self.storage.full_path(location)

        if not os.path.exists(src):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if os.path.exists(dest):
            if self.storage.settings.override_existing:
                os.remove(dest)
            else:
                raise fk.exc.ExistingFileError(self.storage, location)

        shutil.move(src, dest)
        return fk.FileData.from_object(data, location=location)

    # --8<-- [end:manager_move]

    # --8<-- [start:manager_exists]
    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        return os.path.exists(filepath)

    # --8<-- [end:manager_exists]

    # --8<-- [start:manager_remove]
    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True

    # --8<-- [end:manager_remove]

    # --8<-- [start:manager_scan]
    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        search_path = os.path.join(path, "**")

        for entry in glob.glob(search_path, recursive=True):
            if not os.path.isfile(entry):
                continue
            yield os.path.relpath(entry, path)

    # --8<-- [end:manager_scan]

    # --8<-- [start:manager_analyze]
    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData(
            location,
            size=self.size(location, extras),
            content_type=self.content_type(location, extras),
            hash=self.hash(location, extras),
        )

    # --8<-- [end:manager_analyze]

    @override
    def size(self, location: fk.Location, extras: dict[str, Any]) -> int:
        filepath = self.storage.full_path(location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, location)

        return os.path.getsize(filepath)

    @override
    def hash(self, location: fk.Location, extras: dict[str, Any]) -> str:
        filepath = self.storage.full_path(location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, location)

        with open(filepath, "rb") as src:
            reader = fk.HashingReader(src)
            reader.exhaust()
            return reader.get_hash()

    @override
    def content_type(self, location: fk.Location, extras: dict[str, Any]) -> str:
        filepath = self.storage.full_path(location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, location)

        with open(filepath, "rb") as src:
            return magic.from_buffer(src.read(SAMPLE_SIZE), True)


# --8<-- [start:storage]
class FsStorage(fk.Storage):
    """Filesystem storage adapter.

    Stores files on the local filesystem. The `path` setting must be
    configured to point to the base directory where files are stored.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:fs",
        "path": "/path/to/storage",
        "initialize": True,
        "override_existing": False,
    }
    storage = fk.make_storage("fs", settings)
    ```

    Note:
    * The `path` must be an absolute path.
    * The `path` directory must be writable by the application.
    * The `location` used in file operations is relative to the `path`.
    * If `Storage.path` is not empty, the `location` is validated
      to prevent directory traversal.
    * Consider using combination of `storage.prepare_location` with
      `settings.location_transformers` that further sanitizes the path, like
      `safe_relative_path`.
    * If `initialize` is `True`, the storage will attempt to create the
      directory if it does not exist.
    * If `override_existing` is `False`, operations that would overwrite an
      existing file will raise an `ExistingFileError`.
    """

    settings: Settings

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader
    ManagerFactory = Manager


# --8<-- [end:storage]
