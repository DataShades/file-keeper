from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from typing import Any

import sqlalchemy as sa
from typing_extensions import override

import file_keeper as fk


@dataclasses.dataclass()
class Settings(fk.Settings):
    db_url: str = ""
    table_name: str = ""
    location_column: str = ""
    content_column: str = ""

    engine: sa.engine.Engine = None  # pyright: ignore[reportAssignmentType]
    table: sa.Table = None  # pyright: ignore[reportAssignmentType]
    location: sa.Column[str] = None  # pyright: ignore[reportAssignmentType]
    content: sa.Column[bytes] = None  # pyright: ignore[reportAssignmentType]

    def __post_init__(self, **kwargs: Any):  # noqa: C901, PLR0912
        super().__post_init__(**kwargs)

        if not self.engine:
            if not self.db_url:
                raise fk.exc.MissingStorageConfigurationError(self.name, "db_url")
            self.engine = sa.create_engine(self.db_url)

        if self.location is None:  # pyright: ignore[reportUnnecessaryComparison]
            if not self.location_column:
                raise fk.exc.MissingStorageConfigurationError(self.name, "location_column")
            self.location = sa.Column(self.location_column, sa.Text, primary_key=True)
        else:
            self.location_column = self.location.name

        if self.content is None:  # pyright: ignore[reportUnnecessaryComparison]
            if not self.content_column:
                raise fk.exc.MissingStorageConfigurationError(self.name, "content_column")
            self.content = sa.Column(self.content_column, sa.LargeBinary)
        else:
            self.content_column = self.content.name

        if self.table is None:  # pyright: ignore[reportUnnecessaryComparison]
            if not self.table_name:
                raise fk.exc.MissingStorageConfigurationError(self.name, "table_name")

            self.table = sa.Table(
                self.table_name,
                sa.MetaData(),
                self.location,
                self.content,
            )
        else:
            self.table_name = self.table.name

        inspector = sa.inspect(self.engine)
        if not inspector.has_table(self.table.name):
            if self.initialize:
                self.table.create(self.engine)
            else:
                raise fk.exc.InvalidStorageConfigurationError(self.name, f"table {self.table.name} does not exist")


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

        table = self.storage.settings.table

        with self.storage.settings.engine.begin() as conn:
            if conn.scalar(sa.select(1).select_from(table).where(self.storage.settings.location == location)):
                if self.storage.settings.override_existing:
                    stmt = sa.update(table).where(self.storage.settings.location == location).values(values)
                    conn.execute(stmt)
                else:
                    raise fk.exc.ExistingFileError(self.storage, location)
            else:
                stmt = sa.insert(self.storage.settings.table).values(values)
                conn.execute(stmt)

        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            reader.get_hash(),
        )


class Manager(fk.Manager):
    storage: SqlAlchemyStorage
    capabilities: fk.Capability = (
        fk.Capability.SCAN
        | fk.Capability.REMOVE
        | fk.Capability.EXISTS
        | fk.Capability.ANALYZE
        | fk.Capability.COPY
        | fk.Capability.MOVE
    )

    @override
    def move(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if self.exists(fk.FileData(location), extras):
            if self.storage.settings.override_existing:
                self.remove(fk.FileData(location), extras)
            else:
                raise fk.exc.ExistingFileError(self.storage, location)

        stmt = (
            sa.update(self.storage.settings.table)
            .where(self.storage.settings.location == data.location)
            .values({self.storage.settings.location: location})
        )
        with self.storage.settings.engine.begin() as conn:
            conn.execute(stmt)

        return fk.FileData.from_object(data, location=location)

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if self.exists(fk.FileData(location), extras):
            if self.storage.settings.override_existing:
                self.remove(fk.FileData(location), extras)
            else:
                raise fk.exc.ExistingFileError(self.storage, location)

        with self.storage.settings.engine.begin() as conn:
            content = conn.scalar(
                sa.select(self.storage.settings.content).where(self.storage.settings.location == data.location)
            )

            conn.execute(
                sa.insert(self.storage.settings.table).values(
                    {
                        self.storage.settings.location: location,
                        self.storage.settings.content: content,
                    }
                )
            )

        return fk.FileData.from_object(data, location=location)

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        stmt = sa.select(self.storage.settings.content).where(self.storage.settings.location == location)
        with self.storage.settings.engine.connect() as conn:
            content = conn.scalar(stmt)

        if not content:
            raise fk.exc.MissingFileError(self.storage, location)

        upload = fk.make_upload(content)
        reader = upload.hashing_reader()
        reader.exhaust()
        return fk.FileData(
            location,
            upload.size,
            upload.content_type,
            reader.get_hash(),
        )

    @override
    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        stmt = (
            sa.select(1).select_from(self.storage.settings.table).where(self.storage.settings.location == data.location)
        )
        with self.storage.settings.engine.connect() as conn:
            return bool(conn.scalar(stmt))

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        stmt = sa.select(self.storage.settings.location).select_from(self.storage.settings.table)
        with self.storage.settings.engine.connect() as conn:
            for row in conn.execute(stmt):
                yield row[0]

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        if not self.exists(data, extras):
            return False

        stmt = sa.delete(self.storage.settings.table).where(
            self.storage.settings.location == data.location,
        )
        with self.storage.settings.engine.begin() as conn:
            conn.execute(stmt)
        return True


class SqlAlchemyStorage(fk.Storage):
    hidden = True
    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
