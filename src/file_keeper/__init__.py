"""Main entrypoint of the file-keeper.

file-keeper is a Python library that provides a unified interface for
storing, retrieving, and managing files across different storage backends
including local filesystem, cloud services (S3, GCS, Azure), and in-memory
storage.
"""

from .core import exceptions as exc
from .core import types
from .core.data import BaseData, FileData
from .core.registry import Registry
from .core.storage import (
    Manager,
    Reader,
    Settings,
    Storage,
    Uploader,
    adapters,
    get_storage,
    make_storage,
)
from .core.types import Location, SignedAction
from .core.upload import Upload, make_upload
from .core.utils import (
    Capability,
    HashingReader,
    IterableBytesReader,
    humanize_filesize,
    parse_filesize,
)

__all__ = [
    "BaseData",
    "Capability",
    "Location",
    "SignedAction",
    "FileData",
    "HashingReader",
    "IterableBytesReader",
    "Manager",
    "Reader",
    "Registry",
    "Settings",
    "Storage",
    "Upload",
    "Uploader",
    "adapters",
    "exc",
    "hookimpl",
    "humanize_filesize",
    "make_storage",
    "get_storage",
    "make_upload",
    "parse_filesize",
    "types",
    "ext",
]

from .ext import hookimpl  # must be the last line to avoid circular imports
