# SQLAlchemy Adapter

The `file_keeper:sqlalchemy` adapter allows you to use a relational database
managed by SQLAlchemy for storing and retrieving file content. This adapter
stores file content as binary data within the database.

## Overview

This adapter provides a way to integrate a relational database with
file-keeper. You'll need to have SQLAlchemy installed and a configured database
connection string.  This adapter is suitable for scenarios where you need to
store file metadata alongside the file content in a structured manner.

```sh
pip install 'file-keeper[sqlalchemy]'

## or

pip install sqlalchemy
```


## Initialization Example

Here's an example of how to initialize the SQLAlchemy adapter:


```python
storage = make_storage("my_sqlalchemy_storage", {
    "type": "file_keeper:sqlalchemy",
    "db_url": "sqlite:///:memory:",
    "table_name": "file-keeper",
    "location_column": "location",
    "content_column": "content",
    "initialize": True,
})
```

**Important Notes:**

*   Replace the placeholder values with your actual database
    connection string and table name.
*   Enable `initialize` flag or ensure that the specified table exists in your
    database.
*   The database connection string should be in a format supported by
    SQLAlchemy.  Refer to the [SQLAlchemy
    documentation](https://docs.sqlalchemy.org/en/20/core/engines.html) for
    details.
*   Consider the performance implications of storing large files directly in
    the database.
