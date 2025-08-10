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

## Example error handling

```python
from file_keeper import make_storage, make_upload, exc

try:
    storage = make_storage("my_storage", {"type": "file_keeper:fs", "path": "/nonexistent/path"})
except exc.InvalidStorageConfigurationError as e:
    print(f"Error configuring storage: {e}")

upload = make_upload(b"Hello, file-keeper!")

try:
    storage.upload("my_file.txt", upload)
except exc.ExistingFileError as e:
    print(f"File already exists: {e}")

```

::: file_keeper.exc
    options:
        show_source: false
        show_signature: true
        merge_init_into_class: true
