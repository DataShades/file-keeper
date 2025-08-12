# ZIP Archive Adapter

The `file_keeper:zip` adapter allows you to use a ZIP archive as a storage
backend. This adapter is useful for packaging and distributing files in a
single archive.

## Overview

This adapter stores files within a ZIP archive. You'll need to provide the path
to the ZIP archive.  The adapter can create the ZIP archive if it doesn't
exist.

## Initialization Example

Here's an example of how to initialize the ZIP archive adapter:

```python
storage = make_storage("my_zip_storage", {
    "type": "file_keeper:zip",
    "path": "/tmp/my_archive.zip",
})
```

**Important Notes:**

*   Replace `/tmp/my_archive.zip` with the desired path to your ZIP archive.
*   This adapter is suitable for smaller files, as ZIP archives can become slow
    to process with a large number of files.
