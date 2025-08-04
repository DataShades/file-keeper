# Error Handling

file-keeper provides a comprehensive set of exceptions to help you handle errors gracefully. This page documents the available exceptions and provides guidance on how to handle them.

## General Exception Hierarchy

All exceptions in file-keeper inherit from the base `FilesError` exception.  This allows you to catch all file-keeper related errors with a single `except` block.  More specific exceptions are derived from `FilesError` to provide more detailed error information.

## Specific Exceptions

### `FilesError`

*   **Description:** Base class for all file-keeper exceptions.
*   **When it's raised:**  Generally, you won't catch this directly. It's the parent class for more specific exceptions.
*   **How to handle:**  Catch more specific exceptions whenever possible.

### `StorageError`

*   **Description:** Base class for exceptions related to storage operations.
*   **When it's raised:**  When a general storage-related error occurs.
*   **How to handle:**  Catch more specific exceptions derived from `StorageError`.

### `UnknownStorageError`

*   **Description:** Raised when a storage with the specified name is not configured.
*   **When it's raised:**  When you try to use a storage that hasn't been registered.
*   **How to handle:**  Verify that the storage is configured correctly.

### `UnknownAdapterError`

*   **Description:** Raised when a specified storage adapter is not registered.
*   **When it's raised:**  When you try to use an adapter that isn't supported.
*   **How to handle:**  Check the adapter name and ensure it's valid.

### `UnsupportedOperationError`

*   **Description:** Raised when a requested operation is not supported by the storage.
*   **When it's raised:**  When you try to perform an operation that the storage doesn't support.
*   **How to handle:**  Check the storage's capabilities using `storage.supports()` before attempting the operation.

### `PermissionError`

*   **Description:** Raised when the storage client does not have the required permissions.
*   **When it's raised:**  When the storage client lacks the necessary permissions to perform an operation.
*   **How to handle:**  Verify that the storage client has the correct permissions.

### `LocationError`

*   **Description:** Raised when the storage cannot use the given location (e.g., invalid path).
*   **When it's raised:**  When the location is invalid or inaccessible.
*   **How to handle:**  Verify that the location is valid and accessible.

### `MissingFileError`

*   **Description:** Raised when a file does not exist.
*   **When it's raised:**  When you try to access a file that doesn't exist.
*   **How to handle:**  Check if the file exists before attempting to access it.

### `ExistingFileError`

*   **Description:** Raised when a file already exists and overwriting is not allowed.
*   **When it's raised:**  When you try to upload a file that already exists and `override_existing` is set to `False`.
*   **How to handle:**  Either set `override_existing` to `True` or choose a different location.

### `ExtrasError`

*   **Description:** Raised when incorrect extra parameters are passed to a storage method.
*   **When it's raised:**  When a required extra parameter is missing or invalid.
*   **How to handle:**  Verify that you are passing the correct extra parameters.

### `MissingExtrasError`

*   **Description:** Raised when a required extra parameter is missing.
*   **When it's raised:**  When a required extra parameter is not provided.
*   **How to handle:**  Provide the missing extra parameter.

### `InvalidStorageConfigurationError`

*   **Description:** Raised when the storage cannot be initialized with the given configuration.
*   **When it's raised:**  When the storage configuration is invalid.
*   **How to handle:**  Verify that the storage configuration is correct.

### `UploadError`

*   **Description:** Base class for exceptions related to file uploads.
*   **When it's raised:**  When a general upload-related error occurs.
*   **How to handle:**  Catch more specific exceptions derived from `UploadError`.

### `UploadOutOfBoundError`

*   **Description:** Raised when a multipart upload exceeds the expected size.
*   **When it's raised:**  When the uploaded data is larger than the expected size.
*   **How to handle:**  Verify that the upload size is correct.

### `UploadMismatchError`

*   **Description:** Raised when the expected value of a file attribute (e.g., content type, hash) does not match the actual value.
*   **When it's raised:**  When there is a mismatch between the expected and actual file attributes.
*   **How to handle:**  Verify that the file attributes are correct.

### `UploadTypeMismatchError`

*   **Description:** Raised when the expected content type does not match the actual content type.
*   **When it's raised:**  When the content type is incorrect.
*   **How to handle:**  Verify that the content type is correct.

### `UploadHashMismatchError`

*   **Description:** Raised when the expected hash does not match the actual hash.
*   **When it's raised:**  When the file hash is incorrect.
*   **How to handle:**  Verify that the file hash is correct.

### `UploadSizeMismatchError`

*   **Description:** Raised when the expected file size does not match the actual file size.
*   **When it's raised:**  When the file size is incorrect.
*   **How to handle:**  Verify that the file size is correct.

## Example Error Handling

```python
from file_keeper import make_storage, make_upload
from file_keeper.core import exceptions

try:
    storage = make_storage("my_storage", {"type": "file_keeper:fs", "path": "/nonexistent/path"})
    upload = make_upload(b"Hello, file-keeper!")
    storage.upload("my_file.txt", upload)
except exceptions.InvalidStorageConfigurationError as e:
    print(f"Error configuring storage: {e}")
except exceptions.MissingFileError as e:
    print(f"File not found: {e}")
except exceptions.StorageError as e:
    print(f"A general storage error occurred: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```
