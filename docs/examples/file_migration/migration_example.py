"""File Migration Example.

This script demonstrates how to migrate files between different storage backends
using file-keeper. It shows how to copy files from one storage to another,
handle errors during migration, and validate the migration process.
"""

from __future__ import annotations

import logging
import time

import file_keeper as fk
from file_keeper import exc

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def migrate_files(
    source_storage: fk.Storage, dest_storage: fk.Storage, file_filter=None, validate_after_migration: bool = True
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Migrate files from source storage to destination storage.

    Args:
        source_storage: Source storage to migrate from
        dest_storage: Destination storage to migrate to
        file_filter: Optional function to filter which files to migrate
        validate_after_migration: Whether to validate files after migration

    Returns:
        tuple of (successful_migrations, failed_migrations)
    """
    successful_migrations: list[tuple[str, str]] = []
    failed_migrations: list[tuple[str, str]] = []

    logger.info("Starting migration from %s to %s", source_storage, dest_storage)

    # Get all files from source
    for location in source_storage.scan():
        # Apply filter if provided
        if file_filter and not file_filter(location):
            logger.debug("Skipping %s due to filter", location)
            continue

        location = fk.Location(location)
        try:
            logger.info("Migrating: %s", location)

            # Get file info from source
            source_file_info = source_storage.analyze(location)
            logger.debug("Source file info: %s", source_file_info)

            # Get file content as upload object
            upload = source_storage.file_as_upload(source_file_info)

            # Upload to destination
            dest_file_info = dest_storage.upload(location, upload)
            logger.debug("Destination file info: %s", dest_file_info)

            # Validate if requested
            if validate_after_migration:
                validation_success = validate_migration(source_storage, dest_storage, source_file_info, dest_file_info)
                if not validation_success:
                    logger.warning("Validation failed for %s, removing from destination", location)
                    if dest_storage.supports(fk.Capability.REMOVE):
                        dest_storage.remove(dest_file_info)
                    msg = f"Validation failed for {location}"
                    raise fk.exc.FilesError(msg)

            successful_migrations.append((location, "Success"))
            logger.info(f"Successfully migrated: {location}")

        except exc.FilesError as e:
            logger.exception("Failed to migrate %s", location)
            failed_migrations.append((location, str(e)))
        except Exception as e:
            logger.exception("Unexpected error migrating %s", location)
            failed_migrations.append((location, str(e)))

    logger.info("Migration completed. Success: %s, Failed: %s", len(successful_migrations), len(failed_migrations))
    return successful_migrations, failed_migrations


def validate_migration(
    source_storage: fk.Storage, dest_storage: fk.Storage, source_file_info: fk.FileData, dest_file_info: fk.FileData
) -> bool:
    """Validate that the file was correctly migrated.

    Args:
        source_storage: Original storage
        dest_storage: Destination storage
        source_file_info: File info from source
        dest_file_info: File info from destination

    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Compare file sizes
        if source_file_info.size != dest_file_info.size:
            logger.error(f"Size mismatch: {source_file_info.size} vs {dest_file_info.size}")
            return False

        # Compare hashes if available
        if source_file_info.hash and dest_file_info.hash and source_file_info.hash != dest_file_info.hash:
            logger.error(f"Hash mismatch: {source_file_info.hash} vs {dest_file_info.hash}")
            return False

        # Compare content types
        if source_file_info.content_type != dest_file_info.content_type:
            logger.warning(f"Content type differs: {source_file_info.content_type} vs {dest_file_info.content_type}")

        # Optionally compare actual content (be careful with large files)
        source_content = source_storage.content(source_file_info)
        dest_content = dest_storage.content(dest_file_info)

        if source_content != dest_content:
            logger.error("Content mismatch detected")
            return False

        logger.debug(f"Validation passed for {source_file_info.location}")
        return True

    except exc.FilesError:
        logger.exception("Validation error")
        return False


def create_sample_files(storage: fk.Storage, file_count: int = 5) -> list[fk.Location]:
    """Create sample files for testing migration."""
    locations: list[fk.Location] = []

    for i in range(file_count):
        filename = fk.Location(f"sample_file_{i}.txt")
        content = f"This is sample content for file {i}\nCreated at {time.time()}\n".encode()

        upload = fk.make_upload(content)
        file_info = storage.upload(filename, upload)
        locations.append(file_info.location)
        logger.info("Created sample file: %s", filename)

    return locations


def main():
    """Main function demonstrating file migration."""
    # Create source storage (memory for this example)
    source_storage = fk.make_storage("source", {"type": "file_keeper:memory"})

    # Create destination storage (filesystem for this example)
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        dest_storage = fk.make_storage("destination", {"type": "file_keeper:fs", "path": temp_dir, "initialize": True})


        # Create sample files in source storage
        create_sample_files(source_storage, 3)

        # Show source files
        for location in source_storage.scan():
            source_storage.analyze(location)

        # Define a filter function to only migrate .txt files
        def txt_filter(location: str) -> bool:
            return location.endswith(".txt")

        # Perform migration
        successful, failed = migrate_files(
            source_storage, dest_storage, file_filter=txt_filter, validate_after_migration=True
        )

        # Report results
        for location, _status in successful:
            pass

        for location, _error in failed:
            pass

        # Show destination files
        for location in dest_storage.scan():
            dest_storage.analyze(location)



def migrate_between_cloud_storages():
    """Example of migrating between cloud storage services."""
    # Example configuration for cloud migrations
    # NOTE: These are examples - you would need real credentials




def selective_migration_example():
    """Example of selective migration based on criteria."""
    # Create sample storage
    storage1 = fk.make_storage("source", {"type": "file_keeper:memory"})
    storage2 = fk.make_storage("dest", {"type": "file_keeper:memory"})

    # Create various types of files
    files_to_create = [
        ("document.pdf", b"PDF content", "application/pdf"),
        ("image.png", b"PNG content", "image/png"),
        ("data.csv", b"CSV content", "text/csv"),
        ("script.sh", b"Shell script", "text/x-shellscript"),
    ]

    for filename, content, _content_type in files_to_create:
        # Create upload with specific content type
        upload = fk.make_upload(content)
        storage1.upload(filename, upload)

    # Migrate only safe file types
    def safe_file_filter(location: str) -> bool:
        safe_extensions = [".pdf", ".png", ".csv", ".txt", ".jpg", ".jpeg", ".gif"]
        return any(location.lower().endswith(ext) for ext in safe_extensions)

    successful, failed = migrate_files(storage1, storage2, file_filter=safe_file_filter)


    for _location in storage2.scan():
        pass


if __name__ == "__main__":
    main()
    migrate_between_cloud_storages()
    selective_migration_example()
