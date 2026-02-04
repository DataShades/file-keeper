"""Custom Adapter Example.

This example demonstrates how to create custom storage adapters for file-keeper.
It shows the complete process of implementing a new storage backend.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import sqlite3
import tempfile
import time
from collections.abc import Iterable
from typing import Any

from typing_extensions import override

import file_keeper as fk
from file_keeper import Capability, FileData, Manager, Reader, Settings, Storage, Upload, Uploader, exc, types


# Example 1: SQLite-based Storage Adapter
@dataclasses.dataclass
class SQLiteSettings(Settings):
    """Settings for SQLite storage."""

    db_path: str = ":memory:"  # Use in-memory DB by default
    table_name: str = "files"


class SQLiteUploader(Uploader):
    """Uploader for SQLite storage."""

    capabilities = Capability.CREATE
    storage: SQLiteStorage

    @override
    def upload(self, location: types.Location, upload: Upload, extras: dict[str, Any]) -> FileData:
        """Upload file to SQLite database."""
        # Calculate hash while reading
        hashing_stream = upload.hashing_reader()
        content = hashing_stream.read()
        file_hash = hashing_stream.get_hash()

        # Insert into database
        cursor = self.storage.db.cursor()
        cursor.execute(
            f"""
            INSERT OR REPLACE INTO {self.storage.settings.table_name}
            (location, content, size, content_type, hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (str(location), content, upload.size, upload.content_type, file_hash, int(time.time())),
        )
        self.storage.db.commit()

        return FileData(location=location, size=upload.size, content_type=upload.content_type, hash=file_hash)


class SQLiteManager(Manager):
    """Manager for SQLite storage."""

    storage: SQLiteStorage
    capabilities = Capability.EXISTS | Capability.REMOVE | Capability.ANALYZE | Capability.REMOVE

    @override
    def exists(self, data: FileData, extras: dict[str, Any]) -> bool:
        """Check if file exists in database."""
        cursor = self.storage.db.cursor()
        cursor.execute(
            f"SELECT COUNT(*) FROM {self.storage.settings.table_name} WHERE location = ?", (str(data.location),)
        )
        count = cursor.fetchone()[0]
        return count > 0

    @override
    def analyze(self, location: types.Location, extras: dict[str, Any]) -> FileData:
        """Get file metadata from database."""
        cursor = self.storage.db.cursor()
        cursor.execute(
            f"""
            SELECT location, size, content_type, hash
            FROM {self.storage.settings.table_name}
            WHERE location = ?
        """,
            (str(location),),
        )

        row = cursor.fetchone()
        if not row:
            raise exc.MissingFileError(self.storage, str(location))

        location, size, content_type, file_hash = row
        return FileData(location=types.Location(location), size=size, content_type=content_type, hash=file_hash)

    @override
    def remove(self, data: FileData, extras: dict[str, Any]) -> bool:
        """Remove file from SQLite database."""
        cursor = self.storage.db.cursor()
        cursor.execute(f"DELETE FROM {self.storage.settings.table_name} WHERE location = ?", (str(data.location),))
        self.storage.db.commit()

        return cursor.rowcount > 0


