"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal module except for config, types and exceptions. Only independent tools
are stored here, to avoid import cycles.

"""

from __future__ import annotations

import abc
import enum
import functools
import hashlib
import io
import itertools
import logging
import re
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Generic

from typing_extensions import ParamSpec, TypeVar, override

from . import types

T = TypeVar("T")
P = ParamSpec("P")

log = logging.getLogger(__name__)

RE_FILESIZE = re.compile(r"^(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>\w*)$")
CHUNK_SIZE = io.DEFAULT_BUFFER_SIZE
SAMPLE_SIZE = 1024 * 2
BINARY_BASE = 1024
SI_BASE = 1000

UNITS = {
    "": 1,
    "b": 1,
    "k": 10**3,
    "kb": 10**3,
    "m": 10**6,
    "mb": 10**6,
    "g": 10**9,
    "gb": 10**9,
    "t": 10**12,
    "p": 10**15,
    "tb": 10**12,
    "kib": 2**10,
    "mib": 2**20,
    "gib": 2**30,
    "tib": 2**40,
    "pib": 2**50,
}


class run_once(Generic[P, T]):  # noqa: N801
    """Decorator that runs function only once and caches the result."""

    EMPTY = object()

    result: T
    func: Callable[P, T]

    def __init__(self, func: Callable[P, T]):
        self.func = func
        self.result = self.EMPTY  # pyright: ignore[reportAttributeAccessIssue]

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Run function and cache the result."""
        if self.result is self.EMPTY:
            self.result = self.func(*args, **kwargs)
        return self.result

    def reset(self) -> None:
        """Reset cached result to run function again on next call."""
        self.result = self.EMPTY  # pyright: ignore[reportAttributeAccessIssue]


