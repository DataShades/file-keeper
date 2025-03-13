from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest
from faker import Faker

import file_keeper as fk
import file_keeper.default.adapters.fs as fs


@pytest.fixture()
def storage(tmp_path: Path, request: pytest.FixtureRequest):
    settings = {"name": "test", "path": str(tmp_path)}
    marks: Any = request.node.iter_markers("fk_storage_option")
    for mark in marks:
        settings[mark.args[0]] = mark.args[1]

    return fs.FsStorage(settings)


class TestSettings:
    def test_creation(self):
        """Test how settings initialized with and without required option."""
        with pytest.raises(fk.exc.MissingStorageConfigurationError):
            fs.Settings()

        fs.Settings(path="test")


class TestUploader:
    def test_capabilities(self, storage: fk.Storage):
        assert storage.supports(fk.Capability.CREATE)
        assert storage.supports(fk.Capability.MULTIPART)

    @pytest.mark.fk_storage_option("recursive", True)
    def test_sub_directory_allowed(self, storage: fk.Storage, faker: Faker):
        """Can upload into nested dirs when `recursive` enabled."""
        path = faker.file_path(absolute=False)
        result = storage.upload(path, fk.make_upload(b""))
        assert result.location == path

    def test_sub_directory_not_allowed(self, storage: fk.Storage, faker: Faker):
        """Cannot upload into nested dirs by default."""
        with pytest.raises(fk.exc.LocationError):
            storage.upload(faker.file_path(absolute=False), fk.make_upload(b""))

    @pytest.mark.fk_storage_option("recursive", True)
    def test_absolute_sub_path_sanitized(self, storage: fk.Storage, faker: Faker):
        """Cannot upload to absolute path."""
        path = faker.file_path(absolute=True)
        result = storage.upload(path, fk.make_upload(b""))
        assert result.location == path.lstrip("/")

    @pytest.mark.fk_storage_option("recursive", True)
    def test_parent_sub_path_sanitized(self, storage: fk.Storage, faker: Faker):
        """Cannot upload to parent dir."""
        path = faker.file_path(absolute=False)
        result = storage.upload(f"../../{path}", fk.make_upload(b""))
        assert result.location == path

    def test_empty_upload(self, storage: fs.FsStorage, faker: Faker):
        """Empty file can be created."""
        filename = faker.file_name()
        result = storage.upload(filename, fk.make_upload(b""))

        assert result.size == 0

        filepath = os.path.join(storage.settings.path, result.location)
        assert os.path.exists(filepath)
        assert storage.content(result) == b""

    def test_content(self, storage: fk.Storage, faker: Faker):
        """Content matches the uploaded data"""
        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(content))

        assert result.size == 100
        assert storage.content(result) == content

    def test_hash(self, storage: fk.Storage, faker: Faker):
        """Hash computed using full content."""
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert result.hash == hashlib.md5().hexdigest()

        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(content))
        assert result.hash == hashlib.md5(content).hexdigest()

    def test_existing_is_not_replaced_by_default(
        self, storage: fk.Storage, faker: Faker
    ):
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        with pytest.raises(fk.exc.ExistingFileError):
            storage.upload(result.location, fk.make_upload(b""))

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_replace_existing(self, storage: fk.Storage, faker: Faker):
        origin = storage.upload(faker.file_name(), fk.make_upload(b"hello world"))
        overriden = storage.upload(origin.location, fk.make_upload(b"bye"))

        assert origin.location == overriden.location
        assert storage.content(overriden) == b"bye"


