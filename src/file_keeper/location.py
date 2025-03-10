from __future__ import annotations
from collections.abc import Callable
import os
from typing import Any
import uuid
from datetime import datetime

import pytz
from . import utils, upload

strategies = utils.Registry[
    "Callable[[str, upload.Upload | None, dict[str, Any]], str]"
]({})


@strategies.decorated("transparent")
def transparent_strategy(
    location: str, upload: upload.Upload | None, extras: dict[str, Any]
) -> str:
    return location


@strategies.decorated("uuid")
def uuid_strategy(
    location: str, upload: upload.Upload | None, extras: dict[str, Any]
) -> str:
    return str(uuid.uuid4())


@strategies.decorated("uuid_prefix")
def uuid_prefix_strategy(
    location: str, upload: upload.Upload | None, extras: dict[str, Any]
) -> str:
    return str(uuid.uuid4()) + location


@strategies.decorated("uuid_with_extension")
def uuid_with_extension_strategy(
    location: str, upload: upload.Upload | None, extras: dict[str, Any]
) -> str:
    _path, ext = os.path.splitext(location)
    return str(uuid.uuid4()) + ext


@strategies.decorated("datetime_prefix")
def datetime_prefix_strategy(
    location: str, upload: upload.Upload | None, extras: dict[str, Any]
) -> str:
    return datetime.now(pytz.utc).isoformat() + location


@strategies.decorated("datetime_with_extension")
def datetime_with_extension_strategy(
    location: str, upload: upload.Upload | None, extras: dict[str, Any]
) -> str:
    _path, ext = os.path.splitext(location)
    return datetime.now(pytz.utc).isoformat() + ext
