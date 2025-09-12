"""Obstore adapter."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Iterable
from typing import Any, cast

import magic
import obstore
from typing_extensions import override

import file_keeper as fk


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Obstore storage settings."""

    params: dict[str, Any] = cast("dict[str, Any]", dataclasses.field(default_factory=dict))
    """Parameters for obstore store initialization."""
    url: str = ""
    """URL of obstore store."""
    store: obstore.store.ObjectStore = None  # pyright: ignore[reportAssignmentType]
    """Existing obstore store."""

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        self.path = self.path.strip("/")

        if not self.store:
            if not self.url:
                raise fk.exc.MissingStorageConfigurationError(self.name, "url")

            try:
                self.store = obstore.store.from_url(self.url, **self.params)
            except ValueError as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    str(err),
                ) from err


class Uploader(fk.Uploader):
    """FsSpec uploader."""

    storage: ObjectStoreStorage
    capabilities: fk.Capability = fk.Capability.CREATE

    @override
    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        store = self.storage.settings.store
        filepath = self.storage.full_path(location)

        if not self.storage.settings.override_existing:
            try:
                store.head(filepath)
            except FileNotFoundError:
                pass
            else:
                raise fk.exc.ExistingFileError(self.storage, location)

        with obstore.open_writer(store, filepath) as fobj:
            reader = upload.hashing_reader()
            for chunk in reader:
                fobj.write(chunk)

        return fk.FileData(
            location=location,
            size=reader.position,
            content_type=upload.content_type,
            hash=reader.get_hash(),
        )


class Reader(fk.Reader):
    """FsSpec reader."""

    storage: ObjectStoreStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        store = self.storage.settings.store
        filepath = self.storage.full_path(data.location)

        try:
            resp = store.get(filepath)
            return resp.stream()

        except FileNotFoundError as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err


class Manager(fk.Manager):
    """FsSpec manager."""

    storage: ObjectStoreStorage
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
        store = self.storage.settings.store

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(fk.FileData(location), extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        src_location = self.storage.full_path(data.location)
        dest_location = self.storage.full_path(location)

        store.copy(src_location, dest_location, overwrite=self.storage.settings.override_existing)

        return fk.FileData.from_object(data, location=location)

    @override
    def move(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        store = self.storage.settings.store

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(fk.FileData(location), extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        src_location = self.storage.full_path(data.location)
        dest_location = self.storage.full_path(location)

        store.rename(src_location, dest_location, overwrite=self.storage.settings.override_existing)

        return fk.FileData.from_object(data, location=location)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        store = self.storage.settings.store
        try:
            store.head(filepath)
        except FileNotFoundError:
            return False

        return True

    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
        try:
            src = self.storage.stream(fk.FileData(location), **extras)
        except FileNotFoundError as err:
            raise fk.exc.MissingFileError(self.storage, location) from err

        reader = fk.HashingReader(fk.IterableBytesReader(src))
        content_type = magic.from_buffer(next(reader, b""), True)
        reader.exhaust()

        return fk.FileData(location, size=reader.position, content_type=content_type, hash=reader.get_hash())

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        store = self.storage.settings.store

        if not self.exists(data, extras):
            return False

        store.delete(filepath)
        return True

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.full_path(fk.Location(""))

        store = self.storage.settings.store

        for info in store.list(path):  # pyright: ignore[reportUnknownVariableType]
            for name in self._scan_unwrap(info):
                yield os.path.relpath(name, path)

    def _scan_unwrap(self, info: Any) -> Iterable[str]:
        if isinstance(info, str):
            yield info
        elif isinstance(info, dict):
            yield info["path"]

        elif isinstance(info, list):
            for item in info:  # pyright: ignore[reportUnknownVariableType]
                yield from self._scan_unwrap(item)


class ObjectStoreStorage(fk.Storage):
    """Obstore storage adapter.

    This storage uses the [obstore](https://pypi.org/project/obstore/) library to provide
    access to various object storage backends. It supports any backend supported by
    obstore, including local filesystem, S3, Google Cloud Storage, Azure Blob Storage,
    and more.

    To use this storage, you need to provide the `url` setting in the configuration,
    which specifies the URL of the object store. The URL should be in the format
    supported by obstore. For example, to use a local filesystem as the
    object store, you can use the `file:///path/to/directory` URL.


    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:obstore",
        "url": "file:///tmp/file-keeper",
    }

    storage = fk.make_storage("obstore", settings)
    ```

    Note:
    * The `url` setting is required unless an existing `store` is provided.
    * The `params` setting is optional and can be used to provide additional parameters
      to the `obstore.store.from_url` function.
    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader

    @override
    def compute_capabilities(self) -> fk.Capability:
        return super().compute_capabilities()
