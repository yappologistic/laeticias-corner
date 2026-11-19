# Licensing

Copyright © 2026 yappologistic.

Laeticia's Corner has three kinds of content, and each has its own licence.

## Code: Mozilla Public License 2.0

These paths are under the Mozilla Public License, v. 2.0 (full text in [`LICENSE`](LICENSE)):

- `src/`, `tests/`, `tools/`, `cmake/`, `.github/`
- the build files: `CMakeLists.txt`, `CMakePresets.json`, `.gitignore` and the other top-level
  configuration files
- the shaders: `assets/shaders/` (GLSL sources and their compiled SPIR-V)

The source files do not carry individual licence headers yet. This notice applies to every file
under the paths above, as Exhibit A of the licence allows:

> This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy
> of the MPL was not distributed with this file, You can obtain one at
> https://mozilla.org/MPL/2.0/.

In short: you may use, change and share the code, also inside larger works under other licences;
files you change that are covered by the MPL stay under the MPL, and their source must be
available.

## Art, audio, world data, text and design: CC BY-NC-SA 4.0

These paths are under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International licence (full legal code in [`LICENSE-ASSETS`](LICENSE-ASSETS)):

- `assets/`, except `assets/fonts/` and `assets/shaders/`: the sprite atlases and their manifests,
  the audio, the world and region data, the catalogs
- `docs/`: the design documents, the contributor guide and the images
- the text of `README.md`, `CONTRIBUTING.md` and the other top-level documents

In short: you may share and adapt them, not for commercial purposes, giving credit to
"yappologistic, Laeticia's Corner", and sharing what you make from them under the same licence.

Many of these files are produced by the generators under `tools/` (which are code, MPL-2.0).
Running a generator yourself does not change the licence of what it reproduces: the generated
art, audio and world data are works of this project and stay under CC BY-NC-SA 4.0.

## Third-party parts: their own licences

`third_party/` (stb, doctest) and `assets/fonts/` (Nunito, Noto Sans, Lucide) keep the licences
of their authors; the licence text of each sits beside it. [`THIRD-PARTY.md`](THIRD-PARTY.md)
lists them with their versions.

## The name and the logo

The name "Laeticia's Corner" and its logo (the `title/logo` sprite) are reserved. Neither licence
above grants any right to use them as a trademark: a fork or a derived work must use another
name and must not present itself as the original or as endorsed by it. Saying truthfully that a
work is based on Laeticia's Corner is fine.

## Contributions

Contributions come in under the same licences, with one additional grant to the project owner;
[`CONTRIBUTING.md`](CONTRIBUTING.md) explains it.
