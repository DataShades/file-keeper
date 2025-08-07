from __future__ import annotations

import contextlib
import dataclasses
import os
from collections.abc import Iterable
from typing import Any, cast

import requests
from libcloud.base import (
    DriverType,
    get_driver,  # pyright: ignore[reportUnknownVariableType]
)
from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container, StorageDriver
from libcloud.storage.types import ContainerDoesNotExistError, ObjectDoesNotExistError
from typing_extensions import override

import file_keeper as fk

get_driver: Any


@dataclasses.dataclass()
class Settings(fk.Settings):
    provider: dataclasses.InitVar[str] = ""
    key: dataclasses.InitVar[str] = ""
    container_name: dataclasses.InitVar[str] = ""

    secret: dataclasses.InitVar[str | None] = None
    params: dataclasses.InitVar[dict[str, Any] | None] = cast("dict[str, Any] | None", dataclasses.field(default=None))

    public_prefix: str = ""

    driver: StorageDriver = None  # pyright: ignore[reportAssignmentType]
    container: Container = None  # pyright: ignore[reportAssignmentType]

    def __post_init__(
        self,
        provider: str,
        key: str,
        container_name: str,
        secret: str | None,
        params: dict[str, Any] | None,
        **kwargs: Any,
    ):
        super().__post_init__(**kwargs)

        if self.driver is None:  # pyright: ignore[reportUnnecessaryComparison]
            try:
                make_driver = get_driver(DriverType.STORAGE, provider)
            except AttributeError as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    str(err),
                ) from err

            if params is None:
                params = {}
            self.driver = make_driver(key, secret, **params)

        if self.container is None:  # pyright: ignore[reportUnnecessaryComparison]
            try:
                self.container = self.driver.get_container(container_name)

            except ContainerDoesNotExistError as err:
                if self.initialize:
                    self.container = self.driver.create_container(container_name)
                else:
                    raise fk.exc.InvalidStorageConfigurationError(
                        self.name, f"container {container_name} does not exist"
                    ) from err

            except (LibcloudError, requests.RequestException) as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    str(err),
                ) from err


class Uploader(fk.Uploader):
    storage: LibCloudStorage
    capabilities: fk.Capability = fk.Capability.CREATE

    @override
    def upload(self, location: fk.types.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        dest = self.storage.full_path(location)

        if not self.storage.settings.override_existing:
            with contextlib.suppress(ObjectDoesNotExistError):
                self.storage.settings.container.get_object(dest)
                raise fk.exc.ExistingFileError(self.storage, location)

        result = self.storage.settings.container.upload_object_via_stream(
            iter(upload.stream),
            dest,
            extra={"content_type": upload.content_type},
        )

        return fk.FileData(
            location,
            result.size,
            upload.content_type,
            result.hash.strip('"'),
        )


class Reader(fk.Reader):
    storage: LibCloudStorage
    capabilities: fk.Capability = fk.Capability.STREAM | fk.Capability.PERMANENT_LINK

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        location = self.storage.full_path(data.location)

        try:
            obj = self.storage.settings.container.get_object(location)
        except ObjectDoesNotExistError as err:
            raise fk.exc.MissingFileError(
                self.storage,
                data.location,
            ) from err

        return obj.as_stream()

    @override
    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        location = self.storage.full_path(data.location)
        return os.path.join(self.storage.settings.public_prefix, location)

        # try:
        #     obj = self.storage.settings.container.get_object(location)
        # except ObjectDoesNotExistError as err:
        #     raise fk.exc.MissingFileError(
        #         self.storage,
        #         data.location,
        #     ) from err

        # return self.storage.settings.driver.get_object_cdn_url(obj)


class Manager(fk.Manager):
    storage: LibCloudStorage
    capabilities: fk.Capability = (
        fk.Capability.SCAN | fk.Capability.REMOVE | fk.Capability.EXISTS | fk.Capability.ANALYZE
    )

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        for item in self.storage.settings.container.iterate_objects(prefix=path):
            yield os.path.relpath(item.name, path)

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        location = self.storage.full_path(data.location)

        try:
            obj = self.storage.settings.container.get_object(location)
        except ObjectDoesNotExistError:
            return False
        return self.storage.settings.container.delete_object(obj)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        try:
            self.storage.settings.container.get_object(data.location)
        except ObjectDoesNotExistError:
            return False

        return True

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        try:
            obj = self.storage.settings.container.get_object(location)
        except ObjectDoesNotExistError as err:
            raise fk.exc.MissingFileError(self.storage, location) from err

        # TODO: identify content type
        return fk.FileData(location, obj.size, hash=obj.hash)


class LibCloudStorage(fk.Storage):
    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader

    @override
    def compute_capabilities(self) -> fk.Capability:
        cluster = super().compute_capabilities()
        if not self.settings.public_prefix:
            cluster = cluster.exclude(fk.Capability.PERMANENT_LINK)

        return cluster
