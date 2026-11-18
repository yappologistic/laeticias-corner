"""Measure every audio file in assets/audio the way an ear would be asked to judge it, and
write a table: loudness (integrated and true peak by ffmpeg's EBU R128 meter; loudness range by
EBU Tech 3342 on the loop as it plays, wrapped), loudest 100 ms for effects, spectral balance
against a stated target, stereo width and mono compatibility, loop seam (sample jump, level step,
spectral step), the audible period of repetition, DC offset, clicks at the edges and the noise
floor; then the music checks (stem lengths and bar alignment, the sum of every stem, day/night
level match, the tuned notes against the stems' key).

Spectral target: energy per third-octave band, 63 Hz to 8 kHz, should fall with frequency like
natural ambience and acoustic music, a tilt between -1 and -8 dB per octave above 500 Hz, with no
octave region more than 6 dB above the fitted line: a bump at 2-5 kHz is "harsh", at 250-800 Hz
"boxy", at 100-300 Hz "muddy"; beds and music with less than 1/300 of their energy under 200 Hz
are "thin". Energy above 8 kHz more than -20 dB of the whole is "harsh" too.

Usage: tools/audiogen/.venv/bin/python tools/audiogen/measure.py OUT.json [--compare OLD.json]
       [--md OUT.md] [filters ...]"""

import os

# One BLAS thread per process: workers are few and capped in memory (ulimit -v).
os.environ["OPENBLAS_NUM_THREADS"] = os.environ["OMP_NUM_THREADS"] = "1"

import argparse  # noqa: E402
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy import signal

import mastering

ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "assets" / "audio"
SR = mastering.SR
WORKERS = 2  # machine courtesy: run under `ulimit -v 4000000` and nice
BANDS = 1000.0 * 2.0 ** (np.arange(-14, 10) / 3.0)  # third octaves, 40 Hz .. 8 kHz


def kind_of(name, manifests):
    if name in manifests:
        return manifests[name]["kind"]
    if name.startswith("music/"):
        return "stem" if any(s in name for s in ("_pad", "_keys", "_melody", "_bass", "_colour")) \
            else "music"
    return "bed" if name.startswith("amb/") else "sfx"


def ffmpeg_r128(path):
    log = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path), "-af",
                          "ebur128=peak=true", "-f", "null", "-"],
                         check=True, capture_output=True, text=True).stderr
    s = log[log.rindex("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", s).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", s).group(1))
    return i, tp


def lra(x, loop):
    """EBU Tech 3342 loudness range: 3 s short-term windows every 1 s (wrapping round a loop),
    absolute gate -70 LUFS, relative gate -20 LU, the 10th to 95th percentile."""
    y = mastering._k_filter(x if x.ndim == 2 else x[:, None])
    p = np.sum(y**2, axis=1)
    w, hop = 3 * SR, SR
    if loop:
        p = np.concatenate([p, p[:w]])
    if len(p) < w:
        return 0.0, -70.0
    c = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, len(p) - w + 1, hop)
    st = -0.691 + 10 * np.log10((c[starts + w] - c[starts]) / w + 1e-30)
    st = st[st > -70]
    if not len(st):
        return 0.0, -70.0
    rel = -0.691 + 10 * np.log10(np.mean(10 ** ((st + 0.691) / 10))) - 20
    st = st[st > rel]
    return float(np.percentile(st, 95) - np.percentile(st, 10)), float(np.percentile(st, 10))


