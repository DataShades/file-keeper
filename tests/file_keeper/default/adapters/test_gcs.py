from __future__ import annotations

import os
from typing import Any

import pytest
from faker import Faker
from google.auth.credentials import AnonymousCredentials

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
        "bucket": "file-keeper",
        "client_options": {"api_endpoint": endpoint},
    }

    if credentials_file := os.getenv("FILE_KEEPER_TEST_GCS_CREDENTIALS_FILE"):
        settings["credentials_file"] = credentials_file
    else:
        settings["credentials"] = AnonymousCredentials()

    settings.update(storage_settings)
    storage = Storage(settings)

    client = storage.settings.client

    bucket = client.bucket(storage.settings.bucket)
    for blob in bucket.list_blobs():  # pyright: ignore[reportUnknownVariableType]
        bucket.delete_blob(blob.name)

    return storage


class TestSettings: ...


class TestUploaderUpload(standard.Uploader):
    pass


class TestUploaderMultipart(standard.Multiparter):
    pass


class TestReader(standard.Reader):
    pass


class TestManagerCopy(standard.Copier):
    pass


class TestManagerMove(standard.Mover):
    pass


class TestManagerExists(standard.Exister):
    pass


class TestManagerRemove(standard.Remover):
    pass


class TestManagerScan(standard.Scanner):
    pass


class TestManagerAnalyze(standard.Analyzer):
    pass


class TestStorage: ...
