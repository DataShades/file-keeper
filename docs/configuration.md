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

## Common Settings

These settings are available for most storage adapters:

| Setting                 | Type      | Default     | Description                                                                                                                                                                                                                                                              |
|-------------------------|-----------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name`                  | str       | `"unknown"` | Descriptive name of the storage used for debugging.                                                                                                                                                                                                                      |
| `override_existing`     | bool      | `False`     | If `True`, existing files will be overwritten during upload. If `False`, an `ExistingFileError` will be raised if a file with the same location already exists.                                                                                                          |
| `path`                  | str       | `""`        | The base path or directory where files are stored. The exact meaning depends on the adapter (e.g., a path in the filesystem for the FS adapter, a prefix-path inside the bucket for S3).  Required for most adapters.                                                    |
| `location_transformers` | list[str] | `[]`        | A list of names of location transformers to apply to file locations. These transformers can be used to sanitize or modify file paths before they are used to store files. See the [Extending file-keeper documentation](extending/location_transformers.md) for details. |
| `disabled_capabilities` | list[str] | `[]`        | A list of capabilities to disable for the storage adapter. This can be useful for limiting the functionality of an adapter or for testing purposes.                                                                                                                      |
| `initialize`            | bool      | `False`     | Prepare storage backend for uploads. The exact meaning depends on the adapter. Filesystem adapter created the upload folder if it's missing; cloud adapters create a bucket/container if it does not exists.                                                             |


/// warning | Important Considerations

|                    |                                                                                                                                                                                              |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Security**       | Be careful when storing sensitive information like AWS access keys and secret keys in your configuration.  Consider using environment variables or a secure configuration management system. |
| **Validation**     | file-keeper performs some basic validation of the configuration settings, but it's important to ensure that your settings are correct for your specific storage adapter.                     |
| **Error Handling** | Be prepared to handle `InvalidStorageConfigurationError` exceptions if your configuration is invalid.                                                                                        |

///

## Adapter-Specific Settings

In addition to the common settings, adapters have their own specific settings. Certain options are interchangeable


### `file_keeper:azure_blob`

| Setting          | Type                                                               | Default                                          | Description                                   |
|------------------|--------------------------------------------------------------------|--------------------------------------------------|-----------------------------------------------|
| `account_name`   | str                                                                | `""`                                             | Name of the account.                          |
| `account_key`    | str                                                                | `""`                                             | Key for the account.                          |
| `container_name` | str                                                                | `""`                                             | Name of the storage container.                |
| `account_url`    | str                                                                | `"https://{account_name}.blob.core.windows.net"` | Custom resource URL.                          |
| `client`         | BlobServiceClient { title="azure.storage.blob.BlobServiceClient" } | `None`                                           | Existing storage client.                      |
| `container`      | ContainerClient { title="azure.storage.blob.ContainerClient" }     | `None`                                           | Existing container client.                    |
| `path`           | str                                                                | `""`                                             | Prefix for the file location.                 |
| `initialize`     | bool                                                               | `False`                                          | Create `container_name` if it does not exist. |

### `file_keeper:fs`

| Setting      | Type | Default | Description                                |
|--------------|------|---------|--------------------------------------------|
| `path`       | str  | `""`    | The base directory where files are stored. |
| `initialize` | bool | `False` | Create `path` if it does not exist.        |

### `file_keeper:gcs`

| Setting            | Type                                                        | Default | Description                                     |
|--------------------|-------------------------------------------------------------|---------|-------------------------------------------------|
| `bucket_name`      | str                                                         | `""`    | Name of the storage bucket.                     |
| `client`           | Client { title="google.cloud.storage.Client" }              | `None`  | Existing storage client.                        |
| `bucket`           | Bucket { title="google.cloud.storage.Bucket" }              | `None`  | Existing storage bucket.                        |
| `credentials`      | Credentials { title="google.auth.credentials.Credentials" } | `None`  | Existing cloud credentials.                     |
| `credentials_file` | str                                                         | `""`    | Path to the JSON with cloud credentials.        |
| `project_id`       | str                                                         | `""`    | The project which the client acts on behalf of. |
| `client_options`   | dict                                                        | `None`  | Client options for storage client.              |
| `path`             | str                                                         | `""`    | Prefix for the file location.                   |
| `initialize`       | bool                                                        | `False` | Create `bucket_name` if it does not exist.      |

### `file_keeper:libcloud`

| Setting          | Type                                                          | Default | Description                                                                                                                               |
|------------------|---------------------------------------------------------------|---------|-------------------------------------------------------------------------------------------------------------------------------------------|
| `provider`       | str                                                           | `""`    | Name of the [Libcloud provider][libcloud providers]                                                                                       |
| `key`            | str                                                           | `""`    | Access key of the cloud account.                                                                                                          |
| `secret`         | str or None                                                   | `None`  | Secret key of the cloud account.                                                                                                          |
| `params`         | dict                                                          | `{}`    | Additional parameters for cloud provider.                                                                                                 |
| `container_name` | str                                                           | `""`    | Name of the cloud container.                                                                                                              |
| `public_prefix`  | str                                                           | `""`    | Root URL for containers with public access. This URL will be used as a prefix for the file object location when building permanent links. |
| `driver`         | StorageDriver { title="libcloud.storage.base.StorageDriver" } | `None`  | Existing storage driver.                                                                                                                  |
| `container`      | Container { title="libcloud.storage.base.Container" }         | `None`  | Existing container object.                                                                                                                |
| `path`           | str                                                           | `""`    | Prefix for the file location.                                                                                                             |
| `initialize`     | bool                                                          | `False` | Create `container_name` if it does not exist.                                                                                             |

[libcloud providers]: https://libcloud.readthedocs.io/en/stable/supported_providers.html

### `file_keeper:memory`

| Setting  | Type                       | Default | Description                     |
|----------|----------------------------|---------|---------------------------------|
| `bucket` | MutableMapping[str, bytes] | `{}`    | Container for uploaded objects. |

### `file_keeper:null`

No specific settings

### `file_keeper:opendal`

| Setting    | Type             | Default | Description                                     |
|------------|------------------|---------|-------------------------------------------------|
| `operator` | opendal.Operator | `None`  | Existing [OpenDAL operator][opendal operators]  |
| `scheme`   | str              | `""`    | Name of OpenDAL operator's scheme.              |
| `params`   | dict             | `{}`    | Parameters for OpenDAL operator initialization. |
| `path`     | str              | `""`    | Prefix for the file location.                   |

[opendal operators]: https://opendal.apache.org/docs/python/api/operator/

### `file_keeper:fsspec`

| Setting    | Type                      | Default | Description                                   |
|------------|---------------------------|---------|-----------------------------------------------|
| `fs`       | fsspec.AbstractFileSystem | `None`  | Existing fsspec filesystem                    |
| `protocol` | str                       | `""`    | Name of fsspec operator.                      |
| `params`   | dict                      | `{}`    | Parameters for fsspec operatorinitialization. |


### `file_keeper:redis`

| Setting  | Type        | Default | Description                                 |
|----------|-------------|---------|---------------------------------------------|
| `redis`  | redis.Redis | `None`  | Optional existing connection to Redis DB    |
| `url`    | str         | `""`    | URL of the Redis DB.                        |
| `bucket` | str         | `""`    | Key of the Redis HASH for uploaded objects. |

### `file_keeper:s3`

| Setting      | Type     | Default | Description                           |
|--------------|----------|---------|---------------------------------------|
| `bucket`     | str      | `""`    | Name of the storage bucket.           |
| `client`     | S3Client | `None"` | Existing S3 client.                   |
| `key`        | str      | `None`  | The AWS Access Key.                   |
| `secret`     | str      | `None`  | The AWS Secret Key.                   |
| `region`     | str      | `None`  | The AWS Region of the bucket.         |
| `endpoint`   | str      | `None`  | Custom AWS endpoint.                  |
| `path`       | str      | `""`    | Prefix for the file location.         |
| `initialize` | bool     | `False` | Create `bucket` if it does not exist. |

### `file_keeper:sqlalchemy`

| Setting           | Type                                        | Default | Description                                     |
|-------------------|---------------------------------------------|---------|-------------------------------------------------|
| `db_url`          | str                                         | `""`    | URL of the storage DB.                          |
| `table_name`      | str                                         | `""`    | Name of the storage table.                      |
| `location_column` | str                                         | `""`    | Name of the column that contains file location. |
| `content_column`  | str                                         | `""`    | Name of the column that contains file content.  |
| `engine`          | Engine { title="sqlalchemy.engine.Engine" } | `None`  | Existing DB engine.                             |
| `table`           | Engine { title="sqlalchemy.Table" }         | `None`  | Existing DB table.                              |
| `location`        | Engine { title="sqlalchemy.Column[str]" }   | `None`  | Existing column for location.                   |
| `content`         | Engine { title="sqlalchemy.Column[bytes]" } | `None`  | Existing column for content.                    |
| `initialize`      | bool                                        | `False` | Create `table_name` if it does not exist.       |

### `file_keeper:zip`

| Setting    | Type | Default | Description                                   |
|------------|------|---------|-----------------------------------------------|
| `zip_path` | str  | `""`    | Path of the ZIP archive for uploaded objects. |
