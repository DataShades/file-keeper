# Configuration

Behavior of every storage is configurable through the
[Settings][file_keeper.Settings] class. This page details the available
settings and how to use them to customize your storage setup.

## The [Settings][file_keeper.Settings] Class

The [Settings][file_keeper.Settings] class is the central point for configuring each storage
adapter. It defines the options that control how the adapter interacts with the
underlying storage.  Each adapter has its own subclass of [Settings][file_keeper.Settings] that adds
adapter-specific options.

While you *can* directly instantiate a [Settings][file_keeper.Settings]
subclass with its arguments, the most common approach is to pass a dictionary
of options to the storage adapter constructor. file-keeper automatically
handles the transformation of this dictionary into a
[Settings][file_keeper.Settings] object. This provides a more flexible and
user-friendly configuration experience.

/// admonition
    type: example

Let's say you want to configure the S3 adapter. Instead of creating a
[Settings][file_keeper.Settings] object directly, you can simply pass a
dictionary like this:

```python
from file_keeper import make_storage

s3_settings = {
    "type": "file_keeper:s3",
    "bucket": "my-s3-bucket",
    "key": "YOUR_AWS_ACCESS_KEY_ID",
    "secret": "YOUR_AWS_SECRET_ACCESS_KEY",
    "region": "us-east-1",
}

storage = make_storage("my_s3_storage", s3_settings)

# Accessing the settings (for demonstration)
print(storage.settings.bucket) # (1)!
```

1. Output: my-s3-bucket

In this example, `make_storage` automatically creates a `Settings` object from
the `s3_settings` dictionary.
///

**How it Works:**

1.  You provide a dictionary containing the configuration options for the
    storage adapter.
2.  file-keeper's [make_storage][file_keeper.make_storage] function (or the
    adapter's constructor directly) uses the
    [SettingsFactory][file_keeper.Storage.SettingsFactory] associated with the
    adapter to create a [Settings][file_keeper.Settings] object from the
    dictionary.
3.  The [Settings.from_dict()][file_keeper.Settings.from_dict] method handles the conversion, including
    validation and handling of any unexpected options.  Any unrecognized
    options are stored in the `_extra_settings` attribute for later use if
    needed.


**Benefits of using a dictionary:**

*   **Flexibility:** Easily pass configuration options from environment
    variables, configuration files, or other sources.
*   **Readability:** Dictionaries are often more concise and easier to read
    than creating `Settings` objects directly.
*   **Extensibility:** Allows you to pass custom options that are not
    explicitly defined in the `Settings` class.

## Common Settings

These settings are available for most storage adapters:


| Setting                 | Type      | Default     | Description                                                                                                                                                                                                                                        |
|-------------------------|-----------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name`                  | str       | `"unknown"` | Descriptive name of the storage used for debugging.                                                                                                                                                                                                |
| `override_existing`     | bool      | `False`     | If `True`, existing files will be overwritten during upload. If `False`, an `ExistingFileError` will be raised if a file with the same location already exists.                                                                                    |
| `path`                  | str       | `""`        | The base path or directory where files are stored. The exact meaning depends on the adapter (e.g., a path in the filesystem for the FS adapter, a prefix-path inside the bucket for S3).  Required for most adapters.                              |
| `location_transformers` | list[str] | `[]`        | A list of names of location transformers to apply to file locations. These transformers can be used to sanitize or modify file paths before they are used to store files. See the [Extending file-keeper documentation](extending.md) for details. |
| `disabled_capabilities` | list[str] | `[]`        | A list of capabilities to disable for the storage adapter. This can be useful for limiting the functionality of an adapter or for testing purposes.                                                                                                |
| `initialize`            | bool      | `False`     | Prepare storage backend for uploads. The exact meaning depends on the adapter. Filesystem adapter created the upload folder if it's missing; cloud adapters create a bucket/container if it does not exists.                                       |

## Adapter-Specific Settings

In addition to the common settings, each adapter has its own specific
settings:

TODO

```sh
 docker run -p 9000:9000 -p 9001:9001 --name minio -e MINIO_PUBLIC_ADDRESS=0.0.0.0:9000 quay.io/minio/minio server /data --console-address ":9001"

docker run -p 10000:10000 --name azurite-blob mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0

docker run -d --name gcs -p 4443:4443 fsouza/fake-gcs-server -scheme http

```
```sh
 docker run -p 9000:9000 -p 9001:9001 --name minio -e MINIO_PUBLIC_ADDRESS=0.0.0.0:9000 quay.io/minio/minio server /data --console-address ":9001"

docker run -p 10000:10000 --name azurite-blob mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0

docker run -d --name gcs -p 4443:4443 fsouza/fake-gcs-server -scheme http

```


### `file_keeper:fs`
| option | description |
|--------|-------------|
|        |             |

/// admonition
    type: example

```py
storage = make_storage("sandbox", {
    "type": "file_keeper:fs",
    "path": "/tmp/file-keeper",
    "initialize": True,
})
```
///

### `file_keeper:null`
### `file_keeper:memory`
### `file_keeper:zip`

### `file_keeper:redis`
/// admonition
    type: example

```py
storage = make_storage("sandbox", {
    "type": "file_keeper:redis",
    "bucket": "file-keeper"
})
```
///
### `file_keeper:opendal`
### `file_keeper:libcloud`

/// admonition
    type: example

```py
storage = make_storage("sandbox", {
    "type": "file_keeper:libcloud",
    "provider": "MINIO",
    "params": {"host": "127.0.0.1", "port": 9000, "secure": False},
    "key": "***", "secret": "***",
    "container_name": "file-keeper",
})
```
///

### `file_keeper:gcs`
### `file_keeper:s3`
/// admonition
    type: example

```py
storage = make_storage("sandbox", {
    "type": "file_keeper:s3",
    "endpoint": "http://127.0.0.1:9000",
    "key": "***", "secret": "***",
    "bucket": "file-keeper",
})
```
///

### `file_keeper:filebin`
### `file_keeper:sqlalchemy`
### `file_keeper:azure_blob`
### `file_keeper:proxy`


## Important Considerations

*   **Security:**  Be careful when storing sensitive information like AWS access keys and secret keys in your configuration.  Consider using environment variables or a secure configuration management system.
*   **Validation:**  file-keeper performs some basic validation of the configuration settings, but it's important to ensure that your settings are correct for your specific storage adapter.
*   **Error Handling:**  Be prepared to handle `InvalidStorageConfigurationError` exceptions if your configuration is invalid.
