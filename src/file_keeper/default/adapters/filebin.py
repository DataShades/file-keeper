from __future__ import annotations

import base64
import dataclasses
from collections.abc import Iterable
from typing import IO, Any, ClassVar

import requests
from typing_extensions import override

import file_keeper as fk

API_URL = "https://filebin.net"


@dataclasses.dataclass()
class Settings(fk.Settings):
    timeout: int = 10
    bin: str = ""

    _required_options: ClassVar[list[str]] = ["bin"]


class Uploader(fk.Uploader):
    storage: FilebinStorage
    capabilities: fk.Capability = fk.Capability.CREATE

    @override
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
    capabilities: fk.Capability = fk.Capability.STREAM | fk.Capability.PERMANENT_LINK

    @override
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

        return resp.raw  # pyright: ignore[reportReturnType]

    @override
    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return f"{API_URL}/{self.storage.settings.bin}/{data.location}"


class Manager(fk.Manager):
    storage: FilebinStorage
    capabilities: fk.Capability = fk.Capability.REMOVE | fk.Capability.SCAN | fk.Capability.ANALYZE

    @override
    def remove(
        self,
        data: fk.FileData,
        extras: dict[str, Any],
    ) -> bool:
        requests.delete(
            f"{API_URL}/{self.storage.settings.bin}/{data.location}",
            timeout=self.storage.settings.timeout,
        )
        return True

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        resp = requests.get(
            f"{API_URL}/{self.storage.settings.bin}",
            headers={"accept": "application/json"},
            timeout=self.storage.settings.timeout,
        )

        for record in resp.json()["files"]:
            yield record["filename"]

    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
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

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
