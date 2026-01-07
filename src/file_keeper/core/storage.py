"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

import dataclasses
import fnmatch
import functools
import inspect
import json
import logging
import os
import pathlib
from abc import ABC
from collections.abc import Callable, Iterable, Mapping
from typing import Any, ClassVar, Literal, TypeAlias, cast

from typing_extensions import ParamSpec, TypeVar, override

from . import data, exceptions, types, utils
from .registry import Registry
from .upload import Upload, make_upload

try:
    from platformdirs import user_config_dir  # pyright: ignore[reportAssignmentType]
except ImportError:

    def user_config_dir(
        appname: str | None = None,
        appauthor: str | Literal[False] | None = None,
    ):
        """Mock for user config locator."""
        return


try:
    import tomllib as toml  # pyright: ignore[reportMissingImports]
except ImportError:
    try:
        import tomli as toml
    except ImportError:
        toml = None

try:
    import yaml
except ImportError:
    yaml = None


P = ParamSpec("P")
T = TypeVar("T")
S = TypeVar("S", bound="Storage")
TCallable = TypeVar("TCallable", bound=Callable[..., Any])

log = logging.getLogger(__name__)

Capability: TypeAlias = utils.Capability

adapters = Registry["type[Storage]"]()
storages = Registry["Storage"]()

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

    Example:
        ```py
        class Uploader(StorageService):
            capabilities = Capability.CREATE
        ```
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
            capabilities = Capability.CREATE

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

    def resumable_start(self, location: types.Location, size: int, extras: dict[str, Any]) -> data.FileData:
        """Prepare everything for resumable upload.

        Args:
            location: The destination location for the upload.
            size: Expected upload size.
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

    def resumable_resume(self, data: data.FileData, upload: Upload, extras: dict[str, Any]) -> data.FileData:
        """Resume the interrupted resumable upload.

        Args:
            data: The FileData object containing the upload metadata.
            upload: The Upload object containing the content.
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

    def multipart_start(self, location: types.Location, size: int, extras: dict[str, Any]) -> data.FileData:
        """Prepare everything for multipart(resumable) upload.

        Args:
            location: The destination location for the upload.
            size: Expected upload size.
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

    def multipart_update(self, data: data.FileData, upload: Upload, part: int, extras: dict[str, Any]) -> data.FileData:
        """Add data to the incomplete upload.

        Args:
            data: The FileData object containing the upload metadata.
            upload: The Upload object containing the content.
            part: Position of the given part among other parts, starting with 0.
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
            capabilities = Capability.REMOVE
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
        """Combine multiple file inside the storage into a new one.

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

    def filtered_scan(self, prefix: str, glob: str, extras: dict[str, Any]) -> Iterable[str]:
        """List all locations(filenames) in storage that match prefix and glob.

        Args:
            prefix: The prefix to filter locations.
            glob: The glob pattern to filter locations.
            extras: Additional metadata for the operation.
        """
        names = self.scan(extras)
        if glob:
            names = fnmatch.filter(names, glob)

        if prefix:
            names = filter(lambda n: n.startswith(prefix), names)

        yield from names

    def analyze(self, location: types.Location, extras: dict[str, Any]) -> data.FileData:
        """Return details about location.

        Args:
            location: The location of the file to analyze.
            extras: Additional metadata for the operation.
        """
        raise NotImplementedError

    def size(self, location: types.Location, extras: dict[str, Any]) -> int:
        """Return size of the file in bytes.

        Args:
            location: The location of the file.
            extras: Additional metadata for the operation.
        """
        return self.analyze(location, extras).size

    def hash(self, location: types.Location, extras: dict[str, Any]) -> str:
        """Return hash of the file.

        Args:
            location: The location of the file.
            extras: Additional metadata for the operation.
        """
        return self.analyze(location, extras).hash

    def content_type(self, location: types.Location, extras: dict[str, Any]) -> str:
        """Return MIME type of the file.

        Args:
            location: The location of the file.
            extras: Additional metadata for the operation.
        """
        return self.analyze(location, extras).content_type

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
            capabilities = Capability.STREAM

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

    skip_in_place_move: bool = True
    """Skip in-place move operations."""

    skip_in_place_copy: bool = True
    """Skip in-place copy operations."""

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
                "Storage %s received unknown settings: %s",
                cfg.name,
                invalid,
            )
        return cfg


class Storage(ABC):  # noqa: B024
    """Base class for storage implementation.

    Args:
        settings: storage configuration

    Example:
        Extend base class to implement custom storage
        ```py
        class MyStorage(Storage):
            SettingsFactory = Settings
            UploaderFactory = Uploader
            ManagerFactory = Manager
            ReaderFactory = Reader
        ```
        then initialize it using required settings
        ```py
        my_storage = MyStorage({"option": "value"})
        ```
    """

    SettingsFactory: ClassVar[type[Settings]] = Settings
    """Factory class for storage settings."""
    UploaderFactory: ClassVar[type[Uploader]] = Uploader
    """Factory class for uploader service."""
    ManagerFactory: ClassVar[type[Manager]] = Manager
    """Factory class for manager service."""
    ReaderFactory: ClassVar[type[Reader]] = Reader
    """Factory class for reader service."""

    capabilities: Capability = Capability.NONE
    """Operations supported by storage. Computed from capabilities of
    services during storage initialization."""
    hidden: bool = False
    """Flag that marks unsafe/experimental storages."""

    @override
    def __str__(self) -> str:
        return self.settings.name

    @utils.ensure_setup
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

        Returns:
            initialized settings object
        """
        if isinstance(settings, Settings):
            return settings

        return cls.SettingsFactory.from_dict(settings)

    def compute_capabilities(self) -> utils.Capability:
        """Computes the capabilities of the storage based on its services.

        Combines the capabilities of the uploader, manager, and reader services,
        then excludes any capabilities that are listed in the storage settings as disabled.

        Returns:
            The combined capabilities of the storage.
        """
        result = self.uploader.capabilities | self.manager.capabilities | self.reader.capabilities

        for name in self.settings.disabled_capabilities:
            cap = name if isinstance(name, Capability) else Capability[name]
            result = result.exclude(cap)

        return result

    def supports(self, operation: utils.Capability) -> bool:
        """Check whether the storage supports operation.

        Args:
            operation: capability to check

        Returns:
            True if operation is supported, False otherwise
        """
        return self.capabilities.can(operation)

    def supports_synthetic(self, operation: utils.Capability, dest: Storage) -> bool:
        """Check if the storage can emulate operation using other operations.

        This method checks if the storage can perform the specified operation
        using a combination of other supported operations, often in conjunction
        with a destination storage.

        Synthetic operations are not stable and may change in future. They are
        not considered when computing capabilities of the storage. There are
        two main reasons to use them:

        * required operation involves two storage. For example, moving or
          copying file from one storage to another.
        * operation is not natively supported by the storage, but can be
          emulated using other operations. For example,
          [RANGE][file_keeper.Capability.RANGE] capability means that storage
          can return specified slice of the file. When this capability is not
          natively supported, storage can use
          [STREAM][file_keeper.Capability.STREAM] capability to read the whole
          file, returning only specified fragment. This is not efficient but
          still can solve certain problems.

        Args:
            operation: capability to check
            dest: destination storage for operations that require it

        Returns:
            True if operation is supported, False otherwise

        """
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

        This method works as a shortcut for enabling `path` option. Whenever
        your custom storage works with location provided by user, wrap this
        location into this method to get full path:

        ```py
        class MyCustomReader:
            def stream(self, data: FileData, extras):
                real_location = self.storage.full_path(data_location)
                ...
        ```

        Args:
            location: location of the file object
            **kwargs: extra parameters for custom storages

        Returns:
            full path required to access location

        Raises:
            exceptions.LocationError: when location is outside of the storage's path
        """
        # Check for null bytes which could be used for injection
        if "\x00" in location:
            raise exceptions.LocationError(self, location)

        result = os.path.normpath(os.path.join(self.settings.path, location))
        if not result.startswith(self.settings.path):
            raise exceptions.LocationError(self, location)

        return result

    def prepare_location(self, location: str, sample: Upload | None = None, /, **kwargs: Any) -> types.Location:
        """Transform and sanitize location using configured functions.

        This method applies all transformations configured in
        [location_transformers][file_keeper.Settings.location_transformers]
        setting to the provided location. Each transformer is called in the
        order they are listed in the setting. The output of the previous
        transformer is passed as an input to the next one.

        Example:
            ```py
            location = storage.prepare_location(untrusted_location)
            ```

        Args:
            location: initial location provided by user
            sample: optional Upload object that can be used by transformers.
            **kwargs: additional parameters for transformers

        Returns:
            transformed location

        Raises:
            exceptions.LocationTransformerError: when transformer is not found

        """
        for name in self.settings.location_transformers:
            if transformer := location_transformers.get(name):
                location = transformer(location, sample, kwargs)

            else:
                raise exceptions.LocationTransformerError(name)

        return types.Location(location)

    def file_as_upload(self, data: data.FileData, **kwargs: Any) -> Upload:
        """Make an [Upload][file_keeper.Upload] with file content.

        Args:
            data: The FileData object to wrap into Upload
            **kwargs: Additional metadata for the upload.

        Returns:
            Upload object with file content
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

        Requires [CREATE][file_keeper.Capability.CREATE] capability.

        This is the simplest way to upload file into the storage. It uses
        single stream to transfer the whole file. If upload fails, no file is
        created in the storage.

        Content is not modified during upload, it is written as-is. And content
        can be of size 0, which results in empty file in the storage.

        When file already exists, behavior depends on
        [override_existing][file_keeper.Settings.override_existing] setting. If
        it is False, [ExistingFileError][file_keeper.exc.ExistingFileError] is
        raised. If it is True, existing file is replaced with new content. In
        this case, it is possible to lose existing file if upload fails. When
        adapter does not support removal, but supports overrides, this can be
        used to wipe the content of the file.

        Location can contain nested path as long as it does not go outside of
        the [path][file_keeper.Settings.path] from settings. For example, if
        `path` is set to `/data`, location can be `file.txt` or `2024/file.txt`
        but not `../file.txt` or `/etc/passwd`. Violating this rule leads to
        [LocationError][file_keeper.exc.LocationError].

        Args:
            location: The destination location for the upload.
            upload: The Upload object containing the file data.
            **kwargs: Additional metadata for the upload.

        Returns:
            FileData object with details about the uploaded file.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                CREATE operation
            exceptions.ExistingFileError: when file already exists and
                [override_existing][file_keeper.Settings.override_existing] is False
            exceptions.LocationError: when location is outside of the storage's path
        """
        return self.uploader.upload(location, upload, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_start(self, location: types.Location, size: int, /, **kwargs: Any) -> data.FileData:
        """Prepare everything for resumable upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [RESUMABLE][file_keeper.Capability.RESUMABLE] capability.

        `content_type` and `hash` are optional. When any of those provided, it
        will be used to verify the integrity of the upload. If they are
        missing, the upload will be accepted without verification.

        Args:
            location: The destination location for the upload.
            size: The total size of the upload in bytes.
            **kwargs: Additional metadata for the upload.

        Returns:
            details about the upload.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                RESUMABLE operation
        """
        return self.uploader.resumable_start(location, size, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_refresh(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Show details of the incomplete resumable upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [RESUMABLE][file_keeper.Capability.RESUMABLE] capability.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.

        Returns:
            details about the upload.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                RESUMABLE operation
        """
        return self.uploader.resumable_refresh(data, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_resume(self, data: data.FileData, upload: Upload, /, **kwargs: Any) -> data.FileData:
        """Resume the interrupted resumable upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [RESUMABLE][file_keeper.Capability.RESUMABLE] capability.

        Args:
            data: The FileData object containing the upload metadata.
            upload: The Upload object containing the content.
            **kwargs: Additional metadata for the upload.

        Returns:
            details about the upload.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                RESUMABLE operation
        """
        return self.uploader.resumable_resume(data, upload, kwargs)

    @requires_capability(Capability.RESUMABLE)
    def resumable_remove(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Remove incomplete resumable upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [RESUMABLE][file_keeper.Capability.RESUMABLE] capability.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.

        Returns:
            True if upload was removed, False otherwise.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                RESUMABLE operation
        """
        return self.uploader.resumable_remove(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_start(self, location: types.Location, size: int, /, **kwargs: Any) -> data.FileData:
        """Prepare everything for multipart upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [MULTIPART][file_keeper.Capability.MULTIPART] capability.

        `content_type` and `hash` are optional. When any of those provided, it
        will be used to verify the integrity of the upload. If they are
        missing, the upload will be accepted without verification.

        Args:
            location: The destination location for the upload.
            size: The total size of the upload in bytes.
            **kwargs: Additional metadata for the upload.

        Returns:
            details about the upload.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                MULTIPART operation

        """
        return self.uploader.multipart_start(location, size, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_refresh(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Show details of the incomplete upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [MULTIPART][file_keeper.Capability.MULTIPART] capability.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.

        Returns:
            details about the upload.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                MULTIPART operation

        """
        return self.uploader.multipart_refresh(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_update(self, data: data.FileData, upload: Upload, part: int, /, **kwargs: Any) -> data.FileData:
        """Add data to the incomplete upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [MULTIPART][file_keeper.Capability.MULTIPART] capability.

        Args:
            data: The FileData object containing the upload metadata.
            upload: The Upload object containing the content.
            part: Position of the given part among other parts, starting with 0.
            **kwargs: Additional metadata for the upload.

        Returns:
            details about the upload.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                MULTIPART operation

        """
        return self.uploader.multipart_update(data, upload, part, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_complete(self, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Verify file integrity and finalize incomplete upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [MULTIPART][file_keeper.Capability.MULTIPART] capability.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.

        Returns:
            details about the upload.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                MULTIPART operation

        """
        return self.uploader.multipart_complete(data, kwargs)

    @requires_capability(Capability.MULTIPART)
    def multipart_remove(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Interrupt and remove incomplete upload.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [MULTIPART][file_keeper.Capability.MULTIPART] capability.

        Args:
            data: The FileData object containing the upload metadata.
            **kwargs: Additional metadata for the upload.

        Returns:
            True if upload was removed, False otherwise.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                MULTIPART operation

        """
        return self.uploader.multipart_remove(data, kwargs)

    @requires_capability(Capability.EXISTS)
    def exists(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Check if file exists in the storage.

        Requires [EXISTS][file_keeper.Capability.EXISTS] capability.

        Args:
            data: The FileData object representing the file to check.
            **kwargs: Additional metadata for the operation.

        Returns:
            True if file exists, False otherwise.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                EXISTS operation
        """
        return self.manager.exists(data, kwargs)

    @requires_capability(Capability.REMOVE)
    def remove(self, data: data.FileData, /, **kwargs: Any) -> bool:
        """Remove file from the storage.

        Requires [REMOVE][file_keeper.Capability.REMOVE] capability.

        Args:
            data: The FileData object representing the file to remove.
            **kwargs: Additional metadata for the operation.

        Returns:
            True if file was removed, False otherwise.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                REMOVE operation
        """
        return self.manager.remove(data, kwargs)

    @requires_capability(Capability.SCAN)
    def scan(self, **kwargs: Any) -> Iterable[str]:
        """List all locations(filenames) in storage.

        Requires [SCAN][file_keeper.Capability.SCAN] capability.

        This operation lists all locations (filenames) in the storage if they
        start with the configured [path][file_keeper.Settings.path]. If path is
        empty, all locations are listed. Locations that match path
        partially(e.g. location `nested_dir` overlaps with path `nested`) are
        not listed.

        Args:
            **kwargs: Additional metadata for the operation.

        Returns:
            An iterable of location strings.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                SCAN operation
        """
        return self.manager.scan(kwargs)

    @requires_capability(Capability.SCAN)
    def filtered_scan(self, /, prefix: str = "", glob: str = "", **kwargs: Any) -> Iterable[str]:
        """List all locations(filenames) in storage that match prefix and glob.

        Requires [SCAN][file_keeper.Capability.SCAN] capability.

        This operation lists all locations (filenames) in the storage if they
        start with the specified prefix and match the provided glob pattern. If
        no prefix is provided, it defaults to an empty string, meaning all
        locations are considered. If no glob pattern is provided, it defaults to
        an empty string, which matches all filenames.

        Glob parameter supports standard Unix shell-style wildcards:

        * `*` matches everything
        * `?` matches any single character
        * `[seq]` matches any character in seq
        * `[!seq]` matches any character not in seq

        Adapters may choose to support different set of wildcards. Check
        adapter specific documentation for details.

        Args:
            prefix: The prefix to filter locations.
            glob: The glob pattern to filter locations.
            **kwargs: Additional metadata for the operation.

        Returns:
            An iterable of location strings.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                SCAN operation
        """
        return self.manager.filtered_scan(prefix, glob, kwargs)

    @requires_capability(Capability.ANALYZE)
    def analyze(self, location: types.Location, /, **kwargs: Any) -> data.FileData:
        """Return file details.

        Requires [ANALYZE][file_keeper.Capability.ANALYZE] capability.

        [FileData][file_keeper.FileData] produced by this operation is the same
        as data produced by the [upload()][file_keeper.Storage.upload].

        Attempt to analyze non-existing location leads to
        [MissingFileError][file_keeper.exc.MissingFileError]

        Args:
            location: The location of the file to analyze.
            **kwargs: Additional metadata for the operation.

        Returns:
            details about the file.

        Raises:
            exceptions.MissingFileError: when location does not exist
            exceptions.UnsupportedOperationError: when storage does not support
                ANALYZE operation
        """
        return self.manager.analyze(location, kwargs)

    @requires_capability(Capability.ANALYZE)
    def size(self, location: types.Location, /, **kwargs: Any) -> int:
        """Return the size of the file.

        Requires [ANALYZE][file_keeper.Capability.ANALYZE] capability.

        Args:
            location: The location of the file to analyze.
            **kwargs: Additional metadata for the operation.

        Returns:
            size of the file

        Raises:
            exceptions.MissingFileError: when location does not exist
            exceptions.UnsupportedOperationError: when storage does not support
                ANALYZE operation
        """
        return self.manager.size(location, kwargs)

    @requires_capability(Capability.ANALYZE)
    def hash(self, location: types.Location, /, **kwargs: Any) -> str:
        """Return the hash of the file.

        Requires [ANALYZE][file_keeper.Capability.ANALYZE] capability.

        Args:
            location: The location of the file to analyze.
            **kwargs: Additional metadata for the operation.

        Returns:
            hash of the file

        Raises:
            exceptions.MissingFileError: when location does not exist
            exceptions.UnsupportedOperationError: when storage does not support
                ANALYZE operation
        """
        return self.manager.hash(location, kwargs)

    @requires_capability(Capability.ANALYZE)
    def content_type(self, location: types.Location, /, **kwargs: Any) -> str:
        """Return the MIME type of the file.

        Requires [ANALYZE][file_keeper.Capability.ANALYZE] capability.

        Args:
            location: The location of the file to analyze.
            **kwargs: Additional metadata for the operation.

        Returns:
            MIME type of the file

        Raises:
            exceptions.MissingFileError: when location does not exist
            exceptions.UnsupportedOperationError: when storage does not support
                ANALYZE operation
        """
        return self.manager.content_type(location, kwargs)

    @requires_capability(Capability.SIGNED)
    def signed(
        self,
        action: types.SignedAction,
        duration: int,
        location: types.Location,
        **kwargs: Any,
    ) -> str:
        """Make an URL for signed action.

        /// warning
        This operation is not stabilized yet.
        ///

        Requires [SIGNED][file_keeper.Capability.SIGNED] capability.

        This operation creates a signed URL that allows performing the
        specified action (e.g., "upload", "download") on the given location for
        a limited duration. The signed URL is typically used to grant temporary
        access to a file without requiring authentication. The URL includes a
        signature that verifies its authenticity and validity.

        Depending on the action, user is expected to use the URL in
        different ways:

        * upload - use HTTP PUT request to send the file content to the URL.
        * download - use HTTP GET request to retrieve the file content from
            the URL.
        * delete - use HTTP DELETE request to remove the file at the URL.

        Check adapter specific implementation for details. Some actions may not
        be supported or require additional information. For example, upload
        with Azure Blob Storage requires header `x-ms-blob-type: BlockBlob`.

        Args:
            action: The action to sign (upload, download, delete).
            duration: The duration for which the signed URL is valid.
            location: The location of the file to sign.
            **kwargs: Additional metadata for the operation.

        Returns:
            A signed URL as a string.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                SIGNED operation
        """
        return self.manager.signed(action, duration, location, kwargs)

    @requires_capability(Capability.STREAM)
    def stream(self, data: data.FileData, /, **kwargs: Any) -> Iterable[bytes]:
        """Return byte-stream of the file content.

        Requires [STREAM][file_keeper.Capability.STREAM] capability.

        Returns iterable that yields chunks of bytes from the file. The size of
        each chunk depends on the storage implementation. The iterable can be
        used in a for loop or converted to a list to get all chunks at once.

        Args:
            data: The FileData object representing the file to stream.
            **kwargs: Additional metadata for the operation.

        Returns:
            An iterable yielding chunks of bytes from the file.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                STREAM operation
            exceptions.MissingFileError: when file does not exist

        """
        return self.reader.stream(data, kwargs)

    @requires_capability(Capability.RANGE)
    def range(self, data: data.FileData, start: int = 0, end: int | None = None, /, **kwargs: Any) -> Iterable[bytes]:
        """Return slice of the file content.

        Requires [RANGE][file_keeper.Capability.RANGE] capability.

        This operation slices the file content from the specified start byte
        offset to the end byte offset (exclusive). If `end` is None, the slice
        extends to the end of the file. The operation returns an iterable that
        yields chunks of bytes from the specified range. The size of each chunk
        depends on the storage implementation. The iterable can be used in a for
        loop or converted to a list to get all chunks at once.

        Unlike python slices, this operation does not expect negative indexes,
        but certain adapters may support it.

        Attempt to get a range from non-existing file leads to
        [MissingFileError][file_keeper.exc.MissingFileError].

        Args:
            data: The FileData object representing the file to read.
            start: The starting byte offset.
            end: The ending byte offset (inclusive).
            **kwargs: Additional metadata for the operation.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                RANGE operation
            exceptions.MissingFileError: when file does not exist

        """
        return self.reader.range(data, start, end, kwargs)

    def range_synthetic(
        self, data: data.FileData, start: int = 0, end: int | None = None, /, **kwargs: Any
    ) -> Iterable[bytes]:
        """Generic implementation of range operation that relies on [STREAM][file_keeper.Capability.STREAM].

        This method provides a generic implementation of the range operation
        using the STREAM capability. It reads the file in chunks and yields only
        the specified range of bytes.

        Args:
            data: The FileData object representing the file to read.
            start: The starting byte offset.
            end: The ending byte offset (inclusive).
            **kwargs: Additional metadata for the operation.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                STREAM operation
            exceptions.MissingFileError: when file does not exist
        """
        if end is None:
            end = data.size + 1

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

            yield chunk[:end]
            end -= len(chunk)
            if end <= 0:
                break

    @requires_capability(Capability.STREAM)
    def content(self, data: data.FileData, /, **kwargs: Any) -> bytes:
        """Return file content as a single byte object.

        Requires [STREAM][file_keeper.Capability.STREAM] capability.

        Returns complete file content as a single bytes object. This method
        internally uses [stream()][file_keeper.Storage.stream] method to read
        the file content in chunks and then combines those chunks into a single
        bytes object.

        Args:
            data: The FileData object representing the file to read.
            **kwargs: Additional metadata for the operation.

        Returns:
            The complete file content as a single bytes object.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                STREAM operation
            exceptions.MissingFileError: when file does not exist
        """
        return self.reader.content(data, kwargs)

    @requires_capability(Capability.APPEND)
    def append(self, data: data.FileData, upload: Upload, /, **kwargs: Any) -> data.FileData:
        """Append content to existing file.

        Requires [APPEND][file_keeper.Capability.APPEND] capability.

        Args:
            data: The FileData object representing the file to append to.
            upload: The Upload object containing the content to append.
            **kwargs: Additional metadata for the operation.

        Returns:
            Updated FileData object with details about the file after appending.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                APPEND operation
            exceptions.MissingFileError: when file does not exist

        """
        return self.manager.append(data, upload, kwargs)

    @requires_capability(Capability.COPY)
    def copy(self, location: types.Location, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Copy file inside the storage.

        Requires [COPY][file_keeper.Capability.COPY] capability.

        This operation creates a duplicate of the specified file at a new
        location within the same storage. The copied file retains the same
        content and metadata as the original file.

        If file already exists at the destination location, behavior depends on
        [override_existing][file_keeper.Settings.override_existing] setting. If
        it is False, [ExistingFileError][file_keeper.exc.ExistingFileError] is
        raised. If it is True, existing file is replaced with the copied file. In
        this case, it is possible to lose existing file if copy fails.

        Args:
            location: The destination location for the copied file.
            data: The FileData object representing the file to copy.
            **kwargs: Additional metadata for the operation.

        Returns:
            FileData object with details about the copied file.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                COPY operation
            exceptions.MissingFileError: when source file does not exist
            exceptions.ExistingFileError: when destination file already exists and
                [override_existing][file_keeper.Settings.override_existing] is False
        """
        if location == data.location and self.settings.skip_in_place_copy:
            return data

        return self.manager.copy(location, data, kwargs)

    def copy_synthetic(
        self, location: types.Location, data: data.FileData, dest_storage: Storage, /, **kwargs: Any
    ) -> data.FileData:
        """Generic implementation of the copy operation that relies on [CREATE][file_keeper.Capability.CREATE].

        This method provides a generic implementation of the copy operation
        using the CREATE capability of the destination storage and the STREAM
        capability of the source storage. It reads the file content from the
        source storage and uploads it to the destination storage.

        Args:
            location: The destination location for the copied file.
            data: The FileData object representing the file to copy.
            dest_storage: The destination storage
            **kwargs: Additional metadata for the operation.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                CREATE operation
            exceptions.MissingFileError: when source file does not exist
            exceptions.ExistingFileError: when destination file already exists and
                [override_existing][file_keeper.Settings.override_existing] is False

        """
        return dest_storage.upload(
            location,
            self.file_as_upload(data, **kwargs),
            **kwargs,
        )

    @requires_capability(Capability.MOVE)
    def move(self, location: types.Location, data: data.FileData, /, **kwargs: Any) -> data.FileData:
        """Move file to a different location inside the storage.

        Requires [MOVE][file_keeper.Capability.MOVE] capability.

        This operation relocates the specified file to a new location within
        the same storage. After the move operation, the file will no longer
        exist at its original location.

        Args:
            location: The destination location for the moved file.
            data: The FileData object representing the file to move.
            **kwargs: Additional metadata for the operation.

        Returns:
            FileData object with details about the moved file.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                MOVE operation
            exceptions.MissingFileError: when source file does not exist
            exceptions.ExistingFileError: when destination file already exists and
                [override_existing][file_keeper.Settings.override_existing] is False

        """
        if location == data.location and self.settings.skip_in_place_move:
            return data
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

        Returns:
            FileData object with details about the moved file.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                CREATE or REMOVE operation
            exceptions.MissingFileError: when source file does not exist
            exceptions.ExistingFileError: when destination file already exists and
                [override_existing][file_keeper.Settings.override_existing] is False

        """
        result = dest_storage.upload(location, self.file_as_upload(data, **kwargs), **kwargs)
        self.remove(data)
        return result

    @requires_capability(Capability.COMPOSE)
    def compose(self, location: types.Location, /, *files: data.FileData, **kwargs: Any) -> data.FileData:
        """Combine multiple files into a new file.

        Requires [COMPOSE][file_keeper.Capability.COMPOSE] capability.

        This operation combines multiple source files into a single destination
        file. The content of the source files is concatenated in the order they
        are provided to form the content of the new file.

        Args:
            location: The destination location for the composed file.
            *files: FileData objects representing the files to combine.
            **kwargs: Additional metadata for the operation.

        Returns:
            FileData object with details about the composed file.

        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                COMPOSE operation
            exceptions.MissingFileError: when any of source files do not exist
            exceptions.ExistingFileError: when destination file already exists and
                [override_existing][file_keeper.Settings.override_existing] is False
        """
        return self.manager.compose(location, files, kwargs)

    def compose_synthetic(
        self, location: types.Location, dest_storage: Storage, /, *files: data.FileData, **kwargs: Any
    ) -> data.FileData:
        """Generic composition that relies on [APPEND][file_keeper.Capability.APPEND].

        This method provides a generic implementation of the compose operation
        using the APPEND capability of the destination storage. It creates an
        empty file at the destination location and then appends the content of
        each source file to it in sequence.

        Args:
            location: The destination location for the composed file.
            dest_storage: The destination storage
            *files: FileData objects representing the files to combine.
            **kwargs: Additional metadata for the operation.


        Raises:
            exceptions.UnsupportedOperationError: when storage does not support
                APPEND operation
            exceptions.MissingFileError: when any of source files do not exist
            exceptions.ExistingFileError: when destination file already exists and
                [override_existing][file_keeper.Settings.override_existing] is False

        """
        result = dest_storage.upload(location, make_upload(b""), **kwargs)

        # when first append succeeded with the fragment of the file added
        # in the storage, and the following append failed, this incomplete
        # fragment must be removed.
        #
        # Expected reasons of failure are:
        #
        # * one of the source files is missing
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

        Requires [LINK_ONE_TIME][file_keeper.Capability.LINK_ONE_TIME] capability.

        Args:
            data: The FileData object representing the file.
            **kwargs: Additional metadata for the operation.

        Returns:
            A one-time download link as a string, or None if not supported.
        """
        if self.supports(Capability.LINK_ONE_TIME):
            return self.reader.one_time_link(data, kwargs)

    def temporal_link(self, data: data.FileData, duration: int, /, **kwargs: Any) -> str | None:
        """Return temporal download link.

        Requires [LINK_TEMPORAL][file_keeper.Capability.LINK_TEMPORAL] capability.

        Args:
            data: The FileData object representing the file.
            duration: The duration for which the link is valid.
            **kwargs: Additional metadata for the operation.

        Returns:
            A temporal download link as a string, or None if not supported.
        """
        if self.supports(Capability.LINK_TEMPORAL):
            return self.reader.temporal_link(data, duration, kwargs)

    def permanent_link(self, data: data.FileData, /, **kwargs: Any) -> str | None:
        """Return permanent download link.

        Requires [LINK_PERMANENT][file_keeper.Capability.LINK_PERMANENT] capability.

        Args:
            data: The FileData object representing the file.
            **kwargs: Additional metadata for the operation.

        Returns:
            A permanent download link as a string, or None if not supported.
        """
        if self.supports(Capability.LINK_PERMANENT):
            return self.reader.permanent_link(data, kwargs)


@utils.ensure_setup
def make_storage(name: str, settings: dict[str, Any]) -> Storage:
    """Initialize storage instance with specified settings.

    Storage adapter is defined by `type` key of the settings. The rest of
    settings depends on the specific adapter.

    Example:
        ```py
        storage = make_storage("memo", {"type": "file_keeper:memory"})
        ```

    Args:
        name: name of the storage
        settings: configuration for the storage

    Returns:
        storage instance

    Raises:
        exceptions.UnknownAdapterError: storage adapter is not registered


    """
    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)
    if not adapter:
        raise exceptions.UnknownAdapterError(adapter_type)

    settings.setdefault("name", name)

    return adapter(settings)


def get_storage(name: str, settings: dict[str, Any] | None = None) -> Storage:
    """Get storage from the pool.

    If storage accessed for the first time, it's initialized and added to the
    pool. After that the same storage is returned every time the function is
    called with the given name.

    Settings are required only for initialization, so you can omit them if you
    are sure that storage exists. Additionally, if `settings` are not specified
    but storage is missing from the pool, file-keeper makes an attempt to
    initialize storage using global configuration. Global configuration can be
    provided as:

    * `FILE_KEEPER_CONFIG` environment variable that points to a file with configuration
    * `.file-keeper.json` in the current directory hierarchy
    * `file-keeper/file-keeper.json` in the user's config directory(usually,
      `~/.config/`) when [platformdirs](https://pypi.org/project/platformdirs/)
      installed in the environment, for example via `pip install
      'file-keeper[user_config]'` extras.

    File must contain storage configuration provided in format

    ```json5
    {
        "storages": {
            "my_storage": {  # (1)!
                "type": "file_keeper:memory"  # (2)!
            }
        }
    }
    ```

    1. Name of the storage
    2. Options for the storage

    JSON configuration is used by default, because python has built-in JSON
    support. Additional file extensions are checked if environment contains
    corresponding package:

    | Package | Extension |
    |---|---|
    | [tomllib](https://docs.python.org/3/library/tomllib.html) | `.toml` |
    | [tomli](https://pypi.org/project/tomli/) | `.toml` |
    | [pyyaml](https://pypi.org/project/PyYAML/) | `.yaml`, `.yml` |

    Extensions are checked in order `.toml`, `.yaml`, `.yml`, `.json`.

    Example:
        If storage accessed for the first time, settings are required

        ```pycon
        >>> storage = get_storage("memory", {"type": "file_keeper:memory"})
        >>> storage
        <file_keeper.default.adapters.memory.MemoryStorage object at 0x...>

        ```

        and the same storage is returned every time in subsequent calls

        ```pycon
        >>> cached = get_storage("memory")
        >>> storage is cached
        True

        ```

        but if storage does not exist and settings are omitted, exception is raised

        ```pycon
        >>> get_storage("new-memory")
        Traceback (most recent call last):
            ...
        file_keeper.core.exceptions.UnknownStorageError: Storage new-memory is not configured

        ```

    Args:
        name: name of the storage
        settings: configuration for the storage

    Returns:
        storage instance

    Raises:
        exceptions.UnknownStorageError: storage with the given name is not configured
    """
    if name not in storages:
        if settings is None:
            config_file = os.getenv("FILE_KEEPER_CONFIG")

            if not config_file and (config_dir := user_config_dir("file-keeper")):
                config_file = _get_config_file_name(config_dir)

            if not config_file:
                path = pathlib.Path().absolute()

                while len(path.parts) > 1:
                    if config_file := _get_config_file_name(str(path), hidden=True):
                        break

                    path = path.parent

            if config_file:
                log.debug("Load configuration from %s", config_file)
                cfg = _load_config_file(config_file)
                settings = cfg.get("storages", {}).get(name)

            if not settings:
                raise exceptions.UnknownStorageError(name)

        storages.register(name, make_storage(name, settings))

    return storages[name]


def _get_config_file_name(path: str, /, hidden: bool = False):
    basename = ".file-keeper" if hidden else "file-keeper"
    plain_name = os.path.join(path, basename)

    if toml and os.path.exists(f"{plain_name}.toml"):
        return f"{plain_name}.toml"

    if yaml:
        if os.path.exists(f"{plain_name}.yaml"):
            return f"{plain_name}.yaml"

        if os.path.exists(f"{plain_name}.yml"):
            return f"{plain_name}.yml"

    if os.path.exists(f"{plain_name}.json"):
        return f"{plain_name}.json"


def _load_config_file(filename: str) -> dict[str, Any]:
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".toml":
        with open(filename, "rb") as src:
            return toml.load(src)  # pyright: ignore[reportUnknownVariableType, reportOptionalMemberAccess]

    if ext in [".yaml", ".yml"]:
        with open(filename, "rb") as src:
            return yaml.full_load(src)  # pyright: ignore[reportOptionalMemberAccess]

    if ext == ".json":
        with open(filename, "rb") as src:
            return json.load(src)

    raise TypeError(filename)
