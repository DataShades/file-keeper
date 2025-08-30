from __future__ import annotations

import pytest
import urllib3
from faker import Faker

import file_keeper as fk


class Analyzer:
    @pytest.mark.expect_storage_capability(fk.Capability.ANALYZE)
    def test_analyze_capabilities(self, storage: fk.Storage):
        """Analyzer supports ANALYZE capability."""
        assert storage.supports(fk.Capability.ANALYZE), "Does not support ANALYZE"

    @pytest.mark.expect_storage_capability(fk.Capability.ANALYZE, fk.Capability.CREATE)
    def test_analyze_predictability(self, storage: fk.Storage, faker: Faker):
        """Analyzer returns the same data as uploader upon file creation."""
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b"hello"))

        assert storage.analyze(data.location) == data, "Analyzed data does not match creation data"

    @pytest.mark.expect_storage_capability(fk.Capability.ANALYZE)
    def test_analyze_missing(self, storage: fk.Storage, faker: Faker):
        """Missing path cannot be analyzed and must be reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.analyze(fk.Location(faker.file_name()))


class Appender:
    @pytest.mark.expect_storage_capability(fk.Capability.APPEND)
    def test_append_capabilities(self, storage: fk.Storage):
        """Appender supports APPEND capability."""
        assert storage.supports(fk.Capability.APPEND), "Does not support APPEND"

    @pytest.mark.expect_storage_capability(fk.Capability.APPEND, fk.Capability.CREATE, fk.Capability.STREAM)
    def test_append_content(self, storage: fk.Storage, faker: Faker):
        """Content can be appended to the file."""
        content = faker.binary(50)
        result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))

        result = storage.append(result, fk.make_upload(content))
        assert storage.content(result) == content + content, "Content was modified in unexpected way during the appendy"

    @pytest.mark.expect_storage_capability(fk.Capability.APPEND)
    def test_append_missing(self, storage: fk.Storage, faker: Faker):
        """Append to non-existing file is reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.append(fk.FileData(fk.Location(faker.file_name())), fk.make_upload(b""))


class Composer:
    @pytest.mark.expect_storage_capability(fk.Capability.COMPOSE)
    def test_compose_capabilities(self, storage: fk.Storage):
        """Composer supports COMPOSE capability."""
        assert storage.supports(fk.Capability.COMPOSE), "Does not support COMPOSE"

    @pytest.mark.expect_storage_capability(fk.Capability.COMPOSE, fk.Capability.CREATE, fk.Capability.STREAM)
    def test_compose_normal(self, storage: fk.Storage, faker: Faker):
        """Multiple files can be combined into a new file."""
        content_1 = faker.binary(10)
        content_2 = faker.binary(10)

        first = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content_1))
        second = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content_2))

        result = storage.compose(fk.Location(faker.file_name()), first, second)
        assert result.size == first.size + second.size, "Composed file has wrong size"
        assert storage.content(result) == content_1 + content_2, "Composed file has wrong content"
        assert result.location not in [
            first.location,
            second.location,
        ], "Composed file has the same location as one of its sources"

    @pytest.mark.expect_storage_capability(fk.Capability.COMPOSE, fk.Capability.CREATE, fk.Capability.EXISTS)
    def test_compose_with_missing_source(self, storage: fk.Storage, faker: Faker):
        """If source is missing, composition is impossible."""
        first = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b"hello"))

        location = fk.Location(faker.file_name())

        with pytest.raises(fk.exc.MissingFileError):
            storage.compose(
                location,
                first,
                fk.FileData(fk.Location(faker.file_name())),
            )

        assert not storage.exists(fk.FileData(location)), "Composed file created even though the source is missing"

    @pytest.mark.expect_storage_capability(fk.Capability.COMPOSE, fk.Capability.CREATE)
    def test_compose_override_default_prevented(self, storage: fk.Storage, faker: Faker):
        """By default, composition cannot override existing file."""
        first = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))
        second = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))
        existing = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.compose(existing.location, first, second)

    @pytest.mark.expect_storage_capability(fk.Capability.COMPOSE, fk.Capability.CREATE, fk.Capability.STREAM)
    @pytest.mark.fk_storage_option("override_existing", True)
    def test_compose_with_allowed_override(self, storage: fk.Storage, faker: Faker):
        """Overrides are supported when explicitly enabled."""
        first = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b"hello"))
        second = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b" world"))
        existing = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))

        result = storage.compose(existing.location, first, second)
        assert result.location == existing.location, "Composed file has unexpected location"
        assert storage.content(result) == b"hello world", "Composed file has unexpected content"

    @pytest.mark.expect_storage_capability(fk.Capability.COMPOSE)
    def test_compose_with_no_data(self, storage: fk.Storage, faker: Faker):
        """Composition with zero sources is possible."""
        result = storage.compose(
            fk.Location(faker.file_name()),
        )
        assert result.size == 0, "Composed file must be empty"
        assert result.content_type == "application/x-empty", "Empty file has unexpected content type"


