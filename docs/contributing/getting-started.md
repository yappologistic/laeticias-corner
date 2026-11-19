# Getting started

From a clean clone to a tested build and a headless run. The build, test and headless commands
below are the ones the project's publication check ran on a fresh clone (Linux, GCC 16.2,
CMake 4.5, Ninja 1.13, SDL 3.4.20, nlohmann_json 3.12). The `Build` workflow builds and tests
every change on Linux (GCC 14 on AlmaLinux 9) and Windows (see
[Building on Windows](#building-on-windows)). There is no macOS build yet.

## What you need

- A C++23 compiler: GCC (the `release` and `asan` presets) or Clang (`clang-release`,
  `clang-asan`).
- CMake 3.28 or newer and Ninja.
- SDL 3.4 or newer and nlohmann_json 3.11 or newer. When they are installed as system packages
  (with their development files) the build uses them; otherwise the first configure downloads
  the pinned releases named in `CMakeLists.txt`, checks their SHA-256 and builds them with the
  game (SDL as a shared library beside the programs).
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

## Building on Windows

What the `Build` workflow does on GitHub's Windows runner, and so the one way known to work:

- GCC for MinGW-w64 on the UCRT runtime: the workflow uses WinLibs GCC 16.2 (MinGW-w64 14,
  POSIX threads, SEH), unpacked anywhere with its `mingw64\bin` first on `PATH`. Other MinGW-w64
  GCC builds (MSYS2's UCRT64, for one) should work but are untested; MSVC and clang-cl are not
  supported (the build files use GCC's flags).
- CMake 3.28 or newer from Kitware's installer and Ninja. Do not use the `cmake.exe` that comes
  with WinLibs: it cannot check certificates, so the download of SDL fails.
- Git for Windows; the commands below are the same in Git Bash or PowerShell.

```sh
cmake --preset release
cmake --build --preset release -j4
ctest --preset release
build/release/laeticias-corner.exe
```

SDL and nlohmann_json are downloaded on the first configure (there are no system packages);
`SDL3.dll` is copied next to each program that needs it. The game is a windowed program with no
console: `--version` and the log reach a terminal only when its output is redirected
(`laeticias-corner.exe --version | more`). Headless runs set the same variables in PowerShell:
`$env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"`.

A release package (what `release.yml` makes) is laid out by
`cmake --install build/release --prefix <folder> --strip` from a build configured with
`-DLC_STATIC_RUNTIME=ON`, which links the C++ runtime into the programs.

## Before your first pull request

Read [`CONTRIBUTING.md`](../../CONTRIBUTING.md) (the flow and the terms), the
[repository map](repository-map.md), the page for your [kind of change](changing-things.md) and
[proof of work](proof-of-work.md).
