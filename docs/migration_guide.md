# Migration Guide

Learn how to migrate from other file storage libraries to file-keeper.

## Migrating from Direct Filesystem Operations

If you're currently using direct filesystem operations, here's how to migrate to file-keeper's filesystem adapter.

### Before: Direct Filesystem Operations

```python
import os
import shutil
from pathlib import Path

# Creating directories
upload_dir = Path("/uploads")
upload_dir.mkdir(parents=True, exist_ok=True)

# Saving a file
file_path = upload_dir / "myfile.txt"
with open(file_path, 'wb') as f:
    f.write(b"file content")

# Reading a file
with open(file_path, 'rb') as f:
    content = f.read()

# Checking if file exists
if file_path.exists():
    print("File exists")

# Removing a file
if file_path.exists():
    file_path.unlink()
```

### After: Using file-keeper

```python
import file_keeper as fk

# Initialize storage
storage = fk.make_storage("fs", {
    "type": "file_keeper:fs",
    "path": "/uploads",
    "initialize": True  # Creates directory if it doesn't exist
})

# Uploading a file
upload = fk.make_upload(b"file content")
file_info = storage.upload("myfile.txt", upload)

# Reading a file
content = storage.content(file_info)

# Checking if file exists
if storage.supports(fk.Capability.EXISTS):
    exists = storage.exists(file_info)
    print(f"File exists: {exists}")

# Removing a file
if storage.supports(fk.Capability.REMOVE):
    storage.remove(file_info)
```

### Benefits of Migration

1. **Consistency**: Same API regardless of storage backend
2. **Security**: Built-in protection against directory traversal
3. **Flexibility**: Easy switch to cloud storage later
4. **Capabilities**: Runtime checking of supported operations

## Migrating from boto3 (AWS S3)

### Before: Using boto3 directly

```python
import boto3
from botocore.exceptions import ClientError

# Initialize client
s3_client = boto3.client(
    's3',
    aws_access_key_id='your-key',
    aws_secret_access_key='your-secret',
    region_name='us-east-1'
)

bucket_name = 'my-bucket'

# Upload file
def upload_file(key, file_content):
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=file_content
    )

# Download file
def download_file(key):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read()
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        raise

# Check if file exists
def file_exists(key):
    try:
        s3_client.head_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise

# Delete file
def delete_file(key):
    s3_client.delete_object(Bucket=bucket_name, Key=key)
```

### After: Using file-keeper S3 adapter

```python
import file_keeper as fk
from file_keeper import exc

# Initialize storage
storage = fk.make_storage("s3", {
    "type": "file_keeper:s3",
    "bucket": "my-bucket",
    "key": "your-key",
    "secret": "your-secret",
    "region": "us-east-1"
})

# Upload file
upload = fk.make_upload(b"file content")
file_info = storage.upload("myfile.txt", upload)

# Download file
try:
    content = storage.content(file_info)
except exc.MissingFileError:
    content = None

# Check if file exists
if storage.supports(fk.Capability.EXISTS):
    exists = storage.exists(file_info)

# Delete file
if storage.supports(fk.Capability.REMOVE):
    storage.remove(file_info)
```

### Benefits of Migration

1. **Simplified Error Handling**: Unified exception hierarchy
2. **Capability Checking**: Know what operations are supported
3. **Backend Flexibility**: Can switch to local storage for testing
4. **Consistent API**: Same interface as other storage types

## Migrating from Django Storages

### Before: Using Django Storages

```python
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Save file
def save_file(filename, content):
    path = default_storage.save(filename, ContentFile(content))
    return path

# Read file
def read_file(filename):
    if default_storage.exists(filename):
        with default_storage.open(filename, 'rb') as f:
            return f.read()
    return None

# Get file URL
def get_file_url(filename):
    if default_storage.exists(filename):
        return default_storage.url(filename)
    return None

# Delete file
def delete_file(filename):
    if default_storage.exists(filename):
        default_storage.delete(filename)
```

### After: Using file-keeper with Django

```python
import file_keeper as fk
from file_keeper import exc

# Initialize storage (could be configured via Django settings)
storage = fk.make_storage("django_files", {
    "type": "file_keeper:fs",  # or s3, gcs, etc.
    "path": "/path/to/django/media",
    "initialize": True
})

def save_file(filename, content):
    upload = fk.make_upload(content)
    file_info = storage.upload(filename, upload)
    return file_info.location

def read_file(filename):
    # Find file by scanning or you'd need to store file_info elsewhere
    for loc in storage.scan():
        if loc == filename:
            try:
                file_info = storage.analyze(loc)
                return storage.content(file_info)
            except exc.FilesError:
                return None
    return None

def delete_file(filename):
    # Find file by scanning
    for loc in storage.scan():
        if loc == filename:
            try:
                file_info = storage.analyze(loc)
                if storage.supports(fk.Capability.REMOVE):
                    return storage.remove(file_info)
            except exc.FilesError:
                return False
    return False
```

