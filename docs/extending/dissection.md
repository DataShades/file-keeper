# Dissecting storage adapter

This guide walks you through implementation of filesystem adapter. We'll look
at every part of it from the outer layer and going inwards, analyzing the
meaning of the units and reasons they exist.

## Register an adapter

Adapters must be registered to make them available via
[make_storage][file_keeper.make_storage].

Define [an
entry-point](https://setuptools.pypa.io/en/latest/userguide/entry_point.html)
with the name `file_keeper_ext` in the distribution. This entry-point specifies
python module that contains [implementation of the pluggy
hooks](https://pluggy.readthedocs.io/en/stable/#implementations) that extends
file-keeper.

```toml
--8<-- "pyproject.toml:entrypoint"
```


file-keeper expects to find a function decorated with `@file_keeper.hookimpl`
and named `register_adapters` inside the module. This function registers all
custom adapters of the module via call to `register()` method of the
[Registry][file_keeper.Registry] with adapters. This call accepts the name of
the adapter as a first argument, and the class of the adapter as a second
argument.

```py
--8<-- "src/file_keeper/default/__init__.py:register"
```

Adapter names have no restrictions regarding length or allowed symbols, but
it's recommended to use `<package>:<type>` structure, like in
`file_keeper:fs`. If you provide multiple similar adapters, consider adding
third segment, i.e. `file_keeper:fs:v1`, `file_keeper:fs:v2`.


## Create an adapter

The adapter itself is simple and usually contains just few lines of code.

It **must** extend [Storage][file_keeper.Storage] and, optionally, it can
override [SettingsFactory][file_keeper.Storage.SettingsFactory],
[UploaderFactory][file_keeper.Storage.UploaderFactory],
[ManagerFactory][file_keeper.Storage.ManagerFactory], and
[ReaderFactory][file_keeper.Storage.ReaderFactory].

```py
--8<-- "src/file_keeper/default/adapters/fs.py:storage"
```

Filesystem adapter overrides all these attributes because:

* it contains custom settings(`SettingsFactory`)
* it defines how the file is uploaded (`UploaderFactory`)
* it defines how the file is managed, i.e. removed, copied, analyzed (`ManagerFactory`)
* it defines how file is read (`ReaderFactory`)

Additionally it specifies type of `settings` attribute as `settings: Settings`,
i.e. custom `Settings` class that is defined in the same module. This is done
to simplify typing and does not affect the behavior of the adapter. Without
this line typechecker assumes that storage uses base
[Settings][file_keeper.Settings] and complains when custom options are
accessed.

## Define storage settings

Create a dataclass `Settings` to hold configuration options specific to your
storage. This class should inherit from [Settings][file_keeper.Settings].

```py
--8<-- "src/file_keeper/default/adapters/fs.py:storage_cfg"
```

Filesystem settings do not introduce new options, so there are no attributes
here. But some other provider would do the following:

```py
@dataclasses.dataclass()
class Settings(fk.Settings):
    bucket: str = ""
    username: str = ""
    password: str = ""
    params: dict[str, Any] = dataclasses.field(default_factory=dict)
```

These options must include default values due to dataclass restrictions, even
if storage will not work with these defaults. E.g., empty password and username
won't work usually, but you still have to specify them.

And now happens validation. It's provided by the `__post_init__` method of
the dataclass.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:storage_cfg_post_init"
```

Filesystem adapter relies on two generic options. First is `initialize`. When
this flag is enabled, storage checks whether directory for files exists and, if
it's missing, tries to create this directory. If task fails,
[InvalidStorageConfigurationError][file_keeper.exc.InvalidStorageConfigurationError]
is raised. That's how storage reacts on problems with configuration.

Second option is `path`. `path`, usually absolute, defines the location in
filesystem where files are stored. Other storages may treat it differently:
cloud storages use `path` as a prefix of the file name, because cloud storages
do not support directory hierarchy; SQLAlchemy storage ignores path as it has
no meaning in DB context.

Apart from this, storages often initialize and store connections to external
services as storage attributes. For example, `file_keeper:azure_blob` has
`container_name` string options that holds the name of cloud container where
files are stored. Inside `__post_init__` it connects to the container and
stores the container object itself as `container` property, so that storage
doesn't need to constantly re-connect to the containers.


## Create the uploader service

The next target is `Uploader`. It's a service reesponsible for file creation
that must extend [Uploader][file_keeper.Uploader].

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_def"
```

Any service consists of two parts - methods and capabilities. Methods describe
the logic but are hidden from storage initially. I.e., if you only define
methods and ignore capabilities, storage will pretend that service cannot
perform the task.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_method"
        ...
```

And capabilities actually tell storage about operations supported by
storage. Because of this separation, you can pretend that storage cannot
perform an operation, even when it's supported. In this way you can transform
filesystem into a read-only storage without code changes and guarantee that
files won't be accidentally removed from it.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_capability"
```

As you can see, FS storage supports [CREATE][file_keeper.Capability.CREATE] and
[MULTIPART][file_keeper.Capability.MULTIPART]. Capabilities are implemented as
bit masks and can be combined using `|` operator.

Let's look closer at the `upload()` method.

It computes full path to the file location in the beginning. `full_path()` is a
generic method of the storage that naively combine `path` option of the storage
with `location` of the file. Every storage has `path` option and every storage
_can_ use `full_path()` to attach `path` as a prefix to the location, if it
makes any sense.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_impl_path"
```

Now storage uses another generic option, `override_existing`. If it's disabled
and given location already taken by another file, uploader raises
[ExistingFileError][file_keeper.exc.ExistingFileError]. That's recommended
reaction in such situation and you'll notice that other storages also follow
this process.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_impl_check"
```

Then storage ensures that all intermediate folders from the final file's
location are present. If you expect that files are loaded directly into `path`,
it may seem redundant. But FS storage does not imply such restrictions and
there may be nested directories under the `path`, so verifying that all folders
are created is a safest option.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_impl_makedirs"
```

Then file is actually written to the FS. You an read file content using
`upload.read()`, but here we create [HashingReader][file_keeper.HashingReader]
using `hashing_reader()` method of the [Upload][file_keeper.Upload]. This
object also has `read()` method, but in addition it computes the content hash
of the file while it's consumed. As result we have the hash in the and almost
for free.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_impl_write"
```

Other storages, like AWS S3 or Azure Blob Storage, do not need this step,
because content hash is computed by cloud provided and returned with the
metadata of the uploaded object. But if you don't have a cheap way to obtain
the hash, using [HashingReader][file_keeper.HashingReader] is the recommended
option.

In the end, `upload()` method of the service builds
[FileData][file_keeper.FileData] with details of the uploaded file and returns
it to the caller.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:uploader_impl_result"
```


## Create the reader service

`Reader` service is much simpler than `Uploader`. It exposes
[STREAM][file_keeper.Capability.STREAM] capability to notify the storage, that
files can be read from the storage. And it implements `stream()` method, that
explains how exactly bytes of content are obtained.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:reader_impl"
```

Note how it computes the path to the file using `full_path()`, just as
`Uploader` did. Basically, every method that access the file should use
`full_path()`.

Also, pay attention to [MissingFileError][file_keeper.exc.MissingFileError]
raised if file does not exist. That's the recommended way to handle missing
files.

Finally, look at return result. The `stream()` method must return
`Iterable[bytes]`, but not just bytes, e.g. `return b"hello"` is not valid
output.

Anything that can be used in a for-loop and produce `bytes` is a valid output
of the `steam()` method. Few examples:

/// tab | List of byte strings

```py
...
return [b"hello", b" ", b"world"]

```
///

/// tab | Generator of bytes

```py
...
yield b"hello"
yield b" "
yield b"world"
```

///

/// tab | io.BytesIO

```py
...
return BytesIO(b"hello world")
```

///

/// tab | Descriptor of the file opened in `rb` mode

```py
...
return open(path, "rb")
```

///


## Create the manager service

`Manager` service contains a lot of methods and capabilities, but all of them
are pretty straight forward.

Remember, that capabilities tell the storage "what" service can do, while
method implementations explain "how" it's done. Usually, capability and method
come in pair, unless you are certain that you need to separate them.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_capabilities"
```

`remove()` method removes the object. If it's removed, the result is `True`. If
it's not removed(because it does not exists), the result is `False`.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_remove"
```

`scan()` returns an iterable of strings with names of all files available in
the storage.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_scan"
```

`exists()` returns `True` if file exists, and `False` if file is missing.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_exists"
```

`analyze()` returns the same [FileData][file_keeper.FileData] as one, produced
during `upload()`.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_analyze"
```

`copy()` creates a copy of the file, raising
[MissingFileError][file_keeper.exc.MissingFileError] if source file is missing
and [ExistingFileError][file_keeper.exc.ExistingFileError] if destination file
already exist and `override_existing` is disabled.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_copy"
```

`move()` behaves exactly like `copy()`. In addition, the original file is not
available after the move. Basically, `move()` does "rename" if possible, and
"copy" + "remove" if not.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_move"
```

`compose()` is the most challenging method of the `Manager`. It takes few
existing files and combines them into a new one, similar to the `cat` utility.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_compose"
```

`append()` takes content of the existing file and adds it in the end of another
file.

```py
--8<-- "src/file_keeper/default/adapters/fs.py:manager_append"
```
