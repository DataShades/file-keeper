# Storage adapters

The core of file-keeper's flexibility lies in its storage adapters. Adapters
encapsulate the logic for interacting with a specific storage system, allowing
file-keeper to remain agnostic to the underlying implementation.  To create a
custom adapter, you'll need to define a class that inherits from
[Storage][file_keeper.Storage] and implements its services.

## Steps to create a custom adapter

### Define a Settings class

Create a dataclass to hold the configuration options for your storage
adapter. This class should inherit from [Settings][file_keeper.Settings].  This
allows file-keeper to handle validation and default values.

/// admonition
    type: example

```py
from dataclasses import dataclass
import file_keeper as fk

@dataclass
class MyStorageSettings(fk.Settings):
    api_key: str = ""
    endpoint: str = ""
```
///

### Implement the [Storage][file_keeper.Storage] class

Create a class that inherits from [Storage][file_keeper.Storage] and sets the
[SettingsFactory][file_keeper.Storage.SettingsFactory] class attribute to your settings
class. It also sets [UploaderFactory][file_keeper.Storage.UploaderFactory] and
[ReaderFactory][file_keeper.Storage.ReaderFactory] in the same way. The
implementation will follow soon.

/// admonition
    type: example

```python
...

class MyStorage(fk.Storage):
    settings: MyStorageSettings

    SettingsFactory = MyStorageSettings
    UploaderFactory = MyUploader
    ReaderFactory = MyReader
```
///

### Implement [Uploader][file_keeper.Uploader] and [Reader][file_keeper.Reader] services

Create classes for `Uploader` and `Reader` that inherit from
[Uploader][file_keeper.Uploader] and [Reader][file_keeper.Reader]
respectively. These classes will contain the logic for uploading and reading
files to and from your storage system.

Make sure to add [CREATE][file_keeper.Capability.CREATE] capability to
`Uploader` and [STREAM][file_keeper.Capability.STREAM] capability to
`Reader`. Otherwise storage will pretend that these services do not support these operations

/// admonition
    type: example

```python

class MyUploader(fk.Uploader):

    capabilities = fk.Capability.CREATE

    def upload(self, location: fk.Location, upload: fk.Upload, extras: dict[str, Any]) -> fk.FileData:
        # Implement your upload logic here
        reader = upload.hashing_reader()
        for chunk in reader:
            # send fragment to storage

        return fk.FileData(location, upload.size, upload.content_type, reader.get_hash())


class MyReader(fk.Reader):

    capabilities = fk.Capability.STREAM

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        # Implement your streaming logic here
        for chunk in file_stream:
            yield chunk
```
///

### Register the adapter

If you are going to use custom adapter only inside a single script, you can
register it directly using `adapters` registry:


```python
fk.adapters.register("local", MyStorage)
```

But if you are writing a library that will be used accross multiple project
it's better to register storage using entrypoints of the python package.

First, create a function with name `register_adapters` and decorate it with
`hookimpl` decorator. This function is responsible to register the adapter

```py
@fk.hookimpl
def register_adapters(registry: fk.Registry[type[fk.Storage]]):
    registry.register("local", MyStorage)
```

Next, add an entry-point named `file_keeper_ext` pointing to the module with
`register_adapters` to you package's definition. For example, if you are using
`pyproject.toml` add following lines there:

```toml
[project.entry-points."file_keeper_ext"]
my_extension = "my_module.my_storage"

```

Finally, re-install the your package, to refresh entrypoints. From now on your
custom adapter will be available just as any adapter shipped inside file-keeper
as soon as you install your library.

### Initialize the adapter

Now you can use your custom adapter:

```python
storage = fk.make_storage("local", {
    "adapter": "local",
    "api_key": "123",
    "endpoint": "https://example.local",
})
```

This is a basic example, but it demonstrates the fundamental principles of
creating a custom storage adapter.  You can extend this example to support more
complex features and integrate with a wider range of storage systems.
