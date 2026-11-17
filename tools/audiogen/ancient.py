"""Voices for the three ancient cities: plucked strings by digital waveguide (angular harp,
long-necked lute, kithara, lyra, barbitos, cithara), reed pipes played as continuous phrases
(double pipe, aulos, tibia), frame drum, clappers, small cymbals, sistrum, hydraulis, natural
horn and cornu, and a wordless hummed choir. Each returns a mono note or phrase."""

import numpy as np
from scipy import signal

from dsp import (SR, bandpass, highpass, lowpass, perc, phase_of, ramp_in, secs, times, voice,
                 wobble)

CEILING = 7500.0  # nothing above this is synthesised: these are soft, warm instruments

# --- plucked strings -------------------------------------------------------------------

# Each plucked instrument: loss-filter tap (more = duller gut), pluck point along the string
# (small = near the bridge, nasal), excitation brightness (finger vs plectrum), the fundamental's
# ring time at 220 Hz, and the body's resonances (Hz, Q, gain).
STRINGS = {
    # Vertical angular harp: gut strings over a box resonator, plucked with the fingers.
    "harp": dict(loss=0.32, point=0.27, bright=2600, ring=7.0, body=((260, 3, 0.8), (720, 4, 0.5),
                                                                   (1500, 5, 0.25))),
    # Long-necked lute: small skin-topped body, plectrum near the bridge: twangy and nasal.
    "lute": dict(loss=0.18, point=0.09, bright=4200, ring=3.5, body=((420, 6, 1.0),
                                                                   (1150, 7, 0.7), (2400, 6, 0.3))),
    # Kithara: large wooden concert lyre, plectrum, a big resonant box.
    "kithara": dict(loss=0.24, point=0.13, bright=4000, ring=6.0,
                    body=((185, 3, 0.9), (330, 4, 0.7), (620, 4, 0.5), (1150, 5, 0.3))),
    # Lyra: tortoise-shell lyre with a hide front: lighter, a little hollow.
    "lyra": dict(loss=0.3, point=0.16, bright=3200, ring=5.0, body=((300, 4, 0.8), (820, 5, 0.6),
                                                                  (1900, 6, 0.2))),
    # Barbitos: long arms, long low strings, plucked with the fingers: dark and soft.
    "barbitos": dict(loss=0.42, point=0.22, bright=1800, ring=8.0,
                     body=((140, 3, 0.9), (260, 3, 0.7), (540, 4, 0.35))),
    # Roman cithara: the concert instrument of the citharodes, warm and large.
    "cithara": dict(loss=0.28, point=0.15, bright=3400, ring=7.0,
                    body=((160, 3, 1.0), (290, 3, 0.8), (540, 4, 0.5), (980, 5, 0.25))),
}


def _body(x, resonances):
    """Direct sound plus a few parallel body resonances (the soundbox colouring the string)."""
    out = 0.5 * x
    for f, q, g in resonances:
        b, a = signal.iirpeak(f, q, fs=SR)
        out = out + g * signal.lfilter(b, a, x)
    return out


def _waveguide(x, delay, c, b0, b1, b2):
    """y[n] = x[n] + c x[n-1] - c y[n-1] + b0 y[n-D] + b1 y[n-D-1] + b2 y[n-D-2], run a delay
    line at a time: the feedback only reaches back a whole period, so each block depends on
    the previous one plus a first-order all-pass recursion inside it."""
    n = len(x)
    if delay < 120:  # short lines: one direct filter is cheaper than many small blocks
        den = np.zeros(delay + 3)
        den[0], den[1] = 1.0, c
        den[delay:] -= (b0, b1, b2)
        return signal.lfilter([1.0, c], den, x)
    pad = delay + 2
    y = np.zeros(n + pad)
    u = x + c * np.concatenate([[0.0], x[:-1]])
    last = 0.0
    for s in range(0, n, delay):
        e = min(n, s + delay)
        i = np.arange(s, e) + pad
        v = u[s:e] + b0 * y[i - delay] + b1 * y[i - delay - 1] + b2 * y[i - delay - 2]
        blk, _ = signal.lfilter([1.0], [1.0, c], v, zi=[-c * last])
        y[s + pad:e + pad] = blk
        last = blk[-1]
    return y[pad:]


