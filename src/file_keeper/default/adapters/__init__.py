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
    from .libcloud import LibCloudStorage  # type: ignore
except ImportError:
    LibCloudStorage = None

try:
    from .gcs import GcsStorage  # type: ignore
except ImportError:
    GcsStorage = None

try:
    from .s3 import S3Storage  # type: ignore
except ImportError:
    S3Storage = None

__all__ = [
    "FsStorage",
    "RedisStorage",
    "OpenDalStorage",
    "LibCloudStorage",
    "GcsStorage",
    "S3Storage",
]
