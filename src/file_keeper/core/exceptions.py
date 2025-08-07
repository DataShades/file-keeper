"""Exception definitions for the extension.

Hierarchy:

* Exception
    * [FilesError][file_keeper.exc.FilesError]
        * [StorageError][file_keeper.exc.StorageError]
            * [UnknownAdapterError][file_keeper.exc.UnknownAdapterError]
            * [UnknownStorageError][file_keeper.exc.UnknownStorageError]
            * [UnsupportedOperationError][file_keeper.exc.UnsupportedOperationError]
            * [PermissionError][file_keeper.exc.PermissionError]
            * [LocationError][file_keeper.exc.LocationError]
                * [MissingFileError][file_keeper.exc.MissingFileError]
                * [ExistingFileError][file_keeper.exc.ExistingFileError]
            * [ExtrasError][file_keeper.exc.ExtrasError]
                * [MissingExtrasError][file_keeper.exc.MissingExtrasError]
            * [InvalidStorageConfigurationError][file_keeper.exc.InvalidStorageConfigurationError]
                * [MissingStorageConfigurationError][file_keeper.exc.MissingStorageConfigurationError]
            * [UploadError][file_keeper.exc.UploadError]
                * [WrongUploadTypeError][file_keeper.exc.WrongUploadTypeError]
                * [LocationTransformerError][file_keeper.exc.LocationTransformerError]
                * [ContentError][file_keeper.exc.ContentError]
                * [LargeUploadError][file_keeper.exc.LargeUploadError]
                    * [UploadOutOfBoundError][file_keeper.exc.UploadOutOfBoundError]
                * [UploadMismatchError][file_keeper.exc.UploadMismatchError]
                    * [UploadTypeMismatchError][file_keeper.exc.UploadTypeMismatchError]
                    * [UploadHashMismatchError][file_keeper.exc.UploadHashMismatchError]
                    * [UploadSizeMismatchError][file_keeper.exc.UploadSizeMismatchError]

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Storage = Any


class FilesError(Exception):
    """Base error for catch-all scenario."""


class StorageError(FilesError):
    """Error related to storage."""


class UnknownStorageError(StorageError):
    """Storage with the given name is not configured."""

    def __init__(self, storage: str):
        super().__init__(f"Storage {storage} is not configured")


class UnknownAdapterError(StorageError):
    """Specified storage adapter is not registered."""

    def __init__(self, adapter: str):
        super().__init__(f"Storage adapter {adapter} is not registered")


class UnsupportedOperationError(StorageError):
    """Requested operation is not supported by storage."""

    def __init__(self, operation: str, storage: Storage):
        super().__init__(f"Operation {operation} is not supported by {storage} storage")


class InvalidStorageConfigurationError(StorageError):
    """Storage cannot be initialized with given configuration."""

    def __init__(self, adapter_or_storage: type | str, problem: str):
        if isinstance(adapter_or_storage, str):
            what = f"storage {adapter_or_storage}"
        else:
            what = f"storage adapter {adapter_or_storage.__name__}"

        super().__init__(f"Cannot initialize {what}: {problem}")


class PermissionError(StorageError):
    """Storage client does not have required permissions."""

    def __init__(self, storage: Storage, operation: str, problem: str):
        msg = f"Storage {storage} is not allowed to" + f" perform {operation} operation: {problem}"
        super().__init__(msg)


class MissingStorageConfigurationError(InvalidStorageConfigurationError):
    """Storage cannot be initialized due to missing option."""

    def __init__(self, adapter_or_storage: type | str, option: str):
        super().__init__(
            adapter_or_storage,
            f"{option} option is required",
        )


class LocationError(StorageError):
    """Storage cannot use given location."""

    tpl: str = "{storage} cannot use location {location}"

    def __init__(self, storage: Storage, location: str):
        super().__init__(self.tpl.format(storage=storage, location=location))


class MissingFileError(LocationError):
    """File does not exist."""

    tpl: str = "File {location} does not exist inside storage {storage}"


class ExistingFileError(LocationError):
    """File already exists."""

    tpl: str = "File {location} already exists inside storage {storage}"


class UploadError(StorageError):
    """Error related to file upload process."""


class LargeUploadError(UploadError):
    """Storage cannot be initialized due to missing option."""

    tpl: str = "Upload size {actual_size} surpasses max allowed size {max_size}"

    def __init__(self, actual_size: int, max_size: int):
        super().__init__(self.tpl.format(actual_size=actual_size, max_size=max_size))


class UploadOutOfBoundError(LargeUploadError):
    """Ongoing upload exceeds expected size."""

    tpl: str = "Upload size {actual_size} exceeds expected size {max_size}"


class UploadMismatchError(UploadError):
    """Expected value of file attribute doesn't match the actual value."""

    value_formatter: Callable[[Any], Any] = str

    def __init__(self, attribute: str, actual: Any, expected: Any):
        actual = self.value_formatter(actual)
        expected = self.value_formatter(expected)

        super().__init__(f"Actual value of {attribute}({actual})" + f" does not match expected value({expected})")


class UploadTypeMismatchError(UploadMismatchError):
    """Expected value of content type doesn't match the actual value."""

    def __init__(self, actual: Any, expected: Any):
        super().__init__("content type", actual, expected)


class UploadHashMismatchError(UploadMismatchError):
    """Expected value of hash match the actual value."""

    def __init__(self, actual: Any, expected: Any):
        super().__init__("content hash", actual, expected)


class UploadSizeMismatchError(UploadMismatchError):
    """Expected value of upload size doesn't match the actual value."""

    def __init__(self, actual: Any, expected: Any):
        super().__init__("upload size", actual, expected)


class WrongUploadTypeError(UploadError):
    """Storage does not support given MIMEType."""

    def __init__(self, content_type: str):
        super().__init__(f"Type {content_type} is not supported by storage")


class LocationTransformerError(UploadError):
    """Undefined location transformer."""

    def __init__(self, transformer: str):
        super().__init__(f"Unknown location transformer {transformer}")


class ExtrasError(StorageError):
    """Wrong extras passed during upload."""

    def __init__(self, extras: Any):
        super().__init__(f"Wrong extras: {extras}")


class MissingExtrasError(ExtrasError):
    """Wrong extras passed to storage method."""

    def __init__(self, key: Any):
        super().__init__(f"Key {key} is missing from extras")


class ContentError(UploadError):
    """Storage cannot accept uploaded content."""

    def __init__(self, storage: Storage, msg: str):
        super().__init__(f"{storage} rejected upload: {msg}")
