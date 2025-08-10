# Extending file-keeper

file-keeper is designed to be highly extensible, allowing you to add new
storage backends, upload factories, and location transformers without modifying
the core library. This is achieved through the use of the
[Pluggy](https://pluggy.readthedocs.io/) framework.

## Overview

file-keeper uses `pluggy` to discover and register extensions. To extend File
Keeper's capabilities, you need to create a Python package that provides entry
points for the `file_keeper_ext` hook specification.  Within your extension
package, you can define functions decorated with `@file_keeper.hookimpl` to
override or augment existing functionality.

## Available extension points

The following extension points are currently available:

### `register_adapters(registry: Registry[type[storage.Storage]])`

Use this function to register new storage adapters. The `registry` object
allows you to add your `Storage` class to the list of available storage
options.

### `register_upload_factories(registry: Registry[upload.UploadFactory, type])`

Use this function to register new upload factories. The `registry` object
allows you to add your `UploadFactory` class to the list of available upload
factories.

###  `register_location_transformers(registry: Registry[types.LocationTransformer])`

Use this function to register new location transformers. The `registry` object
allows you to add your `LocationTransformer` function to the list of available
location transformers.


## Example: registering a custom storage adapter

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

    === "setup.py"

         ```python
         from setuptools import setup

         setup(
             name="my_storage_extension",
             # ... other setup details ...
             entry_points={
                 "file_keeper_ext": ["my_storage_extension = my_storage"],
             },
         )
         ```

    === "pyproject.toml"

        ```toml
        [project]
        name = "my_storage_extension"
        # ... other project details ...

        [project.entry-points.file_keeper_ext]
        my_storage_extension = "my_storage"
        ```

Now, when file-keeper discovers your extension, it will register
`MyLocalStorage` as a new storage option, accessible by the name "my\_local".

## Example: registering a custom location transformer

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
