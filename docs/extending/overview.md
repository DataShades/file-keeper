# Register file-keeper extension

file-keeper is designed to be highly extensible, allowing you to add new
storage backends, upload factories, and location transformers without modifying
the core library. This is achieved through the use of the
[Pluggy](https://pluggy.readthedocs.io/) framework.

## Overview

If you want to make your module that extends of file-keeper externally
available, register it as a `file_keeper_ext`
[entry-point](https://packaging.python.org/en/latest/specifications/entry-points/)
of your distribution.

/// tab | pyproject.toml

```toml
...

[project.entry-points.file_keeper_ext]
my_storage_extension = "my_storage.my_module"
```

///

/// tab | setup.py

```python
from setuptools import setup

setup(
    ...,
    entry_points={
        "file_keeper_ext": ["my_storage_extension = my_storage.my_module"],
    },
)
```

///

file-keeper iterates through all modules that are registered under
`file_keeper_ext` entry-point and extract [pluggy hook
implementations](https://pluggy.readthedocs.io/en/stable/#implementations) from
them. In this way, anyone who've installed your library will have access to
your customizations.

## Available extension points


The module that contains file-keeper's extension has to define functions that
register new functionality. These functions must have the same name as one of
file-keeper's hooks and be decorated with `@file_keeper.hookimpl` decorator.

The following hooks are currently available:

| Hook                             | Description                                                                                                                                                                          |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `register_adapters`              | Use this function to register new storage adapters. The `registry` object allows you to add your `Storage` class to the list of available storage options.                           |
| `register_location_transformers` | Use this function to register new location transformers. The `registry` object allows you to add your `LocationTransformer` function to the list of available location transformers. |
<!-- | `register_upload_factories`      | Use this function to register new upload factories. The `registry` object allows you to add your `UploadFactory` class to the list of available upload factories.                    | -->


/// admonition
    type: example

Register new storage adapter:

```py

@fk.hookimpl
def register_adapters(registry):
    registry.register("my_custom_adapter", MyStorageClass)
```

Register new location transformers:

```py

@fk.hookimpl
def register_location_transformers(registry):
    registry.register("my_custom_transformer", transformer_func)
```

///


### Example: registering a custom storage adapter

Let's say you want to add a new storage adapter that stores files in a local directory.  Here's how you would do it:

1. Create a new Python package (`my_storage_extension`)

2. Inside your package, create a module ( `my_storage.py`) with the following content:

    ```python
    import file_keeper as fk

    class MyLocalStorage(fk.Storage):
        ...

    @fk.hookimpl
    def register_adapters(registry):
        registry.register("my_local", MyLocalStorage)
    ```

3. Add an entry point to your `setup.py` or `pyproject.toml` file:

    /// tab | setup.py

    ```python
    from setuptools import setup

    setup(
        ...,
        entry_points={
            "file_keeper_ext": ["my_storage_extension = my_storage"],
        },
    )
    ```
    ///

    /// tab | pyproject.toml

   ```toml
   ...

   [project.entry-points.file_keeper_ext]
   my_storage_extension = "my_storage"
   ```
   ///

Now, when file-keeper discovers your extension, it will register
`MyLocalStorage` as a new storage option, accessible by the name "my\_local".

### Example: registering a custom location transformer

Let's say you want to add a location transformer that prepends a prefix to all locations.

1. Create a new Python package

2. Inside your package, create a file  with the following content:

    ```python
    import file_keeper as fk

    def my_location_transformer(location: str, upload, extras: dict[str, any]) -> str:
        return f"prefix_{location}"

    @fk.hookimpl
    def register_location_transformers(registry: Registry[types.LocationTransformer]):
        registry.register("my_prefix", my_location_transformer)
    ```

3. Add an entry point to your `setup.py` or `pyproject.toml` file


Now, when file-keeper discovers your extension, it will register a new location
transformer, accessible by the name "my\_prefix".

## Manual extension

Entry-points are good for python packages, but sometimes you need a custom
storage just for the current script and don't want to mess with packages. In
this case you can register adapter or location transformer manually, using
`file_keeper.core.storage.adapters` and `file_keeper.core.storage.location_transformers`
[Registries][file_keeper.Registry].

/// admonition
    type: example

Let's say you have `MyStorage` adapter and `my_transformer` transformer. In the
following snippet, they will be available after the `register()` calls in the
corresponding registries.

```py

from file_keeper.core.storage import location_transformers, adapters

# not available

adapters.register("my_storage", MyStorage)
location_transformers.register("my_transformer", my_transformer)

# available

storage = make_storage("test", {
    "type": "my_storage",
    "location_transformers": ["my_transformer"]
})

```

///