def string(kind, freq, dur, vel, rng, damp=None):
    """A plucked string by Karplus-Strong waveguide: one period of shaped noise circulates
    through a delay line with a two-tap loss filter (gut damping: high partials die first),
    a first-order all-pass for exact tuning and a pick-position comb; then the body. `dur`
    bounds the ring; `damp` (s) stops the string with the hand, as lyre players did."""
    p = STRINGS[kind]
    n = secs(dur)
    period = SR / freq
    a1 = p["loss"] * min(1.0, (freq / 220.0) ** 0.15)
    a0 = 1.0 - a1
    whole = int(np.floor(period - a1 - 0.1))
    frac = period - a1 - whole  # all-pass carries the fractional delay, kept in [0.1, 1.1)
    c = (1 - frac) / (1 + frac)
    # Per-period gain sets the fundamental's ring time (high notes ring a little shorter).
    ring = p["ring"] * (220.0 / freq) ** 0.35
    loss_f0 = abs(a0 + a1 * np.exp(-2j * np.pi * freq / SR))
    g = min(0.9995, 10 ** (-3 / (freq * ring)) / loss_f0)
    m = int(np.ceil(period))
    shape = 1 - np.abs(np.linspace(-1, 1, m))  # a finger pulls the string into a triangle
    burst = 0.6 * shape + 0.4 * lowpass(rng.standard_normal(m), p["bright"] * (0.6 + 0.6 * vel))
    burst -= burst.mean()
    lag = max(1, int(round(p["point"] * m)))
    burst = burst - np.concatenate([np.zeros(lag), burst[:-lag]])  # pluck point comb
    x = np.zeros(n)
    x[:m] = burst
    y = _waveguide(x, whole, c, g * a0 * c, g * (a0 + a1 * c), g * a1)
    y = lowpass(y, min(CEILING, 1500 + 5000 * vel), 2)
    y = _body(y, p["body"])
    click = lowpass(rng.standard_normal(n) * perc(n, 0.0003, 0.002), p["bright"])
    y = y + 0.04 * vel * click
    t = times(n)
    if damp is not None:
        y *= np.exp(-np.clip(t - damp, 0, None) / 0.06)
    return y * ramp_in(n, 4) * ramp_in(n, secs(0.15))[::-1] * vel


# --- reed pipes ------------------------------------------------------------------------

# Spectral recipe per pipe: odd/even balance (cylindrical bore and reed), formants (Hz,
# bandwidth, gain) giving the nasal bite, breath noise and the scoop into each note (cents).
PIPES = {
    # Elamite double pipe: mellow, reedy, warm.
    "pipe": dict(even=0.45, formants=((950, 700, 1.0), (2300, 900, 0.35)), roll=2600, breath=0.05,
                 scoop=35),
    # Greek aulos: strong, bright and nasal, with breath and pitch bends.
    "aulos": dict(even=0.6, formants=((1250, 600, 1.0), (2800, 900, 0.5)), roll=3800, breath=0.07,
                  scoop=55),
    # Roman tibia: the same family, softer and rounder.
    "tibia": dict(even=0.5, formants=((800, 650, 1.0), (2000, 900, 0.28)), roll=2300, breath=0.06,
                  scoop=30),
}


