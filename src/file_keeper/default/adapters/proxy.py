from __future__ import annotations

import file_keeper as fk


@fk.Storage.register
class ProxyStorage:
    hidden = True
