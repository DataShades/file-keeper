"""Redis adapter."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Iterable
from io import BytesIO
from typing import IO, Any, ClassVar, cast

import magic
import redis
from typing_extensions import override

import file_keeper as fk

pool = fk.Registry[redis.ConnectionPool]()


@dataclasses.dataclass
class Settings(fk.Settings):
    """Settings for Redis storage."""

    bucket: str = ""
    """Key of the Redis HASH for uploaded objects."""
    redis: redis.Redis = None  # pyright: ignore[reportAssignmentType]
    """Existing redis connection"""

    url: str = ""
    """URL of the Redis DB. Used only if `redis` is empty"""

    _required_options: ClassVar[list[str]] = ["bucket"]

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        if self.redis is None:  # pyright: ignore[reportUnnecessaryComparison]
            if self.url not in pool:
                conn = redis.ConnectionPool.from_url(self.url) if self.url else redis.ConnectionPool()
                pool.register(self.url, conn)

            self.redis = redis.Redis(connection_pool=pool[self.url])


class Uploader(fk.Uploader):
    """Redis uploader."""

    storage: RedisStorage
    capabilities: fk.Capability = fk.Capability.CREATE | fk.Capability.RESUMABLE

    @override
    def upload(self, location: fk.types.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)

        cfg = self.storage.settings

        if not cfg.override_existing and cfg.redis.hexists(cfg.bucket, filepath):
            raise fk.exc.ExistingFileError(self.storage, location)

        reader = fk.HashingReader(upload.stream)

        content: Any = reader.read()
        cfg.redis.hset(cfg.bucket, filepath, content)

        return fk.FileData(
            location,
            reader.position,
            upload.content_type,
            reader.get_hash(),
        )

    @override
    def resumable_start(self, location: fk.Location, size: int, extras: dict[str, Any]) -> fk.FileData:
        upload = fk.Upload(
            BytesIO(),
            location,
            0,
            fk.FileData.content_type,
        )
        tmp_result = self.upload(location, upload, extras)

        return fk.FileData.from_dict(
            extras,
            location=tmp_result.location,
            size=size,
            storage_data={"uploaded": 0, "resumable": True},
        )

    @override
    def resumable_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, filepath):
            raise fk.exc.MissingFileError(self.storage, data.location)

        result = fk.FileData.from_object(data)
        result.storage_data["uploaded"] = cfg.redis.hstrlen(cfg.bucket, filepath)

        if result.storage_data["uploaded"] == result.size:
            return self._resumable_complete(result)

        return result

    @override
    def resumable_remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        return self.storage.remove(data)

    @override
    def resumable_resume(self, data: fk.FileData, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, filepath):
            raise fk.exc.MissingFileError(self.storage, data.location)

        current: bytes = cfg.redis.hget(cfg.bucket, filepath)  # pyright: ignore[reportAssignmentType]
        size = len(current)

        expected_size = size + upload.size
        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        new_content: Any = current + upload.stream.read()
        cfg.redis.hset(cfg.bucket, filepath, new_content)

        result = fk.FileData.from_object(data)
        result.storage_data["uploaded"] = expected_size
        if result.storage_data["uploaded"] == result.size:
            return self._resumable_complete(result)

        return result

    def _resumable_complete(self, data: fk.FileData) -> fk.FileData:
        filepath = self.storage.full_path(data.location)

        cfg = self.storage.settings
        content = cast("bytes | None", cfg.redis.hget(cfg.bucket, filepath))
        if content is None:
            raise fk.exc.MissingFileError(self.storage, data.location)

        reader = fk.HashingReader(BytesIO(content))

        content_type = magic.from_buffer(next(reader, b""), True)
        if data.content_type and content_type != data.content_type:
            raise fk.exc.UploadTypeMismatchError(
                content_type,
                data.content_type,
            )
        reader.exhaust()

        if data.hash and data.hash != reader.get_hash():
            raise fk.exc.UploadHashMismatchError(reader.get_hash(), data.hash)

        result = fk.FileData.from_object(data, content_type=content_type, hash=reader.get_hash())
        result.storage_data.pop("uploaded")
        result.storage_data.pop("resumable")
        return result


class Reader(fk.Reader):
    """Redis reader."""

    storage: RedisStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> IO[bytes]:
        return BytesIO(self.content(data, extras))

    @override
    def content(self, data: fk.FileData, extras: dict[str, Any]) -> bytes:
        filepath = self.storage.full_path(data.location)

        cfg = self.storage.settings
        content = cast("bytes | None", cfg.redis.hget(cfg.bucket, filepath))
        if content is None:
            raise fk.exc.MissingFileError(self.storage, data.location)

        return content


class Manager(fk.Manager):
    """Redis manager."""

    storage: RedisStorage

    capabilities: fk.Capability = (
        fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.REMOVE
        | fk.Capability.EXISTS
        | fk.Capability.SCAN
        | fk.Capability.ANALYZE
    )

    @override
    def copy(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        srcpath = self.storage.full_path(data.location)
        destpath = self.storage.full_path(location)

        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, srcpath):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and cfg.redis.hexists(cfg.bucket, destpath):
            raise fk.exc.ExistingFileError(self.storage, location)

        content: Any = cfg.redis.hget(cfg.bucket, srcpath)
        cfg.redis.hset(cfg.bucket, destpath, content)

        return fk.FileData.from_object(data, location=location)

    @override
    def move(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        srcpath = self.storage.full_path(data.location)
        destpath = self.storage.full_path(location)

        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, srcpath):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not cfg.override_existing and cfg.redis.hexists(cfg.bucket, destpath):
            raise fk.exc.ExistingFileError(self.storage, location)

        content: Any = cfg.redis.hget(
            cfg.bucket,
            srcpath,
        )
        cfg.redis.hset(cfg.bucket, destpath, content)
        cfg.redis.hdel(cfg.bucket, srcpath)

        return fk.FileData.from_object(data, location=location)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)

        cfg = self.storage.settings
        return bool(cfg.redis.hexists(cfg.bucket, filepath))

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        cfg = self.storage.settings
        result = cfg.redis.hdel(cfg.bucket, filepath)
        return bool(result)

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"

        cfg = self.storage.settings
        for key in cast("Iterable[bytes]", cfg.redis.hkeys(cfg.bucket)):
            decoded = key.decode()
            if decoded.startswith(path):
                yield os.path.relpath(key.decode(), path)

    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)
        cfg = self.storage.settings
        value: Any = cfg.redis.hget(cfg.bucket, filepath)
        if value is None:
            raise fk.exc.MissingFileError(self.storage, location)

        reader = fk.HashingReader(BytesIO(value))
        content_type = magic.from_buffer(next(reader, b""), True)
        reader.exhaust()

        return fk.FileData(
            location,
            size=reader.position,
            content_type=content_type,
            hash=reader.get_hash(),
        )


class RedisStorage(fk.Storage):
    """Redis storage adapter.

    This adapter uses a Redis HASH to store files. Each file is stored as a field
    in the HASH, where the field name is the file location and the field value is
    the file content.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:redis",
        "bucket": "my_bucket",
        "url": "redis://localhost:6379/0",
        "override_existing": False,
    }

    storage = fk.make_storage("redis", settings)
    ```

    Note:
    * The `bucket` setting is required and specifies the key of the Redis HASH.
    * The `url` setting is optional. If not provided, it defaults to `redis://localhost:6379/0`.
    * The `override_existing` setting controls whether existing files can be overwritten.

    """

    settings: Settings
    SettingsFactory = Settings

    ReaderFactory = Reader
    ManagerFactory = Manager
    UploaderFactory = Uploader
