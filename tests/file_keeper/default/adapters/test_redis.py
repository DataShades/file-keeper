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


@pytest.fixture
def storage(tmp_path: Path, storage_settings: dict[str, Any]):
    settings = {
        "name": "test",
        "bucket": str(tmp_path),
        "url": f"{REDIS_URL}/1",
    }
    settings.update(storage_settings)

    storage = Storage(settings)
    yield storage
    storage.settings.redis.flushall()


class TestSettings:
    def test_creation(self):
        cfg = Settings(bucket="test")
        conn: Any = cfg.redis.connection_pool.get_connection("0")
        assert conn.db == 0

    def test_custom_url(self):
        """Redis can be customized via `redis_url`"""
        cfg = Settings(bucket="test", url=f"{REDIS_URL}/1")
        conn: Any = cfg.redis.connection_pool.get_connection("0")
        assert conn.db == 1

    def test_custom_redis(self):
        """Existing connection can be used for settings."""
        url = f"{REDIS_URL}/2"
        conn = Redis.from_url(url)
        cfg = Settings(bucket="test", redis=conn)
        assert cfg.redis is conn


class TestUploaderUpload(standard.Uploader):
    pass


class TestUploaderMultipart(standard.Multiparter, standard.MultiparterWithUploaded):
    def test_refresh(self, faker: Faker, storage: Storage):
        """`multipart_refresh` synchronized filesize."""
        content: Any = faker.binary(10)
        data = storage.multipart_start(
            fk.FileData(fk.types.Location(faker.file_name()), size=len(content)),
        )
        storage.settings.redis.hset(storage.settings.bucket, data.location, content)

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
    pass


class TestManagerAnalyze(standard.Analyzer):
    pass


class TestStorage:
    pass
