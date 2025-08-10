"""Type definitions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Literal, NewType, Protocol, TypeAlias

if TYPE_CHECKING:
    from .data import BaseData
    from .upload import Upload

Location = NewType("Location", str)

LocationTransformer: TypeAlias = Callable[[str, "Upload | BaseData | None", "dict[str, Any]"], str]

SignedAction = Literal["upload", "download", "delete"]


class PReadable(Protocol):
    """Readable object."""

    def read(self, size: Any = ..., /) -> bytes: ...


class PStream(PReadable, Protocol):
    """Readable stream."""

    def __iter__(self) -> Iterator[bytes]: ...


class PSeekableStream(PStream, Protocol):
    """Stream that supports `seek` operation."""

    def tell(self) -> int:
        """Get the current position of the pointer."""
        ...

    def seek(self, offset: int, whence: int = 0) -> int:
        """Move pointer to the specified position."""
        ...


class PData(Protocol):
    """Structure of the *Data object."""

    location: Location
    size: int
    content_type: str
    hash: str
    storage_data: dict[str, Any]


__all__ = [
    "PData",
    "PStream",
    "PSeekableStream",
]
