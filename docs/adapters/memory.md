# In-Memory Storage Adapter

The `file_keeper:memory` adapter provides a simple in-memory storage solution. This adapter is primarily intended for testing and development purposes, as data is not persisted to disk.

## Overview

This adapter stores files entirely in memory, making it very fast but also volatile. Data is lost when the application exits. It's a convenient way to simulate a storage backend without requiring external dependencies.

## Initialization Example

Here's an example of how to initialize the in-memory storage adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_memory_storage", {
    "type": "file_keeper:memory",
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   No configuration options are required for this adapter.
*   All data is stored in memory and will be lost when the application terminates.
*   This adapter is not suitable for production environments where data persistence is required.
