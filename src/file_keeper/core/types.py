"""Type definitions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Literal, NewType, Protocol, TypeAlias

if TYPE_CHECKING:
    from .upload import Upload

Location = NewType("Location", str)

LocationTransformer: TypeAlias = Callable[[str, "Upload | None", "dict[str, Any]"], str]

SignedAction = Literal["upload", "download", "delete"]


class PReadable(Protocol):
    """Readable object."""

    def read(self, size: Any = ..., /) -> bytes:
        """Read up to `size` bytes. If the argument is negative or omitted, read until EOF.

        Return an empty bytes object on EOF.
        """
        ...


class PStream(PReadable, Protocol):
    """Readable stream."""

    def __iter__(self) -> Iterator[bytes]:
        """Return an iterator over the stream."""
        ...


class PSeekableStream(PStream, Protocol):
    """Stream that supports `seek` operation."""

    def tell(self) -> int:
        """Get the current position of the pointer."""
        ...

    def seek(self, offset: int, whence: int = 0) -> int:
        """Move pointer to the specified position."""
        ...


__all__ = [
    "PStream",
    "PSeekableStream",
]
