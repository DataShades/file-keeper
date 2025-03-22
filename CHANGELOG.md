# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [v0.0.4](https://github.com/DataShades/file-keeper/releases/tag/v0.0.4) - 2025-03-23

<small>[Compare with v0.0.3](https://github.com/DataShades/file-keeper/compare/v0.0.3...v0.0.4)</small>

### Features

- storages accept any type of upload ([a64ee3d](https://github.com/DataShades/file-keeper/commit/a64ee3da989930201964f22b4f32c62641da9294) by Sergey Motornyuk).

### Code Refactoring

- remove validation from storage ([93392f9](https://github.com/DataShades/file-keeper/commit/93392f9d8473a913623b8dd35cd202d35b4368ec) by Sergey Motornyuk).
- remove type and size validation from append and compose ([890c89a](https://github.com/DataShades/file-keeper/commit/890c89a8109c64f2a783c6b8dcd0c59d4c94cd89) by Sergey Motornyuk).
- remove public link method and capability ([cb39151](https://github.com/DataShades/file-keeper/commit/cb39151fb7e09cfdf3b9cdf0d3e2d98ba519edbe) by Sergey Motornyuk).

## [v0.0.3](https://github.com/DataShades/file-keeper/releases/tag/v0.0.3) - 2025-03-19

<small>[Compare with v0.0.2](https://github.com/DataShades/file-keeper/compare/v0.0.2...v0.0.3)</small>

## [v0.0.2](https://github.com/DataShades/file-keeper/releases/tag/v0.0.2) - 2025-03-17

<small>[Compare with v0.0.1](https://github.com/DataShades/file-keeper/compare/v0.0.1...v0.0.2)</small>

### Features

- stream-based composite implementation of range ([7d47bd8](https://github.com/DataShades/file-keeper/commit/7d47bd836c106ce4f4cfa592f54edaca1020b301) by Sergey Motornyuk).
- add Location wrapper around unsafe path parameters ([b99f155](https://github.com/DataShades/file-keeper/commit/b99f155f4db79fc6a177d65d5c43b57d65cfe756) by Sergey Motornyuk).
- file_keeper:opendal adapter ([214fb6c](https://github.com/DataShades/file-keeper/commit/214fb6c1b587648371b622b2537ef6ff63fd5181) by Sergey Motornyuk).
- file_keeper:redis adapter ([8c7da94](https://github.com/DataShades/file-keeper/commit/8c7da94042c2be5947781683cd9c02a7fca6f03f) by Sergey Motornyuk).

### Bug Fixes

- map error during settings initialization into custom exception ([f596037](https://github.com/DataShades/file-keeper/commit/f59603787c634d060a854b4bbf0b86451ffeaea5) by Sergey Motornyuk).
- fs adapter: infer `uploaded` size if it is not specified in `multipart_update` ([620ec3a](https://github.com/DataShades/file-keeper/commit/620ec3a16a18fe2101b98d634cc9815ec93bf20c) by Sergey Motornyuk).

### Code Refactoring

- `location_strategy: str` become `location_transformers: list[str]` ([daf2dc6](https://github.com/DataShades/file-keeper/commit/daf2dc6155b273815d198a7abf4cde6983f7855d) by Sergey Motornyuk).
- remove default range implementation from reader ([36f5f31](https://github.com/DataShades/file-keeper/commit/36f5f31da0d6791d82d20d8ea276140c59b578d0) by Sergey Motornyuk).

## [v0.0.1](https://github.com/DataShades/file-keeper/releases/tag/v0.0.1) - 2025-03-13

<small>[Compare with first commit](https://github.com/DataShades/file-keeper/compare/413e1fcaac8423a278f94a3c78e299ee2d89d7e6...v0.0.1)</small>

