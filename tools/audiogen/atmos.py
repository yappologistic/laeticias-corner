"""Helpers for the atmosphere sets (weather, nature, people): seamless event trains rendered
by circular convolution, oscillators whose phase closes over the loop, wind and gust curves
shared by every intensity family, and the entry table format of the new files."""

import numpy as np
from scipy import signal

import sounds as sd
from dsp import SR, bandpass, circular, secs, smooth_random, times, wrap

CEILING = 7500.0  # nothing above this: weather is soft and wide, never hissy


def train(n, rng, rate, sigma=0.5):
    """Periodic random impulses: Poisson events whose rate per second follows `rate`
    (scalar or per-sample curve), each with a log-normal size. Mono, length n."""
    rate = np.broadcast_to(np.asarray(rate, dtype=float), (n,))
    hits = rng.random(n) < rate / SR
    return hits * rng.lognormal(0, sigma, n)


def conv(x, kernel, n=None):
    """Circular convolution: kernel tails past the end fold onto the start (seamless)."""
    n = n or len(x)
    if x.ndim == 1:
        return wrap(signal.oaconvolve(x, kernel), n)
    return np.stack([wrap(signal.oaconvolve(x[:, c], kernel), n) for c in range(x.shape[1])], 1)


def kernels(make, count, rng):
    """`count` variants of a short sound, so trains of the same event never sound mechanical."""
    return [make(rng) for _ in range(count)]


def scatter_train(n, rng, rate, ks, sigma=0.5, channels=2, spread=0.8):
    """Events from several kernel variants at a total rate, each variant its own train,
    spread across the stereo field (independent left/right trains plus a centre one)."""
    out = np.zeros((n, channels))
    per = np.asarray(rate, dtype=float) / len(ks)
    for k in ks:
        if channels == 1:
            out[:, 0] += conv(train(n, rng, per, sigma), k)
            continue
        left, right, mid = (train(n, rng, per * w, sigma) for w in (0.5 * spread, 0.5 * spread,
                                                                     1 - spread))
        out[:, 0] += conv(left + 0.7 * mid, k)
        out[:, 1] += conv(right + 0.7 * mid, k)
    return out


def loop_tone(freq, rng=None):
    """Phase of an oscillator following the per-sample frequency curve `freq`, nudged so
    that it closes on a whole number of cycles over the loop (no click at the seam)."""
    total = np.sum(freq) / SR
    k = max(1, round(total))
    ph = 2 * np.pi * np.cumsum(freq * (k / total)) / SR
    return ph + (rng.uniform(0, 2 * np.pi) if rng is not None else 0.0)


slow = smooth_random  # periodic slow curves (dsp: on the true frequencies)
swell = sd.swell  # a periodic slow level curve around 1 (showers thickening, waves of cicadas)


def gusts(n, rng, rate, depth, floor=0.12, flutter=0.0):
    """A periodic gust curve around 1 shared by a wind's bands: slow surges with quicker
    gusts riding on them (log-normal, so it never drops to nothing); `flutter` adds the
    fast, small buffeting of strong wind."""
    g = np.exp(depth * (0.75 * slow(n, rng, rate) + 0.55 * slow(n, rng, rate * 4)))
    g /= np.mean(g)
    if flutter:
        g = g * (1 + flutter * slow(n, rng, rate * 25))
    return np.clip(g, floor, None)


def band(n, rng, lo, hi, tilt=0.5, channels=2):
    return sd.loop_noise(n, rng, lo, hi, tilt, channels)


def noise_burst(rng, dur, lo, hi, decay, attack=0.0005):
    """A short band-limited noise burst with an exponential decay (seconds)."""
    m = secs(dur)
    t = times(m)
    env = np.minimum(1, t / max(attack, 1e-5)) * np.exp(-t / decay)
    return bandpass(rng.standard_normal(m), lo, min(hi, CEILING)) * env


def resonant_burst(rng, dur, freq, q, decay, lo=60.0, hi=6000.0):
    """Noise through a resonance (a hollow knock, a slap of water in a hull)."""
    b, a = signal.iirpeak(freq, q, fs=SR)
    return signal.lfilter(b, a, noise_burst(rng, dur, lo, hi, decay))








def _biquad(kind, f, gain_db, q):
    """RBJ cookbook peaking or shelving biquad as one SOS row."""
    a_ = 10 ** (gain_db / 40)
    w = 2 * np.pi * f / SR
    cw, alpha = np.cos(w), np.sin(w) / (2 * q)
    if kind == "peak":
        b = [1 + alpha * a_, -2 * cw, 1 - alpha * a_]
        a = [1 + alpha / a_, -2 * cw, 1 - alpha / a_]
    else:  # "high" or "low" shelf, slope 1
        sq = 2 * np.sqrt(a_) * alpha
        sign = 1 if kind == "high" else -1
        b = [a_ * ((a_ + 1) + sign * (a_ - 1) * cw + sq), -2 * sign * a_ * ((a_ - 1) + sign * (a_ + 1) * cw),
             a_ * ((a_ + 1) + sign * (a_ - 1) * cw - sq)]
        a = [(a_ + 1) - sign * (a_ - 1) * cw + sq, 2 * sign * ((a_ - 1) - sign * (a_ + 1) * cw),
             (a_ + 1) - sign * (a_ - 1) * cw - sq]
    return np.concatenate([np.array(b) / a[0], np.array(a) / a[0]])


def eq(x, bands, loop=True):
    """Gentle tone shaping: `bands` of (kind, Hz, dB, q) with kind "peak", "high" or "low"
    (shelves); run circularly on loops so the seam stays continuous."""
    sos = np.array([_biquad(*b) for b in bands])
    if not loop:
        return signal.sosfilt(sos, x, axis=0)
    return circular(lambda y: signal.sosfilt(sos, y, axis=0), x)


# Broadband water (rain, surf, rapids) synthesised under the 6.5 kHz ceiling piles its energy
# into 2-5 kHz, where a long bed tires the ear: a wide presence dip puts it back near the
# share real recordings have (about a quarter of the energy).
WATER_EQ = (("peak", 3300.0, -4.0, 0.7),)


def tame(x, top, loop):
    """A steep (8th-order) low-pass over the finished sound, so nothing reaches the harsh
    band above 8 kHz, and a 20 Hz high-pass against the DC that bubbles and thuds carry;
    run circularly on loops so the seam stays continuous."""
    sos = np.concatenate([signal.butter(8, top, fs=SR, output="sos"),
                          signal.butter(2, 20.0, "highpass", fs=SR, output="sos")])
    if not loop:
        return signal.sosfilt(sos, x, axis=0)
    return circular(lambda y: signal.sosfilt(sos, y, axis=0), x)


def entry(kind, render, lufs, purpose, gain=1.0, when="always", where=None, quality=0,
          family=None, level=None, level_name=None, tags=(), top=6500.0):
    """One file of an atmosphere set: what the generator renders (through `tame` at `top`)
    and what the manifest says."""
    loop = kind != "sfx"
    e = dict(kind=kind, render=lambda rng: tame(render(rng), top, loop), lufs=lufs, gain=gain,
             when=when, purpose=purpose, tags=list(tags))
    if loop:
        e["quality"] = quality
    if where:
        e["where"] = where
    if family:
        e.update(family=family, level=level, level_name=level_name)
    return e
