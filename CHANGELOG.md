# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [v0.0.10](https://github.com/DataShades/file-keeper/releases/tag/v0.0.10) - 2025-07-13

<small>[Compare with v0.0.9](https://github.com/DataShades/file-keeper/compare/v0.0.9...v0.0.10)</small>

### Features

- add public_prefix(and permanent_link) to libcloud ([3bc7591](https://github.com/DataShades/file-keeper/commit/3bc759105f2d332b329af8b45e04fe2360d5928e) by Sergey Motornyuk).
- static_uuid transformer ([88383e0](https://github.com/DataShades/file-keeper/commit/88383e05c993b156d6a6253e43ef8902e13b3d9f) by Sergey Motornyuk).
- location transformers receive optional upload-or-data second argument ([8e6a6dc](https://github.com/DataShades/file-keeper/commit/8e6a6dc41d50fbcd6e2be8d984673f667333f1c2) by Sergey Motornyuk).

### Bug Fixes

- fix_extension transformer raises an error when upload is missing ([a827df5](https://github.com/DataShades/file-keeper/commit/a827df57168dab6e6d05e82bf9e6d680e25faed3) by Sergey Motornyuk).

## [v0.0.9](https://github.com/DataShades/file-keeper/releases/tag/v0.0.9) - 2025-07-02

<small>[Compare with v0.0.8](https://github.com/DataShades/file-keeper/compare/v0.0.8...v0.0.9)</small>

### Features

- add fix_extension transformer ([1345915](https://github.com/DataShades/file-keeper/commit/13459159fa22a50688d4d224942b383f54c5345e) by Sergey Motornyuk).
- opendal got path option ([d044ade](https://github.com/DataShades/file-keeper/commit/d044ade99fa8139f2ff661bfbd03bf599363ad19) by Sergey Motornyuk).

### Bug Fixes

- cast fs:multipart:position to int ([dc4d768](https://github.com/DataShades/file-keeper/commit/dc4d7686d00f1bae401e5c018e98c49a2ea5f40a) by Sergey Motornyuk).

## [v0.0.8](https://github.com/DataShades/file-keeper/releases/tag/v0.0.8) - 2025-04-23

<small>[Compare with v0.0.7](https://github.com/DataShades/file-keeper/compare/v0.0.7...v0.0.8)</small>

### Features

- libcloud storage got path option ([555036c](https://github.com/DataShades/file-keeper/commit/555036c428a30defe95392407a182f0729919970) by Sergey Motornyuk).

### Bug Fixes

- fs storage reports relative location of the missing file ([cef9589](https://github.com/DataShades/file-keeper/commit/cef9589b667679cd222c56a07931e5f1622ac79c) by Sergey Motornyuk).

## [v0.0.7](https://github.com/DataShades/file-keeper/releases/tag/v0.0.7) - 2025-03-28

<small>[Compare with v0.0.6](https://github.com/DataShades/file-keeper/compare/v0.0.6...v0.0.7)</small>

### Features

- storage upload and append requires Upload ([ebf5fef](https://github.com/DataShades/file-keeper/commit/ebf5fef0294cecc6da880994255696229d96a2ac) by Sergey Motornyuk).

### Bug Fixes

- fs storage checks permission when creating folders ([1791d68](https://github.com/DataShades/file-keeper/commit/1791d68a3d1dd4eaaec4d7a5edc4b7af2fc3ac46) by Sergey Motornyuk).

## [v0.0.6](https://github.com/DataShades/file-keeper/releases/tag/v0.0.6) - 2025-03-23

<small>[Compare with v0.0.4](https://github.com/DataShades/file-keeper/compare/v0.0.4...v0.0.6)</small>

### Features

- add *_synthetic methods ([27c4164](https://github.com/DataShades/file-keeper/commit/27c4164ea128feb9ca5a7e6e8ef83c80f99f70a6) by Sergey Motornyuk).

### Bug Fixes

- multipart update of s3 and gcs work with arbitrary upload ([902c9cb](https://github.com/DataShades/file-keeper/commit/902c9cbd48fcd25ade62f12bd926bfc7ece32998) by Sergey Motornyuk).

## [v0.0.4](https://github.com/DataShades/file-keeper/releases/tag/v0.0.4) - 2025-03-22

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

