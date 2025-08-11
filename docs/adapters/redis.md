# Redis Adapter

The `file_keeper:redis` adapter allows you to use Redis as a storage backend. This adapter stores files as binary data within Redis keys.

## Overview

This adapter provides a simple way to integrate Redis with file-keeper. You'll need to have a running Redis instance and the `redis` Python library installed (`pip install redis`).  This adapter is suitable for smaller files and scenarios where fast access is critical.

## Initialization Example

Here's an example of how to initialize the Redis adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_redis_storage", {
    "type": "file_keeper:redis",
    "host": "localhost",  # Replace with your Redis host
    "port": 6379,          # Replace with your Redis port
    "db": 0,               # Replace with your Redis database number
    "password": "",        # Replace with your Redis password (if any)
    "bucket": "file-keeper",  # Replace with your desired bucket name
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace the placeholder values (host, port, db, password, bucket) with your actual Redis configuration.
*   Ensure that your Redis instance is running and accessible.
*   Consider the limitations of storing large files in Redis, as it is an in-memory data store.
*   The `bucket` parameter is used as a prefix for all keys in Redis, helping to organize your files.
