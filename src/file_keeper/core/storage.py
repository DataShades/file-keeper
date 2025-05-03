"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

import dataclasses
import functools
import logging
from typing import Any, Callable, ClassVar, Iterable, cast

from typing_extensions import Concatenate, ParamSpec, TypeAlias, TypeVar

from . import data, exceptions, types, utils
from .upload import make_upload, Upload
from .registry import Registry

P = ParamSpec("P")
T = TypeVar("T")
S = TypeVar("S", bound="Storage")


log = logging.getLogger(__name__)

LocationTransformer: TypeAlias = Callable[[str, "dict[str, Any]"], str]
Capability: TypeAlias = utils.Capability

adapters = Registry["type[Storage]"]()
location_transformers = Registry[LocationTransformer]()


def requires_capability(capability: Capability):
    def decorator(func: Callable[Concatenate[S, P], T]):
        @functools.wraps(func)
        def method(self: S, *args: P.args, **kwargs: P.kwargs) -> T:
            if not self.supports(capability):
                raise exceptions.UnsupportedOperationError(str(capability.name), self)
            return func(self, *args, **kwargs)

        return method

    return decorator


class StorageService:
    """Base class for services used by storage.

    StorageService.capabilities reflect all operations provided by the
    service.

    Examples:
        >>> class Uploader(StorageService):
        >>>     capabilities = Capability.CREATE
    """

    capabilities = Capability.NONE

    def __init__(self, storage: Storage):
        self.storage = storage


