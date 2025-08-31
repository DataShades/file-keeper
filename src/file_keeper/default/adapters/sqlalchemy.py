"""SQLAlchemy adapter."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Iterable
from typing import Any

import sqlalchemy as sa
from typing_extensions import override

import file_keeper as fk


@dataclasses.dataclass()
class Settings(fk.Settings):
    """SQLAlchemy settings."""

    db_url: str = ""
    """URL of the storage DB."""
    table_name: str = ""
    """Name of the storage table."""
    location_column: str = ""
    """Name of the column that contains file location."""
    content_column: str = ""
    """Name of the column that contains file content."""

    engine: sa.engine.Engine = None  # pyright: ignore[reportAssignmentType]
    """Existing DB engine."""
    table: sa.Table = None  # pyright: ignore[reportAssignmentType]
    """Existing DB table."""
    location: sa.Column[str] = None  # pyright: ignore[reportAssignmentType]
    """Existing column for location."""
    content: sa.Column[bytes] = None  # pyright: ignore[reportAssignmentType]
    """Existing column for content."""

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
    """SQLAlchemy reader."""

    storage: SqlAlchemyStorage
    capabilities: fk.Capability = fk.Capability.STREAM

    @override
    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        filepath = self.storage.full_path(data.location)

        stmt = (
            sa.select(self.storage.settings.content)
            .select_from(self.storage.settings.table)
            .where(self.storage.settings.location == filepath)
        )

        with self.storage.settings.engine.connect() as conn:
            row = conn.execute(stmt).fetchone()

        if row is None:
            raise fk.exc.MissingFileError(self, data.location)

        return row


class Uploader(fk.Uploader):
    """SQLAlchemy uploader."""

    storage: SqlAlchemyStorage
    capabilities: fk.Capability = fk.Capability.CREATE

    @override
    def upload(
        self,
        location: fk.types.Location,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        filepath = self.storage.full_path(location)
        reader = upload.hashing_reader()

        values: dict[Any, Any] = {
            self.storage.settings.location: filepath,
            self.storage.settings.content: reader.read(),
        }

        table = self.storage.settings.table

        with self.storage.settings.engine.begin() as conn:
            if conn.scalar(sa.select(1).select_from(table).where(self.storage.settings.location == filepath)):
                if self.storage.settings.override_existing:
                    stmt = sa.update(table).where(self.storage.settings.location == filepath).values(values)
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
    """SQLAlchemy manager."""

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
        srcpath = self.storage.full_path(data.location)
        destpath = self.storage.full_path(location)

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if self.exists(fk.FileData(location), extras):
            if self.storage.settings.override_existing:
                self.remove(fk.FileData(location), extras)
            else:
                raise fk.exc.ExistingFileError(self.storage, location)

        stmt = (
            sa.update(self.storage.settings.table)
            .where(self.storage.settings.location == srcpath)
            .values({self.storage.settings.location: destpath})
        )
        with self.storage.settings.engine.begin() as conn:
            conn.execute(stmt)

        return fk.FileData.from_object(data, location=location)

    @override
    def copy(self, location: fk.Location, data: fk.FileData, extras: dict[str, Any]) -> fk.FileData:
        srcpath = self.storage.full_path(data.location)
        destpath = self.storage.full_path(location)

        if not self.exists(data, extras):
            raise fk.exc.MissingFileError(self.storage, data.location)

        if self.exists(fk.FileData(location), extras):
            if self.storage.settings.override_existing:
                self.remove(fk.FileData(location), extras)
            else:
                raise fk.exc.ExistingFileError(self.storage, location)

        with self.storage.settings.engine.begin() as conn:
            content = conn.scalar(
                sa.select(self.storage.settings.content).where(self.storage.settings.location == srcpath)
            )

            conn.execute(
                sa.insert(self.storage.settings.table).values(
                    {
                        self.storage.settings.location: destpath,
                        self.storage.settings.content: content,
                    }
                )
            )

        return fk.FileData.from_object(data, location=location)

    @override
    def analyze(self, location: fk.Location, extras: dict[str, Any]) -> fk.FileData:
        filepath = self.storage.full_path(location)

        stmt = sa.select(self.storage.settings.content).where(self.storage.settings.location == filepath)
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
        filepath = self.storage.full_path(data.location)
        stmt = sa.select(1).select_from(self.storage.settings.table).where(self.storage.settings.location == filepath)
        with self.storage.settings.engine.connect() as conn:
            return bool(conn.scalar(stmt))

    @override
    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        stmt = sa.select(self.storage.settings.location).select_from(self.storage.settings.table)
        path = self.storage.settings.path
        # do not add slash when path empty, because it will change it from
        # "current directory" to the "root directory"
        if path:
            path = path.rstrip("/") + "/"

        with self.storage.settings.engine.connect() as conn:
            for row in conn.execute(stmt):
                if row[0].startswith(path):
                    yield os.path.relpath(row[0], path)

    @override
    def remove(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = self.storage.full_path(data.location)
        if not self.exists(data, extras):
            return False

        stmt = sa.delete(self.storage.settings.table).where(
            self.storage.settings.location == filepath,
        )
        with self.storage.settings.engine.begin() as conn:
            conn.execute(stmt)
        return True


class SqlAlchemyStorage(fk.Storage):
    """SQLAlchemy storage.

    This storage uses a SQL database to store files as BLOBs. It requires SQLAlchemy
    to be installed.

    Example configuration:

    ```py
    import file_keeper as fk

    settings = {
        "type": "file_keeper:sqlalchemy",
        "db_url": "sqlite:///file_keeper.db",
        "table_name": "files",
        "location_column": "location",
        "content_column": "content",
        "override_existing": True,
        "initialize": True,
    }

    storage = fk.make_storage("sqlalchemy", settings)
    ```

    Note:
    * The `db_url` setting specifies the database connection URL.
    * The `table_name`, `location_column`, and `content_column` settings specify
      the table and column names to use for storing files.
    * If the specified table does not exist and `initialize` is set to `True`,
        it will be created automatically.
    * If `override_existing` is set to `True`, existing files will be overwritten
        during upload, copy, or move operations.
    """

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader
