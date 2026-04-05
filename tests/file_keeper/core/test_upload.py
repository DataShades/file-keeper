import tempfile
from typing import Any

import pytest
from faker import Faker

from file_keeper import Upload, make_upload

try:
    from werkzeug.datastructures import FileStorage
except ImportError:
    FileStorage: Any = None


class TestMakeUpload:
    @pytest.mark.skipif(not FileStorage, reason="werkzeug is not installed")
    def test_file_storage(self):
        """FileStorage instances returned as-is."""

        result = make_upload(FileStorage())
        assert isinstance(result, Upload)

    def test_tempfile(self):
        """Temp files converted into Upload."""
        with tempfile.SpooledTemporaryFile() as fd:
            _ = fd.write(b"hello")
            _ = fd.seek(0)
            result = make_upload(fd)
            assert isinstance(result, Upload)
            assert result.stream.read() == b"hello"

    def test_str(self, faker: Faker):
        """Strings converted into Upload."""
        string: Any = faker.pystr()
        with pytest.raises(TypeError):
            make_upload(string)

    def test_bytes(self, faker: Faker):
        """Bytes converted into Upload."""
        binary = faker.binary(100)
        result = make_upload(binary)

        assert isinstance(result, Upload)
        assert result.stream.read() == binary

    def test_wrong_type(self):
        """Any unexpected value causes an exception."""
        with pytest.raises(TypeError):
            make_upload(123)

    def test_content_type(self, faker: Faker):
        """Content type is detected from the file content if not provided manually."""
        data = faker.json().encode()
        upload = make_upload(data)
        assert upload.content_type == "application/json"

    def test_manual_content_type(self, faker: Faker):
        """Manual content type overrides detected content type."""
        data = faker.json().encode()
        upload = make_upload(data, "image/png")
        assert upload.content_type == "image/png"
