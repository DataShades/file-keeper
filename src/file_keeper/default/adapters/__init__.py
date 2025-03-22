from .fs import FsStorage

try:
    from .redis import RedisStorage
except ImportError:
    RedisStorage = None

try:
    from .opendal import OpenDalStorage
except ImportError:
    OpenDalStorage = None

try:
    from .libcloud import LibCloudStorage
except ImportError:
    LibCloudStorage = None

try:
    from .gcs import GoogleCloudStorage
except ImportError:
    GoogleCloudStorage = None

try:
    from .s3 import S3Storage
except ImportError:
    S3Storage = None

try:
    from .filebin import FilebinStorage
except ImportError:
    FilebinStorage = None

try:
    from .sqlalchemy import SqlAlchemyStorage
except ImportError:
    SqlAlchemyStorage = None

__all__ = [
    "FsStorage",
    "RedisStorage",
    "OpenDalStorage",
    "LibCloudStorage",
    "FilebinStorage",
    "GoogleCloudStorage",
    "S3Storage",
    "SqlAlchemyStorage"
]
