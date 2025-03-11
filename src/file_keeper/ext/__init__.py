from __future__ import annotations
from pluggy import PluginManager
from pluggy import HookimplMarker
from . import spec
from file_keeper.core import registry

hookimpl = HookimplMarker(spec.name)
plugin = PluginManager(spec.name)
plugin.add_hookspecs(spec)

plugin.load_setuptools_entrypoints(spec.name)
plugin.hook.register_location_strategies(registry=registry.location_strategies)
plugin.hook.register_upload_factories(registry=registry.upload_factories)
plugin.hook.register_adapters(registry=registry.adapters)
