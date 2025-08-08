# Local filesystem

`file_keeper:fs`

No specific settings.

If directory specified by `path` option does not exists, depending on
`initialize` flag, storage will make an attempt to create `path` or rise
[InvalidStorageConfigurationError][file_keeper.exc.InvalidStorageConfigurationError].

/// details | Storage initialization
```mermaid
graph TD
  check{<code>path</code> exists?};
  check_initialize{<code>initialize</code> flag enabled?};
  check_permission{Have permission to create <code>path</code> hierarchy?};

  no_work([Storage initialized]);
  raise([raise InvalidStorageConfigurationError]);
  create([Directories created and storage initialized]);

  check -->|Yes| no_work;
  check -->|No| check_initialize;
  check_initialize -->|No| raise;
  check_initialize -->|Yes| check_permission;
  check_permission -->|No| raise;
  check_permission -->|Yes| create;
```
///

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
