__version__ = "0.0.1"

from .core import exceptions as exc
from .core.registry import Registry, adapters
from .core.data import BaseData, FileData, MultipartData
from .core.storage import (
    Manager,
    Reader,
    Settings,
    Storage,
    Uploader,
    make_storage,
)
from .core.upload import Upload, make_upload
from .core.utils import (
    Capability,
    HashingReader,
    IterableBytesReader,
    humanize_filesize,
    is_supported_type,
    parse_filesize,
)
from . import ext


__all__ = [
    "adapters",
    "FileData",
    "BaseData",
    "MultipartData",
    "is_supported_type",
    "Registry",
    "Capability",
    "parse_filesize",
    "humanize_filesize",
    "IterableBytesReader",
    "HashingReader",
    "make_upload",
    "Upload",
    "exc",
    "make_storage",
    "Storage",
    "Reader",
    "Uploader",
    "Manager",
    "Settings",
    "ext",
]

# ext.setup()