def reed_phrase(kind, notes, n, rng, legato=0.03):
    """One continuous reed line: `notes` are (start_s, dur_s, hz, vel, slur, graces) and the
    pitch glides between them like fingers moving on a pipe, re-tongued unless slurred, with
    grace notes as quick upper-neighbour flicks. Returns n samples (mono)."""
    p = PIPES[kind]
    pitch = np.zeros(n)
    amp = np.zeros(n)
    last = notes[0][2]
    for i, (start, dur, hz, vel, slur, graces) in enumerate(notes):
        # A note flows straight into a slurred successor that starts as it ends.
        flows = (i + 1 < len(notes) and notes[i + 1][4]
                 and abs(notes[i + 1][0] - (start + dur)) < 0.01)
        a, b = secs(start), min(n, secs(start + dur))
        if b <= a:
            continue
        m = b - a
        t = times(m)
        tongue = secs(0.012 if slur else 0.025)
        # Fingered glide from the previous pitch, then a little scoop up into the note.
        glide_n = secs(legato)
        f = np.full(m, hz)
        if graces:
            gn = secs(0.06)
            for i, gh in enumerate(graces):
                lo, hi = i * gn, min(m, (i + 1) * gn)
                f[lo:hi] = gh
        else:
            k = min(m, glide_n)
            f[:k] = last * (hz / last) ** (np.arange(k) / max(1, k))
            if not slur:
                f *= 2 ** (-p["scoop"] / 1200 * np.exp(-t / 0.04))
        pitch[a:b] = f
        env = np.minimum(1.0, t / 0.03 + (1.0 if slur else 0.0))
        if not flows:
            env *= np.minimum(1.0, (m - np.arange(m)) / max(1, secs(0.05)))
        if not slur:
            env *= ramp_in(m, tongue)
        amp[a:b] = np.maximum(amp[a:b], env * vel)
        last = hz
    # Fill gaps' pitch so the oscillator never sees zero frequency.
    held = pitch.copy()
    idx = np.where(held > 0, np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    held = held[idx]
    held[held <= 0] = notes[0][2]
    held *= wobble(n, rng, 0.0012, 3.0)  # a player's breath never holds perfectly still
    amp = lowpass(amp, 60, 2)
    amp *= wobble(n, rng, 0.03, 8.0)
    ph = phase_of(held)
    out = np.zeros(n)
    for k in range(1, 30):
        fk = k * held
        if fk.min() > CEILING:
            break
        w = (1.0 if k % 2 else p["even"]) * k**-0.7
        form = sum(g / (1 + ((fk - c) / (0.5 * bw)) ** 2) for c, bw, g in p["formants"])
        w = w * (0.35 + form) / (1 + (fk / p["roll"]) ** 3) * (fk < CEILING)
        out += w * np.sin(k * ph)
    # Breath: a slow flutter riding on the tone (narrow, so harmonics stay clean) plus a
    # little air in the bore's formant band, both following the player's dynamics.
    flutter = lowpass(rng.standard_normal(n), 300, 2)
    out = out * (1 + p["breath"] * 2 * flutter / (np.std(flutter) + 1e-12))
    air = bandpass(rng.standard_normal(n), 900, 3000, 2)
    out = out + p["breath"] * 0.5 * air * np.std(out) / (np.std(air) + 1e-12)
    return out * amp


# --- percussion ------------------------------------------------------------------------

MEMBRANE = (1.0, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501)


def frame_drum(stroke, vel, rng, f0=92.0):
    """Frame drum (large thin skin on a wooden hoop) by membrane modes: 'D' a low centre
    stroke whose pitch sinks as the skin relaxes, 'T' a ringing edge stroke, 'k' a soft
    finger tap, 'R' one tap of a finger roll."""
    n = secs(0.9 if stroke == "D" else 0.4)
    t = times(n)
    if stroke == "D":
        amps, decay, slap = (1.0, 0.25, 0.12, 0.35, 0.05, 0.08, 0.02, 0.03), 0.22, 0.15
    elif stroke == "T":
        amps, decay, slap = (0.15, 0.5, 0.6, 0.2, 0.5, 0.4, 0.3, 0.25), 0.07, 0.6
    else:
        amps, decay, slap = (0.2, 0.45, 0.45, 0.15, 0.35, 0.3, 0.2, 0.15), 0.04, 0.35
    bend = 1 + 0.05 * vel * np.exp(-t / 0.04)
    out = np.zeros(n)
    for ratio, a in zip(MEMBRANE, amps):
        ph = phase_of(f0 * ratio * bend)
        out += a * np.sin(ph + rng.uniform(0, 6.3)) * np.exp(-t * ratio**0.5 / decay)
    skin = lowpass(rng.standard_normal(n), 2500 if stroke == "D" else 4500) * perc(n, 0.0005, 0.008)
    out = out * ramp_in(n, secs(0.001)) + slap * skin
    return lowpass(out, 5000, 2) * ramp_in(n, secs(0.05))[::-1] * vel


def clapper(vel, rng, f0=1300.0, double=False):
    """Wooden clappers (Persian clapper, Greek krotala): a dry knock of two small boards;
    krotala click twice as the halves meet."""
    n = secs(0.12)
    t = times(n)
    out = np.zeros(n)
    hits = (0.0, rng.uniform(0.012, 0.02)) if double else (0.0,)
    for i, at in enumerate(hits):
        k = secs(at)
        m = n - k
        tm = t[:m]
        x = sum(a * np.sin(2 * np.pi * f0 * r * tm + rng.uniform(0, 6.3)) * np.exp(-tm / d)
                for r, a, d in ((1.0, 1.0, 0.014), (1.71, 0.6, 0.009), (2.63, 0.3, 0.006)))
        x = x + 0.6 * bandpass(rng.standard_normal(m), 900, 4000) * np.exp(-tm / 0.004)
        out[k:] += x * ramp_in(m, 6) * (1.0 if i == 0 else 0.6)
    return lowpass(out, 6500, 2) * ramp_in(n, secs(0.02))[::-1] * vel


def cymbals(vel, rng, f0=1180.0, ring=1.4):
    """Small bronze cymbals touched together: inharmonic plate modes, the lowest ringing
    longest, kept soft and below the ceiling."""
    n = secs(ring * 2)
    t = times(n)
    out = np.zeros(n)
    for r, a in ((1.0, 1.0), (1.47, 0.6), (2.09, 0.5), (2.56, 0.35), (3.12, 0.25), (3.9, 0.15),
                 (4.6, 0.1)):
        fk = f0 * r
        if fk < CEILING:
            beat = 1 + 0.004 * rng.standard_normal()
            out += a * np.sin(2 * np.pi * fk * beat * t + rng.uniform(0, 6.3)) * np.exp(-t * r / ring)
    tap = bandpass(rng.standard_normal(n), 2000, 6000) * perc(n, 0.0005, 0.006)
    out = out * ramp_in(n, secs(0.0015)) + 0.3 * tap
    return lowpass(out, CEILING, 4) * ramp_in(n, secs(0.3))[::-1] * vel


def sistrum(vel, rng, shakes=2, spacing=0.22):
    """Sistrum of Isis: loose metal discs on rods sliding and jangling as the frame is
    shaken back and forth: a swarm of tiny bright ticks gathered in each stroke."""
    n = secs(shakes * spacing + 0.5)
    out = np.zeros(n)
    for s in range(shakes):
        centre = s * spacing + 0.04
        for _ in range(int(rng.integers(26, 40))):
            at = centre + abs(rng.normal(0, 0.03))
            m = secs(0.05)
            tm = times(m)
            f = rng.uniform(2300, 5200)
            tick = np.sin(2 * np.pi * f * tm + rng.uniform(0, 6.3)) * np.exp(-tm / rng.uniform(0.006, 0.02))
            k = secs(at)
            if k + m < n:
                out[k:k + m] += tick * rng.uniform(0.2, 1.0) * (1.0 if s % 2 == 0 else 0.8)
    out += 0.15 * bandpass(rng.standard_normal(n), 2000, 6000) * (np.abs(out) > 0.05)
    return lowpass(out, CEILING, 4) * ramp_in(n, secs(0.003)) * ramp_in(n, secs(0.1))[::-1] * vel


# --- winds -----------------------------------------------------------------------------


def hydraulis(freq, dur, vel, rng, release=0.35):
    """Water organ: bronze flue pipes on a wind chest kept steady by water, so the tone is
    breathy and slightly fluttering (the pump's tremolo); a soft chiff as the slider opens."""
    n = secs(dur + release)
    t = times(n)
    flutter = 1 + 0.025 * np.sin(2 * np.pi * rng.uniform(4.6, 5.4) * t + rng.uniform(0, 6.3))
    ph = phase_of(np.full(n, freq) * (1 + 0.0008 * (flutter - 1) / 0.025))
    tone = sum(a * np.sin(k * ph) for k, a in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12), (5, 0.06),
                                               (6, 0.03)) if k * freq < CEILING)
    wind = bandpass(rng.standard_normal(n), freq * 1.5, min(freq * 8, 6000)) * 0.05
    chiff = bandpass(rng.standard_normal(n), freq * 2, min(freq * 6, 6000)) * perc(n, 0.004, 0.03)
    env = np.minimum(1, t / 0.06) * np.exp(-np.clip(t - dur, 0, None) / (release / 3))
    return ((tone + wind) * flutter * env + 0.3 * chiff) * ramp_in(n, secs(0.02))[::-1] * vel


