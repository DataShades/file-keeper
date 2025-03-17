from __future__ import annotations

from typing import Any

from faker import Faker

import file_keeper as fk


class Source:
    location: str = ""
    size: int = 0
    content_type: str = ""
    hash: Any = ""
    storage_data: dict[str, Any] = {}
    number: int = 42


def test_from_dict(faker: Faker):
    location = fk.types.Location(faker.file_path())
    data = fk.BaseData.from_dict({"location": location, "number": 42})
    assert data == fk.BaseData(location=location)


def test_from_object(faker: Faker):
    location = fk.types.Location(faker.file_path())
    source = Source()
    source.location = location

    data = fk.BaseData.from_object(source)
    assert data == fk.BaseData(location=location)


def test_into_object(faker: Faker):
    location = fk.types.Location(faker.file_path())
    data = fk.BaseData(location=location)
    source = Source()

    data.into_object(source)

    assert source.location == data.location
    assert source.size == data.size
    assert source.hash == data.hash
    assert source.content_type == data.content_type
    assert source.storage_data == data.storage_data
