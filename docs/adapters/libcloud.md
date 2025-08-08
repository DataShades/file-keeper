# Apache Libcloud

`file_keeper:libcloud`

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
