from __future__ import annotations

from typing import TYPE_CHECKING

from pluggy import HookspecMarker

if TYPE_CHECKING:
    from file_keeper.core import storage, types, upload
    from file_keeper.core.registry import Registry


name = "file_keeper_ext"


hookspec = HookspecMarker(name)


@hookspec
def register_adapters(registry: Registry[type[storage.Storage]]): ...


@hookspec
def register_upload_factories(registry: Registry[upload.UploadFactory, type]): ...


@hookspec
def register_location_transformers(registry: Registry[types.LocationTransformer]): ...
