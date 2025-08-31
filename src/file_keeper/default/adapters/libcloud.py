"""Apache Libcloud adapter."""

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
    """Libcloud settings."""

    provider: str = ""
    key: str = ""
    """Access key of the cloud account."""

    secret: str | None = None
    """Secret key of the cloud account."""

    container_name: str = ""
    """Name of the cloud container."""
    params: dict[str, Any] = cast("dict[str, Any]", dataclasses.field(default_factory=dict))
    """Additional parameters for cloud provider."""

    public_prefix: str = ""
    """Root URL for containers with public access."""

    driver: StorageDriver = None  # pyright: ignore[reportAssignmentType]
    """Existing storage driver."""
    container: Container = None  # pyright: ignore[reportAssignmentType]
    """Existing container object."""

    def __post_init__(
        self,
        **kwargs: Any,
    ):
        super().__post_init__(**kwargs)

        # leading slash generally does not break anything, but SCAN relies on
        # method that does not work with leading slash. That's why it's
        # stripped, which shouldn't be a problem as libcloud automatically
        # strips it in majority of operations anyway.
        self.path = self.path.strip("/")

        if self.driver is None:  # pyright: ignore[reportUnnecessaryComparison]
            try:
                make_driver = get_driver(DriverType.STORAGE, self.provider)
            except AttributeError as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    str(err),
                ) from err

            self.driver = make_driver(self.key, self.secret, **self.params)

        if self.container is None:  # pyright: ignore[reportUnnecessaryComparison]
            try:
                self.container = self.driver.get_container(self.container_name)

            except ContainerDoesNotExistError as err:
                if self.initialize:
                    self.container = self.driver.create_container(self.container_name)
                else:
                    raise fk.exc.InvalidStorageConfigurationError(
                        self.name, f"container {self.container_name} does not exist"
                    ) from err

            except (LibcloudError, requests.RequestException) as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    str(err),
                ) from err


class Uploader(fk.Uploader):
    """Libcloud uploader."""

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
    """Libcloud reader."""

    storage: LibCloudStorage
    capabilities: fk.Capability = fk.Capability.STREAM | fk.Capability.LINK_PERMANENT

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
    """Libcloud manager."""

    storage: LibCloudStorage
    capabilities: fk.Capability = (
        fk.Capability.SCAN | fk.Capability.REMOVE | fk.Capability.EXISTS | fk.Capability.ANALYZE
    )

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"

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
        location = self.storage.full_path(data.location)

        try:
            self.storage.settings.container.get_object(location)
        except ObjectDoesNotExistError:
            return False

        return True

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        fullpath = self.storage.full_path(location)

        try:
            obj = self.storage.settings.container.get_object(fullpath)
        except ObjectDoesNotExistError as err:
            raise fk.exc.MissingFileError(self.storage, location) from err

        content_type: str = obj.extra.get("content_type", fk.FileData.content_type)  # pyright: ignore[reportUnknownVariableType]
        hash = obj.hash.strip('"')
        return fk.FileData(location, obj.size, content_type, hash)


class LibCloudStorage(fk.Storage):
    """Libcloud storage adapter.

    This adapter uses [Apache Libcloud](https://libcloud.apache.org/) to connect to
    various cloud storage providers. It supports any provider implemented in Libcloud,
    such as Amazon S3, Google Cloud Storage, Azure Blob Storage, and many others.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:libcloud",
        "name": "my_libcloud_storage",
        "provider": "S3",  # or "GOOGLE_STORAGE", "AZURE_BLOBS", etc.
        "key": "<access key>",
        "secret": "<secret key>",
        "container_name": "file-keeper",
        "params": {
            "region": "us-west-1",  # provider-specific parameters
        },
        "public_prefix": "https://my-bucket.s3.amazonaws.com/",  # optional, if provider supports public links
        "path": "uploads/",
        "override_existing": False,
        "initialize": True,
    }

    storage = fk.make_storage("libcloud", settings)
    ```

    Note:
    * Ensure that the `provider` field matches one of the supported Libcloud storage providers.
    * The `params` field can include any additional parameters required by the specific provider.
    * If `public_prefix` is not set, permanent links will not be available.
    * The `initialize` flag allows automatic creation of the container if it does not exist.
    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader

    @override
    def compute_capabilities(self) -> fk.Capability:
        cluster = super().compute_capabilities()
        if not self.settings.public_prefix:
            cluster = cluster.exclude(fk.Capability.LINK_PERMANENT)

        return cluster
