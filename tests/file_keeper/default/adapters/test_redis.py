from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from faker import Faker
from redis import Redis

import file_keeper as fk
import file_keeper.default.adapters.redis as redis

from . import standard

Settings = redis.Settings
Storage = redis.RedisStorage
REDIS_URL = "redis://localhost:6379"


@pytest.fixture()
def storage(tmp_path: Path, storage_settings: dict[str, Any]):
    settings = {
        "name": "test",
        "path": str(tmp_path),
        "redis_url": f"{REDIS_URL}/1",
    }
    settings.update(storage_settings)

    storage = Storage(settings)
    yield storage
    storage.settings.redis.flushall()


class TestSettings:
    def test_creation(self):
        cfg = Settings(path="test")
        conn: Any = cfg.redis.connection_pool.get_connection("0")
        assert conn.db == 0

    def test_custom_url(self):
        """Redis can be customized via `redis_url`"""
        cfg = Settings(path="test", redis_url=f"{REDIS_URL}/1")
        conn: Any = cfg.redis.connection_pool.get_connection("0")
        assert conn.db == 1

    def test_custom_redis(self):
        """Existing connection can be used for settings."""
        url = f"{REDIS_URL}/2"
        conn = Redis.from_url(url)
        cfg = Settings(path="test", redis=conn)
        assert cfg.redis is conn


class TestUploaderUpload(standard.Uploader):
    pass


class TestUploaderMultipart(standard.Multiparter, standard.MultiparterWithUploaded):
    def test_refresh(self, faker: Faker, storage: Storage):
        """`multipart_refresh` synchronized filesize."""
        content: Any = faker.binary(10)
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=len(content)),
        )
        storage.settings.redis.hset(storage.settings.path, data.location, content)

        data = storage.multipart_refresh(data)
        assert data.storage_data["uploaded"] == len(content)


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
    def test_scan(self, storage: Storage, faker: Faker):
        first = faker.file_name()
        second = faker.file_name()
        third = faker.file_name()

        storage.upload(first, fk.make_upload(b""))
        storage.upload(second, fk.make_upload(b""))

        storage.settings.redis.hset(storage.settings.path, third, "")

        discovered = set(storage.scan())

        assert discovered == {first, second, third}


class TestManagerAnalyze(standard.Analyzer):
    pass


class TestStorage:
    pass