class Copier:
    @pytest.mark.expect_storage_capability(fk.Capability.COPY)
    def test_copy_capabilities(self, storage: fk.Storage):
        """Copier supports COPY capability."""
        assert storage.supports(fk.Capability.COPY), "Does not support COPY"

    @pytest.mark.expect_storage_capability(fk.Capability.COPY, fk.Capability.CREATE)
    def test_copy_normal(self, storage: fk.Storage, faker: Faker):
        """Copied file retains attributes of the original with different location."""
        content = faker.binary(10)
        original = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))
        copy = storage.copy(
            fk.Location(faker.file_name()),
            original,
        )
        assert original.location != copy.location, "File retains old location after the copy"
        assert original.hash == copy.hash, "Content hash was changed during the copy"

    @pytest.mark.expect_storage_capability(fk.Capability.COPY)
    def test_copy_missing(self, storage: fk.Storage, faker: Faker):
        """Cannot copy non-existing file."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.copy(
                fk.Location(faker.file_name()),
                fk.FileData(fk.Location(faker.file_name())),
            )

    @pytest.mark.expect_storage_capability(fk.Capability.COPY, fk.Capability.CREATE)
    def test_copy_into_existing_is_not_allowed_by_default(self, storage: fk.Storage, faker: Faker):
        """Cannot copy into existing location."""
        content = faker.binary(10)
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.copy(
                existing.location,
                data,
            )

    @pytest.mark.expect_storage_capability(fk.Capability.COPY, fk.Capability.CREATE, fk.Capability.STREAM)
    @pytest.mark.fk_storage_option("override_existing", True)
    def test_copy_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        """Overrides during copy can be enabled explicitly."""
        content = faker.binary(10)
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))

        result = storage.copy(
            existing.location,
            data,
        )
        assert existing.location == result.location, "Location of the copy does not match expected value"
        assert storage.content(result) == content, "Content of the copy was changed"


class Creator:
    """Standard logic for any uploader."""

    @pytest.mark.expect_storage_capability(fk.Capability.CREATE)
    def test_create_capabilities(self, storage: fk.Storage):
        """Uploader supports CREATE capability."""
        assert storage.supports(fk.Capability.CREATE), "Does not support CREATE"

    @pytest.mark.expect_storage_capability(fk.Capability.CREATE, fk.Capability.STREAM)
    def test_create_content_non_modified(self, storage: fk.Storage, faker: Faker):
        """Content matches the uploaded data"""
        content = faker.binary(100)
        result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))

        assert result.size == 100, "Uploaded file has wrong filesize"
        assert storage.content(result) == content, "Uploaded file has wrong content"

    @pytest.mark.expect_storage_capability(fk.Capability.CREATE, fk.Capability.STREAM)
    def test_create_empty_upload(self, storage: fk.Storage, faker: Faker):
        """Empty file can be created."""
        filename = faker.file_name()
        result = storage.upload(fk.Location(filename), fk.make_upload(b""))

        assert result.size == 0
        assert storage.content(result) == b""

    @pytest.mark.expect_storage_capability(fk.Capability.CREATE)
    def test_create_existing_is_not_replaced_by_default(self, storage: fk.Storage, faker: Faker):
        """Attempt to replace existing file is reported."""
        result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))
        with pytest.raises(fk.exc.ExistingFileError):
            storage.upload(result.location, fk.make_upload(b""))

    @pytest.mark.expect_storage_capability(fk.Capability.CREATE)
    def test_create_directory_allowed(self, storage: fk.Storage, faker: Faker):
        """Can upload into nested dirs."""
        path = faker.file_path(absolute=False)
        result = storage.upload(fk.Location(path), fk.make_upload(b""))
        assert result.location == path

    @pytest.mark.expect_storage_capability(fk.Capability.CREATE, fk.Capability.STREAM)
    @pytest.mark.fk_storage_option("override_existing", True)
    def test_create_replace_existing(self, storage: fk.Storage, faker: Faker):
        """Overrides can be explicitly enabled."""
        origin = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b"hello world"))
        overriden = storage.upload(origin.location, fk.make_upload(b"bye"))

        assert origin.location == overriden.location, "Location of uploaded file was changed"
        assert storage.content(overriden) == b"bye", "Unexpected content of the file"

    # @pytest.mark.expect_storage_capability(fk.Capability.CREATE)
    # def test_create_hash(self, storage: fk.Storage, faker: Faker):
    #     """Hash computed using full content."""
    #     result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))
    #     assert result.hash == hashlib.md5().hexdigest(), "Content hash of empty file differs from expected value"

    #     content = faker.binary(100)
    #     result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))
    #     assert result.hash == hashlib.md5(content).hexdigest(), "Content hash differs from expected value"


class Exister:
    @pytest.mark.expect_storage_capability(fk.Capability.EXISTS)
    def test_exist_capabilities(self, storage: fk.Storage):
        """Existence supports EXISTS capability."""
        assert storage.supports(fk.Capability.EXISTS), "Does not support EXISTS"

    @pytest.mark.expect_storage_capability(fk.Capability.EXISTS, fk.Capability.CREATE)
    def test_exists_real(self, storage: fk.Storage, faker: Faker):
        """Newly uploaded file exists."""
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))
        assert storage.exists(data), "Storage does not see uploaded file"

    @pytest.mark.expect_storage_capability(fk.Capability.EXISTS)
    def test_exists_missing(self, storage: fk.Storage, faker: Faker):
        """Fake file does not exists."""
        assert not storage.exists(fk.FileData(fk.Location(faker.file_name()))), "Storage sees non-existing file"


class Mover:
    @pytest.mark.expect_storage_capability(fk.Capability.MOVE)
    def test_move_capabilities(self, storage: fk.Storage):
        """Mover supports MOVE capability."""
        assert storage.supports(fk.Capability.MOVE), "Does not support MOVE"

    @pytest.mark.expect_storage_capability(
        fk.Capability.MOVE, fk.Capability.CREATE, fk.Capability.EXISTS, fk.Capability.STREAM
    )
    def test_move_real(self, storage: fk.Storage, faker: Faker):
        """File can be moved to a different location."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test move without EXIST capability")

        content = faker.binary(10)
        original = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))
        result = storage.move(
            fk.Location(faker.file_name()),
            original,
        )

        assert not storage.exists(original), "Moved file is still available under original location"
        assert storage.content(result) == content, "Content of the moved file was changed"

    @pytest.mark.expect_storage_capability(fk.Capability.MOVE)
    def test_move_missing(self, storage: fk.Storage, faker: Faker):
        """Attempt to move non-existing file is reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.move(
                fk.Location(faker.file_name()),
                fk.FileData(fk.Location(faker.file_name())),
            )

    @pytest.mark.expect_storage_capability(fk.Capability.MOVE, fk.Capability.CREATE)
    def test_move_into_existing_is_not_allowed_by_default(self, storage: fk.Storage, faker: Faker):
        """Attempt to override existing destination is reported."""
        content = faker.binary(10)
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))

        with pytest.raises(fk.exc.ExistingFileError):
            storage.move(
                existing.location,
                data,
            )

    @pytest.mark.expect_storage_capability(
        fk.Capability.MOVE, fk.Capability.CREATE, fk.Capability.EXISTS, fk.Capability.STREAM
    )
    @pytest.mark.fk_storage_option("override_existing", True)
    def test_move_into_existing_can_be_enabled(self, storage: fk.Storage, faker: Faker):
        """When explicitly enabled, moved file can override existing destination."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test move with allowed override without EXIST capability")

        content = faker.binary(10)
        data = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))
        existing = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))

        result = storage.move(
            existing.location,
            data,
        )
        assert not storage.exists(data), "Moved file is still available under original location"
        assert existing.location == result.location, "Actual move location is different from the expected location"
        assert storage.content(result) == content, "Content of the moved file was changed"


