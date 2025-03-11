from __future__ import annotations

from collections.abc import Hashable
from typing import TYPE_CHECKING, Any, Callable, Generic
from typing_extensions import TypeAlias, TypeVar

if TYPE_CHECKING:
    import io
    from .upload import Upload
    from .storage import Storage

K = TypeVar("K", default=str, bound=Hashable)
V = TypeVar("V")
UploadFactory: TypeAlias = "Callable[[Any], Upload | io.BytesIO | io.BufferedReader | bytes | bytearray | None]"
LocationStrategy: TypeAlias = Callable[[str, "Upload | None", "dict[str, Any]"], str]


class Registry(Generic[V, K]):
    """Mutable collection of objects.

    Example:
    >>> col = Registry()
    >>>
    >>> col.register("one", 1)
    >>> assert col.get("one") == 1
    >>>
    >>> col.reset()
    >>> assert col.get("one") is None
    """

    def __init__(
        self,
        members: dict[K, V] | None = None,
        collector: Callable[[], dict[K, V]] | None = None,
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



upload_factories: Registry[UploadFactory, type] = Registry(
)

adapters = Registry["type[Storage[Any]]"]()

location_strategies = Registry[LocationStrategy]()
