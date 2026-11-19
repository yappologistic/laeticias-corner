# Changing things, by kind

Each kind of change has its own path through the repository and its own checklist. Copy the
checklist into your pull request's "What changes" if it helps; the proof it asks for goes into
the template's "Proof of work" ([proof of work](proof-of-work.md)).

Before any of these: an accepted issue (unless it is a small fix), and a read of the design
document the feature belongs to under `docs/design/` (`living-corner.md` for the home and its
rules, `living-world.md` for life, `world-tech.md` for the world, `seasons.md`, `look.md`,
`quality-bar.md`).

## Engine code (`src/`, `tests/`, build files)

The engine is C++23 on SDL3. Read [`CLAUDE.md`](../../CLAUDE.md) "Code standards" and
"Performance" first, and check SDL3's headers (`/usr/include/SDL3`) or its wiki before using an
API: SDL3 differs from SDL2 in many places.

- [ ] Logic lives in `src/core`, `src/world` or `src/life` (no SDL there) and has unit tests.
- [ ] Rendering, interface and input changes have a scripted run (`tests/scripts/*.lcs`)
      registered in `tests/CMakeLists.txt`, with `expect` lines that fail without the change.
- [ ] User-visible strings are in `src/ui/strings.hpp`, simulation numbers in
      `src/core/tuning.hpp`, interface spacing in `src/ui/theme.hpp`.
- [ ] No per-frame heap allocation in the steady state; every SDL call that can fail is checked.
- [ ] Warning-free; `clang-format -i` on the files you touched (only those).
- [ ] `ctest --preset release` and `ctest --preset asan` pass.
- [ ] Anything that could cost frame time: `--bench` before and after (see [testing](testing.md)).

## Home content in the catalog (`assets/catalog.json`)

Items, terrain, visitors, wishes, nooks, events and the resident are data. The fields are
documented in `docs/design/living-corner.md` §11 and `docs/design/living-world.md`; the engine
validates the catalog at start and names the entry it refuses.

- [ ] Ids are unique; home ids have no dot.
- [ ] Every sprite and sound the entry names exists, made by the generators in the same pull
      request (`ctest -R coverage` proves it).
- [ ] New progress content is reachable: granted by exactly one reachable wish
      (`living-corner.md` §12).
- [ ] A scripted run shows the new piece or visitor doing what it should.
- [ ] Before and after screenshots.

## Art (`tools/artgen`)

All sprites are computed by Python from code: models, materials, lighting and palettes. Read
`tools/artgen/README.md` and the art direction in `docs/design/look.md` and
`docs/design/quality-bar.md`.

- [ ] The change is in the generator, never in a PNG or manifest by hand.
- [ ] Regenerated with `tools/artgen/build.sh` (the home page) or
      `tools/artgen/build.sh --set <set>` (a set's pages and geometry); validation passed.
- [ ] `git status` lists only the outputs meant to change; a second run changes nothing.
- [ ] `ctest --preset release` passes (coverage included).
- [ ] Before and after screenshots of the same view in the game, attached.
- [ ] Historical subjects cite their published sources in the generator's docstring.

## Audio (`tools/audiogen`)

All music, ambience and effects are synthesised by Python (`tools/audiogen/README.md`). The
contract for loops, loudness and peaks is in `CLAUDE.md` ("Audio").

- [ ] The change is in the generator, never in an audio file by hand.
- [ ] Regenerated with `tools/audiogen/generate.sh` (optionally only the names you changed);
      its validation passed (it needs `ffmpeg` installed).
- [ ] Untouched files are byte for byte the same; a second run changes nothing.
- [ ] `ctest --preset release` passes, including the audio capture tests.
- [ ] Say in the pull request where and when the sound plays and how to hear it in a run.

## World data (`tools/worldgen`)

The world (layers, graphs, the overview) and each region's life and text are authored in
Python under `tools/worldgen/` and compiled into `assets/world/` and `assets/regions/`
(`tools/worldgen/README.md`, `docs/design/world-tech.md`).

- [ ] The change is in the plan or the region's sources, never in `.lcw`, graph or region JSON
      by hand.
- [ ] Compiled with `tools/worldgen/build.sh <layer>`; `tools/worldgen/build.sh --check` passes;
      `tools/worldgen/build.sh --test` passes.
- [ ] `build/release/lifeinfo problems` names nothing new.
- [ ] Bridges, stairs, gates and roads meet what they join, in the data and on screen.
- [ ] Before and after screenshots of the place (`set world PLACE ZOOM` in a script).

## Interface text and layout (`src/ui/`)

- [ ] Every string is in `src/ui/strings.hpp`; British spelling, the quiet tone of the rest.
- [ ] The `coverage` test passes (every string can be drawn by the bundled fonts).
- [ ] Spacing comes from `src/ui/theme.hpp`; the layout holds at 960×600 and at 2560×1440.
- [ ] Hover, pressed and disabled states for anything clickable.
- [ ] Before and after screenshots at the smallest window size, attached.

## Documentation

- [ ] Plain words, short sentences, British spelling.
- [ ] Every command shown is one you ran.
- [ ] No naming of other games, studios, artists or products as a model for this one, and nothing
      personal.
