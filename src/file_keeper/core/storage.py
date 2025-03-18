"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Callable, ClassVar, Iterable, cast

from typing_extensions import Concatenate, ParamSpec, TypeAlias, TypeVar

from . import data, exceptions, types, upload, utils
from .registry import Registry

P = ParamSpec("P")
T = TypeVar("T")


log = logging.getLogger(__name__)

LocationTransformer: TypeAlias = Callable[[str, "dict[str, Any]"], str]

adapters = Registry["type[Storage]"]()
location_transformers = Registry[LocationTransformer]()


def requires_capability(capability: utils.Capability):
    def decorator(func: Callable[Concatenate[Storage, P], T]):
        def method(self: Storage, *args: P.args, **kwargs: P.kwargs) -> T:
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
        upload: upload.Upload,
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
        upload: upload.Upload,
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


class Validator(StorageService):
    """Service responsible for validation of data and uploads."""

    def size(self, size: int):
        max_size = self.storage.settings.max_size
        if max_size and size > max_size:
            raise exceptions.LargeUploadError(size, max_size)

    def content_type(self, content_type: str):
        supported_types = self.storage.settings.supported_types
        if supported_types and not utils.is_supported_type(
            content_type,
            supported_types,
        ):
            raise exceptions.WrongUploadTypeError(content_type)

    def upload(self, upload: upload.Upload, /, **kwargs: Any):
        self.size(upload.size)
        self.content_type(upload.content_type)

    def data(self, data: data.BaseData, /, **kwargs: Any):
        self.size(data.size)
        self.content_type(data.content_type)


@dataclasses.dataclass()
class Settings:
    name: str = "unknown"
    override_existing: bool = False
    supported_types: list[str] = dataclasses.field(default_factory=list)
    max_size: int = 0
    location_transformers: list[str] = dataclasses.field(default_factory=list)

    _required_options: ClassVar[list[str]] = []

    def __post_init__(self, **kwargs: Any):
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

    settings: Settings
    SettingsFactory: type[Settings] = Settings

    UploaderFactory: type[Uploader] = Uploader
    ManagerFactory: type[Manager] = Manager
    ReaderFactory: type[Reader] = Reader
    ValidatorFactory: Callable[[Storage], Validator] = Validator

    def __str__(self):
        return self.settings.name

    def __init__(self, settings: dict[str, Any], /):
        self.settings = self.configure(settings)
        self.uploader = self.make_uploader()
        self.manager = self.make_manager()
        self.reader = self.make_reader()
        self.validator = self.make_validator()

        self.capabilities = self.compute_capabilities()

    def make_validator(self):
        return self.ValidatorFactory(self)

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

    def compute_capabilities(self) -> utils.Capability:
        return (
            self.uploader.capabilities
            | self.manager.capabilities
            | self.reader.capabilities
        )

    def supports(self, operation: utils.Capability) -> bool:
        return self.capabilities.can(operation)

    def prepare_location(self, location: str, /, **kwargs: Any) -> types.Location:
        for name in self.settings.location_transformers:
            if transformer := location_transformers.get(name):
                location = transformer(location, kwargs)
            else:
                raise exceptions.LocationTransformerError(name)

        return types.Location(location)

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

    @requires_capability(utils.Capability.CREATE)
    def upload(
        self, location: types.Location, upload: upload.Upload, /, **kwargs: Any
    ) -> data.FileData:
        self.validator.upload(upload, **kwargs)
        return self.uploader.upload(location, upload, kwargs)

    @requires_capability(utils.Capability.MULTIPART)
    def multipart_start(
        self,
        location: types.Location,
        data: data.MultipartData,
        /,
        **kwargs: Any,
    ) -> data.MultipartData:
        self.validator.data(data, **kwargs)
        return self.uploader.multipart_start(location, data, kwargs)

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
    def analyze(self, location: types.Location, /, **kwargs: Any) -> data.FileData:
        return self.manager.analyze(location, kwargs)

    @requires_capability(utils.Capability.STREAM)
    def stream(self, data: data.FileData, /, **kwargs: Any) -> Iterable[bytes]:
        return self.reader.stream(data, kwargs)

    def range(
        self,
        data: data.FileData,
        start: int = 0,
        end: int | None = None,
        /,
        **kwargs: Any,
    ) -> Iterable[bytes]:
        """Return byte-stream of the file content."""
        if self.supports(utils.Capability.RANGE):
            return self.reader.range(data, start, end, kwargs)

        if self.supports(utils.Capability.STREAM):
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

                yield chunk[:end and None]
                end -= len(chunk)
                if end <= 0:
                    break
            return

        raise exceptions.UnsupportedOperationError("range", self)

    @requires_capability(utils.Capability.STREAM)
    def content(self, data: data.FileData, /, **kwargs: Any) -> bytes:
        return self.reader.content(data, kwargs)

    @requires_capability(utils.Capability.APPEND)
    def append(
        self,
        data: data.FileData,
        upload: upload.Upload,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        return self.manager.append(data, upload, kwargs)

    def copy(
        self,
        location: types.Location,
        data: data.FileData,
        dest_storage: Storage,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        if dest_storage is self and self.supports(utils.Capability.COPY):
            return self.manager.copy(location, data, kwargs)

        if self.supports(utils.Capability.STREAM) and dest_storage.supports(
            utils.Capability.CREATE,
        ):
            return dest_storage.upload(
                location,
                self.stream_as_upload(data, **kwargs),
                **kwargs,
            )

        raise exceptions.UnsupportedOperationError("copy", self)

    def move(
        self,
        location: types.Location,
        data: data.FileData,
        dest_storage: Storage,
        /,
        **kwargs: Any,
    ) -> data.FileData:
        if dest_storage is self and self.supports(utils.Capability.MOVE):
            return self.manager.move(location, data, kwargs)

        if self.supports(
            utils.Capability.STREAM | utils.Capability.REMOVE,
        ) and dest_storage.supports(utils.Capability.CREATE):
            result = dest_storage.upload(
                location,
                self.stream_as_upload(data, **kwargs),
                **kwargs,
            )
            dest_storage.remove(data)
            return result

        raise exceptions.UnsupportedOperationError("move", self)

    def compose(
        self,
        location: types.Location,
        dest_storage: Storage,
        /,
        *files: data.FileData,
        **kwargs: Any,
    ) -> data.FileData:
        if dest_storage is self and self.supports(utils.Capability.COMPOSE):
            return self.manager.compose(location, files, kwargs)

        # REMOVE capability is required for cleaning. Alternatively, we can
        # compute expected size and check existence in advance. But this is
        # just a fallback method - use explicit implementation for efficiency.
        if self.supports(utils.Capability.STREAM) and dest_storage.supports(
            utils.Capability.CREATE | utils.Capability.APPEND | utils.Capability.REMOVE
        ):
            result = dest_storage.upload(location, upload.make_upload(b""), **kwargs)

            # append creates file only when there are no problems. But when
            # first append succeeded with the fragment of the file added in the
            # storage, and the following append failed, this incomplete
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

        raise exceptions.UnsupportedOperationError("compose", self)

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
