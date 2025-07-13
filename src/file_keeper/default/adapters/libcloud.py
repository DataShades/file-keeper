from __future__ import annotations

import os
import dataclasses
import requests
from typing import Any, ClassVar, Iterable

from libcloud.base import DriverType, get_driver  # type: ignore
from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container, StorageDriver
from libcloud.storage.types import ContainerDoesNotExistError, ObjectDoesNotExistError

import file_keeper as fk

get_driver: Any


@dataclasses.dataclass()
class Settings(fk.Settings):
    provider: str = ""
    key: str = ""
    container_name: str = ""

    path: str = ""

    secret: str | None = None
    params: dict[str, Any] = dataclasses.field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]

    public_prefix: str = ""

    driver: StorageDriver = None  # type: ignore
    container: Container = None  # type: ignore

    _required_options: ClassVar[list[str]] = ["provider", "key", "container_name"]

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        try:
            make_driver = get_driver(DriverType.STORAGE, self.provider)
        except AttributeError as err:
            raise fk.exc.InvalidStorageConfigurationError(
                self.name,
                str(err),
            ) from err

        self.driver = make_driver(self.key, self.secret, **self.params)

        try:
            self.container = self.driver.get_container(self.container_name)

        except ContainerDoesNotExistError as err:
            msg = f"Container {self.container_name} does not exist"
            raise fk.exc.InvalidStorageConfigurationError(self.name, msg) from err

        except (LibcloudError, requests.RequestException) as err:
            raise fk.exc.InvalidStorageConfigurationError(
                self.name,
                str(err),
            ) from err


class Uploader(fk.Uploader):
    storage: LibCloudStorage
    capabilities = fk.Capability.CREATE

    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        dest = os.path.join(self.storage.settings.path, location)

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
    capabilities = fk.Capability.STREAM | fk.Capability.PERMANENT_LINK

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        location = os.path.join(self.storage.settings.path, data.location)

        try:
            obj = self.storage.settings.container.get_object(location)
        except ObjectDoesNotExistError as err:
            raise fk.exc.MissingFileError(
                self.storage,
                data.location,
            ) from err

        return obj.as_stream()

    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        location = os.path.join(self.storage.settings.path, data.location)
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
    capabilities = fk.Capability.SCAN | fk.Capability.REMOVE

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        for item in self.storage.settings.container.iterate_objects(
            prefix=path
        ):
            yield os.path.relpath(item.name, path)

    def remove(
        self,
        data: fk.FileData | fk.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        location = os.path.join(self.storage.settings.path, data.location)

        try:
            obj = self.storage.settings.container.get_object(location)
        except ObjectDoesNotExistError:
            return False
        return self.storage.settings.container.delete_object(obj)


class LibCloudStorage(fk.Storage):
    settings: Settings  # type: ignore
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader

    def compute_capabilities(self) -> fk.Capability:
        cluster = super().compute_capabilities()
        if not self.settings.public_prefix:
            cluster = cluster.exclude(fk.Capability.PERMANENT_LINK)

        return cluster
