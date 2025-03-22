from __future__ import annotations

import base64
import dataclasses
import os
import re
from typing import Any, ClassVar, Iterable

import boto3

import file_keeper as fk

RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")
HTTP_RESUME = 308


def decode(value: str) -> str:
    return base64.decodebytes(value.encode()).hex()


@dataclasses.dataclass()
class Settings(fk.Settings):
    path: str = ""

    bucket: str = ""

    key: str | None = None
    secret: str | None = None
    region: str | None = None
    endpoint: str | None = None

    client: Any = None

    _required_options: ClassVar[list[str]] = ["bucket"]

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        self.path = self.path.lstrip("/")

        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.key,
            aws_secret_access_key=self.secret,
            region_name=self.region,
            endpoint_url=self.endpoint,
        )


class Reader(fk.Reader):
    storage: S3Storage
    capabilities = fk.Capability.STREAM

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

    capabilities = fk.Capability.CREATE | fk.Capability.MULTIPART

    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        filepath = os.path.join(self.storage.settings.path, location)

        client = self.storage.settings.client
        obj = client.put_object(
            Bucket=self.storage.settings.bucket, Key=filepath, Body=upload.stream
        )

        filehash = obj["ETag"].strip('"')

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            filehash,
        )

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

        data.location = location
        data.storage_data = dict(
            data.storage_data,
            upload_id=obj["UploadId"],
            uploaded=0,
            part_number=1,
            upload_url=self._presigned_part(filepath, obj["UploadId"], 1),
            etags={},
        )
        return data

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
                Body=upload.stream,
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

    capabilities = fk.Capability.REMOVE | fk.Capability.ANALYZE

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
    settings: Settings  # type: ignore
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
