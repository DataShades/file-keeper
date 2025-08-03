from __future__ import annotations

import base64
from collections.abc import Iterable
import dataclasses
import os
import re
from typing import TYPE_CHECKING, Any, ClassVar

import boto3
from typing_extensions import override

import file_keeper as fk

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")
HTTP_RESUME = 308


def decode(value: str) -> str:
    return base64.decodebytes(value.encode()).hex()


@dataclasses.dataclass()
class Settings(fk.Settings):
    path: str = ""

    bucket: str = ""

    key: dataclasses.InitVar[str | None] = None
    secret: dataclasses.InitVar[str | None] = None
    region: dataclasses.InitVar[str | None] = None
    endpoint: dataclasses.InitVar[str | None] = None

    client: S3Client = None  # pyright: ignore[reportAssignmentType]

    _required_options: ClassVar[list[str]] = ["bucket"]

    def __post_init__(
        self,
        key: str | None,
        secret: str | None,
        region: str | None,
        endpoint: str | None,
        **kwargs: Any,
    ):
        super().__post_init__(**kwargs)

        self.path = self.path.lstrip("/")

        if self.client is None:  # pyright: ignore[reportUnnecessaryComparison]
            self.client = boto3.client(
                "s3",
                aws_access_key_id=key,
                aws_secret_access_key=secret,
                region_name=region,
                endpoint_url=endpoint,
            )


class Reader(fk.Reader):
    storage: S3Storage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        client = self.storage.settings.client
        filepath = os.path.join(self.storage.settings.path, data.location)

        try:
            obj: Any = client.get_object(
                Bucket=self.storage.settings.bucket, Key=filepath
            )
        except client.exceptions.NoSuchKey as err:
            raise fk.exc.MissingFileError(
                self.storage.settings.name,
                data.location,
            ) from err

        return obj["Body"]


class Uploader(fk.Uploader):
    storage: S3Storage

    capabilities: fk.Capability = fk.Capability.CREATE | fk.Capability.MULTIPART

    @override
    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        if not self.storage.settings.override_existing and self.storage.exists(
            fk.FileData(location), **extras
        ):
            raise fk.exc.ExistingFileError(self.storage, location)

        filepath = os.path.join(self.storage.settings.path, location)

        client = self.storage.settings.client

        obj = client.put_object(
            Bucket=self.storage.settings.bucket,
            Key=filepath,
            Body=upload.stream,  # pyright: ignore[reportArgumentType]
        )

        filehash = obj["ETag"].strip('"')

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            filehash,
        )

    @override
    def multipart_start(
        self,
        location: fk.types.Location,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        filepath = os.path.join(self.storage.settings.path, location)
        client = self.storage.settings.client
        obj = client.create_multipart_upload(
            Bucket=self.storage.settings.bucket,
            Key=filepath,
            ContentType=data.content_type,
        )

        result = fk.MultipartData.from_object(data, location=location)

        result.storage_data.update(
            {
                "upload_id": obj["UploadId"],
                "uploaded": 0,
                "part_number": 1,
                "upload_url": self._presigned_part(filepath, obj["UploadId"], 1),
                "etags": {},
            }
        )
        return result

    def _presigned_part(self, key: str, upload_id: str, part_number: int):
        return self.storage.settings.client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self.storage.settings.bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
        )

    @override
    def multipart_update(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        filepath = os.path.join(self.storage.settings.path, data.location)
        if "upload" in extras:
            upload = fk.make_upload(extras["upload"])

            first_byte = data.storage_data["uploaded"]

            last_byte = first_byte + upload.size
            size = data.size

            if last_byte > size:
                raise fk.exc.UploadOutOfBoundError(last_byte, size)

            if upload.size < 1024 * 1024 * 5 and last_byte < size:
                raise fk.exc.ExtrasError(
                    {"upload": ["Only the final part can be smaller than 5MiB"]}
                )

            resp = self.storage.settings.client.upload_part(
                Bucket=self.storage.settings.bucket,
                Key=filepath,
                UploadId=data.storage_data["upload_id"],
                PartNumber=data.storage_data["part_number"],
                Body=upload.stream,  # pyright: ignore[reportArgumentType]
            )

            etag = resp["ETag"].strip('"')
            data.storage_data["uploaded"] = data.storage_data["uploaded"] + upload.size

        elif "etag" in extras:
            etag = extras["etag"].strip('"')
            data.storage_data["uploaded"] = data.storage_data["uploaded"] + extras.get(
                "uploaded", 0
            )

        else:
            raise fk.exc.ExtrasError(
                {"upload": ["Either upload or etag must be specified"]}
            )

        data.storage_data["etags"][data.storage_data["part_number"]] = etag
        data.storage_data["part_number"] = data.storage_data["part_number"] + 1

        data.storage_data["upload_url"] = self._presigned_part(
            filepath, data.storage_data["upload_id"], data.storage_data["part_number"]
        )

        return data

    @override
    def multipart_complete(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        filepath = os.path.join(self.storage.settings.path, data.location)

        result = self.storage.settings.client.complete_multipart_upload(
            Bucket=self.storage.settings.bucket,
            Key=filepath,
            UploadId=data.storage_data["upload_id"],
            MultipartUpload={
                "Parts": [
                    {"PartNumber": int(num), "ETag": tag}
                    for num, tag in data.storage_data["etags"].items()
                ]
            },
        )

        obj = self.storage.settings.client.get_object(
            Bucket=self.storage.settings.bucket, Key=result["Key"]
        )

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
    storage: S3Storage

    capabilities: fk.Capability = (
        fk.Capability.REMOVE
        | fk.Capability.ANALYZE
        | fk.Capability.EXISTS
        | fk.Capability.SCAN
        | fk.Capability.MOVE
        | fk.Capability.COPY
    )

    @override
    def copy(
        self,
        location: fk.Location,
        data: fk.FileData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        client = self.storage.settings.client
        bucket = self.storage.settings.bucket

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and self.exists(
            fk.FileData(location), extras
        ):
            raise fk.exc.ExistingFileError(self.storage, location)

        old_key = os.path.join(str(self.storage.settings.path), data.location)
        new_key = os.path.join(str(self.storage.settings.path), location)

        client.copy_object(
            Bucket=bucket, CopySource={"Bucket": bucket, "Key": old_key}, Key=new_key
        )

        return self.analyze(location, extras)

    @override
    def move(
        self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]
    ) -> fk.FileData:
        result = self.copy(location, data, extras)
        self.remove(data, extras)

        return result

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        client = self.storage.settings.client
        path = self.storage.settings.path

        marker = ""
        while True:
            resp = client.list_objects(
                Bucket=self.storage.settings.bucket,
                Marker=marker,
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
        filepath = os.path.join(str(self.storage.settings.path), data.location)
        client = self.storage.settings.client

        try:
            client.get_object(Bucket=self.storage.settings.bucket, Key=filepath)
        except client.exceptions.NoSuchKey:
            return False

        return True

    @override
    def remove(
        self, data: fk.FileData | fk.MultipartData, extras: dict[str, Any]
    ) -> bool:
        if isinstance(data, fk.MultipartData):
            return False

        filepath = os.path.join(str(self.storage.settings.path), data.location)
        client = self.storage.settings.client

        # TODO: check if file exists before removing to return correct status
        client.delete_object(Bucket=self.storage.settings.bucket, Key=filepath)

        return True

    @override
    def analyze(
        self, location: fk.types.Location, extras: dict[str, Any]
    ) -> fk.FileData:
        """Return all details about location."""
        filepath = os.path.join(str(self.storage.settings.path), location)
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
    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
