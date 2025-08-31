"""Azure Blob Storage adapter."""

from __future__ import annotations

import codecs
import dataclasses
import os
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import (
    BlobBlock,
    BlobSasPermissions,
    BlobServiceClient,
    ContainerClient,
    ContentSettings,
    generate_blob_sas,
)
from typing_extensions import override

import file_keeper as fk


@dataclasses.dataclass
class Settings(fk.Settings):
    """Azure Blob Storage settings."""

    account_name: str | None = None
    """Name of the account."""
    account_key: str = ""
    """Key for the account."""

    account_url: str = "https://{account_name}.blob.core.windows.net"
    """Custom resource URL."""
    ## azurite
    # account_url: str = "http://127.0.0.1:10000/{account_name}"

    client: BlobServiceClient = None  # pyright: ignore[reportAssignmentType]
    """Existing storage client."""

    container_name: str = ""
    """Name of the storage container."""

    container: ContainerClient = None  # pyright: ignore[reportAssignmentType]
    """Existing container client."""

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        self.path = self.path.strip("/")

        if not self.client:
            if self.account_name:
                self.account_url = self.account_url.format(account_name=self.account_name)
                credential = {
                    "account_name": self.account_name,
                    "account_key": self.account_key,
                }
            elif self.account_key:
                credential = self.account_key
            else:
                credential = None

            self.client = BlobServiceClient(
                self.account_url,
                credential,
            )

        self.account_url = self.client.url.rstrip("/")
        self.account_name = self.client.account_name

        if not self.container:
            self.container = self.client.get_container_client(self.container_name)
        self.container_name = self.container.container_name

        if not self.container.exists():
            if self.initialize:
                self.container.create_container()
            else:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    f"container `{self.container_name}` does not exist",
                )


class Uploader(fk.Uploader):
    """Azure Blob Storage uploader.

    Supports single-part and multipart uploads.
    """

    storage: AzureBlobStorage
    capabilities = fk.Capability.CREATE | fk.Capability.MULTIPART

    @override
    def upload(self, location: fk.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        blob = self.storage.settings.container.get_blob_client(filepath)

        if not self.storage.settings.override_existing and blob.exists():
            raise fk.exc.ExistingFileError(self.storage, location)

        result = blob.upload_blob(
            upload.stream,
            overwrite=True,
            content_settings=ContentSettings(content_type=upload.content_type),
        )

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            codecs.encode(result["content_md5"], "hex").decode(),
        )

    @override
    def multipart_start(self, location: fk.Location, size: int, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData.from_dict(
            extras,
            location=location,
            size=size,
            storage_data={"multipart": True, "parts": {}, "uploaded": 0},
        )

    @override
    def multipart_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)
        blob = self.storage.settings.container.get_blob_client(filepath)

        try:
            blocks = blob.get_block_list("uncommitted")[1]
        except ResourceNotFoundError as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err

        storage_data = {}
        if blocks:
            parts = {}
            uploaded = 0
            for idx, block in enumerate(blocks):
                parts[idx] = block["id"]
                uploaded += block["size"]

            storage_data.update(multipart=True, parts=parts, uploaded=uploaded)
        return fk.FileData.from_object(data, storage_data=storage_data)

    @override
    def multipart_remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        blob_client = self.storage.settings.container.get_blob_client(filepath)
        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            return False

        return True

    @override
    def multipart_complete(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)
        blob = self.storage.settings.container.get_blob_client(filepath)

        if data.size != data.storage_data["uploaded"]:
            raise fk.exc.UploadSizeMismatchError(data.storage_data["uploaded"], data.size)

        blob.commit_block_list([BlobBlock(item[1]) for item in sorted(data.storage_data["parts"].items())])

        return fk.FileData.from_object(data, storage_data={})

    @override
    def multipart_update(self, data: fk.FileData, upload: fk.Upload, part: int, extras: dict[str, Any]) -> fk.FileData:
        size = data.storage_data["uploaded"] + upload.size
        if size > data.size:
            raise fk.exc.UploadOutOfBoundError(size, data.size)

        filepath = self.storage.full_path(data.location)
        blob = self.storage.settings.container.get_blob_client(filepath)

        block_id = uuid.uuid4().hex
        blob.stage_block(block_id, upload.stream)

        result = fk.FileData.from_object(data)
        result.storage_data["parts"][part] = block_id
        result.storage_data["uploaded"] = size
        return result


