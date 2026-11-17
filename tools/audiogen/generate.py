"""Render every audio file named in assets/catalog.json into assets/audio/, then run
the validator. Deterministic: each file's RNG is seeded from its own name.

Usage: tools/audiogen/generate.sh [name-filter ...]   (e.g. `sfx/` or `music/day`)"""

import json
import os
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# One BLAS thread per worker: the build already runs one process per core, and
# oversubscribed spinning BLAS threads slow it down by orders of magnitude.
os.environ["OPENBLAS_NUM_THREADS"] = os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np  # noqa: E402  (must follow the thread setting)

import ambience  # noqa: E402
import mastering  # noqa: E402
import music  # noqa: E402
import sfx  # noqa: E402
import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets" / "catalog.json"
OUT = ROOT / "assets" / "audio"

# Loops: name -> (renderer, integrated loudness target in LUFS, Vorbis quality).
LOOPS = {
    "music/day.ogg": (music.day, -18.0, 4),
    "music/night.ogg": (music.night, -18.0, 4),
    "amb/birds.ogg": (ambience.birds, -23.0, 3),
    "amb/crickets.ogg": (ambience.crickets, -23.0, 3),
    "amb/rain.ogg": (ambience.rain, -21.0, 3),
    "amb/water.ogg": (ambience.water, -22.0, 3),
}

# Effects: name -> (renderer, loudest-100 ms target in LUFS). Relative levels are the
# mix: placements sit a little under the music, UI ticks far under it.
EFFECTS = {
    "sfx/place_soft.wav": (sfx.place_soft, -21.0),
    "sfx/place_wood.wav": (sfx.place_wood, -20.0),
    "sfx/place_stone.wav": (sfx.place_stone, -21.0),
    "sfx/splash.wav": (sfx.splash, -21.0),
    "sfx/paint.wav": (sfx.paint, -27.0),
    "sfx/remove.wav": (sfx.remove, -22.0),
    "sfx/rotate.wav": (sfx.rotate, -25.0),
    "sfx/invalid.wav": (sfx.invalid, -23.0),
    "sfx/undo.wav": (sfx.undo, -24.0),
    "sfx/redo.wav": (sfx.redo, -24.0),
    "sfx/ui_hover.wav": (sfx.ui_hover, -33.0),
    "sfx/ui_click.wav": (sfx.ui_click, -27.0),
    "sfx/ui_open.wav": (sfx.ui_open, -25.0),
    "sfx/ui_close.wav": (sfx.ui_close, -25.0),
    "sfx/shutter.wav": (sfx.shutter, -21.0),
    "sfx/discover.wav": (sfx.discover, -20.0),
    "sfx/duck.wav": (sfx.duck, -21.0),
    "sfx/hen.wav": (sfx.hen, -21.0),
    "sfx/cat.wav": (sfx.cat, -21.0),
}


def catalog_names():
    audio = json.loads(CATALOG.read_text())["audio"]
    return [name for group in ("music", "ambience", "sfx") for name in audio[group]]


def alignment_lag(a, b, span=5 * mastering.SR):
    """Lag (samples) at which b best matches a: proves the encoder kept sample alignment.
    Waveform error is no use here, since Vorbis legitimately rebuilds noise differently."""
    a, b = a[:span].sum(axis=1), b[:span].sum(axis=1)
    corr = np.fft.irfft(np.fft.rfft(b, 2 * span) * np.conj(np.fft.rfft(a, 2 * span)))
    lag = int(np.argmax(corr))
    return lag if lag < span else lag - 2 * span


def build(name):
    """Render, master and write one file; returns a one-line summary."""
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if name in LOOPS:
        render, target, quality = LOOPS[name]
        x = mastering.master_loop(render(rng), target)
        mastering.write_ogg(path, x, quality)
        back = mastering.decode(path)
        assert back.shape == x.shape, f"{name}: Ogg round trip changed length {x.shape} -> {back.shape}"
        lag = alignment_lag(x, back)
        assert lag == 0, f"{name}: Ogg round trip shifted the audio by {lag} samples"
    else:
        render, target = EFFECTS[name]
        x = mastering.master_sfx(render(rng), target)
        mastering.write_wav16(path, x)
    return f"{name:22s} {len(x) / mastering.SR:7.2f} s"


def main(filters):
    names = catalog_names()
    missing = set(names) - set(LOOPS) - set(EFFECTS)
    extra = (set(LOOPS) | set(EFFECTS)) - set(names)
    if missing or extra:
        sys.exit(f"catalog/generator mismatch: missing {sorted(missing)}, unknown {sorted(extra)}")
    todo = [n for n in names if not filters or any(f in n for f in filters)]
    with ProcessPoolExecutor() as pool:
        for line in pool.map(build, todo):
            print("rendered", line, flush=True)
    sys.exit(validate.main())


if __name__ == "__main__":
    main(sys.argv[1:])
