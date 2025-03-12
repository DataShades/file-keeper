from __future__ import annotations

import copy
import dataclasses
import glob
import logging
import os
import shutil
from io import BytesIO
from typing import IO, Any, ClassVar, Iterable

import magic

import file_keeper as fk

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Settings for FS storage.

    Args:
        create_path: create `path` if it does not exist
        recursive: expect files inside subfolders the `path`
        path: non-empty location for storage folder
    """

    create_path: bool = False
    recursive: bool = False
    path: str = ""

    _required_options: ClassVar[list[str]] = ["path"]


class Uploader(fk.Uploader):
    storage: FsStorage
    capabilities = fk.Capability.CREATE | fk.Capability.MULTIPART

    def upload(
        self,
        location: str,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Upload file to computed location.

        File is always stored under the configured `path`. If `recursive`
        uploads allowed, nested directories may be created.

        When an attempt to upload file using an absolute path or path that
        resolves to parent directory is detected, problematic part is stripped
        and only valid relative subpath is used.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            LocationError: unallowed usage of subdirectory

        Returns:
            New file data
        """
        subpath, basename = os.path.split(location)

        # TODO: consider adding `strict` option and report attempts to create
        # file outside of the storage location
        subpath = os.path.normpath(subpath).lstrip("./")

        if subpath and not self.storage.settings.recursive:
            raise fk.exc.LocationError(self.storage, subpath)

        location = os.path.join(subpath, basename)

        dest = os.path.join(self.storage.settings.path, location)

        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, dest)

        # `recursive` is checked earlier and either subpath is empty(no
        # directories created on the next line) or `reqursive` is
        # enabled(creation of intermediate path is allowed)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        reader = fk.HashingReader(upload.stream)
        with open(dest, "wb") as fd:
            for chunk in reader:
                fd.write(chunk)

        return fk.FileData(
            location,
            os.path.getsize(dest),
            upload.content_type,
            reader.get_hash(),
        )

    def multipart_start(
        self,
        location: str,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        """Create an empty file using `upload` method.

        Put `uploaded=0` into `data.storage_data` and copy the `location` from
        the newly created empty file.

        Returns:
            New file data
        """
        upload = fk.Upload(
            BytesIO(),
            location,
            data.size,
            data.content_type,
        )

        tmp_result = self.upload(location, upload, extras)

        data.location = tmp_result.location
        data.storage_data = dict(tmp_result.storage_data, uploaded=0)
        return data

    def multipart_refresh(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        """Synchronize `storage_data["uploaded"]` with actual value.

        Raises:
            MissingFileError: location does not exist

        Returns:
            Updated file data
        """
        filepath = os.path.join(
            self.storage.settings.path,
            data.location,
        )

        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, filepath)

        data.storage_data["uploaded"] = os.path.getsize(filepath)

        return data

    def multipart_update(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.MultipartData:
        """Add part to existing multipart upload.

        The content of upload is taken from `extras["upload"]`.

        By default, upload continues from the position specified by
        `storage_data["uploaded"]`. But if `extras["position"]` is set, it is
        used as starting point instead.

        In the end, `storage_data["uploaded"]` is set to the actial space taken
        by the file in the system after the update.

        Raises:
            UploadOutOfBoundError: part exceeds allocated file size
            MissingExtrasError: extra parameters are missing

        Returns:
            Updated file data
        """
        # this is the point from which upload continues. It is not used often,
        # but in specific scenario one can override previously uploaded part
        # rewinding the `position`.
        extras.setdefault("position", data.storage_data["uploaded"])

        if "upload" not in extras:
            raise fk.exc.MissingExtrasError("upload")

        upload: fk.Upload = extras["upload"]

        # when re-uploading existing parts via explicit `position`, `uploaded`
        # can be greater than `position` + part size. For example, existing
        # content is `hello world` with size 11. One can override the first
        # word by providing content `HELLO` and position 0, resulting in
        # `position` + part size equal 5, while existing upload size remains
        # 11.
        expected_size = max(
            extras["position"] + upload.size,
            data.storage_data["uploaded"],
        )

        if expected_size > data.size:
            raise fk.exc.UploadOutOfBoundError(expected_size, data.size)

        filepath = os.path.join(self.storage.settings.path, data.location)
        with open(filepath, "rb+") as dest:
            dest.seek(extras["position"])
            for chunk in upload.stream:
                dest.write(chunk)

        data.storage_data["uploaded"] = os.path.getsize(filepath)
        return data

    def multipart_complete(
        self,
        data: fk.MultipartData,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Finalize the upload.

        Raises:
            UploadSizeMismatchError: actual and expected sizes are different
            UploadTypeMismatchError: actual and expected content types are different
            UploadHashMismatchError: actual and expected content hashes are different

        Returns:
            File data
        """
        filepath = os.path.join(self.storage.settings.path, data.location)
        size = os.path.getsize(filepath)
        if size != data.size:
            raise fk.exc.UploadSizeMismatchError(size, data.size)

        with open(filepath, "rb") as src:
            reader = fk.HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            if data.content_type and content_type != data.content_type:
                raise fk.exc.UploadTypeMismatchError(
                    content_type,
                    data.content_type,
                )
            reader.exhaust()

        if data.hash and data.hash != reader.get_hash():
            raise fk.exc.UploadHashMismatchError(reader.get_hash(), data.hash)

        return fk.FileData(data.location, size, content_type, reader.get_hash())


class Manager(fk.Manager):
    storage: FsStorage
    capabilities = (
        fk.Capability.REMOVE
        | fk.Capability.SCAN
        | fk.Capability.EXISTS
        | fk.Capability.ANALYZE
        | fk.Capability.COPY
        | fk.Capability.MOVE
        | fk.Capability.COMPOSE
        | fk.Capability.APPEND
    )

    def compose(
        self,
        datas: Iterable[fk.FileData],
        location: str,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Combine multipe file inside the storage into a new one.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        dest = os.path.join(self.storage.settings.path, location)
        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, dest)

        sources: list[str] = []
        for data in datas:
            src = os.path.join(self.storage.settings.path, data.location)

            if not os.path.exists(src):
                raise fk.exc.MissingFileError(self.storage, src)
            sources.append(src)

        with open(dest, "wb") as to_fd:
            for src in sources:
                with open(src, "rb") as from_fd:
                    shutil.copyfileobj(from_fd, to_fd)

        return self.analyze(dest, extras)

    def append(
        self,
        data: fk.FileData,
        upload: fk.Upload,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Append content to existing file."""
        dest = os.path.join(self.storage.settings.path, data.location)
        with open(dest, "ab") as fd:
            fd.write(upload.stream.read())

        return self.analyze(dest, extras)

    def copy(
        self,
        data: fk.FileData,
        location: str,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Copy file inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        src = os.path.join(self.storage.settings.path, data.location)
        dest = os.path.join(self.storage.settings.path, location)

        if not os.path.exists(src):
            raise fk.exc.MissingFileError(self.storage, src)

        if os.path.exists(dest) and not self.storage.settings.override_existing:
            raise fk.exc.ExistingFileError(self.storage, dest)

        shutil.copy(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def move(
        self,
        data: fk.FileData,
        location: str,
        extras: dict[str, Any],
    ) -> fk.FileData:
        """Move file to a different location inside the storage.

        Raises:
            ExistingFileError: file exists and overrides are not allowed
            MissingFileError: source file does not exist
        """
        src = os.path.join(self.storage.settings.path, data.location)
        dest = os.path.join(self.storage.settings.path, location)

        if not os.path.exists(src):
            raise fk.exc.MissingFileError(self.storage, src)

        if os.path.exists(dest):
            if self.storage.settings.override_existing:
                os.remove(dest)
            else:
                raise fk.exc.ExistingFileError(self.storage, dest)

        shutil.move(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def exists(self, data: fk.FileData, extras: dict[str, Any]) -> bool:
        filepath = os.path.join(self.storage.settings.path, data.location)
        return os.path.exists(filepath)

    def remove(
        self, data: fk.FileData | fk.MultipartData, extras: dict[str, Any]
    ) -> bool:
        filepath = os.path.join(self.storage.settings.path, data.location)
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings.path
        search_path = os.path.join(path, "**")

        for entry in glob.glob(
            search_path,
            recursive=self.storage.settings.recursive,
        ):
            if not os.path.isfile(entry):
                continue
            yield os.path.relpath(entry, path)

    def analyze(self, location: str, extras: dict[str, Any]) -> fk.FileData:
        """Return all details about location.

        Raises:
            MissingFileError: file does not exist
        """
        filepath = os.path.join(self.storage.settings.path, location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, filepath)

        with open(filepath, "rb") as src:
            reader = fk.HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            reader.exhaust()

        return fk.FileData(
            location,
            size=os.path.getsize(filepath),
            content_type=content_type,
            hash=reader.get_hash(),
        )


class Reader(fk.Reader):
    storage: FsStorage
    capabilities = fk.Capability.STREAM | fk.Capability.TEMPORAL_LINK

    def stream(self, data: fk.FileData, extras: dict[str, Any]) -> IO[bytes]:
        """...

        Raises:
            MissingFileError: file does not exist
        """
        filepath = os.path.join(self.storage.settings.path, data.location)
        if not os.path.exists(filepath):
            raise fk.exc.MissingFileError(self.storage, filepath)

        return open(filepath, "rb")  # noqa: SIM115


class FsStorage(fk.Storage):
    """Store files in local filesystem."""

    settings: Settings  # type: ignore

    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader
    ManagerFactory = Manager

    @classmethod
    def configure(cls, settings: dict[str, Any]):
        """...

        Raises:
            InvalidStorageConfigurationError: incorrect configuration value
        """
        cfg: Settings = super().configure(settings)

        path = cfg.path

        if not os.path.exists(path):
            if cfg.create_path:
                os.makedirs(path)
            else:
                raise fk.exc.InvalidStorageConfigurationError(
                    cls,
                    f"path `{path}` does not exist",
                )

        return cfg
