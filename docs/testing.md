# Testing

This document outlines the recommended approach for writing tests for new
storage adapters within the `file_keeper` project.  The goal is to ensure
consistent behavior and adherence to the defined capabilities.

## Core Principles

Tests should primarily focus on verifying that an adapter correctly implements
the capabilities. Validate the *behavior* of the adapter, not necessarily the
internal implementation details. User has certain expectations depending on the
storage capabilities and assumes that two different storage adapters with same
capabilities behave identically in similar conditions. That's why testing
publicly exposed interface is the highest priority.

## The `Standard` Class and Inheritance

The `tests/file_keeper/default/adapters/standard.py` file provides a `Standard`
class that serves as a foundation for testing adapters. This class encapsulates
a comprehensive suite of tests covering various storage capabilities.

/// admonition
    type: tip

When creating tests for a new adapter, **inherit from the `Standard`
class**. This automatically provides a significant amount of pre-built test
coverage.  You only need to override or add tests to address specific adapter
behavior or unique capabilities.

///


The `Standard` class defines a series of test methods (e.g.,
`test_append_content`, `test_remove_real`, `test_move_missing`). Each test
specifies capabilities required for verification and is automatically skipped
if given capabilities are not supported by the storage.

If all the required capabilities are supported, test verifies that
implementation of capability is predictable. For example:

* REMOVE: returns `True` when removing real file and `False` if file does not exists
* CREATE: raises [ExistingFileError][file_keeper.exc.ExistingFileError] if file
  already exists at the given location and
  [override_existing][file_keeper.Settings.override_existing] option is not
  enabled
* STREAM: output of [stream()][file_keeper.Storage.stream] and
  [content()][file_keeper.Storage.content] is the same
* ANALYZE: content hash of the file is the same as one, computed during the upload


/// note

`Standard` class covers only adapter-agnostic functionality and it does not
verify internal processes of the storage.

Testing that filesystem storage actually writes data into the configured
directory and cloud storage communicates with the cloud provider is still
required. But these tests must be implemented individually for each provider
and they are not included into generic `Standard` class.

///

## Writing New Tests

### Create a Test Class

Create a new test class that inherits from `Standard`.

```py
from tests.file_keeper.default.adapters.standard import Standard
import pytest

class MyStorageAdapterTests(Standard):
    # Your tests here
    pass
```

### Override Existing Tests (if necessary)

If your adapter has specific behavior in addition to the default
implementation, override the corresponding test method in the `Standard` class.
Be sure to call `super()` to execute the original test logic first, and then
add your custom assertions.

```py
class MyStorageAdapterTests(Standard):
    def test_create_content_non_modified(self, storage: fk.Storage, faker: Faker):
        super().test_create_content_non_modified(storage, faker)
        # Add custom assertions specific to your adapter
        assert "some_adapter_specific_check" in storage.content(result)
```

### Add New Tests

If your adapter supports new capabilities or has unique behavior that is not
covered by the `Standard` class, add new test methods to your test class.

```py
class MyStorageAdapterTests(Standard):

    def test_my_custom_behavior(self, storage: fk.Storage, faker: Faker):
        # Your test logic here
        assert True
```
