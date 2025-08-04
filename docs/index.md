# Getting started

file-keeper provides an abstraction layer for storing and retrieving files,
supporting various storage backends like local filesystems, cloud storage (S3,
GCS), and more.  It simplifies file management by providing a consistent API
regardless of the underlying storage.

## Installation

You can install file-keeper using pip:

```sh
pip install file-keeper
```

To use specific storage adapters, you'll need to install extra
dependencies. Here's a table of available extras:

| Storage Type         | Adapter Name             | Extras       |
|----------------------|--------------------------|--------------|
| AWS S3               | `file_keeper:s3`         | `s3`         |
| Apache Libcloud      | `file_keeper:libcloud`   | `libcloud`   |
| Apache OpenDAL       | `file_keeper:opendal`    | `opendal`    |
| Google Cloud Storage | `file_keeper:gcs`        | `gcs`        |
| Redis                | `file_keeper:redis`      | `redis`      |
| SQLAlchemy           | `file_keeper:sqlalchemy` | `sqlalchemy` |

For example, to install file-keeper with S3 support:

```bash
pip install 'file-keeper[s3]'
```

## Basic configuration and usage (FS adapter)

Let's start with a simple example using the local filesystem (FS) adapter.

```python
from file_keeper import make_storage, make_upload

# Create a storage instance.  The 'path' setting specifies the root directory
# for storing files. 'create_path' will automatically create the directory
# if it doesn't exist.
storage = make_storage(
    "my_fs_storage",  # A name for your storage (for logging/debugging)
    {
        "type": "file_keeper:fs",
        "path": "/tmp/my_filekeeper_files",
        "create_path": True,
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
```

**Explanation:**

*   `make_storage()`: Creates a storage instance with the specified configuration.
*   `make_upload()`: Creates an `Upload` object from the data you want to store.
*   `storage.upload()`: Uploads the data to the storage.
*   `FileData`:  A dataclass that contains metadata about the uploaded file, including its location, size, content type, and hash.

## Next Steps

This is just a basic example to get you started.  For more detailed information, see the following documentation pages:

*   [Configuration](configuration.md): Learn about all the available settings and how to configure different storage adapters.
*   [Storage Adapters](adapters.md):  Explore the different storage adapters supported by file-keeper.
