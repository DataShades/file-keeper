from __future__ import annotations

import hashlib

import pytest
from faker import Faker

import file_keeper as fk


class Analyzer:
    def test_std_capabilities(self, storage: fk.Storage):
        """Analyzer supports ANALYZE capability."""
        assert storage.supports(fk.Capability.ANALYZE), "Does not support ANALYZE"

    def test_std_analyze(self, storage: fk.Storage, faker: Faker):
        """Analyzer returns the same data as uploader upon file creation."""
        data = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b"hello"))

        assert storage.analyze(data.location) == data, "Analyzed data does not match creation data"

    def test_std_missing(self, storage: fk.Storage, faker: Faker):
        """Missing path cannot be analyzed and must be reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.analyze(fk.types.Location(faker.file_name()))


class Scanner:
    def test_std_capabilities(self, storage: fk.Storage):
        """Scanner supports SCAN capability."""
        assert storage.supports(fk.Capability.SCAN), "Does not support SCAN"

    def test_std_scan_normal(self, storage: fk.Storage, faker: Faker):
        first = faker.file_name()
        second = faker.file_name()
        third = faker.file_path(absolute=False)

        storage.upload(fk.types.Location(first), fk.make_upload(b""))
        storage.upload(fk.types.Location(second), fk.make_upload(b""))
        storage.upload(fk.types.Location(third), fk.make_upload(b""))
        discovered = set(storage.scan())

        assert discovered == {first, second, third}


class Remover:
    def test_std_capabilities(self, storage: fk.Storage):
        """Remover supports REMOVE capability."""
        assert storage.supports(fk.Capability.REMOVE), "Does not support REMOVE"

    def test_std_removal_missing(self, storage: fk.Storage, faker: Faker):
        """Removal of the missing file must return `False`."""
        assert not storage.remove(fk.FileData(fk.types.Location(faker.file_name()))), (
            "Storage pretends that non-existing file was removed."
        )

    def test_std_removal(self, storage: fk.Storage, faker: Faker):
        """Removed file is identified as non-existing."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test removal without EXIST capability")

        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b"hello world"))
        assert storage.remove(result), "Storage pretends that file does never existed"
        assert not storage.exists(result), "File still exists available after removal"


class Exister:
    def test_std_capabilities(self, storage: fk.Storage):
        """Existence supports EXISTS capability."""
        assert storage.supports(fk.Capability.EXISTS), "Does not support EXISTS"

    def test_std_exists(self, storage: fk.Storage, faker: Faker):
        """Newly uploaded file exists."""
        data = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))
        assert storage.exists(data), "Storage does not see uploaded file"

    def test_std_exists_missing(self, storage: fk.Storage, faker: Faker):
        """Fake file does not exists."""
        assert not storage.exists(fk.FileData(fk.types.Location(faker.file_name()))), "Storage sees non-existing file"


