# Apache OpenDAL

The `file_keeper:opendal` adapter allows you to use [Apache
OpenDAL](https://opendal.apache.org/) for storing and retrieving files. OpenDAL
provides a unified interface for interacting with various object storage
systems and local filesystems.

## Overview

This adapter leverages the OpenDAL library to provide storage
functionality. You'll need to have OpenDAL installed and configure it with the
appropriate credentials and configuration for your chosen storage provider.

```sh
pip install 'file-keeper[opendal]'

## or

pip install opendal
```


## Initialization Example

Here's an example of how to initialize the OpenDAL adapter:


/// tab | MinIO

```py
storage = make_storage("my_opendal_storage", {
     "type": "file_keeper:opendal",
     "scheme": "s3",
     "params": {
         "bucket": "file-keeper",
         "access_key_id": "minioadmin",
         "secret_access_key": "minioadmin",
         "endpoint": "http://127.0.0.1:9000",
         "region": "auto"
     },
 })
```

///

/// tab | Azurite

```python

storage = make_storage("my_opendal_storage", {
     "type": "file_keeper:opendal",
     "scheme": "azblob",
     "params": {
         "container": "file-keeper",
         "account_name": "devstoreaccount1",
         "account_key": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
         "endpoint": "http://127.0.0.1:10000/devstoreaccount1",
     },
 })

```

///

/// tab | Fake GCS

```python

storage = make_storage("my_opendal_storage", {
     "type": "file_keeper:opendal",
     "scheme": "gcs",
     "params": {
         "bucket": "file-keeper",
         "endpoint": "http://127.0.0.1:4443",
     },
 })

```

///


**Important Notes:**

*   Replace the params with your actual OpenDAL location and credentials.
*   Refer to the [Apache OpenDAL
    documentation](https://opendal.readthedocs.io/) for a complete list of
    supported storage systems and their specific configuration options.
*   Ensure that you have the necessary credentials and permissions to access
    the specified storage location.
