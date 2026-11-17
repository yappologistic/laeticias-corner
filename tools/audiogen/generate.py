"""Render every audio file named in a catalog (default assets/catalog.json) into
assets/audio/, then run the validator. Deterministic: each file's RNG is seeded from its
own name.

Usage: tools/audiogen/generate.sh [--catalog PATH] [name-filter ...]
       (e.g. `sfx/` or `music/day`; a filter matching any stem renders its whole piece)"""

import argparse
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
import athens  # noqa: E402
import mastering  # noqa: E402
import music  # noqa: E402
import parsa  # noqa: E402
import score  # noqa: E402
import sfx  # noqa: E402
import validate  # noqa: E402
from dsp import stereo  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "audio"
WORKERS = 4  # machine courtesy: the owner uses this computer while it renders

# Loops: name -> (renderer, integrated loudness target in LUFS, Vorbis quality).
LOOPS = {
    "music/day.ogg": (music.day, -18.0, 4),
    "music/night.ogg": (music.night, -18.0, 4),
    "amb/birds.ogg": (ambience.birds, -23.0, 3),
    "amb/crickets.ogg": (ambience.crickets, -23.0, 3),
    "amb/rain.ogg": (ambience.rain, -21.0, 3),
    "amb/water.ogg": (ambience.water, -22.0, 3),
    "amb/autumn.ogg": (ambience.autumn, -22.0, 1),
    "amb/winter.ogg": (ambience.winter, -23.0, 1),
    "amb/night_spring.ogg": (ambience.night_spring, -23.0, 1),
    "amb/night_winter.ogg": (ambience.night_winter, -23.0, 1),
    "amb/waterfall.ogg": (ambience.waterfall, -21.0, 1),
}

# Music pieces whose stems are rendered from the same session as the full mix.
PIECES = {"music/day.ogg": music.DAY, "music/night.ogg": music.NIGHT}
STEM_QUALITY = 2  # stems add up: q2 keeps the folder near 15 MB and attacks clean

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
    # Notes are played by the engine ~8 dB under the place sounds (kNoteLevel).
    **{f"sfx/note_{i}.wav": (sfx.note(i), -21.0) for i in range(len(sfx.NOTES))},
    "sfx/owl.wav": (sfx.owl, -23.0),
    "sfx/heron.wav": (sfx.heron, -24.0),
    "sfx/hedgehog.wav": (sfx.hedgehog, -24.0),
    "sfx/fox.wav": (sfx.fox, -23.0),
    "sfx/frog.wav": (sfx.frog, -23.0),
    "sfx/robin.wav": (sfx.robin, -24.0),
    "sfx/deer.wav": (sfx.deer, -24.0),
    "sfx/laeticia_1.wav": (sfx.laeticia_1, -24.0),
    "sfx/laeticia_2.wav": (sfx.laeticia_2, -24.0),
    "sfx/laeticia_3.wav": (sfx.laeticia_3, -25.0),
    "sfx/purr.wav": (sfx.purr, -25.0),
    "sfx/pet.wav": (sfx.pet, -24.0),
    "sfx/wish.wav": (sfx.wish, -22.0),
    "sfx/wish_granted.wav": (sfx.wish_granted, -20.0),
    "sfx/nook.wav": (sfx.nook, -20.0),
    "sfx/land_open.wav": (sfx.land_open, -20.0),
    "sfx/season.wav": (sfx.season, -21.0),
    "sfx/harvest.wav": (sfx.harvest, -22.0),
    "sfx/rustle.wav": (sfx.rustle, -25.0),
    "sfx/flap.wav": (sfx.flap, -24.0),
    "sfx/gust.wav": (sfx.gust, -24.0),
    "sfx/rainbow.wav": (sfx.rainbow, -21.0),
    "sfx/twinkle.wav": (sfx.twinkle, -24.0),
    "sfx/well.wav": (sfx.well, -22.0),
    "sfx/pick.wav": (sfx.pick, -25.0),
    "sfx/page.wav": (sfx.page, -26.0),
}


# Region sets (world-tech §2.2: assets/audio/<music|amb|sfx>/<set>/…), each with a manifest
# at assets/audio/<set>/manifest.json for the engine and the region theme files.
SETS = {"parsa": parsa.FILES, "athens": athens.FILES}
REGION = {name: entry for files in SETS.values() for name, entry in files.items()}


def alignment_lag(a, b, span=5 * mastering.SR):
    """Lag (samples) at which b best matches a: proves the encoder kept sample alignment.
    Waveform error is no use here, since Vorbis legitimately rebuilds noise differently."""
    a, b = a[:span].sum(axis=1), b[:span].sum(axis=1)
    corr = np.fft.irfft(np.fft.rfft(b, 2 * span) * np.conj(np.fft.rfft(a, 2 * span)))
    lag = int(np.argmax(corr))
    return lag if lag < span else lag - 2 * span