class Multiparter:
    """Multipart uploader without assumption about internal implementation"""

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipalrt_capabilities(self, storage: fk.Storage):
        """Multiparter supports MULTIPART capability."""
        assert storage.supports(fk.Capability.MULTIPART), "Does not support MULTIPART"

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_refresh_missing(self, faker: Faker, storage: fk.Storage):
        """Refreshing missing multipart upload is reported."""
        with pytest.raises(fk.exc.MissingFileError):
            storage.multipart_refresh(fk.FileData(fk.Location(faker.file_name())))

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_start_minimal(self, storage: fk.Storage, faker: Faker):
        """Multipart upload can be started with minimal parameters."""
        location = fk.Location(faker.file_name())
        data = storage.multipart_start(location, faker.pyint(1))
        assert data.storage_data["multipart"], "Multipart upload has no 'multipart' flag in storage_data"
        assert "parts" in data.storage_data, "Multipart upload has no 'parts' list in storage_data"

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_start_with_params(self, storage: fk.Storage, faker: Faker):
        """Multipart upload can be started with given parameters."""
        location = fk.Location(faker.file_name())
        content_type = faker.mime_type()
        hash = faker.md5()
        data = storage.multipart_start(location, faker.pyint(1), content_type=content_type, hash=hash)

        assert data.content_type == content_type, "Multipart upload has wrong content type"
        assert data.hash == hash, "Multipart upload has wrong hash"

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_remove(self, storage: fk.Storage, faker: Faker):
        """Multipart upload can be removed and cannot be removed twice."""
        location = fk.Location(faker.file_name())
        data = storage.multipart_start(location, faker.pyint(1))

        assert storage.multipart_remove(data), "Multipart upload was not removed"
        assert not storage.multipart_remove(data), "Removed multipart upload can be removed again"

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_update_out_of_bound(self, storage: fk.Storage, faker: Faker):
        """Uploading out of declared bounds is reported."""
        location = fk.Location(faker.file_name())
        data = storage.multipart_start(location, 10)

        content = faker.binary(11)
        with pytest.raises(fk.exc.UploadOutOfBoundError):
            storage.multipart_update(data, fk.make_upload(content), 0)

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_refresh_existing(self, storage: fk.Storage, faker: Faker):
        """Refreshing multipart upload with progress returns updated data."""
        location = fk.Location(faker.file_name())
        content = faker.binary(10)
        data = storage.multipart_start(location, 10)

        updated = storage.multipart_update(data, fk.make_upload(content), 0)
        refreshed = storage.multipart_refresh(data)

        assert updated == refreshed

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_complete_early(self, storage: fk.Storage, faker: Faker):
        """Completing multipart upload before all data is uploaded is reported."""
        location = fk.Location(faker.file_name())
        data = storage.multipart_start(location, 10)

        with pytest.raises(fk.exc.UploadSizeMismatchError):
            storage.multipart_complete(data)

    @pytest.mark.expect_storage_capability(fk.Capability.MULTIPART)
    def test_multipart_complete_normally(self, storage: fk.Storage, faker: Faker):
        location = fk.Location(faker.file_name())
        data = storage.multipart_start(location, 10)
        data = storage.multipart_update(data, fk.make_upload(faker.binary(10)), 1)
        result = storage.multipart_complete(data)

        assert "multipart" not in result.storage_data
        assert "parts" not in result.storage_data


