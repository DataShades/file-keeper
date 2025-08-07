from __future__ import annotations

from collections.abc import Hashable, Mapping, MutableMapping
from typing import Callable, Generic

from typing_extensions import TypeVar

K = TypeVar("K", default=str, bound=Hashable)
V = TypeVar("V")


class Registry(Generic[V, K]):
    """Mutable collection of objects.

    Example:
        ```py
        col = Registry()

        col.register("one", 1)
        assert col.get("one") == 1

        col.reset()
        assert col.get("one") is None

        assert list(col) == ["one"]
        ```
    """

    members: MutableMapping[K, V]
    collector: Callable[[], Mapping[K, V]] | None

    def __init__(
        self,
        members: dict[K, V] | None = None,
        collector: Callable[[], Mapping[K, V]] | None = None,
    ):
        if members is None:
            members = {}
        self.members = members
        self.collector = collector

    def __len__(self):
        return len(self.members)

    def __bool__(self):
        return bool(self.members)

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, key: K):
        return self.members[key]

    def __contains__(self, item: K):
        return item in self.members

    def collect(self):
        if self.collector:
            self.members.update(self.collector())

    def reset(self):
        """Remove all members from registry."""
        self.members.clear()

    def register(self, key: K, member: V):
        """Add a member to registry."""
        self.members[key] = member

    def get(self, key: K) -> V | None:
        """Get the optional member from registry."""
        return self.members.get(key)

    def pop(self, key: K) -> V | None:
        """Remove the member from registry."""
        return self.members.pop(key, None)

    def decorated(self, key: K):
        def decorator(value: V):
            self.register(key, value)
            return value

        return decorator
