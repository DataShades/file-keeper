from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterable
from typing import Any

import file_keeper as fk

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for Null storage."""


class Uploader(fk.Uploader):
    storage: NullStorage
    capabilities = fk.Capability.UPLOADER_CAPABILITIES

    def upload(
        self,
        location: fk.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        reader = upload.hashing_reader()
        return fk.FileData(location, hash=reader.get_hash())

    def multipart_start(
        self,
        location: fk.Location,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        return fk.MultipartData(location)

    def multipart_refresh(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        return data

    def multipart_update(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        return data

    def multipart_complete(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        return fk.FileData.from_object(data)


class Manager(fk.Manager):
    storage: NullStorage
    capabilities = fk.Capability.MANAGER_CAPABILITIES

    def remove(
        self, data: fk.FileData | fk.MultipartData, extras: dict[str, Any]
    ) -> bool:
        return False

    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        return False

    def compose(
        self,
        location: fk.Location,
        datas: Iterable[fk.FileData],
        extras: dict[str, Any],
    ) -> fk.FileData:
        return fk.FileData(location)

    def append(
        self,
        data: fk.FileData,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        return fk.FileData.from_object(data)

    def copy(
        self,
        location: fk.Location,
        data: fk.FileData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        result = fk.FileData.from_object(data)
        result.location = location
        return result

    def move(
        self,
        location: fk.Location,
        data: fk.FileData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        result = fk.FileData.from_object(data)
        result.location = location
        return result

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        return []

    def analyze(
        self,
        location: fk.Location,
        extras: dict[str, Any],
    ) -> fk.FileData:
        return fk.FileData(location)


class Reader(fk.Reader):
    storage: NullStorage
    capabilities = fk.Capability.READER_CAPABILITIES

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        return []

    def range(
        self,
        data: fk.FileData,
        start: int,
        end: int | None,
        extras: dict[str, Any],
    ) -> Iterable[bytes]:
        return []

    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return data.location

    def temporal_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return data.location

    def one_time_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return data.location


class NullStorage(fk.Storage):
    """Immitate storage behavior but do not store anything."""

    settings: Settings  # type: ignore

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader
    ManagerFactory = Manager
