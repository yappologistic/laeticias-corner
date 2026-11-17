"""Signal-processing building blocks shared by every generator: envelopes, filters,
noise, panning, reverb and loop helpers. Signals are float64 numpy arrays at SR;
stereo signals have shape (n, 2)."""

import numpy as np
from scipy import signal

SR = 44100


def secs(n_or_s):
    """Seconds -> sample count."""
    return int(round(n_or_s * SR))


def times(n):
    return np.arange(n) / SR


def midi_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


# --- envelopes -------------------------------------------------------------------------


def ramp_in(n, length):
    """Raised-cosine fade-in curve of `length` samples, padded with ones to n."""
    out = np.ones(n)
    k = min(n, max(1, length))
    out[:k] = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    return out


def fade(x, fade_in, fade_out):
    """Apply raised-cosine fades (seconds) to the ends of x (mono or stereo)."""
    n = len(x)
    g = ramp_in(n, secs(fade_in)) * ramp_in(n, secs(fade_out))[::-1]
    return x * (g if x.ndim == 1 else g[:, None])


def adsr(n, attack, decay, sustain, release_at, release):
    """Classic envelope; times in seconds, release starts at `release_at`."""
    t = times(n)
    env = np.where(
        t < attack,
        0.5 - 0.5 * np.cos(np.pi * t / max(attack, 1e-6)),
        sustain + (1 - sustain) * np.exp(-(t - attack) / max(decay, 1e-6)),
    )
    rel = np.clip(t - release_at, 0, None)
    return env * np.exp(-rel / max(release, 1e-6)) * ramp_in(n, 8)[::-1]


def perc(n, attack, decay):
    """Fast attack, exponential decay (time constant `decay` seconds)."""
    t = times(n)
    return ramp_in(n, secs(attack)) * np.exp(-t / decay)


# --- oscillators -----------------------------------------------------------------------


def phase_of(freq):
    """Integrate an instantaneous-frequency curve (Hz per sample) into phase."""
    return 2 * np.pi * np.cumsum(freq) / SR


def glide(n, points):
    """Piecewise-exponential curve through (time_s, value) points, sampled n times."""
    pts = np.array(points, dtype=float)
    return np.exp(np.interp(times(n), pts[:, 0], np.log(pts[:, 1])))


def line(n, points):
    """Piecewise-linear curve through (time_s, value) points, sampled n times."""
    pts = np.array(points, dtype=float)
    return np.interp(times(n), pts[:, 0], pts[:, 1])


def voiced(f0, formants, n_harm=40):
    """Band-limited harmonic source shaped by formants (source-filter by additive
    synthesis, so pitch glides never alias). f0 is a per-sample curve; formants is
    a list of (centre_hz, bandwidth_hz, gain) with scalars or per-sample curves."""
    ph = phase_of(f0)
    out = np.zeros(len(f0))
    for k in range(1, n_harm + 1):
        fk = k * f0
        if fk.min() > 9000:
            break
        amp = np.zeros(len(f0))
        for centre, bw, gain in formants:
            amp += gain / (1 + ((fk - centre) / (0.5 * bw)) ** 2)
        amp *= fk < 9000
        out += amp * np.sin(k * ph)
    return out


# --- filters ---------------------------------------------------------------------------