def spectrum(x):
    """Third-octave band energies (dB re the whole) of the mono fold."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    f, pxx = signal.welch(m, SR, nperseg=8192)
    tot = pxx.sum() + 1e-30
    lo, hi = BANDS * 2 ** (-1 / 6), BANDS * 2 ** (1 / 6)
    e = np.array([pxx[(f >= a) & (f < b)].sum() for a, b in zip(lo, hi)]) / tot
    under200 = pxx[f < 200].sum() / tot
    over8k = pxx[f > 8000].sum() / tot
    return 10 * np.log10(e + 1e-12), under200, over8k, float((f * pxx).sum() / tot)


def tonal_flags(bands, kind):
    """Flags from third-octave band levels (dB re the whole): a bump at 250-630 Hz over both
    neighbouring octaves of more than 5 dB is "boxy"; more than half the energy at 80-315 Hz is "muddy" (not for
    wind, sea and thunder, whose weight is down there); over a quarter at 2-5 kHz, or energy above
    8 kHz over -20 dB, is "harsh"; under 1/300 below 200 Hz is "thin" (beds and music)."""
    e = 10 ** (np.asarray(bands) / 10)

    def share(lo, hi):
        return 10 * np.log10(e[(BANDS >= lo) & (BANDS <= hi)].sum() + 1e-12)

    def level(lo, hi):
        s_ = (BANDS >= lo) & (BANDS <= hi)
        return 10 * np.log10(e[s_].mean() + 1e-12)

    boxy = level(250, 630) - max(level(100, 200), level(800, 1600))
    vals = dict(boxy_bump=round(float(boxy), 1), low_mid=round(float(share(80, 315)), 1),
                presence=round(float(share(2000, 5000)), 1), low_db=round(float(share(0, 200)), 1))
    flags = []
    broad = kind in ("bed", "loop")
    if vals["presence"] > -6:
        flags.append("harsh")
    if boxy > 5 and broad:
        flags.append("boxy")
    if vals["low_mid"] > -3 and kind in ("bed", "loop", "music"):
        flags.append("muddy")
    if kind in ("bed", "music") and vals["low_db"] < -25:
        flags.append("thin")
    return vals, flags


def balance(x, kind):
    bands, _, over8k, centroid = spectrum(x)
    oct_ = np.log2(BANDS / 1000.0)
    sel = (BANDS >= 500) & (bands > -60)
    tilt = float(np.polyfit(oct_[sel], bands[sel], 1)[0]) if sel.sum() >= 3 else 0.0
    hf = 10 * np.log10(over8k + 1e-12)
    vals, flags = tonal_flags(bands, kind)
    if hf > -20 and "harsh" not in flags:
        flags.append("harsh")
    vals.update(tilt=round(tilt, 1), hf_db=round(hf, 1), centroid=round(centroid),
                bands=[round(float(v), 1) for v in bands])
    return vals, flags


def stereo(x):
    if x.ndim == 1 or x.shape[1] == 1:
        return {}, []
    l, r = x[:, 0], x[:, 1]
    corr = float(np.corrcoef(l, r)[0, 1]) if np.std(l) > 0 and np.std(r) > 0 else 1.0
    mid, side = (l + r) / 2, (l - r) / 2
    width = 10 * np.log10((np.sum(side**2) + 1e-30) / (np.sum(mid**2) + 1e-30))
    # Folded to mono at equal power, what cancels: 0 dB for uncorrelated or identical channels'
    # power sum, negative when the channels oppose each other.
    mono = 10 * np.log10(np.sum((l + r) ** 2) / (np.sum(l**2) + np.sum(r**2) + 1e-30) + 1e-30)
    flags = []
    if corr < 0:
        flags.append("anti-phase")
    if mono < -1.5:
        flags.append("mono loss")
    return dict(corr=round(corr, 2), width_db=round(width, 1), mono_loss=round(mono, 1)), flags


def seam(x):
    """Sample jump against the file's own 99.9th percentile, 50 ms level step against the
    largest step inside, and the log-spectral distance across the seam against interior points."""
    xs = x if x.ndim == 2 else x[:, None]
    jumps = np.abs(np.diff(xs, axis=0)).max(axis=1)
    jump = float(np.abs(xs[0] - xs[-1]).max() / max(np.percentile(jumps, 99.9), 1e-6))
    w = int(0.05 * SR)
    blocks = np.sum(xs[: len(xs) // w * w] ** 2, axis=1).reshape(-1, w).mean(axis=1) + 1e-12
    lv = 10 * np.log10(blocks)
    inner = np.abs(np.diff(lv))
    step = abs(lv[0] - lv[-1])
    step_pct = float((inner < step).mean() * 100)
    m = xs.mean(axis=1)
    n = 2048
    win = np.hanning(n)

    def lsd(at):
        a = np.abs(np.fft.rfft(np.take(m, range(at - n, at), mode="wrap") * win)) + 1e-9
        b = np.abs(np.fft.rfft(np.take(m, range(at, at + n), mode="wrap") * win)) + 1e-9
        return float(np.sqrt(np.mean((20 * np.log10(a / b)) ** 2)))

    rng = np.random.default_rng(1)
    inner = [lsd(int(a)) for a in rng.integers(n, len(m) - n, 120)]
    spec = lsd(0)
    pct = float((np.array(inner) < spec).mean() * 100)
    flags = []
    if jump > 1.0:
        flags.append("seam jump")
    if step_pct > 99.5 and step > 3.0:
        flags.append("seam step")
    # Vorbis at q0 smears its first and last frames a little; only a seam well beyond the
    # file's own frame-to-frame change is flagged.
    if spec > np.percentile(inner, 98) + 3.0:
        flags.append("seam spectrum")
    return dict(seam_jump=round(jump, 2), seam_step_db=round(step, 1), seam_step_pct=round(step_pct),
                seam_spec_pct=round(pct), seam_lsd=round(spec, 1),
                seam_lsd_p98=round(float(np.percentile(inner, 98)), 1)), flags


def repetition(x):
    """Largest normalised cross-correlation between any two 2 s windows at least 0.5 s apart
    (mono, 11 kHz, wrapping): above 0.9 means the file repeats itself inside; the audible period
    is then that lag, else the file's length."""
    m = signal.resample_poly(x.mean(axis=1) if x.ndim == 2 else x, 1, 4)
    sr = SR // 4
    n, w = len(m), 2 * sr
    if n < 3 * w:
        return dict(rep_ncc=0.0, period_s=round(len(x) / SR, 2))
    ext = np.concatenate([m, m[:w]])
    c2 = np.concatenate([[0.0], np.cumsum(ext**2)])
    energy = np.sqrt(np.maximum(c2[w:w + n] - c2[:n], 1e-20))
    spec = np.fft.rfft(m)
    best, lag_best = 0.0, 0
    floor = 1e-3 * np.median(energy) + 1e-12  # windows near silence carry no evidence
    for s in range(0, n - w, sr):
        if energy[s] < floor:
            continue
        seg = np.zeros(n)
        seg[:w] = m[s:s + w]
        corr = np.fft.irfft(np.conj(np.fft.rfft(seg)) * spec, n)
        ncc = corr / (energy * np.sqrt(np.sum(m[s:s + w] ** 2)) + 1e-20)
        d = (np.arange(n) - s) % n
        d = np.minimum(d, n - d)
        ncc[d < sr // 2] = 0
        ncc[energy < floor] = 0
        k = int(np.argmax(ncc))
        if ncc[k] > best:
            best, lag_best = float(ncc[k]), int(d[k])
    period = lag_best / sr if best > 0.9 else len(x) / SR
    return dict(rep_ncc=round(best, 2), period_s=round(period, 2))


def edges(x):
    xs = x if x.ndim == 2 else x[:, None]
    peak = np.abs(xs).max() + 1e-12
    edge = float(max(np.abs(xs[0]).max(), np.abs(xs[-1]).max()))
    w = min(int(0.05 * SR), len(xs) // 2)
    m = np.sum(xs**2, axis=1)
    c = np.concatenate([[0.0], np.cumsum(m)])
    rms = (c[w:] - c[:-w]) / w
    floor = 10 * np.log10(rms.min() + 1e-14)
    head = 10 * np.log10(np.mean(m[: int(0.001 * SR)]) / peak**2 + 1e-14)
    flags = []
    if edge > 2e-3:
        flags.append("edge click")
    return dict(edge=round(edge, 4), head_db=round(head, 1), floor_db=round(floor, 1)), flags


def load(path):
    """One file's samples: mono as a flat array (never (n, 1): it broadcasts against windows)."""
    x = mastering.decode(path)
    return x[:, 0].copy() if x.shape[1] == 1 else x


def measure(job):
    name, kind = job
    path = AUDIO / name
    x = load(path)
    loop = kind != "sfx"
    i, tp = ffmpeg_r128(path)
    row = dict(file=name, kind=kind, seconds=round(len(x) / SR, 3),
               channels=1 if x.ndim == 1 else x.shape[1], lufs=round(i, 1), tp=round(tp, 2),
               kb=round(path.stat().st_size / 1024))
    flags = []
    rng_, low = lra(x, loop)
    row.update(lra=round(rng_, 1), st_p10=round(low, 1))
    dc = float(np.abs(x.mean(axis=0)).max())
    row["dc"] = round(dc, 5)
    if dc > 1e-3:
        flags.append("DC")
    b, f = balance(x, kind)
    row.update(b)
    flags += f
    s, f = stereo(x)
    row.update(s)
    flags += f
    if kind == "sfx":
        row["loud100"] = round(mastering.max_short_lufs(x), 1)
        e, f = edges(x)
        row.update(e)
        flags += f
        if tp > -3.0:
            flags.append("peak")
    else:
        sm, f = seam(x)
        row.update(sm)
        flags += f
        if kind != "stem":
            row.update(repetition(x) if kind != "music" else
                       dict(rep_ncc=None, period_s=row["seconds"]))
        if tp > -1.0:
            flags.append("peak")
        if kind == "bed" and row["lra"] < 1.5:
            flags.append("static")
        if kind in ("bed", "loop") and row.get("period_s", 99) < 20 and row.get("rep_ncc", 0) > 0.9:
            flags.append("repeats inside")
    row["flags"] = flags
    return row


# -- music ---------------------------------------------------------------------------------

def pitch_cents(x):
    """Fundamental of a plucked note (strongest low partial with harmonic support) as MIDI."""
    a = int(0.02 * SR)
    seg = np.ravel(x)[a:a + int(0.5 * SR)]
    seg = seg * np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(seg, 1 << 18))
    f = np.fft.rfftfreq(1 << 18, 1 / SR)
    cand = (f > 100) & (f < 1500)
    hps = spec.copy()
    for h in (2, 3):
        hps[: len(hps) // h] *= spec[::h][: len(hps) // h]
    k = int(np.argmax(np.where(cand, hps, 0)))
    # parabolic refinement
    y0, y1, y2 = np.log(spec[k - 1:k + 2] + 1e-12)
    k = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    hz = k * SR / (1 << 18)
    return 69 + 12 * np.log2(hz / 440.0)


PROFILE_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])


