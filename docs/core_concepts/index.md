# Core Concepts

file-keeper is built around three fundamental concepts that work together to provide a unified interface for file storage across multiple backends. Understanding these concepts is essential for effectively using the library.

## Overview

The three core concepts are:

- **[Data Model](data_model.md)**: How file information is represented and managed
- **[Capabilities](capabilities.md)**: How different storage backends declare their supported operations
- **[Uploads](uploads.md)**: How data flows from your application to storage

These concepts work together to provide a consistent abstraction layer regardless of the underlying storage system.

## How They Work Together

1. **Data Model** provides the standardized representation of files (`FileData`) that remains consistent across all storage backends
2. **Capabilities** enable the library to adapt its behavior based on what operations each storage system supports
3. **Uploads** handle the transport of data from your application to the storage system, with appropriate buffering and integrity checking

This architecture allows file-keeper to provide a uniform API while maximizing the efficiency of each storage backend's native capabilities.