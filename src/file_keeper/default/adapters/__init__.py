"""Built-in storage adapters."""

import contextlib

from .fs import FsStorage
from .memory import MemoryStorage
from .null import NullStorage
from .proxy import ProxyStorage
from .zip import ZipStorage

AzureBlobStorage = None
with contextlib.suppress(ImportError):
    from .azure_blob import AzureBlobStorage

FilebinStorage = None
with contextlib.suppress(ImportError):
    from .filebin import FilebinStorage


GoogleCloudStorage = None
with contextlib.suppress(ImportError):
    from .gcs import GoogleCloudStorage

LibCloudStorage = None
with contextlib.suppress(ImportError):
    from .libcloud import LibCloudStorage

OpenDalStorage = None
with contextlib.suppress(ImportError):
    from .opendal import OpenDalStorage

RedisStorage = None
with contextlib.suppress(ImportError):
    from .redis import RedisStorage


S3Storage = None
with contextlib.suppress(ImportError):
    from .s3 import S3Storage

FsSpecStorage = None
with contextlib.suppress(ImportError):
    from .fsspec import FsSpecStorage

ObjectStoreStorage = None
with contextlib.suppress(ImportError):
    from .obstore import ObjectStoreStorage

SqlAlchemyStorage = None
with contextlib.suppress(ImportError):
    from .sqlalchemy import SqlAlchemyStorage

__all__ = [
    "AzureBlobStorage",
    "FilebinStorage",
    "FsStorage",
    "GoogleCloudStorage",
    "LibCloudStorage",
    "MemoryStorage",
    "NullStorage",
    "OpenDalStorage",
    "ProxyStorage",
    "RedisStorage",
    "S3Storage",
    "SqlAlchemyStorage",
    "ZipStorage",
    "FsSpecStorage",
    "ObjectStoreStorage",
]