class Ranger:
    @pytest.mark.expect_storage_capability(fk.Capability.RANGE)
    def test_range_capabilities(self, storage: fk.Storage):
        """Ranger supports RANGE capability."""
        assert storage.supports(fk.Capability.RANGE), "Does not support RANGE"


class Remover:
    @pytest.mark.expect_storage_capability(fk.Capability.REMOVE)
    def test_remove_capabilities(self, storage: fk.Storage):
        """Remover supports REMOVE capability."""
        assert storage.supports(fk.Capability.REMOVE), "Does not support REMOVE"

    @pytest.mark.expect_storage_capability(fk.Capability.REMOVE)
    def test_remove_missing(self, storage: fk.Storage, faker: Faker):
        """Removal of the missing file must return `False`."""
        assert not storage.remove(fk.FileData(fk.Location(faker.file_name()))), (
            "Storage pretends that non-existing file was removed."
        )

    @pytest.mark.expect_storage_capability(fk.Capability.REMOVE, fk.Capability.CREATE, fk.Capability.EXISTS)
    def test_remove_real(self, storage: fk.Storage, faker: Faker):
        """Removed file is identified as non-existing."""
        if not storage.supports(fk.Capability.EXISTS):
            pytest.skip("Cannot test removal without EXIST capability")

        result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b"hello world"))
        assert storage.remove(result), "Storage pretends that file does never existed"
        assert not storage.exists(result), "File still exists available after removal"


