from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import file_keeper as fk
import file_keeper.default.adapters.zip as zip

from . import standard

Settings = zip.Settings
Storage = zip.ZipStorage


@pytest.fixture
def storage(tmp_path: Path, storage_settings: dict[str, Any]):
    settings = {"name": "test", "path": f"{tmp_path}/test.zip"}
    settings.update(storage_settings)

    return Storage(settings)


class TestSettings:
    def test_creation(self, tmp_path: Path):
        """Test how settings initialized with and without required option."""
        with pytest.raises(fk.exc.MissingStorageConfigurationError):
            Settings()

        Settings(path=str(tmp_path))


class TestStorage(standard.Standard): ...
