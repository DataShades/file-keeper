# Null Adapter

The `file_keeper:null` adapter provides a no-op storage solution. It does not actually store any files and is primarily intended for testing or situations where you want to disable storage functionality.

## Overview

This adapter implements all the required storage interfaces but performs no real operations. Any attempt to upload, download, or manage files will be silently ignored. It's a useful tool for isolating issues or running tests without interacting with external storage.

## Initialization Example

Here's an example of how to initialize the null adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_null_storage", {
    "type": "file_keeper:null",
})

# Now you can use the 'storage' object, but all operations will be no-ops.
```

**Important Notes:**

*   No configuration options are required for this adapter.
*   All operations are silently ignored.
*   This adapter is not suitable for production environments where data persistence is required.
