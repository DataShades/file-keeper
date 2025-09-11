"""AWS S3 adapter."""

from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import urlparse, urlunparse

import boto3
from typing_extensions import override

import file_keeper as fk

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import CreateMultipartUploadRequestTypeDef

RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")
HTTP_RESUME = 308


@dataclasses.dataclass()
class Settings(fk.Settings):
    """AWS S3 settings."""

    bucket: str = ""
    """Name of the storage bucket."""
    client: S3Client = None  # pyright: ignore[reportAssignmentType]
    """Existing S3 client."""
    key: str | None = None
    """The AWS Access Key."""
    secret: str | None = None
    """The AWS Secret Key."""
    region: str | None = None
    """AWS Region of the bucket."""
    endpoint: str | None = None
    """Custom AWS endpoint."""

    _required_options: ClassVar[list[str]] = ["bucket"]

    def __post_init__(
        self,
        **kwargs: Any,
    ):
        super().__post_init__(**kwargs)

        # leading slash generally does not break anything, but SCAN relies on
        # method that does not work with leading slash. That's why it's
        # stripped, which shouldn't be a problem as boto3 automatically strips
        # it in majority of operations anyway.
        self.path = self.path.strip("/")

        if self.client is None:  # pyright: ignore[reportUnnecessaryComparison]
            self.client = boto3.client(
                "s3",
                aws_access_key_id=self.key,
                aws_secret_access_key=self.secret,
                region_name=self.region,
                endpoint_url=self.endpoint,
            )

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except self.client.exceptions.ClientError as err:
            if self.initialize:
                self.client.create_bucket(Bucket=self.bucket)
            else:
                raise fk.exc.InvalidStorageConfigurationError(
                    self.name, f"container {self.bucket} does not exist"
                ) from err


class Reader(fk.Reader):
    """AWS S3 reader."""

    storage: S3Storage
    capabilities: fk.Capability = fk.Capability.STREAM | fk.Capability.LINK_PERMANENT

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        client = self.storage.settings.client
        filepath = self.storage.full_path(data.location)

        try:
            obj: Any = client.get_object(Bucket=self.storage.settings.bucket, Key=filepath)
        except client.exceptions.NoSuchKey as err:
            raise fk.exc.MissingFileError(
                self.storage.settings.name,
                data.location,
            ) from err

        return obj["Body"]

    @override
    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        name = self.storage.full_path(data.location)
        signed = self.storage.settings.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.storage.settings.bucket, "Key": name}
        )

        return urlunparse(urlparse(signed)._replace(query=None))


