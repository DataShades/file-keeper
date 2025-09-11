# Fsspec

The `file_keeper:fsspec` adapter uses the
[fsspec](https://filesystem-spec.readthedocs.io/en/latest/index.html) library
to provide access to a wide range of storage backends supported by `fsspec`
(e.g., local filesystems, cloud storage like S3, GCS, Azure Blob Storage, and
more). The core idea is to use `fsspec`'s unified interface to interact with
these different storage systems.

## Overview

```sh
pip install 'file-keeper[fsspec]'

## or

pip install fsspec
```


## Initialization Example

Here's an example of how to initialize the fsspec adapter:


/// tab | Memory

```py
storage = make_storage("my_fsspec_storage", {
     "type": "file_keeper:fsspec",
     "protocol": "memory",
})
```

///

/// tab | Local FS

```python

storage = make_storage("my_fsspec_storage", {
     "type": "file_keeper:fsspec",
     "protocol": "local",
     "path": "/tmp/file-keeper",
     "params": {"auto_mkdir": True}
})

```

///



**Important Notes:**

*   Replace the params with your actual fsspec configuration
*   Ensure that you have the necessary credentials and permissions to access
    the specified storage location.
