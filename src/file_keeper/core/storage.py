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
import inspect
import logging
import os
from abc import ABC
from collections.abc import Callable, Iterable, Mapping
from typing import Any, ClassVar, cast

from typing_extensions import ParamSpec, TypeAlias, TypeVar, override

from . import data, exceptions, types, utils
from .registry import Registry
from .upload import Upload, make_upload

P = ParamSpec("P")
T = TypeVar("T")
S = TypeVar("S", bound="Storage")
TCallable = TypeVar("TCallable", bound=Callable[..., Any])

log = logging.getLogger(__name__)

Capability: TypeAlias = utils.Capability

adapters = Registry["type[Storage]"]()
location_transformers = Registry[types.LocationTransformer]()


def requires_capability(capability: Capability):
    """Decorator to ensure a method requires a specific capability."""

    def decorator(func: TCallable) -> TCallable:
        """Wraps the function to check for the required capability."""

        @functools.wraps(func)
        def method(self: Any, *args: Any, **kwargs: Any):
            """Executes the function if the capability is supported."""
            if not self.supports(capability):
                raise exceptions.UnsupportedOperationError(str(capability.name), self)
            return func(self, *args, **kwargs)

        return cast(Any, method)

    return decorator


class StorageService:
    """Base class for services used by storage.

    StorageService.capabilities reflect all operations provided by the
    service.

    Examples:
        >>> class Uploader(StorageService):
        >>>     capabilities = Capability.CREATE
    """

    capabilities: Capability = Capability.NONE

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
                self, location: types.Location, upload: Upload, extras: dict[str, Any]
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

    def upload(self, location: types.Location, upload: Upload, extras: dict[str, Any]) -> data.FileData:
        """Upload file using single stream.

        Args:
            location: The destination location for the upload.
            upload: The Upload object containing the file data.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def resumable_start(self, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Prepare everything for resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def resumable_refresh(self, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Show details of the incomplete resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def resumable_resume(self, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Resume the interrupted resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def resumable_remove(self, data: data.FileData, extras: dict[str, Any]) -> bool:
        """Remove incomplete resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def multipart_start(self, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Prepare everything for multipart(resumable) upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def multipart_refresh(self, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Show details of the incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def multipart_update(self, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Add data to the incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def multipart_complete(self, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Verify file integrity and finalize incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError

    def multipart_remove(self, data: data.FileData, extras: dict[str, Any]) -> bool:
        """Interrupt and remove incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            extras: Additional metadata for the upload.
        """
        raise NotImplementedError


class Manager(StorageService):
    """Service responsible for maintenance file operations.

    `Storage` internally calls methods of this service. For example,
    `Storage.remove(data, **kwargs)` results in `Manager.remove(data, kwargs)`.

    Example:
        ```python
        class MyManager(Manager):
            def remove(
                self, data: FileData|FileData, extras: dict[str, Any]
            ) -> bool:
                os.remove(data.location)
                return True
        ```
    """

    def remove(self, data: data.FileData, extras: dict[str, Any]) -> bool:
        """Remove file from the storage.

        Args:
            data: The FileData object representing the file to remove.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def exists(self, data: data.FileData, extras: dict[str, Any]) -> bool:
        """Check if file exists in the storage.

        Args:
            data: The FileData object representing the file to check.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def compose(
        self, location: types.Location, datas: Iterable[data.FileData], extras: dict[str, Any]
    ) -> data.FileData:
        """Combine multipe file inside the storage into a new one.

        Args:
            location: The destination location for the composed file.
            datas: An iterable of FileData objects representing the files to combine.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def append(self, data: data.FileData, upload: Upload, extras: dict[str, Any]) -> data.FileData:
        """Append content to existing file.

        Args:
            data: The FileData object representing the file to append to.
            upload: The Upload object containing the content to append.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def copy(self, location: types.Location, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Copy file inside the storage.

        Args:
            location: The destination location for the copied file.
            data: The FileData object representing the file to copy.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def move(self, location: types.Location, data: data.FileData, extras: dict[str, Any]) -> data.FileData:
        """Move file to a different location inside the storage.

        Args:
            location: The destination location for the moved file.
            data: The FileData object representing the file to move.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """List all locations(filenames) in storage.

        Args:
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def analyze(self, location: types.Location, extras: dict[str, Any]) -> data.FileData:
        """Return details about location.

        Args:
            location: The location of the file to analyze.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def signed(
        self, action: types.SignedAction, duration: int, location: types.Location, extras: dict[str, Any]
    ) -> str:
        """Make an URL for signed action.

        Args:
            action: The action to sign (e.g., "upload", "download").
            duration: The duration for which the signed URL is valid.
            location: The location of the file to sign.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError


class Reader(StorageService):
    """Service responsible for reading data from the storage.

    `Storage` internally calls methods of this service. For example,
    `Storage.stream(data, **kwargs)` results in `Reader.stream(data, kwargs)`.

    Example:
        ```python
        class MyReader(Reader):
            def stream(
                self, data: data.FileData, extras: dict[str, Any]
            ) -> Iterable[bytes]:
                return open(data.location, "rb")
        ```
    """

    def stream(self, data: data.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        """Return byte-stream of the file content.

        Args:
            data: The FileData object representing the file to stream.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def content(self, data: data.FileData, extras: dict[str, Any]) -> bytes:
        """Return file content as a single byte object.

        Args:
            data: The FileData object representing the file to read.
            extras: Additional metadata for the operation.
        """
        return b"".join(self.stream(data, extras))

    def range(self, data: data.FileData, start: int, end: int | None, extras: dict[str, Any]) -> Iterable[bytes]:
        """Return slice of the file content.

        Args:
            data: The FileData object representing the file to read.
            start: The starting byte offset.
            end: The ending byte offset (inclusive).
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def permanent_link(self, data: data.FileData, extras: dict[str, Any]) -> str:
        """Return permanent download link.

        Args:
            data: The FileData object representing the file.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def temporal_link(self, data: data.FileData, duration: int, extras: dict[str, Any]) -> str:
        """Return temporal download link.

        Args:
            data: The FileData object representing the file.
            duration: The duration for which the link is valid.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def one_time_link(self, data: data.FileData, extras: dict[str, Any]) -> str:
        """Return one-time download link.

        Args:
            data: The FileData object representing the file.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError


@dataclasses.dataclass()
class Settings:
    """Settings for the storage adapter."""

    name: str = "unknown"
    """Descriptive name of the storage used for debugging."""

    override_existing: bool = False
    """If file already exists, replace it with new content."""

    path: str = ""
    """Prefix for the file's location."""

    location_transformers: list[str] = cast("list[str]", dataclasses.field(default_factory=list))
    """List of transformations applied to the file location."""

    disabled_capabilities: list[str] = cast("list[str]", dataclasses.field(default_factory=list))
    """Capabilities that are not supported even if implemented."""

    initialize: bool = False
    """Prepare storage backend for uploads(create path, bucket, DB)"""

    _required_options: ClassVar[list[str]] = []
    _extra_settings: dict[str, Any] = cast("dict[str, Any]", dataclasses.field(default_factory=dict))

    def __post_init__(self, **kwargs: Any):
        for attr in self._required_options:
            if not getattr(self, attr):
                raise exceptions.MissingStorageConfigurationError(self.name, attr)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Settings:
        """Make settings object using dictionary as a source.

        Any unexpected options are extracted from the `data` to avoid
        initialization errors from dataclass constructor.

        Args:
            data: mapping with settings

        Returns:
            settings object built from data

        """
        # try:
        #     return cls(**settings)
        # except TypeError as err:
        #     raise exceptions.InvalidStorageConfigurationError(
        #         settings.get("name") or cls, str(err)
        #     ) from err

        sig = inspect.signature(cls)
        names = set(sig.parameters)

        valid = {}
        invalid = {}
        for k, v in data.items():
            if k in names:
                valid[k] = v
            else:
                invalid[k] = v

        valid.setdefault("_extra_settings", {}).update(invalid)
        cfg = cls(**valid)
        if invalid:
            log.warning(
                "Storage %s received unknow settings: %s",
                cfg.name,
                invalid,
            )
        return cfg


class Storage(ABC):  # noqa: B024
    """Base class for storage implementation.

    Args:
        settings: storage configuration

    Example:
        ```py
        class MyStorage(Storage):
            SettingsFactory = MySettings
            UploaderFactory = MyUploader
            ManagerFactory = MyManager
            ReaderFactory = MyReader
        ```
    """

    # do not show storage adapter
    hidden: bool = False
    """Flag that marks unsafe/experimental storages."""

    capabilities: Capability = Capability.NONE
    """Operations supported by storage. Computed from capabilities of
    services during storage initialization."""

    SettingsFactory: ClassVar[type[Settings]] = Settings
    """Factory class for storage settings."""
    UploaderFactory: ClassVar[type[Uploader]] = Uploader
    """Factory class for uploader service."""
    ManagerFactory: ClassVar[type[Manager]] = Manager
    """Factory class for manager service."""
    ReaderFactory: ClassVar[type[Reader]] = Reader
    """Factory class for reader service."""

    @override
    def __str__(self) -> str:
        return self.settings.name

    def __init__(self, settings: Mapping[str, Any] | Settings, /):
        self.settings = self.configure(settings)
        self.uploader = self.make_uploader()
        self.manager = self.make_manager()
        self.reader = self.make_reader()

        self.capabilities = self.compute_capabilities()

    def make_uploader(self):
        """Initialize [uploader][file_keeper.Uploader] service."""
        return self.UploaderFactory(self)

    def make_manager(self):
        """Initialize [manager][file_keeper.Manager] service."""
        return self.ManagerFactory(self)

    def make_reader(self):
        """Initialize [reader][file_keeper.Reader] service."""
        return self.ReaderFactory(self)

    @classmethod
    def configure(cls, settings: Mapping[str, Any] | Settings) -> Settings:
        """Initialize storage configuration.

        This method is responsible for transforming mapping with options into
        storage's settings. It also can initialize additional services and
        perform extra work, like verifying that storage is ready to accept
        uploads.

        Args:
            settings: mapping with storage configuration

        """
        if isinstance(settings, Settings):
            return settings

        return cls.SettingsFactory.from_dict(settings)

    def compute_capabilities(self) -> Capability:
        """Computes the capabilities of the storage based on its services."""
        result = self.uploader.capabilities | self.manager.capabilities | self.reader.capabilities

        for name in self.settings.disabled_capabilities:
            result = result.exclude(Capability[name])

        return result

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

    def full_path(self, location: types.Location, /, **kwargs: Any) -> str:
        """Compute path to the file from the storage's root.

        Args:
            location: location of the file object
            **kwargs: exra parameters for custom storages

        Returns:
            full path required to access location
        """
        return os.path.join(self.settings.path, location)

    def prepare_location(
        self, location: str, upload_or_data: data.BaseData | Upload | None = None, /, **kwargs: Any
    ) -> types.Location:
        """Transform and sanitize location using configured functions."""
        for name in self.settings.location_transformers:
            if transformer := location_transformers.get(name):
                location = transformer(location, upload_or_data, kwargs)
            else:
                raise exceptions.LocationTransformerError(name)

        return types.Location(location)

    def file_as_upload(self, data: data.FileData, **kwargs: Any) -> Upload:
        """Make an [Upload][file_keeper.Upload] with file content.

        Args:
            data: The FileData object to wrap into Upload
            **kwargs: Additional metadata for the upload.
        """
        stream = self.stream(data, **kwargs)
        stream = cast(types.PStream, stream) if hasattr(stream, "read") else utils.IterableBytesReader(stream)

        return Upload(
            stream,
            data.location,
            data.size,
            data.content_type,
        )

    @requires_capability(Capability.CREATE)
    def upload(self, location: types.Location, upload: Upload, /, **kwargs: Any) -> data.FileData:
        """Upload file using single stream.

        Args:
            location: The destination location for the upload.
            upload: The Upload object containing the file data.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.upload(location, upload, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_start(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Prepare everything for resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.resumable_start(data, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_refresh(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Show details of the incomplete resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.resumable_refresh(data, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_resume(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Resume the interrupted resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.resumable_resume(data, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_remove(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Remove incomplete resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.resumable_remove(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_start(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Prepare everything for multipart upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.multipart_start(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_refresh(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Show details of the incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.multipart_refresh(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_update(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Add data to the incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.multipart_update(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_complete(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Verify file integrity and finalize incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.multipart_complete(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_remove(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Interrupt and remove incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.
        """
        return self.uploader.multipart_remove(data, kwargs)

    @requires_capability(Capability.EXISTS)
    def exists(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Check if file exists in the storage.

        Args:
            data: The FileData object representing the file to check.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.exists(data, kwargs)

    @requires_capability(Capability.REMOVE)
    def remove(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Remove file from the storage.

        Args:
            data: The FileData object representing the file to remove.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.remove(data, kwargs)

    @requires_capability(Capability.SCAN)
    def scan(self, **kwargs: Any) -> Iterable[str]:
        """List all locations(filenames) in storage.

        Args:
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.scan(kwargs)

    @requires_capability(Capability.ANALYZE)
    def analyze(self, location: types.Location, /, **kwargs: Any) -> data.FileData:
        """Return file details.

        Args:
            location: The location of the file to analyze.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.analyze(location, kwargs)

    @requires_capability(Capability.SIGNED)
    def signed(
        self,
        action: types.SignedAction,
        duration: int,
        location: types.Location,
        **kwargs: Any,
    ) -> str:
        """Make an URL for signed action.

        Args:
            action: The action to sign (e.g., "upload", "download").
            duration: The duration for which the signed URL is valid.
            location: The location of the file to sign.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.signed(action, duration, location, kwargs)

    @requires_capability(Capability.STREAM)
    def stream(self, data: data.FileData, /, **kwargs: Any) -> Iterable[bytes]:
        """Return byte-stream of the file content.

        Args:
            data: The FileData object representing the file to stream.
            **kwargs: Additional metadata for the operation.
        """
        return self.reader.stream(data, kwargs)

    @requires_capability(Capability.RANGE)
    def range(self, data: data.FileData, start: int = 0, end: int | None = None, /, **kwargs: Any) -> Iterable[bytes]:
        """Return slice of the file content.

        Args:
            data: The FileData object representing the file to read.
            start: The starting byte offset.
            end: The ending byte offset (inclusive).
            **kwargs: Additional metadata for the operation.
        """
        return self.reader.range(data, start, end, kwargs)

    def range_synthetic(
        self, data: data.FileData, start: int = 0, end: int | None = None, /, **kwargs: Any
    ) -> Iterable[bytes]:
        """Generic implementation of range operation that relies on [STREAM][file_keeper.Capability.STREAM].

        Args:
            data: The FileData object representing the file to read.
            start: The starting byte offset.
            end: The ending byte offset (inclusive).
            **kwargs: Additional metadata for the operation.
        """
        if end is None:
            end = cast(int, float("inf"))

        end -= start
        if end <= 0:
            return

        for chunk in self.stream(data, **kwargs):
            if start > 0:
                start -= len(chunk)
                if start < 0:
                    chunk = chunk[start:]  # noqa: PLW2901
                else:
                    continue

            yield chunk[: end and None]
            end -= len(chunk)
            if end <= 0:
                break

    @requires_capability(Capability.STREAM)
    def content(self, data: data.FileData, /, **kwargs: Any) -> bytes:
        """Return file content as a single byte object.

        Args:
            data: The FileData object representing the file to read.
            **kwargs: Additional metadata for the operation.
        """
        return self.reader.content(data, kwargs)

    @requires_capability(Capability.APPEND)
    def append(self, data: data.FileData, upload: Upload, /, **kwargs: Any) -> data.FileData:
        """Append content to existing file.

        Args:
            data: The FileData object representing the file to append to.
            upload: The Upload object containing the content to append.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.append(data, upload, kwargs)

    @requires_capability(Capability.COPY)
    def copy(self, location: types.Location, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Copy file inside the storage.

        Args:
            location: The destination location for the copied file.
            data: The FileData object representing the file to copy.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.copy(location, data, kwargs)

    def copy_synthetic(
        self, location: types.Location, data: data.FileData, dest_storage: Storage, /, **kwargs: Any
    ) -> data.FileData:
        """Generic implementation of the copy operation that relies on [CREATE][file_keeper.Capability.CREATE].

        Args:
            location: The destination location for the copied file.
            data: The FileData object representing the file to copy.
            dest_storage: The destination storage
            **kwargs: Additional metadata for the operation.
        """
        return dest_storage.upload(
            location,
            self.file_as_upload(data, **kwargs),
            **kwargs,
        )

    @requires_capability(Capability.MOVE)
    def move(self, location: types.Location, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Move file to a different location inside the storage.

        Args:
            location: The destination location for the moved file.
            data: The FileData object representing the file to move.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.move(location, data, kwargs)

    def move_synthetic(
        self, location: types.Location, data: data.FileData, dest_storage: Storage, /, **kwargs: Any
    ) -> data.FileData:
        """Generic implementation of move operation.

        Relies on [CREATE][file_keeper.Capability.CREATE] and
        [REMOVE][file_keeper.Capability.REMOVE].

        Args:
            location: The destination location for the moved file.
            data: The FileData object representing the file to move.
            dest_storage: The destination storage
            **kwargs: Additional metadata for the operation.

        """
        result = dest_storage.upload(location, self.file_as_upload(data, **kwargs), **kwargs)
        self.remove(data)
        return result

    @requires_capability(Capability.COMPOSE)
    def compose(self, location: types.Location, /, *files: data.FileData, **kwargs: Any) -> data.FileData:
        """Combine multiple files into a new file.

        Args:
            location: The destination location for the composed file.
            *files: FileData objects representing the files to combine.
            **kwargs: Additional metadata for the operation.
        """
        return self.manager.compose(location, files, kwargs)

    def compose_synthetic(
        self, location: types.Location, dest_storage: Storage, /, *files: data.FileData, **kwargs: Any
    ) -> data.FileData:
        """Generic composition that relies on [APPEND][file_keeper.Capability.APPEND].

        Args:
            location: The destination location for the composed file.
            dest_storage: The destination storage
            *files: FileData objects representing the files to combine.
            **kwargs: Additional metadata for the operation.
        """
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
                    self.file_as_upload(item, **kwargs),
                    **kwargs,
                )
        except (exceptions.MissingFileError, exceptions.UploadError):
            self.remove(result, **kwargs)
            raise

        return result

    def one_time_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        """Return one-time download link.

        Args:
            data: The FileData object representing the file.
            **kwargs: Additional metadata for the operation.
        """
        if self.supports(Capability.ONE_TIME_LINK):
            return self.reader.one_time_link(data, kwargs)

    def temporal_link(self, data: data.FileData, duration: int, /, **kwargs: Any) -> str | None:
        """Return temporal download link.

        Args:
            data: The FileData object representing the file.
            duration: The duration for which the link is valid.
            **kwargs: Additional metadata for the operation.
        """
        if self.supports(Capability.TEMPORAL_LINK):
            return self.reader.temporal_link(data, duration, kwargs)

    def permanent_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        """Return permanent download link.

        Args:
            data: The FileData object representing the file.
            **kwargs: Additional metadata for the operation.
        """
        if self.supports(Capability.PERMANENT_LINK):
            return self.reader.permanent_link(data, kwargs)


def make_storage(name: str, settings: dict[str, Any]) -> Storage:
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
