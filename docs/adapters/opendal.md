# Apache OpenDAL

The `file_keeper:opendal` adapter allows you to use Apache OpenDAL for storing and retrieving files. OpenDAL provides a unified interface for interacting with various object storage systems and local filesystems.

## Overview

This adapter leverages the OpenDAL library to provide storage functionality. You'll need to have OpenDAL installed (`pip install opendal`) and configure it with the appropriate credentials and configuration for your chosen storage provider.

## Initialization Example

Here's an example of how to initialize the OpenDAL adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_opendal_storage", {
    "type": "file_keeper:opendal",
    "location": "s3://your-s3-bucket",  # Replace with your OpenDAL location (e.g., s3://bucket, azure://container, file://path)
    "access_key": "YOUR_ACCESS_KEY",  # Replace with your access key (if required)
    "secret_key": "YOUR_SECRET_KEY",  # Replace with your secret key (if required)
    "endpoint": "https://your-s3-endpoint", # Optional: Specify the endpoint
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace the placeholder values (location, access\_key, secret\_key, endpoint) with your actual OpenDAL location and credentials.
*   Refer to the [Apache OpenDAL documentation](https://opendal.readthedocs.io/) for a complete list of supported storage systems and their specific configuration options.
*   Ensure that you have the necessary credentials and permissions to access the specified storage location.
