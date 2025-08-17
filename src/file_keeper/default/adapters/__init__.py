"""Built-in storage adapters."""

from .fs import FsStorage
from .memory import MemoryStorage
from .null import NullStorage
from .proxy import ProxyStorage
from .zip import ZipStorage

try:
    from .azure_blob import AzureBlobStorage
except ImportError:
    AzureBlobStorage = None

try:
    from .filebin import FilebinStorage
except ImportError:
    FilebinStorage = None

try:
    from .gcs import GoogleCloudStorage
except ImportError:
    GoogleCloudStorage = None

try:
    from .libcloud import LibCloudStorage
except ImportError:
    LibCloudStorage = None

try:
    from .opendal import OpenDalStorage
except ImportError:
    OpenDalStorage = None

try:
    from .redis import RedisStorage
except ImportError:
    RedisStorage = None

try:
    from .s3 import S3Storage
except ImportError:
    S3Storage = None

try:
    from .sqlalchemy import SqlAlchemyStorage
except ImportError:
    SqlAlchemyStorage = None

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
]
