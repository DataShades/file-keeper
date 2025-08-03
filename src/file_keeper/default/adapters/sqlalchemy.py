from __future__ import annotations

from collections.abc import Iterable
import dataclasses
from typing import Any, ClassVar

import sqlalchemy as sa
from typing_extensions import override

import file_keeper as fk


@dataclasses.dataclass()
class Settings(fk.Settings):
    db_url: dataclasses.InitVar[str] = ""
    table_name: dataclasses.InitVar[str] = ""
    location_column: dataclasses.InitVar[str] = ""
    content_column: dataclasses.InitVar[str] = ""

    engine: sa.engine.Engine = None  # pyright: ignore[reportAssignmentType]
    table: sa.TableClause = None  # pyright: ignore[reportAssignmentType]
    location: sa.ColumnClause[str] = None  # pyright: ignore[reportAssignmentType]
    content: sa.ColumnClause[bytes] = None  # pyright: ignore[reportAssignmentType]

    _required_options: ClassVar[list[str]] = [
        "db_url",
        "table",
        "location_column",
        "content_column",
    ]

    def __post_init__(
        self,
        db_url: str,
        table_name: str,
        location_column: str,
        content_column: str,
        **kwargs: Any,
    ):
        super().__post_init__(**kwargs)

        if not self.engine:
            self.engine = sa.create_engine(db_url)
        if self.location is None:  # pyright: ignore[reportUnnecessaryComparison]
            self.location = sa.column(location_column)
        if self.content is None:  # pyright: ignore[reportUnnecessaryComparison]
            self.content = sa.column(content_column)
        if self.table is None:  # pyright: ignore[reportUnnecessaryComparison]
            self.table = sa.table(
                table_name,
                self.location,
                self.content,
            )


class Reader(fk.Reader):
    storage: SqlAlchemyStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
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
    capabilities: fk.Capability = fk.Capability.CREATE

    @override
    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        reader = upload.hashing_reader()

        values: dict[Any, Any] = {
            self.storage.settings.location: location,
            self.storage.settings.content: reader.read(),
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
    capabilities: fk.Capability = fk.Capability.SCAN | fk.Capability.REMOVE

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        stmt = sa.select(self.storage.settings.location).select_from(
            self.storage.settings.table
        )
        with self.storage.settings.engine.connect() as conn:
            for row in conn.execute(stmt):
                yield row[0]

    @override
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
    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
