# Filebin Adapter

The `file_keeper:filebin` adapter allows you to use Filebin for storing and retrieving files. Filebin is a simple, self-hosted file storage service. This adapter leverages the `filebin` Python library.

## Overview

This adapter provides a convenient way to integrate Filebin with file-keeper. You'll need to have the `filebin` library installed (`pip install filebin`) and a running Filebin instance.

## Initialization Example

Here's an example of how to initialize the Filebin adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_filebin_storage", {
    "type": "file_keeper:filebin",
    "url": "http://your_filebin_instance:8000",  # Replace with your Filebin instance URL
    "api_key": "YOUR_API_KEY",  # Replace with your Filebin API key
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace the placeholder values (url, api\_key) with your actual Filebin instance URL and API key.
*   Ensure that your Filebin instance is running and accessible.
*   Refer to the [Filebin documentation](https://filebin.readthedocs.io/) for more information about Filebin.
