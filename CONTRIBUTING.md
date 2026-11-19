# Contributing to Laeticia's Corner

Thank you for wanting to help. This project is run by one person, so it has a few firm rules
that keep it manageable. The forms and an automatic check enforce them, so nothing depends on
anyone's memory.

## The flow

1. **Issue first.** For anything beyond a small fix (a typo, a broken link, an obvious one-line
   bug), open an issue with the right form (bug report, proposal, or content) and wait until the
   maintainer marks it `accepted`. Work on something that was not accepted may be closed.
2. **One logical change per pull request**, small enough to review in one sitting. Link the
   issue ("Closes #123"). No drive-by refactoring or reformatting of code you did not need to
   touch.
3. **Fill in the pull request template completely**: proof of work, AI disclosure, contribution
   terms. The `PR description` check fails until every required part is there.
4. The maintainer reviews, may ask for changes, and squash-merges.

The scope limits in [`CLAUDE.md`](CLAUDE.md) ("Non-negotiables") apply to everyone: small, fast,
correct; no speculative abstractions, dead code or TODOs; everything tested; warning-free under
both the release and the sanitizer presets.

## The guide

| Page | What it covers |
|---|---|
| [Getting started](docs/contributing/getting-started.md) | build, test and run headless from a clean clone |
| [Repository map](docs/contributing/repository-map.md) | what lives where, what is generated, what you may change |
| [Changing things](docs/contributing/changing-things.md) | how to change engine code, catalog content, art, audio, world data and interface text, each with a checklist |
| [Testing](docs/contributing/testing.md) | unit tests, scripted runs, the sanitizer preset, the performance gates |
| [Proof of work](docs/contributing/proof-of-work.md) | exactly what every issue and pull request must show |
| [AI assistance](docs/contributing/ai-policy.md) | allowed, always disclosed; no outside generated art or audio |
| [Maintainer's guide](docs/contributing/maintainers.md) | labels, triage, review, merging, releases |

In short: build with `cmake --preset release && cmake --build --preset release`, test with
`ctest --preset release`, follow the code standards in [`CLAUDE.md`](CLAUDE.md) ("Code
standards"), format with `clang-format`, and write commit messages in the Conventional Commits
style (`feat(render): …`, `fix(core): …`, `test: …`, `assets: …`, `docs: …`).

## AI assistance

Allowed, and it must be disclosed on every issue and pull request, also when the answer is
"none": the tool or harness, the exact model and version, which parts it produced, and your
statement that you have read every line, built it and run it yourself and answer for it.
Undisclosed or misdescribed assistance closes the contribution. Art and audio made by outside
generative models are not accepted. Details: [AI assistance](docs/contributing/ai-policy.md).

## Contribution terms

By opening a pull request you agree to these terms:

1. **Your contribution is licensed under the project's licences**: code under the Mozilla
   Public License 2.0, and art, audio, world data, text and documentation under Creative Commons
   Attribution-NonCommercial-ShareAlike 4.0 ([`LICENSING.md`](LICENSING.md) says which path is
   which).
2. **You also grant the project owner (yappologistic) a perpetual, worldwide, non-exclusive,
   royalty-free, irrevocable right** to use, copy, modify, sublicense and distribute your
   contribution under other terms as well, including commercially.
3. **You have the right to make the contribution**: it is your own work, or you may contribute
   it under these terms, and it contains nothing taken from works you may not share this way.

**Why the second point:** the owner may later publish a paid build of the game. The art and
audio licence forbids commercial use, so without this grant your contribution could not be part
of that build. You keep the copyright in your work and may use it however you like; the grant is
non-exclusive.

The pull request template has a box to tick for these terms; a pull request without it is not
merged.