class SQLiteReader(Reader):
    """Reader for SQLite storage."""

    storage: SQLiteStorage
    capabilities = Capability.STREAM

    @override
    def stream(self, data: FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        """Stream file content from database."""
        cursor = self.storage.db.cursor()
        cursor.execute(
            f"SELECT content FROM {self.storage.settings.table_name} WHERE location = ?", (str(data.location),)
        )

        row = cursor.fetchone()
        if not row:
            raise fk.exc.MissingFileError(self.storage, data.location)

        # Return content as iterable of bytes
        yield row[0]


class SQLiteStorage(Storage):
    """SQLite-based storage implementation."""

    settings: SQLiteSettings
    SettingsFactory = SQLiteSettings
    UploaderFactory = SQLiteUploader
    ManagerFactory = SQLiteManager
    ReaderFactory = SQLiteReader

    capabilities = Capability.CREATE | Capability.STREAM | Capability.EXISTS | Capability.REMOVE | Capability.ANALYZE

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)

        # Connect to database
        self.db = sqlite3.connect(self.settings.db_path, check_same_thread=False)

        # Create table if it doesn't exist
        self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.settings.table_name} (
                location TEXT PRIMARY KEY,
                content BLOB NOT NULL,
                size INTEGER NOT NULL,
                content_type TEXT NOT NULL,
                hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        self.db.commit()

    def __del__(self):
        """Close database connection."""
        if hasattr(self, "db"):
            self.db.close()


# Example 2: Encrypted File Storage Adapter
from cryptography.fernet import Fernet


@dataclasses.dataclass
class EncryptedSettings(Settings):
    """Settings for encrypted storage."""

    base_path: str = ""
    encryption_key: str = ""  # Will be generated if not provided
    _required_options = ["base_path"]


class EncryptedUploader(Uploader):
    """Uploader for encrypted storage."""

    storage: EncryptedStorage

    capabilities = Capability.CREATE

    @override
    def upload(self, location: types.Location, upload: Upload, extras: dict[str, Any]) -> FileData:
        """Upload encrypted file."""
        # Get raw content
        content = b"".join(upload.stream) if hasattr(upload.stream, "__iter__") else upload.stream.read()

        # Encrypt content
        cipher_suite = Fernet(self.storage.encryption_key.encode())
        encrypted_content = cipher_suite.encrypt(content)

        # Save to file
        full_path = os.path.join(self.storage.base_path, str(location))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(encrypted_content)

        # Calculate hash of original content (before encryption)
        original_hash = hashlib.md5(content).hexdigest()

        return FileData(
            location=location,
            size=len(encrypted_content),
            content_type=upload.content_type,
            hash=original_hash,  # Store hash of original content
        )


class EncryptedManager(Manager):
    """Manager for encrypted storage."""

    capabilities = Capability.EXISTS | Capability.REMOVE | Capability.ANALYZE | Capability.REMOVE
    storage: EncryptedStorage

    @override
    def exists(self, data: FileData, extras: dict[str, Any]) -> bool:
        """Check if encrypted file exists."""
        full_path = os.path.join(self.storage.base_path, str(data.location))
        return os.path.exists(full_path)

    @override
    def remove(self, data: FileData, extras: dict[str, Any]) -> bool:
        """Remove encrypted file."""
        full_path = os.path.join(self.storage.base_path, str(data.location))
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    @override
    def analyze(self, location: types.Location, extras: dict[str, Any]) -> FileData:
        """Analyze encrypted file (returns encrypted file info)."""
        full_path = os.path.join(self.storage.base_path, str(location))
        if not os.path.exists(full_path):
            raise exc.MissingFileError(self.storage, str(location))

        stat = os.stat(full_path)
        # Note: We can't get original content type or hash without decrypting
        return FileData(
            location=location,
            size=stat.st_size,
            content_type="application/octet-stream",  # Can't determine original type
            hash="",  # Can't determine original hash without decrypting
        )


class EncryptedReader(Reader):
    """Reader for encrypted storage."""

    capabilities = Capability.STREAM
    storage: EncryptedStorage

    @override
    def stream(self, data: FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        """Stream decrypted file content."""
        full_path = os.path.join(self.storage.base_path, str(data.location))
        if not os.path.exists(full_path):
            raise exc.MissingFileError(self.storage, str(data.location))

        # Read encrypted content
        with open(full_path, "rb") as f:
            encrypted_content = f.read()

        # Decrypt
        cipher_suite = Fernet(self.storage.encryption_key.encode())
        try:
            decrypted_content = cipher_suite.decrypt(encrypted_content)
        except Exception as e:
            raise exc.FilesError(f"Decryption failed: {str(e)}")

        # Return as iterable
        yield decrypted_content


class EncryptedStorage(Storage):
    """Encrypted file storage implementation."""

    settings: EncryptedSettings
    SettingsFactory = EncryptedSettings
    UploaderFactory = EncryptedUploader
    ManagerFactory = EncryptedManager
    ReaderFactory = EncryptedReader

    capabilities = Capability.CREATE | Capability.STREAM | Capability.EXISTS | Capability.REMOVE | Capability.ANALYZE

    def __init__(self, settings: dict[str, Any]):
        super().__init__(settings)
        self.base_path = self.settings.base_path
        self.encryption_key = self.settings.encryption_key

        # Generate key if not provided
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            # In a real implementation, you'd want to store this securely


def register_adapters():
    """Register the custom adapters with file-keeper."""
    fk.ext.setup()

    # Register SQLite adapter
    fk.adapters.register("file_keeper:sqlite", SQLiteStorage)

    # Register encrypted adapter
    fk.adapters.register("file_keeper:encrypted", EncryptedStorage)



def demonstrate_sqlite_adapter():
    """Demonstrate the SQLite adapter."""
    # Register adapters
    register_adapters()

    # Create SQLite storage
    storage = fk.make_storage(
        "sqlite_demo",
        {
            "type": "file_keeper:sqlite",
            "db_path": ":memory:",  # Use in-memory database
            "table_name": "demo_files",
        },
    )


    # Upload a file
    upload = fk.make_upload(b"Hello, SQLite storage!")
    file_info = storage.upload(fk.Location("hello.txt"), upload)

    # Read the file
    storage.content(file_info)

    # Check if file exists
    storage.exists(file_info)

    # Analyze file
    storage.analyze(fk.Location("hello.txt"))

    # Remove file
    if storage.supports(fk.Capability.REMOVE):
        storage.remove(file_info)

        # Check if it still exists
        storage.exists(file_info)



def demonstrate_encrypted_adapter():
    """Demonstrate the encrypted adapter."""
    # Create temporary directory for encrypted files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create encrypted storage
        storage = fk.make_storage(
            "encrypted_demo",
            {
                "type": "file_keeper:encrypted",
                "base_path": temp_dir,
                # encryption_key will be auto-generated
            },
        )


        # Upload a file
        upload = fk.make_upload(b"This is a secret message!")
        file_info = storage.upload(fk.Location("secret.txt"), upload)

        # Verify file is encrypted on disk
        file_path = os.path.join(temp_dir, "secret.txt")
        with open(file_path, "rb") as f:
            f.read()

        # Read the file (should be decrypted)
        storage.content(file_info)

        # Check if file exists
        storage.exists(file_info)

        # Remove file
        if storage.supports(fk.Capability.REMOVE):
            storage.remove(file_info)

            # Verify file is gone
            storage.exists(file_info)



def adapter_best_practices():
    """Show best practices for creating adapters."""
    practices = [
        "1. Define appropriate Settings with validation",
        "2. Implement only the capabilities your backend supports",
        "3. Handle errors appropriately with file-keeper's exception hierarchy",
        "4. Respect the storage path setting for security",
        "5. Use the provided services (Uploader, Manager, Reader) properly",
        "6. Test your adapter with the standard test suite",
        "7. Document the capabilities and limitations of your adapter",
        "8. Consider thread safety if your backend supports concurrent access",
        "9. Implement proper cleanup in __del__ or via context managers",
        "10. Follow the same interface contracts as built-in adapters",
    ]

    for _practice in practices:
        pass



def create_minimal_adapter():
    """Example of a minimal adapter implementation."""

    # A minimal in-memory adapter for demonstration
    class MinimalSettings(Settings):
        namespace: str = "default"

    class MinimalUploader(Uploader):
        capabilities = Capability.CREATE

        def upload(self, location: types.Location, upload: Upload, extras: dict[str, Any]) -> FileData:
            content = b"".join(upload.stream) if hasattr(upload.stream, "__iter__") else upload.stream.read()
            self.storage._data[str(location)] = {"content": content, "size": upload.size, "type": upload.content_type}

            return FileData(
                location=location,
                size=upload.size,
                content_type=upload.content_type,
                hash=hashlib.md5(content).hexdigest(),
            )

    class MinimalReader(Reader):
        capabilities = Capability.STREAM

        def stream(self, data: FileData, extras: dict[str, Any]) -> Iterable[bytes]:
            if str(data.location) not in self.storage._data:
                raise exc.MissingFileError(str(data.location))
            yield self.storage._data[str(data.location)]["content"]

    class MinimalStorage(Storage):
        SettingsFactory = MinimalSettings
        UploaderFactory = MinimalUploader
        ReaderFactory = MinimalReader
        # No Manager - so no EXISTS, REMOVE, etc. capabilities

        def __init__(self, settings: dict[str, Any]):
            super().__init__(settings)
            self._data = {}

    # Register the minimal adapter
    fk.adapters.register("file_keeper:minimal", MinimalStorage)

    # Test it
    storage = fk.make_storage("minimal", {"type": "file_keeper:minimal"})
    upload = fk.make_upload(b"minimal content")
    file_info = storage.upload("test.txt", upload)
    storage.content(file_info)


    # Show what capabilities it has



def main():
    """Main function demonstrating custom adapters."""
    demonstrate_sqlite_adapter()
    demonstrate_encrypted_adapter()
    adapter_best_practices()
    create_minimal_adapter()



if __name__ == "__main__":
    main()