class Resumer:
    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE)
    def test_resumable_capabilities(self, storage: fk.Storage):
        """Resumer supports RESUMABLE capability."""
        assert storage.supports(fk.Capability.RESUMABLE), "Does not support RESUMABLE"

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE)
    def test_resumable_start_with_params(self, storage: fk.Storage, faker: Faker):
        """Resumable upload can be started with given parameters."""
        size = faker.pyint(1)
        content_type = faker.mime_type()
        hash = faker.md5()
        location = fk.Location(faker.file_name())

        result = storage.resumable_start(location, size, content_type=content_type, hash=hash)
        assert result.size == size, "Resumable upload has wrong size"
        assert result.content_type == content_type, "Resumable upload has wrong content type"
        assert result.hash == hash, "Resumable upload has wrong hash"
        assert result.storage_data["resumable"], "Resumable upload has no 'resumable' flag in storage_data"

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE)
    def test_resumable_start_without_params(self, storage: fk.Storage, faker: Faker):
        """Resumable upload can be started without additional fields."""
        location = fk.Location(faker.file_name())
        size = faker.pyint(1)

        result = storage.resumable_start(location, size)
        assert result.size == size, "Resumable upload has wrong size"
        assert result.content_type == fk.FileData.content_type, "Resumable upload has wrong content type"
        assert result.hash == fk.FileData.hash, "Resumable upload has wrong hash"
        assert result.storage_data["resumable"], "Resumable upload has no 'resumable' flag in storage_data"

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE, fk.Capability.EXISTS)
    def test_resumable_resume_with_whole_file(self, storage: fk.Storage, faker: Faker):
        """Resumable upload can be completed in one request."""
        location = fk.Location(faker.file_name())
        size = 1024 * 1024

        data = storage.resumable_start(location, size)

        content = faker.binary(size)
        result = storage.resumable_resume(data, fk.make_upload(content))

        assert storage.exists(result), "Resumable upload was not completed"
        assert result is not data, "Data was not copied during resume"
        assert "resumable" not in result.storage_data, "Resumable flag was not removed after completion"

        assert storage.content(result) == content, "Content of the resumable upload does not match the original"

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE, fk.Capability.EXISTS)
    def test_resumable_resume_chunked(self, storage: fk.Storage, faker: Faker):
        """Resumable upload can be completed in multiple requests"""
        location = fk.Location(faker.file_name())
        chunk = 1024 * 256

        data = storage.resumable_start(location, chunk * 4)

        content = faker.binary(chunk * 4)

        tmp_data = data
        for step in range(4):
            tmp_data = storage.resumable_resume(tmp_data, fk.make_upload(content[step * chunk : step * chunk + chunk]))

            has_flag = "resumable" in tmp_data.storage_data
            last_chunk = step == 3
            assert has_flag is not last_chunk

        result = tmp_data

        assert storage.exists(result), "Resumable upload was not completed"
        assert result is not data, "Data was not copied during resume"
        assert "resumable" not in result.storage_data, "Resumable flag was not removed after completion"
        assert storage.content(result) == content, "Content of the resumable upload does not match the original"

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE, fk.Capability.EXISTS)
    def test_resumable_refresh_without_changes(self, storage: fk.Storage, faker: Faker):
        """Refreshing resumable upload without progress returns the same data."""
        location = fk.Location(faker.file_name())
        data = storage.resumable_start(location, faker.pyint(1))
        refreshed = storage.resumable_refresh(data)

        assert refreshed == data, "Data was modified without any progress"

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE, fk.Capability.EXISTS)
    def test_resumable_refresh(self, storage: fk.Storage, faker: Faker):
        """Refreshing resumable upload can be used multiple times."""
        location = fk.Location(faker.file_name())
        chunk = 1024 * 256

        data = storage.resumable_start(location, chunk * 4)

        content = faker.binary(chunk * 4)

        tmp_data = data
        for step in range(4):
            tmp_data = storage.resumable_resume(tmp_data, fk.make_upload(content[step * chunk : step * chunk + chunk]))
            refreshed_data = storage.resumable_refresh(data)
            assert refreshed_data == tmp_data, "Data was modified without any progress"

    @pytest.mark.expect_storage_capability(fk.Capability.RESUMABLE)
    def test_resumable_refresh_missing(self, storage: fk.Storage, faker: Faker):
        """Refreshing missing resumable upload is reported."""
        location = fk.Location(faker.file_name())
        data = storage.resumable_start(location, faker.pyint(1))
        storage.resumable_remove(data)

        with pytest.raises(fk.exc.MissingFileError):
            storage.resumable_refresh(data)


