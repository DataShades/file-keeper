from __future__ import annotations

import dataclasses
from typing import Any, ClassVar, Iterable

import sqlalchemy as sa

import file_keeper as fk


@dataclasses.dataclass()
class Settings(fk.Settings):
    db_url: str = ""
    table_name: str = ""
    location_column: str = ""
    content_column: str = ""

    engine: sa.Engine = None  # type: ignore
    table: Any = None
    location: Any = None
    content: Any = None

    _required_options: ClassVar[list[str]] = [
        "db_url",
        "table",
        "location_column",
        "content_column",
    ]

    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        self.engine = sa.create_engine(self.db_url)
        self.location = sa.column(self.location_column)
        self.content = sa.column(self.content_column)
        self.table = sa.table(
            self.table_name,
            self.location,
            self.content,
        )


class Reader(fk.Reader):
    storage: SqlAlchemyStorage
    capabilities = fk.Capability.STREAM

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        stmt = (
            sa.select(self.storage.settings.content)
            .select_from(self.storage.settings.table)
            .where(self.storage.settings.location == data.location)
        )

        with self.storage.settings.engine.connect() as conn:
            row = conn.execute(stmt).fetchone()

        if row is None:
            raise fk.exc.MissingFileError(self, data.location)

        return row


class Uploader(fk.Uploader):
    storage: SqlAlchemyStorage
    capabilities = fk.Capability.CREATE

    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        reader = upload.hashing_reader()

        values: dict[Any, Any] = {
            self.storage.settings.location_column: location,
            self.storage.settings.content_column: reader.read(),
        }
        stmt = sa.insert(self.storage.settings.table).values(values)

        with self.storage.settings.engine.connect() as conn:
            conn.execute(stmt)

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            reader.get_hash(),
        )


class Manager(fk.Manager):
    storage: SqlAlchemyStorage
    capabilities = fk.Capability.SCAN | fk.Capability.REMOVE

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        stmt = sa.select(self.storage.settings.location).select_from(
            self.storage.settings.table
        )
        with self.storage.settings.engine.connect() as conn:
            for row in conn.execute(stmt):
                yield row[0]

    def remove(
        self,
        data: fk.FileData | fk.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        stmt = sa.delete(self.storage.settings.table).where(
            self.storage.settings.location == data.location,
        )
        with self.storage.settings.engine.connect() as conn:
            conn.execute(stmt)
        return True


class SqlAlchemyStorage(fk.Storage):
    hidden = True
    settings: Settings  # type: ignore
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
