"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal module except for config, types and exceptions. Only independent tools
are stored here, to avoid import cycles.

"""

from __future__ import annotations

import abc
import enum
import hashlib
import io
import itertools
import logging
import re
from typing import Generic, Iterable, Iterator

from typing_extensions import TypeVar

from . import types

T = TypeVar("T")

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

    def __init__(
        self,
        stream: types.PStream,
        chunk_size: int = CHUNK_SIZE,
        algorithm: str = "md5",
    ):
        self.stream = stream
        self.chunk_size = chunk_size
        self.algorithm = algorithm
        self.hashsum = hashlib.new(algorithm)
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

    next = __next__

    def read(self) -> bytes:
        """Read and return all bytes from stream at once."""
        return b"".join(self)

    def get_hash(self):
        """Get current content hash as a string."""
        return self.hashsum.hexdigest()

    def exhaust(self):
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

    # return file details from the storage, as if file was uploaded just now
    ANALYZE = enum.auto()
    # add content to the existing file
    APPEND = enum.auto()
    # combine multiple files into a new one in the same storage
    COMPOSE = enum.auto()
    # make a copy of the file inside the same storage
    COPY = enum.auto()
    # create a file as an atomic object
    CREATE = enum.auto()
    # check if file exists
    EXISTS = enum.auto()
    # move file to a different location inside the same storage
    MOVE = enum.auto()
    # create file in 3 stages: initialize, upload(repeatable), complete
    MULTIPART = enum.auto()
    # return specific range of bytes from the file
    RANGE = enum.auto()
    # remove file from the storage
    REMOVE = enum.auto()
    # iterate over all files in the storage
    SCAN = enum.auto()
    # return file content as stream of bytes
    STREAM = enum.auto()

    # make permanent download link for file
    PERMANENT_LINK = enum.auto()
    # make expiring download link for private file
    TEMPORAL_LINK = enum.auto()
    # make one-time download link for private file
    ONE_TIME_LINK = enum.auto()

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
        raise ValueError(value)

    size, unit = result.groups()

    multiplier = UNITS.get(unit.lower())
    if not multiplier:
        raise ValueError(value)

    return int(float(size) * multiplier)


def humanize_filesize(value: int | float, base: int = SI_BASE) -> str:
    """Transform an integer into human-readable filesize.

    Args:
        value: size in bytes

    Named args:
        base: 1000 for SI(KB, MB) or 1024 for binary(KiB, MiB)

    Raises:
        ValueError: base is not recognized

    Example:
        ```python
        size = humanize_filesize(10_737_418_240, base=1024)
        assert size == "10GiB"
        size = humanize_filesize(10_418_240, base=1024)
        assert size == "9.9MiB"
        ```

    """
    if base == SI_BASE:
        suffixes = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    elif base == BINARY_BASE:
        suffixes = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]
    else:
        raise ValueError(base)

    iteration = 0

    while value >= base:
        iteration += 1
        value /= base

    value = int(value * 100) / 100

    num_format = ".2f" if iteration and not value.is_integer() else ".0f"

    return f"{value:{num_format}}{suffixes[iteration]}"


class AbstractReader(Generic[T], abc.ABC):
    def __init__(self, source: T, chunk_size: int = CHUNK_SIZE):
        self.source = source
        self.chunk_size = chunk_size

    def __iter__(self):
        while chunk := self.read(self.chunk_size):
            yield chunk

    @abc.abstractmethod
    def read(self, size: int | None = None) -> bytes: ...


class IterableBytesReader(AbstractReader[Iterable[int]]):
    def __init__(self, source: Iterable[bytes], chunk_size: int = CHUNK_SIZE):
        super().__init__(itertools.chain.from_iterable(source), chunk_size)

    def read(self, size: int | None = None):
        return bytes(itertools.islice(self.source, 0, size))
