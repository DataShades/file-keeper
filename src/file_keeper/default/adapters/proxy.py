"""Proxy-storage adapter."""
from __future__ import annotations

import file_keeper as fk

# settings:
# * adapter(str)
# * options(dict)


@fk.Storage.register
class ProxyStorage:
    """Wrapper for other storages."""
    hidden = True
