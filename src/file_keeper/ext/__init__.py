from __future__ import annotations

import os

from pluggy import HookimplMarker, PluginManager

from file_keeper.core import storage, upload

from . import spec

hookimpl = HookimplMarker(spec.name)
plugin = PluginManager(spec.name)
plugin.add_hookspecs(spec)


def setup():
    plugin.load_setuptools_entrypoints(spec.name)
    plugin.hook.register_location_strategies(registry=storage.location_strategies)
    plugin.hook.register_upload_factories(registry=upload.upload_factories)
    plugin.hook.register_adapters(registry=storage.adapters)


if not os.getenv("FILE_KEEPER_NO_SETUP"):
    setup()