class Mover:
    def test_std_capabilities(self, storage: fk.Storage):
        """Mover supports MOVE capability."""
        assert storage.supports(fk.Capability.MOVE), "Does not support MOVE"

    def test_std_move(self, storage: fk.Storage, faker: Faker):
        """File can be moved to a different location."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test move without EXIST capability")

        content = faker.binary(10)
        original = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))
        result = storage.move(
            fk.types.Location(faker.file_name()),
            original,
        )

        assert not storage.exists(original), "Moved file is still available under original location"
        assert storage.content(result) == content, "Content of the moved file was changed"

    def test_std_move_missing(self, storage: fk.Storage, faker: Faker):
        """Attempt to move non-existing file is reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.move(
                fk.types.Location(faker.file_name()),
                fk.FileData(fk.types.Location(faker.file_name())),
            )

    def test_std_move_into_existing_is_not_allowed_by_default(self, storage: fk.Storage, faker: Faker):
        """Attempt to override existing destination is reported."""
        content = faker.binary(10)
        data = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.move(
                existing.location,
                data,
            )

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_std_move_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        """When explicitly enabled, moved file can override existing destination."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test move with allowed override without EXIST capability")

        content = faker.binary(10)
        data = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))

        result = storage.move(
            existing.location,
            data,
        )
        assert not storage.exists(data), "Moved file is still available under original location"
        assert existing.location == result.location, "Actual move location is different from the expected location"
        assert storage.content(result) == content, "Content of the moved file was changed"


class Copier:
    def test_std_capabilities(self, storage: fk.Storage):
        """Copier supports COPY capability."""
        assert storage.supports(fk.Capability.COPY), "Does not support COPY"

    def test_std_copy(self, storage: fk.Storage, faker: Faker):
        """Copied file retains attributes of the original with different location."""
        content = faker.binary(10)
        original = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))
        copy = storage.copy(
            fk.types.Location(faker.file_name()),
            original,
        )
        assert original.location != copy.location, "File retains old location after the copy"
        assert original.hash == copy.hash, "Content hash was changed during the copy"

    def test_std_copy_missing(self, storage: fk.Storage, faker: Faker):
        """Cannot copy non-existing file."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.copy(
                fk.types.Location(faker.file_name()),
                fk.FileData(fk.types.Location(faker.file_name())),
            )

    def test_std_copy_into_existing_is_not_allowed_by_default(self, storage: fk.Storage, faker: Faker):
        """Cannot copy into existing location."""
        content = faker.binary(10)
        data = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.copy(
                existing.location,
                data,
            )

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_std_copy_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        """Overrides during copy can be enabled explicitly."""
        content = faker.binary(10)
        data = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))

        result = storage.copy(
            existing.location,
            data,
        )
        assert existing.location == result.location, "Location of the copy does not match expected value"
        assert storage.content(result) == content, "Content of the copy was changed"


