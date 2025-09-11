"""Proxy-storage adapter."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any, ClassVar, cast

import file_keeper as fk


@dataclasses.dataclass
class Settings(fk.Settings):
    """Proxy settings."""

    options: dict[str, Any] = cast("dict[str, Any]", dataclasses.field(default_factory=dict))

    storage: fk.Storage = None  # pyright: ignore[reportAssignmentType]

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        if not self.storage:
            self.storage = fk.make_storage(self.name, self.options)


@fk.Storage.register
class ProxyStorage:
    """Wrapper for other storages."""

    hidden = True
    ProxySettingsFactory: ClassVar[type[Settings]] = Settings
    proxy_settings: Settings

    def __init__(self, settings: Mapping[str, Any] | Settings, /):
        self.proxy_settings = (  # pyright: ignore[reportAttributeAccessIssue]
            settings if isinstance(settings, Settings) else self.ProxySettingsFactory.from_dict(settings)
        )

    def __getattr__(self, name: str):
        return getattr(self.proxy_settings.storage, name)
