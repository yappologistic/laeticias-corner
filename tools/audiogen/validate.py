"""Check every audio file named in a catalog against the content contract: container,
codec, sample rate, channels, loudness / true peak (measured by ffmpeg's own EBU R128
meter, independent of the generator), DC offset, clipping, loop seams, effect edges and
durations; then the groups: music stems must sum to their full mix and every unlockable
subset must stay full enough, and the tuned notes must match each other in loudness.
Exit status is the number of failures.

Usage: tools/audiogen/.venv/bin/python tools/audiogen/validate.py [--catalog PATH]"""

import argparse
import itertools
import json
import re
import subprocess
from pathlib import Path

import numpy as np

import mastering

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets" / "catalog.json"
AUDIO = ROOT / "assets" / "audio"

# group -> (format, codec, channels, duration window s, loudness window LUFS, peak ceiling dB)
RULES = {
    "music": ("ogg", "vorbis", 2, (90, 150), (-19.0, -17.0), -1.0),
    "stem": ("ogg", "vorbis", 2, (90, 150), (-45.0, -17.0), -1.0),  # natural level in the mix
    "ambience": ("ogg", "vorbis", 2, (30, 90), (-25.0, -17.0), -1.0),
    "sfx": ("wav", "pcm_s16le", 1, (0.02, 3.2), None, -3.0),
    # Region sets (assets/audio/<set>/manifest.json): music as above, beds at bed level,
    # positional loops a little lower, effects up to 6 s (arrival motifs, horn calls).
    "bed": ("ogg", "vorbis", 2, (30, 90), (-23.5, -20.5), -1.0),
    "loop": ("ogg", "vorbis", 2, (4, 40), (-27.0, -20.0), -1.0),
    "region_sfx": ("wav", "pcm_s16le", 1, (0.02, 6.0), None, -3.0),
}
KINDS = {"music": "music", "bed": "bed", "loop": "loop", "sfx": "region_sfx"}
MUSIC_SAMPLES = 4_704_000  # 32 bars at 72 bpm: the shared loop length of mixes and stems
STEM_RESIDUAL_DB = -20.0  # base stems summed vs the full mix, both decoded (codec noise only)
STEM_SUM_LUFS = (-19.0, -16.5)  # all stems together: the mix plus the colour layer
SUBSET_MIN_LU = -6.0  # quietest unlockable subset relative to the full mix
NOTE_SPREAD_DB = 1.0  # loudest 100 ms, max - min over the tuned notes
NOTE_SECONDS = 1.2
SFX_SHORT_LUFS = (-36.0, -17.0)  # loudest 100 ms: keeps effects mutually balanced
SFX_MAX_SECONDS = {"ui_hover": 0.08, "ui_click": 0.08, "paint": 0.12, "rotate": 0.25,
                   "place_soft": 0.35, "place_wood": 0.35, "place_stone": 0.35,
                   "pick": 0.25, "page": 0.35, "pet": 0.4, "deer": 0.5, "harvest": 0.5,
                   "flap": 0.5, "laeticia_1": 0.5, "laeticia_2": 0.5, "laeticia_3": 0.5}


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=format_name:stream=codec_name,sample_rate,channels",
         "-of", "json", str(path)], check=True, capture_output=True, text=True).stdout
    info = json.loads(out)
    s = info["streams"][0]
    return info["format"]["format_name"], s["codec_name"], int(s["sample_rate"]), int(s["channels"])


def ebur128(path):
    """Integrated loudness and true peak from ffmpeg's meter."""
    log = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true",
         "-f", "null", "-"], check=True, capture_output=True, text=True).stderr
    summary = log[log.rindex("Summary:"):]
    integrated = float(re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary).group(1))
    return integrated, peak