class Uploader(fk.Uploader):
    """AWS S3 uploader."""

    storage: S3Storage

    capabilities: fk.Capability = fk.Capability.CREATE | fk.Capability.MULTIPART

    @override
    def upload(self, location: fk.types.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        if not self.storage.settings.override_existing and self.storage.exists(fk.FileData(location), **extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        filepath = self.storage.full_path(location)

        client = self.storage.settings.client

        obj = client.put_object(
            Bucket=self.storage.settings.bucket,
            Key=filepath,
            Body=upload.stream,  # pyright: ignore[reportArgumentType]
            ContentType=upload.content_type,
        )

        filehash = obj["ETag"].strip('"')

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            filehash,
        )

    def _presigned_part(self, key: str, upload_id: str, part: int):
        """Generate a presigned URL for uploading a part."""
        return self.storage.settings.client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self.storage.settings.bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part,
            },
        )

    @override
    def multipart_start(self, location: fk.Location, size: int, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        client = self.storage.settings.client

        params: CreateMultipartUploadRequestTypeDef = {
            "Bucket": self.storage.settings.bucket,
            "Key": filepath,
        }
        if content_type := extras.get("content_type"):
            params["ContentType"] = content_type

        obj = client.create_multipart_upload(**params)

        return fk.FileData.from_dict(
            extras,
            location=location,
            size=size,
            storage_data={
                "multipart": True,
                "upload_id": obj["UploadId"],
                "uploaded": 0,
                "parts": {},
            },
        )

    @override
    def multipart_remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        client = self.storage.settings.client
        filepath = self.storage.full_path(data.location)

        resp = client.list_multipart_uploads(
            Bucket=self.storage.settings.bucket,
            Prefix=filepath,
            MaxUploads=1,
        )

        if "Uploads" in resp:
            client.abort_multipart_upload(
                Bucket=self.storage.settings.bucket,
                Key=filepath,
                UploadId=data.storage_data["upload_id"],
            )
            return True

        return False

    @override
    def multipart_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        client = self.storage.settings.client
        filepath = self.storage.full_path(data.location)

        marker = 0
        parts = {}
        uploaded = 0
        upload_id = data.storage_data.get("upload_id", "")
        try:
            while True:
                resp = client.list_parts(
                    Bucket=self.storage.settings.bucket,
                    Key=filepath,
                    UploadId=upload_id,
                    PartNumberMarker=marker,
                )

                if "Parts" not in resp:
                    break

                for item in resp["Parts"]:
                    if "PartNumber" not in item or "ETag" not in item:
                        continue

                    parts[item["PartNumber"] - 1] = item["ETag"].strip('"')
                    uploaded += item.get("Size", 0)

                marker = resp["NextPartNumberMarker"]
                if not marker:
                    break
        except client.exceptions.NoSuchUpload as err:
            raise fk.exc.MissingFileError(self.storage, data.location) from err

        return fk.FileData.from_object(
            data,
            storage_data={"multipart": True, "upload_id": upload_id, "uploaded": uploaded, "parts": parts},
        )

    @override
    def multipart_update(self, data: fk.FileData, upload: fk.Upload, part: int, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        first_byte = data.storage_data["uploaded"]
        last_byte = first_byte + upload.size

        size = data.size

        if last_byte > size:
            raise fk.exc.UploadOutOfBoundError(last_byte, size)

        if last_byte < size and upload.size < 1024 * 1024 * 5:
            msg = "Only the final part can be smaller than 5MiB"
            raise fk.exc.MultipartUploadError(msg)

        resp = self.storage.settings.client.upload_part(
            Bucket=self.storage.settings.bucket,
            Key=filepath,
            UploadId=data.storage_data["upload_id"],
            PartNumber=part + 1,
            Body=upload.stream,  # pyright: ignore[reportArgumentType]
        )

        etag = resp["ETag"].strip('"')
        data.storage_data["uploaded"] = data.storage_data["uploaded"] + upload.size

        data.storage_data["parts"][part] = etag

        return data

    @override
    def multipart_complete(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        if data.size != data.storage_data["uploaded"]:
            raise fk.exc.UploadSizeMismatchError(data.storage_data["uploaded"], data.size)

        result = self.storage.settings.client.complete_multipart_upload(
            Bucket=self.storage.settings.bucket,
            Key=filepath,
            UploadId=data.storage_data["upload_id"],
            MultipartUpload={
                "Parts": [{"PartNumber": int(num) + 1, "ETag": tag} for num, tag in data.storage_data["parts"].items()]
            },
        )

        obj = self.storage.settings.client.get_object(Bucket=self.storage.settings.bucket, Key=result["Key"])

        return fk.FileData(
            fk.types.Location(
                os.path.relpath(
                    result["Key"],
                    self.storage.settings.path,
                )
            ),
            obj["ContentLength"],
            obj["ContentType"],
            obj["ETag"].strip('"'),
        )


class Manager(fk.Manager):
    """AWS S3 manager."""

    storage: S3Storage

    capabilities: fk.Capability = (
        fk.Capability.REMOVE
        | fk.Capability.ANALYZE
        | fk.Capability.EXISTS
        | fk.Capability.SCAN
        | fk.Capability.MOVE
        | fk.Capability.COPY
        | fk.Capability.SIGNED
    )

    @override
    def signed(self, action: fk.types.SignedAction, duration: int, location: fk.Location, extras: dict[str, Any]):
        """Make an URL for signed action.

        This method uses `generate_presigned_url` internally, which does not
        support content restrictions. If you need to enforce content
        type/size/hash validation, consider `generate_presigned_post`.

        @inherit_doc
        """
        client = self.storage.settings.client
        method = {
            "download": "get_object",
            "upload": "put_object",
            "delete": "delete_object",
        }[action]

        key = self.storage.full_path(location)

        return client.generate_presigned_url(
            ClientMethod=method,
            Params={"Bucket": self.storage.settings.bucket, "Key": key},
            ExpiresIn=duration,
        )

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        client = self.storage.settings.client
        bucket = self.storage.settings.bucket

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(fk.FileData(location), extras):
            raise fk.exc.ExistingFileError(self.storage, location)

        old_key = self.storage.full_path(data.location)
        new_key = self.storage.full_path(location)

        client.copy_object(Bucket=bucket, CopySource={"Bucket": bucket, "Key": old_key}, Key=new_key)

        return self.analyze(location, extras)

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        result = self.copy(location, data, extras)
        self.remove(data, extras)

        return result

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        client = self.storage.settings.client
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"

        marker = ""

        while True:
            resp = client.list_objects(
                Bucket=self.storage.settings.bucket,
                Marker=marker,
                Prefix=path,
            )
            if "Contents" not in resp:
                break

            for item in resp["Contents"]:
                if "Key" not in item:
                    continue
                key = item["Key"]
                yield os.path.relpath(key, path)

            if "NextMarker" not in resp:
                break

            marker = resp["NextMarker"]

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        client = self.storage.settings.client

        try:
            client.get_object(Bucket=self.storage.settings.bucket, Key=filepath)
        except client.exceptions.NoSuchKey:
            return False

        return True

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        client = self.storage.settings.client

        try:
            client.head_object(Bucket=self.storage.settings.bucket, Key=filepath)
        except client.exceptions.ClientError:
            return False

        client.delete_object(Bucket=self.storage.settings.bucket, Key=filepath)

        return True

    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        client = self.storage.settings.client

        try:
            obj = client.get_object(Bucket=self.storage.settings.bucket, Key=filepath)
        except client.exceptions.NoSuchKey as err:
            raise fk.exc.MissingFileError(self.storage, filepath) from err

        return fk.FileData(
            location,
            size=obj["ContentLength"],
            content_type=obj["ContentType"],
            hash=obj["ETag"].strip('"'),
        )


class S3Storage(fk.Storage):
    """AWS S3 storage adapter.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:s3",
        "bucket": "my-bucket,
        "key": "<access key>",
        "secret": "<secret key>",
        "initialize": True,
        ## uncomment following line to use MinIO on port 9000
        # "endpoint": "http://127.0.0.1:9000/",
    }
    storage = fk.make_storage("s3", settings)
    ```

    Note:
    * The `bucket` option is required.
    * If `initialize` is set to `True`, the bucket will be created if it does not exist.
    * If `key` and `secret` are not provided, the default AWS credentials chain
      will be used.
    * The `path` option can be used to set a prefix within the bucket.
    * The `region` option can be used to set the AWS region for the bucket.
    * The `endpoint` option can be used to set a custom endpoint, e.g. for MinIO.
    * The `override_existing` option controls whether existing files can be overwritten.
    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