def ensure_setup(func: Callable[P, T]) -> Callable[P, T]:
    """Initialize file-keeper if required."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        from file_keeper.ext import setup  # noqa: PLC0415

        setup()

        return func(*args, **kwargs)

    return wrapper


class HashingReader:
    """IO stream wrapper that computes content hash while stream is consumed.

    Args:
        stream: iterable of bytes or file-like object
        chunk_size: max number of bytes read at once
        algorithm: hashing algorithm

    Example:
        ```
        reader = HashingReader(readable_stream)
        for chunk in reader:
            ...
        print(f"Hash: {reader.get_hash()}")
        ```
    """

    stream: types.PStream
    chunk_size: int
    algorithm: str
    hashsum: Any
    position: int

    def __init__(
        self,
        stream: types.PStream,
        chunk_size: int = CHUNK_SIZE,
        algorithm: str = "md5",
    ):
        self.hashsum = hashlib.new(algorithm)
        self.stream = stream
        self.chunk_size = chunk_size
        self.algorithm = algorithm
        self.position = 0

    def __iter__(self) -> Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        chunk = self.stream.read(self.chunk_size)
        if not chunk:
            raise StopIteration

        self.position += len(chunk)
        self.hashsum.update(chunk)
        return chunk

    next: Callable[..., bytes] = __next__

    def read(self) -> bytes:
        """Read and return all bytes from stream at once."""
        return b"".join(self)

    def get_hash(self) -> str:
        """Get current content hash as a string."""
        return self.hashsum.hexdigest()

    def exhaust(self) -> None:
        """Exhaust internal stream to compute final version of content hash.

        Note, this method does not returns data from the stream. The content
        will be irreversibly lost after method execution.
        """
        for _ in self:
            pass


class Capability(enum.Flag):
    """Enumeration of operations supported by the storage.

    Example:
        ```python
        read_and_write = Capability.STREAM | Capability.CREATE
        if storage.supports(read_and_write)
            ...
        ```
    """

    NONE = 0

    ANALYZE = enum.auto()
    """Return file details from the storage."""

    APPEND = enum.auto()
    """Add content to the existing file."""

    COMPOSE = enum.auto()
    """Combine multiple files into a new one in the same storage."""

    COPY = enum.auto()
    """Make a copy of the file inside the same storage."""

    CREATE = enum.auto()
    """Create a file as an atomic object."""

    EXISTS = enum.auto()
    """Check if file exists."""

    LINK_PERMANENT = enum.auto()
    """Make permanent download link."""

    LINK_TEMPORAL = enum.auto()
    """Make expiring download link."""

    LINK_ONE_TIME = enum.auto()
    """Make one-time download link."""

    MOVE = enum.auto()
    """Move file to a different location inside the same storage."""

    MULTIPART = enum.auto()
    """Create file in 3 stages: initialize, upload(repeatable), complete."""

    RANGE = enum.auto()
    """Return specific range of bytes from the file."""

    REMOVE = enum.auto()
    """Remove file from the storage."""

    RESUMABLE = enum.auto()
    """Perform resumable uploads that can be continued after interruption."""

    SCAN = enum.auto()
    """Iterate over all files in the storage."""

    SIGNED = enum.auto()
    """Generate signed URL for specific operation."""

    STREAM = enum.auto()
    """Return file content as stream of bytes."""

    MANAGER_CAPABILITIES = ANALYZE | SCAN | COPY | MOVE | APPEND | COMPOSE | EXISTS | REMOVE | SIGNED
    READER_CAPABILITIES = RANGE | STREAM | LINK_PERMANENT | LINK_TEMPORAL | LINK_ONE_TIME
    UPLOADER_CAPABILITIES = CREATE | MULTIPART | RESUMABLE

    def exclude(self, *capabilities: Capability):
        """Remove capabilities from the cluster.

        Other Args:
            capabilities: removed capabilities

        Example:
            ```python
            cluster = cluster.exclude(Capability.REMOVE)
            ```
        """
        result = Capability(self)
        for capability in capabilities:
            result = result & ~capability
        return result

    def can(self, operation: Capability) -> bool:
        """Check whether the cluster supports given operation."""
        return (self & operation) == operation


def parse_filesize(value: str) -> int:
    """Transform human-readable filesize into an integer.

    Args:
        value: human-readable filesize

    Raises:
        ValueError: size cannot be parsed or uses unknown units

    Example:
        ```python
        size = parse_filesize("10GiB")
        assert size == 10_737_418_240
        ```
    """
    result = RE_FILESIZE.match(value.strip())
    if not result:
        msg = f"Cannot parse filesize: '{value}'"
        raise ValueError(msg)

    size, unit = result.groups()

    multiplier = UNITS.get(unit.lower())
    if not multiplier:
        msg = f"Unknown unit '{unit}' in filesize: '{value}'"
        raise ValueError(msg)

    # using `int` here means that `1.9 bytes` will be truncated to `1 byte`. I
    # don't know situation where fraction of bytes makes sens and this behavior
    # seems sensible
    return int(float(size) * multiplier)


def humanize_filesize(value: int | float, base: int = SI_BASE) -> str:
    """Transform an integer into human-readable filesize.

    Args:
        value: size in bytes
        base: 1000 for SI(KB, MB) or 1024 for binary(KiB, MiB)

    Raises:
        ValueError: base is not recognized

    Example:
        ```python
        size = humanize_filesize(10_737_418_240, base=1024)
        assert size == "10GiB"
        size = humanize_filesize(10_418_240, base=1024)
        assert size == "9.93MiB"
        ```

    """
    if base == SI_BASE:
        suffixes = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    elif base == BINARY_BASE:
        suffixes = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]
    else:
        msg = f"Base must be {SI_BASE} (SI) or {BINARY_BASE} (binary), got {base}"
        raise ValueError(msg)

    iteration = 0

    while value >= base:
        iteration += 1
        value /= base

    value = int(value * 100) / 100

    num_format = ".2f" if iteration and not value.is_integer() else ".0f"

    return f"{value:{num_format}}{suffixes[iteration]}"


class AbstractReader(Generic[T], abc.ABC):
    """Abstract wrapper that transforms data into readable stream."""

    source: T
    chunk_size: int

    def __init__(self, source: T, chunk_size: int = CHUNK_SIZE):
        self.source = source
        self.chunk_size = chunk_size

    def __iter__(self):
        while chunk := self.read(self.chunk_size):
            yield chunk

    @abc.abstractmethod
    def read(self, size: int | None = None) -> bytes:
        """Read bytes from the source."""
        ...


class IterableBytesReader(AbstractReader[Iterable[int]]):
    """Wrapper that transforms iterable of bytes into readable stream.

    Example:
        The simplest iterable of bytes is a list that contains byte strings:
        ```py
        parts = [b"hello", b" ", b"world"]
        reader = IterableBytesReader(parts)
        assert reader.read() == b"hello world"
        ```

        More realistic scenario is wrapping generator that produces byte string
        in order to initialize [Upload][file_keeper.Upload]:
        ```py
        def data_generator():
            yield b"hello"
            yield b" "
            yield b"world"

        stream = IterableBytesReader(data_generator())
        upload = Upload(stream, "my_file.txt", 11, "text/plain")
        ```

    """

    def __init__(self, source: Iterable[bytes], chunk_size: int = CHUNK_SIZE):
        super().__init__(itertools.chain.from_iterable(source), chunk_size)

    @override
    def read(self, size: int | None = None):
        return bytes(itertools.islice(self.source, 0, size))
