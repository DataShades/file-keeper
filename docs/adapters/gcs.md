# Google Cloud Storage

The `file_keeper:gcs` adapter allows you to use [Google Cloud
Storage](https://cloud.google.com/storage?hl=uk) for storing and retrieving
files. This adapter leverages the `google-cloud-storage` Python library.

## Overview

This adapter provides a convenient way to integrate Google Cloud Storage with
file-keeper. You'll need to have the `google-cloud-storage` library installed
and configure it with the appropriate credentials for your Google Cloud
project.


```sh
pip install 'file-keeper[gcs]'

## or

pip install google-cloud-storage
```

## Initialization Example

Here's an example of how to initialize the Google Cloud Storage adapter:

/// tab | Google Cloud Storage

```python
storage = make_storage("my_gcs_storage", {
    "type": "file_keeper:gcs",
    "project_id": "file-keeper",  # Replace with your Google Cloud project ID
    "bucket_name": "file-keeper",
    "initialize": True,
    "credentials_file": "/path/to/your/credentials.json",  # Replace with the path to your service account key file
})
```

///

/// tab | Fake GCS

```python
storage = make_storage("my_gcs_storage", {
    "type": "file_keeper:gcs",
    "project_id": "file-keeper",
    "bucket_name": "file-keeper",
    "initialize": True,
    "client_options": {"api_endpoint": "http://127.0.0.1:4443"},
})
```
///


**Important Notes:**

*   Replace the placeholder values with your actual Google Cloud project ID,
    GCS bucket name, and the path to your service account key file.
*   Ensure that you have created a bucket in your Google Cloud Storage account
    to store the files.
*   For enhanced security, it's recommended to use a service account with
    limited permissions.
*   Refer to the [Google Cloud Storage
    documentation](https://cloud.google.com/storage/docs) for more information
    about Google Cloud Storage.
