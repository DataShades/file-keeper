# Apache Libcloud Adapter

The `file_keeper:libcloud` adapter allows you to use [Apache
Libcloud](https://libcloud.apache.org/) to connect to a wide range of cloud
[storage
providers](https://libcloud.readthedocs.io/en/stable/supported_providers.html). Libcloud
provides a unified interface for interacting with various storage services,
simplifying integration and reducing vendor lock-in.

## Overview

This adapter leverages the Libcloud library to provide storage
functionality. You'll need to have Libcloud installed and configure it with the
appropriate credentials for your chosen provider.

```sh
pip install 'file-keeper[libcloud]'

## or

pip install apache-libcloud
```

## Initialization Example

Here's an example of how to initialize the Libcloud adapter:


/// tab | AWS S3

```py
storage = make_storage("my_libcloud_storage", {
    "type": "file_keeper:libcloud",
    "provider": "S3",
    "key": "***",
    "secret": "***",
    "container_name": "file-keeper",
    "initialize": True,
})

```

///

/// tab | MinIO

```python

storage = make_storage("my_libcloud_storage", {
    "type": "file_keeper:libcloud",
    "provider": "MINIO",
    "key": "minioadmin",
    "secret": "minioadmin",
    "container_name": "file-keeper",
    "initialize": True,
    "params": {
        "host": "127.0.0.1",
        "port": 9000,
        "secure": False,
    },
})
```

///

/// tab | Azurite

```python

storage = make_storage("my_libcloud_storage", {
    "type": "file_keeper:libcloud",
    "provider": "AZURE_BLOBS",
    "key": "devstoreaccount1",
    "secret": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
    "container_name": "file-keeper",
    "initialize": True,
    "params": {
        "host": "127.0.0.1",
        "port": 10000,
        "secure": False,
    },
})
```
///


**Important Notes:**

*   Replace the placeholder values (provider, host, port, secure, key, secret,
    container\_name) with your actual provider credentials and configuration.
*   Refer to the [Apache Libcloud
    documentation](https://libcloud.readthedocs.io/) for a complete list of
    supported providers and their specific configuration options.
*   Ensure that the necessary Libcloud drivers are installed for your chosen
    provider.
