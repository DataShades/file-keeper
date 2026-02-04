# Batch Processing Example

This example demonstrates how to efficiently process multiple files in batch using file-keeper.

## Overview

This script shows:

- Batch uploading of multiple files
- Parallel processing of file operations
- Performance comparison between parallel and sequential processing
- Advanced batch operations with filtering and grouping
- Error handling in batch operations

## Prerequisites

- Python 3.10+
- file-keeper library

## Installation

```bash
pip install file-keeper
```

## Usage

### Run the basic batch processing example:
```bash
python batch_example.py
```

This will:

1. Create sample files
2. Demonstrate batch upload operations
3. Show filtering and metadata extraction
4. Compare parallel vs sequential processing
5. Demonstrate advanced batch operations

## Key Features Demonstrated

### 1. Basic Batch Upload
```python
from batch_example import BatchProcessor

processor = BatchProcessor(storage)
files_to_upload = [
    ("file1.txt", b"content1"),
    ("file2.txt", b"content2"),
    ("file3.txt", b"content3"),
]

results = processor.upload_batch(files_to_upload)
```

### 2. Parallel Processing
```python
# Process multiple files in parallel
processor = BatchProcessor(storage, max_workers=4)
results = processor.process_batch(my_operation, file_locations)
```

### 3. Batch Downloads
```python
# Download multiple files efficiently
contents = processor.download_batch(locations)
```

### 4. Batch Deletion
```python
# Delete multiple files in batch
results = processor.delete_batch(locations)
```

## Performance Optimization

The example demonstrates how parallel processing can significantly improve performance:

```python
# Sequential processing
start_time = time.time()
for location in locations:
    process_file_sequential(storage, location)
sequential_time = time.time() - start_time

# Parallel processing
start_time = time.time()
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_file_parallel, storage, loc) for loc in locations]
    for future in futures:
        future.result()
parallel_time = time.time() - start_time

print(f"Speedup: {sequential_time/parallel_time:.2f}x")
```

## Error Handling

Batch operations include comprehensive error handling:

```python
def handle_batch_errors(results):
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    for result in failed:
        print(f"Error processing {result.location}: {result.error}")
```

## Real-World Use Cases

### 1. Bulk File Import
```python
def import_bulk_files(storage, file_paths):
    files_to_upload = []
    for path in file_paths:
        with open(path, 'rb') as f:
            content = f.read()
        files_to_upload.append((Path(path).name, content))

    processor = BatchProcessor(storage)
    return processor.upload_batch(files_to_upload)
```

### 2. Media Processing Pipeline
```python
def process_media_pipeline(storage):
    # Get all image files
    image_files = filter_files_by_criteria(
        storage,
        lambda info: info.content_type.startswith('image/')
    )

    # Process images in parallel
    processor = BatchProcessor(storage)
    results = processor.process_batch(resize_image, image_files)

    return results
```

### 3. Data Migration
```python
def migrate_data_batch(source_storage, dest_storage, batch_size=100):
    all_files = list(source_storage.scan())

    for i in range(0, len(all_files), batch_size):
        batch = all_files[i:i+batch_size]

        # Process batch
        processor = BatchProcessor(source_storage)
        contents = processor.download_batch(batch)

        # Upload to destination
        dest_processor = BatchProcessor(dest_storage)
        upload_batch = [(loc, contents[loc]) for loc in batch if loc in contents]
        results = dest_processor.upload_batch(upload_batch)

        print(f"Processed batch {i//batch_size + 1}/{(len(all_files)-1)//batch_size + 1}")
```

## Best Practices

1. **Use appropriate worker counts**: Match the number of workers to your storage backend's capabilities
2. **Handle errors gracefully**: Always check batch operation results
3. **Monitor resource usage**: Batch operations can consume significant memory
4. **Validate results**: Ensure batch operations completed successfully
5. **Use filters**: Pre-filter files to reduce unnecessary processing

## Performance Considerations

- For I/O-bound operations, parallel processing provides significant speedups
- For CPU-bound operations, consider using multiprocessing instead of threading
- Monitor memory usage when processing large batches
- Consider using streaming for very large files to avoid memory issues
