"""Batch Processing Example.

This example demonstrates how to efficiently process multiple files in batch
using file-keeper. It shows bulk operations, parallel processing, and
performance optimization techniques.
"""

from __future__ import annotations

import concurrent.futures
import logging
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import file_keeper as fk
from file_keeper import Capability, exc

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of a batch operation."""

    success: bool
    location: str
    error: str | None = None
    file_info: fk.FileData | None = None


class BatchProcessor:
    """Handles batch operations on file-keeper storage."""

    def __init__(self, storage: fk.Storage, max_workers: int = 4):
        self.storage = storage
        self.max_workers = max_workers
        self.lock = threading.Lock()

    def upload_batch(self, files: list[tuple[Any]]) -> list[BatchResult]:
        """Upload multiple files in batch.

        Args:
            files: list of (location, content) tuples

        Returns:
            list of BatchResult objects
        """
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all upload tasks
            future_to_file = {
                executor.submit(self._upload_single, location, content): (location, content)
                for location, content in files
            }

            # Collect results
            for future in concurrent.futures.as_completed(future_to_file):
                location, content = future_to_file[future]
                try:
                    file_info = future.result()
                    results.append(BatchResult(True, location, file_info=file_info))
                    logger.info(f"Uploaded: {location}")
                except Exception as e:
                    results.append(BatchResult(False, location, error=str(e)))
                    logger.exception(f"Failed to upload {location}: {e}")

        return results

    def _upload_single(self, location: str, content) -> fk.FileData:
        """Upload a single file."""
        upload = fk.make_upload(content)
        return self.storage.upload(location, upload)

    def process_batch(self, operation: Callable, locations: list[str]) -> list[BatchResult]:
        """Apply an operation to multiple files in batch.

        Args:
            operation: Function that takes (storage, file_info) and returns result
            locations: list of file locations to process

        Returns:
            list of BatchResult objects
        """
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Get file infos first
            file_infos = []
            for location in locations:
                try:
                    file_info = self.storage.analyze(location)
                    file_infos.append((location, file_info))
                except exc.MissingFileError:
                    results.append(BatchResult(False, location, error="File not found"))

            # Submit processing tasks
            future_to_location = {
                executor.submit(operation, self.storage, file_info): location for location, file_info in file_infos
            }

            # Collect results
            for future in concurrent.futures.as_completed(future_to_location):
                location = future_to_location[future]
                try:
                    future.result()
                    results.append(BatchResult(True, location))
                    logger.info(f"Processed: {location}")
                except Exception as e:
                    results.append(BatchResult(False, location, error=str(e)))
                    logger.exception(f"Failed to process {location}: {e}")

        return results

    def delete_batch(self, locations: list[str]) -> list[BatchResult]:
        """Delete multiple files in batch."""
        if not self.storage.supports(Capability.REMOVE):
            raise exc.UnsupportedOperationError("REMOVE", self.storage)

        def delete_op(storage, file_info):
            return storage.remove(file_info)

        return self.process_batch(delete_op, locations)

    def download_batch(self, locations: list[str]) -> dict[str, bytes]:
        """Download multiple files in batch."""
        results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit download tasks
            future_to_location = {executor.submit(self._download_single, location): location for location in locations}

            # Collect results
            for future in concurrent.futures.as_completed(future_to_location):
                location = future_to_location[future]
                try:
                    content = future.result()
                    results[location] = content
                    logger.info(f"Downloaded: {location}")
                except Exception as e:
                    logger.exception(f"Failed to download {location}: {e}")

        return results

    def _download_single(self, location: str) -> bytes:
        """Download a single file."""
        file_info = self.storage.analyze(location)
        return self.storage.content(file_info)


def create_sample_files(storage: fk.Storage, count: int = 10) -> list[str]:
    """Create sample files for batch processing."""
    locations = []

    for i in range(count):
        location = f"batch_file_{i:03d}.txt"
        content = f"Sample content for file {i}\nGenerated at {time.time()}\n".encode()

        upload = fk.make_upload(content)
        storage.upload(location, upload)
        locations.append(location)
        logger.info(f"Created: {location}")

    return locations


def process_large_files_batch(storage: fk.Storage, locations: list[str]) -> list[dict[str, Any]]:
    """Process large files with additional metadata extraction."""
    results = []

    for location in locations:
        try:
            file_info = storage.analyze(location)
            content = storage.content(file_info)

            # Extract metadata
            metadata = {
                "location": location,
                "size": file_info.size,
                "content_type": file_info.content_type,
                "char_count": len(content),
                "line_count": len(content.split(b"\\n")),
                "word_count": len(content.split()),
                "hash": file_info.hash,
            }

            results.append(metadata)
            logger.info(f"Processed metadata for: {location}")

        except Exception as e:
            logger.exception(f"Failed to process {location}: {e}")
            results.append({"location": location, "error": str(e)})

    return results


def filter_files_by_criteria(storage: fk.Storage, criteria_fn: Callable) -> list[str]:
    """Filter files based on custom criteria."""
    matching_locations = []

    for location in storage.scan():
        try:
            file_info = storage.analyze(location)
            if criteria_fn(file_info):
                matching_locations.append(location)
        except exc.MissingFileError:
            continue  # File disappeared between scan and analyze

    return matching_locations


def main():
    """Main function demonstrating batch processing."""
    # Create storage for the example
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = fk.make_storage("batch_example", {"type": "file_keeper:fs", "path": temp_dir, "initialize": True})


        # Create sample files
        create_sample_files(storage, 5)

        # Show all files
        for location in storage.scan():
            storage.analyze(location)

        # Batch upload example
        new_files = [
            ("new_file_1.txt", b"Content of new file 1"),
            ("new_file_2.txt", b"Content of new file 2"),
            ("new_file_3.txt", b"Content of new file 3"),
        ]

        processor = BatchProcessor(storage)
        upload_results = processor.upload_batch(new_files)

        for _result in upload_results:
            pass

        # Filter files by size (larger than 20 bytes)
        filter_files_by_criteria(storage, lambda info: info.size > 20)

        # Process files in batch to extract metadata
        metadata_results = process_large_files_batch(storage, list(storage.scan()))

        for meta in metadata_results[:3]:
            if "error" not in meta:
                pass

        # Batch deletion example
        files_to_delete = [f for f in storage.scan() if f.startswith("new_file")]

        delete_results = processor.delete_batch(files_to_delete)

        for _result in delete_results:
            pass

        # Show remaining files
        for location in storage.scan():
            storage.analyze(location)



def parallel_vs_sequential_demo():
    """Demonstrate the performance difference between parallel and sequential processing."""
    # Create storage
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = fk.make_storage("perf_demo", {"type": "file_keeper:fs", "path": temp_dir, "initialize": True})

        # Create many sample files
        sample_files = create_sample_files(storage, 20)

        # Sequential processing time
        start_time = time.time()
        process_large_files_batch(storage, sample_files[:5])  # Just first 5 for demo
        time.time() - start_time

        # Parallel processing time
        BatchProcessor(storage, max_workers=4)
        start_time = time.time()

        # For parallel demo, we'll process metadata extraction differently
        parallel_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_location = {
                executor.submit(process_single_file_metadata, storage, location): location
                for location in sample_files[:5]
            }

            for future in concurrent.futures.as_completed(future_to_location):
                result = future.result()
                parallel_results.append(result)

        time.time() - start_time



def process_single_file_metadata(storage, location):
    """Helper function for parallel processing demo."""
    try:
        file_info = storage.analyze(location)
        content = storage.content(file_info)

        return {
            "location": location,
            "size": file_info.size,
            "char_count": len(content),
        }
    except Exception as e:
        return {"location": location, "error": str(e)}


def advanced_batch_operations():
    """Example of advanced batch operations."""
    # Create memory storage for this example
    storage = fk.make_storage("advanced", {"type": "file_keeper:memory"})

    # Create various types of files
    files_to_create = [
        ("image1.jpg", b"JPEG content", "image/jpeg"),
        ("image2.png", b"PNG content", "image/png"),
        ("doc1.pdf", b"PDF content", "application/pdf"),
        ("text1.txt", b"Text content", "text/plain"),
        ("text2.txt", b"More text", "text/plain"),
    ]

    for filename, content, content_type in files_to_create:
        # Create upload with specific content type
        upload = fk.make_upload(content)
        storage.upload(filename, upload)

    # Group files by content type
    content_type_groups = {}
    for location in storage.scan():
        file_info = storage.analyze(location)
        content_type = file_info.content_type

        if content_type not in content_type_groups:
            content_type_groups[content_type] = []
        content_type_groups[content_type].append(location)

    for content_type in content_type_groups:
        pass

    # Process each group differently
    BatchProcessor(storage)

    # Process images
    image_files = content_type_groups.get("image/jpeg", []) + content_type_groups.get("image/png", [])
    if image_files:
        # Could resize, optimize, etc.
        for _img_file in image_files:
            pass

    # Process documents
    doc_files = content_type_groups.get("application/pdf", [])
    if doc_files:
        # Could extract text, generate thumbnails, etc.
        for _doc_file in doc_files:
            pass


if __name__ == "__main__":
    main()
    parallel_vs_sequential_demo()
    advanced_batch_operations()
