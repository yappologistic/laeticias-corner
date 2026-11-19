<!--
Thank you for contributing. Every section below is required and is checked automatically
(.github/scripts/check_pr.py). Write your answers under the headings; text inside these comment
markers does not count. The guide: docs/contributing/proof-of-work.md
-->

## Issue

<!-- "Closes #123" for the accepted issue this implements. Only a small fix (a typo, a broken
link, a one-line obvious bug) may go without one: then write "Small fix:" and one sentence. -->


## What changes

<!-- One logical change, in a few sentences: what it does and why. No unrelated refactoring or
reformatting. -->


## Kind of change

<!-- Tick every box that applies (put an x between the brackets: [x]). -->

- [ ] Bug fix
- [ ] Engine code (`src/`, `tests/`, build files)
- [ ] Home content in the catalog (items, visitors, wishes, nooks)
- [ ] Art generator (`tools/artgen`) and regenerated atlases
- [ ] Audio generator (`tools/audiogen`) and regenerated audio
- [ ] World data (`tools/worldgen`, `assets/world`, `assets/regions`)
- [ ] Interface text or layout
- [ ] Changes what is seen on screen
- [ ] Performance
- [ ] Documentation only

## Proof of work

### Build and test

<!-- The exact commands you ran and their result lines, copied from your terminal, e.g. the
cmake build and "100% tests passed, 0 tests failed out of N" from `ctest --preset release`.
Engine changes: the `asan` preset too. -->


### Platform

<!-- Operating system and version, compiler and version, SDL version (`pkg-config --modversion
sdl3`), and the renderer if it matters. -->


### Reproduction

<!-- Bug fixes: the test or .lcs script that fails before this change and passes after it, and
both results. Otherwise write "n/a". -->


### Before and after

<!-- Anything visible: before and after screenshots made headless (same view, same seed, same
size), attached here as images, and the script or command that made them. Otherwise "n/a".
Changes under assets/, docs/images/, tools/artgen/ or tools/worldgen/regions/ need images. -->


### Benchmark

<!-- Performance claims: `--bench` output before and after, on the same machine. Otherwise
"n/a". -->


### Regeneration

<!-- Generator changes: the command you ran, confirmation that the regenerated outputs are
committed, and the result of the tool's validation and of a second run being identical.
Otherwise "n/a". -->


## AI assistance

<!-- Required, also when no AI tool was used (then write "none" in all three fields). Give the
model exactly as the tool reports it. Policy: docs/contributing/ai-policy.md -->

- Tool or harness:
- Model and version:
- What it produced:

- [ ] I have read every line of this change, built it and run it myself, and I answer for it.

## Contribution terms

- [ ] I agree to the contribution terms in CONTRIBUTING.md: my contribution is licensed under
  the project's licences (code MPL-2.0, assets and text CC BY-NC-SA 4.0), and I grant the project
  owner the additional right to use and distribute it under other terms, including commercially.
