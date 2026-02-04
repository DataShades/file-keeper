# Getting Started

This tutorial will walk you through the basics of using file-keeper to manage files across different storage backends. By the end of this tutorial, you'll understand how to:

- Install and set up file-keeper
- Configure different storage backends
- Perform basic file operations
- Handle errors gracefully
- Choose the right storage for your needs

## Installation

First, install file-keeper using pip:

```bash
pip install file-keeper
```

For specific storage backends, you may need additional dependencies:

```bash
# For S3 support
pip install 'file-keeper[s3]'

# For all optional dependencies
pip install 'file-keeper[all]'
```

## Basic Setup

Let's start with a simple example using in-memory storage for testing:

```python
import file_keeper as fk

# Create an in-memory storage for testing
storage = fk.make_storage("test_storage", {
    "type": "file_keeper:memory"
})

# Create an upload object from data
upload = fk.make_upload(b"Hello, file-keeper!")

# Upload the file
file_info = storage.upload("hello.txt", upload)

print(f"File uploaded: {file_info.location}")
print(f"File size: {file_info.size} bytes")
```

## Using File System Storage

For production use, you'll likely want to use file system storage:

```python
import tempfile
import file_keeper as fk

# Create a temporary directory for our example
with tempfile.TemporaryDirectory() as tmpdir:
    # Create file system storage
    fs_storage = fk.make_storage("fs_example", {
        "type": "file_keeper:fs",
        "path": tmpdir,
        "initialize": True  # Create directory if it doesn't exist
    })

    # Upload a file
    upload = fk.make_upload(b"Sample file content")
    file_info = fs_storage.upload("sample.txt", upload)

    print(f"File saved at: {fs_storage.full_path(file_info.location)}")

    # Read the file content back
    content = fs_storage.content(file_info)
    print(f"Content: {content.decode('utf-8')}")
```

## Working with Different Storage Types

file-keeper supports many storage backends. Here are examples of common ones:

### Memory Storage (for testing)
```python
import file_keeper as fk

memory_storage = fk.make_storage("test", {
    "type": "file_keeper:memory"
})
```

### File System Storage (for local files)
```python
fs_storage = fk.make_storage("local", {
    "type": "file_keeper:fs",
    "path": "/path/to/storage",
    "initialize": True
})
```

### Checking Capabilities

Different storage backends support different operations. Always check capabilities before performing operations:

```python
import file_keeper as fk

storage = fk.make_storage("example", {
    "type": "file_keeper:memory"
})

# Check if storage supports removing files
if storage.supports(fk.Capability.REMOVE):
    # Safe to call remove
    storage.remove(file_info)
else:
    print("Remove operation not supported by this storage")
```

## Error Handling

Always handle potential errors when working with file storage:

```python
import file_keeper as fk
from file_keeper import exc

storage = fk.make_storage("safe_storage", {
    "type": "file_keeper:memory"
})

try:
    upload = fk.make_upload(b"Test content")
    file_info = storage.upload("test.txt", upload)

    # Try to read the content
    content = storage.content(file_info)
    print(f"Successfully read: {content.decode()}")

except exc.FilesError as e:
    print(f"File operation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Complete Example Application

Here's a complete example of a simple file management application:

```python
import file_keeper as fk
from file_keeper import exc
import tempfile

class FileManager:
    def __init__(self, storage_config):
        self.storage = fk.make_storage("manager", storage_config)

    def save_file(self, filename, content):
        """Save content to a file."""
        try:
            upload = fk.make_upload(content.encode() if isinstance(content, str) else content)
            file_info = self.storage.upload(filename, upload)
            return file_info
        except exc.FilesError as e:
            print(f"Failed to save file {filename}: {e}")
            return None

    def load_file(self, file_info):
        """Load content from a file."""
        try:
            if self.storage.supports(fk.Capability.STREAM):
                return self.storage.content(file_info)
        except exc.MissingFileError:
            print(f"File not found: {file_info.location}")
            return None
        except exc.FilesError as e:
            print(f"Failed to load file {file_info.location}: {e}")
            return None

    def delete_file(self, file_info):
        """Delete a file."""
        if self.storage.supports(fk.Capability.REMOVE):
            try:
                return self.storage.remove(file_info)
            except exc.FilesError as e:
                print(f"Failed to delete file {file_info.location}: {e}")
                return False
        else:
            print("Delete operation not supported")
            return False

# Example usage
with tempfile.TemporaryDirectory() as tmpdir:
    # Initialize the file manager with file system storage
    fm = FileManager({
        "type": "file_keeper:fs",
        "path": tmpdir,
        "initialize": True
    })

    # Save a file
    file_info = fm.save_file("example.txt", "Hello, file-keeper!")
    if file_info:
        print(f"File saved: {file_info.location}")

        # Load the file
        content = fm.load_file(file_info)
        if content:
            print(f"File content: {content.decode()}")
```

## Next Steps

Now that you've learned the basics, you can:

- Learn about advanced features in the [Core Concepts](../core_concepts/index.md) section
- Check out the [API Reference](../api.md) for detailed information about all functions
- Look at the [Configuration](../configuration.md) guide for advanced setup options

In the next tutorial, we'll cover more advanced topics like custom adapters and performance optimization.
