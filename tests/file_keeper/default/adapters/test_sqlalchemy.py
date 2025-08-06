from __future__ import annotations

import os
from typing import Any

import pytest
from faker import Faker
from google.auth.credentials import AnonymousCredentials

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
    storage = Storage(settings)

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