class Appender:
    def test_std_capabilities(self, storage: fk.Storage):
        """Appender supports APPEND capability."""
        assert storage.supports(fk.Capability.APPEND), "Does not support APPEND"

    def test_std_append(self, storage: fk.Storage, faker: Faker):
        """Content can be appended to the file."""
        content = faker.binary(50)
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))

        result = storage.append(result, fk.make_upload(content))
        assert storage.content(result) == content + content, "Content was modified in unexpected way during the appendy"

    def test_std_missing(self, storage: fk.Storage, faker: Faker):
        """Append to non-existing file is reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.append(fk.FileData(fk.types.Location(faker.file_name())), fk.make_upload(b""))


class Composer:
    def test_std_capabilities(self, storage: fk.Storage):
        """Composer supports COMPOSE capability."""
        assert storage.supports(fk.Capability.COMPOSE), "Does not support COMPOSE"

    def test_std_compose(self, storage: fk.Storage, faker: Faker):
        """Multiple files can be combined into a new file."""
        content_1 = faker.binary(10)
        content_2 = faker.binary(10)

        first = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content_1))
        second = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content_2))

        result = storage.compose(fk.types.Location(faker.file_name()), first, second)
        assert result.size == first.size + second.size, "Composed file has wrong size"
        assert storage.content(result) == content_1 + content_2, "Composed file has wrong content"
        assert result.location not in [
            first.location,
            second.location,
        ], "Composed file has the same location as one of its sources"

    def test_std_compose_with_missing_source(self, storage: fk.Storage, faker: Faker):
        """If source is missing, composition is impossible."""
        first = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b"hello"))

        location = fk.types.Location(faker.file_name())

        with pytest.raises(fk.exc.MissingFileError):
            storage.compose(
                location,
                first,
                fk.FileData(fk.types.Location(faker.file_name())),
            )

        assert not storage.exists(fk.FileData(location)), "Composed file created even though the source is missing"

    def test_std_compose_override_default_prevented(self, storage: fk.Storage, faker: Faker):
        """By default, composition cannot override existing file."""
        first = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))
        second = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))
        existing = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.compose(existing.location, first, second)

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_std_compose_with_allowed_override(self, storage: fk.Storage, faker: Faker):
        """Overrides are supported when explicitly enabled."""
        first = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b"hello"))
        second = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b" world"))
        existing = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))

        result = storage.compose(existing.location, first, second)
        assert result.location == existing.location, "Composed file has unexpected location"
        assert storage.content(result) == b"hello world", "Composed file has unexpected content"

    def test_std_compose_with_no_data(self, storage: fk.Storage, faker: Faker):
        """Composition with zero sources is possible."""
        result = storage.compose(
            fk.types.Location(faker.file_name()),
        )
        assert result.size == 0, "Composed file must be empty"
        assert result.content_type == "application/x-empty", "Empty file has unexpected content type"


class Reader:
    """Standard expectations for readable storage"""

    def test_std_capabilities(self, storage: fk.Storage):
        """Reader supports STREAM capability."""
        assert storage.supports(fk.Capability.STREAM), "Does not support STREAM"

    def test_std_stream(self, storage: fk.Storage, faker: Faker):
        """Content of uploaded file can be received."""
        content = faker.binary(100)
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))

        actual = b"".join(storage.stream(result))
        assert actual == content, "Content of the file was modified during stream"

    def test_std_content_matches_stream(self, storage: fk.Storage, faker: Faker):
        """Content and stream produces the same result received."""
        content = faker.binary(100)
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))

        actual = b"".join(storage.stream(result))
        assert storage.content(result) == actual, "storage.content does not match storage.stream"

    def test_std_missing(self, storage: fk.Storage, faker: Faker):
        """Missing files cannot be read."""
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))
        wrong_location = fk.types.Location(result.location + faker.file_name())

        with pytest.raises(fk.exc.MissingFileError):
            next(iter(storage.stream(fk.FileData(wrong_location))))


class Multiparter:
    """Multipart uploader without assumption about internal implementation"""

    def test_std_capabilities(self, storage: fk.Storage):
        """Multiparter supports MULTIPART capability."""
        assert storage.supports(fk.Capability.MULTIPART), "Does not support MULTIPART"

    def test_std_refresh_missing(self, faker: Faker, storage: fk.Storage):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_refresh(fk.MultipartData(fk.types.Location(faker.file_name())))


class MultiparterWithUploaded:
    """Multipart upload with number of uploaded bytes."""

    def test_std_initialization(self, storage: fk.Storage, faker: Faker):
        """`multipart_start` creates an empty file."""
        size = faker.pyint()
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(size=size),
        )
        assert data.size == size
        assert data.storage_data["uploaded"] == 0
        assert storage.content(fk.FileData(fk.types.Location(data.location))) == b""

    def test_std_update(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` appends parts by default."""
        size = 100
        step = size // 10

        content = faker.binary(size)
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(size=size),
        )

        for pos in range(0, size, step):
            data = storage.multipart_update(
                data,
                upload=fk.make_upload(content[pos : pos + step]),
            )
            assert data.size == size
            assert data.storage_data["uploaded"] == min(size, pos + step)

    def test_std_update_wihtout_uploaded(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` appends parts by default."""
        size = 100
        step = size // 10

        content = faker.binary(size)
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(size=size),
        )

        for pos in range(0, size, step):
            data = storage.multipart_update(
                data,
                upload=fk.make_upload(content[pos : pos + step]),
            )
            assert data.size == size
            assert data.storage_data.pop("uploaded") == min(size, pos + step)

    def test_std_update_without_upload_field(self, storage: fk.Storage, faker: Faker):
        data = storage.multipart_start(fk.types.Location(faker.file_name()), fk.MultipartData(size=10))

        with pytest.raises(fk.exc.MissingExtrasError):
            storage.multipart_update(data)

    def test_std_update_out_of_bound(self, storage: fk.Storage, faker: Faker):
        """`multipart_update` controls size of the upload."""
        content = b"hello world"
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(size=len(content) // 2),
        )

        with pytest.raises(fk.exc.UploadOutOfBoundError):
            storage.multipart_update(data, upload=fk.make_upload(content))

    def test_std_update_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_update(
                fk.MultipartData(fk.types.Location(faker.file_path())),
                upload=fk.make_upload(b""),
            )

    def test_std_complete(self, storage: fk.Storage, faker: Faker):
        """File parameters validated upon completion."""
        content = b"hello world"
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
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

    def test_std_complete_wrong_hash(self, storage: fk.Storage, faker: Faker):
        """File parameters validated upon completion."""
        content = b"hello world"
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(
                content_type="text/plain",
                size=len(content),
                hash="hello",
            ),
        )

        data = storage.multipart_update(data, upload=fk.make_upload(content))
        with pytest.raises(fk.exc.UploadHashMismatchError):
            storage.multipart_complete(data)

    def test_std_complete_wrong_type(self, storage: fk.Storage, faker: Faker):
        """File parameters validated upon completion."""
        content = b'{"hello":"world"}'
        data = storage.multipart_start(
            fk.types.Location(faker.file_name()),
            fk.MultipartData(
                content_type="text/plain",
                size=len(content),
            ),
        )

        data = storage.multipart_update(data, upload=fk.make_upload(content))
        with pytest.raises(fk.exc.UploadTypeMismatchError):
            storage.multipart_complete(data)

    def test_std_complete_missing(self, storage: fk.Storage, faker: Faker):
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_complete(
                fk.MultipartData(fk.types.Location(faker.file_path())),
                upload=fk.make_upload(b""),
            )


class Uploader:
    """Standard logic for any uploader."""

    def test_std_capabilities(self, storage: fk.Storage):
        """Uploader supports CREATE capability."""
        assert storage.supports(fk.Capability.CREATE), "Does not support CREATE"

    def test_std_content(self, storage: fk.Storage, faker: Faker):
        """Content matches the uploaded data"""
        content = faker.binary(100)
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))

        assert result.size == 100, "Uploaded file has wrong filesize"
        assert storage.content(result) == content, "Uploaded file has wrong content"

    def test_std_empty_upload(self, storage: fk.Storage, faker: Faker):
        """Empty file can be created."""
        filename = faker.file_name()
        result = storage.upload(fk.types.Location(filename), fk.make_upload(b""))

        assert result.size == 0
        assert storage.content(result) == b""

    def test_std_existing_is_not_replaced_by_default(self, storage: fk.Storage, faker: Faker):
        """Attempt to replace existing file is reported."""
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))
        with pytest.raises(fk.exc.ExistingFileError):
            storage.upload(result.location, fk.make_upload(b""))

    def test_sub_directory_allowed(self, storage: fk.Storage, faker: Faker):
        """Can upload into nested dirs."""
        path = faker.file_path(absolute=False)
        result = storage.upload(fk.types.Location(path), fk.make_upload(b""))
        assert result.location == path

    @pytest.mark.fk_storage_option("override_existing", True)
    def test_std_replace_existing(self, storage: fk.Storage, faker: Faker):
        """Overrides can be explicitly enabled."""
        origin = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b"hello world"))
        overriden = storage.upload(origin.location, fk.make_upload(b"bye"))

        assert origin.location == overriden.location, "Location of uploaded file was changed"
        assert storage.content(overriden) == b"bye", "Unexpected content of the file"

    def test_std_hash(self, storage: fk.Storage, faker: Faker):
        """Hash computed using full content."""
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(b""))
        assert result.hash == hashlib.md5().hexdigest(), "Content hash of empty file differs from expected value"

        content = faker.binary(100)
        result = storage.upload(fk.types.Location(faker.file_name()), fk.make_upload(content))
        assert result.hash == hashlib.md5(content).hexdigest(), "Content hash differs from expected value"
