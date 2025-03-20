from __future__ import annotations

from pathlib import Path
from typing import Any

import opendal
import pytest

import file_keeper as fk
import file_keeper.default.adapters.opendal as od

from . import standard

Settings = od.Settings
Storage = od.OpenDalStorage


@pytest.fixture()
def storage(tmp_path: Path, storage_settings: dict[str, Any]):
    settings: dict[str, Any] = {
        "name": "test",
        "scheme": "fs",
        "params": {"root": str(tmp_path)},
    }
    settings.update(storage_settings)

    return Storage(settings)


class TestSettings:
    def test_scheme_required(self):
        with pytest.raises(fk.exc.MissingStorageConfigurationError):
            Settings()

    def test_error_mapping(self):
        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            Settings(scheme="fs")

    def test_operator(self, tmp_path: Path):
        op = opendal.Operator("fs", root=str(tmp_path))
        cfg = Settings(operator=op)
        assert cfg.operator is op


class TestUploaderUpload(standard.Uploader, standard.UploaderRecursive):
    pass


class TestReader(standard.Reader):
    pass


class TestManagerExists(standard.Exister):
    pass


class TestManagerRemove(standard.Remover):
    pass


class TestManagerScan(standard.Scanner):
    pass


class TestManagerCopy(standard.Copier):
    pass


class TestManagerMove(standard.Mover):
    pass


class TestManagerAnalyze(standard.Analyzer):
    pass


class TestManagerAppend(standard.Appender):
    ...

class TestStorage:
    def test_capabilities_fs(self, storage: Storage):
        assert storage.supports(
            fk.Capability.STREAM
            | fk.Capability.EXISTS
            | fk.Capability.ANALYZE
            | fk.Capability.CREATE
            | fk.Capability.SCAN
            | fk.Capability.REMOVE
            | fk.Capability.APPEND
            | fk.Capability.MOVE
            | fk.Capability.COPY
        )

    def test_capabilities_http(self):
        storage = Storage(
            {"scheme": "http", "params": {"endpoint": "https://google.com"}}
        )
        assert not storage.supports(fk.Capability.REMOVE)
        assert not storage.supports(fk.Capability.SCAN)
        assert not storage.supports(fk.Capability.CREATE)
        assert not storage.supports(fk.Capability.COPY)
        assert not storage.supports(fk.Capability.MOVE)
        assert not storage.supports(fk.Capability.REMOVE)
