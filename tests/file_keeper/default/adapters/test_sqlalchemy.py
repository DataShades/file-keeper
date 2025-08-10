from __future__ import annotations

from typing import Any

import pytest
from faker import Faker

import file_keeper.default.adapters.sqlalchemy as sqlalchemy

from . import standard

Settings = sqlalchemy.Settings
Storage = sqlalchemy.SqlAlchemyStorage


@pytest.fixture
def storage(faker: Faker, storage_settings: dict[str, Any]):
    settings: dict[str, Any] = {
        "name": "test",
        "initialize": True,
        "db_url": "sqlite:///:memory:",
        "location_column": "location",
        "content_column": "content",
        "table_name": "file-keeper",
    }

    settings.update(storage_settings)
    return Storage(settings)


class TestSettings: ...


class TestStorage(standard.Standard): ...
