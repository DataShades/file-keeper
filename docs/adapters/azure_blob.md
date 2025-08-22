# Azure Blob Storage

The `file_keeper:azure_blob` adapter allows you to use [Microsoft Azure Blob
Storage](https://azure.microsoft.com/en-us/products/storage/blobs) for storing
and retrieving files. This adapter leverages the `azure-storage-blob` Python
library.

## Overview

This adapter provides a convenient way to integrate Azure Blob Storage with
file-keeper. You'll need to have the `azure-storage-blob` library installed and
configure it with the appropriate credentials for your Azure account.

```sh
pip install 'file-keeper[azure]'

## or

pip install azure-storage-blob
```


## Initialization

/// details | Flow

```mermaid
graph TB
    subgraph a [Client initialization]
        direction TB
        has_client -->|Yes| set_url_and_name
        has_client -->|No| has_account_name
        has_account_name -->|Yes| initialize_client
        has_account_name -->|No| has_account_key
        has_account_key -->|Yes| initialize_client
        has_account_key -->|No| initialize_client
        initialize_client --> set_url_and_name
    end
    a --> b
    subgraph b [Container initialization]
        direction TB

        has_container -->|Yes| set_container_name
        has_container -->|No| initialize_container
        initialize_container --> set_container_name
    end
    b --> c
    subgraph c [Container creation]
        direction TB

        container_exists -->|Yes| done
        container_exists -->|No| has_initialize_flag
        has_initialize_flag -->|Yes| create_container
        has_initialize_flag -->|No| fail
        create_container --> done
    end

    has_client{**client** specified?}
    has_account_name{**account_name** specified?}
    has_account_key{**account_key** specified?}
    set_url_and_name[**account_url** and **account_name** from the **client** object are added to settings]
    has_container{**container** specified?}
    has_initialize_flag{**initialize** enabled?}
    initialize_client[**client** initialized using **account_url** and available credentials]
    initialize_container[**container** reference created]
    set_container_name[**container_name** from the **container** is added to settings]
    create_container[real **contaner** created in cloud]
    container_exists{real **container** exists in cloud?}
    done([Storage initialized])
    fail([Exception raised])
```

///

Here's an example of how to initialize the Azure Blob Storage adapter:



/// tab | Azure Blob Storage

```py
storage = make_storage("my_azure_storage", {
    "type": "file_keeper:azure_blob",
    "account_name": "***",
    "account_key": "***",
    "container_name": "file-keeper",
    "initialize": True,
})

```

///

/// tab | Azurite

```python
storage = make_storage("my_azure_storage", {
    "type": "file_keeper:azure_blob",
    "account_name": "devstoreaccount1",
    "account_key": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
    "container_name": "file-keeper",
    "initialize": True,
    "account_url": "http://127.0.0.1:10000/{account_name}",
})

```

///

## Important Notes

*   Replace the placeholder values with your actual Azure account credentials
    and configuration.
*   Ensure that you have created a container in your Azure Blob Storage account
    to store the files.
*   For enhanced security, consider using Azure Active Directory (Azure AD)
    authentication instead of account keys.  Refer to the `azure-storage-blob`
    documentation for details on Azure AD authentication.
*   Refer to the [Azure Blob Storage
    documentation](https://learn.microsoft.com/en-us/azure/storage/blobs/index)
    for more information about Azure Blob Storage.
