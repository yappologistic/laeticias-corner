"""Pitched voices for the music and the chime: felt piano, music-box tine, warm pad and
sub bass. Each returns a mono (or stereo, for the pad) note rendered from scratch."""

import numpy as np

from dsp import adsr, bandpass, lowpass, perc, phase_of, ramp_in, secs, times

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


def wooden_flute(freq, dur, vel, rng, release=0.18):
    """Soft wooden flute: a nearly pure tone with a little 2nd and 3rd harmonic, a short
    breathy chiff and a small upward scoop on the attack, breath noise under the tone,
    and a gentle vibrato that only arrives once the note has settled."""
    n = secs(dur + release)
    t = times(n)
    vib = 0.004 * np.clip((t - 0.3) / 0.4, 0, 1) * np.sin(2 * np.pi * 4.8 * t + rng.uniform(0, 6.3))
    f = freq * (1 - 0.01 * np.exp(-t / 0.03)) * (1 + vib)
    ph = phase_of(f)
    tone = sum(a * np.sin(k * ph) for k, a in ((1, 1.0), (2, 0.28), (3, 0.1), (4, 0.03))
               if k * freq < NYQUIST_GUARD)
    breath = bandpass(rng.standard_normal(n), freq * 0.9, min(freq * 3.5, 6000))
    chiff = bandpass(rng.standard_normal(n), 1200, 3500) * perc(n, 0.004, 0.03)
    env = adsr(n, 0.07, 0.4, 0.8, dur, release / 3)
    return ((tone + 0.06 * breath) * env + 0.12 * chiff * env.max()) * vel


def shaker(vel, rng):
    """One brushed shaker stroke: beads swelling in and falling away, kept below 7 kHz."""
    n = secs(0.18)
    t = times(n)
    env = ramp_in(n, secs(0.025)) * np.exp(-np.clip(t - 0.025, 0, None) / 0.045)
    beads = 0.6 + 0.4 * np.abs(lowpass(rng.standard_normal(n), 400)) * 3
    x = bandpass(rng.standard_normal(n), 2200, 6000) * env * beads
    return lowpass(x, 7000, 4) * ramp_in(n, secs(0.02))[::-1] * vel


def cello_harmonic(freq, dur, vel, rng, release=1.2):
    """Bowed cello harmonic: an almost pure, glassy tone that swells in slowly, with a
    faint bow hiss around the pitch and a late, slow vibrato."""
    n = secs(dur + release)
    t = times(n)
    vib = 0.0025 * np.clip((t - 0.8) / 0.8, 0, 1) * np.sin(2 * np.pi * 4.6 * t
                                                           + rng.uniform(0, 6.3))
    ph = phase_of(freq * (1 + vib))
    tone = np.sin(ph) + 0.06 * np.sin(2 * ph) + 0.02 * np.sin(3 * ph)
    bow = bandpass(rng.standard_normal(n), freq * 0.85, freq * 1.2) * 0.05
    env = adsr(n, 0.7, 1.5, 0.85, dur, release / 3)
    return (tone + bow) * env * vel


def clarinet(freq, dur, vel, rng, release=0.2):
    """Low clarinet (chalumeau): odd harmonics strongest, rolled off softly so it stays
    woody rather than reedy, a breathy onset and a slight swell through the note."""
    n = secs(dur + release)
    t = times(n)
    ph = phase_of(np.full(n, freq))
    bright = 900 + 700 * vel
    tone = np.zeros(n)
    for k, a in ((1, 1.0), (2, 0.05), (3, 0.45), (4, 0.04), (5, 0.22), (6, 0.02), (7, 0.1),
                 (9, 0.04)):
        if k * freq < NYQUIST_GUARD:
            tone += a / (1 + (k * freq / bright) ** 2) * np.sin(k * ph)
    breath = bandpass(rng.standard_normal(n), 800, 3000) * perc(n, 0.01, 0.06)
    swell = 1 + 0.12 * np.clip(t / max(dur, 0.1), 0, 1)
    env = adsr(n, 0.06, 0.3, 0.8, dur, release / 3)
    return (tone * swell + 0.15 * breath) * env * vel


def harp(freq, dur, vel, rng):
    """Plucked harp string: near-harmonic partials whose upper members die away first,
    a soft finger-pluck noise, and a ring bounded by `dur`."""
    n = secs(dur)
    t = times(n)
    t_main = 1.8 * (440 / freq) ** 0.5
    out = np.zeros(n)
    for k in range(1, 12):
        fk = k * freq * (1 + 0.0004 * k * k)
        if fk > TINE_CEILING:
            break
        amp = k**-1.4 * np.sin(np.pi * k * 0.17) ** 2  # plucked a little off the string's end
        out += amp * np.exp(-t * (1 + 0.6 * (k - 1)) / t_main) * np.sin(2 * np.pi * fk * t
                                                                         + rng.uniform(0, 6.3))
    pluck = lowpass(rng.standard_normal(n) * perc(n, 0.0005, 0.003), 3000)
    return (out * ramp_in(n, secs(0.002)) + 0.08 * pluck) * ramp_in(n, secs(0.2))[::-1] * vel


def glass(freq, dur, vel, rng):
    """Glass shimmer: a pure tone and its octave, swelling in softly and beating gently
    against a detuned twin, like a rubbed glass rim."""
    n = secs(dur)
    t = times(n)
    out = np.zeros(n)
    for ratio, amp in ((1.0, 1.0), (2.0, 0.12)):
        for detune in (-0.6, 0.6):
            out += amp * np.sin(2 * np.pi * (freq * ratio + detune) * t + rng.uniform(0, 6.3))
    env = ramp_in(n, secs(0.08)) * np.exp(-t / (0.45 * dur)) * ramp_in(n, secs(0.3))[::-1]
    return 0.5 * out * env * vel


def bell(freq, dur, vel, rng):
    """Soft small bell: a handbell's partials (hum, prime, tierce, quint, nominal) with
    long low and short high decays, struck by a padded clapper."""
    n = secs(dur)
    t = times(n)
    out = np.zeros(n)
    for ratio, amp, tau in ((0.5, 0.25, 1.6), (1.0, 1.0, 1.2), (1.19, 0.25, 0.7), (1.5, 0.2, 0.5),
                            (2.0, 0.35, 0.45), (2.66, 0.08, 0.2)):
        fk = freq * ratio
        if fk < TINE_CEILING:
            out += amp * np.exp(-t / tau) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.3))
    return out * ramp_in(n, secs(0.003)) * ramp_in(n, secs(0.3))[::-1] * vel
