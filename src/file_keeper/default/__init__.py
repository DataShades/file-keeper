"""Default implementations of file-keeper units."""

from __future__ import annotations

import contextlib
import io
import logging
import mimetypes
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, cast

import magic

from file_keeper import BaseData, Registry, Storage, Upload, ext, types
from file_keeper.core.upload import UploadFactory

from . import adapters

SAMPLE_SIZE = 1024 * 2

log = logging.getLogger(__name__)
FILE_KEEPER_DNS = uuid.UUID("5b762d43-ec0d-3270-a565-8bb44bdaf6cf")


@ext.hookimpl
def register_location_transformers(registry: Registry[types.LocationTransformer]):
    """Built-in location transformers."""
    registry.register("datetime_prefix", datetime_prefix_transformer)
    registry.register("datetime_with_extension", datetime_with_extension_transformer)
    registry.register("fix_extension", fix_extension_transformer)
    registry.register("safe_relative_path", safe_relative_path_transformer)
    registry.register("uuid", uuid_transformer)
    registry.register("uuid_prefix", uuid_prefix_transformer)
    registry.register("uuid_with_extension", uuid_with_extension_transformer)
    registry.register("static_uuid", static_uuid_transformer)


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


def uuid_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Transform location into random UUID."""
    return str(uuid.uuid4())


def static_uuid_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Transform location into static UUID.

    The same location always transformed into the same UUID. This transformer
    combined with `fix_extension` can be used as an alternative to the
    `safe_relative_path` if you want to avoid nested folders.
    """
    return str(uuid.uuid5(FILE_KEEPER_DNS, location))


def uuid_prefix_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Prefix the location with random UUID."""
    return str(uuid.uuid4()) + location


def uuid_with_extension_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Replace location with random UUID, but keep the original extension."""
    ext = os.path.splitext(location)[1]
    return str(uuid.uuid4()) + ext


def datetime_prefix_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Prefix location with current date-timestamp."""
    return datetime.now(timezone.utc).isoformat() + location


def datetime_with_extension_transformer(location: str, upload: Upload | None, extras: dict[str, Any]) -> str:
    """Replace location with current date-timestamp, but keep the extension."""
    ext = os.path.splitext(location)[1]
    return datetime.now(timezone.utc).isoformat() + ext


@ext.hookimpl
def register_upload_factories(registry: Registry[UploadFactory, type]):
    """Built-in upload converter."""
    registry.register(tempfile.SpooledTemporaryFile, tempfile_into_upload)
    registry.register(io.TextIOWrapper, textiowrapper_into_upload)


with contextlib.suppress(ImportError):
    import cgi

    @ext.hookimpl(specname="register_upload_factories")
    def _(registry: Registry[UploadFactory, type]):
        registry.register(cgi.FieldStorage, cgi_field_storage_into_upload)

    def cgi_field_storage_into_upload(value: cgi.FieldStorage):
        """cgi.field-into-upload factory."""
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


with contextlib.suppress(ImportError):
    from werkzeug.datastructures import FileStorage

    @ext.hookimpl(specname="register_upload_factories")
    def _(registry: Registry[UploadFactory, type]):
        registry.register(FileStorage, werkzeug_file_storage_into_upload)

    def werkzeug_file_storage_into_upload(value: FileStorage):
        """werkzeug.FileStorage-into-upload converter."""
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
    """tmpfile-into-upload converter."""
    mime = magic.from_buffer(value.read(SAMPLE_SIZE), True)
    _ = value.seek(0, 2)
    size = value.tell()
    _ = value.seek(0)

    return Upload(value, value.name or "", size, mime)


def textiowrapper_into_upload(value: io.TextIOWrapper):
    """TextIO-into-upload converter."""
    return cast(io.BufferedReader, value.buffer)


# --8<-- [start:register]
@ext.hookimpl
def register_adapters(registry: Registry[type[Storage]]):  # noqa: C901
    """Built-in storage adapters."""
    registry.register("file_keeper:fs", adapters.FsStorage)
    # --8<-- [end:register]
    registry.register("file_keeper:null", adapters.NullStorage)
    registry.register("file_keeper:memory", adapters.MemoryStorage)
    registry.register("file_keeper:zip", adapters.ZipStorage)

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

    if adapters.AzureBlobStorage:
        registry.register("file_keeper:azure_blob", adapters.AzureBlobStorage)

    if adapters.ObjectStoreStorage:
        registry.register("file_keeper:object_store", adapters.ObjectStoreStorage)

    if adapters.FsSpecStorage:
        registry.register("file_keeper:fsspec", adapters.FsSpecStorage)

    registry.register("file_keeper:proxy", adapters.ProxyStorage)  # pyright: ignore[reportArgumentType]
