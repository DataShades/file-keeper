from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.fs as fs

from . import standard

Settings = fs.Settings
Storage = fs.FsStorage


@pytest.fixture
def storage(tmp_path: Path, storage_settings: dict[str, Any]):
    settings = {"name": "test", "path": str(tmp_path)}
    settings.update(storage_settings)

    return Storage(settings)


class TestSettings:
    def test_initialize(self, storage: Storage, tmp_path: Path, faker: Faker):
        """Initialize flag controls path creation."""
        subpath = faker.file_path(absolute=False, extension="")
        path = os.path.join(tmp_path, subpath)

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            storage.SettingsFactory(path=path)

        storage.SettingsFactory(path=path, initialize=True)
        assert os.path.exists(path)

        # if path exists, settings do not require `initialize` flag
        storage.SettingsFactory(path=path)


class TestStorage(standard.Standard): ...
