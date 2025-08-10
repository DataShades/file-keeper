# ZIP Archive Adapter

The `file_keeper:zip` adapter allows you to use a ZIP archive as a storage backend. This adapter is useful for packaging and distributing files in a single archive.

## Overview

This adapter stores files within a ZIP archive. You'll need to provide the path to the ZIP archive.  The adapter can create the ZIP archive if it doesn't exist.

## Initialization Example

Here's an example of how to initialize the ZIP archive adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_zip_storage", {
    "type": "file_keeper:zip",
    "path": "/tmp/my_archive.zip",  # Replace with your desired ZIP archive path
    "create": True,  # Optional: Create the ZIP archive if it doesn't exist
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace `/tmp/my_archive.zip` with the desired path to your ZIP archive.
*   The `create` option (defaulting to `False`) determines whether the adapter should attempt to create the ZIP archive if it doesn't exist. If `create` is `True` and the ZIP archive cannot be created (e.g., due to permissions issues), an error will be raised.
*   This adapter is suitable for smaller files, as ZIP archives can become slow to process with a large number of files.
