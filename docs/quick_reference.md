# Quick Reference

Common file-keeper operations at a glance.

## Installation

```bash
pip install file-keeper
# With specific adapter support
pip install 'file-keeper[s3]'  # for S3
pip install 'file-keeper[all]'  # for all adapters
```

## Basic Usage

```python
import file_keeper as fk

# Create storage
storage = fk.make_storage("my_storage", {
    "type": "file_keeper:memory"  # or :fs, :s3, etc.
})

# Upload a file
upload = fk.make_upload(b"file content")
file_info = storage.upload("filename.txt", upload)

# Read file content
content = storage.content(file_info)

# Check capabilities
if storage.supports(fk.Capability.REMOVE):
    storage.remove(file_info)
```

## Common Operations

| Operation | Method | Capability Required |
|-----------|--------|-------------------|
| Upload file | `storage.upload(location, upload)` | `CREATE` |
| Read content | `storage.content(file_data)` | `STREAM` |
| Stream content | `storage.stream(file_data)` | `STREAM` |
| Check existence | `storage.exists(file_data)` | `EXISTS` |
| Remove file | `storage.remove(file_data)` | `REMOVE` |
| Copy file | `storage.copy(new_location, file_data)` | `COPY` |
| Move file | `storage.move(new_location, file_data)` | `MOVE` |
| Get file info | `storage.analyze(location)` | `ANALYZE` |
| List files | `storage.scan()` | `SCAN` |

## Error Handling

```python
from file_keeper import exc

try:
    # file operations
    pass
except exc.MissingFileError:
    # File doesn't exist
    pass
except exc.ExistingFileError:
    # File already exists
    pass
except exc.FilesError as e:
    # Other file-keeper errors
    pass
```

## Common Configurations

### File System Storage
```python
{
    "type": "file_keeper:fs",
    "path": "/path/to/storage",
    "initialize": True,
    "override_existing": False
}
```

### S3 Storage
```python
{
    "type": "file_keeper:s3",
    "bucket": "my-bucket",
    "key": "access-key",
    "secret": "secret-key",
    "region": "us-east-1"
}
```

### Memory Storage (for testing)
```python
{
    "type": "file_keeper:memory"
}
```

## Capability Checks

```python
# Single capability
if storage.supports(fk.Capability.CREATE):
    # Can create files

# Multiple capabilities
if storage.supports(fk.Capability.CREATE | fk.Capability.REMOVE):
    # Can create and remove files

# Check for read capabilities
read_capable = storage.supports(fk.Capability.STREAM | fk.Capability.ANALYZE)
```

## Working with Uploads

```python
# From bytes
upload = fk.make_upload(b"content")

# From file
with open("file.txt", "rb") as f:
    upload = fk.make_upload(f)
    # make sure to upload the file before with-block ends
    ...

# Manual upload (for streaming)
upload = fk.Upload(stream, location, size, content_type)
```

## File Information

The `FileData` object contains:

- `location`: Where the file is stored
- `size`: Size in bytes
- `content_type`: MIME type
- `hash`: Content hash
- `storage_data`: Backend-specific metadata
