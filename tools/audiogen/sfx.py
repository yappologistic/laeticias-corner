"""Short mono effects. Each starts and ends at silence, stays soft and below ~8 kHz,
and is built from a few physical-ish layers (modes, filtered noise, voiced glides)."""

import numpy as np
from scipy import signal

import instruments as ins
from dsp import (bandpass, fade, glide, highpass, impulse_response, line, lowpass,
                 midi_hz, perc, phase_of, place, ramp_in, secs, sweep_lowpass, times,
                 voiced)


def modes(n, freqs, amps, decays, rng):
    """A struck object: decaying sine modes with random phases."""
    t = times(n)
    out = np.zeros(n)
    for f, a, d in zip(freqs, amps, decays):
        out += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t / d)
    return out * ramp_in(n, secs(0.0006))  # random phases must not start with a step


def noise_burst(n, rng, lo, hi, attack, decay):
    return bandpass(rng.standard_normal(n), lo, hi) * perc(n, attack, decay)


def room(x, rng, wet=0.15, size=0.3):
    """A touch of small-room reverb, mixed to mono, tail kept."""
    ir = impulse_response(rng, size, size * 0.6, size * 0.3, predelay=0.004).mean(axis=1)
    out = wet * signal.oaconvolve(x, ir)
    out[: len(x)] += x
    return out


def finish(x, fade_in=0.002, fade_out=0.02):
    """Trim the inaudible tail (below -60 dB of peak) and fade both ends to zero."""
    peak = np.max(np.abs(x))
    loud = np.nonzero(np.abs(x) > peak * 10 ** (-60 / 20))[0]
    x = x[: loud[-1] + 1] if len(loud) else x
    return fade(x, fade_in, fade_out)


# --- placement -------------------------------------------------------------------------


def place_soft(rng):
    """Leafy, earthy pat: a soft low thump, a muffled soil puff, and leaf rustle."""
    n = secs(0.22)
    t = times(n)
    thump = np.sin(phase_of(glide(n, [(0, 150), (0.08, 70)]))) * np.exp(-t / 0.035)
    soil = lowpass(rng.standard_normal(n), 900) * perc(n, 0.003, 0.03)
    rustle = np.zeros(n)
    for _ in range(9):
        g = secs(rng.uniform(0.004, 0.012))
        grain = bandpass(rng.standard_normal(g), 1500, 4500) * np.hanning(g)
        place(rustle, grain * rng.uniform(0.3, 1.0), secs(rng.uniform(0.0, 0.09)))
    return finish(room(thump + 0.6 * soil + 0.25 * rustle, rng, 0.1))


def place_wood(rng):
    """Wooden knock: a short block-like modal hit over a round low body."""
    n = secs(0.25)
    f0 = 340.0
    hit = modes(n, [f0, f0 * 2.31, f0 * 3.87, f0 * 5.4], [1.0, 0.55, 0.3, 0.12],
                [0.05, 0.03, 0.018, 0.01], rng)
    body = modes(n, [130, 210], [0.7, 0.3], [0.05, 0.035], rng)
    click = lowpass(rng.standard_normal(n) * perc(n, 0.0003, 0.002), 4000)
    return finish(room(lowpass(hit + body + 0.4 * click, 6000), rng, 0.12))


def place_stone(rng):
    """Stone clack: two small stones meeting, bright but short, with a grainy edge."""
    n = secs(0.2)
    f0 = 1250.0
    hit = modes(n, [f0, f0 * 1.63, f0 * 2.72, f0 * 3.9], [1.0, 0.7, 0.4, 0.15],
                [0.022, 0.016, 0.01, 0.007], rng)
    grit = noise_burst(n, rng, 1500, 5000, 0.0003, 0.006)
    thud = modes(n, [110, 180], [0.8, 0.4], [0.03, 0.02], rng)
    second = np.zeros(n)
    place(second, 0.35 * modes(secs(0.06), [f0 * 1.1, f0 * 1.9], [1.0, 0.5], [0.012, 0.008], rng),
          secs(0.028))
    mix = hit + 0.5 * grit + thud + second
    return finish(room(lowpass(mix, 6500), rng, 0.12))


