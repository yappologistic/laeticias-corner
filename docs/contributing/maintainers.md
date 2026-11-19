# Maintainer's guide

How the project is run by one person. The forms and the `PR description` check do the
enforcing; the maintainer decides and reviews.

## Labels

| Label | Meaning |
|---|---|
| `needs-triage` | new, not looked at yet (set by every issue form) |
| `bug` | something does not work as documented (set by the bug form) |
| `proposal` | a new feature or change (set by the proposal form) |
| `content` | art, audio or world data through the generators (set by the content form) |
| `accepted` | the maintainer agrees it should be done this way; work may start |
| `needs-info` | waiting for the reporter: a reproduction, a screenshot, the log, a clearer design |
| `declined` | will not be done (with a sentence why); the issue is closed |
| `duplicate` | already tracked elsewhere (link it); closed |
| `good first issue` | small, well understood, a good start for a new contributor |
| `help wanted` | accepted, and nobody is working on it |
| `area/engine`, `area/tests`, `area/art`, `area/audio`, `area/world`, `area/content`, `area/interface`, `area/docs`, `area/ci` | which part of the repository a pull request touches (the paths are in `.github/labeler.yml`) |

Create these labels once after creating the repository (Issues → Labels).

## Triage (new issues)

1. Is it complete? The forms require every field; if the content is not usable (no steps, no
   screenshot for something visual, a log that does not match), add `needs-info` and say what is
   missing. Close after 30 days without an answer.
2. Is the AI disclosure plausible? If it is evidently wrong, ask once; if it stays wrong, close
   ([AI assistance](ai-policy.md)).
3. Is it a duplicate, out of scope, or against the direction in [`CLAUDE.md`](../../CLAUDE.md)
   ("Where this is going", "Non-negotiables")? Label and close with one sentence.
4. Bugs: reproduce with the given script or steps on the current `main`. Confirmed: remove
   `needs-triage`; add `good first issue` or `help wanted` if you will not fix it yourself.
5. Proposals and content: decide. `accepted` means "a pull request that does this, proven as the
   proposal says, will be merged". Say what the first small pull request should be.

## Reviewing a pull request

The `PR description` check must be green. Then:

1. **Scope.** It links an accepted issue (or is a genuine small fix), does one logical thing,
   and touches nothing unrelated. Ask for a split otherwise.
2. **Proof.**
   - The build and test lines are plausible for the change (the test count matches `main`'s
     plus the new tests; engine changes include the `asan` run).
   - A bug fix's reproduction fails on `main` and passes on the branch: run it.
   - Screenshots: reproduce at least one. Check out the branch in a worktree under `out/`, build
     it, run the script given in the description with the same `--size` and `--seed`, and
     compare with the attached image. Headless runs use the software renderer, so the same
     build gives the same pixels. Do the same on `main` for the "before".
   - Benchmarks: both runs on the same machine; the budgets in `CLAUDE.md` still hold.
   - Generators: regenerate on the branch; `git status` must stay clean (the committed outputs
     are exactly what the generator makes).
3. **Code.** The standards in `CLAUDE.md` ("Code standards"): warning-free, formatted, tested,
   no per-frame allocation, strings and numbers in their one place, no dead code or TODOs.
4. **Licence and origin.** The contribution-terms box is ticked; nothing in the change comes from
   outside sources (art, audio, code under incompatible licences); no personal data in files,
   logs or screenshots.
5. Never run a contributor's code on your own machine with access to anything private; use a
   worktree, headless runs and a scratch `--save-dir`.

## Merging

- **Squash and merge** only, so `main` keeps a linear history with one commit per pull request.
- The squash commit's title is a Conventional Commits line (`fix(core): …`), edited if needed;
  the body keeps the issue link and any `Co-Authored-By` lines.
- Merge only when the check is green and the review is done. Close the issue with the merge.

## Making a release

Releases are built by GitHub Actions, never on a personal machine: the `Release` workflow
(`.github/workflows/release.yml`) runs the `Build` workflow on the tag (build, tests, packages,
the proof that each unpacked package runs on a clean machine) and then creates a **draft**
pre-release with the archives and `SHA256SUMS.txt`. Nothing is published until you publish the
draft.

1. On an up-to-date `main` whose `Build` run is green: `ctest --preset release-full` and
   `ctest --preset asan` pass on your machine, and `--bench` passes on the reference machine
   (the CI runners skip the timing gates).
2. Set the version in a pull request of its own: `project(laeticias_corner VERSION x.y.z)` and
   `LC_VERSION_SUFFIX` (for example `-prealpha.2`, empty for a final release) in
   `CMakeLists.txt`, and add the release notes as `docs/releases/<version>.md` (`<version>` is
   `x.y.z` plus the suffix). The notes say what the game is, what works, what is known not to
   work, how to start it on each system and how to report a bug.
3. Tag the merge commit with `v<version>` and push the tag:
   `git tag -a v0.1.0-prealpha.1 -m "Laeticia's Corner 0.1.0-prealpha.1"` then
   `git push origin v0.1.0-prealpha.1`. A tag that does not match the version in
   `CMakeLists.txt` finds no archives and stops the workflow.
4. When the `Release` run is green, open the draft on the Releases page: download each archive,
   check it against `SHA256SUMS.txt`, look at the proof screenshots of the run (artifacts
   `proof-windows`, `proof-linux-*`), then publish it.
5. If the run fails: delete the draft (if any) and the tag (`git push --delete origin <tag>`,
   `git tag -d <tag>`), fix the cause on `main`, and tag again. A published tag is never moved.

## Repository settings (once, by hand, after creating the repository)

1. **General:** default branch `main`; Features: Issues on, Discussions off (or on, if wanted),
   Wiki off, Projects off.
2. **General → Pull Requests:** allow squash merging only (turn off merge commits and rebase
   merging); "Default commit message: pull request title and description"; turn on "Always
   suggest updating pull request branches" and "Automatically delete head branches".
3. **Branches → add a branch ruleset (or protection rule) for `main`:** require a pull request
   before merging (1 approval, dismiss stale approvals, require review from code owners);
   require status checks to pass, with the `check` job of the `PR description` workflow required (it appears in the
   list after the workflow has run once); require linear history; block force pushes and
   deletion; do not allow bypassing, except the owner if wanted.
4. **Who may push:** only the owner has write access; contributors work from forks.
5. **Actions → General:** allow GitHub Actions; "Fork pull request workflows from outside
   collaborators: require approval for first-time contributors"; workflow permissions "Read
   repository contents" (read-only token).
6. **Code security:** turn on private vulnerability reporting (needed by `SECURITY.md`),
   secret scanning and push protection, and Dependabot alerts.
7. **Labels:** create the labels in the table above.
8. **Optional, automatic area labels:** `.github/labeler.yml` is ready for the labeller action.
   Adding labels needs a token that can write to pull requests, which the read-only check does
   not have; enable it only with a separate workflow on `pull_request_target` that never checks
   out or runs the pull request's code.
