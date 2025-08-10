# Upload

The [Upload][file_keeper.Upload] class represents the data you want to store in
a storage backend. It's a key component in file-keeper, encapsulating the
file's content, metadata, and instructions for how to transfer it to
storage. This document explains how to create and use
[Upload][file_keeper.Upload] objects, covering streaming uploads and hashing
for data integrity.

## What is an [Upload][file_keeper.Upload]?

Think of an [Upload][file_keeper.Upload] as a package containing everything
needed to send a file to storage. It's more than just the raw data; it includes
information about the file itself, like its name, size, and content type. This
metadata is essential for proper storage and retrieval.

The [Upload][file_keeper.Upload] object decouples the *source* of the data from
the *transfer* process. This allows file-keeper to handle various data sources
– files on disk, in-memory buffers, network streams – without changing the core
storage logic.

## Creating an [Upload][file_keeper.Upload] Object

You can create an [Upload][file_keeper.Upload] object in several ways,
depending on the source of your data. The recommended way is using
[make_upload][file_keeper.make_upload] helper:

*   **From a File-like Object:** If you have an open file, you can directly
    pass it to the [make_upload][file_keeper.make_upload] function. file-keeper will
    handle reading the data from the file.

    ```python
    src = open("my_image.jpg", "rb")
    upload = make_upload(src)
    ```

*   **From a Byte String:** If your data is already in memory as a byte string,
    you can pass it directly.

    ```python
    data = b"This is the content of my file."
    upload = make_upload(data)
    ```

*   **From an werkzeug's FileStorage:** when writing an application using
    werkzeug-based framework you can handle uploaded files in this way.

    ```python
    from werkzeug.datastructures import FileStorage

    data = FileStorage(..., "my_data.txt")
    upload = make_upload(data)
    ```

*   **From arbitrary source manually:** This is useful for large files that
    don't fit in memory. You need to provide an object that has methods `read`
    and `__iter__` producing byte string as a first argument to
    [Upload][file_keeper.Upload] class. If you have a generator that yields
    data, wrap it into [IterableBytesReader][file_keeper.IterableBytesReader]
    instead of manually implementing class with required methods:

    ```python
    from file_keeper import Upload, IterableBytesReader

    def data_generator():
        yield b"hello"
        yield b" "
        yield b"world"

    stream = IterableBytesReader(data_generator())
    upload = Upload(stream, "my_file.txt", 11, "text/plain")
    ```


The [make_upload][file_keeper.make_upload] function automatically determines
the file size and content type for supported source types.

## Streaming Uploads

For very large files, loading the entire content into memory is
impractical. Streaming uploads allow you to send the data in chunks, reducing
memory usage and improving performance.

As shown in the example above, you can create an [Upload][file_keeper.Upload]
object from an iterable of bytes. file-keeper will then stream the data to the
storage backend as it becomes available. This is the preferred method for
handling large files, but it expects that you compute the size and content type
of the upload in advance and provide these details to the
[Upload][file_keeper.Upload] constructor.

## Hashing for Data Integrity

Data integrity is crucial when transferring files. Hashing ensures that the
data you upload is exactly the same as the data stored in the
backend. file-keeper automatically calculates a hash of the upload data during
the transfer process.

The calculated hash is stored as part of the [FileData][file_keeper.FileData]
metadata. When you retrieve the file, file-keeper can recalculate the hash via
[Storage.analyze][file_keeper.Storage.analyze] method to verify data
integrity. If the hashes don't match, it indicates that the file has been
corrupted or tampered with.

Hashing is performed transparently during the upload process, so you don't need
to worry about implementing it yourself. It provides an extra layer of
assurance that your data is stored reliably.