class Scanner:
    @pytest.mark.expect_storage_capability(fk.Capability.SCAN)
    def test_scan_capabilities(self, storage: fk.Storage):
        """Scanner supports SCAN capability."""
        assert storage.supports(fk.Capability.SCAN), "Does not support SCAN"

    @pytest.mark.expect_storage_capability(fk.Capability.SCAN)
    def test_scan_normal(self, storage: fk.Storage, faker: Faker):
        first = faker.file_name()
        second = faker.file_name()
        third = faker.file_path(absolute=False)

        storage.upload(fk.Location(first), fk.make_upload(b""))
        storage.upload(fk.Location(second), fk.make_upload(b""))
        storage.upload(fk.Location(third), fk.make_upload(b""))
        discovered = set(storage.scan())

        assert discovered == {first, second, third}


class Signer:
    @pytest.mark.expect_storage_capability(fk.Capability.SIGNED)
    def test_signed_capabilities(self, storage: fk.Storage):
        """Reader supports STREAM capability."""
        assert storage.supports(fk.Capability.SIGNED), "Does not support SIGNED"

    @pytest.mark.expect_storage_capability(fk.Capability.SIGNED, fk.Capability.CREATE)
    def test_signed_download(self, storage: fk.Storage, faker: Faker):
        data = faker.binary(100)
        location = fk.Location(faker.file_name())
        storage.upload(location, fk.make_upload(data))

        url = storage.signed("download", 24 * 3600, location)
        resp = urllib3.request("GET", url)

        assert resp.data == data, "Signed download does not match content"

    @pytest.mark.expect_storage_capability(fk.Capability.SIGNED, fk.Capability.STREAM)
    def test_signed_upload(self, storage: fk.Storage, faker: Faker):
        data = faker.binary(100)
        location = fk.Location(faker.file_name())

        url = storage.signed("upload", 24 * 3600, location)

        urllib3.request(
            "PUT",
            url,
            body=data,
            headers={
                # azure requirements
                "x-ms-blob-type": "BlockBlob",
            },
        )
        assert storage.content(fk.FileData(location)) == data, "Signed upload does not match content"

    @pytest.mark.expect_storage_capability(fk.Capability.SIGNED, fk.Capability.EXISTS, fk.Capability.CREATE)
    def test_signed_delete(self, storage: fk.Storage, faker: Faker):
        data = faker.binary(100)
        location = fk.Location(faker.file_name())
        storage.upload(location, fk.make_upload(data))
        url = storage.signed("delete", 24 * 3600, location)

        urllib3.request(
            "DELETE",
            url,
        )
        assert not storage.exists(fk.FileData(location)), "Signed delete did not removed file"


