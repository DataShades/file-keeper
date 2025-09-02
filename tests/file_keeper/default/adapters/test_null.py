from __future__ import annotations

import hashlib
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.null as null

Settings = null.Settings
Storage = null.NullStorage


@pytest.fixture
def storage(storage_settings: dict[str, Any]):
    settings = {}
    settings.update(storage_settings)

    return Storage(settings)


class TestStorage:
    def test_upload_computes_hash(self, storage: fk.Storage, faker: Faker):
        """Upload uses hash of an empty file."""
        content = faker.binary(100)
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))

        expected = hashlib.md5().hexdigest()
        assert data.hash == expected

    def test_upload_sets_zero_size_and_default_content_type(self, storage: fk.Storage, faker: Faker):
        """Content of upload ignored and size/content_type of result set to default values."""
        content = faker.binary(100)
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))

        assert data.size == 0
        assert data.content_type == "application/octet-stream"

    def test_multipart_chain_works_without_errors(self, storage: fk.Storage, faker: Faker):
        """Multipart methods work without errors."""
        location = fk.Location(faker.file_name())
        size = faker.random_int(0)

        data = storage.multipart_start(location, size)
        assert data.location == location
        assert data.size == size

        data = storage.multipart_refresh(data)
        assert data.location == location
        assert data.size == size

        content = faker.binary(100)
        upload = fk.make_upload(content)
        data = storage.multipart_update(data, upload, 0)
        assert data.location == location
        assert data.size == size

        data = storage.multipart_complete(data)
        assert data.location == location
        assert data.size == size

        removed = storage.multipart_remove(data)
        assert not removed

    def test_resumable_chain_works_without_errors(self, storage: fk.Storage, faker: Faker):
        """Resumable methods work without errors."""
        location = fk.Location(faker.file_name())
        size = faker.random_int(0)

        data = storage.resumable_start(location, size)
        assert data.location == location
        assert data.size == size

        data = storage.resumable_refresh(data)
        assert data.location == location
        assert data.size == size

        content = faker.binary(100)
        upload = fk.make_upload(content)
        data = storage.resumable_resume(data, upload)
        assert data.location == location
        assert data.size == size

        removed = storage.resumable_remove(data)
        assert not removed

    def test_remove_always_returns_false(self, storage: fk.Storage, faker: Faker):
        """Remove always returns false."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(location)

        removed = storage.remove(data)
        assert not removed

    def test_exists_always_returns_false(self, storage: fk.Storage, faker: Faker):
        """Exists always returns false."""
        location = fk.Location(faker.file_name())

        exists = storage.exists(fk.FileData(location))
        assert not exists

    def test_compose_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """Compose always returns FileData with given location."""
        location = fk.Location(faker.file_name())
        datas = [fk.FileData(fk.Location(faker.file_name())) for _ in range(3)]

        result = storage.compose(location, datas)
        assert result.location == location
        assert result.size == 0
        assert result.content_type == "application/octet-stream"
        assert result.hash == ""

    def test_append_always_returns_data(self, storage: fk.Storage, faker: Faker):
        """Append always returns given FileData."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(location)

        content = faker.binary(100)
        upload = fk.make_upload(content)

        result = storage.append(data, upload)
        assert result.location == location
        assert result.size == 0
        assert result.content_type == "application/octet-stream"
        assert result.hash == ""

    def test_copy_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """Copy always returns FileData with given location."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(fk.Location(faker.file_name()))

        result = storage.copy(location, data)
        assert result.location == location
        assert result.size == 0
        assert result.content_type == "application/octet-stream"
        assert result.hash == ""

    def test_move_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """Move always returns FileData with given location."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(fk.Location(faker.file_name()))

        result = storage.move(location, data)
        assert result.location == location
        assert result.size == 0
        assert result.content_type == "application/octet-stream"
        assert result.hash == ""

    def test_scan_always_returns_empty_list(self, storage: fk.Storage):
        """Scan always returns empty list."""
        results = list(storage.scan())
        assert results == []

    def test_analyze_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """Analyze always returns FileData with given location."""
        location = fk.Location(faker.file_name())

        result = storage.analyze(location)
        assert result.location == location
        assert result.size == 0
        assert result.content_type == "application/octet-stream"
        assert result.hash == ""

    def test_signed_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """Signed always returns given location."""
        location = fk.Location(faker.file_name())

        result = storage.signed("download", 60, location)
        assert result == location

    def test_stream_always_returns_empty_iterator(self, storage: fk.Storage, faker: Faker):
        """Stream always returns empty iterator."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(location)

        result = list(storage.stream(data))
        assert result == []

    def test_range_always_returns_empty_iterator(self, storage: fk.Storage, faker: Faker):
        """Range always returns empty iterator."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(location)

        result = list(storage.range(data, 0, 10))
        assert result == []

    def test_permanent_link_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """Permanent link always returns location."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(location)

        result = storage.permanent_link(data)
        assert result == location

    def test_temporal_link_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """Temporal link always returns location."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(location)

        result = storage.temporal_link(data, 60)
        assert result == location

    def test_one_time_link_always_returns_location(self, storage: fk.Storage, faker: Faker):
        """One-time link always returns location."""
        location = fk.Location(faker.file_name())
        data = fk.FileData(location)

        result = storage.one_time_link(data)
        assert result == location