def chroma(x):
    m = x.mean(axis=1) if x.ndim == 2 else x
    f, _, z = signal.stft(m, SR, nperseg=8192)
    p = np.mean(np.abs(z) ** 2, axis=1)
    sel = (f > 60) & (f < 2500)
    midi = 69 + 12 * np.log2(f[sel] / 440.0)
    c = np.zeros(12)
    np.add.at(c, np.round(midi).astype(int) % 12, p[sel])
    cents = (midi - np.round(midi)) * 100
    tuning = float(np.average(cents, weights=p[sel]))
    return c / c.sum(), tuning


def true_peak(x, block=1 << 18):
    """4x-oversampled peak in blocks (with a margin for the filter), so long files stay small."""
    pad = 64
    best = 0.0
    for i in range(0, len(x), block):
        seg = x[max(0, i - pad): i + block + pad]
        best = max(best, float(np.abs(signal.resample_poly(seg, 4, 1, axis=0)).max()))
    return 20 * np.log10(best + 1e-20)


def music_checks(manifests):
    out = {}
    cat = json.loads((ROOT / "assets/catalog.json").read_text())["audio"]
    names = ["pad", "keys", "melody", "bass", "colour"]
    for piece in ("day", "night"):
        # One stem decoded at a time, summed as it comes (never all five alive at once).
        lens, total, base = {}, None, None
        for st in names:
            y = mastering.decode(AUDIO / f"music/{piece}_{st}.ogg")
            lens[st] = len(y)
            total = y.copy() if total is None else total + y
            if st in ("pad", "keys"):
                base = y.copy() if base is None else base + y
            del y
        mix = mastering.decode(AUDIO / f"music/{piece}.ogg")
        lens["mix"] = len(mix)
        peak_blocks = np.abs(total[: len(total) // 441 * 441]).reshape(-1, 441, 2).max(axis=(1, 2))
        dwell = float((20 * np.log10(peak_blocks + 1e-9) > 20 * np.log10(peak_blocks.max()) - 1)
                      .mean() * 100)
        r, _ = lra(total, True)
        out[piece] = dict(lengths=lens, bars=len(mix) / 147000,
                          bar_aligned=all(n % 147000 == 0 for n in lens.values()),
                          all_stems_lufs=round(mastering.integrated_lufs(total), 2),
                          all_stems_tp=round(true_peak(total), 2),
                          all_stems_sample_peak=round(mastering.sample_peak_db(total), 2),
                          all_stems_lra=round(r, 1),
                          plr=round(true_peak(total) - mastering.integrated_lufs(total), 1),
                          near_peak_share_pct=round(dwell, 2),
                          mix_lufs=round(mastering.integrated_lufs(mix), 2),
                          base_lufs=round(mastering.integrated_lufs(base), 2))
        c, tuning = chroma(mix)
        keys = [float(np.dot(np.roll(PROFILE_MAJOR, k), c)) for k in range(12)]
        out[piece]["key_major"] = "C C# D D# E F F# G G# A A# B".split()[int(np.argmax(keys))]
        out[piece]["scale_classes"] = sorted(int(k) for k in np.argsort(c)[-7:])
        out[piece]["tuning_cents"] = round(tuning, 1)
    d, n = out["day"], out["night"]
    out["day_night"] = dict(mix_diff=round(d["mix_lufs"] - n["mix_lufs"], 2),
                            base_diff=round(d["base_lufs"] - n["base_lufs"], 2),
                            all_diff=round(d["all_stems_lufs"] - n["all_stems_lufs"], 2))
    notes = []
    for f in cat["notes"]:
        mm = pitch_cents(load(AUDIO / f))
        notes.append(dict(file=f, midi=round(float(mm), 2), cents=round(float(mm - round(mm)) * 100, 1),
                          pc=int(round(mm)) % 12,
                          in_day=int(round(mm)) % 12 in d["scale_classes"],
                          in_night=int(round(mm)) % 12 in n["scale_classes"]))
    out["notes"] = notes
    regional = []
    for m in manifests.values():
        if m["kind"] == "music" and "music" in m:
            info = m["music"]
            beats_per_bar = sum(info["meter"]) / len(info["meter"]) if info["meter"] else 4
            regional.append(dict(file=m["file"], samples=m["samples"], want=info["samples"],
                                 bars=info["bars"], beats=info["beats"],
                                 whole_beats=abs(info["beats"] * 60 / info["bpm"] * SR
                                                 - m["samples"]) < 2,
                                 beats_per_bar=beats_per_bar))
    out["regional"] = regional
    return out


def load_manifests():
    out = {}
    for f in sorted(AUDIO.glob("*/manifest.json")):
        for e in json.loads(f.read_text())["files"]:
            out[e["file"]] = e
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--compare", type=Path)
    ap.add_argument("--md", type=Path)
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("filters", nargs="*")
    a = ap.parse_args()
    manifests = load_manifests()
    files = sorted(p.relative_to(AUDIO).as_posix() for p in AUDIO.rglob("*")
                   if p.suffix in (".ogg", ".wav"))
    files = [f for f in files if not a.filters or any(x in f for x in a.filters)]
    # Resumable: one row per file appended to OUT.rows.jsonl as it finishes; files already
    # there are skipped. One file per task, and a fresh worker every few files.
    part = a.out.with_suffix(".rows.jsonl")
    part.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if part.exists():
        for line in part.read_text().splitlines():
            r = json.loads(line)
            done[r["file"]] = r
    todo = [(f, kind_of(f, manifests)) for f in files if f not in done]
    if todo:
        with ProcessPoolExecutor(WORKERS, max_tasks_per_child=8) as pool, part.open("a") as out:
            for r in pool.map(measure, todo):
                out.write(json.dumps(r) + "\n")
                out.flush()
                done[r["file"]] = r
    rows = [done[f] for f in files if f in done]
    tonal = {"harsh", "boxy", "muddy", "thin"}
    for r in rows:  # tonal flags follow the current rules, from the stored band levels
        vals, flags = tonal_flags(r["bands"], r["kind"])
        if r["hf_db"] > -20 and "harsh" not in flags:
            flags.append("harsh")
        r.update(vals)
        r["flags"] = [f for f in r["flags"] if f not in tonal] + flags
    doc = {"files": rows}
    if not a.no_music and not a.filters:
        doc["music"] = music_checks(manifests)
    doc["size_kb"] = round(sum(p.stat().st_size for p in AUDIO.rglob("*") if p.is_file()) / 1024)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, indent=1))
    old = {r["file"]: r for r in json.loads(a.compare.read_text())["files"]} if a.compare else {}
    if a.md:
        a.md.write_text(table(rows, old))
    flagged = [r for r in rows if r["flags"]]
    print(f"{len(rows)} files, {len(flagged)} flagged, {doc['size_kb'] / 1024:.1f} MB")
    for r in flagged:
        print(f"  {r['file']:44s} {', '.join(r['flags'])}")


