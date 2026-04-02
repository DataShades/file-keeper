"""Default implementations of file-keeper units."""

from __future__ import annotations

import contextlib
import io
import logging
import mimetypes
import tempfile
from typing import cast

import magic

from file_keeper import Registry, Storage, Upload, ext, types
from file_keeper.core.upload import UploadFactory

from . import adapters, transformers

SAMPLE_SIZE = 1024 * 2

log = logging.getLogger(__name__)


@ext.hookimpl
def register_location_transformers(registry: Registry[types.LocationTransformer]):
    """Built-in location transformers."""
    registry.register("datetime_prefix", transformers.datetime_prefix_transformer)
    registry.register("datetime_with_extension", transformers.datetime_with_extension_transformer)
    registry.register("fix_extension", transformers.fix_extension_transformer)
    registry.register("safe_relative_path", transformers.safe_relative_path_transformer)
    registry.register("uuid4", transformers.uuid4_transformer)
    registry.register("uuid4_prefix", transformers.uuid4_prefix_transformer)
    registry.register("uuid4_with_extension", transformers.uuid4_with_extension_transformer)
    registry.register("uuid5", transformers.uuid5_transformer)


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