class Streamer:
    """Standard expectations for readable storage"""

    @pytest.mark.expect_storage_capability(fk.Capability.STREAM)
    def test_stream_capabilities(self, storage: fk.Storage):
        """Reader supports STREAM capability."""
        assert storage.supports(fk.Capability.STREAM), "Does not support STREAM"

    @pytest.mark.expect_storage_capability(fk.Capability.STREAM)
    def test_stream_real(self, storage: fk.Storage, faker: Faker):
        """Content of uploaded file can be received."""
        content = faker.binary(100)
        result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))

        actual = b"".join(storage.stream(result))
        assert actual == content, "Content of the file was modified during stream"

    @pytest.mark.expect_storage_capability(fk.Capability.STREAM)
    def test_stream_matches_content(self, storage: fk.Storage, faker: Faker):
        """Content and stream produces the same result received."""
        content = faker.binary(100)
        result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(content))

        actual = b"".join(storage.stream(result))
        assert storage.content(result) == actual, "storage.content does not match storage.stream"

    @pytest.mark.expect_storage_capability(fk.Capability.STREAM)
    def test_stream_missing(self, storage: fk.Storage, faker: Faker):
        """Missing files cannot be read."""
        result = storage.upload(fk.Location(faker.file_name()), fk.make_upload(b""))
        wrong_location = fk.Location(result.location + faker.file_name())

        with pytest.raises(fk.exc.MissingFileError):
            next(iter(storage.stream(fk.FileData(wrong_location))))


class PermanentLinker:
    @pytest.mark.expect_storage_capability(fk.Capability.LINK_PERMANENT)
    def test_permanent_link_capabilities(self, storage: fk.Storage):
        assert storage.supports(fk.Capability.LINK_PERMANENT), "Does not support LINK_PERMANENT"


class TemporalLinker:
    @pytest.mark.expect_storage_capability(fk.Capability.LINK_TEMPORAL)
    def test_temporal_link_capabilities(self, storage: fk.Storage):
        assert storage.supports(fk.Capability.LINK_TEMPORAL), "Does not support LINK_TEMPORAL"


class OneTimeLinker:
    @pytest.mark.expect_storage_capability(fk.Capability.LINK_ONE_TIME)
    def test_one_time_link_capabilities(self, storage: fk.Storage):
        assert storage.supports(fk.Capability.LINK_ONE_TIME), "Does not support LINK_ONE_TIME"


@pytest.mark.usefixtures("expect_storage_capability")
class Standard(
    Analyzer,
    Appender,
    Composer,
    Copier,
    Creator,
    Exister,
    Mover,
    Multiparter,
    Ranger,
    Remover,
    Resumer,
    Scanner,
    Signer,
    Streamer,
    PermanentLinker,
    TemporalLinker,
    OneTimeLinker,
): ...
