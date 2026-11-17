# audiogen

Synthesises every file listed under `audio` in a catalog (default `assets/catalog.json`)
into `assets/audio/`.
No samples or soundfonts: every sound is built from oscillators, noise and filters, so the
output is fully original and licence-free. Rendering is deterministic (each file's RNG is
seeded from its name; Ogg is written with ffmpeg's bit-exact flags).

```sh
tools/audiogen/generate.sh              # render everything, then validate
tools/audiogen/generate.sh sfx/ duck    # re-render only names containing a filter
tools/audiogen/generate.sh --catalog docs/design/catalog.next.json   # a batch's catalog
tools/audiogen/.venv/bin/python tools/audiogen/validate.py [--catalog PATH]   # validate only
```

Files in `assets/audio/` that the chosen catalog does not list are reported, not failed,
so the live catalog still validates while the folder runs ahead of it during a batch.

Needs Python 3, `ffmpeg`/`ffprobe` with libvorbis. The script creates `.venv` from the
pinned `requirements.txt`. Nothing is ever played back.

| Module | Role |
|---|---|
| `dsp.py` | envelopes, filters, periodic noise, panning, convolution reverb, loop wrapping |
| `instruments.py` | felt piano, music-box tine, pad, bass; flute, shaker, cello harmonic, clarinet; harp, glass, bell |
| `music.py` | chord table, note-data notation, the day and night pieces and their stems |
| `ambience.py` | birds, crickets (+owl, frog), rain, water; autumn, winter, spring and winter nights, waterfall |
| `sfx.py` | placement, UI, tuned notes, stingers, nature, critter voices, Laeticia |
| `mastering.py` | BS.1770 loudness, true-peak limiter, WAV/Ogg writing, decoding |
| `validate.py` | contract checks (ffmpeg's EBU R128 meter as an independent reference), stem sums and subsets, note balance |
| `ancient.py` | waveguide plucked strings (angular harp, long-necked lute, kithara, lyra, barbitos, cithara), reed pipes as continuous phrases (double pipe, aulos, tibia), frame drum, clappers, cymbals, sistrum, hydraulis, horns, hummed voices |
| `score.py` | note notation with exact fractions (dyads, graces, slurs, percussion strokes), rubato, piece renderer, loop facts for manifests |
| `sounds.py` | bed assembly (`Bed`), wordless crowds and songs, birds and animals, struck stone and metal, feet, hooves, wheels, water, fire, insects, workshops |
| `parsa.py`, `athens.py`, `rome.py`, `world.py` | each region set: music, beds, positional loops, effects and its `FILES` table |
| `generate.py` | catalog ↔ renderer table, loudness targets, region sets and their manifests, parallel build |

## Loops

Music and ambience are seamless whole-file loops: play the decoded stream from sample 0
to its end and jump straight back to sample 0. Music loops are an exact number of bars
(32 bars at 72 bpm = 106.667 s = 4 704 000 samples). Reverb and note tails that run past
the end are folded onto the start, beds are periodic noise generated in the frequency
domain, and every filter is run circularly, so the seam is a moment like any other. The
generator decodes each Ogg after writing it and fails if the sample count changed.

## Stems

`music/<piece>_{pad,keys,melody,bass,colour}.ogg` come from the same render as
`music/<piece>.ogg`: every note is routed to one stem as well as to the mix, each stem
gets its own share of the same reverb, and all stems receive the mix's exact mastering
gain curve. So pad + keys + melody + bass equals the full mix (only Vorbis noise differs),
and colour is an extra layer in the same room. Stems are not normalised individually.
All mixes and stems have the same 4 704 000-sample length and start together at sample 0.

## Voices

Animal and human voices use `dsp.voice`: harmonics with a glottal spectral tilt, random
jitter and shimmer, optional period-doubling roughness, and aspiration noise filtered
through the same time-varying formants (`dsp.formant_noise`, frame by frame in the STFT).

## Region sets

The city and world audio is not in the catalog: each set module (`parsa`, `athens`, `rome`,
`world`) lists its files in `FILES`, and the generator writes them to
`assets/audio/<music|amb|sfx>/<set>/` (the layout in `docs/design/world-tech.md` §2.2) plus a
manifest at `assets/audio/<set>/manifest.json`: per file its kind (`music`, `bed`, `loop`,
`sfx`), loop flag, exact length, suggested gain, when and where it plays, and what it is for;
music also carries bpm, metre, bars and the seconds where phrases begin (the engine restarts a
piece at a phrase boundary). `tools/audiogen/generate.sh rome/` renders one set. The validator
checks every manifest: each file against its kind's rules, its length against the manifest,
and that every file in the set's folders is listed.

City music is note data in the set module, rendered by `score.render` with all tails folded,
so every piece is an exact number of bars; beds and loops are seamless the same way (periodic
noise, events wrapped, every filter run circularly).
