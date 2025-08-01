
## [unreleased]
[Compare with v0.0.10](https://github.com/DataShades/file-keeper/compare/v0.0.10..HEAD)

### 🚀 Features

- [**breaking**] frozen FileData and MultipartData ([cb9dbf8](https://github.com/DataShades/file-keeper/commit/cb9dbf8ddf7516d461d0a295f69d41090b706195))
- less strict typing rules for storage settings ([247d1c6](https://github.com/DataShades/file-keeper/commit/247d1c6291ab1bc52324f13bdbf642b8c9c53c1b))
- remove __str__ from exceptions ([2ecd8a2](https://github.com/DataShades/file-keeper/commit/2ecd8a2b8ca2cf90c8e7d1c9fc2e70f6dd39f216))
- add memory storage ([3abc218](https://github.com/DataShades/file-keeper/commit/3abc2181493c50061ce05c185af29ebe65863d02))
- storage.ext.register accepts optional `reset` parameter ([c5edce8](https://github.com/DataShades/file-keeper/commit/c5edce8c397bc326c6448f0cb382900995757c4f))
- Settings log extra options with debug level instead of raising an exception ([7308578](https://github.com/DataShades/file-keeper/commit/7308578d8f4281e427b439ba8cb9540c3ce61d30))
- add null storage ([c1f8476](https://github.com/DataShades/file-keeper/commit/c1f8476e701bfc9b7a3ced532d8c4edffefdeae0))

### 🐛 Bug Fixes

- storage settings keep a lot of intermediate parameters ([cf69cf2](https://github.com/DataShades/file-keeper/commit/cf69cf26f4d7ad9e2b16204c6a9803ec6c0a2edb))
- libcloud silently overrides existing objects ([599f099](https://github.com/DataShades/file-keeper/commit/599f09992ed14e926878b9997abd2bca2155326a))

## [v0.0.10](https://github.com/DataShades/file-keeper/releases/tag/v0.0.10) - 2025-07-13
[Compare with v0.0.9](https://github.com/DataShades/file-keeper/compare/v0.0.9..v0.0.10)

### 🚀 Features

- add public_prefix(and permanent_link) to libcloud ([3bc7591](https://github.com/DataShades/file-keeper/commit/3bc759105f2d332b329af8b45e04fe2360d5928e))
- static_uuid transformer ([88383e0](https://github.com/DataShades/file-keeper/commit/88383e05c993b156d6a6253e43ef8902e13b3d9f))
- location transformers receive optional upload-or-data second argument ([8e6a6dc](https://github.com/DataShades/file-keeper/commit/8e6a6dc41d50fbcd6e2be8d984673f667333f1c2))

### 🐛 Bug Fixes

- fix_extension transformer raises an error when upload is missing ([a827df5](https://github.com/DataShades/file-keeper/commit/a827df57168dab6e6d05e82bf9e6d680e25faed3))

### ❌ Removal

- delete Storage.public_link ([da08744](https://github.com/DataShades/file-keeper/commit/da08744021d56ea090cc522b82be70a4d5334771))

## [v0.0.9](https://github.com/DataShades/file-keeper/releases/tag/v0.0.9) - 2025-07-02
[Compare with v0.0.8](https://github.com/DataShades/file-keeper/compare/v0.0.8..v0.0.9)

### 🚀 Features

- add fix_extension transformer ([1345915](https://github.com/DataShades/file-keeper/commit/13459159fa22a50688d4d224942b383f54c5345e))
- opendal got path option ([d044ade](https://github.com/DataShades/file-keeper/commit/d044ade99fa8139f2ff661bfbd03bf599363ad19))

### 🐛 Bug Fixes

- cast fs:multipart:position to int ([dc4d768](https://github.com/DataShades/file-keeper/commit/dc4d7686d00f1bae401e5c018e98c49a2ea5f40a))

## [v0.0.8](https://github.com/DataShades/file-keeper/releases/tag/v0.0.8) - 2025-04-23
[Compare with v0.0.7](https://github.com/DataShades/file-keeper/compare/v0.0.7..v0.0.8)

### 🚀 Features

- libcloud storage got path option ([555036c](https://github.com/DataShades/file-keeper/commit/555036c428a30defe95392407a182f0729919970))

### 🐛 Bug Fixes

- fs storage reports relative location of the missing file ([cef9589](https://github.com/DataShades/file-keeper/commit/cef9589b667679cd222c56a07931e5f1622ac79c))

## [v0.0.7](https://github.com/DataShades/file-keeper/releases/tag/v0.0.7) - 2025-03-28
[Compare with v0.0.6](https://github.com/DataShades/file-keeper/compare/v0.0.6..v0.0.7)

### 🚀 Features

- storage upload and append requires Upload ([ebf5fef](https://github.com/DataShades/file-keeper/commit/ebf5fef0294cecc6da880994255696229d96a2ac))

### 🐛 Bug Fixes

- fs storage checks permission when creating folders ([1791d68](https://github.com/DataShades/file-keeper/commit/1791d68a3d1dd4eaaec4d7a5edc4b7af2fc3ac46))

## [v0.0.6](https://github.com/DataShades/file-keeper/releases/tag/v0.0.6) - 2025-03-23
[Compare with v0.0.4](https://github.com/DataShades/file-keeper/compare/v0.0.4..v0.0.6)

### 🚀 Features

- add *_synthetic methods ([27c4164](https://github.com/DataShades/file-keeper/commit/27c4164ea128feb9ca5a7e6e8ef83c80f99f70a6))

### 🐛 Bug Fixes

- multipart update of s3 and gcs work with arbitrary upload ([902c9cb](https://github.com/DataShades/file-keeper/commit/902c9cbd48fcd25ade62f12bd926bfc7ece32998))

## [v0.0.4](https://github.com/DataShades/file-keeper/releases/tag/v0.0.4) - 2025-03-22
[Compare with v0.0.3](https://github.com/DataShades/file-keeper/compare/v0.0.3..v0.0.4)

### 🚀 Features

- storages accept any type of upload ([a64ee3d](https://github.com/DataShades/file-keeper/commit/a64ee3da989930201964f22b4f32c62641da9294))

### 🚜 Refactor

- remove validation from storage ([93392f9](https://github.com/DataShades/file-keeper/commit/93392f9d8473a913623b8dd35cd202d35b4368ec))
- remove type and size validation from append and compose ([890c89a](https://github.com/DataShades/file-keeper/commit/890c89a8109c64f2a783c6b8dcd0c59d4c94cd89))
- remove public link method and capability ([cb39151](https://github.com/DataShades/file-keeper/commit/cb39151fb7e09cfdf3b9cdf0d3e2d98ba519edbe))

### ❌ Removal

- drop link storage ([3328eb2](https://github.com/DataShades/file-keeper/commit/3328eb20a581efc58eef6eb232ada1f9c13753af))

## [v0.0.2](https://github.com/DataShades/file-keeper/releases/tag/v0.0.2) - 2025-03-17
[Compare with v0.0.1](https://github.com/DataShades/file-keeper/compare/v0.0.1..v0.0.2)

### 🚀 Features

- stream-based composite implementation of range ([7d47bd8](https://github.com/DataShades/file-keeper/commit/7d47bd836c106ce4f4cfa592f54edaca1020b301))
- add Location wrapper around unsafe path parameters ([b99f155](https://github.com/DataShades/file-keeper/commit/b99f155f4db79fc6a177d65d5c43b57d65cfe756))
- file_keeper:opendal adapter ([214fb6c](https://github.com/DataShades/file-keeper/commit/214fb6c1b587648371b622b2537ef6ff63fd5181))
- file_keeper:redis adapter ([8c7da94](https://github.com/DataShades/file-keeper/commit/8c7da94042c2be5947781683cd9c02a7fca6f03f))

### 🐛 Bug Fixes

- map error during settings initialization into custom exception ([f596037](https://github.com/DataShades/file-keeper/commit/f59603787c634d060a854b4bbf0b86451ffeaea5))
- fs adapter: infer `uploaded` size if it is not specified in `multipart_update` ([620ec3a](https://github.com/DataShades/file-keeper/commit/620ec3a16a18fe2101b98d634cc9815ec93bf20c))

### 🚜 Refactor

- `location_strategy: str` become `location_transformers: list[str]` ([daf2dc6](https://github.com/DataShades/file-keeper/commit/daf2dc6155b273815d198a7abf4cde6983f7855d))
- remove default range implementation from reader ([36f5f31](https://github.com/DataShades/file-keeper/commit/36f5f31da0d6791d82d20d8ea276140c59b578d0))

### 🧪 Testing

- add standard adapter tests ([d961682](https://github.com/DataShades/file-keeper/commit/d9616827673a74f18c83515e127cfa014b038511))

## [v0.0.1](https://github.com/DataShades/file-keeper/releases/tag/v0.0.1) - 2025-03-13
