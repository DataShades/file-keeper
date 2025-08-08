from __future__ import annotations

import file_keeper as fk

# settings:
# * adapter(str)
# * options(dict)


@fk.Storage.register
class ProxyStorage:
    hidden = True
