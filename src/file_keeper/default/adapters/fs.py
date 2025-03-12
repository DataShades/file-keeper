from __future__ import annotations

import copy
import dataclasses
import glob
import logging
import os
import shutil
from io import BytesIO
from typing import IO, Any, ClassVar, Iterable

import magic

import file_keeper as fk

log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for FS storage.

    Args:
        create_path: create `path` if it does not exist
        recursive: expect files inside subfolders the `path`
        path: non-empty location for storage folder
    """

    create_path: bool = False
    recursive: bool = False
    path: str = ""

    _required_options: ClassVar[list[str]] = ["path"]


class Uploader(fk.Uploader):
    storage: FsStorage
    capabilities = fk.Capability.CREATE | fk.Capability.MULTIPART

    def upload(
        self,
        location: str,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Upload file to computed location.

        File is always stored under the configured `path`. If `recursive`
        uploads allowed, nested directories may be created.

        When an attempt to upload file using an absolute path or path that
        resolves to parent directory is detected, problematic part is stripped
        and only valid relative subpath is used.
        """
        subpath, basename = os.path.split(location)
        subpath = os.path.normpath(subpath).lstrip("./")

        if subpath and not self.storage.settings.recursive:
            raise fk.exc.LocationError(self.storage, subpath)

        location = os.path.join(subpath, basename)

        dest = os.path.join(self.storage.settings.path, location)

        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, dest)

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        reader = fk.HashingReader(upload.stream)
        with open(dest, "wb") as fd:
            for chunk in reader:
                fd.write(chunk)

        return fk.FileData(
            location,
            os.path.getsize(dest),
            upload.content_type,
            reader.get_hash(),
        )

    def multipart_start(
        self,
        location: str,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        upload = fk.Upload(
            BytesIO(),
            location,
            data.size,
            data.content_type,
        )

        tmp_result = self.upload(location, upload, extras)

        data.location = tmp_result.location
        data.storage_data = dict(tmp_result.storage_data, uploaded=0)
        return data

    def multipart_refresh(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        filepath = os.path.join(
            str(self.storage.settings.path),
            data.location,
        )
        data.storage_data["uploaded"] = os.path.getsize(filepath)

        return data

    def multipart_update(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        extras.setdefault("position", data.storage_data["uploaded"])
        upload: fk.Upload = extras["upload"]

        expected_size = extras["position"] + upload.size
        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        filepath = os.path.join(
            str(self.storage.settings.path),
            data.location,
        )
        with open(filepath, "rb+") as dest:
            dest.seek(extras["position"])
            dest.write(upload.stream.read())

        data.storage_data["uploaded"] = os.path.getsize(filepath)
        return data

    def multipart_complete(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        filepath = os.path.join(
            str(self.storage.settings.path),
            data.location,
        )
        size = os.path.getsize(filepath)
        if size != data.size:
            raise fk.exc.UploadSizeMismatchError(size, data.size)

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

        return fk.FileData(data.location, size, content_type, reader.get_hash())


class Manager(fk.Manager):
    storage: FsStorage
    capabilities = (
        fk.Capability.REMOVE
        | fk.Capability.SCAN
        | fk.Capability.EXISTS
        | fk.Capability.ANALYZE
        | fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.COMPOSE
        | fk.Capability.APPEND
    )

    def compose(
        self,
        datas: Iterable[fk.FileData],
        location: str,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Combine multipe file inside the storage into a new one."""
        dest = os.path.join(self.storage.settings.path, location)
        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, dest)

        sources: list[str] = []
        for data in datas:
            src = os.path.join(str(self.storage.settings.path), data.location)

            if not os.path.exists(src):
                raise fk.exc.MissingFileError(self.storage, src)
            sources.append(src)

        with open(dest, "wb") as to_fd:
            for src in sources:
                with open(src, "rb") as from_fd:
                    shutil.copyfileobj(from_fd, to_fd)

        return self.analyze(dest, extras)

    def append(
        self,
        data: fk.FileData,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Append content to existing file."""
        dest = os.path.join(str(self.storage.settings.path), data.location)
        with open(dest, "ab") as fd:
            fd.write(upload.stream.read())

        return self.analyze(dest, extras)

    def copy(
        self,
        data: fk.FileData,
        location: str,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Copy file inside the storage."""
        src = os.path.join(str(self.storage.settings.path), data.location)
        dest = os.path.join(str(self.storage.settings.path), location)

        if not os.path.exists(src):
            raise fk.exc.MissingFileError(self.storage, src)

        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, dest)

        shutil.copy(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def move(
        self,
        data: fk.FileData,
        location: str,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Move file to a different location inside the storage."""
        src = os.path.join(str(self.storage.settings.path), data.location)
        dest = os.path.join(str(self.storage.settings.path), location)

        if not os.path.exists(src):
            raise fk.exc.MissingFileError(self.storage, src)

        if os.path.exists(dest):
            if self.storage.settings.override_existing:
                os.remove(dest)
            else:
                raise fk.exc.ExistingFileError(self.storage, dest)

        shutil.move(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = os.path.join(str(self.storage.settings.path), data.location)
        return os.path.exists(filepath)

    def remove(
        self, data: fk.FileData | fk.MultipartData, extras: dict[str, Any]
    ) -> bool:
        filepath = os.path.join(str(self.storage.settings.path), data.location)
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        search_path = os.path.join(path, "**")

        for entry in glob.glob(
            search_path,
            recursive=self.storage.settings.recursive,
        ):
            if not os.path.isfile(entry):
                continue
            yield os.path.relpath(entry, path)

    def analyze(self, location: str, extras: dict[str, Any]) -> fk.FileData:
        """Return all details about location."""
        filepath = os.path.join(str(self.storage.settings.path), location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, filepath)

        with open(filepath, "rb") as src:
            reader = fk.HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            reader.exhaust()

        return fk.FileData(
            location,
            size=os.path.getsize(filepath),
            content_type=content_type,
            hash=reader.get_hash(),
        )


class Reader(fk.Reader):
    storage: FsStorage
    capabilities = fk.Capability.STREAM | fk.Capability.TEMPORAL_LINK

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> IO[bytes]:
        filepath = os.path.join(str(self.storage.settings.path), data.location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, filepath)

        return open(filepath, "rb")  # noqa: SIM115


class FsStorage(fk.Storage):
    """Store files in local filesystem."""

    settings: Settings

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader
    ManagerFactory = Manager

    @classmethod
    def configure(cls, settings: dict[str, Any]):
        cfg: Settings = super().configure(settings)

        path = cfg.path

        if not os.path.exists(path):
            if cfg.create_path:
                os.makedirs(path)
            else:
                raise fk.exc.InvalidStorageConfigurationError(
                    cls,
                    f"path `{path}` does not exist",
                )

        return cfg
