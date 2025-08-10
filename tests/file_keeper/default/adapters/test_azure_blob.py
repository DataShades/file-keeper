from __future__ import annotations

import dataclasses
import os
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.azure_blob as azure

from . import standard

Settings = azure.Settings
Storage = azure.AzureBlobStorage


@pytest.fixture
def storage(faker: Faker, storage_settings: dict[str, Any]):
    name = os.getenv("FILE_KEEPER_TEST_AZURITE_ACCOUNT_NAME")
    if not name:
        pytest.skip("Azurite is not configured")

    settings: dict[str, Any] = {
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


class TestSettings:
    def test_initialize(self, storage: Storage):
        """Initialize flag controls container creation."""
        storage.settings.container.delete_container()
        assert not storage.settings.container.exists()

        params = dataclasses.asdict(storage.settings)

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            storage.SettingsFactory.from_dict(dict(params, initialize=False))

        storage.SettingsFactory.from_dict(params)
        assert storage.settings.container.exists()


class TestStorage(standard.Standard): ...