def splash(rng):
    """Small water plop: the classic rising bubble 'bloop', a soft spray, droplets."""
    n = secs(0.45)
    t = times(n)
    bloop = np.sin(phase_of(glide(n, [(0, 260), (0.06, 820), (0.1, 900)]))) * perc(n, 0.002, 0.045)
    spray = noise_burst(n, rng, 600, 3500, 0.004, 0.06)
    drops = np.zeros(n)
    for _ in range(5):
        f = rng.uniform(900, 2000)
        m = secs(0.05)
        tm = times(m)
        d = np.sin(phase_of(f * (1 + 2 * tm))) * np.exp(-tm / 0.01)
        place(drops, d * rng.uniform(0.15, 0.35), secs(rng.uniform(0.08, 0.3)))
    under = lowpass(rng.standard_normal(n), 300) * np.exp(-t / 0.08)
    mix = lowpass(bloop + 0.35 * spray + drops + 0.4 * under, 4500, 4)
    return finish(room(mix, rng, 0.18), fade_out=0.04)


def paint(rng):
    """Very short soft brush-on-soil swish, gentle enough to repeat rapidly."""
    n = secs(0.085)
    env = np.sin(np.pi * np.arange(n) / n) ** 1.5
    brush = bandpass(rng.standard_normal(n), 700, 3200) * env
    soil = lowpass(rng.standard_normal(n), 400) * env
    return finish(lowpass(brush + 0.8 * soil, 5000, 4), 0.003, 0.015)


def remove(rng):
    """Soft poof: an airy puff whose colour sinks as it fades, with a faint drop."""
    n = secs(0.32)
    cutoff = glide(n, [(0, 2200), (0.3, 300)])
    puff = sweep_lowpass(rng.standard_normal(n), cutoff)
    puff *= perc(n, 0.012, 0.08)
    sink = np.sin(phase_of(glide(n, [(0, 320), (0.2, 160)]))) * perc(n, 0.01, 0.06)
    return finish(room(lowpass(puff, 3500, 4) + 0.5 * sink, rng, 0.15), fade_out=0.05)


def rotate(rng):
    """Light turn: a quick airy swish rising in colour, ending in a tiny wooden tick."""
    n = secs(0.16)
    t = times(n)
    env = np.sin(np.pi * np.clip(t / 0.11, 0, 1)) ** 2
    swish = bandpass(rng.standard_normal(n), 900, 2600) * env
    tick = np.zeros(n)
    place(tick, modes(secs(0.04), [1900, 3100], [1.0, 0.4], [0.006, 0.004], rng), secs(0.1))
    return finish(lowpass(0.6 * swish + tick, 5000, 4))


def invalid(rng):
    """Muted 'nope': two soft low notes falling a minor third, round and short."""
    out = np.zeros(secs(0.42))
    for i, (m, at) in enumerate(((57, 0.0), (54, 0.13))):  # A3 -> F#3
        n = secs(0.25)
        t = times(n)
        f = midi_hz(m)
        ph = 2 * np.pi * f * t
        x = (np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)) * perc(n, 0.008, 0.07)
        place(out, x * (1.0 if i == 0 else 0.85), secs(at))
    return finish(lowpass(room(out, rng, 0.1), 2000))


def _two_tines(rng, first, second):
    """Two quick music-box notes; the shared gesture behind undo and redo."""
    out = np.zeros(secs(0.5))
    for i, m in enumerate((first, second)):
        x = ins.tine(midi_hz(m), 0.4, 0.6, rng) * np.exp(-times(secs(0.4)) / 0.09)
        place(out, x * (1.0 if i else 0.8), secs(0.07 * i))
    return finish(room(out, rng, 0.12), fade_out=0.06)


def undo(rng):
    return _two_tines(rng, 81, 76)  # A5 -> E5: a step back


def redo(rng):
    return _two_tines(rng, 78, 83)  # F#5 -> B5: the same step forward, a little higher


# --- interface -------------------------------------------------------------------------


def ui_hover(rng):
    """Barely-there tick."""
    n = secs(0.03)
    return finish(modes(n, [1700, 2900], [1.0, 0.3], [0.004, 0.002], rng), 0.0005, 0.008)


def ui_click(rng):
    """Soft click: a small rounded tap with a hint of body."""
    n = secs(0.06)
    x = modes(n, [950, 2100, 3300], [1.0, 0.5, 0.15], [0.01, 0.005, 0.003], rng)
    x += 0.15 * lowpass(rng.standard_normal(n) * perc(n, 0.0002, 0.0015), 5000)
    return finish(x, 0.0005, 0.012)


def _pop(rng, start, end):
    """A small bubble-like pop gliding between two pitches."""
    n = secs(0.12)
    x = np.sin(phase_of(glide(n, [(0, start), (0.07, end)]))) * perc(n, 0.004, 0.035)
    x += 0.3 * np.sin(2 * phase_of(glide(n, [(0, start), (0.07, end)]))) * perc(n, 0.004, 0.02)
    return finish(room(x, rng, 0.08), 0.001, 0.02)


