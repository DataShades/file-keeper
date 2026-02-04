# Advanced patterns

This tutorial covers advanced patterns and techniques for using file-keeper effectively in production applications. We'll explore performance optimization, error handling strategies, and integration with web frameworks.

## Performance Optimization

### Efficient Large File Handling

For large files, use streaming to avoid loading everything into memory:

```python
import file_keeper as fk
from file_keeper import IterableBytesReader

def upload_large_file_from_chunks(storage, location, chunk_generator):
    """Upload a large file from a generator of chunks."""
    # Create an upload from an iterable of bytes
    stream = IterableBytesReader(chunk_generator)
    upload = fk.Upload(stream, location, estimate_size(chunk_generator), "application/octet-stream")

    return storage.upload(location, upload)

def estimate_size(chunk_generator):
    """Estimate total size from chunks."""
    total = 0
    for chunk in chunk_generator:
        total += len(chunk)
    return total

# Example usage
def file_chunk_generator(filepath, chunk_size=8192):
    """Generate chunks from a file."""
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

# Upload a large file efficiently
# file_info = upload_large_file_from_chunks(storage, "large_file.dat", file_chunk_generator("/path/to/large/file"))
```

Note, the code above reads data from the existing file and can be written simply as:
```py
with open("/path/to/large/file", "rb") as src:
    upload = fk.make_upload(src)
    return storage.upload(location, upload)
```

But when the content does not exist and needs to be generated in real-time,
`make_upload` cannot produce the required upload object. That's when
`IterableBytesReader` comes in handy.


### Batch Operations

When working with multiple files, consider batch operations where possible:

```python
def batch_upload(storage, file_dict):
    """Upload multiple files efficiently."""
    results = {}

    for filename, content in file_dict.items():
        try:
            upload = fk.make_upload(content)
            file_info = storage.upload(filename, upload)
            results[filename] = file_info
        except fk.exc.FilesError as e:
            print(f"Failed to upload {filename}: {e}")
            results[filename] = None

    return results

# Example usage
files_to_upload = {
    "file1.txt": b"Content of file 1",
    "file2.txt": b"Content of file 2",
    "file3.txt": b"Content of file 3"
}

results = batch_upload(storage, files_to_upload)
```

## Error Handling Strategies

### Retry Mechanisms

Implement robust retry logic for transient failures:

```python
import time
import random
from file_keeper import exc

def retry_on_failure(func, max_retries=3, base_delay=1, backoff_factor=2, jitter=True):
    """Execute a function with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return func()
        except (exc.ConnectionError, exc.UploadError) as e:
            if attempt == max_retries - 1:  # Last attempt
                raise e

            delay = base_delay * (backoff_factor ** attempt)
            if jitter:
                delay += random.uniform(0, 0.1 * delay)  # Add jitter

            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)

# Example usage
def upload_with_retry(storage, location, upload):
    def attempt():
        return storage.upload(location, upload)

    return retry_on_failure(attempt)
```

### Circuit Breaker Pattern

For external services, implement circuit breaker pattern:

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

class StorageCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, storage_func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise exc.FilesError("Circuit breaker is OPEN")

        try:
            result = storage_func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return result
        except exc.FilesError:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

            raise

# Example usage
breaker = StorageCircuitBreaker()

try:
    file_info = breaker.call(storage.upload, "test.txt", upload)
except exc.FilesError as e:
    print(f"Operation failed: {e}")
