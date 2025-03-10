from __future__ import annotations
import contextlib
from io import BufferedReader, BytesIO, TextIOWrapper
import mimetypes
import tempfile
from typing import Any, cast

import dataclasses

import magic


from . import utils, types


SAMPLE_SIZE = 1024 * 2

upload_factories: "utils.Registry[types.UploadFactory, type]" = utils.Registry()


@dataclasses.dataclass
class Upload:
    """Standard upload details.

    Args:
        stream: iterable of bytes or file-like object
        filename: name of the file
        size: size of the file in bytes
        content_type: MIMEtype of the file

    Example:
        ```
        Upload(
            BytesIO(b"hello world"),
            "file.txt",
            11,
            "text/plain",
        )
        ```
    """

    stream: types.PStream
    filename: str
    size: int
    content_type: str

    @property
    def seekable_stream(self) -> types.PSeekableStream | None:
        """Return stream that can be rewinded after reading.

        If internal stream does not support file-like `seek`, nothing is
        returned from this property.

        Use this property if you want to read the file ahead, to get CSV column
        names, list of files inside ZIP, EXIF metadata. If you get `None` from
        it, stream does not support seeking and you won't be able to rewind
        cursor to the beginning of the file after reading something.

        Example:
            ```python
            upload = make_upload(...)
            if fd := upload.seekable_stream():
                # read fragment of the file
                chunk = fd.read(1024)
                # move cursor to the end of the stream
                fd.seek(0, 2)
                # position of the cursor is the same as number of bytes in stream
                size = fd.tell()
                # move cursor back, because you don't want to accidentally loose
                # any bites from the beginning of stream when uploader reads from it
                fd.seek(0)
            ```

        Returns:
            file-like stream or nothing

        """
        if hasattr(self.stream, "tell") and hasattr(self.stream, "seek"):
            return cast(types.PSeekableStream, self.stream)

        return None

    def hashing_reader(self, **kwargs: Any) -> utils.HashingReader:
        return utils.HashingReader(self.stream, **kwargs)


with contextlib.suppress(ImportError):  # pragma: no cover
    import cgi

    @upload_factories.decorated(cgi.FieldStorage)
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

    @upload_factories.decorated(FileStorage)
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


@upload_factories.decorated(tempfile.SpooledTemporaryFile)
def tempfile_into_upload(value: tempfile.SpooledTemporaryFile[bytes]):
    mime = magic.from_buffer(value.read(SAMPLE_SIZE), True)
    _ = value.seek(0, 2)
    size = value.tell()
    _ = value.seek(0)

    return Upload(value, value.name or "", size, mime)


@upload_factories.decorated(TextIOWrapper)
def textiowrapper_into_upload(value: TextIOWrapper):
    return cast(BufferedReader, value.buffer)


def make_upload(value: Any) -> Upload:
    """Convert value into Upload object.

    Use this function for simple and reliable initialization of Upload
    object. Avoid creating Upload manually, unless you are 100% sure you can
    provide correct MIMEtype, size and stream.

    Args:
        value: content of the file

    Raises:
        TypeError: content has unsupported type

    Returns:
        upload object with specified content

    Example:
        ```python
        storage.upload("file.txt", make_upload(b"hello world"))
        ```

    """
    if isinstance(value, Upload):
        return value

    initial_type: type = type(value)

    fallback_factory = None
    for t in upload_factories:
        if initial_type is t:
            transformed_value = upload_factories[t](value)
            if transformed_value is not None:
                value = transformed_value
                break

        if not fallback_factory and issubclass(initial_type, t):
            fallback_factory = upload_factories[t]

    else:
        if fallback_factory:
            value = fallback_factory(value)

    # ideal situation: factory produced the Upload object
    if isinstance(value, Upload):
        return value

    if isinstance(value, (bytes, bytearray)):
        value = BytesIO(value)

    # convenient situation: factory produced binary buffer and we know how to
    # transform it into an Upload. Factories will choose this option to avoid
    # repeating mimetype detection logic
    if isinstance(value, (BytesIO, BufferedReader)):
        mime = magic.from_buffer(value.read(SAMPLE_SIZE), True)
        _ = value.seek(0, 2)
        size = value.tell()
        _ = value.seek(0)

        return Upload(value, getattr(value, "name", ""), size, mime)

    raise TypeError(type(value))
