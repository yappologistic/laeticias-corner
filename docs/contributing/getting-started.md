# Getting started

From a clean clone to a tested build and a headless run. The build, test and headless commands
below are the ones the project's publication check ran on a fresh clone (Linux, GCC 16.2,
CMake 4.5, Ninja 1.13, SDL 3.4.20, nlohmann_json 3.12).

## What you need

- A C++23 compiler: GCC (the `release` and `asan` presets) or Clang (`clang-release`,
  `clang-asan`).
- CMake 3.28 or newer and Ninja.
- SDL 3.4 or newer and nlohmann_json 3.11 or newer, as system packages (with their development
  files).
- Python 3 with `venv`, only to regenerate assets (each generator makes its own virtual
  environment); `ffmpeg` to validate regenerated audio.

## Build

```sh
git clone <repository-url> laeticias-corner
cd laeticias-corner
cmake --preset release
cmake --build --preset release -j3
```

`-j3` sets the number of parallel jobs; choose what your machine can spare. The game is
`build/release/laeticias-corner`; the build also makes the tools `worldinfo` and `lifeinfo` and
the test binary `build/release/tests/lc_tests`.

## Test

```sh
ctest --preset release -R unit       # the unit tests: under a minute
ctest --preset release               # the whole default suite: minutes on an idle machine
```

Both must end with `100% tests passed`. The sanitizer build is separate:
`cmake --preset asan && cmake --build --preset asan -j3 && ctest --preset asan`.
[Testing](testing.md) explains the suites.

## Run headless

Automated runs never open a window or play sound:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy build/release/laeticias-corner \
    --headless --size 1280x800 --save-dir out/try --frames 300
```

It loads the world, plays 300 frames and exits with status 0. `--save-dir` keeps its save away
from your real one; `out/` is ignored by git. Add `--script FILE.lcs` to drive it with a script
([testing](testing.md)).

## Play

```sh
build/release/laeticias-corner
```

opens the game in a window. The controls are in the [README](../../README.md).

## Before your first pull request

Read [`CONTRIBUTING.md`](../../CONTRIBUTING.md) (the flow and the terms), the
[repository map](repository-map.md), the page for your [kind of change](changing-things.md) and
[proof of work](proof-of-work.md).
