from __future__ import annotations

import dataclasses
from typing import Any

import pytest
import sqlalchemy as sa
from faker import Faker

import file_keeper as fk
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
        "path": faker.file_path(extension=[]),
    }

    settings.update(storage_settings)
    return Storage(settings)


class TestSettings:
    def test_initialize(self, storage: Storage):
        """Initialize flag controls container creation."""
        storage.settings.table.drop(storage.settings.engine)
        inspector = sa.inspect(storage.settings.engine)
        assert not inspector.has_table(storage.settings.table.name)

        params = {field.name: getattr(storage.settings, field.name) for field in dataclasses.fields(storage.settings)}

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            storage.SettingsFactory.from_dict(dict(params, initialize=False))

        storage.SettingsFactory.from_dict(dict(params, initialize=True))
        inspector = sa.inspect(storage.settings.engine)

        assert inspector.has_table(storage.settings.table.name)


class TestStorage(standard.Standard): ...
