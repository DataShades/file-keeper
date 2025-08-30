from __future__ import annotations

import dataclasses
import os
from typing import Any
from urllib.parse import urlparse

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.libcloud as lc

from . import standard

Settings = lc.Settings
Storage = lc.LibCloudStorage


@pytest.fixture
def storage(faker: Faker, storage_settings: dict[str, Any], request: pytest.FixtureRequest):
    match request.param:
        case "MINIO":
            endpoint = os.getenv("FILE_KEEPER_TEST_MINIO_ENDPOINT")
            if not endpoint:
                pytest.skip("MinIO is not configured")

            parsed_endpoint = urlparse(endpoint)

            settings: dict[str, Any] = {
                "name": "test",
                "provider": "MINIO",
                "key": os.getenv("FILE_KEEPER_TEST_MINIO_KEY"),
                "secret": os.getenv("FILE_KEEPER_TEST_MINIO_SECRET"),
                "container_name": "file-keeper",
                "initialize": True,
                "params": {
                    "host": parsed_endpoint.hostname,
                    "port": parsed_endpoint.port,
                    "secure": False,
                },
                "path": faker.file_path(extension=[]),
            }

        case "AZURITE":
            name = os.getenv("FILE_KEEPER_TEST_AZURITE_ACCOUNT_NAME")
            if not name:
                pytest.skip("Azurite is not configured")

            parsed_endpoint = urlparse(os.getenv("FILE_KEEPER_TEST_AZURITE_ACCOUNT_URL"))

            settings = {
                "name": "test",
                "provider": "AZURE_BLOBS",
                "key": name,
                "secret": os.getenv("FILE_KEEPER_TEST_AZURITE_ACCOUNT_KEY"),
                "container_name": os.getenv("FILE_KEEPER_TEST_AZURITE_CONTAINER_NAME"),
                "initialize": True,
                "params": {
                    "host": parsed_endpoint.hostname,
                    "port": parsed_endpoint.port,
                    "secure": False,
                },
                "path": faker.file_path(extension=[]),
            }

        case _:
            pytest.fail(f"Unexpected cloud provider {request.param}")

    settings.update(storage_settings)

    storage = Storage(settings)

    driver = storage.settings.driver
    for obj in storage.settings.container.list_objects():
        storage.settings.container.delete_object(obj)
    driver.delete_container(storage.settings.container)
    storage.settings.container = driver.create_container(storage.settings.container_name)

    return storage


@pytest.mark.parametrize("storage", ["MINIO", "AZURITE"], indirect=True)
class TestSettings:
    def test_initialize(self, storage: Storage):
        """Initialize flag controls container creation."""
        storage.settings.driver.delete_container(storage.settings.container)

        params = {field.name: getattr(storage.settings, field.name) for field in dataclasses.fields(storage.settings)}

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            storage.SettingsFactory.from_dict(dict(params, initialize=False, container=None))

        storage.SettingsFactory.from_dict(dict(params, initialize=True, container=None))


@pytest.mark.parametrize("storage", ["MINIO", "AZURITE"], indirect=True)
class TestStorage(standard.Standard): ...
