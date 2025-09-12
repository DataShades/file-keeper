from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from faker import Faker

try:
    import file_keeper.default.adapters.obstore as ob
except ImportError:
    pytest.skip("obstore is not installed", allow_module_level=True)

from . import standard

Settings = ob.Settings
Storage = ob.ObjectStoreStorage


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
                    "url": "memory:///",
                }
            )
        case "local":
            settings.update(
                {
                    "url": f"file://{str(tmp_path)}",
                }
            )

        case _:
            pytest.fail(f"Unexpected store {request.param}")

    settings.update(storage_settings)

    return Storage(settings)


class TestSettings:
    pass


@pytest.mark.parametrize("storage", ["memory", "local"], indirect=True)
class TestStorage(standard.Standard):
    pass
