from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Iterator, NewType, Protocol

from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from .data import BaseData
    from .upload import Upload

Location = NewType("Location", str)

LocationTransformer: TypeAlias = Callable[
    [str, "Upload | BaseData | None", "dict[str, Any]"], str
]


class PReadable(Protocol):
    def read(self, size: Any = ..., /) -> bytes: ...


class PStream(PReadable, Protocol):
    def __iter__(self) -> Iterator[bytes]: ...


class PSeekableStream(PStream, Protocol):
    def tell(self) -> int: ...

    def seek(self, offset: int, whence: int = 0) -> int: ...


class PData(Protocol):
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
