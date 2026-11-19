"""Loudness measurement (ITU-R BS.1770-4 / EBU R128), true-peak limiting, and file
writing. Used both to master renders and by the validator, which cross-checks
against ffmpeg's own meter."""

import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d, uniform_filter1d

from dsp import SR


def _k_weighting(fs):
    """K-weighting biquads for any sample rate (libebur128's analog-matched design)."""
    f0, gain, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = np.tan(np.pi * f0 / fs)
    vh = 10 ** (gain / 20)
    vb = vh**0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf_b = [(vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0]
    shelf_a = [1, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]
    f0, q = 38.13547087602444, 0.5003270373238773
    k = np.tan(np.pi * f0 / fs)
    a0 = 1 + k / q + k * k
    hp_a = [1, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]
    return (shelf_b, shelf_a), ([1, -2, 1], hp_a)


def _k_filter(x):
    x = x if x.ndim == 2 else x[:, None]
    for b, a in _k_weighting(SR):
        x = signal.lfilter(b, a, x, axis=0)
    return x


def integrated_lufs(x):
    """Gated integrated loudness. Mono counts as a single channel, like ffmpeg ebur128."""
    x = np.asarray(x, dtype=np.float64)  # float64 sums over long files
    x = x if x.ndim == 2 else x[:, None]
    block, step = int(0.4 * SR), int(0.1 * SR)
    starts = np.arange(0, max(len(x), block) - block + 1, step)
    z = 0.0
    for c in range(x.shape[1]):  # a channel at a time: the same sums, half the memory
        y = _k_filter(x[:, c])[:, 0]
        y *= y
        if len(y) < block:
            y = np.concatenate([y, np.zeros(block - len(y))])
        csum = np.concatenate([[0.0], np.cumsum(y)])
        del y
        z = z + (csum[starts + block] - csum[starts]) / block
    lk = -0.691 + 10 * np.log10(z + 1e-20)
    z = z[lk > -70]
    if len(z) == 0:
        return -np.inf
    rel = -0.691 + 10 * np.log10(z.mean()) - 10
    z = z[-0.691 + 10 * np.log10(z) > rel]
    return float(-0.691 + 10 * np.log10(z.mean()))


def max_short_lufs(x, window=0.1):
    """Loudest `window`-long stretch, K-weighted: a fair loudness figure for effects
    far shorter than the 400 ms blocks of integrated loudness."""
    y = _k_filter(x) ** 2
    w = max(1, int(window * SR))
    ms = uniform_filter1d(y.sum(axis=1), w, mode="constant")
    return float(-0.691 + 10 * np.log10(ms.max() + 1e-20))


def true_peak_db(x, block=1 << 17):
    """4x-oversampled peak, a block at a time so a long file never holds its oversampled copy:
    each block is filtered with a margin wider than the polyphase filter and only its centre
    is kept, so the result equals filtering the whole file at once."""
    pad = 256
    best = 0.0
    for i in range(0, len(x), block):
        a = max(0, i - pad)
        up = signal.resample_poly(x[a:i + block + pad], 4, 1, axis=0)
        lo = 4 * (i - a)
        best = max(best, float(np.max(np.abs(up[lo:lo + 4 * min(block, len(x) - i)]))))
    return float(20 * np.log10(best + 1e-20))


def sample_peak_db(x):
    return float(20 * np.log10(np.max(np.abs(x)) + 1e-20))


def oversampled_peaks(x2, block=1 << 17):
    """Per-sample peak of the 4x-oversampled signal (largest of the four sub-samples, over
    channels), a block at a time with a margin wider than the filter: equal to filtering the
    whole file at once, without holding its oversampled copy."""
    pad = 256
    peak = np.empty(len(x2))
    for i in range(0, len(x2), block):
        a = max(0, i - pad)
        m = min(block, len(x2) - i)
        up = np.abs(signal.resample_poly(x2[a:i + block + pad], 4, 1, axis=0)).max(axis=1)
        lo = 4 * (i - a)
        peak[i:i + m] = up[lo:lo + 4 * m].reshape(m, 4).max(axis=1)
    return peak


def limit(x, ceiling_db, loop):
    """Look-ahead peak limiter on the 4x-oversampled envelope. With loop=True the gain
    curve is computed circularly so the seam stays seamless. Returns the limited signal
    and the per-sample gain it applied."""
    ceiling = 10 ** (ceiling_db / 20)
    mode = "wrap" if loop else "nearest"
    total = np.ones(len(x))
    for _ in range(4):
        peak = oversampled_peaks(x if x.ndim == 2 else x[:, None])
        need = np.minimum(1.0, ceiling / np.maximum(peak, 1e-12))
        if need.min() >= 1.0:
            break
        hold = int(0.02 * SR)
        gain = minimum_filter1d(need, 2 * hold + 1, mode=mode)
        gain = uniform_filter1d(gain, hold + 1, mode=mode)
        x = x * (gain if x.ndim == 1 else gain[:, None]) * 0.999
        total *= gain * 0.999
    return x, total


def master_loop(x, target_lufs, ceiling_db=-1.5):
    """Normalise a loop to the target integrated loudness under a true-peak ceiling.
    Returns the mastered loop and the per-sample gain applied, so stems of the same
    session can be given exactly the same treatment."""
    total = np.ones(len(x))
    for _ in range(3):
        k = 10 ** ((target_lufs - integrated_lufs(x)) / 20)
        x = x * k
        x, gain = limit(x, ceiling_db, loop=True)
        total *= k * gain
    return x, total


def master_sfx(x, target_short_lufs, ceiling_db=-4.0):
    """Normalise an effect by its loudest 100 ms, then cap its peak."""
    x = x - np.mean(x)
    x = x * 10 ** ((target_short_lufs - max_short_lufs(x)) / 20)
    peak = true_peak_db(x)
    if peak > ceiling_db:
        x = x * 10 ** ((ceiling_db - peak) / 20)
    return x


def write_wav16(path, x):
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype(np.int16)
    wavfile.write(path, SR, pcm)


def write_ogg(path, x, quality):
    """Encode stereo float audio as Ogg Vorbis. Bit-exact flags keep the output
    reproducible (no random stream serials, no encoder version tags)."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "in.wav"
        wavfile.write(wav, SR, x.astype(np.float32))
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(wav),
             "-c:a", "libvorbis", "-q:a", str(quality),
             "-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1",
             str(path)],
            check=True,
        )


def decode(path):
    """Decode any audio file to float64 (n, channels) with ffmpeg."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=channels", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    channels = int(probe.stdout.strip())
    raw = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "f64le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float64).reshape(-1, channels)