```

## Framework Integration

### Flask Integration

Integrate file-keeper with Flask for web file uploads:

```python
from flask import Flask, request, jsonify
import file_keeper as fk
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Initialize storage
storage = fk.make_storage("flask_storage", {
    "type": "file_keeper:fs",
    "path": "./uploads",
    "initialize": True
})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Create upload from Werkzeug FileStorage
        upload = fk.make_upload(file)

        # Sanitize filename
        filename = secure_filename(file.filename)

        # Upload the file
        file_info = storage.upload(filename, upload)

        return jsonify({
            'success': True,
            'location': file_info.location,
            'size': file_info.size,
            'hash': file_info.hash
        })
    except fk.exc.FilesError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Find file by scanning (in a real app, you'd store file_info elsewhere)
        for loc in storage.scan():
            if loc == filename:
                file_info = storage.analyze(loc)
                content = storage.content(file_info)
                return content, 200, {'Content-Type': file_info.content_type}

        return jsonify({'error': 'File not found'}), 404
    except fk.exc.FilesError as e:
        return jsonify({'error': str(e)}), 500
```

### Django Integration

For Django applications:

```python
# views.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import file_keeper as fk
from file_keeper import exc

# Initialize storage
storage = fk.make_storage("django_storage", {
    "type": "file_keeper:fs",
    "path": "./media",
    "initialize": True
})

@csrf_exempt
@require_http_methods(["POST"])
def upload_view(request):
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    uploaded_file = request.FILES['file']

    try:
        # Create upload from Django UploadedFile
        upload = fk.make_upload(uploaded_file)

        # Upload the file
        file_info = storage.upload(uploaded_file.name, upload)

        return JsonResponse({
            'success': True,
            'location': file_info.location,
            'size': file_info.size
        })
    except exc.FilesError as e:
        return JsonResponse({'error': str(e)}, status=500)

def download_view(request, filename):
    try:
        # Find and serve the file
        for loc in storage.scan():
            if loc == filename:
                file_info = storage.analyze(loc)
                content = storage.content(file_info)

                response = HttpResponse(content, content_type=file_info.content_type)
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

        return JsonResponse({'error': 'File not found'}, status=404)
    except exc.FilesError as e:
        return JsonResponse({'error': str(e)}, status=500)
```

## Security Considerations

### Input Validation

Always validate file inputs to prevent security vulnerabilities:

```python
import mimetypes
import os
from file_keeper import exc

def is_safe_file_type(filename, allowed_types):
    """Check if file type is allowed."""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type in allowed_types
    return False

def is_safe_file_size(upload, max_size_mb=10):
    """Check if file size is within limits."""
    return upload.size <= (max_size_mb * 1024 * 1024)

def safe_upload(storage, filename, upload, allowed_types, max_size_mb=10):
    """Safely upload a file with validation."""
    # Validate file type
    if not is_safe_file_type(filename, allowed_types):
        raise exc.FilesError(f"File type not allowed: {filename}")

    # Validate file size
    if not is_safe_file_size(upload, max_size_mb):
        raise exc.FilesError(f"File too large: {filename}")

    # Sanitize filename to prevent directory traversal
    safe_filename = os.path.basename(filename)

    return storage.upload(safe_filename, upload)

# Example usage
ALLOWED_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'text/plain',
    'application/pdf'
]

try:
    file_info = safe_upload(
        storage,
        "../../../etc/passwd",  # This would be sanitized
        upload,
        ALLOWED_TYPES,
        max_size_mb=5
    )
except exc.FilesError as e:
    print(f"Upload rejected: {e}")
```

## Monitoring and Logging

Implement proper monitoring for file operations:

```python
import logging
import time
from file_keeper import exc

logger = logging.getLogger(__name__)

class MonitoredStorage:
    def __init__(self, storage):
        self.storage = storage

    def upload(self, location, upload):
        start_time = time.time()
        try:
            result = self.storage.upload(location, upload)
            duration = time.time() - start_time
            logger.info(f"Upload successful: {location}, size: {upload.size}, duration: {duration:.2f}s")
            return result
        except exc.FilesError as e:
            duration = time.time() - start_time
            logger.error(f"Upload failed: {location}, duration: {duration:.2f}s, error: {e}")
            raise

    def content(self, file_data):
        start_time = time.time()
        try:
            result = self.storage.content(file_data)
            duration = time.time() - start_time
            logger.info(f"Content read successful: {file_data.location}, size: {len(result)}, duration: {duration:.2f}s")
            return result
        except exc.FilesError as e:
            duration = time.time() - start_time
            logger.error(f"Content read failed: {file_data.location}, duration: {duration:.2f}s, error: {e}")
            raise

    def __getattr__(self, name):
        # Delegate other methods to the wrapped storage
        return getattr(self.storage, name)

# Example usage
monitored_storage = MonitoredStorage(storage)
file_info = monitored_storage.upload("test.txt", upload)
content = monitored_storage.content(file_info)
```

## Conclusion

This tutorial covered advanced patterns for using file-keeper effectively:

1. **Performance**: Use streaming for large files and batch operations for multiple files
2. **Reliability**: Implement retry mechanisms and circuit breakers for external services
3. **Integration**: Connect file-keeper with popular web frameworks
4. **Security**: Validate inputs to prevent vulnerabilities
5. **Monitoring**: Track performance and errors for operational insight

These patterns will help you build robust, scalable applications with file-keeper.
