"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any, Generic

from typing_extensions import TypeVar

from . import types

TData = TypeVar("TData", bound=types.PData, default=Any)


@dataclasses.dataclass
class BaseData(Generic[TData]):
    location: types.Location
    size: int = 0
    content_type: str = ""
    hash: str = ""
    storage_data: dict[str, Any] = dataclasses.field(default_factory=dict)

    _plain_keys = ["location", "size", "content_type", "hash"]
    _complex_keys = ["storage_data"]

    @classmethod
    def from_dict(cls, record: dict[str, Any]):
        return cls(
            *[record[key] for key in cls._plain_keys if key in record],
            *[copy.deepcopy(record[key]) for key in cls._complex_keys if key in record],
        )

    @classmethod
    def from_object(cls, obj: TData):
        return cls(
            *[getattr(obj, key) for key in cls._plain_keys],
            *[copy.deepcopy(getattr(obj, key)) for key in cls._complex_keys],
        )

    def into_object(self, obj: TData):
        for key in self._plain_keys:
            setattr(obj, key, getattr(self, key))

        for key in self._complex_keys:
            setattr(obj, key, copy.deepcopy(getattr(self, key)))

        return obj


@dataclasses.dataclass
class FileData(BaseData[TData]):
    """Information required by storage to operate the file.

    Args:
        location: filepath, filename or any other type of unique identifier
        size: size of the file in bytes
        content_type: MIMEtype of the file
        hash: checksum of the file
        storage_data: additional details set by storage adapter

    Example:
        ```
        FileData(
            "local/path.txt",
            123,
            "text/plain",
            md5_of_content,
        )
        ```
    """

    content_type: str = "application/octet-stream"


@dataclasses.dataclass
class MultipartData(BaseData[TData]):
    """Information required by storage to operate the incomplete upload.

    Args:
        location: filepath, filename or any other type of unique identifier
        size: expected size of the file in bytes
        content_type: expected MIMEtype of the file
        hash: expected checksum of the file
        storage_data: additional details set by storage adapter

    Example:
        ```
        MultipartData(
            "local/path.txt",
            expected_size,
            expected_content_type,
            expected_hash,
        )
        ```
    """

    location: types.Location = types.Location("")
