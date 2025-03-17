from __future__ import annotations

import dataclasses
from typing import Any, ClassVar, Iterable

from libcloud.base import DriverType, get_driver
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

    secret: str | None = None
    params: dict[str, Any] = dataclasses.field(default_factory=dict)

    driver: StorageDriver = None  # type: ignore
    container: Container = None  # type: ignore

    _required_options: ClassVar[list[str]] = ["provider", "key", "container_name"]

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        try:
            make_driver = get_driver(DriverType.STORAGE, self.provider)
        except AttributeError as err:
            raise fk.exc.InvalidStorageConfigurationError(
                type(self),
                str(err),
            ) from err

        self.driver = make_driver(self.key, self.secret, **self.params)

        try:
            self.container = self.driver.get_container(self.container_name)

        except ContainerDoesNotExistError as err:
            msg = f"Container {self.container_name} does not exist"
            raise fk.exc.InvalidStorageConfigurationError(type(self), msg) from err

        except LibcloudError as err:
            raise fk.exc.InvalidStorageConfigurationError(
                type(self),
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
        result = self.storage.settings.container.upload_object_via_stream(
            iter(upload.stream),
            location,
            extra={"content_type": upload.content_type},
        )

        return fk.FileData(
            fk.types.Location(result.name),
            result.size,
            upload.content_type,
            result.hash.strip('"'),
        )


class Reader(fk.Reader):
    storage: LibCloudStorage
    capabilities = fk.Capability.STREAM | fk.Capability.TEMPORAL_LINK

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        try:
            obj = self.storage.settings.container.get_object(data.location)
        except ObjectDoesNotExistError as err:
            raise fk.exc.MissingFileError(
                self.storage,
                data.location,
            ) from err

        return obj.as_stream()


class Manager(fk.Manager):
    storage: LibCloudStorage
    capabilities = fk.Capability.SCAN | fk.Capability.REMOVE

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        for item in self.storage.settings.container.iterate_objects():
            yield item.name

    def remove(
        self,
        data: fk.FileData | fk.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        try:
            obj = self.storage.settings.container.get_object(data.location)
        except ObjectDoesNotExistError:
            return False
        return self.storage.settings.container.delete_object(obj)


class LibCloudStorage(fk.Storage):
    settings: Settings  # type: ignore
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