## Migrating from Google Cloud Storage (gcs)

### Before: Using google-cloud-storage directly

```python
from google.cloud import storage
from google.cloud.exceptions import NotFound

# Initialize client
client = storage.Client()
bucket = client.bucket('my-bucket')

# Upload file
def upload_file(blob_name, file_content):
    blob = bucket.blob(blob_name)
    blob.upload_from_string(file_content)

# Download file
def download_file(blob_name):
    blob = bucket.blob(blob_name)
    try:
        return blob.download_as_bytes()
    except NotFound:
        return None

# Check if file exists
def file_exists(blob_name):
    blob = bucket.blob(blob_name)
    return blob.exists()

# Delete file
def delete_file(blob_name):
    blob = bucket.blob(blob_name)
    blob.delete()
```

### After: Using file-keeper GCS adapter

```python
import file_keeper as fk
from file_keeper import exc

# Initialize storage
storage = fk.make_storage("gcs", {
    "type": "file_keeper:gcs",
    "bucket_name": "my-bucket",
    "credentials_file": "/path/to/credentials.json"  # or use other auth methods
})

# Upload file
upload = fk.make_upload(b"file content")
file_info = storage.upload("myfile.txt", upload)

# Download file
try:
    content = storage.content(file_info)
except exc.MissingFileError:
    content = None

# Check if file exists
if storage.supports(fk.Capability.EXISTS):
    exists = storage.exists(file_info)

# Delete file
if storage.supports(fk.Capability.REMOVE):
    storage.remove(file_info)
```

## Migration Strategy

### 1. Gradual Migration Approach

Start by replacing one storage operation at a time:

```python
# Old code
import os
def save_user_avatar_old(user_id, avatar_data):
    filepath = f"/avatars/{user_id}.jpg"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(avatar_data)
    return filepath

# New code
import file_keeper as fk
storage = fk.make_storage("avatars", {
    "type": "file_keeper:fs",
    "path": "/avatars",
    "initialize": True
})

def save_user_avatar_new(user_id, avatar_data):
    upload = fk.make_upload(avatar_data)
    file_info = storage.upload(f"{user_id}.jpg", upload)
    return file_info.location
```

### 2. Configuration Management

Create a configuration factory to make switching between environments easier:

```python
import os
import file_keeper as fk

def create_file_storage(env=None):
    """Create appropriate storage based on environment."""
    env = env or os.getenv('ENVIRONMENT', 'development')
    
    if env == 'production':
        return fk.make_storage("prod", {
            "type": "file_keeper:s3",
            "bucket": os.getenv('S3_BUCKET'),
            "key": os.getenv('AWS_ACCESS_KEY_ID'),
            "secret": os.getenv('AWS_SECRET_ACCESS_KEY'),
            "region": os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        })
    else:
        # Use local storage for development/testing
        return fk.make_storage("dev", {
            "type": "file_keeper:fs",
            "path": "./dev-storage",
            "initialize": True
        })

# Use the factory
storage = create_file_storage()
```

### 3. Testing During Migration

Maintain both old and new implementations temporarily and compare results:

```python
import tempfile
import os

def test_migration_consistency():
    """Test that old and new implementations produce same results."""
    
    # Old implementation
    with tempfile.TemporaryDirectory() as tmpdir:
        old_filepath = os.path.join(tmpdir, "test.txt")
        with open(old_filepath, 'wb') as f:
            f.write(b"test content")
        
        with open(old_filepath, 'rb') as f:
            old_content = f.read()
    
    # New implementation
    storage = fk.make_storage("test", {
        "type": "file_keeper:fs",
        "path": tmpdir,
        "initialize": True
    })
    
    upload = fk.make_upload(b"test content")
    file_info = storage.upload("test.txt", upload)
    new_content = storage.content(file_info)
    
    # Compare
    assert old_content == new_content
    print("Migration test passed!")
```

## Common Migration Pitfalls to Avoid

1. **Don't forget to check capabilities** - Always verify that operations are supported before calling them
2. **Handle exceptions properly** - Use file-keeper's exception hierarchy
3. **Update your tests** - Mock file-keeper storage instead of filesystem operations
4. **Consider data migration** - Plan how to migrate existing files to new storage
5. **Update security policies** - Ensure new storage backend has appropriate access controls

By following these migration patterns, you can gradually transition your application to use file-keeper while maintaining functionality and gaining the benefits of a unified storage interface.