class Reader(fk.Reader):
    """Azure Blob Storage reader.

    Supports streaming and permanent links.
    """

    storage: AzureBlobStorage
    capabilities = fk.Capability.STREAM | fk.Capability.LINK_PERMANENT

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        filepath = self.storage.full_path(data.location)

        blob = self.storage.settings.container.get_blob_client(filepath)
        if not blob.exists():
            raise fk.exc.MissingFileError(self.storage, data.location)

        return blob.download_blob().chunks()

    @override
    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        account_url = self.storage.settings.account_url
        container = self.storage.settings.container
        filepath = self.storage.full_path(data.location)

        return f"{account_url}/{container.container_name}/{filepath}"


class Manager(fk.Manager):
    """Azure Blob Storage manager."""

    storage: AzureBlobStorage
    capabilities = (
        fk.Capability.REMOVE
        | fk.Capability.SIGNED
        | fk.Capability.EXISTS
        | fk.Capability.SCAN
        | fk.Capability.ANALYZE
        | fk.Capability.COPY
        | fk.Capability.MOVE
    )

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        src_filepath = self.storage.full_path(data.location)
        blob = self.storage.settings.container.get_blob_client(src_filepath)
        if not blob.exists():
            raise fk.exc.MissingFileError(self.storage, data.location)

        dest_filepath = self.storage.full_path(location)
        dest = self.storage.settings.container.get_blob_client(dest_filepath)
        if not self.storage.settings.override_existing and dest.exists():
            raise fk.exc.ExistingFileError(self.storage, location)

        account_url = self.storage.settings.account_url
        container_name = self.storage.settings.container_name
        url = f"{account_url}/{container_name}/{src_filepath}"
        dest.start_copy_from_url(url)
        return self.analyze(location, extras)

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        self.copy(location, data, extras)
        self.remove(data, extras)
        return self.analyze(location, extras)

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        blob = self.storage.settings.container.get_blob_client(filepath)
        if not blob.exists():
            raise fk.exc.MissingFileError(self.storage, location)

        info = blob.get_blob_properties()
        content_info = info["content_settings"]
        return fk.FileData(
            location,
            info["size"],
            content_info["content_type"],
            codecs.encode(content_info["content_md5"], "hex").decode(),
        )

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        blob_client = self.storage.settings.container.get_blob_client(filepath)
        return blob_client.exists()

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"

        for name in self.storage.settings.container.list_blob_names(name_starts_with=path):
            yield os.path.relpath(name, path)

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        blob_client = self.storage.settings.container.get_blob_client(filepath)
        if not blob_client.exists():
            return False

        blob_client.delete_blob()
        return True

    @override
    def signed(self, action: fk.types.SignedAction, duration: int, location: fk.Location, extras: dict[str, Any]):
        """Generate a signed URL for a file.

        Upload requires `x-ms-blob-type: BlockBlob` header.
        """
        perms = {}
        if action == "download":
            perms["read"] = True
        elif action == "upload":
            perms["write"] = True
            perms["create"] = True
        elif action == "delete":
            perms["delete"] = True

        client = self.storage.settings.client
        container = self.storage.settings.container
        filepath = self.storage.full_path(location)

        start_time = datetime.now(timezone.utc)
        expiry_time = start_time + timedelta(seconds=duration)

        sas = generate_blob_sas(
            account_name=client.account_name,  # pyright: ignore[reportArgumentType]
            account_key=self.storage.settings.account_key,
            container_name=container.container_name,
            blob_name=filepath,
            permission=BlobSasPermissions(**perms),
            expiry=expiry_time,
        )
        account_url = self.storage.settings.account_url

        return f"{account_url}/{container.container_name}/{filepath}?{sas}"


class AzureBlobStorage(fk.Storage):
    """Azure Blob Storage adapter.

    Uses `azure-storage-blob <https://pypi.org/project/azure-storage-blob/>`_
    package. Make sure to install it first.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:azure_blob",
        "account_name": "<account_name>",
        "account_key": "<account_key>",
        "container_name": "<container_name>",
        "path": "optional/path/prefix",
        "initialize": True,  # create container if it does not exist
        ## uncomment following line to use azurite running on 10000 port
        "account_url": "http://127.0.0.1:10000/{account_name}",
    }
    storage = fk.make_storage("azure", settings)
    ```

    Note:
    * `account_name` and `account_key` are required unless you provide an existing
      `client` instance.
    * `container_name` is required.
    * `account_url` is optional and defaults to Azure public cloud. You can use it
      to point to a different cloud or a local emulator like azurite.
    * `path` is optional and can be used to prefix all file locations.
    * `initialize` controls whether the container should be created if it does not
      exist. Defaults to `False`.
    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
