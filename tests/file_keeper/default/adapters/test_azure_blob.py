from __future__ import annotations

import os
from typing import Any

import pytest
from faker import Faker

import file_keeper.default.adapters.azure_blob as azure

from . import standard

Settings = azure.Settings
Storage = azure.AzureBlobStorage


@pytest.fixture
def storage(faker: Faker, storage_settings: dict[str, Any]):
    name = os.getenv("FILE_KEEPER_TEST_AZURITE_ACCOUNT_NAME")
    if not name:
        pytest.skip("Azurite is not configured")

    settings = {
        "name": "test",
        "path": faker.file_path(extension=[]),
        "account_name": name,
        "account_key": os.getenv("FILE_KEEPER_TEST_AZURITE_ACCOUNT_KEY"),
        "container_name": os.getenv("FILE_KEEPER_TEST_AZURITE_CONTAINER_NAME"),
        "account_url": os.getenv("FILE_KEEPER_TEST_AZURITE_ACCOUNT_URL"),
        "initialize": True,
    }
    settings.update(storage_settings)

    storage = Storage(settings)
    if storage.settings.container.exists():
        storage.settings.container.delete_container()

    storage.settings.container.create_container()

    return storage


class TestSettings: ...


class TestUploaderUpload(standard.Uploader):
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
