# Location transformers

Location transformers allow you to modify the [Location][file_keeper.Location]
string before it's used to access a file in the storage backend. This is useful
for scenarios where you need to perform additional processing or formatting on
the location, such as adding prefixes, encoding characters, or generating
unique identifiers.

## What are location transformers?

A location transformer is a callable (usually a function) that takes the
original [Location][file_keeper.Location] string, optional
[Upload][file_keeper.Upload], and any extra data as input, and returns a
modified [Location][file_keeper.Location] string. They provide a flexible way
to customize how locations are handled by file-keeper.

Location transformers are set per-storage via
[location_transformers][file_keeper.Settings.location_transformers] option. To
apply them call [prepare_location()][file_keeper.Storage.prepare_location]
method.

/// admonition
    type: example

```py

storage = make_storage("test", {
    "type": "file_keeper:fs",
    "location_transformers": ["safe_relative_path"],
    "path": "/tmp",
})

unsafe_location = "../etc/passwd"

safe_location = storage.prepare_location(unsafe_location)

storage.upload(safe_location, ...)

```
///

## Steps to create a custom location transformer

### Define your transformer

Create a function that accepts the [Location][file_keeper.Location], optional
[Upload][file_keeper.Upload], and `extras` as input and returns the transformed
[Location][file_keeper.Location].

```python
def my_location_transformer(location, upload_or_none, extras):
    # Perform custom transformation here
    return "prefix_" + location
```

### Register the transformer

Use the `register_location_transformers` hook to register your
transformer. This makes it available for use when creating or accessing files.

```python
import file_keeper as fk

@fk.hookimpl
def register_location_transformers(registry):
    registry.register("my_transformer", my_location_transformer)
```

## Using Your Custom Transformer

To use your custom transformer, specify its name when creating a `Storage` object in the settings.

```python

storage = make_storage("my_storage", {
    "adapter": "s3",
    "location_transformers": ["my_transformer"],
})
```

And apply `Storage.prepare_location` to original location:

```python
transformed = storage.prepare_location("hello.txt")

assert transformed == "prefix_hello.txt"

```
