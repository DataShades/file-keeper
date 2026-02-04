# File Upload Web Application Example

This example demonstrates how to use file-keeper in a web application with Flask.

## Overview

This Flask application shows:

- File uploads using file-keeper
- Security best practices
- Error handling
- Different storage backends (filesystem, memory)

## Prerequisites

- Python 3.10+
- pip

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run with Filesystem Storage (Default)
```bash
python app.py
```

### Run with Memory Storage (for testing)
```bash
STORAGE_TYPE=memory python app.py
```

### Run with Custom Storage Path
```bash
STORAGE_PATH=/path/to/uploads python app.py
```

## API Endpoints

- `POST /upload` - Upload a file
- `GET /files` - List all files
- `GET /file/<filename>` - Download a file
- `DELETE /file/<filename>` - Delete a file
- `GET /health` - Health check

## Example Usage

### Upload a file:
```bash
curl -X POST -F "file=@myfile.txt" http://localhost:5000/upload
```

### List files:
```bash
curl http://localhost:5000/files
```

### Download a file:
```bash
curl http://localhost:5000/file/myfile.txt -O
```

## Security Features

- Filename sanitization using werkzeug's secure_filename
- File type validation
- File size limits
- Directory traversal prevention
- Capability checking before operations

## Configuration

You can configure the application using environment variables:

- `STORAGE_TYPE`: Storage backend ('fs' for filesystem, 'memory' for in-memory)
- `STORAGE_PATH`: Path for filesystem storage (defaults to './uploads')

## Testing

The application includes basic functionality testing. For comprehensive testing,
consider using pytest with the following test structure:

```python
# test_app.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    rv = client.get('/health')
    assert b'healthy' in rv.data
```
