# Glossary

Definitions of key terms used in file-keeper documentation.

## A

**Adapter** - A concrete implementation of the Storage interface that connects to a specific storage backend (e.g., S3, filesystem, memory).

## C

**Capability** - A flag indicating what operations a storage backend supports. Examples include CREATE, READ, UPDATE, DELETE, and more specialized operations.

**Configuration** - Settings that define how a storage adapter behaves, including connection details, paths, and options.

## D

**Data Model** - The structure used to represent file information consistently across all storage backends.

**FileData** - A data class containing metadata about a stored file, including location, size, content type, and hash.

## L

**Location** - A string identifier that uniquely identifies a file within a storage backend. This could be a file path, object key, or other identifier depending on the backend.

## S

**Settings** - The configuration object used to initialize a storage adapter.

**Storage** - The main interface for interacting with a file storage backend. Provides methods for uploading, downloading, and managing files.

**Storage Service** - Components of a storage implementation that handle specific types of operations (Uploader, Manager, Reader).

## U

**Upload** - An object representing data to be stored, including the content and metadata about the file.

**Uploader** - A service responsible for writing data to storage.

## R

**Reader** - A service responsible for reading data from storage.

## M

**Manager** - A service responsible for maintenance operations like copying, moving, and deleting files.
