from __future__ import annotations

import copy
import dataclasses
from io import BytesIO
from typing import IO, Any, ClassVar, Iterable, cast

import magic
import redis

import file_keeper as fk

pools = fk.Registry[redis.ConnectionPool]()


@dataclasses.dataclass
class Settings(fk.Settings):
    """Settings for Redis storage.

    Args:
        redis: existing redis connection
        redis_url: URL of the redis DB. Used only if `redis` is empty
    """

    path: str = ""
    redis: redis.Redis[bytes] = None  # type: ignore

    redis_url: dataclasses.InitVar[str] = ""

    _required_options: ClassVar[list[str]] = ["path"]

    def __post_init__(self, redis_url: str, **kwargs: Any):
        super().__post_init__(**kwargs)

        if not self.redis:
            if redis_url not in pools:
                pools.register(
                    redis_url,
                    redis.ConnectionPool.from_url(redis_url)
                    if redis_url
                    else redis.ConnectionPool(),
                )

            self.redis = redis.Redis(connection_pool=pools[redis_url])


class Uploader(fk.Uploader):
    storage: RedisStorage
    capabilities = fk.Capability.CREATE | fk.Capability.MULTIPART

    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Upload file to into location within storage path.

        Raises:
            ExistingFileError: file exists and overrides are not allowed

        Returns:
            New file data
        """
        cfg = self.storage.settings

        if not cfg.override_existing and cfg.redis.hexists(cfg.path, location):
            raise fk.exc.ExistingFileError(self.storage, location)

        reader = fk.HashingReader(upload.stream)

        content: Any = reader.read()
        cfg.redis.hset(cfg.path, location, content)

        return fk.FileData(
            location,
            reader.position,
            upload.content_type,
            reader.get_hash(),
        )

    def multipart_start(
        self,
        location: fk.types.Location,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        """Create an empty file using `upload` method.

        Put `uploaded=0` into `data.storage_data` and copy the `location` from
        the newly created empty file.

        Returns:
            New file data
        """
        upload = fk.Upload(
            BytesIO(),
            location,
            data.size,
            data.content_type,
        )
        tmp_result = self.upload(location, upload, extras)

        data.location = tmp_result.location
        data.storage_data = dict(tmp_result.storage_data, uploaded=0)
        return data

    def multipart_refresh(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        """Synchronize `storage_data["uploaded"]` with actual value.

        Raises:
            MissingFileError: location does not exist

        Returns:
            Updated file data
        """
        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.path, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        data.storage_data["uploaded"] = cfg.redis.hstrlen(cfg.path, data.location)

        return data

    def multipart_update(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
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

        if not cfg.redis.hexists(cfg.path, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if "upload" not in extras:
            raise fk.exc.MissingExtrasError("upload")
        upload = fk.make_upload(extras["upload"])

        current = cast(bytes, cfg.redis.hget(cfg.path, data.location))
        size = len(current)

        if "uploaded" not in data.storage_data:
            data.storage_data["uploaded"] = size

        expected_size = size + upload.size
        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        new_content: Any = current + upload.stream.read()
        cfg.redis.hset(cfg.path, data.location, new_content)

        data.storage_data["uploaded"] = expected_size
        return data

    def multipart_complete(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.FileData:
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
        content = cast("bytes | None", cfg.redis.hget(cfg.path, data.location))
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
    capabilities = fk.Capability.STREAM

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> IO[bytes]:
        """Return file open in binary-read mode.

        Returns:
            File content iterator
        """
        return BytesIO(self.content(data, extras))

    def content(self, data: fk.FileData, extras: dict[str, Any]) -> bytes:
        """Return content of the file.

        Raises:
            MissingFileError: file does not exist
        """
        cfg = self.storage.settings
        content = cast("bytes | None", cfg.redis.hget(cfg.path, data.location))
        if content is None:
            raise fk.exc.MissingFileError(self.storage, data.location)

        return content


class Manager(fk.Manager):
    storage: RedisStorage

    capabilities = (
        fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.REMOVE
        | fk.Capability.EXISTS
        | fk.Capability.SCAN
        | fk.Capability.ANALYZE
    )

    def copy(
        self,
        location: fk.types.Location,
        data: fk.FileData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Copy file inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.path, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not self.storage.settings.override_existing and cfg.redis.hexists(
            cfg.path, location
        ):
            raise fk.exc.ExistingFileError(self.storage, location)

        content: Any = cfg.redis.hget(cfg.path, data.location)
        cfg.redis.hset(cfg.path, location, content)

        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def move(
        self,
        location: fk.types.Location,
        data: fk.FileData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Move file to a different location inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        cfg = self.storage.settings

        if not cfg.redis.hexists(cfg.path, data.location):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if not cfg.override_existing and cfg.redis.hexists(cfg.path, location):
            raise fk.exc.ExistingFileError(self.storage, location)

        content: Any = cfg.redis.hget(
            cfg.path,
            data.location,
        )
        cfg.redis.hset(cfg.path, location, content)
        cfg.redis.hdel(cfg.path, data.location)
        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        """Check if file exists."""
        cfg = self.storage.settings
        return bool(cfg.redis.hexists(cfg.path, data.location))

    def remove(
        self, data: fk.FileData | fk.MultipartData, extras: dict[str, Any]
    ) -> bool:
        """Remove the file."""
        cfg = self.storage.settings
        result = cfg.redis.hdel(cfg.path, data.location)
        return bool(result)

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """Discover filenames under storage path."""
        cfg = self.storage.settings
        for key in cast("Iterable[bytes]", cfg.redis.hkeys(cfg.path)):
            yield key.decode()

    def analyze(
        self, location: fk.types.Location, extras: dict[str, Any]
    ) -> fk.FileData:
        """Return all details about location.

        Raises:
            MissingFileError: file does not exist
        """
        cfg = self.storage.settings
        value: Any = cfg.redis.hget(cfg.path, location)
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
    settings: Settings  # type: ignore
    SettingsFactory = Settings

    ReaderFactory = Reader
    ManagerFactory = Manager
    UploaderFactory = Uploader
