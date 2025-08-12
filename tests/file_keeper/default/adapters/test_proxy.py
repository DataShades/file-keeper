from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.proxy as proxy

Settings = proxy.Settings
Storage = proxy.ProxyStorage


@pytest.fixture
def storage(storage_settings: dict[str, Any]):
    settings = {"options": {"type": "file_keeper:memory"}}
    settings.update(storage_settings)

    return Storage(settings)


class TestSettings:
    def test_creation(self, tmp_path: Path): ...


class TestStorage:
    def test_basic(self, storage: fk.Storage, faker: Faker):
        adapter = type(fk.make_storage("memory", {"type": "file_keeper:memory"}))  # pyright: ignore[reportUnknownVariableType]
        assert isinstance(storage.proxy_settings.storage, adapter)  # pyright: ignore[reportAttributeAccessIssue]

        assert storage.settings is storage.proxy_settings.storage.settings  # pyright: ignore[reportAttributeAccessIssue]

        content = faker.binary(100)
        info = storage.upload(fk.Location("test"), fk.make_upload(content))

        assert storage.content(info) == content
        assert storage.proxy_settings.storage.content(info) == content  # pyright: ignore[reportAttributeAccessIssue]
