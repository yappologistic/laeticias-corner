# Testing

Everything is tested: logic by unit tests, rendering, interface and input by scripted headless
runs that check state and take screenshots. A change is done when the build is warning-free and
`ctest` passes under both the release and the sanitizer presets ([`CLAUDE.md`](../../CLAUDE.md)
"Non-negotiables").

All runs are headless. Never open a window or play sound from a test: the tests set
`SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` themselves, and when you run the game by hand
for a test, set them too and give it a scratch `--save-dir` (never your real save folder).

## The suites

```sh
ctest --preset release                 # everything except the "heavy" label (a few minutes)
ctest --preset release -R unit         # only the unit tests (doctest, fast)
ctest --preset release -R coverage     # every sprite, sound and glyph the data names exists
ctest --preset release -R script_      # the scripted runs
ctest --preset release-full            # also the heavy runs (large windows, the big bench)
ctest --preset asan                    # Debug + AddressSanitizer + UndefinedBehaviorSanitizer
```

The sanitizer preset is built separately: `cmake --preset asan && cmake --build --preset asan`.
Engine changes must pass it.

## Unit tests

Unit tests use doctest and live in `tests/*.cpp`, built into one `lc_tests` binary. Pure logic
(`src/core`, `src/world`, `src/life`) is tested directly, without SDL. Add a `TEST_CASE` beside
the tests of the same area and give it a name that says what must hold. To run one test case:

```sh
build/release/tests/lc_tests --test-case="*name*"
```

## Scripted runs (`.lcs`)

A scripted run drives the real game through synthesised input, the same path real input takes,
checks the state with `expect` lines, and can save screenshots. The language is documented at
the top of `src/app/script.hpp`; `tests/scripts/` holds many examples. A small one:

```text
# The clock pins to night and the corner is dark.
set clock night
expect phase night
wait 30
expect luma 290,175,60,20 25 55
shot shots/clock_night.png
```

- `set …` puts the game in a state (clock, weather, season, camera, unlocks, a place in the
  world); `place` and `paint` build directly; `click`, `drag`, `key` and `wheel` are input.
- `expect …` fails the run when the state does not match: tiles and items, open panels, actors
  and where they are, events, image statistics of a screen region (`luma`, `color`, `contrast`,
  `lit`), city life.
- `waitfor N WHAT …` waits up to N frames for an `expect` to hold; `fast S` simulates S seconds
  without drawing.

Run a script by hand:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy build/release/laeticias-corner \
    --script tests/scripts/clock_phases.lcs --size 640x400 --save-dir out/test-save
```

It exits non-zero when an `expect` fails and names the line. To make it part of the suite, add
an entry `name|script|size|labels` to `LC_SCRIPTS` in `tests/CMakeLists.txt`; the test is then
`script_<name>` and its screenshots go to `build/<preset>/shots/`. A bug fix's script must fail
without the fix: check that before you commit it.

`determinism_check` runs one script twice and compares its screenshots and the world save byte
for byte (apart from the save's creation time): the simulation
is reproducible from one seed, and new code must keep it so (derive random streams from the
game's seed, never from time).

## Performance gates

The budgets in [`CLAUDE.md`](../../CLAUDE.md) ("Performance") are part of "done". The gates:

```sh
build/release/laeticias-corner --bench --renderer opengl --size 1920x1080 --save-dir out/bench
build/release/laeticias-corner --soak 600 --save-dir out/soak
build/release/lifeinfo bench
```

`--bench` times the home region, the dense city views, the overview, crowds and fast travel, and
exits 3 when a budget fails; `--soak` runs busy play fast and fails when memory grows. The
`bench` tests in `ctest` run them on the windowless GPU path and are skipped (exit 77) where no
GPU renderer can be created.

Timings need a **quiet machine**: close other heavy programs, run the same command before and
after your change on the same machine, and paste both outputs. Numbers from a busy machine or
from two different machines prove nothing. `F3` in the game shows the profiler and
`--perf-log FILE` writes per-frame timings as CSV for finding where time goes.

## Generator tests

Each generator has its own tests and validation:

```sh
tools/worldgen/build.sh --test       # worldgen's unit tests
tools/worldgen/build.sh --check      # validate the composed world
```

`tools/artgen/build.sh` and `tools/audiogen/generate.sh` validate what they write; their READMEs
list the checks.
