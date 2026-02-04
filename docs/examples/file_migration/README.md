# File Migration Example

This example demonstrates how to migrate files between different storage backends using file-keeper.

## Overview

This script shows:

- How to migrate files from one storage backend to another
- Validation of migrated files
- Error handling during migration
- Selective migration based on filters
- Examples for cloud storage migrations

## Prerequisites

- Python 3.10+
- file-keeper library

## Installation

```bash
pip install file-keeper
```

## Usage

### Run the basic migration example:
```bash
python migration_example.py
```

This will:

1. Create sample files in memory storage
2. Migrate them to temporary filesystem storage
3. Validate the migration
4. Show results

## Key Features Demonstrated

### 1. Basic Migration
```python
from file_migration import migrate_files

successful, failed = migrate_files(source_storage, dest_storage)
```

### 2. Filtered Migration
```python
# Only migrate .txt files
def txt_filter(location: str) -> bool:
    return location.endswith('.txt')

successful, failed = migrate_files(
    source_storage,
    dest_storage,
    file_filter=txt_filter
)
```

### 3. Validated Migration
```python
# Enable validation to ensure file integrity
successful, failed = migrate_files(
    source_storage,
    dest_storage,
    validate_after_migration=True
)
```

## Real-World Usage

### Migrating from S3 to Google Cloud Storage:
```python
import file_keeper as fk

# Source: S3
s3_source = fk.make_storage("s3_source", {
    "type": "file_keeper:s3",
    "bucket": "my-source-bucket",
    "key": os.getenv('AWS_ACCESS_KEY_ID'),
    "secret": os.getenv('AWS_SECRET_ACCESS_KEY'),
    "region": "us-east-1"
})

# Destination: Google Cloud Storage
gcs_dest = fk.make_storage("gcs_dest", {
    "type": "file_keeper:gcs",
    "bucket_name": "my-dest-bucket",
    "credentials_file": "/path/to/gcs-credentials.json"
})

# Perform migration
successful, failed = migrate_files(s3_source, gcs_dest)
```

### Migrating with size limits:
```python
def size_filter(location: str) -> bool:
    # Skip files larger than 100MB
    file_info = source_storage.analyze(location)
    return file_info.size <= (100 * 1024 * 1024)

successful, failed = migrate_files(
    source_storage,
    dest_storage,
    file_filter=size_filter
)
```

## Error Handling

The migration function handles various error conditions:

- Network interruptions
- Permission issues
- Storage capacity limits
- Invalid file formats

Failed migrations are logged and returned separately for further processing.

## Security Considerations

- Files are validated after migration to ensure integrity
- Content is compared between source and destination
- Filters can be used to prevent migration of unsafe file types
- All operations respect storage capabilities

## Performance Tips

- For large migrations, consider batching operations
- Use appropriate storage backends for temporary files
- Monitor storage quotas during migration
- Consider using multipart uploads for large files
