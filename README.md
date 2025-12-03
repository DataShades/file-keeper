[![Tests](https://github.com/DataShades/file-keeper/actions/workflows/test.yml/badge.svg)](https://github.com/DataShades/file-keeper/actions/workflows/test.yml)

# file-keeper

Abstraction layer for reading, writing and managing file-like objects.

The package implements drivers for a number of storage types(local filesystem,
redis, AWS S3, etc.) and defines a set of tools to simplify building your own
drivers for storage you are using.

Read the [documentation](https://datashades.github.io/file-keeper/) for a full
user guide.

## Features

- **Unified API**: Consistent interface across multiple storage backends
- **Multiple Storage Backends**: Support for file system, memory, S3, GCS, Azure, Redis, and more
- **Type Safety**: Comprehensive type annotations for better development experience
- **Security**: Built-in protection against directory traversal and other attacks
- **Extensible**: Plugin architecture for adding custom storage adapters
- **Comprehensive Testing**: Extensive test coverage with security-focused tests

## API Overview

### Creating Storage

Use `make_storage()` to create storage instances:

```python
import file_keeper as fk

# Create memory storage for testing
storage = fk.make_storage("sandbox", {"type": "file_keeper:memory"})

# Create filesystem storage
storage = fk.make_storage("fs", {
    "type": "file_keeper:fs",
    "path": "/path/to/files",
    "initialize": True
})
```

### File Operations

```python
# Upload a file
upload = fk.make_upload(b"file content")
result = storage.upload("filename.txt", upload)

# Read file content
content = storage.content(result)

# Check if file exists
exists = storage.exists(result)

# Remove file
removed = storage.remove(result)
```

### Key Functions

- `make_storage(name, settings)`: Create a storage instance
- `make_upload(data)`: Create an upload object from data
- `get_storage(name, settings=None)`: Get or create a named storage instance from the pool

## Usage

Initialize storage pointing to `/tmp/example` folder:

```python
import os
from file_keeper import make_storage

storage = make_storage("sandbox", {
    "type": "file_keeper:fs",
    "path": "/tmp/example",
    # this option creates the folder if it does not exist.
    # Without it storage raises an error if folder is missing
    "initialize": True,
})
assert os.path.isdir("/tmp/example")
```

Upload file into the storage initialized in the previous step and play with it
a bit:

```python
from file_keeper import make_upload
upload = make_upload(b"hello world")

# save the data and verify its presence in the system
result = storage.upload("hello.txt", upload)
assert result.size == 11
assert os.path.isfile("/tmp/example/hello.txt")

# change location of the file
moved_result = storage.move("moved-hello.txt", result, storage)
assert not os.path.exists("/tmp/example/hello.txt")
assert os.path.isfile("/tmp/example/moved-hello.txt")

# read the file
assert storage.content(moved_result) == b"hello world"

# remove the file
storage.remove(moved_result)
assert not os.path.exists("/tmp/example/moved-hello.txt")
```

## Development

Install `dev` extras:

```sh
pip install -e '.[dev]'
```

Run unittests:
```sh
pytest
```

Run typecheck:
```sh
pyright
```


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
