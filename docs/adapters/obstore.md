# Object Store

The `file_keeper:obstore` adapter uses the
[obstore](https://developmentseed.org/obstore/latest/) library to provide
access to various object storage backends. It supports any backend supported by
obstore, including local filesystem, S3, Google Cloud Storage, Azure Blob
Storage, and more.

## Overview

```sh
pip install 'file-keeper[obstore]'

## or

pip install obstore
```


## Initialization Example

Here's an example of how to initialize the obstore adapter:


/// tab | Memory

```py
storage = make_storage("my_fsspec_storage", {
     "type": "file_keeper:obstore",
     "url": "memory:///",
})
```

///

/// tab | Local FS

```python

storage = make_storage("my_fsspec_storage", {
     "type": "file_keeper:obstore",
     "url": "file:///tmp/file-keeper",
})

```

///



**Important Notes:**

*   Replace the params with your actual obstore configuration
