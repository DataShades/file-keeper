# Welcome to file-keeper

file-keeper provides an abstraction layer for storing and retrieving files,
supporting various storage backends like local filesystems, cloud storage (S3,
GCS), and more. It simplifies file management by providing a consistent API
regardless of the underlying storage.

## Getting Started

If you're new to file-keeper, start with our [Getting Started Tutorial](tutorials/getting_started.md) which covers installation, basic configuration, and fundamental operations.

## Key Features

- **Unified API**: Consistent interface across multiple storage backends
- **Multiple Storage Backends**: Support for file system, memory, S3, GCS, Azure, Redis, and more
- **Type Safety**: Comprehensive type annotations for better development experience
- **Security**: Built-in protection against directory traversal and other attacks
- **Extensible**: Plugin architecture for adding custom storage adapters
- **Comprehensive Testing**: Extensive test coverage with security-focused tests

## Installation

You can install file-keeper using pip:

```sh
pip install file-keeper
```

/// details | Additional dependencies

To use specific storage adapters, you may need to install extra
dependencies. Most standard adapters do *not* require extras, but some – like
those interfacing with external cloud providers – do. Here's a table of
available extras:

| Storage Type         | Adapter Name             | Extras       | Driver                                                                 |
|----------------------|--------------------------|--------------|------------------------------------------------------------------------|
| AWS S3               | `file_keeper:s3`         | `s3`         | [boto3](https://pypi.org/project/boto3/)                               |
| Apache Libcloud      | `file_keeper:libcloud`   | `libcloud`   | [apache-libcloud](https://pypi.org/project/apache-libcloud/)           |
| Apache OpenDAL       | `file_keeper:opendal`    | `opendal`    | [opendal](https://pypi.org/project/opendal/)                           |
| Azure Blob Storage   | `file_keeper:azure_blob` | `azure`      | [azure-storage-blob](https://pypi.org/project/azure-storage-blob/)     |
| Google Cloud Storage | `file_keeper:gcs`        | `gcs`        | [google-cloud-storage](https://pypi.org/project/google-cloud-storage/) |
| Redis                | `file_keeper:redis`      | `redis`      | [redis](https://pypi.org/project/redis/)                               |
| SQLAlchemy           | `file_keeper:sqlalchemy` | `sqlalchemy` | [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)                     |



For example, to install file-keeper with S3 support:

```bash
pip install 'file-keeper[s3]'
```

And if you are not sure which storage backend you will use, you can install all
extras:
```bash
pip install 'file-keeper[all]'
```

///

## Basic configuration and usage (FS adapter)

/// admonition
    type: example
```python
from file_keeper import make_storage, make_upload

# Create a storage instance.  The 'path' setting specifies the root directory
# for storing files. 'initialize' will automatically create the directory
# if it doesn't exist.
storage = make_storage(
    "my_fs_storage",  # A name for your storage (for logging/debugging)
    {
        "type": "file_keeper:fs",
        "path": "/tmp/my_filekeeper_files",
        "initialize": True,
    },
)

# Create an upload object from a byte string.
upload = make_upload(b"Hello, file-keeper!")

# Upload the file.  This returns a FileData object containing information
# about the uploaded file.
file_data = storage.upload("my_file.txt", upload)

# Print the file data.
print(file_data)

# The file is now stored in /tmp/my_filekeeper_files/my_file.txt

# Get the content of file using corresponding FileData object
content: bytes = storage.content(file_data)
```
///
**Explanation:**

*   `make_storage()`: Creates a storage instance with the specified configuration.
*   `make_upload()`: Creates an `Upload` object from the data you want to store.
*   `storage.upload()`: Uploads the data to the storage.
*   `FileData`:  A dataclass that contains metadata about the uploaded file, including its location, size, content type, and hash.
*   `storage.content()`: Locates file using `FileData` and returns byte string with its content

## Documentation Structure

This documentation is organized to help you find what you need:

- **[Tutorials](tutorials/getting_started.md)**: Step-by-step guides for beginners
- **[Core Concepts](core_concepts/index.md)**: Understanding the fundamental ideas
- **[Reference](api.md)**: Technical reference materials
- **[Storage Adapters](adapters/fs.md)**: Specific information for each storage backend
