from __future__ import annotations

import logging
import contextlib
import io
import mimetypes
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, cast

import magic
import pytz
from pluggy import HookimplMarker

from file_keeper import Registry, Storage, Upload, ext
from file_keeper.core.storage import LocationTransformer
from file_keeper.core.upload import UploadFactory

from . import adapters

hookimpl = HookimplMarker("file-keeper-ext")
SAMPLE_SIZE = 1024 * 2

log = logging.getLogger(__name__)


@ext.hookimpl
def register_location_transformers(registry: Registry[LocationTransformer]):
    registry.register("safe_relative_path", safe_relative_path_transformer)
    registry.register("fix_extension", fix_extension_transformer)
    registry.register("uuid", uuid_transformer)
    registry.register("uuid_prefix", uuid_prefix_transformer)
    registry.register("uuid_with_extension", uuid_with_extension_transformer)
    registry.register("datetime_prefix", datetime_prefix_transformer)
    registry.register("datetime_with_extension", datetime_with_extension_transformer)


def fix_extension_transformer(location: str, extras: dict[str, Any]) -> str:
    """Choose extension depending on MIME type of upload.

    Upload object must be passed as `upload` inside `extras`, or else
    transformer does nothing.
    """
    if "upload" not in extras:
        return location

    upload = extras["upload"]
    if not isinstance(upload, Upload):
        log.debug(
            "Location %s remains unchanged because of unexpected upload: %s",
            location,
            upload,
        )

    name = os.path.splitext(location)[0]
    if ext := mimetypes.guess_extension(upload.content_type):
        return name + ext

    return location


def safe_relative_path_transformer(location: str, extras: dict[str, Any]) -> str:
    """Remove unsafe segments from path and strip leading slash."""
    return os.path.normpath(location).lstrip("./")


def uuid_transformer(location: str, extras: dict[str, Any]) -> str:
    """Transform location into random UUID."""
    return str(uuid.uuid4())


def uuid_prefix_transformer(location: str, extras: dict[str, Any]) -> str:
    """Prefix the location with random UUID."""
    return str(uuid.uuid4()) + location


def uuid_with_extension_transformer(location: str, extras: dict[str, Any]) -> str:
    """Replace location with random UUID, but keep the original extension."""
    ext = os.path.splitext(location)[1]
    return str(uuid.uuid4()) + ext


def datetime_prefix_transformer(location: str, extras: dict[str, Any]) -> str:
    """Prefix location with current date-timestamp."""
    return datetime.now(pytz.utc).isoformat() + location


def datetime_with_extension_transformer(location: str, extras: dict[str, Any]) -> str:
    """Replace location with current date-timestamp, but keep the extension."""
    ext = os.path.splitext(location)[1]
    return datetime.now(pytz.utc).isoformat() + ext


@ext.hookimpl
def register_upload_factories(registry: Registry[UploadFactory, type]):
    registry.register(tempfile.SpooledTemporaryFile, tempfile_into_upload)
    registry.register(io.TextIOWrapper, textiowrapper_into_upload)


with contextlib.suppress(ImportError):  # pragma: no cover
    import cgi

    @ext.hookimpl(specname="register_upload_factories")
    def _(registry: Registry[UploadFactory, type]):
        registry.register(cgi.FieldStorage, cgi_field_storage_into_upload)

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

    @ext.hookimpl(specname="register_upload_factories")
    def _(registry: Registry[UploadFactory, type]):
        registry.register(FileStorage, werkzeug_file_storage_into_upload)

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
def register_adapters(registry: Registry[type[Storage]]):
    registry.register("file_keeper:fs", adapters.FsStorage)

    if adapters.RedisStorage:
        registry.register("file_keeper:redis", adapters.RedisStorage)

    if adapters.OpenDalStorage:
        registry.register("file_keeper:opendal", adapters.OpenDalStorage)

    if adapters.LibCloudStorage:
        registry.register("file_keeper:libcloud", adapters.LibCloudStorage)

    if adapters.GoogleCloudStorage:
        registry.register("file_keeper:gcs", adapters.GoogleCloudStorage)

    if adapters.S3Storage:
        registry.register("file_keeper:s3", adapters.S3Storage)

    if adapters.FilebinStorage:
        registry.register("file_keeper:filebin", adapters.FilebinStorage)

    if adapters.SqlAlchemyStorage:
        registry.register("file_keeper:sqlalchemy", adapters.SqlAlchemyStorage)
