# Local Filesystem Adapter

The `file_keeper:fs` adapter allows you to use your local filesystem for storing and retrieving files. This adapter is useful for testing, development, or scenarios where you need to store files locally.

## Overview

This adapter provides a simple way to interact with the local filesystem. You'll need to specify the base path where files will be stored.

## Initialization Example

Here's an example of how to initialize the local filesystem adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_local_storage", {
    "type": "file_keeper:fs",
    "path": "/tmp/file-keeper",  # Replace with your desired base path
    "initialize": True,  # Optional: Create the directory if it doesn't exist
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace `/tmp/file-keeper` with the desired base path on your system.
*   The `initialize` option (defaulting to `False`) determines whether the adapter should attempt to create the specified directory if it doesn't exist. If `initialize` is `True` and the directory cannot be created (e.g., due to permissions issues), an error will be raised.
*   Ensure that the process running file-keeper has the necessary permissions to read and write to the specified directory.
