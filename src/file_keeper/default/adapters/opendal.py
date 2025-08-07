from __future__ import annotations

import dataclasses
import io
import os
from collections.abc import Iterable
from typing import Any, cast

import magic
import opendal
from typing_extensions import override

import file_keeper as fk


class FileStream:
    file: opendal.File

    def __init__(self, file: opendal.File):
        self.file = file

    def __iter__(self):
        while chunk := self.file.read(io.DEFAULT_BUFFER_SIZE):
            if isinstance(chunk, memoryview):  # pyright: ignore[reportUnnecessaryIsInstance]
                yield chunk.tobytes()
            else:
                yield chunk


@dataclasses.dataclass()
class Settings(fk.Settings):
    params: dataclasses.InitVar[dict[str, Any] | None] = cast("dict[str, Any]|None", dataclasses.field(default=None))
    scheme: dataclasses.InitVar[str] = ""

    operator: opendal.Operator = None  # pyright: ignore[reportAssignmentType]

    def __post_init__(self, params: dict[str, Any] | None, scheme: str, **kwargs: Any):
        super().__post_init__(**kwargs)

        if self.operator is None:  # pyright: ignore[reportUnnecessaryComparison]
            if not scheme:
                raise fk.exc.MissingStorageConfigurationError(self.name, "scheme")

            try:
                if params is None:
                    params = {}
                self.operator = opendal.Operator(scheme, **params)
            except opendal.exceptions.ConfigInvalid as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    str(err),
                ) from err


class Uploader(fk.Uploader):
    storage: OpenDalStorage
    capabilities: fk.Capability = fk.Capability.CREATE

    @override
    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Upload file to computed location.

        Schemas working with filesystem-like paths assume that location is
        relative the configured `path`. The location is not sanitized and can
        lead outside the configured `path`. Consider using combination of
        `storage.prepare_location` with `settings.location_transformers` that
        sanitizes the path, like `safe_relative_path`.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            LocationError: unallowed usage of subdirectory

        Returns:
            New file data

        """
        op = self.storage.settings.operator
        dest = self.storage.full_path(location)
        subpath = os.path.dirname(dest)

        if subpath and not op.capability().create_dir:
            raise fk.exc.LocationError(self.storage, subpath)

        try:
            op.stat(dest)
        except opendal.exceptions.NotFound:
            pass
        else:
            if not self.storage.settings.override_existing:
                raise fk.exc.ExistingFileError(self.storage, location)

        if subpath:
            # opendal reuquires `/` as a last character
            op.create_dir(subpath.rstrip("/") + "/")

        reader = upload.hashing_reader()
        with op.open(dest, "wb") as fobj:
            for chunk in reader:
                fobj.write(chunk)

        return fk.FileData(
            location,
            reader.position,
            upload.content_type,
            reader.get_hash(),
        )


class Reader(fk.Reader):
    storage: OpenDalStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        """Return file open in binary-read mode.

        Raises:
            MissingFileError: file does not exist

        Returns:
            File content iterator
        """
        location = self.storage.full_path(data.location)

        try:
            content = self.storage.settings.operator.open(location, "rb")
        except opendal.exceptions.NotFound as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err

        return FileStream(content)


class Manager(fk.Manager):
    storage: OpenDalStorage
    capabilities: fk.Capability = (
        fk.Capability.REMOVE
        | fk.Capability.SCAN
        | fk.Capability.EXISTS
        | fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.ANALYZE
        | fk.Capability.APPEND
    )

    @override
    def copy(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Copy file inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        op = self.storage.settings.operator

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(fk.FileData(location), extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        src_location = self.storage.full_path(data.location)
        dest_location = self.storage.full_path(location)

        op.copy(src_location, dest_location)

        return fk.FileData.from_object(data, location=location)

    @override
    def move(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Move file to a different location inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        op = self.storage.settings.operator

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(fk.FileData(location), extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        src_location = self.storage.full_path(data.location)
        dest_location = self.storage.full_path(location)

        op.rename(src_location, dest_location)

        return fk.FileData.from_object(data, location=location)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        """Check if file exists."""
        location = self.storage.full_path(data.location)

        try:
            self.storage.settings.operator.stat(location)
        except opendal.exceptions.NotFound:
            return False

        return True

    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
        """Check if file exists."""
        stream = self.storage.stream(fk.FileData(location))

        reader = fk.HashingReader(fk.IterableBytesReader(stream))
        content_type = magic.from_buffer(next(reader, b""), True)
        reader.exhaust()

        return fk.FileData(
            location,
            size=reader.position,
            content_type=content_type,
            hash=reader.get_hash(),
        )

    @override
    def remove(
        self,
        data: fk.FileData,
        extras: dict[str, Any],
    ) -> bool:
        """Remove the file."""
        op = self.storage.settings.operator
        location = self.storage.full_path(data.location)

        try:
            op.stat(location)
        except opendal.exceptions.NotFound:
            return False

        op.delete(location)
        return True

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """Discover filenames in the storage."""
        for entry in self.storage.settings.operator.scan(self.storage.settings.path):
            stat = self.storage.settings.operator.stat(entry.path)
            if opendal.EntryMode.is_file(stat.mode):
                yield entry.path

    @override
    def append(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        """Append content to existing file.

        If final content type is not supported by the storage, original file is
        removed.

        Raises:
            MissingFileError: file does not exist
        """
        op = self.storage.settings.operator

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        location = self.storage.full_path(data.location)

        op.write(location, upload.stream.read(), append=True)

        return self.analyze(data.location, extras)


class OpenDalStorage(fk.Storage):
    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader

    @override
    def compute_capabilities(self) -> fk.Capability:
        cluster = super().compute_capabilities()
        capabilities = self.settings.operator.capability()

        if not capabilities.stat:
            cluster = cluster.exclude(fk.Capability.EXISTS | fk.Capability.ANALYZE)

        if not capabilities.delete:
            cluster = cluster.exclude(fk.Capability.REMOVE)

        if not capabilities.list or not capabilities.stat:
            cluster = cluster.exclude(fk.Capability.SCAN)

        if not capabilities.write:
            cluster = cluster.exclude(fk.Capability.CREATE)

        if not capabilities.read:
            cluster = cluster.exclude(fk.Capability.STREAM)

        if not capabilities.rename:
            cluster = cluster.exclude(fk.Capability.MOVE)

        if not capabilities.copy:
            cluster = cluster.exclude(fk.Capability.COPY)

        if not capabilities.write_can_append:
            cluster = cluster.exclude(fk.Capability.APPEND)

        return cluster
