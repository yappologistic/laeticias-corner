# audiogen

Synthesises every file listed under `audio` in a catalog (default `assets/catalog.json`)
into `assets/audio/`.
No samples or soundfonts: every sound is built from oscillators, noise and filters, so the
output is fully original and licence-free. Rendering is deterministic (each file's RNG is
seeded from its name; Ogg is written with ffmpeg's bit-exact flags).

```sh
# Two worker processes; run under a memory limit so a mistake fails fast:
(ulimit -v 4000000; nice -n 19 tools/audiogen/generate.sh)
tools/audiogen/generate.sh              # render everything, then validate
tools/audiogen/generate.sh sfx/ duck    # re-render only names containing a filter
tools/audiogen/generate.sh --catalog docs/design/catalog.next.json   # a batch's catalog
tools/audiogen/.venv/bin/python tools/audiogen/validate.py [--catalog PATH]   # validate only
```

Files in `assets/audio/` that the chosen catalog does not list are reported, not failed,
so the live catalog still validates while the folder runs ahead of it during a batch.

Measure (resumable: rows go to `OUT.rows.jsonl` as each file finishes; one file per task):

```sh
(ulimit -v 4000000; nice -n 19 tools/audiogen/.venv/bin/python tools/audiogen/measure.py \
    out/audiogen/after.json --compare out/audiogen/before.json --md out/audiogen/after.md)
```

Memory: every process stays under 1 GB. Long signals are processed a block or a channel at a
time (true peak and the limiter's oversampled envelope in blocks, circular filters warmed up from
the loop's last two seconds instead of a second copy, music stems in float32 and finished one at
a time); mono files are flat arrays, never `(n, 1)` (they broadcast against windows).

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
| `atmos.py` | atmosphere helpers: seamless event trains by circular convolution, phase-closed oscillators, slow curves and gusts, the 8th-order `tame` low-pass, the `entry` table format |
| `weather.py` | wind (4 strengths × open, street, sea, mountain), rain (3 intensities) and surface layers, thunder, snow, fog, heat, dust, sea state (coast, harbour), rivers, waterfalls, fires, turns of weather |
| `wildlife.py` | dawn, dusk and night beds by climate, cicadas in three heats, animal voices (syllable model) with variations, the home duck/hen/cat |
| `people.py` | wordless crowds (3 sizes × Latin, Greek, Persian), footsteps, hooves and carts, work loops and effects, crowd responses, a far chorus, a wedding song, Laeticia's steps and watering can |
| `stings.py` | sunrise, nightfall, storm clearing, rainbow and first-snow stings in the home key and each city's mode |
| `seasons.py` | the year in sound: the cities' seasonal beds, autumn and winter nature beds and snow beds for the countryside, spring frogs, wind in bare branches, the winter marsh, floodwater, the seasons' work loops, each civilization's festival loops and instruments, the season-turn stings and turn cues |
| `between.py` | the land and sea between the cities: wind in leafy trees, rocky shores and the open sea by state, streams, a grazing flock, oars; one-shots (cart passing, sail, owls, wolves, nightingale, stag, geese, starlings, lark, gulls, drips) |
| `measure.py` | the quality pass by instrument: per file loudness, true peak, loudness range, loudest 100 ms, spectral balance against a stated target, stereo width and mono fold, seam (jump, level and spectral step), period of repetition, DC, edges, noise floor; music stems, bars, sums, day/night match, notes against the key; before/after tables |
| `generate.py` | catalog ↔ renderer table, loudness targets, region sets and their manifests, parallel build |

## Intensity families

Weather, sea, rivers, cicadas and crowds come in families (`family`, `level`, `level_name` in
the manifest): one recipe sampled at each level from independent noise, mastered in steps of
3.5 LU, so the engine cross-fades neighbours at unity gain and two neighbours played together
add in power. The validator checks each family's steps, that neighbour sums stay within 1 LU
of the power sum (no phasing), that neighbours are uncorrelated and keep their colour. Files
of the atmosphere sets also carry `tags` (surface, climate, what they are) and must keep their
energy above 8 kHz at least 25 dB under the whole. `assets/audio/home/manifest.json` lists the
home additions the catalog does not (variations, Laeticia's steps, stings).

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