def write_loop(name, x, quality):
    """Encode a loop and prove the round trip kept its length and sample alignment."""
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    mastering.write_ogg(path, x, quality)
    back = mastering.decode(path)
    assert back.shape == x.shape, f"{name}: Ogg round trip changed length {x.shape} -> {back.shape}"
    lag = alignment_lag(x, back)
    assert lag == 0, f"{name}: Ogg round trip shifted the audio by {lag} samples"
    return f"{name:26s} {len(x) / mastering.SR:7.2f} s"


def build(job):
    """Render, master and write one file (or a piece and its stems); returns summary lines."""
    name, stems = job
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    if name in REGION:
        return [build_region(name, REGION[name], rng)]
    if name in LOOPS:
        render, target, quality = LOOPS[name]
        if not stems:
            # Low-bitrate Vorbis overshoots more on transients, so give it more headroom.
            ceiling = -1.5 if quality >= 2 else -2.5
            x = mastering.master_loop(render(rng), target, ceiling)[0]
            return [write_loop(name, x, quality)]
        # Stems share the mix's mastering gain curve, so they still sum to it exactly.
        colour_rng = np.random.default_rng(zlib.crc32(stems["colour"].encode()))
        mix, parts = music.render(PIECES[name], rng, colour_rng)
        x, gain = mastering.master_loop(mix, target)
        lines = [write_loop(name, x, quality)]
        for stem, file in stems.items():
            lines.append(write_loop(file, parts[stem] * gain[:, None], STEM_QUALITY))
        return lines
    render, target = EFFECTS[name]
    x = mastering.master_sfx(render(rng), target)
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    mastering.write_wav16(path, x)
    return [f"{name:26s} {len(x) / mastering.SR:7.2f} s"]


def build_region(name, entry, rng):
    """Render, master and write one region-set file."""
    x = entry["render"](rng)
    if entry["kind"] == "sfx":
        x = mastering.master_sfx(x, entry["lufs"])
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        mastering.write_wav16(path, x)
        return f"{name:26s} {len(x) / mastering.SR:7.2f} s"
    x = stereo(x)  # positional loops may be built mono; every loop file is stereo
    x = mastering.master_loop(x, entry["lufs"], -1.5 if entry["quality"] >= 2 else -2.5)[0]
    return write_loop(name, x, entry["quality"])


def write_manifest(set_name, files):
    """assets/audio/<set>/manifest.json: every file of the set with what the engine needs."""
    entries = []
    for name, e in files.items():
        path = OUT / name
        if not path.is_file():
            continue
        samples = len(mastering.decode(path))
        item = {"file": name, "kind": e["kind"], "loop": e["kind"] != "sfx",
                "seconds": round(samples / mastering.SR, 4), "samples": samples,
                "gain": e["gain"], "when": e.get("when", "event"), "for": e["purpose"]}
        if "where" in e:
            item["where"] = e["where"]
        if "piece" in e:
            item["music"] = score.info(e["piece"])
            assert item["music"]["samples"] == samples, name
        entries.append(item)
    out = OUT / set_name / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {"version": 1, "set": set_name, "files": entries}
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def jobs(audio):
    """(name, {stem id: file}) for every renderable entry; stems ride with their piece."""
    stems = {f"music/{piece}.ogg": {s["id"]: s["file"] for s in entries}
             for piece, entries in audio.get("stems", {}).items()}
    stem_files = {f: piece for piece, files in stems.items() for f in files.values()}
    names = [n for group in ("music", "ambience", "sfx") for n in audio[group]]
    unknown = [n for n in names if n not in LOOPS and n not in EFFECTS and n not in stem_files]
    if unknown:
        sys.exit(f"no renderer for {unknown}")
    for piece, files in stems.items():
        if piece not in PIECES or set(files) != set(music.STEMS) | {"colour"}:
            sys.exit(f"stems of {piece} must be {sorted(set(music.STEMS) | {'colour'})}")
    return [(n, stems.get(n, {})) for n in names if n not in stem_files], stem_files


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--catalog", type=Path, default=validate.CATALOG)
    ap.add_argument("filters", nargs="*")
    args = ap.parse_args()
    todo, stem_files = jobs(json.loads(args.catalog.read_text())["audio"])
    todo += [(name, {}) for name in REGION]
    wanted = {piece for f, piece in stem_files.items() if any(x in f for x in args.filters)}

    def selected(job):
        name = job[0]
        return not args.filters or name in wanted or any(f in name for f in args.filters)

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for lines in pool.map(build, [j for j in todo if selected(j)]):
            for line in lines:
                print("rendered", line, flush=True)
    for set_name, files in SETS.items():
        write_manifest(set_name, files)
    sys.exit(validate.main(["--catalog", str(args.catalog)]))


if __name__ == "__main__":
    main()