COLS = [("lufs", "I/L100"), ("tp", "TP"), ("lra", "LRA"), ("tilt", "tilt"),
        ("presence", "2-5k"), ("width_db", "S/M"), ("mono_loss", "mono"), ("period_s", "period"),
        ("seam_jump", "jump")]


def table(rows, old):
    lines = ["| file | kind | s | " + " | ".join(c for _, c in COLS) + " | flags |",
             "|---|---|---|" + "---|" * len(COLS) + "---|"]
    for r in rows:
        vals = []
        for k, _ in COLS:
            v = r.get("loud100") if (k == "lufs" and r["kind"] == "sfx") else r.get(k)
            o = old.get(r["file"], {})
            ov = o.get("loud100") if (k == "lufs" and r["kind"] == "sfx") else o.get(k)
            cell = "" if v is None else f"{v}"
            if o and ov is not None and v is not None and ov != v:
                cell = f"{ov} → {v}"
            vals.append(cell)
        oflags = old.get(r["file"], {}).get("flags")
        fl = ", ".join(r["flags"])
        if oflags is not None and oflags != r["flags"]:
            fl = f"{', '.join(oflags) or '–'} → {fl or 'ok'}"
        lines.append(f"| `{r['file']}` | {r['kind']} | {r['seconds']} | " + " | ".join(vals)
                     + f" | {fl} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
