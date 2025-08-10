"""Plugin specification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pluggy import HookspecMarker

if TYPE_CHECKING:
    from file_keeper.core import storage, types, upload
    from file_keeper.core.registry import Registry


name = "file_keeper_ext"


hookspec = HookspecMarker(name)


@hookspec
def register_adapters(registry: Registry[type[storage.Storage]]):
    """Register storage adapters."""


@hookspec
def register_upload_factories(registry: Registry[upload.UploadFactory, type]):
    """Register upload factories.

    Example:
        ```py
        def register_upload_factories(registry):
            def string_into_upload(value: str):
                return bytes(value, "utf8")
            registry.register(str, string_into_upload)
        ```
    """


@hookspec
def register_location_transformers(registry: Registry[types.LocationTransformer]):
    """Register location transformers.

    Example:
        ```py
        def register_location_transformers(registry):
            def lower(location, upload, extras):
                return location.lower().

            registry.register("lower", lower)
        ```
    """