def butter(x, kind, freq, order=2):
    sos = signal.butter(order, freq, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def lowpass(x, freq, order=2):
    return butter(x, "lowpass", freq, order)


def highpass(x, freq, order=2):
    return butter(x, "highpass", freq, order)


def bandpass(x, lo, hi, order=2):
    return butter(x, "bandpass", [lo, hi], order)


def resonator(x, freq, q):
    """Second-order peaking band-pass (constant 0 dB peak gain)."""
    b, a = signal.iirpeak(freq, q, fs=SR)
    return signal.lfilter(b, a, x, axis=0)


def sweep_lowpass(x, cutoff, block=128):
    """Two cascaded one-pole low-passes following a per-sample cutoff curve (mono)."""
    out = np.empty_like(x)
    last = [0.0, 0.0]
    for i in range(0, len(x), block):
        a = np.exp(-2 * np.pi * float(cutoff[i]) / SR)
        seg = x[i : i + block]
        for stage in range(2):
            seg, _ = signal.lfilter([1 - a], [1, -a], seg, zi=[a * last[stage]])
            last[stage] = seg[-1]
        out[i : i + block] = seg
    return out


def circular(fn, x):
    """Run a causal filter on a loop as if it had been playing forever: filter two
    periods and keep the second, so the filter state at the seam is continuous."""
    n = len(x)
    return fn(np.concatenate([x, x]))[n:]


# --- noise -----------------------------------------------------------------------------


def shaped_noise(n, rng, gain_of_freq, channels=1):
    """Noise of exactly n samples whose spectrum follows gain_of_freq(f). Built in the
    frequency domain, so it is perfectly periodic: ideal for seamless loops."""
    f = np.fft.rfftfreq(n, 1 / SR)
    g = gain_of_freq(np.maximum(f, 1.0))
    g[0] = 0
    out = []
    for _ in range(channels):
        spec = (rng.standard_normal(len(f)) + 1j * rng.standard_normal(len(f))) * g
        x = np.fft.irfft(spec, n)
        out.append(x / (np.std(x) + 1e-12))
    return out[0] if channels == 1 else np.stack(out, axis=1)


def smooth_random(n, rng, cutoff_hz):
    """Periodic slowly-wandering curve with zero mean and unit deviation."""
    return shaped_noise(n, rng, lambda f: np.exp(-((f / cutoff_hz) ** 2)))


# --- space -----------------------------------------------------------------------------


def pan(x, position):
    """Equal-power pan of a mono signal; position in [-1, 1]."""
    a = (np.clip(position, -1, 1) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def stereo(x):
    return x if x.ndim == 2 else np.stack([x, x], axis=1) * np.sqrt(0.5)


def impulse_response(rng, length, t60_low, t60_high, predelay=0.012, crossover=2500.0):
    """Stereo room impulse response: decorrelated noise whose decay time falls from
    t60_low (bass) to t60_high (treble), plus a few early reflections. Convolving with
    it gives a smooth, dense, colourless tail without per-sample loops."""
    n = secs(length)
    t = times(n)
    bands = [(None, 400.0), (400.0, crossover), (crossover, None)]
    t60s = [t60_low, 0.5 * (t60_low + t60_high), t60_high]
    ir = np.zeros((n, 2))
    for (lo, hi), t60 in zip(bands, t60s):
        noise = rng.standard_normal((n, 2))
        if lo is None:
            noise = lowpass(noise, hi, 4)
        elif hi is None:
            noise = highpass(noise, lo, 4)
        else:
            noise = bandpass(noise, lo, hi, 4)
        ir += noise * np.exp(-6.91 * t / t60)[:, None]
    ir = lowpass(ir, 7000.0, 2)
    ir *= ramp_in(n, secs(0.02))[:, None]
    pre = secs(predelay)
    ir = np.concatenate([np.zeros((pre, 2)), ir])[:n]
    for k in range(6):
        d = pre + secs(rng.uniform(0.004, 0.03))
        ir[d, :] += rng.uniform(0.3, 0.6) * rng.choice([-1, 1], 2) * (0.8 ** k)
    return ir / np.sqrt(np.sum(ir**2) / 2)


def reverb(x, ir):
    """Convolve (mono or stereo) x with a stereo IR; output is longer by len(ir) - 1."""
    x = stereo(x)
    return np.stack([signal.oaconvolve(x[:, c], ir[:, c]) for c in range(2)], axis=1)


def with_reverb(dry, send, ir, wet=1.0):
    """dry + wet * (send convolved with ir), keeping the whole tail for wrap()."""
    out = reverb(send, ir) * wet
    out[: len(dry)] += stereo(dry)
    return out


def wrap(x, n):
    """Fold everything past sample n back onto the start, as a loop would play it."""
    out = x[:n].copy()
    for i in range(n, len(x), n):
        seg = x[i : i + n]
        out[: len(seg)] += seg
    return out


def place(buf, x, at):
    """Mix x into buf starting at sample `at` (buf is long enough or x is clipped)."""
    end = min(len(buf), at + len(x))
    if end > at:
        buf[at:end] += x[: end - at]


def softclip(x, drive=1.0):
    return np.tanh(drive * x) / np.tanh(drive)
