"""Google Cloud Storage adapter."""

from __future__ import annotations

import base64
import dataclasses
import os
import re
from collections.abc import Iterable
from datetime import timedelta
from http import HTTPStatus
from typing import Any, cast

import urllib3
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
        self.path = self.path.strip("/")

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

    capabilities: fk.Capability = fk.Capability.CREATE | fk.Capability.RESUMABLE

    @override
    def upload(self, location: fk.types.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
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

    def _resumable_complete(self, data: fk.FileData, info: dict[str, Any]):
        """Finalize a resumable upload session."""
        # size is returned as a string
        size = int(info["size"])
        if data.size and data.size != size:
            raise fk.exc.UploadSizeMismatchError(size, data.size)

        filehash = decode(info["md5Hash"])
        if data.hash and data.hash != filehash:
            raise fk.exc.UploadHashMismatchError(filehash, data.hash)

        content_type = info["contentType"]
        if data.content_type and data.content_type != content_type:
            raise fk.exc.UploadTypeMismatchError(content_type, data.content_type)

        result = fk.FileData.from_object(data, size=size, content_type=content_type, hash=hash)
        result.storage_data.pop("gcs_resumable")
        result.storage_data.pop("resumable")
        return result

    @override
    def resumable_start(self, location: fk.Location, size: int, extras: dict[str, Any]) -> fk.FileData:
        """Start a resumable upload session.

        [Google Cloud
        Documentation](https://cloud.google.com/storage/docs/performing-resumable-uploads#initiate-session)
        contains detailed description of the process.

        Accepts additional extras:

        * origin: If set, the upload can only be completed by a user-agent that
            uploads from the given origin. This can be useful when passing the
            session to a web client.

        """
        filepath = self.storage.full_path(location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(filepath)

        params = {k: extras[k] for k in ["content_type", "origin"] if k in extras}

        url = cast("str | None", blob.create_resumable_upload_session(size=size, **params))

        if not url:
            msg = "Cannot initialize session URL"
            raise fk.exc.ResumableUploadError(msg)

        return fk.FileData.from_dict(
            extras,
            location=location,
            size=size,
            storage_data={
                "gcs_resumable": {"session_url": url, "uploaded": 0, "origin": extras.get("origin")},
                "resumable": True,
            },
        )

    @override
    def resumable_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:  # noqa: C901
        if not data.storage_data.get("resumable"):
            msg = "Not a resumable data"
            raise fk.exc.StorageDataError(msg)

        session_url: str | None = data.storage_data.get("gcs_resumable", {}).get("session_url")

        if not session_url:
            msg = "`gcs_resumable.session_url` is missing"
            raise fk.exc.StorageDataError(msg)

        timeout = extras.get("request_timeout", 10)
        resp = urllib3.request(
            "PUT",
            session_url,
            headers={
                "content-range": f"bytes */{data.size}",
                "content-length": "0",
            },
            timeout=timeout,
        )

        if resp.status in [HTTPStatus.GONE, HTTPStatus.NOT_FOUND]:
            raise fk.exc.MissingFileError(self.storage, data.location)

        if resp.status in [HTTPStatus.OK, HTTPStatus.CREATED]:
            return self._resumable_complete(data, resp.json())

        if resp.status != HTTPStatus.PERMANENT_REDIRECT:
            msg = f"Unexpected status code {resp.status}"
            raise fk.exc.ResumableUploadError(msg, resp)

        result = fk.FileData.from_object(data)
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
            result.storage_data["gcs_resumable"]["uploaded"] = int(range_match.group("last_byte")) + 1
        else:
            result.storage_data["gcs_resumable"]["uploaded"] = 0

        return data

    @override
    def resumable_resume(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        gcs_data = data.storage_data["gcs_resumable"]

        first_byte = gcs_data["uploaded"]
        last_byte = first_byte + upload.size - 1
        size = data.size

        if last_byte >= size:
            raise fk.exc.UploadOutOfBoundError(last_byte, size)

        if last_byte + 1 != size and upload.size < 256 * 1024:
            msg = "Only the final part can be smaller than 256KiB"
            raise fk.exc.ResumableUploadError(msg)

        resp = urllib3.request(
            "PUT",
            gcs_data["session_url"],
            body=upload.stream.read(),
            headers={
                "content-range": f"bytes {first_byte}-{last_byte}/{size}",
            },
            timeout=extras.get("request_timeout", 10),
        )

        if resp.status in [HTTPStatus.OK, HTTPStatus.CREATED]:
            return self._resumable_complete(data, resp.json())

        if resp.status != HTTPStatus.PERMANENT_REDIRECT:
            msg = f"Cannot resume upload: {resp.status} {resp.data}"
            raise fk.exc.ResumableUploadError(msg, resp)

        range_match = RE_RANGE.match(resp.headers["range"])
        if not range_match:
            msg = "Invalid response from Google Cloud"
            raise fk.exc.ResumableUploadError(msg)

        result = fk.FileData.from_object(data)
        result.storage_data["gcs_resumable"]["uploaded"] = int(range_match.group("last_byte")) + 1

        return result

    @override
    def resumable_remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        gcs_data = data.storage_data["gcs_resumable"]
        resp = urllib3.request("DELETE", gcs_data["session_url"])
        cancel_status = 499
        return resp.status == cancel_status


class Reader(fk.Reader):
    """GCS Reader."""

    storage: GoogleCloudStorage

    capabilities = fk.Capability.STREAM | fk.Capability.LINK_PERMANENT

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
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
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"

        bucket = self.storage.settings.bucket

        for blob in cast(Iterable[Blob], bucket.list_blobs(prefix=path)):
            name: str = cast(str, blob.name)
            yield os.path.relpath(name, path)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        bucket = self.storage.settings.bucket
        blob = bucket.blob(filepath)
        return blob.exists()

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
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
    """Google Cloud Storage adapter.

    Example configuration:
    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:gcs",
        "bucket_name": "my-bucket",
        "path": "uploads",
        "credentials_file": "/path/to/credentials.json",
        "project_id": "my-project-id",
        "override_existing": False,
        "initialize": True,
    }

    storage = fk.make_storage("gcss", settings)
    ```

    Note:
    * `credentials_file` or `credentials` along with `project_id` are required
      to initialize the storage client.
    * If `initialize` is set to `True`, the bucket will be created if it
        does not exist.

    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
