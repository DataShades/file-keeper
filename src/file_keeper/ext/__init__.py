from __future__ import annotations
from pluggy import PluginManager
from pluggy import HookimplMarker
from . import spec

hookimpl = HookimplMarker(spec.name)
plugin = PluginManager(spec.name)
plugin.add_hookspecs(spec)
