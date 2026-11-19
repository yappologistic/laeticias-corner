# AI assistance

Contributors may use AI tools: coding agents, editor integrations, chat assistants. What matters
is that the work is correct, that a person stands behind it, and that everyone can see how it
was made.

## Disclosure is mandatory

Every issue and every pull request states, also when the answer is "none":

1. **The tool or harness**: the kind of tool and its name as you used it (a coding agent in the
   terminal, an editor integration, a chat product, a local runner), or "none".
2. **The exact model identifier and version**, as the tool reports it (for example in its
   settings, its `--version` output or its about screen). "The latest model" or a product name
   without a version is not enough. If several models were used, list each and what it did.
3. **What it produced**: the code, the tests, the text of the issue or the description, the
   analysis, the scripts, the screenshots' set-up. Be specific: "drafted the parser and its
   tests; I rewrote the error handling" is useful, "helped" is not.
4. **Your statement** that you have read every line, built it and run it yourself, and that you
   answer for it. The forms have a box for this.

The pull request check fails when a field is empty, when a tool is named without a model
version, or when the box is not ticked. The issue forms will not submit without them.

**Undisclosed or misdescribed assistance closes the contribution.** Repeated, it ends the
contributor's participation.

## What stays the same with or without AI

- You are the author. Review comments are answered by you, from your own understanding of the
  change.
- The proof of work ([proof of work](proof-of-work.md)) is the same: real commands you ran, real
  output, real screenshots. Output that was not produced by running the code (invented test
  results, edited logs, mock-ups presented as screenshots) closes the contribution.
- Small, focused changes. A tool makes large diffs cheap to write; they are still expensive to
  review, and they are declined.
- Do not paste private material into a tool you do not control: other people's code under
  licences that forbid it, secrets, personal data.

## No outside generated art or audio

Every sprite, sound and piece of music in the game is produced by the repository's own
deterministic generators under `tools/`. Images, sounds, music or voices produced by outside
generative models, or taken from other sources, are not accepted, also not as a starting point
that is then edited. Two reasons:

- **Reproducibility.** Anyone can regenerate every asset from the code with fixed seeds and get
  the same bytes. A file that only exists as an output cannot be regenerated, changed
  consistently with the rest (a new tile size, a palette change, a season) or reviewed as code.
- **Licence clarity.** The assets are licensed CC BY-NC-SA 4.0 and the owner may also distribute
  them commercially. That requires a clear chain of authorship for every file, which outside
  model output and found material cannot give.

You may of course use an AI tool to help write the *generator code* that makes art or audio, as
long as it is disclosed like any other code.
