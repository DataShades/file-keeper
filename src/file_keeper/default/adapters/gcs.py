"""Google Cloud Storage adapter."""

from __future__ import annotations

import base64
import dataclasses
import os
import re
from collections.abc import Iterable
from datetime import timedelta
from typing import Any, cast

import requests
from google.api_core.exceptions import Forbidden
from google.auth.credentials import Credentials
from google.cloud.storage import Blob, Bucket, Client
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from typing_extensions import override

import file_keeper as fk

RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")
HTTP_RESUME = 308


def decode(value: str) -> str:
    """Normalize base64-encoded md5-hash of file content."""
    return base64.decodebytes(value.encode()).hex()


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for GCS adapter."""

    bucket_name: str = ""
    """Name of the storage bucket."""
    client: Client = None  # pyright: ignore[reportAssignmentType]
    """Existing storage client."""
    bucket: Bucket = None  # pyright: ignore[reportAssignmentType]
    """Existing storage bucket."""

    credentials_file: str = ""
    """Path to the JSON with cloud credentials."""
    credentials: Credentials | None = None
    """Existing cloud credentials."""
    project_id: str = ""
    """The project which the client acts on behalf of."""

    client_options: dict[str, Any] | None = None
    """Client options for storage client."""

    def __post_init__(
        self,
        **kwargs: Any,
    ):
        super().__post_init__(**kwargs)

        # GCS ignores first slash and keeping it complicates work for
        # os.path.relpath
        self.path = self.path.lstrip("/")

        if not self.client:
            if not self.credentials and self.credentials_file:
                try:
                    self.credentials = ServiceAccountCredentials.from_service_account_file(self.credentials_file)
                except OSError as err:
                    raise fk.exc.InvalidStorageConfigurationError(
                        self.name,
                        f"file `{self.credentials_file}` does not exist",
                    ) from err
                if not self.project_id:
                    self.project_id = self.credentials.project_id or ""

            if not self.project_id:
                raise fk.exc.MissingStorageConfigurationError(self.name, "project_id")

            self.client = Client(
                self.project_id,
                credentials=self.credentials,
                client_options=self.client_options,
            )

        if not self.bucket:
            self.bucket = self.client.bucket(self.bucket_name)

        if not self.bucket.exists():
            if self.initialize:
                self.client.create_bucket(self.bucket_name)
            else:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name,
                    f"bucket `{self.bucket_name}` does not exist",
                )


class Uploader(fk.Uploader):
    """GCS Uploader."""

    storage: GoogleCloudStorage

    capabilities: fk.Capability = fk.Capability.CREATE

    @override
    def upload(self, location: fk.types.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        """Upload a file to GCS."""
        filepath = self.storage.full_path(location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(filepath)

        if not self.storage.settings.override_existing and blob.exists():
            raise fk.exc.ExistingFileError(self.storage, location)

        blob.upload_from_file(upload.stream, content_type=upload.content_type)

        filehash = decode(blob.md5_hash)
        return fk.FileData(
            location,
            blob.size or upload.size,
            upload.content_type,
            filehash,
        )

    @override
    def multipart_start(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Start a multipart upload session."""
        filepath = self.storage.full_path(data.location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(filepath)

        url = cast(
            str,
            blob.create_resumable_upload_session(size=data.size),
        )

        if not url:
            msg = "Cannot initialize session URL"
            raise fk.exc.UploadError(msg)

        result = fk.FileData.from_object(data)
        result.storage_data.update(
            {
                "session_url": url,
                "uploaded": 0,
            }
        )
        return result

    @override
    def multipart_update(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Update a multipart upload session."""
        if "upload" in extras:
            upload = fk.make_upload(extras["upload"])

            first_byte = extras.get("position", data.storage_data["uploaded"])
            last_byte = first_byte + upload.size - 1
            size = data.size

            if last_byte >= size:
                raise fk.exc.UploadOutOfBoundError(last_byte, size)

            if upload.size < 256 * 1024 and last_byte < size - 1:
                raise fk.exc.ExtrasError(
                    {"upload": ["Only the final part can be smaller than 256KiB"]},
                )

            try:
                resp = requests.put(
                    data.storage_data["session_url"],
                    data=upload.stream.read(),
                    headers={
                        "content-range": f"bytes {first_byte}-{last_byte}/{size}",
                    },
                    timeout=10,
                )
            except requests.exceptions.RequestException as e:
                msg = f"Failed to update upload: {e}"
                raise fk.exc.UploadError(msg) from e

            if not resp.ok:
                raise fk.exc.ExtrasError({"upload": [resp.text]})

            if "range" not in resp.headers:
                data.storage_data["uploaded"] = data.size
                data.storage_data["result"] = resp.json()
                return data

            range_match = RE_RANGE.match(resp.headers["range"])
            if not range_match:
                raise fk.exc.ExtrasError(
                    {"upload": ["Invalid response from Google Cloud"]},
                )
            data.storage_data["uploaded"] = int(range_match.group("last_byte")) + 1

        elif "uploaded" in extras:
            data.storage_data["uploaded"] = extras["uploaded"]

        else:
            raise fk.exc.ExtrasError(
                {"upload": ["Either upload or uploaded must be specified"]},
            )

        return data

    @override
    def multipart_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Refresh a multipart upload session."""
        if "session_url" not in data.storage_data:
            raise fk.exc.MissingFileError(self.storage, data.location)

        try:
            resp = requests.put(
                data.storage_data["session_url"],
                headers={
                    "content-range": f"bytes */{data.size}",
                    "content-length": "0",
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            msg = f"Failed to refresh upload: {e}"
            raise fk.exc.UploadError(msg) from e

        if not resp.ok:
            raise fk.exc.ExtrasError({"session_url": [resp.text]})

        if resp.status_code == HTTP_RESUME:
            if "range" in resp.headers:
                range_match = RE_RANGE.match(resp.headers["range"])
                if not range_match:
                    raise fk.exc.ExtrasError(
                        {
                            "session_url": [
                                "Invalid response from Google Cloud:" + " missing range header",
                            ],
                        },
                    )
                data.storage_data["uploaded"] = int(range_match.group("last_byte")) + 1
            else:
                data.storage_data["uploaded"] = 0
        elif resp.status_code in [200, 201]:
            data.storage_data["uploaded"] = data.size
            data.storage_data["result"] = resp.json()

        else:
            raise fk.exc.ExtrasError(
                {
                    "session_url": [
                        "Invalid response from Google Cloud:" + f" unexpected status {resp.status_code}",
                    ],
                },
            )

        return data

    @override
    def multipart_complete(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Complete a multipart upload session."""
        data = self.multipart_refresh(data, extras)
        if data.storage_data["uploaded"] != data.size:
            raise fk.exc.UploadSizeMismatchError(
                data.storage_data["uploaded"],
                data.size,
            )

        filehash = decode(data.storage_data["result"]["md5Hash"])
        if data.hash and data.hash != filehash:
            raise fk.exc.UploadHashMismatchError(filehash, data.hash)

        content_type = data.storage_data["result"]["contentType"]
        if data.content_type and content_type != data.content_type:
            raise fk.exc.UploadTypeMismatchError(content_type, data.content_type)

        return fk.FileData(
            fk.types.Location(
                os.path.relpath(
                    data.storage_data["result"]["name"],
                    self.storage.settings.path,
                )
            ),
            data.size,
            content_type,
            filehash,
        )


class Reader(fk.Reader):
    """GCS Reader."""

    storage: GoogleCloudStorage

    capabilities = fk.Capability.STREAM | fk.Capability.LINK_PERMANENT

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        """Stream a file from GCS."""
        name = self.storage.full_path(data.location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(name)

        if not blob.exists():
            raise fk.exc.MissingFileError(self.storage, data.location)

        with blob.open("rb") as stream:
            yield from cast(Iterable[bytes], stream)

    @override
    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        name = self.storage.full_path(data.location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(name)

        if not blob.exists():
            raise fk.exc.MissingFileError(self.storage, data.location)
        return blob.public_url


class Manager(fk.Manager):
    """GCS Manager."""

    storage: GoogleCloudStorage
    capabilities: fk.Capability = (
        fk.Capability.REMOVE
        | fk.Capability.SIGNED
        | fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.EXISTS
        | fk.Capability.ANALYZE
        | fk.Capability.SCAN
    )

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """Scan the storage for files."""
        bucket = self.storage.settings.bucket

        for blob in cast(Iterable[Blob], bucket.list_blobs()):
            name: str = cast(str, blob.name)
            yield os.path.relpath(name, self.storage.settings.path)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        """Check if a file exists in GCS."""
        filepath = self.storage.full_path(data.location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(filepath)
        return blob.exists()

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Move a file in GCS."""
        src_filepath = self.storage.full_path(data.location)
        dest_filepath = self.storage.full_path(location)

        bucket = self.storage.settings.bucket
        src_blob = bucket.blob(src_filepath)
        if not src_blob.exists():
            raise fk.exc.MissingFileError(self.storage, data.location)

        dest_blob = bucket.blob(dest_filepath)
        if not self.storage.settings.override_existing and dest_blob.exists():
            raise fk.exc.ExistingFileError(self.storage, location)

        bucket.rename_blob(src_blob, dest_filepath)
        return self.analyze(location, extras)

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Copy a file in GCS."""
        src_filepath = self.storage.full_path(data.location)
        dest_filepath = self.storage.full_path(location)

        bucket = self.storage.settings.bucket
        src_blob = bucket.blob(src_filepath)
        if not src_blob.exists():
            raise fk.exc.MissingFileError(self.storage, data.location)

        dest_blob = bucket.blob(dest_filepath)
        if not self.storage.settings.override_existing and dest_blob.exists():
            raise fk.exc.ExistingFileError(self.storage, location)

        bucket.copy_blob(src_blob, bucket, dest_filepath)
        return self.analyze(location, extras)

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(filepath)

        if not blob.exists():
            raise fk.exc.MissingFileError(self.storage, location)

        blob.reload()  # pull hash, type, size

        filehash = decode(blob.md5_hash)
        size = cast(int, blob.size)

        return fk.FileData(
            location,
            size,
            blob.content_type,
            filehash,
        )

    @override
    def signed(
        self, action: fk.types.SignedAction, duration: int, location: fk.Location, extras: dict[str, Any]
    ) -> str:
        name = self.storage.full_path(location)

        bucket = self.storage.settings.bucket
        blob = bucket.blob(name)

        method = {"download": "GET", "upload": "PUT", "delete": "DELETE"}[action]

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=duration),
            method=method,
        )

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        bucket = self.storage.settings.bucket

        blob = bucket.blob(filepath)

        try:
            exists = blob.exists()
        except Forbidden as err:
            raise fk.exc.PermissionError(
                self,
                "exists",
                str(err),
            ) from err

        if exists:
            try:
                blob.delete()
            except Forbidden as err:
                raise fk.exc.PermissionError(
                    self,
                    "remove",
                    str(err),
                ) from err
            return True
        return False


class GoogleCloudStorage(fk.Storage):
    """Google Cloud Storage adapter."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