class TestMultipartUploader:
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

    def test_refresh(self, faker: Faker, storage: fs.FsStorage):
        """`multipart_refresh` synchronized filesize."""
        content = faker.binary(10)
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=len(content)),
        )
        with open(os.path.join(storage.settings.path, data.location), "wb") as dest:
            dest.write(content)

        data = storage.multipart_refresh(data)
        assert data.storage_data["uploaded"] == len(content)

    def test_refresh_missing(self, faker: Faker, storage: fs.FsStorage):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_refresh(fk.MultipartData(faker.file_name()))

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

    def test_update_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_update(
                fk.MultipartData(faker.file_path()), upload=fk.make_upload(b"")
            )

    def test_update_without_upload_field(self, storage: fk.Storage, faker: Faker):
        data = storage.multipart_start(faker.file_name(), fk.MultipartData(size=10))

        with pytest.raises(fk.exc.MissingExtrasError):
            storage.multipart_update(data)

    def test_update_with_position(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` can override existing parts."""
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=len(content)),
        )

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(content),
        )

        data = storage.multipart_update(
            data,
            upload=fk.make_upload(b"LLO W"),
            position=2,
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == len(content)

        assert storage.content(fk.FileData(data.location)) == b"heLLO World"

    def test_update_out_of_bound(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` controls size of the upload."""
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            fk.MultipartData(size=len(content) // 2),
        )

        with pytest.raises(fk.exc.UploadOutOfBoundError):
            storage.multipart_update(data, upload=fk.make_upload(content))

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


class TestReader:
    def test_capabilities(self, storage: fk.Storage):
        assert storage.supports(fk.Capability.STREAM)

    def test_stream(self, storage: fk.Storage, faker: Faker):
        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(content))

        assert storage.content(result) == content

    def test_missing(self, storage: fk.Storage, faker: Faker):
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        result.location += faker.file_name()

        with pytest.raises(fk.exc.MissingFileError):
            storage.stream(result)


class TestManager:
    def test_capabilities(self, storage: fk.Storage):
        assert storage.supports(fk.Capability.REMOVE)
        assert storage.supports(fk.Capability.SCAN)
        assert storage.supports(fk.Capability.EXISTS)
        assert storage.supports(fk.Capability.ANALYZE)
        assert storage.supports(fk.Capability.COPY)
        assert storage.supports(fk.Capability.MOVE)
        assert storage.supports(fk.Capability.COMPOSE)
        assert storage.supports(fk.Capability.APPEND)

    def test_compose(self, storage: fk.Storage, faker: Faker):
        content_1 = faker.binary(10)
        content_2 = faker.binary(10)

        first = storage.upload(faker.file_name(), fk.make_upload(content_1))
        second = storage.upload(faker.file_name(), fk.make_upload(content_2))

        result = storage.compose(faker.file_name(), storage, first, second)
        assert result.size == first.size + second.size
        assert storage.content(result) == content_1 + content_2
        assert result.location not in [first.location, second.location]

    def test_compose_with_missing_source(self, storage: fk.Storage, faker: Faker):
        first = storage.upload(faker.file_name(), fk.make_upload(b"hello"))

        location = faker.file_name()

        with pytest.raises(fk.exc.MissingFileError):
            storage.compose(location, storage, first, fk.FileData(faker.file_name()))

        assert not storage.exists(fk.FileData(location))

    def test_compose_override_default_prevented(
        self, storage: fk.Storage, faker: Faker
    ):
        first = storage.upload(faker.file_name(), fk.make_upload(b""))
        second = storage.upload(faker.file_name(), fk.make_upload(b""))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.compose(existing.location, storage, first, second)

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_compose_with_allowed_override(self, storage: fk.Storage, faker: Faker):
        first = storage.upload(faker.file_name(), fk.make_upload(b"hello"))
        second = storage.upload(faker.file_name(), fk.make_upload(b" world"))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        result = storage.compose(existing.location, storage, first, second)
        assert result.location == existing.location
        assert storage.content(result) == b"hello world"

    def test_compose_with_no_data(self, storage: fk.Storage, faker: Faker):
        result = storage.compose(faker.file_name(), storage)
        assert result.size == 0
        assert result.content_type == "application/x-empty"

    @pytest.mark.fk_storage_option("supported_types", ["text"])
    def test_compose_with_wrong_final_type(self, storage: fs.FsStorage, faker: Faker):
        """If source files produce unsupported composed type, it is removed."""
        first = storage.upload(faker.file_name(), fk.make_upload(b'{"hello":'))
        second = storage.upload(faker.file_name(), fk.make_upload(b'"world"}'))

        location = faker.file_name()
        with pytest.raises(fk.exc.WrongUploadTypeError):
            storage.compose(location, storage, first, second)

        assert not os.path.exists(os.path.join(storage.settings.path, location))

    @pytest.mark.fk_storage_option("max_size", 10)
    def test_compose_with_immense_size(self, storage: fs.FsStorage, faker: Faker):
        """If source files produce too big result it is removed."""
        content = faker.binary(storage.settings.max_size - 1)
        first = storage.upload(faker.file_name(), fk.make_upload(content))
        second = storage.upload(faker.file_name(), fk.make_upload(content))

        location = faker.file_name()
        with pytest.raises(fk.exc.LargeUploadError):
            storage.compose(location, storage, first, second)

        assert not os.path.exists(os.path.join(storage.settings.path, location))

    def test_append(self, storage: fs.FsStorage, faker: Faker):
        content = faker.binary(50)
        result = storage.append(fk.FileData(faker.file_name()), fk.make_upload(content))
        assert storage.content(result) == content

        result = storage.append(result, fk.make_upload(content))
        assert storage.content(result) == content + content

    @pytest.mark.fk_storage_option("max_size", 10)
    def test_append_with_big_file(self, storage: fk.Storage, faker: Faker):
        content = faker.binary(storage.settings.max_size + 1)
        with pytest.raises(fk.exc.LargeUploadError):
            storage.append(fk.FileData(faker.file_name()), fk.make_upload(content))

    @pytest.mark.fk_storage_option("supported_types", ["text"])
    def test_append_with_wrong_final_type(self, storage: fs.FsStorage, faker: Faker):
        """If source files produce unsupported composed type, it is removed."""
        data = storage.upload(faker.file_name(), fk.make_upload(b'{"hello":'))
        with pytest.raises(fk.exc.WrongUploadTypeError):
            storage.append(data, fk.make_upload(b'"world"}'))

        assert not os.path.exists(os.path.join(storage.settings.path, data.location))

    def test_copy(self, storage: fk.Storage, faker: Faker):
        content = faker.binary(10)
        original = storage.upload(faker.file_name(), fk.make_upload(content))
        copy = storage.copy(faker.file_name(), original, storage)
        assert original.location != copy.location
        assert original.hash == copy.hash

    def test_copy_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.copy(faker.file_name(), fk.FileData(faker.file_name()), storage)

    def test_copy_into_existing_is_not_allowed_by_default(
        self, storage: fk.Storage, faker: Faker
    ):
        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.copy(existing.location, data, storage)

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_copy_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        result = storage.copy(existing.location, data, storage)
        assert existing.location == result.location
        assert storage.content(result) == content

    def test_move(self, storage: fk.Storage, faker: Faker):
        content = faker.binary(10)
        original = storage.upload(faker.file_name(), fk.make_upload(content))
        result = storage.move(faker.file_name(), original, storage)

        assert not storage.exists(original)
        assert storage.content(result) == content

    def test_move_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.move(faker.file_name(), fk.FileData(faker.file_name()), storage)

    def test_move_into_existing_is_not_allowed_by_default(
        self, storage: fk.Storage, faker: Faker
    ):
        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.move(existing.location, data, storage)

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_move_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        result = storage.move(existing.location, data, storage)
        assert not storage.exists(data)
        assert existing.location == result.location
        assert storage.content(result) == content

    def test_exists(self, storage: fk.Storage, faker: Faker):
        data = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert storage.exists(data)

    def test_exists_missing(self, storage: fk.Storage, faker: Faker):
        assert not storage.exists(fk.FileData(faker.file_name()))

    def test_removal(self, storage: fs.FsStorage, faker: Faker):
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert storage.remove(result)
        assert not storage.exists(result)

    def test_removal_missing(self, storage: fk.Storage, faker: Faker):
        assert not storage.remove(fk.FileData(faker.file_name()))

    def test_scan(self, storage: fs.FsStorage, faker: Faker):
        first = storage.upload(faker.file_name(), fk.make_upload(b""))
        second = storage.upload(faker.file_name(), fk.make_upload(b""))

        relpath = faker.file_path(absolute=False)
        nested_path = os.path.join(storage.settings.path, relpath)
        os.makedirs(os.path.dirname(nested_path))
        with open(nested_path, "wb"):
            pass

        discovered = set(storage.scan())

        assert discovered == {first.location, second.location}

    @pytest.mark.fk_storage_option("recursive", True)
    def test_scan_recursive(self, storage: fs.FsStorage, faker: Faker):
        first = storage.upload(faker.file_name(), fk.make_upload(b""))
        second = storage.upload(faker.file_name(), fk.make_upload(b""))

        relpath = faker.file_path(absolute=False)
        nested_path = os.path.join(storage.settings.path, relpath)
        os.makedirs(os.path.dirname(nested_path))
        with open(nested_path, "wb"):
            pass

        discovered = set(storage.scan())

        assert discovered == {first.location, second.location, relpath}

    def test_analyze(self, storage: fk.Storage, faker: Faker):
        data = storage.upload(faker.file_name(), fk.make_upload(b""))

        assert storage.analyze(data.location) == data

    def test_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.analyze(faker.file_name())


class TestStorage:
    def test_missing_path(self, tmp_path: Path, faker: Faker):
        path = faker.file_path(absolute=False, extension="")

        with pytest.raises(fk.exc.InvalidStorageConfigurationError):
            fs.FsStorage(
                {"path": os.path.join(tmp_path, path)},
            )

    def test_missing_path_created(self, tmp_path: Path, faker: Faker):
        subpath = faker.file_path(absolute=False, extension="")
        path = os.path.join(tmp_path, subpath)

        fs.FsStorage({"path": path, "create_path": True})
        assert os.path.exists(path)
