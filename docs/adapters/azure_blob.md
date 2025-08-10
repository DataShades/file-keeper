# Azure Blob Storage

The `file_keeper:azure_blob` adapter allows you to use Microsoft Azure Blob Storage for storing and retrieving files. This adapter leverages the `azure-storage-blob` Python library.

## Overview

This adapter provides a convenient way to integrate Azure Blob Storage with File Keeper. You'll need to have the `azure-storage-blob` library installed (`pip install azure-storage-blob`) and configure it with the appropriate credentials for your Azure account.

## Initialization Example

Here's an example of how to initialize the Azure Blob Storage adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_azure_storage", {
    "type": "file_keeper:azure_blob",
    "account_name": "your_account_name",  # Replace with your Azure account name
    "account_key": "your_account_key",  # Replace with your Azure account key
    "container_name": "file-keeper-container",  # Replace with your container name
    "endpoint": "https://your_account_name.blob.core.windows.net/", # Optional: Specify the endpoint
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace the placeholder values (account\_name, account\_key, container\_name, endpoint) with your actual Azure account credentials and configuration.
*   Ensure that you have created a container in your Azure Blob Storage account to store the files.
*   For enhanced security, consider using Azure Active Directory (Azure AD) authentication instead of account keys.  Refer to the `azure-storage-blob` documentation for details on Azure AD authentication.
*   Refer to the [Azure Blob Storage documentation](https://learn.microsoft.com/en-us/azure/storage/blobs/index) for more information about Azure Blob Storage.
