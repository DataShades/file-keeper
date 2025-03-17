from __future__ import annotations

import dataclasses
import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

import file_keeper as fk

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class Settings(fk.Settings):
    timeout: int = 5


class Reader(fk.Reader):
    capabilities = fk.Capability.PUBLIC_LINK
    storage: LinkStorage

    def public_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return data.location


class Uploader(fk.Uploader):
    capabilities = fk.Capability.CREATE
    storage: LinkStorage

    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        try:
            url = urlunparse(urlparse(upload.stream.read())).decode()
        except ValueError as err:
            raise fk.exc.ContentError(self, str(err)) from err

        return self.storage.analyze(fk.types.Location(url))


class Manager(fk.Manager):
    capabilities = fk.Capability.ANALYZE | fk.Capability.REMOVE
    storage: LinkStorage

    def remove(
        self,
        data: fk.FileData | fk.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        return True

    def analyze(
        self, location: fk.types.Location, extras: dict[str, Any]
    ) -> fk.FileData:
        resp = requests.head(location, timeout=self.storage.settings.timeout)
        if not resp.ok:
            log.debug("Cannot analyze URL %s: %s", location, resp)

        content_length = resp.headers.get("content-length") or "0"
        size = int(content_length) if content_length.isnumeric() else 0

        content_type = resp.headers.get("content-type") or "application/octet-stream"
        content_type = content_type.split(";", 1)[0]

        hash = resp.headers.get("etag") or ""

        return fk.FileData(location, size, content_type, hash)


class LinkStorage(fk.Storage):
    settings: Settings  # type: ignore
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
