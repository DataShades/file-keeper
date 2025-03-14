from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from redis import Redis
import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.redis as redis
from . import standard

Settings = redis.Settings
Storage = redis.RedisStorage
REDIS_URL = "redis://localhost:6379"


@pytest.fixture()
def storage(tmp_path: Path, request: pytest.FixtureRequest):
    settings = {
        "name": "test",
        "path": str(tmp_path),
        "redis_url": f"{REDIS_URL}/1",
    }
    marks: Any = request.node.iter_markers("fk_storage_option")
    for mark in marks:
        settings[mark.args[0]] = mark.args[1]

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


class TestUploaderMultipart(standard.Multiparter):
    def test_initialization(self, storage: fk.Storage, faker: Faker):
        """`multipart_start` creates an empty file."""
        size = faker.pyint(0, storage.settings.max_size)
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=size),
        )
        assert data.size == size
        assert data.storage_data["uploaded"] == 0
        assert storage.content(fk.FileData(data.location)) == b""

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

    def test_update(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` appends parts by default."""
        size = 100
        step = size // 10

        content = faker.binary(size)
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=size),
        )

        for pos in range(0, size, step):
            data = storage.multipart_update(
                data,
                upload=fk.make_upload(content[pos : pos + step]),
            )
            assert data.size == size
            assert data.storage_data["uploaded"] == min(size, pos + step)

    def test_update_wihtout_uploaded(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` appends parts by default."""
        size = 100
        step = size // 10

        content = faker.binary(size)
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=size),
        )

        for pos in range(0, size, step):
            data = storage.multipart_update(
                data,
                upload=fk.make_upload(content[pos : pos + step]),
            )
            assert data.size == size
            assert data.storage_data.pop("uploaded") == min(size, pos + step)

    def test_update_without_upload_field(self, storage: fk.Storage, faker: Faker):
        data = storage.multipart_start(faker.file_name(), fk.MultipartData(size=10))

        with pytest.raises(fk.exc.MissingExtrasError):
            storage.multipart_update(data)

    def test_update_out_of_bound(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` controls size of the upload."""
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=len(content) // 2),
        )

        with pytest.raises(fk.exc.UploadOutOfBoundError):
            storage.multipart_update(data, upload=fk.make_upload(content))

    def test_update_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_update(
                fk.MultipartData(faker.file_path()), upload=fk.make_upload(b"")
            )

    def test_complete(self, storage: fk.Storage, faker: Faker):
        """File parameters validated upon completion."""
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(content_type="text/plain", size=len(content)),
        )

        with pytest.raises(fk.exc.UploadSizeMismatchError):
            storage.multipart_complete(data)

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(content),
        )
        data = storage.multipart_complete(data)
        assert data.size == len(content)
        assert data.hash == hashlib.md5(content).hexdigest()

    def test_complete_wrong_hash(self, storage: fk.Storage, faker: Faker):
        """File parameters validated upon completion."""
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(
                content_type="text/plain",
                size=len(content),
                hash="hello",
            ),
        )

        data = storage.multipart_update(data, upload=fk.make_upload(content))
        with pytest.raises(fk.exc.UploadHashMismatchError):
            storage.multipart_complete(data)

    def test_complete_wrong_type(self, storage: fk.Storage, faker: Faker):
        """File parameters validated upon completion."""
        content = b'{"hello":"world"}'
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(
                content_type="text/plain",
                size=len(content),
            ),
        )

        data = storage.multipart_update(data, upload=fk.make_upload(content))
        with pytest.raises(fk.exc.UploadTypeMismatchError):
            storage.multipart_complete(data)

    def test_complete_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_complete(
                fk.MultipartData(faker.file_path()), upload=fk.make_upload(b"")
            )


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
