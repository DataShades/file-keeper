from __future__ import annotations

import hashlib

import pytest
from faker import Faker

import file_keeper as fk


class Analyzer:
    def test_capabilities(self, storage: fk.Storage):
        """Analyzer supports ANALYZE capability."""
        assert storage.supports(fk.Capability.ANALYZE), "Does not support ANALYZE"

    def test_analyze(self, storage: fk.Storage, faker: Faker):
        """Analyzer returns the same data as uploader upon file creation."""
        data = storage.upload(faker.file_name(), fk.make_upload(b""))

        assert (
            storage.analyze(data.location) == data
        ), "Analyzed data does not match creation data"

    def test_missing(self, storage: fk.Storage, faker: Faker):
        """Missing path cannot be analyzed and must be reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.analyze(faker.file_name())


class Scanner:
    def test_capabilities(self, storage: fk.Storage):
        """Scanner supports SCAN capability."""
        assert storage.supports(fk.Capability.SCAN), "Does not support SCAN"


class Remover:
    def test_capabilities(self, storage: fk.Storage):
        """Remover supports REMOVE capability."""
        assert storage.supports(fk.Capability.REMOVE), "Does not support REMOVE"

    def test_removal_missing(self, storage: fk.Storage, faker: Faker):
        """Removal of the missing file must return `False`."""
        assert not storage.remove(
            fk.FileData(faker.file_name())
        ), "Storage pretends that non-existing file was removed."

    def test_removal(self, storage: fk.Storage, faker: Faker):
        """Removed file is identified as non-existing."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test removal without EXIST capability")

        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert storage.remove(result), "Storage pretends that file does never existed"
        assert not storage.exists(result), "File still exists available after removal"


class Exister:
    def test_capabilities(self, storage: fk.Storage):
        """Existence supports EXISTS capability."""
        assert storage.supports(fk.Capability.EXISTS), "Does not support EXISTS"

    def test_exists(self, storage: fk.Storage, faker: Faker):
        """Newly uploaded file exists."""
        data = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert storage.exists(data), "Storage does not see uploaded file"

    def test_exists_missing(self, storage: fk.Storage, faker: Faker):
        """Fake file does not exists."""
        assert not storage.exists(
            fk.FileData(faker.file_name())
        ), "Storage sees non-existing file"


class Mover:
    def test_capabilities(self, storage: fk.Storage):
        """Mover supports MOVE capability."""
        assert storage.supports(fk.Capability.MOVE), "Does not support MOVE"

    def test_move(self, storage: fk.Storage, faker: Faker):
        """File can be moved to a different location."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test move without EXIST capability")

        content = faker.binary(10)
        original = storage.upload(faker.file_name(), fk.make_upload(content))
        result = storage.move(
            faker.file_name(),
            original,
            storage,
        )

        assert not storage.exists(
            original
        ), "Moved file is still available under original location"
        assert (
            storage.content(result) == content
        ), "Content of the moved file was changed"

    def test_move_missing(self, storage: fk.Storage, faker: Faker):
        """Attempt to move non-existing file is reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.move(faker.file_name(), fk.FileData(faker.file_name()), storage)

    def test_move_into_existing_is_not_allowed_by_default(
        self, storage: fk.Storage, faker: Faker
    ):
        """Attempt to override existing destination is reported."""
        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.move(existing.location, data, storage)

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_move_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        """When explicitly enabled, moved file can override existing destination."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip(
                "Cannot test move with allowed override without EXIST capability"
            )

        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        result = storage.move(existing.location, data, storage)
        assert not storage.exists(
            data
        ), "Moved file is still available under original location"
        assert (
            existing.location == result.location
        ), "Actual move location is different from the expected location"
        assert (
            storage.content(result) == content
        ), "Content of the moved file was changed"


class Copier:
    def test_capabilities(self, storage: fk.Storage):
        """Copier supports COPY capability."""
        assert storage.supports(fk.Capability.COPY), "Does not support COPY"

    def test_copy(self, storage: fk.Storage, faker: Faker):
        """Copied file retains attributes of the original with different location."""
        content = faker.binary(10)
        original = storage.upload(faker.file_name(), fk.make_upload(content))
        copy = storage.copy(faker.file_name(), original, storage)
        assert (
            original.location != copy.location
        ), "File retains old location after the copy"
        assert original.hash == copy.hash, "Content hash was changed during the copy"

    def test_copy_missing(self, storage: fk.Storage, faker: Faker):
        """Cannot copy non-existing file."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.copy(faker.file_name(), fk.FileData(faker.file_name()), storage)

    def test_copy_into_existing_is_not_allowed_by_default(
        self, storage: fk.Storage, faker: Faker
    ):
        """Cannot copy into existing location."""
        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.copy(existing.location, data, storage)

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_copy_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        """Overrides during copy can be enabled explicitly."""
        content = faker.binary(10)
        data = storage.upload(faker.file_name(), fk.make_upload(content))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        result = storage.copy(existing.location, data, storage)
        assert (
            existing.location == result.location
        ), "Location of the copy does not match expected value"
        assert storage.content(result) == content, "Content of the copy was changed"


