# audiogen

Synthesises every file listed under `audio` in `assets/catalog.json` into `assets/audio/`.
No samples or soundfonts: every sound is built from oscillators, noise and filters, so the
output is fully original and licence-free. Rendering is deterministic (each file's RNG is
seeded from its name; Ogg is written with ffmpeg's bit-exact flags).

```sh
tools/audiogen/generate.sh              # render everything, then validate
tools/audiogen/generate.sh sfx/ duck    # re-render only names containing a filter
tools/audiogen/.venv/bin/python tools/audiogen/validate.py   # validate only
```

Needs Python 3, `ffmpeg`/`ffprobe` with libvorbis. The script creates `.venv` from the
pinned `requirements.txt`. Nothing is ever played back.

| Module | Role |
|---|---|
| `dsp.py` | envelopes, filters, periodic noise, panning, convolution reverb, loop wrapping |
| `instruments.py` | felt piano, music-box tine, warm pad, sub bass |
| `music.py` | chord table, note-data notation, the day and night pieces |
| `ambience.py` | birds, crickets (+owl, frog), rain, water |
| `sfx.py` | placement, UI, chime and animal effects |
| `mastering.py` | BS.1770 loudness, true-peak limiter, WAV/Ogg writing, decoding |
| `validate.py` | contract checks, using ffmpeg's EBU R128 meter as an independent reference |
| `generate.py` | catalog ↔ renderer table, loudness targets, parallel build |

## Loops

Music and ambience are seamless whole-file loops: play the decoded stream from sample 0
to its end and jump straight back to sample 0. Music loops are an exact number of bars
(32 bars at 72 bpm = 106.667 s = 4 704 000 samples). Reverb and note tails that run past
the end are folded onto the start, beds are periodic noise generated in the frequency
domain, and every filter is run circularly, so the seam is a moment like any other. The
generator decodes each Ogg after writing it and fails if the sample count changed.
