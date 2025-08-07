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
from typing import Any, ClassVar, Generic, cast

from typing_extensions import TypeVar

from . import types

TData = TypeVar("TData", bound=types.PData, default=Any)


@dataclasses.dataclass(frozen=True)
class BaseData(Generic[TData]):
    location: types.Location
    size: int = 0
    content_type: str = ""
    hash: str = ""
    storage_data: dict[str, Any] = cast("dict[str, Any]", dataclasses.field(default_factory=dict))

    _plain_keys: ClassVar[list[str]] = ["location", "size", "content_type", "hash"]
    _complex_keys: ClassVar[list[str]] = ["storage_data"]

    @classmethod
    def from_dict(cls, record: dict[str, Any], **overrides: Any):
        return cls._from(record, operator.getitem, operator.contains, overrides)

    @classmethod
    def from_object(cls, obj: TData, **overrides: Any):
        return cls._from(obj, getattr, hasattr, overrides)

    @classmethod
    def _from(
        cls,
        source: Any,
        getter: Callable[[Any, str], Any],
        checker: Callable[[Any, str], bool],
        overrides: dict[str, Any],
    ):
        return cls(
            *[
                overrides[key] if key in overrides else getter(source, key)
                for key in cls._plain_keys
                if checker(source, key)
            ],
            *[
                overrides[key] if key in overrides else copy.deepcopy(getter(source, key))
                for key in cls._complex_keys
                if checker(source, key)
            ],
        )

    def into_object(self, obj: TData):
        for key in self._plain_keys:
            setattr(obj, key, getattr(self, key))

        for key in self._complex_keys:
            setattr(obj, key, copy.deepcopy(getattr(self, key)))

        return obj


@dataclasses.dataclass(frozen=True)
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
