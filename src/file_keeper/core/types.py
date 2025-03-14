from __future__ import annotations

from typing import Any, Iterator, Protocol


class PReadable(Protocol):
    def read(self, size: Any = ..., /) -> bytes: ...

class PStream(PReadable, Protocol):
    def __iter__(self) -> Iterator[bytes]: ...


class PSeekableStream(PStream):
    def tell(self) -> int: ...

    def seek(self, offset: int, whence: int = 0) -> int: ...


class PData(Protocol):
    location: str
    size: int
    content_type: str
    hash: str
    storage_data: dict[str, Any]


__all__ = [
    "PData",
    "PStream",
    "PSeekableStream",
]
