import pytest
from faker import Faker

from file_keeper import Registry


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

    def test_bool(self):
        empty = Registry[object]()
        assert not empty

        non_empty = Registry[object]({"test": object()})
        assert non_empty

    def test_collect(self):
        registry = Registry[int](collector=lambda: {"test": 42})
        assert not registry.get("test")

        registry.collect()
        assert registry["test"] == 42
