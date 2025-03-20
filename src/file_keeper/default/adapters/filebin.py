from __future__ import annotations

import base64
import dataclasses
from typing import IO, Any, ClassVar, Iterable

import requests

import file_keeper as fk

API_URL = "https://filebin.net"


@dataclasses.dataclass()
class Settings(fk.Settings):
    timeout: int = 10
    bin: str = ""

    _required_options: ClassVar[list[str]] = ["bin"]


class Uploader(fk.Uploader):
    storage: FilebinStorage
    required_options = ["bin"]
    capabilities = fk.Capability.CREATE

    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        resp = requests.post(
            f"{API_URL}/{self.storage.settings.bin}/{location}",
            data=upload.stream,
            timeout=self.storage.settings.timeout,
        )
        if not resp.ok:
            raise fk.exc.UploadError(resp.content)

        info: dict[str, Any] = resp.json()["file"]
        return fk.FileData(
            info["filename"],
            upload.size,
            upload.content_type,
            base64.decodebytes(info["md5"].encode()).decode(),
        )


class Reader(fk.Reader):
    storage: FilebinStorage
    required_options = ["bin"]
    capabilities = (
        fk.Capability.STREAM | fk.Capability.PERMANENT_LINK
    )

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> IO[bytes]:
        resp = requests.get(
            f"{API_URL}/{self.storage.settings.bin}/{data.location}",
            timeout=self.storage.settings.timeout,
            stream=True,
            headers={"accept": "*/*"},
        )
        if verified := resp.cookies.get("verified"):
            resp = requests.get(
                f"{API_URL}/{self.storage.settings.bin}/{data.location}",
                cookies={"verified": verified},
                timeout=self.storage.settings.timeout,
                stream=True,
                headers={"accept": "*/*"},
            )

        return resp.raw  # type: ignore

    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return f"{API_URL}/{self.storage.settings.bin}/{data.location}"


class Manager(fk.Manager):
    storage: FilebinStorage
    required_options = ["bin"]
    capabilities = fk.Capability.REMOVE | fk.Capability.SCAN | fk.Capability.ANALYZE

    def remove(
        self,
        data: fk.FileData | fk.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        requests.delete(
            f"{API_URL}/{self.storage.settings.bin}/{data.location}",
            timeout=self.storage.settings.timeout,
        )
        return True

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        resp = requests.get(
            f"{API_URL}/{self.storage.settings.bin}",
            headers={"accept": "application/json"},
            timeout=self.storage.settings.timeout,
        )

        for record in resp.json()["files"]:
            yield record["filename"]

    def analyze(
        self, location: fk.types.Location, extras: dict[str, Any]
    ) -> fk.FileData:
        resp = requests.get(
            f"{API_URL}/{self.storage.settings.bin}",
            headers={"accept": "application/json"},
            timeout=self.storage.settings.timeout,
        )
        for record in resp.json()["files"]:
            if record["filename"] == location:
                return fk.FileData(
                    record["filename"],
                    record["size"],
                    record["content-type"],
                    base64.decodebytes(record["md5"].encode()).decode(),
                )

        raise fk.exc.MissingFileError(self.storage, location)


class FilebinStorage(fk.Storage):
    hidden = True

    settings: Settings  # type: ignore
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
