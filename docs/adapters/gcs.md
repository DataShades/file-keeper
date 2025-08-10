# Google Cloud Storage

The `file_keeper:gcs` adapter allows you to use Google Cloud Storage for storing and retrieving files. This adapter leverages the `google-cloud-storage` Python library.

## Overview

This adapter provides a convenient way to integrate Google Cloud Storage with File Keeper. You'll need to have the `google-cloud-storage` library installed (`pip install google-cloud-storage`) and configure it with the appropriate credentials for your Google Cloud project.

## Initialization Example

Here's an example of how to initialize the Google Cloud Storage adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_gcs_storage", {
    "type": "file_keeper:gcs",
    "project": "your-gcp-project-id",  # Replace with your Google Cloud project ID
    "bucket_name": "your-gcs-bucket-name",  # Replace with your GCS bucket name
    "credentials_path": "/path/to/your/credentials.json",  # Replace with the path to your service account key file
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace the placeholder values (project, bucket\_name, credentials\_path) with your actual Google Cloud project ID, GCS bucket name, and the path to your service account key file.
*   Ensure that you have created a bucket in your Google Cloud Storage account to store the files.
*   For enhanced security, it's recommended to use a service account with limited permissions.
*   Refer to the [Google Cloud Storage documentation](https://cloud.google.com/storage/docs) for more information about Google Cloud Storage.
