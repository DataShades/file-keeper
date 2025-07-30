# Overview

Abstraction layer for reading, writing, and managing file-like objects.

The package implements adapters for several storage types(local filesystem,
redis, AWS S3, etc.) and defines a set of tools to simplify building your own
adapters for the storage you are using.

## Usage

The main object required for managing files is a *storage*. Storage initialized
using a mapping with settings that contains the type of the underlying
driver. And, depending on the driver itself, additional options may be
required: FS storage needs the path inside the filesystem, while cloud storages
would ask you to provide bucket names, secrets, etc.

### Local filesystem

Let's use the filesystem driver, which is called `file_keeper:fs`. This driver
requires the `path` of a root directory where uploaded files are stored. If
given path does not exist, the storage will raise an error during
initialization. We can either create the directory in advance manually, or
enable `create_path` option of the storage, to automatically add missing
folders instead of raising an exception.

To initialize the storage, one must call `make_storage` function, that accepts
the name of the storage(used internally for making readable error messages) and
the mapping with settings.

```python
from file_keeper import make_storage

storage = make_storage("sandbox", {
    "type": "file_keeper:fs",
    "path": "/tmp/example",
    "create_path": True,
})
```

Now we need at least one file uploaded into the storage via it's `upload`
method. This method requires the *location* of the upload and the `Upload`
object with the content. This upload object can be created using `make_upload`
function - just pass bytes, `BytesIO` or file-like object into it.

```python
from file_keeper import make_upload

upload = make_upload(b"hello world")
info = storage.upload("hello.txt", upload)
```

`upload` method has produced `info` object of type `FileData`. This is a
dataclass that contains the most essential details about the new upload:
location, size, content type and content hash. You need this object to get the
file back from the storage.

If you don't have such object, but you are sure that there is a file in storage
available at the certain location, `hello.txt` for example, you can build such
info object on your own. You don't even need size or content type - just
providing the location should be enough:

```python
from file_keeper import FileData

info = FileData("hello.txt")
```

Now, when you have `info` object, use it to:

* read the file

    ```python
    content = storage.content(info)
    assert content == b"hello world"
    ```

* move the file to a new location. Note, this method produces a new `info`
  object that we'll use from now on to access the file. Previous `info` is no
  longer required as it points to non-existing location

    ```python
    info = storage.move("moved-hello.txt", info)
    ```

* remove the file

    ```python
    storage.remove(info)
    ```


If you want to use a different storage adapter, initialize a different
storage. All other operations remain the same.

### Redis

Let's try Redis storage, which is available if you installed file-keeper with
`redis` extras:

```sh
pip install 'file-keeper[redis]'
```

The adapter is called
`file_keeper:redis`. It expects Redis DB to be available at
`redis://localhost:6379/0`(which can be changed via `url` option). And it also
requires `path` option, but here it will be used as a name of HASH where all
the files are stored Redis.

```python
from file_keeper import make_storage, make_upload

storage = make_storage("sandbox", {
    "type": "file_keeper:redis",
    "path": "files-from-file-keeper"
})

upload = make_upload(b"hello world")

info = storage.upload("hello.txt", upload)
assert info.size == 11

content = storage.content(info)
assert content == b"hello world"

storage.remove(info)
# method that checks whether the file exists in the storage
assert not storage.exists(info)
```


### Cloud

Finally, let's check cloud storage. There are multiple options, but we'll use
[Apache Libcloud](https://libcloud.apache.org/) adapter. To make it available,
install file-keeper with `libcloud` extras:

```sh
pip install 'file-keeper[libcloud]'
```

The adapter is called `file_keeper:libcloud`. Unlike previous adapters, it has
a lot of options and majority of them are required:

* `provider`: name of [Apache Libcloud
  provider](https://libcloud.readthedocs.io/en/stable/supported_providers.html)
* `params`: mapping with additional parameters specific for the chosen provider
* `key`: access key for the cloud storage
* `secret`: access secret for the cloud storage
* `container_name`: name of the container/bucket where files are stored

Requirements regarding this options are not the same for different storage
providers. We'll use `MINIO` provider(because it's free). For this example, we
assume that MINIO is running locally, on 9000 port, without SSL. You can create
a Docker container using the command below:

```sh
docker run -p 9000:9000 -p 9001:9001 \
    --name minio -e MINIO_PUBLIC_ADDRESS=0.0.0.0:9000 \
    quay.io/minio/minio server /data --console-address ":9001"
```

Details about this local MinIO service will be encoded into `params` option:
`{"host": "127.0.0.1", "port": 9000, "secure": False}`.

Create MinIO credentials using WebUI available at [http://127.0.0.1:9001](http://127.0.0.1:9001) and add
them as `key` and `secret` options.

Finally, create a bucket `file-keeper` and specify it using `container_name` option.

That's how initialization will look when all preparations are done:

```python
storage = make_storage("sandbox", {
    "type": "file_keeper:libcloud",
    "provider": "MINIO",
    "params": {"host": "127.0.0.1", "port": 9000, "secure": False},
    "key": "***",
    "secret": "***",
    "container_name": "file-keeper",
})
```

/// note

`file_keeper:libcloud` adapter does not support `move` operation and you'll see
an exception upon calling `storage.move`.

Instead of using `file_keeper:libcloud`, you can try `file_keeper:s3` adapter
that relies on [boto3](https://pypi.org/project/boto3/) and is available when
file-keeper is installed with `s3` extras:

```sh
pip install 'file-keeper[s3]'
```

Unlike `file_keeper:libcloud`, `s3` adapter works only with AWS S3(and MinIO
that has identical API). But it supports wider list of storage operations, so
it worth using it if you know that you are not going to use different cloud
provider.

Initialization is slighly different for `file_keeper:s3`:

* use `bucket` instead of `container_name`
* add `endpoint` that combines `params.host` and `params.port` from `file_keeper:libcloud`

```python
from file_keeper import make_storage

storage = make_storage("sandbox", {
    "type": "file_keeper:s3",
    "endpoint": "http://127.0.0.1:9000",
    "key": "***",
    "secret": "***",
    "bucket": "file-keeper",
})
```

With `file_keeper:s3` you can use `move` and can replicate all operations used
in previous examples.
///