def ui_open(rng):
    return _pop(rng, 420, 880)


def ui_close(rng):
    return _pop(rng, 880, 420)


def shutter(rng):
    """Camera shutter: an opening snap, a short mechanical whirr, a closing clack."""
    n = secs(0.2)
    out = np.zeros(n)
    for at, f, level in ((0.0, 2400, 1.0), (0.075, 1800, 0.8)):
        m = secs(0.04)
        click = noise_burst(m, rng, 1500, 6000, 0.0002, 0.003)
        click += modes(m, [f, f * 1.7, 700], [0.6, 0.3, 0.4], [0.008, 0.005, 0.012], rng)
        place(out, click * level, secs(at))
    whirr = bandpass(rng.standard_normal(n), 800, 2500) * np.clip(
        line(n, [(0, 0), (0.01, 0.12), (0.07, 0.12), (0.08, 0)]), 0, None)
    return finish(room(lowpass(out + whirr, 7000), rng, 0.1))


def discover(rng):
    """Happy chime: A5 D6 F#6 A6 on the music box, the day theme's key (D major)."""
    out = np.zeros(secs(1.8))
    for i, m in enumerate((81, 86, 90, 93)):
        x = ins.tine(midi_hz(m), 1.5, 0.75, rng)
        place(out, x * (0.75 + 0.1 * i), secs(0.09 * i))
    return finish(room(out, rng, 0.25, 1.0), fade_out=0.3)


# --- animals ---------------------------------------------------------------------------


def duck(rng):
    """Two soft, nasal quacks, the second a touch lower."""
    out = np.zeros(secs(0.5))
    for i, (at, scale) in enumerate(((0.0, 1.0), (0.21, 0.92))):
        dur = 0.15
        n = secs(dur)
        f0 = glide(n, [(0, 330 * scale), (0.03, 300 * scale), (dur, 230 * scale)])
        formants = [(900, 350, 1.0), (1500, 400, 0.7), (2600, 600, 0.25)]
        x = voiced(f0, formants) * perc(n, 0.006, 0.06) * ramp_in(n, secs(0.03))[::-1]
        x += 0.08 * bandpass(rng.standard_normal(n), 1000, 3000) * perc(n, 0.002, 0.03)
        place(out, x * (1.0 if i == 0 else 0.8), secs(at))
    return finish(room(lowpass(out, 5000), rng, 0.08))


def hen(rng):
    """A short run of clucks: buk, buk, bu-kawk."""
    out = np.zeros(secs(0.65))
    for at, dur, top, bottom, level in ((0.0, 0.06, 520, 380, 0.8), (0.14, 0.06, 540, 390, 0.8),
                                        (0.3, 0.05, 500, 420, 0.7), (0.37, 0.2, 640, 470, 1.0)):
        n = secs(dur)
        f0 = glide(n, [(0, top), (dur, bottom)])
        f1 = line(n, [(0, 700), (dur * 0.3, 1000), (dur, 800)])
        x = voiced(f0, [(f1, 300, 1.0), (2200, 500, 0.4), (3200, 700, 0.12)])
        env = perc(n, 0.004, dur * 0.5) * ramp_in(n, secs(0.015))[::-1]
        place(out, x * env * level, secs(at))
    return finish(room(lowpass(out, 5500), rng, 0.08))


def cat(rng):
    """A short, friendly 'mrrp-miaow': rolled start, then a vowel opening and closing."""
    dur = 0.55
    n = secs(dur)
    t = times(n)
    f0 = glide(n, [(0, 430), (0.12, 520), (0.25, 680), (0.42, 600), (dur, 470)])
    f1 = line(n, [(0, 450), (0.12, 450), (0.28, 950), (0.45, 700), (dur, 450)])
    f2 = line(n, [(0, 1900), (0.12, 2100), (0.28, 1600), (0.45, 1100), (dur, 900)])
    x = voiced(f0, [(f1, 250, 1.0), (f2, 350, 0.55), (3200, 600, 0.12)])
    trill = 1 - 0.6 * (t < 0.12) * (0.5 + 0.5 * np.cos(2 * np.pi * 28 * t))
    env = np.clip(line(n, [(0, 0), (0.03, 0.6), (0.14, 0.7), (0.3, 1.0), (0.45, 0.6), (dur, 0)]), 0, 1)
    breath = 0.03 * highpass(rng.standard_normal(n), 2000) * env
    return finish(room(lowpass(x * trill * env + breath, 5000), rng, 0.08), fade_out=0.04)
