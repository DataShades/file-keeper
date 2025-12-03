# Contributing to file-keeper

Thank you for your interest in contributing to file-keeper! This document provides guidelines and instructions to help you contribute effectively.

## Table of Contents
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Pull Request Guidelines](#pull-request-guidelines)

## Development Setup

1. Fork the repository on GitHub
2. Clone your forked repository:
   ```bash
   git clone https://github.com/your-username/file-keeper.git
   cd file-keeper
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. Install the package in development mode:
   ```bash
   make install-dev
   ```
   or
   ```bash
   pip install -e '.[dev]'
   ```

## Code Style

We use several tools to maintain code quality:

- **Ruff** for linting and formatting
- **Pyright** for type checking

Before submitting changes, please run:
```bash
make check
```

To format your code:
```bash
make format
```

To run type checks:
```bash
make type-check
```

## Testing

All changes should include appropriate tests. Run the test suite before submitting:

```bash
make test
```

Or run specific tests:
```bash
pytest tests/test_specific_file.py
```

When adding new functionality, please include tests that cover:
- Normal operation
- Edge cases
- Error conditions

## Submitting Changes

1. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   or
   ```bash
   git checkout -b bugfix/your-bugfix-name
   ```

2. Make your changes, following the style guide
3. Add or update tests as needed
4. Run all checks:
   ```bash
   make check
   make test
   ```
5. Commit your changes with a clear, descriptive commit message
6. Push your branch to your fork
7. Open a pull request to the main repository

## Pull Request Guidelines

- Keep pull requests focused on a single feature or bug fix
- Update documentation as needed
- Follow the existing code style
- Include tests for new functionality
- Update the changelog if your change affects users
- Ensure all CI checks pass

## Development Commands

Use the following `make` commands to help with development:

- `make install-dev` - Install development dependencies
- `make test` - Run tests
- `make lint` - Run linter
- `make format` - Format code
- `make type-check` - Run type checker
- `make check` - Run all checks
