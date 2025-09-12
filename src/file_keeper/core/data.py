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
import operator
from collections.abc import Callable
from typing import Any, ClassVar, cast

from typing_extensions import TypeVar

from . import types

T = TypeVar("T")


@dataclasses.dataclass(frozen=True)
class BaseData:
    """Base class for file details."""

    location: types.Location
    size: int = 0
    content_type: str = ""
    hash: str = ""
    storage_data: dict[str, Any] = cast("dict[str, Any]", dataclasses.field(default_factory=dict))

    _plain_keys: ClassVar[list[str]] = ["location", "size", "content_type", "hash"]
    _complex_keys: ClassVar[list[str]] = ["storage_data"]

    @classmethod
    def from_string(cls, location: str | types.Location):
        """Create data object from location string."""
        return cls(types.Location(location))

    @classmethod
    def from_dict(cls, record: dict[str, Any], **overrides: Any):
        """Transform dictionary into data object."""
        return cls._from(record, operator.getitem, operator.contains, overrides)

    @classmethod
    def from_object(cls, obj: Any, **overrides: Any):
        """Copy data details from another object."""
        return cls._from(obj, getattr, hasattr, overrides)

    @classmethod
    def _from(
        cls,
        source: Any,
        getter: Callable[[Any, str], Any],
        checker: Callable[[Any, str], bool],
        overrides: dict[str, Any],
    ):
        data = {}
        for key in cls._plain_keys:
            if key in overrides:
                data[key] = overrides[key]
            elif checker(source, key):
                data[key] = getter(source, key)

        for key in cls._complex_keys:
            if key in overrides:
                data[key] = overrides[key]
            elif checker(source, key):
                data[key] = copy.deepcopy(getter(source, key))

        return cls(**data)

    def into_object(self, obj: T) -> T:
        """Copy data attributes into another object."""
        for key in self._plain_keys:
            setattr(obj, key, getattr(self, key))

        for key in self._complex_keys:
            setattr(obj, key, copy.deepcopy(getattr(self, key)))

        return obj

    def as_dict(self):
        """Return data as dictionary."""
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class FileData(BaseData):
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
