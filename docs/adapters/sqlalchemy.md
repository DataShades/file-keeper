# SQLAlchemy Adapter

The `file_keeper:sqlalchemy` adapter allows you to use a relational database managed by SQLAlchemy for storing and retrieving file metadata and content. This adapter stores file content as binary data within the database.

## Overview

This adapter provides a way to integrate a relational database with file-keeper. You'll need to have SQLAlchemy installed (`pip install sqlalchemy`) and a configured database connection string.  This adapter is suitable for scenarios where you need to store file metadata alongside the file content in a structured manner.

## Initialization Example

Here's an example of how to initialize the SQLAlchemy adapter:

```python
from file_keeper import make_storage

storage = make_storage("my_sqlalchemy_storage", {
    "type": "file_keeper:sqlalchemy",
    "url": "postgresql://user:password@host:port/database",  # Replace with your database connection string
    "table_name": "files",  # Replace with the name of the table to store files
})

# Now you can use the 'storage' object to upload, download, and manage files.
```

**Important Notes:**

*   Replace the placeholder values (url, table\_name) with your actual database connection string and table name.
*   Ensure that the specified table exists in your database. The adapter will create the table if it doesn't exist, but you may need to adjust the schema based on your specific requirements.
*   The database connection string should be in a format supported by SQLAlchemy.  Refer to the [SQLAlchemy documentation](https://www.sqlalchemy.org/core/connections.html) for details.
*   Consider the performance implications of storing large files directly in the database.
