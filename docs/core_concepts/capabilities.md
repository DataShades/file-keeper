# Capabilities

The [Capability][file_keeper.Capability] enum defines the features supported by different storage
backends. It's a fundamental concept in file-keeper, enabling the system to
adapt to the limitations and strengths of each storage provider. This document
explains the [Capability][file_keeper.Capability] enum, how to check for support, and provides
practical examples.

## What are Capabilities?

Not all storage systems are created equal. Some support resumable uploads,
while others don't. Some offer efficient copy and move operations, while others
require you to handle this type of tasks yourself.
[Capabilities][file_keeper.Capability] provide a standardized way to describe
what a particular storage backend *can do*.

The [Capability][file_keeper.Capability] enum is a set of flags, each
representing a specific feature.  By checking which capabilities a
[Storage][file_keeper.Storage] object possesses, file-keeper can dynamically
adjust its behavior to ensure compatibility and optimal performance.

## The [Capability][file_keeper.Capability] Enum

Here's a breakdown of the key capabilities:

| Capability                                              | Description                                                         |
|---------------------------------------------------------|---------------------------------------------------------------------|
| [ANALYZE][file_keeper.Capability.ANALYZE]               | Return file details from the storage.                               |
| [APPEND][file_keeper.Capability.APPEND]                 | Add content to the existing file.                                   |
| [COMPOSE][file_keeper.Capability.COMPOSE]               | Combine multiple files into a new one in the same storage.          |
| [COPY][file_keeper.Capability.COPY]                     | Make a copy of the file inside the same storage.                    |
| [CREATE][file_keeper.Capability.CREATE]                 | Create a file as an atomic object.                                  |
| [EXISTS][file_keeper.Capability.EXISTS]                 | Check if file exists.                                               |
| [MOVE][file_keeper.Capability.MOVE]                     | Move file to a different location inside the same storage.          |
| [MULTIPART][file_keeper.Capability.MULTIPART]           | Create file in 3 stages: initialize, upload(repeatable), complete.  |
| [RANGE][file_keeper.Capability.RANGE]                   | Return specific range of bytes from the file.                       |
| [REMOVE][file_keeper.Capability.REMOVE]                 | Remove file from the storage.                                       |
| [RESUMABLE][file_keeper.Capability.RESUMABLE]           | Perform resumable uploads that can be continued after interruption. |
| [SCAN][file_keeper.Capability.SCAN]                     | Iterate over all files in the storage.                              |
| [SIGNED][file_keeper.Capability.SIGNED]                 | Generate signed URL for specific operation.                         |
| [STREAM][file_keeper.Capability.STREAM]                 | Return file content as stream of bytes.                             |
| [PERMANENT_LINK][file_keeper.Capability.PERMANENT_LINK] | Make permanent download link.                                       |
| [TEMPORAL_LINK][file_keeper.Capability.TEMPORAL_LINK]   | Make expiring download link.                                        |
| [ONE_TIME_LINK][file_keeper.Capability.ONE_TIME_LINK]   | Make one-time download link.                                        |


## Checking for Capability Support

You can determine if a [Storage][file_keeper.Storage] object supports a specific capability using
the [supports()][file_keeper.Storage.supports] method:


```python
from file_keeper import Capability, make_storage

storage = make_storage("my_storage", {"adapter": "s3", "region": "us-east-1"})

if storage.supports(Capability.RESUMABLE):
    print("This storage supports resumable uploads!")
else:
    print("Resumable uploads are not supported by this storage.")

if storage.supports(Capability.REMOVE):
    print("This storage supports file removal.")
else:
    print("File removal is not supported by this storage.")
```

The `supports()` method returns `True` if the storage backend has the specified
capability, and `False` otherwise.
