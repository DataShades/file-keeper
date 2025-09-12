from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from faker import Faker

try:
    import file_keeper.default.adapters.fsspec as fs
except ImportError:
    pytest.skip("fsspec is not installed", allow_module_level=True)

from . import standard

Settings = fs.Settings
Storage = fs.FsSpecStorage


@pytest.fixture
def storage(request: pytest.FixtureRequest, faker: Faker, tmp_path: Path, storage_settings: dict[str, Any]):
    settings: dict[str, Any] = {
        "name": "test",
        "path": faker.file_path(extension=[]),
    }

    match request.param:
        case "memory":
            settings.update(
                {
                    "protocol": "memory",
                }
            )
        case "local":
            settings.update(
                {
                    "protocol": "local",
                    "path": str(tmp_path),
                    "params": {
                        "auto_mkdir": True,
                    },
                }
            )

        case _:
            pytest.fail(f"Unexpected protocol {request.param}")

    settings.update(storage_settings)

    storage = Storage(settings)
    if request.param == "memory":
        storage.settings.fs.rm("/", True)
    return storage


class TestSettings:
    pass


@pytest.mark.parametrize("storage", ["memory", "local"], indirect=True)
class TestStorage(standard.Standard):
    pass
