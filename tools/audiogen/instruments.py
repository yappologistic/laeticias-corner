"""Pitched voices for the music and the chime: felt piano, music-box tine, warm pad and
sub bass. Each returns a mono (or stereo, for the pad) note rendered from scratch."""

import numpy as np

from dsp import adsr, lowpass, perc, ramp_in, secs, times

NYQUIST_GUARD = 9000.0  # keep partials below this: nothing glassy or harsh up top
TINE_CEILING = 7000.0  # bar modes ring longest, so they get a lower ceiling


def felt_piano(freq, dur, vel, rng, release=0.35):
    """Soft felt-hammer piano: slightly inharmonic partials, two detuned strings per
    note, two-stage decay, brightness rising with velocity, damper on note-off."""
    n = secs(dur + release + 0.05)
    t = times(n)
    inharm = 0.00025 * (freq / 261.6) ** 0.8
    t_main = 4.5 * (261.6 / freq) ** 0.6
    bright = 1200 + 3200 * vel
    out = np.zeros(n)
    for k in range(1, 16):
        fk = k * freq * np.sqrt(1 + inharm * k * k)
        if fk > NYQUIST_GUARD:
            break
        amp = k**-1.1 / (1 + (fk / bright) ** 2)
        tau = t_main / (1 + 0.45 * (k - 1))
        env = 0.6 * np.exp(-t / (0.12 * tau + 0.05)) + 0.4 * np.exp(-t / tau)
        for detune in (-0.12, 0.12):
            ph = rng.uniform(0, 2 * np.pi)
            out += 0.5 * amp * env * np.sin(2 * np.pi * (fk + detune * k**0.5) * t + ph)
    thump = lowpass(rng.standard_normal(n) * perc(n, 0.001, 0.012), 300 + 200 * vel)
    out = out * ramp_in(n, secs(0.006)) + 0.6 * thump
    damper = np.exp(-np.clip(t - dur, 0, None) / (release / 4))
    return out * damper * ramp_in(n, secs(0.01))[::-1] * vel


def tine(freq, dur, vel, rng):
    """Music-box / kalimba tine: a clamped bar's inharmonic modes (1, 6.27, 17.55)
    with fast-decaying upper modes, a little second harmonic for warmth, and a soft
    mallet tick. `dur` only bounds the ring time."""
    n = secs(dur)
    t = times(n)
    t_main = 2.2 * (440 / freq) ** 0.4
    soft_top = 1 / (1 + (freq / 1200) ** 2)  # high notes keep only a faint shimmer
    modes = [(1.0, 1.0, t_main), (2.0, 0.14, t_main * 0.5), (3.0, 0.04, t_main * 0.3),
             (6.27, 0.22 * vel * soft_top, t_main / 9), (17.55, 0.05 * vel * soft_top, t_main / 30)]
    out = np.zeros(n)
    for ratio, amp, tau in modes:
        fk = freq * ratio
        if fk > TINE_CEILING:
            continue
        ph = rng.uniform(0, 2 * np.pi)
        out += amp * np.exp(-t / tau) * (np.sin(2 * np.pi * fk * t + ph)
                                         + 0.3 * np.sin(2 * np.pi * (fk + 0.7) * t))
    tick = lowpass(rng.standard_normal(n) * perc(n, 0.0005, 0.004), 2500)
    out = out * ramp_in(n, secs(0.002)) + 0.15 * vel * tick
    return out * ramp_in(n, secs(0.4))[::-1] * vel


def pad(freq, dur, vel, rng, attack=1.2, release=2.0, cutoff=2200.0):
    """Warm additive pad: soft-rolled harmonics, three slowly beating voices spread
    across the stereo field, long attack and release. Returns stereo."""
    n = secs(dur + release)
    t = times(n)
    out = np.zeros((n, 2))
    for k in range(1, 12):
        fk = k * freq
        if fk > cutoff * 2:
            break
        amp = k**-1.5 / (1 + (fk / cutoff) ** 4)
        for detune, (gl, gr) in ((-0.004, (0.9, 0.3)), (0.0, (0.6, 0.6)), (0.004, (0.3, 0.9))):
            ph = rng.uniform(0, 2 * np.pi)
            wob = 1 + 0.15 * np.sin(2 * np.pi * rng.uniform(0.05, 0.2) * t + ph)
            s = amp * wob * np.sin(2 * np.pi * fk * (1 + detune) * t + ph)
            out[:, 0] += gl * s
            out[:, 1] += gr * s
    env = adsr(n, attack, 1.5, 0.8, dur, release / 3)
    return out * env[:, None] * vel


def sub_bass(freq, dur, vel, release=0.4):
    """Round, felt-like bass: sine plus a touch of 2nd and 3rd harmonic."""
    n = secs(dur + release)
    t = times(n)
    ph = 2 * np.pi * freq * t
    tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    env = adsr(n, 0.02, 1.2, 0.55, dur, release / 3)
    return tone * env * vel
