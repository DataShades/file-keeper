from __future__ import annotations
from typing import TYPE_CHECKING
from pluggy import HookspecMarker

if TYPE_CHECKING:
    from file_keeper.storage import Storage
    from file_keeper.registry import LocationStrategy, UploadFactory


name = "file_keeper_ext"


hookspec = HookspecMarker(name)


@hookspec
def collect_adapters() -> dict[str, type[Storage]]: ...


@hookspec
def collect_upload_factories() -> dict[type, UploadFactory]: ...


@hookspec
def collect_location_strategies() -> dict[str, LocationStrategy]: ...
