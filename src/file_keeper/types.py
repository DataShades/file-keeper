from __future__ import annotations

from collections.abc import Callable, Hashable, Iterator
from io import BufferedReader, BytesIO
from typing import TYPE_CHECKING, Any, Protocol

from typing_extensions import TypeAlias, TypeVar

if TYPE_CHECKING:
    from .upload import Upload


K = TypeVar("K", default=str, bound=Hashable)
V = TypeVar("V")
T = TypeVar("T")

UploadFactory: TypeAlias = (
    "Callable[[Any], Upload | BytesIO | BufferedReader | bytes | bytearray | None]"
)


class PStream(Protocol):
    def read(self, size: Any = ..., /) -> bytes: ...

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
    "PStream",
    "PSeekableStream",
    "UploadFactory",
    "K",
    "V",
    "T",
]