class Appender:
    def test_capabilities(self, storage: fk.Storage):
        """Appender supports APPEND capability."""
        assert storage.supports(fk.Capability.APPEND), "Does not support APPEND"

    def test_append(self, storage: fk.Storage, faker: Faker):
        """Content can be appended to the file."""
        content = faker.binary(50)
        result = storage.upload(faker.file_name(), fk.make_upload(content))

        result = storage.append(result, fk.make_upload(content))
        assert (
            storage.content(result) == content + content
        ), "Content was modified in unexpected way during the appendy"

    def test_missing(self, storage: fk.Storage, faker: Faker):
        """Append to non-existing file is reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.append(fk.FileData(faker.file_name()), fk.make_upload(b""))

    @pytest.mark.fk_storage_option("max_size", 10)
    def test_append_with_big_file(self, storage: fk.Storage, faker: Faker):
        """Size limits are tracked during the append."""
        content = faker.binary(storage.settings.max_size // 2 + 1)
        data = storage.upload(faker.file_name(), fk.make_upload(content))

        with pytest.raises(fk.exc.LargeUploadError):
            storage.append(data, fk.make_upload(content))


class Composer:
    def test_capabilities(self, storage: fk.Storage):
        """Composer supports COMPOSE capability."""
        assert storage.supports(fk.Capability.COMPOSE), "Does not support COMPOSE"

    def test_compose(self, storage: fk.Storage, faker: Faker):
        """Multiple files can be combined into a new file."""
        content_1 = faker.binary(10)
        content_2 = faker.binary(10)

        first = storage.upload(faker.file_name(), fk.make_upload(content_1))
        second = storage.upload(faker.file_name(), fk.make_upload(content_2))

        result = storage.compose(faker.file_name(), storage, first, second)
        assert result.size == first.size + second.size, "Composed file has wrong size"
        assert (
            storage.content(result) == content_1 + content_2
        ), "Composed file has wrong content"
        assert result.location not in [
            first.location,
            second.location,
        ], "Composed file has the same location as one of its sources"

    def test_compose_with_missing_source(self, storage: fk.Storage, faker: Faker):
        """If source is missing, composition is impossible."""
        first = storage.upload(faker.file_name(), fk.make_upload(b"hello"))

        location = faker.file_name()

        with pytest.raises(fk.exc.MissingFileError):
            storage.compose(location, storage, first, fk.FileData(faker.file_name()))

        assert not storage.exists(
            fk.FileData(location)
        ), "Composed file created even though the source is missing"

    def test_compose_override_default_prevented(
        self, storage: fk.Storage, faker: Faker
    ):
        """By default, composition cannot override existing file."""
        first = storage.upload(faker.file_name(), fk.make_upload(b""))
        second = storage.upload(faker.file_name(), fk.make_upload(b""))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.compose(existing.location, storage, first, second)

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_compose_with_allowed_override(self, storage: fk.Storage, faker: Faker):
        """Overrides are supported when explicitly enabled."""
        first = storage.upload(faker.file_name(), fk.make_upload(b"hello"))
        second = storage.upload(faker.file_name(), fk.make_upload(b" world"))
        existing = storage.upload(faker.file_name(), fk.make_upload(b""))

        result = storage.compose(existing.location, storage, first, second)
        assert (
            result.location == existing.location
        ), "Composed file has unexpected location"
        assert (
            storage.content(result) == b"hello world"
        ), "Composed file has unexpected content"

    def test_compose_with_no_data(self, storage: fk.Storage, faker: Faker):
        """Composition with zero sources is possible."""
        result = storage.compose(faker.file_name(), storage)
        assert result.size == 0, "Composed file must be empty"
        assert (
            result.content_type == "application/x-empty"
        ), "Empty file has unexpected content type"


class Reader:
    def test_capabilities(self, storage: fk.Storage):
        """Reader supports STREAM capability."""
        assert storage.supports(fk.Capability.STREAM), "Does not support STREAM"

    def test_stream(self, storage: fk.Storage, faker: Faker):
        """Content of uploaded file can be received."""
        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(content))

        actual = b"".join(storage.stream(result))
        assert actual == content, "Content of the file was modified"

    def test_content_matches_stream(self, storage: fk.Storage, faker: Faker):
        """Content and stream produces the same result received."""
        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(content))

        actual = b"".join(storage.stream(result))
        assert storage.content(result) == actual, "Content does not match stream"

    def test_missing(self, storage: fk.Storage, faker: Faker):
        """Missing files cannot be read."""
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        result.location += faker.file_name()

        with pytest.raises(fk.exc.MissingFileError):
            storage.stream(result)


class Multiparter:
    def test_capabilities(self, storage: fk.Storage):
        """Multiparter supports MULTIPART capability."""
        assert storage.supports(fk.Capability.MULTIPART), "Does not support MULTIPART"

    def test_refresh_missing(self, faker: Faker, storage: fk.Storage):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_refresh(fk.MultipartData(faker.file_name()))


class MultiparterWithUploaded:
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


class Uploader:
    def test_capabilities(self, storage: fk.Storage):
        """Uploader supports CREATE capability."""
        assert storage.supports(fk.Capability.CREATE), "Does not support CREATE"

    def test_content(self, storage: fk.Storage, faker: Faker):
        """Content matches the uploaded data"""
        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(content))

        assert result.size == 100, "Uploaded file has wrong filesize"
        assert storage.content(result) == content, "Uploaded file has wrong content"

    def test_empty_upload(self, storage: fk.Storage, faker: Faker):
        """Empty file can be created."""
        filename = faker.file_name()
        result = storage.upload(filename, fk.make_upload(b""))

        assert result.size == 0
        assert storage.content(result) == b""

    def test_existing_is_not_replaced_by_default(
        self, storage: fk.Storage, faker: Faker
    ):
        """Attempt to replace existing file is reported."""
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        with pytest.raises(fk.exc.ExistingFileError):
            storage.upload(result.location, fk.make_upload(b""))

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_replace_existing(self, storage: fk.Storage, faker: Faker):
        """Overrides can be explicitly enabled."""
        origin = storage.upload(faker.file_name(), fk.make_upload(b"hello world"))
        overriden = storage.upload(origin.location, fk.make_upload(b"bye"))

        assert (
            origin.location == overriden.location
        ), "Location of uploaded file was changed"
        assert storage.content(overriden) == b"bye", "Unexpected content of the file"

    def test_hash(self, storage: fk.Storage, faker: Faker):
        """Hash computed using full content."""
        result = storage.upload(faker.file_name(), fk.make_upload(b""))
        assert (
            result.hash == hashlib.md5().hexdigest()
        ), "Content hash of empty file differs from expected value"

        content = faker.binary(100)
        result = storage.upload(faker.file_name(), fk.make_upload(content))
        assert (
            result.hash == hashlib.md5(content).hexdigest()
        ), "Content hash differs from expected value"
