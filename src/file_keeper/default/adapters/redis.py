from __future__ import annotations

import dataclasses
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
    """Settings for Redis storage.

    Args:
        redis: existing redis connection
        redis_url: URL of the redis DB. Used only if `redis` is empty
    """

    bucket: str = ""
    redis: redis.Redis = None  # pyright: ignore[reportAssignmentType]

    url: dataclasses.InitVar[str] = ""

    _required_options: ClassVar[list[str]] = ["bucket"]

    def __post_init__(self, url: str, **kwargs: Any):
        super().__post_init__(**kwargs)

        if self.redis is None:  # pyright: ignore[reportUnnecessaryComparison]
            if url not in pool:
                conn = redis.ConnectionPool.from_url(url) if url else redis.ConnectionPool()
                pool.register(url, conn)

            self.redis = redis.Redis(connection_pool=pool[url])


class Uploader(fk.Uploader):
    storage: RedisStorage
    capabilities: fk.Capability = fk.Capability.CREATE | fk.Capability.MULTIPART

    @override
    def upload(self, location: fk.types.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        """Upload file to into location within storage bucket.

        Raises:
            ExistingFileError: file exists and overrides are not allowed

        Returns:
            New file data
        """
        cfg = self.storage.settings

        if not cfg.override_existing and cfg.redis.hexists(cfg.bucket, location):
            raise fk.exc.ExistingFileError(self.storage, location)

        reader = fk.HashingReader(upload.stream)

        content: Any = reader.read()
        cfg.redis.hset(cfg.bucket, location, content)

        return fk.FileData(
            location,
            reader.position,
            upload.content_type,
            reader.get_hash(),
        )

    @override
    def multipart_start(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Create an empty file using `upload` method.

        Put `uploaded=0` into `data.storage_data` and copy the `location` from
        the newly created empty file.

        Returns:
            New file data
        """
        upload = fk.Upload(
            BytesIO(),
            data.location,
            data.size,
            data.content_type,
        )
        tmp_result = self.upload(data.location, upload, extras)

        result = fk.FileData.from_object(data, location=tmp_result.location)
        result.storage_data.update({"uploaded": 0})
        return result

    @override
    def multipart_refresh(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Synchronize `storage_data["uploaded"]` with actual value.

        Raises:
            MissingFileError: location does not exist

        Returns:
            Updated file data
        """
        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        data.storage_data["uploaded"] = cfg.redis.hstrlen(cfg.bucket, data.location)

        return data

    @override
    def multipart_update(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Add part to existing multipart upload.

        The content of upload is taken from `extras["upload"]`.

        In the end, `storage_data["uploaded"]` is set to the actial space taken
        by the storage in the system after the update.

        Raises:
            MissingFileError: file is missing
            MissingExtrasError: extra parameters are missing
            UploadOutOfBoundError: part exceeds allocated file size

        Returns:
            Updated file data
        """
        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if "upload" not in extras:
            raise fk.exc.MissingExtrasError("upload")
        upload = fk.make_upload(extras["upload"])

        current: bytes = cfg.redis.hget(cfg.bucket, data.location)  # pyright: ignore[reportAssignmentType]
        size = len(current)

        if "uploaded" not in data.storage_data:
            data.storage_data["uploaded"] = size

        expected_size = size + upload.size
        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        new_content: Any = current + upload.stream.read()
        cfg.redis.hset(cfg.bucket, data.location, new_content)

        data.storage_data["uploaded"] = expected_size
        return data

    @override
    def multipart_complete(self, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Finalize the upload.

        Raises:
            MissingFileError: file does not exist
            UploadSizeMismatchError: actual and expected sizes are different
            UploadTypeMismatchError: actual and expected content types are different
            UploadHashMismatchError: actual and expected content hashes are different

        Returns:
            File data
        """
        cfg = self.storage.settings
        content = cast("bytes | None", cfg.redis.hget(cfg.bucket, data.location))
        if content is None:
            raise fk.exc.MissingFileError(self.storage, data.location)

        size = len(content)
        if size != data.size:
            raise fk.exc.UploadSizeMismatchError(size, data.size)

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

        return fk.FileData(data.location, size, content_type, reader.get_hash())


class Reader(fk.Reader):
    storage: RedisStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> IO[bytes]:
        """Return file open in binary-read mode.

        Returns:
            File content iterator
        """
        return BytesIO(self.content(data, extras))

    @override
    def content(self, data: fk.FileData, extras: dict[str, Any]) -> bytes:
        """Return content of the file.

        Raises:
            MissingFileError: file does not exist
        """
        cfg = self.storage.settings
        content = cast("bytes | None", cfg.redis.hget(cfg.bucket, data.location))
        if content is None:
            raise fk.exc.MissingFileError(self.storage, data.location)

        return content


class Manager(fk.Manager):
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
        """Copy file inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and cfg.redis.hexists(cfg.bucket, location):
            raise fk.exc.ExistingFileError(self.storage, location)

        content: Any = cfg.redis.hget(cfg.bucket, data.location)
        cfg.redis.hset(cfg.bucket, location, content)

        return fk.FileData.from_object(data, location=location)

    @override
    def move(self, location: fk.types.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        """Move file to a different location inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.bucket, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not cfg.override_existing and cfg.redis.hexists(cfg.bucket, location):
            raise fk.exc.ExistingFileError(self.storage, location)

        content: Any = cfg.redis.hget(
            cfg.bucket,
            data.location,
        )
        cfg.redis.hset(cfg.bucket, location, content)
        cfg.redis.hdel(cfg.bucket, data.location)

        return fk.FileData.from_object(data, location=location)

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        """Check if file exists."""
        cfg = self.storage.settings
        return bool(cfg.redis.hexists(cfg.bucket, data.location))

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        """Remove the file."""
        cfg = self.storage.settings
        result = cfg.redis.hdel(cfg.bucket, data.location)
        return bool(result)

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """Discover filenames under storage path."""
        cfg = self.storage.settings
        for key in cast("Iterable[bytes]", cfg.redis.hkeys(cfg.bucket)):
            yield key.decode()

    @override
    def analyze(self, location: fk.types.Location, extras: dict[str, Any]) -> fk.FileData:
        """Return all details about location.

        Raises:
            MissingFileError: file does not exist
        """
        cfg = self.storage.settings
        value: Any = cfg.redis.hget(cfg.bucket, location)
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
    settings: Settings
    SettingsFactory = Settings

    ReaderFactory = Reader
    ManagerFactory = Manager
    UploaderFactory = Uploader
