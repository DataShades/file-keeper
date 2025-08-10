# Apache Libcloud Adapter

The `file_keeper:libcloud` adapter allows you to use Apache Libcloud to connect to a wide range of cloud storage providers. Libcloud provides a unified interface for interacting with various storage services, simplifying integration and reducing vendor lock-in.

## Overview

This adapter leverages the Libcloud library to provide storage functionality. You'll need to have Libcloud installed (`pip install apache-libcloud`) and configure it with the appropriate credentials for your chosen provider.

## Initialization Example

Here's an example of how to initialize the Libcloud adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_libcloud_storage", {
    "type": "file_keeper:libcloud",
    "provider": "MINIO",  # Replace with your provider (e.g., AWS, Azure, Google Cloud)
    "params": {
        "host": "127.0.0.1",  # Replace with your provider's host
        "port": 9000,          # Replace with your provider's port
        "secure": False,       # Set to True for HTTPS
    },
    "key": "YOUR_ACCESS_KEY",  # Replace with your access key
    "secret": "YOUR_SECRET_KEY",  # Replace with your secret key
    "container_name": "file-keeper",  # Replace with your container/bucket name
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace the placeholder values (provider, host, port, secure, key, secret, container\_name) with your actual provider credentials and configuration.
*   Refer to the [Apache Libcloud documentation](https://libcloud.readthedocs.io/) for a complete list of supported providers and their specific configuration options.
*   Ensure that the necessary Libcloud drivers are installed for your chosen provider.
