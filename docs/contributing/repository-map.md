# Repository map

What lives where, what is generated, and what a contribution may change. The full table with
the engine's internal ownership is in [`CLAUDE.md`](../../CLAUDE.md) ("Layout and ownership").

| Path | What it is | Hand-written or generated |
|---|---|---|
| `src/core/` | pure game logic without SDL: grid, catalog, placement, undo, save, visitors, clock, weather | hand-written |
| `src/world/` | the world's data runtime (loaders, the composed world, graphs) and the `worldinfo` tool | hand-written |
| `src/life/` | city life over the world (populations, chains, events, figures) and the `lifeinfo` tool | hand-written |
| `src/render/`, `src/ui/`, `src/audio/`, `src/worldview/`, `src/app/`, `src/platform/` | everything that touches SDL: drawing, interface, sound, the world renderer (also the `laeticias-world` viewer), the app and its script runner, platform helpers | hand-written |
| `tests/` | unit tests (doctest), scripted runs (`tests/scripts/*.lcs`), test tools | hand-written |
| `CMakeLists.txt`, `CMakePresets.json`, `cmake/`, `.clang-format`, `.clang-tidy` | build and tooling configuration | hand-written |
| `third_party/` | vendored stb and doctest | upstream, unmodified |
| `assets/catalog.json`, `assets/sets/<set>/catalog.json` | the content contract: what exists, its rules and data | hand-written (the contract) |
| `assets/atlas.*`, `assets/atlas/` | sprite pages, manifests and geometry | **generated** by `tools/artgen` |
| `assets/audio/` | music, ambience and effects | **generated** by `tools/audiogen` |
| `assets/world/`, `assets/regions/` | the world's layers, graphs, overview and the regions' life and text | **generated** by `tools/worldgen` |
| `assets/shaders/` | GLSL sources and their SPIR-V | sources hand-written; `.spv` compiled from them (`--target shaders`) |
| `assets/fonts/` | bundled fonts with their licences | upstream |
| `tools/artgen/`, `tools/audiogen/`, `tools/worldgen/` | the Python generators, each with a README, pinned `requirements.txt` and tests | hand-written |
| `docs/design/` | the design documents every feature follows | hand-written |
| `docs/contributing/` | this guide | hand-written |

`src/core`, `src/world` and `src/life` never include SDL headers; dependencies point one way:
`app → worldview → ui/render/audio → life → world → core`.

## Generated files are never edited by hand

Atlases, audio and world data are outputs. To change one, change its generator (or the catalog
or region data it reads), regenerate, and commit the generator change together with its
outputs in the same pull request. A pull request that edits a generated file by hand is closed.

How a regeneration is shown to be faithful:

- **It reproduces what it did not mean to change.** The generators are deterministic (fixed
  seeds, pinned packages). Regenerate, then `git status` must list only the outputs your change
  was meant to touch; everything else stays byte for byte the same.
- **A second run is identical.** Run the generator twice; the second run changes nothing.
- **The tool's own validation passes**: `tools/artgen/build.sh` validates the atlas as it writes
  it, `tools/audiogen/generate.sh` validates every file (format, loudness, loops), and
  `tools/worldgen/build.sh --check` validates the composed world.
- **The engine accepts it**: `ctest --preset release` passes, including `coverage` (every sprite
  and sound the catalogs name exists) and the scripted runs.

## Who may change what

- Anyone may propose a change anywhere through an accepted issue.
- `CLAUDE.md`, `assets/catalog.json` and the set catalogs are contracts between the engine and
  the generators: a change to them needs an accepted proposal that says which side changes.
- Licence files, `LICENSING.md`, `THIRD-PARTY.md` and `.github/` are changed by the maintainer.
- A new third-party dependency needs a written justification in its proposal
  ([`CLAUDE.md`](../../CLAUDE.md) "Stack"); its licence must allow distribution under the
  project's licences.
