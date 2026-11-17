"""Check every audio file named in assets/catalog.json against the content contract:
container, codec, sample rate, channels, loudness / true peak (measured by ffmpeg's
own EBU R128 meter, independent of the generator), DC offset, clipping, loop seams,
effect edges and durations. Exit status is the number of failing files.

Usage: tools/audiogen/.venv/bin/python tools/audiogen/validate.py"""

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
    "ambience": ("ogg", "vorbis", 2, (30, 60), (-25.0, -17.0), -1.0),
    "sfx": ("wav", "pcm_s16le", 1, (0.02, 2.0), None, -3.0),
}
SFX_SHORT_LUFS = (-36.0, -17.0)  # loudest 100 ms: keeps effects mutually balanced
SFX_MAX_SECONDS = {"ui_hover": 0.08, "ui_click": 0.08, "paint": 0.12, "rotate": 0.25,
                   "place_soft": 0.35, "place_wood": 0.35, "place_stone": 0.35}


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


def check(group, name):
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
    if not dmin <= seconds <= dmax:
        problems.append(f"duration {seconds:.3f} s outside [{dmin}, {dmax}]")
    lufs, true_peak = ebur128(path)
    sample_peak = mastering.sample_peak_db(x)
    if max(true_peak, sample_peak) > ceiling:
        problems.append(f"peak {max(true_peak, sample_peak):.2f} dB > {ceiling}")
    if np.max(np.abs(x)) >= 0.999:
        problems.append("clipping")
    dc = np.abs(x.mean(axis=0)).max()
    if dc > 1e-3:
        problems.append(f"DC offset {dc:.4f}")
    if group == "sfx":
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


def main():
    audio = json.loads(CATALOG.read_text())["audio"]
    listed = set()
    failures = 0
    print(f"{'file':22s} {'seconds':>8s} {'LUFS':>7s} {'peak dB':>8s}  result")
    for group in ("music", "ambience", "sfx"):
        for name in audio[group]:
            listed.add(name)
            stats, problems = check(group, name)
            failures += bool(problems)
            cols = f"{stats[0]:8.2f} {stats[1]:7.1f} {stats[2]:8.2f}" if stats else " " * 25
            print(f"{name:22s} {cols}  {'; '.join(problems) or 'ok'}")
    for path in sorted(p for p in AUDIO.rglob("*") if p.is_file()):
        rel = path.relative_to(AUDIO).as_posix()
        if rel not in listed:
            failures += 1
            print(f"{rel:22s} not in the catalog")
    print("(sfx LUFS column = loudest 100 ms; loops = integrated)")
    print("validation", "passed" if failures == 0 else f"FAILED for {failures} file(s)")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
