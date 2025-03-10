from collections.abc import Iterable
import hashlib
from io import BytesIO

import pytest
from faker import Faker
from file_keeper import (
    Registry,
    HashingReader,
    Capability,
    parse_filesize,
    is_supported_type,
)
from file_keeper.utils import humanize_filesize


class TestRegistry:
    def test_missing_key(self, faker: Faker):
        registry = Registry[object]()
        key = faker.word()

        assert registry.get(key) is None
        with pytest.raises(KeyError):
            registry[key]

    def test_existing_key(self, faker: Faker):
        registry = Registry[object]()
        key = faker.word()
        value = object()

        registry.register(key, value)
        assert registry.get(key) is value
        assert registry[key] is value

    def test_listing_and_reset(self, faker: Faker):
        registry = Registry[object]()
        key = faker.word()
        registry.register(key, object())

        assert list(registry) == [key]
        registry.reset()
        assert list(registry) == []

    def test_removal(self, faker: Faker):
        registry = Registry[object]()
        key = faker.word()
        value = object()
        registry.register(key, value)

        assert registry.pop(key) is value
        assert registry.pop(key) is None

    def test_decorator(self, faker: Faker):
        registry = Registry[object]()
        key = faker.word()

        @registry.decorated(key)
        def value():
            pass

        assert registry[key] is value


class TestHasingReader:
    def test_empty_hash(self):
        """Empty reader produces the hash of empty string."""
        reader = HashingReader(BytesIO())
        reader.exhaust()

        assert reader.get_hash() == hashlib.md5().hexdigest()

    def test_hash(self, faker: Faker):
        """Reader's hash is based on the stream content."""
        content = faker.binary(100)
        expected = hashlib.md5(content).hexdigest()

        reader = HashingReader(BytesIO(content))

        output = b""
        for chunk in reader:
            output += chunk

        assert output == content
        assert reader.get_hash() == expected


@pytest.mark.parametrize(
    ["type", "supported", "outcome"],
    [
        ("text/csv", ["csv"], True),
        ("text/csv", ["json", "text"], True),
        ("text/csv", ["application/json", "text/plain", "text/csv", "image/png"], True),
        ("text/csv", ["json", "image"], False),
        ("text/csv", ["application/csv"], False),
        ("text/csv", ["text/plain"], False),
        ("text/csv", ["non-csv"], False),
    ],
)
def test_is_supported_type(type: str, supported: Iterable[str], outcome: bool):
    assert is_supported_type(type, supported) is outcome


class TestCapabilities:
    def test_not_intersecting_exclusion(self):
        """Nothing changes when non-existing unit excluded."""
        cluster = Capability.CREATE | Capability.REMOVE

        assert Capability.exclude(cluster, Capability.MULTIPART) is cluster

    def test_exclusion_of_single_unit(self):
        """Single unit exclusion leaves all other units inside cluster."""
        cluster = Capability.CREATE | Capability.REMOVE

        assert Capability.exclude(cluster, Capability.CREATE) is Capability.REMOVE

    def test_multi_unit_exclusion(self):
        """Multiple units can be excluded at once."""
        cluster = Capability.CREATE | Capability.REMOVE | Capability.STREAM
        assert (
            Capability.exclude(cluster, Capability.REMOVE, Capability.CREATE)
            == Capability.STREAM
        )

    def test_exclusion_of_cluster(self):
        """The whole cluster can be excluded at once."""
        cluster = Capability.CREATE | Capability.REMOVE | Capability.STREAM

        empty = Capability.exclude(cluster, Capability.CREATE | Capability.STREAM)
        assert empty == Capability.REMOVE

    def test_can_single_capability(self):
        """Individual capabilites are identified in cluster."""
        cluster = Capability.CREATE | Capability.REMOVE
        assert cluster.can(Capability.CREATE)
        assert cluster.can(Capability.REMOVE)
        assert not cluster.can(Capability.STREAM)

    def test_can_cluster_capability(self):
        """Cluster capabilites are identified in cluster."""
        cluster = Capability.CREATE | Capability.REMOVE | Capability.STREAM

        assert cluster.can(Capability.CREATE | Capability.REMOVE)
        assert not cluster.can(Capability.CREATE | Capability.MOVE)


class TestParseFilesize:
    @pytest.mark.parametrize(
        ("value", "size"),
        [
            ("1", 1),
            ("1b", 1),
            ("1kb", 10**3),
            ("1kib", 2**10),
            ("1mb", 10**6),
            ("1mib", 2**20),
            ("1gb", 10**9),
            ("1gib", 2**30),
            ("1tb", 10**12),
            ("1tib", 2**40),
            ("  117  ", 117),
            ("0.7 mib", 734003),
            ("1 kib", 1024),
            ("10.43 kib", 10680),
            ("1024b", 1024),
            ("11 GiB", 11811160064),
            ("117 b", 117),
            ("117 kib", 119808),
            ("117b", 117),
            ("117kib", 119808),
            ("11GiB", 11811160064),
            ("1mib", 1048576),
            ("343.1MiB", 359766425),
            ("5.2 mib", 5452595),
            ("58 kib", 59392),
        ],
    )
    def test_valid_sizes(self, value: str, size: int):
        """Human-readable filesize is parsed into number of bytes."""
        assert parse_filesize(value) == size

    def test_empty_string(self):
        """Empty string causes an exception."""
        with pytest.raises(ValueError):  # noqa: PT011
            parse_filesize("")

    def test_invalid_multiplier(self):
        """Empty string causes an exception."""
        with pytest.raises(ValueError):  # noqa: PT011
            parse_filesize("1PB")


class TestHumanizeFilesize:
    @pytest.mark.parametrize(
        ("text", "size", "base"),
        [
            ("1B", 1, 1000),
            ("1B", 1, 1024),
            ("1KB", 10**3, 1000),
            ("1KiB", 2**10, 1024),
            ("1MB", 10**6, 1000),
            ("1MiB", 2**20, 1024),
            ("1GB", 10**9, 1000),
            ("1GiB", 2**30, 1024),
            ("1TB", 10**12, 1000),
            ("1TiB", 2**40, 1024),
            ("117B", 117, 1000),
            ("716.79KiB", 734003, 1024),
            ("1KiB", 1024, 1024),
            ("10.42KiB", 10680, 1024),
            ("1.02KB", 1024, 1000),
            ("11GiB", 11811160064, 1024),
            ("117B", 117, 1000),
            ("117KiB", 119808, 1024),
            ("117B", 117, 1000),
            ("117KiB", 119808, 1024),
            ("11GiB", 11811160064, 1024),
            ("1MiB", 1048576, 1024),
            ("343.09MiB", 359766425, 1024),
            ("5.19MiB", 5452595, 1024),
            ("58KiB", 59392, 1024),
        ],
    )
    def test_valid_bases(self, text: str, size: int, base: int):
        assert humanize_filesize(size, base) == text

    def test_invalid_base(self):
        with pytest.raises(ValueError):  # noqa: PT011
            humanize_filesize(1, 42)
