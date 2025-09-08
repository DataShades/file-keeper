"""Initialization of file-keepers extensions."""

from __future__ import annotations

import logging
import os

from pluggy import HookimplMarker, PluginManager

from file_keeper.core import storage, upload, utils

from . import spec

hookimpl = HookimplMarker(spec.name)
plugin = PluginManager(spec.name)
plugin.add_hookspecs(spec)
log = logging.getLogger(__name__)


@utils.run_once
def setup():
    """Discover and register file-keeper extensions."""
    try:
        plugin.load_setuptools_entrypoints(spec.name)
    except ModuleNotFoundError:
        msg = (
            "File-keeper extension is missing, try to re-install the problematic package."
            + " Only default adapters will be loaded"
        )
        log.exception(msg)
        plugin.load_setuptools_entrypoints(spec.name, "default")
    for name in os.getenv("FILE_KEEPER_DISABLED_EXTENSIONS", "").split():
        undesired = plugin.get_plugin(name)
        if plugin.is_registered(undesired):
            plugin.unregister(undesired)

    register(True)


def register(reset: bool = False):
    """Register built-in units."""
    if reset:
        storage.location_transformers.reset()
        upload.upload_factories.reset()
        storage.adapters.reset()
    plugin.hook.register_location_transformers(registry=storage.location_transformers)
    plugin.hook.register_upload_factories(registry=upload.upload_factories)
    plugin.hook.register_adapters(registry=storage.adapters)


if os.getenv("FILE_KEEPER_AUTO_SETUP"):
    setup()
