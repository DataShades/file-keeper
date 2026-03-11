"""Default transformers for file_keeper."""

from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from file_keeper import BaseData, Upload

FILE_KEEPER_DNS = uuid.UUID("5b762d43-ec0d-3270-a565-8bb44bdaf6cf")

log = logging.getLogger(__name__)


def uuid_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Transform location into random UUID."""
    dir, file = os.path.split(location)
    return os.path.join(dir, str(uuid.uuid4()))


def uuid_prefix_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Prefix the location with random UUID."""
    dir, file = os.path.split(location)
    return os.path.join(dir, f"{uuid.uuid4()}{file}")


def uuid_with_extension_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Replace location with random UUID, but keep the original extension."""
    dir, file = os.path.split(location)
    ext = os.path.splitext(file)[1]
    return os.path.join(dir, str(uuid.uuid4()) + ext)


def static_uuid_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Transform location into static UUID.

    The same location always transformed into the same UUID. This transformer
    combined with `fix_extension` can be used as an alternative to the
    `safe_relative_path` if you want to avoid nested folders.
    """
    dir, file = os.path.split(location)
    return os.path.join(dir, str(uuid.uuid5(FILE_KEEPER_DNS, location)))

def datetime_prefix_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Prefix location with current date-timestamp."""
    dir, file = os.path.split(location)
    now = datetime.now(timezone.utc).isoformat()
    return os.path.join(dir, now + file)


def datetime_with_extension_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Replace location with current date-timestamp, but keep the extension."""
    dir, file = os.path.split(location)
    ext = os.path.splitext(file)[1]
    now = datetime.now(timezone.utc).isoformat()
    return os.path.join(dir, now + ext)


def fix_extension_transformer(location: str, upload: Upload | BaseData | None, extras: dict[str, Any]) -> str:
    """Choose extension depending on MIME type of upload.

    When upload is not specified, transformer does nothing.
    """
    if not upload:
        log.debug("Location %s remains unchanged because upload is not specified", location)
        return location

    name = os.path.splitext(location)[0]

    if ext := mimetypes.guess_extension(upload.content_type):
        return name + ext

    log.debug(
        "Location %s remains unchanged because of unexpected upload: %s",
        location,
        upload,
    )
    return location


def safe_relative_path_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Remove unsafe segments from path and strip leading slash."""
    return os.path.normpath(location).lstrip("./")
