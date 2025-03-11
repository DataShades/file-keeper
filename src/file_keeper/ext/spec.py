from __future__ import annotations
from typing import TYPE_CHECKING
from pluggy import HookspecMarker

if TYPE_CHECKING:
    from file_keeper.core.storage import Storage
    from file_keeper.core.registry import LocationStrategy, UploadFactory, Registry


name = "file_keeper_ext"


hookspec = HookspecMarker(name)


@hookspec
def register_adapters(registry: Registry[type[Storage]]): ...


@hookspec
def register_upload_factories(registry: Registry[UploadFactory, type]): ...


@hookspec
def register_location_strategies(registry: Registry[LocationStrategy]): ...
