from __future__ import annotations

import dataclasses
import os
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.s3 as s3

from . import standard

Settings = s3.Settings
Storage = s3.S3Storage


@pytest.fixture
def storage(faker: Faker, storage_settings: dict[str, Any]):
    endpoint = os.getenv("FILE_KEEPER_TEST_MINIO_ENDPOINT")
    if not endpoint:
        pytest.skip("MinIO is not configured")

    settings: dict[str, Any] = {
        "name": "test",
        "bucket": "file-keeper",
        "path": faker.file_path(extension=[]),
        "key": os.getenv("FILE_KEEPER_TEST_MINIO_KEY"),
        "secret": os.getenv("FILE_KEEPER_TEST_MINIO_SECRET"),
        "endpoint": endpoint,
        "initialize": True,
    }
    settings.update(storage_settings)

    storage = Storage(settings)

    client = storage.settings.client

    result = client.list_objects_v2(Bucket=storage.settings.bucket)
    if items := result.get("Contents"):
        keys = [{"Key": obj["Key"]} for obj in items]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        client.delete_objects(Bucket=storage.settings.bucket, Delete={"Objects": keys})  # pyright: ignore[reportArgumentType]

    return storage


class TestSettings:
    def test_initialize(self, storage: Storage):
        """Initialize flag controls container creation."""
        storage.settings.client.delete_bucket(Bucket=storage.settings.bucket)

        params = {field.name: getattr(storage.settings, field.name) for field in dataclasses.fields(storage.settings)}

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            storage.SettingsFactory.from_dict(dict(params, initialize=False))

        storage.SettingsFactory.from_dict(dict(params, initialize=True))
        assert storage.settings.client.head_bucket(Bucket=storage.settings.bucket)


class TestStorage(standard.Standard): ...
