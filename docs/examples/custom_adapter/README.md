# Custom Adapter Example

This example demonstrates how to create custom storage adapters for file-keeper.

## Overview

This script shows:

- How to create a SQLite-based storage adapter
- How to create an encrypted file storage adapter
- Best practices for adapter development
- Minimal adapter implementation example

## Prerequisites

- Python 3.10+
- file-keeper library
- cryptography library (for encrypted adapter)

## Installation

```bash
pip install file-keeper cryptography
```

## Usage

### Run the custom adapter examples:
```bash
python custom_adapter_example.py
```

This will:

1. Demonstrate the SQLite storage adapter
2. Demonstrate the encrypted storage adapter
3. Show best practices for adapter development
4. Provide a minimal adapter example

## Key Concepts

### 1. Adapter Structure

Every adapter consists of:

- **Settings**: Configuration class inheriting from `fk.Settings`
- **Uploader**: Handles file uploads (inherits from `fk.Uploader`)
- **Manager**: Handles file management (inherits from `fk.Manager`)
- **Reader**: Handles file reading (inherits from `fk.Reader`)
- **Storage**: Main class combining all components (inherits from `fk.Storage`)

### 2. Capability System

Adapters declare their capabilities by setting the `capabilities` attribute:

```python
class MyUploader(Uploader):
    capabilities = Capability.CREATE

class MyManager(Manager):
    capabilities = Capability.EXISTS | Capability.ANALYZE | Capability.REMOVE

class MyReader(Reader):
    capabilities = Capability.STREAM | Capability.RANGE
```

### 3. SQLite Adapter Example

```python
class SQLiteStorage(Storage):
    SettingsFactory = SQLiteSettings
    UploaderFactory = SQLiteUploader
    ManagerFactory = SQLiteManager
    ReaderFactory = SQLiteReader

    def __init__(self, settings):
        super().__init__(settings)
        # Initialize database connection
        self.db = sqlite3.connect(settings.db_path)
```

## Creating Your Own Adapter

### Step 1: Define Settings
```python
from file_keeper import Settings
import dataclasses

@dataclasses.dataclass
class MyCustomSettings(Settings):
    host: str = "localhost"
    port: int = 8080
    username: str = ""
    password: str = ""
    _required_options = ["host"]  # Required fields
```

### Step 2: Implement Services
```python
from file_keeper import Uploader, Manager, Reader, Capability

class MyUploader(Uploader):
    capabilities = Capability.CREATE

    def upload(self, location, upload, extras):
        # Implement upload logic
        pass

class MyManager(Manager):
    capabilities = Capability.EXISTS | Capability.ANALYZE | Capability.REMOVE

    def exists(self, data, extras):
        # Implement existence check
        pass

    def analyze(self, location, extras):
        pass

    def remove(self, data, extras):
        pass

class MyReader(Reader):
    capabilities = Capability.STREAM

    def stream(self, data, extras):
        # Implement streaming logic
        pass
```

### Step 3: Create Storage Class
```python
from file_keeper import Storage

class MyCustomStorage(Storage):
    SettingsFactory = MyCustomSettings
    UploaderFactory = MyUploader
    ManagerFactory = MyManager
    ReaderFactory = MyReader

    def __init__(self, settings):
        super().__init__(settings)
        # Initialize your backend connection
        self.client = self.initialize_backend()

    def initialize_backend(self):
        # Initialize your storage backend
        pass
```

### Step 4: Register the Adapter
```python
import file_keeper as fk

# initialize adapter registry. This is not required when storages
# are registered via package entry-points.
fk.ext.setup()

# Register your adapter
fk.adapters.register("file_keeper:myadapter", MyCustomStorage)

# Now you can use it
storage = fk.make_storage("my_storage", {
    "type": "file_keeper:myadapter",
    "host": "myserver.com",
    "port": 9000
})
```

## Best Practices

1. **Define appropriate settings**: Include validation and required fields
2. **Implement only supported capabilities**: Don't claim capabilities your backend doesn't support
3. **Handle errors properly**: Use file-keeper's exception hierarchy
4. **Respect security**: Validate paths and implement proper access controls
5. **Test thoroughly**: Test with the standard test suite
6. **Document limitations**: Clearly document what your adapter supports
7. **Follow interface contracts**: Maintain compatibility with file-keeper interfaces
8. **Consider thread safety**: If your backend supports concurrent access

## Security Considerations

When creating custom adapters, pay attention to:
- Path traversal prevention
- Authentication and authorization
- Data encryption at rest
- Secure credential handling
- Input validation

## Performance Considerations

- Minimize network calls when possible
- Implement efficient streaming for large files
- Use appropriate caching strategies
- Consider connection pooling for network backends
- Optimize for your specific use case

## Testing Your Adapter

Create tests that verify:

- All claimed capabilities work correctly
- Error conditions are handled properly
- Security measures are effective
- Performance meets requirements
- Edge cases are handled
