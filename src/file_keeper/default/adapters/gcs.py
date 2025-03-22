from __future__ import annotations

import base64
import dataclasses
import os
import re
from typing import Any, ClassVar, cast

import requests
from google.api_core.exceptions import Forbidden
from google.cloud.storage import Client
from google.oauth2.service_account import Credentials

import file_keeper as fk

RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")
HTTP_RESUME = 308


def decode(value: str) -> str:
    return base64.decodebytes(value.encode()).hex()


@dataclasses.dataclass()
class Settings(fk.Settings):
    path: str = ""
    bucket: str = ""
    credentials_file: str = ""
    resumable_origin: str = ""

    container: str = ""

    client: Client = None  # type: ignore
    _required_options: ClassVar[list[str]] = ["bucket", "path", "credentials_file"]

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)
        self.path = self.path.lstrip("/")

        credentials = None
        if self.credentials_file:
            try:
                credentials = Credentials.from_service_account_file(
                    self.credentials_file
                )
            except OSError as err:
                raise fk.exc.InvalidStorageConfigurationError(
                    type(self),
                    f"file `{self.credentials_file}` does not exist",
                ) from err

        self.client = Client(credentials=credentials)


class Uploader(fk.Uploader):
    storage: GoogleCloudStorage

    capabilities = fk.Capability.CREATE | fk.Capability.MULTIPART

    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        filepath = os.path.join(self.storage.settings.path, location)

        client = self.storage.settings.client
        blob = client.bucket(self.storage.settings.bucket).blob(filepath)

        blob.upload_from_file(upload.stream)
        filehash = decode(blob.md5_hash)
        return fk.FileData(
            location,
            blob.size or upload.size,
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
        blob = client.bucket(self.storage.settings.bucket).blob(filepath)

        url = cast(
            str,
            blob.create_resumable_upload_session(
                size=data.size,
                origin=self.storage.settings.resumable_origin,
            ),
        )

        if not url:
            msg = "Cannot initialize session URL"
            raise fk.exc.UploadError(msg)

        data.location = location
        data.storage_data = dict(
            data.storage_data,
            session_url=url,
            uploaded=0,
        )
        return data

    def multipart_update(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
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

            resp = requests.put(
                data.storage_data["session_url"],
                data=upload.stream.read(),
                headers={
                    "content-range": f"bytes {first_byte}-{last_byte}/{size}",
                },
                timeout=10,
            )

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

    def multipart_refresh(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        resp = requests.put(
            data.storage_data["session_url"],
            headers={
                "content-range": f"bytes */{data.size}",
                "content-length": "0",
            },
            timeout=10,
        )
        if not resp.ok:
            raise fk.exc.ExtrasError({"session_url": [resp.text]})

        if resp.status_code == HTTP_RESUME:
            if "range" in resp.headers:
                range_match = RE_RANGE.match(resp.headers["range"])
                if not range_match:
                    raise fk.exc.ExtrasError(
                        {
                            "session_url": [
                                "Invalid response from Google Cloud:"
                                + " missing range header",
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
                        "Invalid response from Google Cloud:"
                        + f" unexpected status {resp.status_code}",
                    ],
                },
            )

        return data

    def multipart_complete(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.FileData:
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


class Manager(fk.Manager):
    storage: GoogleCloudStorage
    capabilities = fk.Capability.REMOVE

    def remove(
        self, data: fk.FileData | fk.MultipartData, extras: dict[str, Any]
    ) -> bool:
        if isinstance(data, fk.MultipartData):
            return False

        filepath = os.path.join(str(self.storage.settings.path), data.location)
        client: Client = self.storage.settings.client
        blob = client.bucket(self.storage.settings.bucket).blob(filepath)

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
    settings: Settings  # type: ignore
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    # ReaderFactory = Reader
