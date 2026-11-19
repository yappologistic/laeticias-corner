# Proof of work

A contribution is reviewed by checking its proof, not by trusting its description. This page says
exactly what each kind of contribution must show. The pull request template has a place for each
item, and the `PR description` check (`.github/scripts/check_pr.py`) fails until the required
ones are there.

## Every pull request

- **Build and test**: the exact commands you ran and their result lines, copied from your
  terminal. At least the release build and `ctest --preset release`, ending in
  `100% tests passed out of N`. **Engine changes** (`src/`, `tests/`, build
  files): also the `asan` preset (`cmake --preset asan && cmake --build --preset asan &&
  ctest --preset asan`).
- **Platform**: operating system and version, compiler and version, SDL version
  (`pkg-config --modversion sdl3`), and the renderer when it matters.
- **AI assistance** and the **contribution terms** ([AI assistance](ai-policy.md),
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md)).

Documentation-only changes may write "n/a" for the build, the test and the platform.

## By kind

| Kind | What to show |
|---|---|
| Bug fix | A reproduction that **fails before** the change and **passes after**: a unit test or a `.lcs` script (with `expect` lines), and both results. It stays in the repository as a regression test. |
| Anything visible | **Before and after screenshots** made headless (below): same view, same seed, same size, attached to the pull request as images, plus the script that made them. |
| Performance | `--bench` output **before and after on the same machine**, quiet, both with the same command ([testing](testing.md)). Claims without numbers are not accepted. |
| Generator change | The regenerated outputs committed with the change; the tool's validation result; that a second run changes nothing; that `git status` after regenerating lists only the outputs meant to change ([repository map](repository-map.md)). |

The check requires images when "Changes what is seen on screen" is ticked or when any changed
path is an image or lies under `assets/` (other than `assets/audio/`), `docs/images/`,
`tools/artgen/` or `tools/worldgen/regions/`.

You can run the same check before you open the pull request, with your description saved in a
file:

```sh
git diff --name-only main... > /tmp/changed.txt
python3 .github/scripts/check_pr.py --body-file my-description.md --files-file /tmp/changed.txt
```

It prints what is missing and exits 1, or says the description is complete. Its own tests:
`python3 .github/scripts/test_check_pr.py`.

## Making screenshots headless

Screenshots come from the game itself, driven by a script, never from a desktop capture and
never edited. Write a small script (the language is documented at the top of
`src/app/script.hpp`; [testing](testing.md) explains it), for example
[`shots.lcs`](shots.lcs) beside this page:

```text
# Fixed hour and weather, so before and after differ only by the change.
set clock day
set weather clear
set world forum 1
wait 120
shot forum.png
quit
```

Run it on the build **before** your change and on the build **after**, with the same size and
seed, in a scratch save directory:

```sh
mkdir -p out/shots && cd out/shots
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ../../build/release/laeticias-corner \
    --script ../../docs/contributing/shots.lcs --size 1280x800 --seed 1 --save-dir save
```

`shot` writes into the working directory (`out/` is ignored by git). Rename the two files `before.png` and `after.png` and
drag both into the pull request description. Show the same view: same `set world` or
`set camera`, same `set clock` or `set time`, same `--size` and `--seed`. The headless run uses
the software renderer, so two runs of the same build give the same pixels.

To build the "before" binary without disturbing your work, use a second worktree under `out/`:
`git worktree add out/before main`, build it there with the same preset, and remove the worktree
when done (`git worktree remove out/before`).

## Bug reports

The bug form asks for: the version or commit, the platform, the renderer, steps (or better a
`.lcs` script and the command that runs it), what you expected, what happened, a screenshot for
anything visual, and the log (the terminal output). Before pasting a log, look through it for
anything private, such as your user name in paths.

## Proposals and content issues

Say how the work will be proven: which tests, scripts, screenshots or benchmarks. A proposal
that cannot say how it will be proven is not ready to be accepted.