def seam_problems(x):
    """A loop's seam must look like any other moment: no sample jump or 50 ms level step
    across it that is larger than what the file itself contains."""
    problems = []
    jumps = np.abs(np.diff(x, axis=0)).max(axis=1)
    seam = np.abs(x[0] - x[-1]).max()
    if seam > max(np.percentile(jumps, 99.9), 1e-4):
        problems.append(f"seam jump {seam:.4f} > p99.9 {np.percentile(jumps, 99.9):.4f}")
    w, hop = int(0.05 * mastering.SR), int(0.005 * mastering.SR)
    energy = np.concatenate([[0.0], np.cumsum(np.sum(x**2, axis=1))])
    starts = np.arange(0, len(x) - w, hop)
    levels = 10 * np.log10((energy[starts + w] - energy[starts]) / w + 1e-12)
    inner = np.abs(levels[w // hop :] - levels[: -(w // hop)]).max()  # adjacent windows
    step = abs(levels[0] - 10 * np.log10(np.mean(np.sum(x[-w:] ** 2, axis=1)) + 1e-12))
    if step > inner + 0.5:
        problems.append(f"seam level step {step:.1f} dB > {inner:.1f} dB inside the file")
    return problems


def check(group, name, samples=None):
    path = AUDIO / name
    if not path.is_file():
        return None, ["missing"]
    fmt, codec, channels, (dmin, dmax), loud_win, ceiling = RULES[group]
    problems = []
    got = probe(path)
    want = (fmt, codec, mastering.SR, channels)
    if got != want:
        problems.append(f"format {got} != {want}")
    x = mastering.decode(path)
    seconds = len(x) / mastering.SR
    stem = Path(name).stem
    dmax = SFX_MAX_SECONDS.get(stem, dmax) if group == "sfx" else dmax
    sfx_like = group in ("sfx", "region_sfx")
    if not dmin <= seconds <= dmax:
        problems.append(f"duration {seconds:.3f} s outside [{dmin}, {dmax}]")
    want_n = samples if samples is not None else MUSIC_SAMPLES if group in ("music", "stem") else None
    if want_n is not None and len(x) != want_n:
        problems.append(f"{len(x)} samples, not {want_n}")
    lufs, true_peak = ebur128(path)
    sample_peak = mastering.sample_peak_db(x)
    if max(true_peak, sample_peak) > ceiling:
        problems.append(f"peak {max(true_peak, sample_peak):.2f} dB > {ceiling}")
    if np.max(np.abs(x)) >= 0.999:
        problems.append("clipping")
    dc = np.abs(x.mean(axis=0)).max()
    if dc > 1e-3:
        problems.append(f"DC offset {dc:.4f}")
    if sfx_like:
        short = mastering.max_short_lufs(x)
        if not SFX_SHORT_LUFS[0] <= short <= SFX_SHORT_LUFS[1]:
            problems.append(f"loudest 100 ms {short:.1f} LUFS outside {SFX_SHORT_LUFS}")
        if max(abs(x[0]).max(), abs(x[-1]).max()) > 2e-3:
            problems.append("does not start and end at silence")
        loudness = short
    else:
        if not loud_win[0] <= lufs <= loud_win[1]:
            problems.append(f"loudness {lufs:.1f} LUFS outside {loud_win}")
        problems += seam_problems(x)
        loudness = lufs
    return (seconds, loudness, max(true_peak, sample_peak)), problems


def db(x):
    return float(10 * np.log10(x + 1e-30))


def check_stems(piece, entries):
    """All stems but colour must sum to the full mix; the full set sits near the mix level
    under the peak ceiling; every subset the unlock conditions allow (the always-on stems
    plus any combination of the others) stays within reach of the mix's loudness."""
    files = [f"music/{piece}.ogg"] + [e["file"] for e in entries]
    if not all((AUDIO / f).is_file() for f in files):
        return [], ["files missing"]
    stems = {e["id"]: mastering.decode(AUDIO / e["file"]) for e in entries}
    mix = mastering.decode(AUDIO / f"music/{piece}.ogg")
    lines, problems = [], []
    base = sum(stems[s] for s in stems if s != "colour")
    residual = db(np.sum((base - mix) ** 2)) - db(np.sum(mix**2))
    mix_lufs = mastering.integrated_lufs(mix)
    lines.append(f"stem sum vs mix residual {residual:6.1f} dB "
                 f"(residual loudness {mastering.integrated_lufs(base - mix) - mix_lufs:6.1f} LU)")
    if residual > STEM_RESIDUAL_DB:
        problems.append(f"stems do not sum to the mix: residual {residual:.1f} dB")
    always = [e["id"] for e in entries if "when" not in e]
    optional = [e["id"] for e in entries if "when" in e]
    for r in range(len(optional) + 1):
        for extra in itertools.combinations(optional, r):
            ids = always + list(extra)
            y = sum(stems[s] for s in ids)
            lufs, peak = mastering.integrated_lufs(y), mastering.true_peak_db(y)
            lines.append(f"{'+'.join(ids):30s} {lufs:6.1f} LUFS {lufs - mix_lufs:+5.1f} LU "
                         f"peak {peak:6.2f} dB")
            if peak > RULES["music"][5]:
                problems.append(f"{'+'.join(ids)} peaks at {peak:.2f} dB")
            if lufs - mix_lufs < SUBSET_MIN_LU:
                problems.append(f"{'+'.join(ids)} is {lufs - mix_lufs:.1f} LU under the mix")
            if len(ids) == len(stems) and not STEM_SUM_LUFS[0] <= lufs <= STEM_SUM_LUFS[1]:
                problems.append(f"all stems at {lufs:.1f} LUFS outside {STEM_SUM_LUFS}")
    return lines, problems


def check_notes(names):
    """Tuned placement notes: same length, and level-matched by their loudest 100 ms."""
    levels, problems = [], []
    for name in names:
        x = mastering.decode(AUDIO / name)
        levels.append(mastering.max_short_lufs(x))
        if abs(len(x) / mastering.SR - NOTE_SECONDS) > 0.01:
            problems.append(f"{name} lasts {len(x) / mastering.SR:.3f} s, not {NOTE_SECONDS}")
    spread = max(levels) - min(levels)
    if spread > NOTE_SPREAD_DB:
        problems.append(f"note loudness spread {spread:.2f} dB > {NOTE_SPREAD_DB}")
    lines = [f"note loudness {min(levels):.2f} .. {max(levels):.2f} LUFS (spread {spread:.2f} dB)"]
    return lines, problems


def check_sets():
    """Every region set's manifest: each listed file passes its kind's rules and matches
    the manifest's length; every file in the set's folders is listed. Returns (listed
    files, failure count)."""
    listed, failures = set(), 0
    for manifest in sorted(AUDIO.glob("*/manifest.json")):
        doc = json.loads(manifest.read_text())
        set_name = doc["set"]
        listed.add(manifest.relative_to(AUDIO).as_posix())
        print(f"set {set_name}:")
        names = set()
        for e in doc["files"]:
            name = e["file"]
            names.add(name)
            group = KINDS[e["kind"]]
            stats, problems = check(group, name, e["samples"] if e["loop"] else None)
            if stats and abs(stats[0] - e["seconds"]) > 1e-3:
                problems.append(f"manifest says {e['seconds']} s")
            if e["loop"] != (group != "region_sfx"):
                problems.append("loop flag does not match its kind")
            failures += bool(problems)
            cols = f"{stats[0]:8.2f} {stats[1]:7.1f} {stats[2]:8.2f}" if stats else " " * 25
            print(f"  {name:32s} {cols}  {'; '.join(problems) or 'ok'}")
        on_disk = {p.relative_to(AUDIO).as_posix() for sub in ("music", "amb", "sfx")
                   for p in (AUDIO / sub / set_name).glob("*") if p.is_file()}
        for name in sorted(on_disk - names):
            failures += 1
            print(f"  {name:32s} not in the manifest")
        listed |= names
    return listed, failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--catalog", type=Path, default=CATALOG)
    audio = json.loads(ap.parse_args(argv).catalog.read_text())["audio"]
    stem_files = {e["file"] for entries in audio.get("stems", {}).values() for e in entries}
    listed = set()
    failures = 0
    print(f"{'file':26s} {'seconds':>8s} {'LUFS':>7s} {'peak dB':>8s}  result")
    for group in ("music", "ambience", "sfx"):
        for name in audio[group]:
            listed.add(name)
            stats, problems = check("stem" if name in stem_files else group, name)
            failures += bool(problems)
            cols = f"{stats[0]:8.2f} {stats[1]:7.1f} {stats[2]:8.2f}" if stats else " " * 25
            print(f"{name:26s} {cols}  {'; '.join(problems) or 'ok'}")
    groups = [(f"stems: {piece}", check_stems, (piece, entries))
              for piece, entries in audio.get("stems", {}).items()]
    if audio.get("notes"):
        groups.append(("notes", check_notes, (audio["notes"],)))
    for title, fn, fn_args in groups:
        lines, problems = fn(*fn_args)
        failures += len(problems)
        print(f"{title}: {'; '.join(problems) or 'ok'}")
        for line in lines:
            print("   ", line)
    set_files, set_failures = check_sets()
    failures += set_failures
    listed |= set_files
    # The folder may run ahead of a catalog during a batch: unlisted files are reported,
    # not failed, so the live catalog still validates before the next one is promoted.
    for path in sorted(p for p in AUDIO.rglob("*") if p.is_file()):
        rel = path.relative_to(AUDIO).as_posix()
        if rel not in listed:
            print(f"{rel:26s} not in this catalog (ignored)")
    print("(sfx LUFS column = loudest 100 ms; loops = integrated)")
    print("validation", "passed" if failures == 0 else f"FAILED ({failures} problem(s))")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
