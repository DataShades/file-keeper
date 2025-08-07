# Configuration

Behavior of every storage is configurable through the `Settings` class. This
page details the available settings and how to use them to customize your
storage setup.

## The `Settings` Class

The `Settings` class is the central point for configuring each storage
adapter. It defines the options that control how the adapter interacts with the
underlying storage.  Each adapter has its own subclass of `Settings` that adds
adapter-specific options.

While you *can* directly instantiate a `Settings` subclass with its arguments,
the most common approach is to pass a dictionary of options to the storage
adapter constructor. file-keeper automatically handles the transformation of
this dictionary into a `Settings` object. This provides a more flexible and
user-friendly configuration experience.

**How it Works:**

1.  You provide a dictionary containing the configuration options for the
    storage adapter.
2.  file-keeper's `make_storage` function (or the adapter's constructor
    directly) uses the `SettingsFactory` associated with the adapter to create
    a `Settings` object from the dictionary.
3.  The `SettingsFactory.from_dict()` method handles the conversion, including
    validation and handling of any unexpected options.  Any unrecognized
    options are stored in the `_extra_settings` attribute for later use if
    needed.

**Example:**

Let's say you want to configure the S3 adapter. Instead of creating a
`Settings` object directly, you can simply pass a dictionary like this:

```python
from file_keeper import make_storage

s3_settings = {
    "type": "file_keeper:s3",
    "bucket": "my-s3-bucket",
    "key": "YOUR_AWS_ACCESS_KEY_ID",
    "secret": "YOUR_AWS_SECRET_ACCESS_KEY",
    "region": "us-east-1",
    "extra_option": "some_value",  # This will be stored in _extra_settings
}

storage = make_storage("my_s3_storage", s3_settings)

# Accessing the settings (for demonstration)
print(storage.settings.bucket)  # Output: my-s3-bucket
print(storage.settings._extra_settings.get("extra_option"))  # Output: some_value
```

In this example, `make_storage` automatically creates a `Settings` object from
the `s3_settings` dictionary.  The `extra_option` is stored in the
`_extra_settings` dictionary, allowing you to access it if needed.

**Benefits of using a dictionary:**

*   **Flexibility:** Easily pass configuration options from environment
    variables, configuration files, or other sources.
*   **Readability:** Dictionaries are often more concise and easier to read
    than creating `Settings` objects directly.
*   **Extensibility:** Allows you to pass custom options that are not
    explicitly defined in the `Settings` class.

## Common Settings

These settings are available for most storage adapters:

*   **`override_existing` (bool, default: `False`):** If `True`, existing files
    will be overwritten during upload. If `False` (the default), an
    `ExistingFileError` will be raised if a file with the same location already
    exists.
*   **`path` (str, required for most adapters):** The base path or directory
    where files are stored.  The exact meaning of this setting depends on the
    adapter (e.g., a path in the filesystem for the FS adapter, a prefix-path
    inside the bucket for S3).
*   **`location_transformers` (list[str], default: `[]`):** A list of names of
    location transformers to apply to file locations.  These transformers can
    be used to sanitize or modify file paths before they are used to store
    files.  See the [Extending file-keeper documentation](extending.md) for
    details on creating custom location transformers.
*   **`disabled_capabilities` (list[str], default: `[]`):** A list of
    capabilities to disable for the storage adapter. This can be useful for
    limiting the functionality of an adapter or for testing purposes.

## Adapter-Specific Settings

In addition to the common settings, each adapter has its own specific
settings:

### `file_keeper:fs`

*   **`initialize` (bool, default: `False`):** If `True`, the `path` directory
    will be created if it doesn't exist. If `False`, an
    `InvalidStorageConfigurationError` will be raised if the `path` directory
    doesn't exist.

### `file_keeper:libcloud`

*   **`container_name` (str, required):** The name of the cloud container to use.
*   **`key` (str):** The access key.
*   **`secret` (str):** The secret access key.
*   **`provider` (str):** apache-libcloud storage provider.
*   **`params` (str):** JSON object with additional parameters passed directly to storage constructor.

### `file_keeper:s3`

*   **`bucket` (str):** The name of the S3 bucket to use.
*   **`key` (str):** The AWS access key ID.  If not provided, the AWS
    credentials will be loaded from the environment or the AWS configuration
    file.
*   **`secret` (str):** The AWS secret access key.  If not provided, the AWS
    credentials will be loaded from the environment or the AWS configuration
    file.
*   **`region` (str):** The AWS region to use.  If not provided, the AWS
    credentials will be used to determine the region.
*   **`endpoint` (str):** The S3 endpoint URL.  This can be used to connect to
    a custom S3-compatible storage service.

### GCS Adapter

*   **`bucket` (str):** The name of the GCS bucket to use.
*   **`credentials_file` (str):** The path to the Google Cloud service account credentials file. If not provided, the credentials will be loaded from the environment.

## Configuration Examples

Here are some examples of how to configure different storage adapters:

**FS Adapter:**

```python
settings = {
    "type": "file_keeper:fs",
    "path": "/tmp/my_files",
    "initialize": True,
}
```

**S3 Adapter:**

```python
settings = {
    "type": "file_keeper:s3",
    "bucket": "my-s3-bucket",
    "key": "YOUR_AWS_ACCESS_KEY_ID",
    "secret": "YOUR_AWS_SECRET_ACCESS_KEY",
    "region": "us-east-1",
}
```

**GCS Adapter:**

```python
settings = {
    "type": "file_keeper:gcs",
    "bucket": "my-gcs-bucket",
    "credentials_file": "/path/to/your/credentials.json",
}
```

## Using `Settings.from_dict()`

The `Settings.from_dict()` method provides a convenient way to create a `Settings` object from a dictionary. It also handles validation and provides a way to pass in extra settings that are not defined in the `Settings` class.

```python
from file_keeper.default.adapters.fs import Settings

settings_data = {
    "path": "/tmp/my_files",
    "initialize": True,
    "extra_setting": "some_value",  # This will be stored in settings._extra_settings
}

settings = Settings.from_dict(settings_data)

print(settings.path)  # Output: /tmp/my_files
print(settings._extra_settings["extra_setting"])  # Output: some_value
```

## Important Considerations

*   **Security:**  Be careful when storing sensitive information like AWS access keys and secret keys in your configuration.  Consider using environment variables or a secure configuration management system.
*   **Validation:**  file-keeper performs some basic validation of the configuration settings, but it's important to ensure that your settings are correct for your specific storage adapter.
*   **Error Handling:**  Be prepared to handle `InvalidStorageConfigurationError` exceptions if your configuration is invalid.