class Uploader(StorageService):
    """Service responsible for writing data into a storage.

    `Storage` internally calls methods of this service. For example,
    `Storage.upload(location, upload, **kwargs)` results in
    `Uploader.upload(location, upload, kwargs)`.

    Example:
        ```python
        class MyUploader(Uploader):
            def upload(
                self, location: Location, upload: Upload, extras: dict[str, Any]
            ) -> FileData:
                reader = upload.hashing_reader()

                with open(location, "wb") as dest:
                    dest.write(reader.read())

                return FileData(
                    location, upload.size,
                    upload.content_type,
                    reader.get_hash()
                )
        ```
    """

    def upload(
        self,
        location: types.Location,
        upload: Upload,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Upload file using single stream."""
        raise NotImplementedError

    def multipart_start(
        self,
        location: types.Location,
        data: data.MultipartData,
        extras: dict[str, Any],
    ) -> data.MultipartData:
        """Prepare everything for multipart(resumable) upload."""
        raise NotImplementedError

    def multipart_refresh(
        self,
        data: data.MultipartData,
        extras: dict[str, Any],
    ) -> data.MultipartData:
        """Show details of the incomplete upload."""
        raise NotImplementedError

    def multipart_update(
        self,
        data: data.MultipartData,
        extras: dict[str, Any],
    ) -> data.MultipartData:
        """Add data to the incomplete upload."""
        raise NotImplementedError

    def multipart_complete(
        self,
        data: data.MultipartData,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Verify file integrity and finalize incomplete upload."""
        raise NotImplementedError


class Manager(StorageService):
    """Service responsible for maintenance file operations.

    `Storage` internally calls methods of this service. For example,
    `Storage.remove(data, **kwargs)` results in `Manager.remove(data, kwargs)`.

    Example:
        ```python
        class MyManager(Manager):
            def remove(
                self, data: FileData|MultipartData, extras: dict[str, Any]
            ) -> bool:
                os.remove(data.location)
                return True
        ```
    """

    def remove(
        self, data: data.FileData | data.MultipartData, extras: dict[str, Any]
    ) -> bool:
        """Remove file from the storage."""
        raise NotImplementedError

    def exists(self, data: data.FileData, extras: dict[str, Any]) -> bool:
        """Check if file exists in the storage."""
        raise NotImplementedError

    def compose(
        self,
        location: types.Location,
        datas: Iterable[data.FileData],
        extras: dict[str, Any],
    ) -> data.FileData:
        """Combine multipe file inside the storage into a new one."""
        raise NotImplementedError

    def append(
        self,
        data: data.FileData,
        upload: Upload,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Append content to existing file."""
        raise NotImplementedError

    def copy(
        self,
        location: types.Location,
        data: data.FileData,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Copy file inside the storage."""
        raise NotImplementedError

    def move(
        self,
        location: types.Location,
        data: data.FileData,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Move file to a different location inside the storage."""
        raise NotImplementedError

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """List all locations(filenames) in storage."""
        raise NotImplementedError

    def analyze(
        self,
        location: types.Location,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Return all details about filename."""
        raise NotImplementedError


class Reader(StorageService):
    """Service responsible for reading data from the storage.

    `Storage` internally calls methods of this service. For example,
    `Storage.stream(data, **kwargs)` results in `Reader.stream(data, kwargs)`.

    Example:
        ```python
        class MyReader(Reader):
            def stream(
                self, data: FileData, extras: dict[str, Any]
            ) -> Iterable[bytes]:
                return open(data.location, "rb")
        ```
    """

    def stream(self, data: data.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        """Return byte-stream of the file content."""
        raise NotImplementedError

    def content(self, data: data.FileData, extras: dict[str, Any]) -> bytes:
        """Return file content as a single byte object."""
        return b"".join(self.stream(data, extras))

    def range(
        self,
        data: data.FileData,
        start: int,
        end: int | None,
        extras: dict[str, Any],
    ) -> Iterable[bytes]:
        """Return slice of the file content."""
        raise NotImplementedError

    def permanent_link(self, data: data.FileData, extras: dict[str, Any]) -> str:
        """Return permanent download link."""
        raise NotImplementedError

    def temporal_link(self, data: data.FileData, extras: dict[str, Any]) -> str:
        """Return temporal download link.

        extras["ttl"] controls lifetime of the link(30 seconds by default).

        """
        raise NotImplementedError

    def one_time_link(self, data: data.FileData, extras: dict[str, Any]) -> str:
        """Return one-time download link."""
        raise NotImplementedError

    def public_link(self, data: data.FileData, extras: dict[str, Any]) -> str:
        """Return public link."""
        raise NotImplementedError


@dataclasses.dataclass()
class Settings:
    name: str = "unknown"
    """Name of the storage"""
    override_existing: bool = False
    """Allow overriding existing files"""
    location_transformers: list[str] = dataclasses.field(default_factory=list)
    """Names of functions used to sanitize location"""

    _required_options: ClassVar[list[str]] = []

    def __post_init__(self, **kwargs: Any):
        for attr in self._required_options:
            if not getattr(self, attr):
                raise exceptions.MissingStorageConfigurationError(self.name, attr)


class Storage:
    """Base class for storage implementation.

    Args:
        settings: storage configuration

    Examples:
        >>> class MyStorage(Storage):
        >>>     def make_uploader(self):
        >>>         return MyUploader(self)

        >>>     def make_reader(self):
        >>>         return MyReader(self)

        >>>     def make_manager(self):
        >>>         return MyManager(self)
    """

    # do not show storage adapter
    hidden = False

    capabilities: Capability = Capability.NONE
    """Operations supported by storage. Computed from capabilities of
    services during storage initialization."""

    settings: Settings
    """Settings of the storage"""

    SettingsFactory: type[Settings] = Settings
    """Factory class for storage settings."""
    UploaderFactory: type[Uploader] = Uploader
    """Factory class for uploader service."""
    ManagerFactory: type[Manager] = Manager
    """Factory class for manager service."""
    ReaderFactory: type[Reader] = Reader
    """Factory class for reader service."""

    def __str__(self):
        return self.settings.name

    def __init__(self, settings: dict[str, Any], /):
        self.settings = self.configure(settings)
        self.uploader = self.make_uploader()
        self.manager = self.make_manager()
        self.reader = self.make_reader()

        self.capabilities = self.compute_capabilities()

    def make_uploader(self):
        return self.UploaderFactory(self)

    def make_manager(self):
        return self.ManagerFactory(self)

    def make_reader(self):
        return self.ReaderFactory(self)

    @classmethod
    def configure(cls, settings: dict[str, Any]) -> Any:
        try:
            return cls.SettingsFactory(**settings)
        except TypeError as err:
            raise exceptions.InvalidStorageConfigurationError(
                settings.get("name") or cls, str(err)
            ) from err

        # fields = dataclasses.fields(cls.SettingsFactory)
        # cls.SettingsFactory
        # names = {field.name for field in fields}  # initfields lost here

        # valid = {}
        # invalid = []
        # for k, v in settings.items():
        #     if k in names:
        #         valid[k] = v
        #     else:
        #         invalid.append(k)

        # cfg = cls.SettingsFactory(**valid)
        # if invalid:
        #     log.debug(
        #         "Storage %s received unknow settings: %s",
        #         cfg.name,
        #         invalid,
        #     )
        # return cfg

    def compute_capabilities(self) -> Capability:
        return (
            self.uploader.capabilities
            | self.manager.capabilities
            | self.reader.capabilities
        )

    def supports(self, operation: Capability) -> bool:
        """Check whether the storage supports operation."""
        return self.capabilities.can(operation)

    def supports_synthetic(self, operation: Capability, dest: Storage) -> bool:
        """Check if the storage can emulate operation using other operations."""
        if operation is Capability.RANGE:
            return self.supports(Capability.STREAM)

        if operation is Capability.COPY:
            return self.supports(Capability.STREAM) and dest.supports(
                Capability.CREATE,
            )

        if operation is Capability.MOVE:
            return self.supports(
                Capability.STREAM | Capability.REMOVE,
            ) and dest.supports(Capability.CREATE)

        if operation is Capability.COMPOSE:
            return self.supports(Capability.STREAM) and dest.supports(
                Capability.CREATE | Capability.APPEND | Capability.REMOVE
            )

        return False

    def prepare_location(self, location: str, /, **kwargs: Any) -> types.Location:
        """Transform and sanitize location using configured functions."""
        for name in self.settings.location_transformers:
            if transformer := location_transformers.get(name):
                location = transformer(location, kwargs)
            else:
                raise exceptions.LocationTransformerError(name)

        return types.Location(location)

    def stream_as_upload(self, data: data.FileData, **kwargs: Any) -> Upload:
        """Make an Upload with file content."""
        stream = self.stream(data, **kwargs)
        if hasattr(stream, "read"):
            stream = cast(types.PStream, stream)
        else:
            stream = utils.IterableBytesReader(stream)

        return Upload(
            stream,
            data.location,
            data.size,
            data.content_type,
        )

    @requires_capability(Capability.CREATE)
    def upload(
        self, location: types.Location, upload: Upload, /, **kwargs: Any
    ) -> data.FileData:
        """Upload data into specified location."""
        return self.uploader.upload(location, upload, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_start(
        self,
        location: types.Location,
        data: data.MultipartData,
        /,
        **kwargs: Any,
    ) -> data.MultipartData:
        """Initialize multipart upload."""
        return self.uploader.multipart_start(location, data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_refresh(
        self, data: data.MultipartData, /, **kwargs: Any
    ) -> data.MultipartData:
        """Return the current state of the multipart upload."""
        return self.uploader.multipart_refresh(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_update(
        self, data: data.MultipartData, /, **kwargs: Any
    ) -> data.MultipartData:
        """Update multipart upload."""
        return self.uploader.multipart_update(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_complete(
        self, data: data.MultipartData, /, **kwargs: Any
    ) -> data.FileData:
        """Finalize multipart upload."""
        return self.uploader.multipart_complete(data, kwargs)

    @requires_capability(Capability.EXISTS)
    def exists(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Test whether the file exists in the storage."""
        return self.manager.exists(data, kwargs)

    @requires_capability(Capability.REMOVE)
    def remove(
        self, data: data.FileData | data.MultipartData, /, **kwargs: Any
    ) -> bool:
        """Remove file from the storage."""
        return self.manager.remove(data, kwargs)

    @requires_capability(Capability.SCAN)
    def scan(self, **kwargs: Any) -> Iterable[str]:
        """Discover existing locations in the storage."""
        return self.manager.scan(kwargs)

    @requires_capability(Capability.ANALYZE)
    def analyze(self, location: types.Location, /, **kwargs: Any) -> data.FileData:
        """Return file details for the given location."""
        return self.manager.analyze(location, kwargs)

    @requires_capability(Capability.STREAM)
    def stream(self, data: data.FileData, /, **kwargs: Any) -> Iterable[bytes]:
        """Return the stream of file's content."""
        return self.reader.stream(data, kwargs)

    @requires_capability(Capability.RANGE)
    def range(
        self,
        data: data.FileData,
        start: int = 0,
        end: int | None = None,
        /,
        **kwargs: Any,
    ) -> Iterable[bytes]:
        """Return byte-stream of the file's fragment."""
        return self.reader.range(data, start, end, kwargs)

    def range_synthetic(
        self,
        data: data.FileData,
        start: int = 0,
        end: int | None = None,
        /,
        **kwargs: Any,
    ) -> Iterable[bytes]:
        """Generic implementation of range operation that relies on STREAM."""
        if end is None:
            end = cast(int, float("inf"))

        end -= start
        if end <= 0:
            return

        for chunk in self.stream(data, **kwargs):
            if start > 0:
                start -= len(chunk)
                if start < 0:
                    chunk = chunk[start:]
                else:
                    continue

            yield chunk[: end and None]
            end -= len(chunk)
            if end <= 0:
                break

    @requires_capability(Capability.STREAM)
    def content(self, data: data.FileData, /, **kwargs: Any) -> bytes:
        """Return content of the file."""
        return self.reader.content(data, kwargs)

    @requires_capability(Capability.APPEND)
    def append(
        self,
        data: data.FileData,
        upload: Upload,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        """Append data to the file."""
        return self.manager.append(data, upload, kwargs)

    @requires_capability(Capability.COPY)
    def copy(
        self,
        location: types.Location,
        data: data.FileData,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        """Copy file into specified location."""
        return self.manager.copy(location, data, kwargs)

    def copy_synthetic(
        self,
        location: types.Location,
        data: data.FileData,
        dest_storage: Storage,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        """Generic implementation of the copy operation that relies on CREATE."""
        return dest_storage.upload(
            location,
            self.stream_as_upload(data, **kwargs),
            **kwargs,
        )

    @requires_capability(Capability.MOVE)
    def move(
        self,
        location: types.Location,
        data: data.FileData,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        """Move file to specific location."""
        return self.manager.move(location, data, kwargs)

    def move_synthetic(
        self,
        location: types.Location,
        data: data.FileData,
        dest_storage: Storage,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        """Generic implementation of move operation that relies on CREATE and REMOVE."""
        result = dest_storage.upload(
            location,
            self.stream_as_upload(data, **kwargs),
            **kwargs,
        )
        self.remove(data)
        return result

    @requires_capability(Capability.COMPOSE)
    def compose(
        self,
        location: types.Location,
        /,
        *files: data.FileData,
        **kwargs: Any,
    ) -> data.FileData:
        """Combine multiple files into a new file."""
        return self.manager.compose(location, files, kwargs)

    def compose_synthetic(
        self,
        location: types.Location,
        dest_storage: Storage,
        /,
        *files: data.FileData,
        **kwargs: Any,
    ) -> data.FileData:
        """Generic composition that relies on APPEND"""
        result = dest_storage.upload(location, make_upload(b""), **kwargs)

        # when first append succeeded with the fragment of the file added
        # in the storage, and the following append failed, this incomplete
        # fragment must be removed.
        #
        # Expected reasons of failure are:
        #
        # * one of the source fiels is missing
        # * file will go over the size limit after the following append
        try:
            for item in files:
                result = dest_storage.append(
                    result,
                    self.stream_as_upload(item, **kwargs),
                    **kwargs,
                )
        except (exceptions.MissingFileError, exceptions.UploadError):
            self.remove(result, **kwargs)
            raise

        return result

    def one_time_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        """Link that can be used limited number of times."""
        if self.supports(Capability.ONE_TIME_LINK):
            return self.reader.one_time_link(data, kwargs)

    def temporal_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        """Link that remains valid for a limited duration of time."""
        if self.supports(Capability.TEMPORAL_LINK):
            return self.reader.temporal_link(data, kwargs)

    def permanent_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        """Link that remains valid as long as file exists."""
        if self.supports(Capability.PERMANENT_LINK):
            return self.reader.permanent_link(data, kwargs)


def make_storage(
    name: str,
    settings: dict[str, Any],
) -> Storage:
    """Initialize storage instance with specified settings.

    Storage adapter is defined by `type` key of the settings. The rest of
    settings depends on the specific adapter.

    Args:
        name: name of the storage
        settings: configuration for the storage

    Returns:
        storage instance

    Raises:
        exceptions.UnknownAdapterError: storage adapter is not registered

    Example:
        ```
        storage = make_storage("memo", {"type": "files:redis"})
        ```

    """
    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)
    if not adapter:
        raise exceptions.UnknownAdapterError(adapter_type)

    settings.setdefault("name", name)

    return adapter(settings)