def horn(freq, dur, vel, rng, bright=1.0, release=0.4):
    """Brass natural horn (Persian long horn, Roman cornu): lip-buzzed partials that grow
    brighter as the note swells, a scoop from below as the lips find the partial."""
    n = secs(dur + release)
    t = times(n)
    env = np.minimum(1, t / 0.12) ** 1.5 * np.exp(-np.clip(t - dur, 0, None) / (release / 3))
    env *= 1 + 0.08 * np.sin(np.pi * np.clip(t / max(dur, 0.1), 0, 1))
    f = freq * (1 - 0.03 * np.exp(-t / 0.05)) * wobble(n, rng, 0.0015, 4.0)
    ph = phase_of(f)
    out = np.zeros(n)
    for k in range(1, 16):
        if k * freq > CEILING:
            break
        # Brightness follows the swell: upper partials need more breath.
        w = k**-1.0 * np.clip(env * bright * 1.2, 0, 1) ** (0.4 * (k - 1))
        out += w * np.sin(k * ph)
    buzz = bandpass(rng.standard_normal(n), freq * 2, min(freq * 6, 5000)) * perc(n, 0.01, 0.05)
    return (out * env + 0.1 * buzz) * ramp_in(n, secs(0.02))[::-1] * vel


def hum(freq, dur, vel, rng, release=1.2, vowel="m"):
    """A wordless hummed voice: closed-mouth 'mm' (nasal murmur) or open 'oo', with natural
    jitter and a slow swell; used in small groups for a soft drone."""
    n = secs(dur + release)
    t = times(n)
    formants = {"m": [(280, 120, 1.0), (1150, 300, 0.08), (2500, 400, 0.03)],
                "o": [(420, 120, 1.0), (800, 160, 0.45), (2600, 400, 0.04)]}[vowel]
    f0 = np.full(n, float(freq)) * (1 + 0.003 * np.sin(2 * np.pi * 5.0 * t + rng.uniform(0, 6.3))
                                    * np.clip((t - 0.6) / 0.6, 0, 1))
    x = voice(f0, formants, rng, tilt=1.4, jitter=0.002, shimmer=0.04, breath=0.12)
    env = np.minimum(1, t / 0.8) ** 2 * np.exp(-np.clip(t - dur, 0, None) / (release / 3))
    return highpass(x, 90, 2) * env * ramp_in(n, secs(0.05))[::-1] * vel


def flute(freq, dur, vel, rng, release=0.15):
    """Shepherd's pipe / syrinx tube: a breathy, almost pure tone with a puff on the attack."""
    n = secs(dur + release)
    t = times(n)
    f = freq * (1 - 0.012 * np.exp(-t / 0.03)) * wobble(n, rng, 0.001, 4.0)
    ph = phase_of(f)
    tone = np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    breath = bandpass(rng.standard_normal(n), freq * 0.8, min(freq * 4, 6500))
    puff = bandpass(rng.standard_normal(n), 800, 3000) * perc(n, 0.005, 0.04)
    env = np.minimum(1, t / 0.05) * np.exp(-np.clip(t - dur, 0, None) / (release / 3))
    return ((tone + 0.18 * breath) * env + 0.2 * puff) * ramp_in(n, secs(0.02))[::-1] * vel
