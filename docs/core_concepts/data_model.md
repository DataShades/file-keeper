# Data model

This document details the core data models used within the file-keeper system:
[Storage][file_keeper.Storage], [FileData][file_keeper.FileData], and
[Location][file_keeper.Location]. It explains the *why* behind these concepts
and how they work together to provide a flexible and reliable file storage
solution.

## Storage

The [Storage][file_keeper.Storage] class is the central point of interaction
with any underlying storage system – whether that's a cloud provider like AWS
S3 or Google Cloud Storage, a local filesystem, or something else entirely.
Think of it as an adapter that translates file-keeper's generic requests into
the specific language of the storage backend.

Instead of directly dealing with the complexities of each storage system, you
interact with [Storage][file_keeper.Storage] objects.  file-keeper handles the
details of connecting, authenticating, and performing operations.  Each
[Storage][file_keeper.Storage] instance is equipped with specialized *services*
– [Uploader][file_keeper.Uploader], [Reader][file_keeper.Reader], and
[Manager][file_keeper.Manager] – to handle different types of tasks.  This
separation of concerns makes the system more modular and easier to extend.


## FileData

[FileData][file_keeper.FileData] represents a file as *known to
file-keeper*. It's a metadata record that contains everything we need to
identify and manage a file, regardless of where it's physically stored.

Crucially, [FileData][file_keeper.FileData] is independent of the underlying
storage. It's a consistent representation that allows file-keeper to work with
different storage backends seamlessly.  It tracks essential information like
the file's name, size, content type, and content hash.  It can also store
additional, storage-specific metadata in the
[storage_data][file_keeper.FileData] field.

[FileData][file_keeper.FileData] is the key to operations like tracking
progress during uploads, managing file versions, and providing consistent
access to file information across different storage systems.

## Location

[Location][file_keeper.Location] represents the *address* of a file within a
specific storage system.  It's a simple string, but it's given a specific
meaning within file-keeper.

Think of it as a path or key that uniquely identifies a file within its storage
backend.  The format of a [Location][file_keeper.Location] will vary depending
on the storage system (e.g., an S3 key, a filesystem path).

file-keeper uses [Location][file_keeper.Location] objects to tell the
[Storage][file_keeper.Storage] adapter *where* to find a file.  It also
provides a mechanism for transforming [Location][file_keeper.Location] objects
to different formats if needed, allowing for flexibility and compatibility with
different storage systems.
