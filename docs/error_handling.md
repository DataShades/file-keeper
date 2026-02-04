# Error handling

file-keeper provides a comprehensive set of exceptions to help you handle
errors gracefully. This page documents the available exceptions and provides
guidance on how to handle them.

## General exception hierarchy

All exceptions in file-keeper inherit from the base
[`FilesError`][file_keeper.exc.FilesError] exception.  This allows you to catch
all file-keeper related errors with a single `except` block.  More specific
exceptions are derived from [FilesError][file_keeper.exc.FilesError] to
provide more detailed error information.


/// note

file-keeper's exceptions can be imported from `file_keeper.core.exceptions`

```py
from file_keeper.core.exceptions import FilesError

try:
    ...
except FilesError:
    ...
```

As a shortcut, they can be accessed from the `exc` object available at the root
of file-keeper module

```py
from file_keeper import exc

try:
    ...
except exc.FilesError:
    ...

```

///

## Common Error Scenarios and Solutions

### Storage Configuration Errors

When creating a storage instance, configuration errors are common:

```python
from file_keeper import make_storage, exc

try:
    storage = make_storage("my_storage", {
        "type": "file_keeper:fs", 
        "path": "/nonexistent/path",
        "initialize": False  # This will cause an error if path doesn't exist
    })
except exc.InvalidStorageConfigurationError as e:
    print(f"Storage configuration error: {e}")
    # Solution: Set initialize=True or ensure the path exists
    storage = make_storage("my_storage", {
        "type": "file_keeper:fs", 
        "path": "/tmp/my_files",
        "initialize": True
    })

# Unknown adapter type
try:
    storage = make_storage("bad_storage", {"type": "unknown:adapter"})
except exc.UnknownAdapterError as e:
    print(f"Unknown adapter: {e}")
    # Solution: Check available adapters or register a custom one
```

### File Operation Errors

Common errors during file operations:

```python
from file_keeper import make_storage, make_upload, exc

storage = make_storage("memory", {"type": "file_keeper:memory"})
upload = make_upload(b"Hello, file-keeper!")

# Upload a file
file_info = storage.upload("test.txt", upload)

# Handle file not found
try:
    content = storage.content(file_info)
except exc.MissingFileError as e:
    print(f"File not found: {e}")
    # Handle missing file appropriately

# Handle existing file when override is disabled
try:
    storage.upload("test.txt", make_upload(b"New content"))
except exc.ExistingFileError as e:
    print(f"File already exists: {e}")
    # Either enable override_existing in settings or handle differently

# Check capabilities before operations
if storage.supports(exc.Capability.REMOVE):
    storage.remove(file_info)
else:
    print("Remove operation not supported by this storage")
```

### Network and External Service Errors

For cloud storage adapters:

```python
from file_keeper import exc

try:
    # This might fail due to network issues or service unavailability
    storage.upload("remote_file.txt", upload)
except exc.UploadError as e:
    print(f"Upload failed: {e}")
    # Implement retry logic or fallback mechanism
except exc.ConnectionError as e:
    print(f"Connection error: {e}")
    # Check network connectivity or service availability
```

## Best Practices for Error Handling

### 1. Check Capabilities Before Operations

```python
from file_keeper import Capability

# Check if operation is supported before attempting it
if storage.supports(Capability.REMOVE):
    storage.remove(file_info)
else:
    # Handle unsupported operation gracefully
    print("Remove operation not supported")
```

### 2. Implement Retry Logic for Transient Errors

```python
import time
from file_keeper import exc

def upload_with_retry(storage, location, upload, max_retries=3):
    for attempt in range(max_retries):
        try:
            return storage.upload(location, upload)
        except (exc.ConnectionError, exc.UploadError) as e:
            if attempt == max_retries - 1:  # Last attempt
                raise e
            print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
            time.sleep(2 ** attempt)  # Exponential backoff
```

### 3. Graceful Degradation

```python
from file_keeper import Capability, exc

def get_file_content_safe(storage, file_info):
    """Get file content with graceful degradation."""
    try:
        # Try to get content directly
        return storage.content(file_info)
    except exc.MissingFileError:
        print("File not found")
        return None
    except exc.UnsupportedOperationError:
        # If content() is not supported, try streaming
        if storage.supports(Capability.STREAM):
            return b"".join(storage.stream(file_info))
        else:
            print("No way to retrieve file content")
            return None
    except exc.FilesError as e:
        print(f"Unexpected error: {e}")
        return None
```

### 4. Proper Resource Cleanup

```python
from file_keeper import exc

def process_file_with_cleanup(storage, upload_data):
    """Process a file and ensure cleanup on failure."""
    file_info = None
    try:
        file_info = storage.upload("temp_file.txt", upload_data)
        
        # Process the file
        content = storage.content(file_info)
        processed_content = content.upper()  # Example processing
        
        # Save processed file
        processed_info = storage.upload("processed_file.txt", make_upload(processed_content))
        
        return processed_info
    except exc.FilesError as e:
        print(f"Processing failed: {e}")
        # Clean up temporary file if it was created
        if file_info and storage.supports(Capability.REMOVE):
            try:
                storage.remove(file_info)
            except exc.FilesError:
                pass  # Ignore cleanup errors
        raise  # Re-raise the original error
```

## Exception Reference

::: file_keeper.exc
    options:
        show_source: false
        show_signature: true
        merge_init_into_class: true