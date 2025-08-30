from __future__ import annotations

import dataclasses
import os
from typing import Any

import pytest
from faker import Faker
from google.auth.credentials import AnonymousCredentials
from typing_extensions import override

import file_keeper as fk
import file_keeper.default.adapters.gcs as gcs

from . import standard

Settings = gcs.Settings
Storage = gcs.GoogleCloudStorage


@pytest.fixture
def storage(faker: Faker, storage_settings: dict[str, Any]):
    endpoint = os.getenv("FILE_KEEPER_TEST_GCS_ENDPOINT")
    if not endpoint:
        pytest.skip("MinIO is not configured")

    settings: dict[str, Any] = {
        "name": "test",
        "project_id": "test",
        "path": faker.file_path(extension=[]),
        "initialize": True,
        "bucket_name": "file-keeper",
        "client_options": {"api_endpoint": endpoint},
    }

    if credentials_file := os.getenv("FILE_KEEPER_TEST_GCS_CREDENTIALS_FILE"):
        settings["credentials_file"] = credentials_file
    else:
        settings["credentials"] = AnonymousCredentials()

    settings.update(storage_settings)

    storage = Storage(settings)

    client = storage.settings.client

    bucket = client.bucket(storage.settings.bucket_name)
    for blob in bucket.list_blobs():  # pyright: ignore[reportUnknownVariableType]
        bucket.delete_blob(blob.name)

    return storage


class TestSettings:
    def test_initialize(self, storage: Storage):
        """Initialize flag controls container creation."""
        storage.settings.bucket.delete(True)
        assert not storage.settings.bucket.exists()

        params = {field.name: getattr(storage.settings, field.name) for field in dataclasses.fields(storage.settings)}

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            storage.SettingsFactory.from_dict(dict(params, initialize=False))

        storage.SettingsFactory.from_dict(dict(params, initialize=True))
        assert storage.settings.bucket.exists()


class TestStorage(standard.Standard):
    @override
    def test_signed_download(self, storage: fk.Storage, faker: Faker):
        if not storage.settings.credentials_file:  # pyright: ignore[reportAttributeAccessIssue]
            pytest.skip("Fake GCS does not support signed downloads without service credentials")
        super().test_signed_download(storage, faker)

    @override
    def test_signed_upload(self, storage: fk.Storage, faker: Faker):
        if not storage.settings.credentials_file:  # pyright: ignore[reportAttributeAccessIssue]
            pytest.skip("Fake GCS does not support signed uploads without service credentials")
        super().test_signed_upload(storage, faker)

    @override
    def test_signed_delete(self, storage: fk.Storage, faker: Faker):
        if not storage.settings.credentials_file:  # pyright: ignore[reportAttributeAccessIssue]
            pytest.skip("Fake GCS does not support signed removals without service credentials")
        super().test_signed_delete(storage, faker)

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE)
    def test_resumable_start_gcs_data(self, storage: fk.Storage, faker: Faker):
        """GCS-specific data is set on resumable start."""
        result = storage.resumable_start(fk.Location(faker.file_name()), faker.pyint(1))

        assert "gcs_resumable" in result.storage_data

        data = result.storage_data["gcs_resumable"]
        assert data["uploaded"] == 0
        assert data["origin"] is None

        origin = faker.url()
        result = storage.resumable_start(fk.Location(faker.file_name()), faker.pyint(1), origin=origin)
        assert result.storage_data["gcs_resumable"]["origin"] == origin

    @override
    @pytest.mark.xfail
    def test_resumable_refresh_without_changes(self, storage: fk.Storage, faker: Faker):
        super().test_resumable_refresh_without_changes(storage, faker)

    @override
    @pytest.mark.xfail
    def test_resumable_refresh(self, storage: fk.Storage, faker: Faker):
        super().test_resumable_refresh(storage, faker)

    @override
    @pytest.mark.xfail
    def test_resumable_refresh_missing(self, storage: fk.Storage, faker: Faker):
        super().test_resumable_refresh_missing(storage, faker)
