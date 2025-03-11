__version__ = "0.0.1"

import file_keeper.exceptions as exc
from file_keeper.registry import Registry, adapters, collect_all
from file_keeper.data import BaseData, FileData, MultipartData
from file_keeper.storage import (
    Manager,
    Reader,
    Settings,
    Storage,
    Uploader,
    make_storage,
)
from file_keeper.upload import Upload, make_upload
from file_keeper.utils import (
    Capability,
    HashingReader,
    IterableBytesReader,
    humanize_filesize,
    is_supported_type,
    parse_filesize,
)
from file_keeper import ext


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


ext.plugin.load_setuptools_entrypoints(ext.spec.name)
collect_all()
