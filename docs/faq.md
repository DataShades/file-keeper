# Frequently Asked Questions (FAQ)

Answers to common questions about file-keeper.

## General Questions

### What is file-keeper?

file-keeper is a Python library that provides a unified interface for storing, retrieving, and managing files across different storage backends. It supports local filesystem, cloud storage services (AWS S3, Google Cloud Storage, Azure), in-memory storage, and more.

### Why should I use file-keeper instead of directly using storage SDKs?

file-keeper provides several advantages:

1. **Unified API**: Same interface regardless of storage backend
2. **Easy migration**: Switch between storage systems without changing application code
3. **Built-in features**: Security protections, capability detection, error handling
4. **Extensibility**: Easy to add custom storage adapters
5. **Type safety**: Comprehensive type annotations

### Which storage backends are supported?

file-keeper supports many storage backends including:

- Local filesystem (`file_keeper:fs`)
- In-memory storage (`file_keeper:memory`)
- AWS S3 (`file_keeper:s3`)
- Google Cloud Storage (`file_keeper:gcs`)
- Azure Blob Storage (`file_keeper:azure_blob`)
- Redis (`file_keeper:redis`)
- SQL databases via SQLAlchemy (`file_keeper:sqlalchemy`)
- And many more!

## Configuration Questions

### How do I configure different storage backends?

Each storage backend has its own configuration options, but they all follow the same pattern:

```python
import file_keeper as fk

# File system storage
storage = fk.make_storage("fs", {
    "type": "file_keeper:fs",
    "path": "/path/to/storage",
    "initialize": True
})

# S3 storage
storage = fk.make_storage("s3", {
    "type": "file_keeper:s3",
    "bucket": "my-bucket",
    "key": "access-key",
    "secret": "secret-key"
})
```

### What are common configuration options?

All storage adapters share these common options:

- `type`: The adapter type (required)
- `name`: Identifier for the storage instance
- `path`: Base path/prefix for files
- `override_existing`: Whether to overwrite existing files
- `initialize`: Whether to create the storage container if it doesn't exist
- `location_transformers`: Functions to transform file locations

### How do I handle sensitive configuration like API keys?

Never hardcode credentials. Use environment variables or configuration management:

```python
import os
import file_keeper as fk

storage = fk.make_storage("s3", {
    "type": "file_keeper:s3",
    "bucket": "my-bucket",
    "key": os.getenv("AWS_ACCESS_KEY_ID"),
    "secret": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1")
})
```

## Usage Questions

### How do I upload a file?

```python
import file_keeper as fk

storage = fk.make_storage("memory", {"type": "file_keeper:memory"})
upload = fk.make_upload(b"Hello, world!")
file_info = storage.upload("hello.txt", upload)
```

### How do I check if a file exists?

```python
# Check if storage supports EXISTS capability first
if storage.supports(fk.Capability.EXISTS):
    exists = storage.exists(file_info)
    print(f"File exists: {exists}")
else:
    print("Existence check not supported by this storage")
```

### How do I handle errors properly?

```python
from file_keeper import exc

try:
    file_info = storage.upload("myfile.txt", upload)
    content = storage.content(file_info)
except exc.MissingFileError:
    print("File not found")
except exc.ExistingFileError:
    print("File already exists")
except exc.InvalidStorageConfigurationError as e:
    print(f"Storage configuration error: {e}")
except exc.FilesError as e:
    print(f"File operation failed: {e}")
```

### How do I work with large files without loading everything into memory?

`make_file` function can transform file descriptior(file opened with built-in
`open` function) into efficient streamable object. For other content generated
in real-time, use `IterableBytesReader`:

```python
from file_keeper import IterableBytesReader

def upload_large_file_in_chunks(storage, location, stream, file_size):
    stream = IterableBytesReader(stream)
    upload = fk.Upload(stream, location, file_size, "application/octet-stream")

    return storage.upload(location, upload)

def chunk_generator():
    yield b"hello"
    yield b" "
    yield b"world"

upload_large_file_in_chunks(
    make_storage(...),
    "big-file.txt",
    chunk_generator(),
    11,
)
```

## Performance Questions

### How can I optimize performance?

1. **Use appropriate storage for your use case**: Local filesystem for local access, CDN-backed storage for public files
2. **Enable compression** if supported by your storage backend
3. **Use streaming** for large files to avoid memory issues
4. **Cache frequently accessed files** in memory or a fast storage tier

### Does file-keeper support multipart uploads?

Yes, for storage backends that support it. Check for the `MULTIPART` capability:

```python
if storage.supports(fk.Capability.MULTIPART):
    # Use multipart upload
    upload_info = storage.multipart_start(location, file_size)
    # Upload parts...
    final_info = storage.multipart_complete(upload_info)
```

## Security Questions

### How does file-keeper protect against directory traversal attacks?

file-keeper validates file locations to ensure they don't escape the configured storage path:

```python
# This would raise a LocationError if it tries to go outside the storage path
file_info = storage.upload("../../etc/passwd", upload)
```

### How do I validate file types and sizes?

Validate before uploading:

```python
def safe_upload(storage, filename, upload, allowed_types, max_size):
    # Validate file type
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type not in allowed_types:
        raise ValueError(f"File type not allowed: {mime_type}")

    # Validate file size
    if upload.size > max_size:
        raise ValueError(f"File too large: {upload.size} bytes")

    # Sanitize filename
    import os
    safe_filename = os.path.basename(filename)

    return storage.upload(safe_filename, upload)
```

## Troubleshooting

### I'm getting "Unknown adapter" error, what should I do?

This usually means you're using an adapter type that isn't registered or available:

1. Check the spelling of the adapter type
2. Make sure required dependencies are installed (e.g., `pip install 'file-keeper[s3]'` for S3 support)
3. Verify the adapter name format: `file_keeper:adapter_name`
4. Check the list of available adapters:
   ```py
   import file_keeper as fk
   print(fk.list_adapters())
   ```

### My uploads are failing with connection errors

This could be due to:

1. Network connectivity issues
2. Incorrect credentials
3. Insufficient permissions
4. Rate limiting by the storage service

Implement retry logic:

```python
import time
from file_keeper import exc

def upload_with_retry(storage, location, upload, max_retries=3):
    for attempt in range(max_retries):
        try:
            return storage.upload(location, upload)
        except (exc.ConnectionError, exc.UploadError) as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
```

### How do I migrate from one storage backend to another?

Use the scan and copy functionality:

```python
def migrate_storage(source_storage, dest_storage):
    for location in source_storage.scan():
        file_info = source_storage.analyze(location)
        upload = source_storage.file_as_upload(file_info)
        dest_storage.upload(location, upload)
        print(f"Migrated: {location}")
```

## Development Questions

### How do I create a custom storage adapter?

Extend the Storage class and implement the required services:

```python
from file_keeper import Storage, Settings, Uploader, Manager, Reader
from file_keeper import Capability, FileData

class CustomSettings(Settings):
    api_key: str = ""
    endpoint: str = ""

class CustomUploader(Uploader):
    capabilities = Capability.CREATE

    def upload(self, location, upload, extras):
        # Implement upload logic
        pass

class CustomStorage(Storage):
    SettingsFactory = CustomSettings
    UploaderFactory = CustomUploader
    # Implement other services as needed
```

Then register your adapter:

```python
from file_keeper import adapters
adapters.register("file_keeper:custom", CustomStorage)
```
