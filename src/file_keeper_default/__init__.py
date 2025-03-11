from __future__ import annotations

import contextlib
import io
import mimetypes
import tempfile
import os
import uuid
from datetime import datetime
from typing import Any, cast
import magic
import pytz

from file_keeper.upload import Upload
from file_keeper import Upload, ext, Storage
from file_keeper.registry import LocationStrategy, UploadFactory


from pluggy import HookimplMarker

hookimpl = HookimplMarker("file-keeper-ext")
SAMPLE_SIZE = 1024 * 2


@ext.hookimpl
def collect_location_strategies() -> dict[str, LocationStrategy]:
    return {
        "transparent": transparent_strategy,
        "uuid": uuid_strategy,
        "uuid_prefix": uuid_prefix_strategy,
        "uuid_with_extension": uuid_with_extension_strategy,
        "datetime_prefix": datetime_prefix_strategy,
        "datetime_with_extension": datetime_with_extension_strategy,
    }


def transparent_strategy(
    location: str, upload: Upload | None, extras: dict[str, Any]
) -> str:
    return location


def uuid_strategy(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    return str(uuid.uuid4())


def uuid_prefix_strategy(
    location: str, upload: Upload | None, extras: dict[str, Any]
) -> str:
    return str(uuid.uuid4()) + location


def uuid_with_extension_strategy(
    location: str, upload: Upload | None, extras: dict[str, Any]
) -> str:
    _path, ext = os.path.splitext(location)
    return str(uuid.uuid4()) + ext


def datetime_prefix_strategy(
    location: str, upload: Upload | None, extras: dict[str, Any]
) -> str:
    return datetime.now(pytz.utc).isoformat() + location


def datetime_with_extension_strategy(
    location: str, upload: Upload | None, extras: dict[str, Any]
) -> str:
    _path, ext = os.path.splitext(location)
    return datetime.now(pytz.utc).isoformat() + ext


@ext.hookimpl
def collect_upload_factories() -> dict[type, UploadFactory]:
    return {
        tempfile.SpooledTemporaryFile: tempfile_into_upload,
        io.TextIOWrapper: textiowrapper_into_upload,
    }


with contextlib.suppress(ImportError):  # pragma: no cover
    import cgi

    @ext.hookimpl(specname="collect_upload_factories")
    def _() -> dict[type, UploadFactory]:
        return {
            cgi.FieldStorage: cgi_field_storage_into_upload,
        }

    def cgi_field_storage_into_upload(value: cgi.FieldStorage):
        if not value.filename or not value.file:
            return None

        mime, _encoding = mimetypes.guess_type(value.filename)
        if not mime:
            mime = magic.from_buffer(value.file.read(SAMPLE_SIZE), True)
            _ = value.file.seek(0)

        _ = value.file.seek(0, 2)
        size = value.file.tell()
        _ = value.file.seek(0)

        return Upload(
            value.file,
            value.filename,
            size,
            mime,
        )


with contextlib.suppress(ImportError):  # pragma: no cover
    from werkzeug.datastructures import FileStorage

    @ext.hookimpl(specname="collect_upload_factories")
    def _() -> dict[type, UploadFactory]:
        return {FileStorage: werkzeug_file_storage_into_upload}

    def werkzeug_file_storage_into_upload(value: FileStorage):
        name: str = value.filename or value.name or ""
        if value.content_length:
            size = value.content_length
        else:
            _ = value.stream.seek(0, 2)
            size = value.stream.tell()
            _ = value.stream.seek(0)

        mime = magic.from_buffer(value.stream.read(SAMPLE_SIZE), True)
        _ = value.stream.seek(0)

        return Upload(value.stream, name, size, mime)


def tempfile_into_upload(value: tempfile.SpooledTemporaryFile[bytes]):
    mime = magic.from_buffer(value.read(SAMPLE_SIZE), True)
    _ = value.seek(0, 2)
    size = value.tell()
    _ = value.seek(0)

    return Upload(value, value.name or "", size, mime)


def textiowrapper_into_upload(value: io.TextIOWrapper):
    return cast(io.BufferedReader, value.buffer)


@ext.hookimpl
def collect_adapters() -> dict[str, type[Storage]]: ...
