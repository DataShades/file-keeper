"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

import dataclasses
import itertools
import logging
from collections.abc import Callable
from io import BytesIO
from typing import Any, ClassVar, Iterable, cast

from typing_extensions import Concatenate, ParamSpec

import file_keeper

from . import data, exceptions, types, upload, utils
from .location import strategies as location_strategies

P = ParamSpec("P")

adapters = utils.Registry["type[Storage]"]({})

log = logging.getLogger(__name__)


def requires_capability(capability: utils.Capability):
    def decorator(func: Callable[Concatenate[Storage, P], types.T]):
        def method(self: Storage, *args: P.args, **kwargs: P.kwargs) -> types.T:
            if not self.supports(capability):
                raise exceptions.UnsupportedOperationError(str(capability.name), self)
            return func(self, *args, **kwargs)

        return method

    return decorator


class StorageService:
    """Base class for services used by storage.

    StorageService.capabilities reflect all operations provided by the
    service.

    >>> class Uploader(StorageService):
    >>>     capabilities = Capability.CREATE
    """

    capabilities = utils.Capability.NONE

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
                self, location: str, upload: Upload, extras: dict[str, Any]
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
        location: str,
        upload: upload.Upload,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Upload file using single stream."""
        raise NotImplementedError

    def multipart_start(
        self,
        location: str,
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
        datas: Iterable[data.FileData],
        location: str,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Combine multipe file inside the storage into a new one."""
        raise NotImplementedError

    def append(
        self,
        data: data.FileData,
        upload: upload.Upload,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Append content to existing file."""
        raise NotImplementedError

    def copy(
        self,
        data: data.FileData,
        location: str,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Copy file inside the storage."""
        raise NotImplementedError

    def move(
        self,
        data: data.FileData,
        location: str,
        extras: dict[str, Any],
    ) -> data.FileData:
        """Move file to a different location inside the storage."""
        raise NotImplementedError

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """List all locations(filenames) in storage."""
        raise NotImplementedError

    def analyze(self, location: str, extras: dict[str, Any]) -> data.FileData:
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
        """Return byte-stream of the file content."""
        ints = itertools.chain.from_iterable(self.stream(data, extras))

        if end and end < 0:
            end += data.size

        if start < 0:
            start += data.size

        fragment = bytes(itertools.islice(ints, start, end))
        return BytesIO(fragment)

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
    override_existing: bool = False
    supported_types: list[str] = dataclasses.field(default_factory=list)
    max_size: int = 0
    location_strategy: str = "transparent"

    _required_options: ClassVar[list[str]] = []

    def __post_init__(self):
        for attr in self._required_options:
            if not getattr(self, attr):
                raise exceptions.MissingStorageConfigurationError(self.name, attr)


class Storage:
    """Base class for storage implementation.

    Args:
        settings: storage configuration

    Example:
        ```python
        class MyStorage(Storage):
            def make_uploader(self):
                return MyUploader(self)

            def make_reader(self):
                return MyReader(self)

            def make_manager(self):
                return MyManager(self)
        ```
    """

    # do not show storage adapter
    hidden = False

    # operations that storage performs. Will be overriden by capabilities of
    # services inside constructor.
    capabilities = utils.Capability.NONE

    # settings: Settings

    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
    SettingsFactory = Settings

    def __str__(self):
        return self.settings.name

    def __init__(self, settings: dict[str, Any], /):
        self.settings = self.make_settings(settings)

        self.uploader = self.make_uploader()
        self.manager = self.make_manager()
        self.reader = self.make_reader()

        self.capabilities = self.compute_capabilities()

    @property
    def max_size(self) -> int:
        """Max allowed upload size.

        Max size set to 0 removes all limitations.

        """
        return self.settings.max_size

    @property
    def supported_types(self) -> list[str]:
        """List of supported MIMEtypes or their parts."""
        return self.settings.supported_types

    def compute_capabilities(self) -> utils.Capability:
        return (
            self.uploader.capabilities
            | self.manager.capabilities
            | self.reader.capabilities
        )

    def make_settings(self, settings: dict[str, Any] | Settings):
        if isinstance(settings, Settings):
            return settings

        fields = dataclasses.fields(self.SettingsFactory)
        names = {field.name for field in fields}

        valid = {}
        invalid = []
        for k, v in settings.items():
            if k in names:
                valid[k] = v
            else:
                invalid.append(k)

        result = self.SettingsFactory(**valid)

        log.debug("Storage %s received unknow settings: %s", result.name, invalid)

        return result

    def make_uploader(self):
        return self.UploaderFactory(self)

    def make_manager(self):
        return self.ManagerFactory(self)

    def make_reader(self):
        return self.ReaderFactory(self)

    def supports(self, operation: utils.Capability) -> bool:
        return self.capabilities.can(operation)

    def compute_location(
        self,
        location: str,
        upload: upload.Upload | None = None,
        /,
        **kwargs: Any,
    ) -> str:
        name = self.settings.location_strategy
        if strategy := location_strategies.get(name):
            return strategy(location, upload, kwargs)

        raise exceptions.NameStrategyError(name)

    def validate(self, upload: upload.Upload, /, **kwargs: Any):
        if self.max_size and upload.size > self.max_size:
            raise exceptions.LargeUploadError(upload.size, self.max_size)

        if self.supported_types and not utils.is_supported_type(
            upload.content_type,
            self.supported_types,
        ):
            raise exceptions.WrongUploadTypeError(upload.content_type)

    @requires_capability(utils.Capability.CREATE)
    def upload(
        self, location: str, upload: upload.Upload, /, **kwargs: Any
    ) -> data.FileData:
        self.validate(upload, **kwargs)

        return self.uploader.upload(location, upload, kwargs)

    @requires_capability(utils.Capability.MULTIPART)
    def multipart_start(
        self,
        name: str,
        data: data.MultipartData,
        /,
        **kwargs: Any,
    ) -> data.MultipartData:
        return self.uploader.multipart_start(name, data, kwargs)

    @requires_capability(utils.Capability.MULTIPART)
    def multipart_refresh(
        self, data: data.MultipartData, /, **kwargs: Any
    ) -> data.MultipartData:
        return self.uploader.multipart_refresh(data, kwargs)

    @requires_capability(utils.Capability.MULTIPART)
    def multipart_update(
        self, data: data.MultipartData, /, **kwargs: Any
    ) -> data.MultipartData:
        return self.uploader.multipart_update(data, kwargs)

    @requires_capability(utils.Capability.MULTIPART)
    def multipart_complete(
        self, data: data.MultipartData, /, **kwargs: Any
    ) -> data.FileData:
        return self.uploader.multipart_complete(data, kwargs)

    @requires_capability(utils.Capability.EXISTS)
    def exists(self, data: data.FileData, /, **kwargs: Any) -> bool:
        return self.manager.exists(data, kwargs)

    @requires_capability(utils.Capability.REMOVE)
    def remove(
        self, data: data.FileData | data.MultipartData, /, **kwargs: Any
    ) -> bool:
        return self.manager.remove(data, kwargs)

    @requires_capability(utils.Capability.SCAN)
    def scan(self, **kwargs: Any) -> Iterable[str]:
        return self.manager.scan(kwargs)

    @requires_capability(utils.Capability.ANALYZE)
    def analyze(self, location: str, /, **kwargs: Any) -> data.FileData:
        return self.manager.analyze(location, kwargs)

    @requires_capability(utils.Capability.STREAM)
    def stream(self, data: data.FileData, /, **kwargs: Any) -> Iterable[bytes]:
        return self.reader.stream(data, kwargs)

    @requires_capability(utils.Capability.RANGE)
    def range(
        self,
        data: data.FileData,
        start: int = 0,
        end: int | None = None,
        /,
        **kwargs: Any,
    ) -> Iterable[bytes]:
        """Return byte-stream of the file content."""
        return self.reader.range(data, start, end, kwargs)

    @requires_capability(utils.Capability.STREAM)
    def content(self, data: data.FileData, /, **kwargs: Any) -> bytes:
        return self.reader.content(data, kwargs)

    def copy(
        self,
        data: data.FileData,
        storage: Storage,
        location: str,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        if storage is self and self.supports(utils.Capability.COPY):
            return self.manager.copy(data, location, kwargs)

        if self.supports(utils.Capability.STREAM) and storage.supports(
            utils.Capability.CREATE,
        ):
            return storage.upload(
                location,
                self.stream_as_upload(data, **kwargs),
                **kwargs,
            )

        raise exceptions.UnsupportedOperationError("copy", self)

    def compose(
        self,
        storage: Storage,
        location: str,
        /,
        *datas: data.FileData,
        **kwargs: Any,
    ) -> data.FileData:
        if storage is self and self.supports(utils.Capability.COMPOSE):
            return self.manager.compose(datas, location, kwargs)

        if self.supports(utils.Capability.STREAM) and storage.supports(
            utils.Capability.CREATE | utils.Capability.APPEND,
        ):
            dest_data = storage.upload(location, file_keeper.make_upload(b""), **kwargs)
            for data in datas:
                dest_data = storage.append(
                    dest_data,
                    self.stream_as_upload(data, **kwargs),
                    **kwargs,
                )
            return dest_data

        raise exceptions.UnsupportedOperationError("compose", self)

    def stream_as_upload(self, data: data.FileData, **kwargs: Any) -> upload.Upload:
        """Make an Upload with file content."""
        stream = self.stream(data, **kwargs)
        if hasattr(stream, "read"):
            stream = cast(types.PStream, stream)
        else:
            stream = utils.IterableBytesReader(stream)

        return upload.Upload(
            stream,
            data.location,
            data.size,
            data.content_type,
        )

    @requires_capability(utils.Capability.APPEND)
    def append(
        self,
        data: data.FileData,
        upload: upload.Upload,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        return self.manager.append(data, upload, kwargs)

    def move(
        self,
        data: data.FileData,
        storage: Storage,
        location: str,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        if storage is self and self.supports(utils.Capability.MOVE):
            return self.manager.move(data, location, kwargs)

        if self.supports(
            utils.Capability.STREAM | utils.Capability.REMOVE,
        ) and storage.supports(utils.Capability.CREATE):
            result = storage.upload(
                location,
                self.stream_as_upload(data, **kwargs),
                **kwargs,
            )
            storage.remove(data)
            return result

        raise exceptions.UnsupportedOperationError("move", self)

    def public_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        if self.supports(utils.Capability.PUBLIC_LINK):
            return self.reader.public_link(data, kwargs)

    def one_time_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        if self.supports(utils.Capability.ONE_TIME_LINK):
            return self.reader.one_time_link(data, kwargs)

    def temporal_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        if self.supports(utils.Capability.TEMPORAL_LINK):
            return self.reader.temporal_link(data, kwargs)

    def permanent_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        if self.supports(utils.Capability.PERMANENT_LINK):
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
