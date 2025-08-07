from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterable
from typing import Any

from typing_extensions import override

import file_keeper as fk

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for Null storage."""


class Uploader(fk.Uploader):
    storage: NullStorage
    capabilities: fk.Capability = fk.Capability.UPLOADER_CAPABILITIES

    @override
    def upload(self, location: fk.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        reader = upload.hashing_reader()
        return fk.FileData(location, hash=reader.get_hash())

    @override
    def multipart_start(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData.from_object(data)

    @override
    def multipart_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        return data

    @override
    def multipart_update(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        return data

    @override
    def multipart_complete(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData.from_object(data)

    @override
    def multipart_remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        return False


class Manager(fk.Manager):
    storage: NullStorage
    capabilities: fk.Capability = fk.Capability.MANAGER_CAPABILITIES

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        return False

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        return False

    @override
    def compose(self, location: fk.Location, datas: Iterable[fk.FileData], extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData(location)

    @override
    def append(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData.from_object(data)

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData.from_object(data, location=location)

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData.from_object(data, location=location)

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        return []

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        return fk.FileData(location)


class Reader(fk.Reader):
    storage: NullStorage
    capabilities: fk.Capability = fk.Capability.READER_CAPABILITIES

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        return []

    @override
    def range(self, data: fk.FileData, start: int, end: int | None, extras: dict[str, Any]) -> Iterable[bytes]:
        return []

    @override
    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return data.location

    @override
    def temporal_link(self, data: fk.FileData, duration: int, extras: dict[str, Any]) -> str:
        return data.location

    @override
    def one_time_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        return data.location


class NullStorage(fk.Storage):
    """Immitate storage behavior but do not store anything."""

    settings: Settings

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader
    ManagerFactory = Manager
