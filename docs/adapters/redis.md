# Redis Adapter

The `file_keeper:redis` adapter allows you to use Redis as a storage
backend. This adapter stores files as binary data within Redis HASH.

## Overview

This adapter provides a simple way to integrate Redis with file-keeper. You'll
need to have a running Redis instance and the `redis` Python library installed.
This adapter is suitable for smaller files and scenarios where fast access is
critical.

```sh
pip install 'file-keeper[redis]'

## or

pip install redis
```


## Initialization Example

Here's an example of how to initialize the Redis adapter:

```python
storage = make_storage("my_redis_storage", {
    "type": "file_keeper:redis",
    "host": "redis://localhost:6379/0",
    "bucket": "file-keeper",
})
```

**Important Notes:**

*   Replace the placeholder values with your actual Redis configuration.
*   Ensure that your Redis instance is running and accessible.
*   Consider the limitations of storing large files in Redis, as it is an
    in-memory data store.
*   The `bucket` parameter is used as name of the Redis HASH key under which
    files will be stored.
