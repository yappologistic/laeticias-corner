"""Ambience beds: birds, crickets, rain and water. Each is a seamless stereo loop: beds
are periodic noise built in the frequency domain, events are scattered over the loop
and their tails folded back onto its start."""

import numpy as np

from dsp import (SR, bandpass, circular, glide, highpass, impulse_response, line, lowpass, pan,
                 phase_of, place, ramp_in, secs, shaped_noise, smooth_random,
                 times, voiced, with_reverb, wrap)


def tone(freq, env, harm2=0.0):
    """Sine (plus optional second harmonic) following a frequency curve."""
    ph = phase_of(freq)
    return env * (np.sin(ph) + harm2 * np.sin(2 * ph))


def arch(n, power=0.6):
    """Smooth swell-and-fade envelope for a syllable."""
    return np.sin(np.pi * np.arange(n) / n) ** power


def concat(parts):
    """Join (signal, gap_seconds) pairs into one call."""
    out = []
    for x, gap in parts:
        out += [x, np.zeros(secs(gap))]
    return np.concatenate(out)


# --- birds -----------------------------------------------------------------------------


def whistle(rng, f):
    """Two- or three-note clear whistle, falling ("fee-bee")."""
    notes = [(rng.uniform(0.22, 0.32), f, f * 0.985), (rng.uniform(0.28, 0.38), f * 0.81, f * 0.79)]
    if rng.random() < 0.4:
        notes.append((0.18, f * 0.83, f * 0.8))
    parts = []
    for dur, a, b in notes:
        n = secs(dur)
        vib = 1 + 0.006 * np.sin(2 * np.pi * 6.5 * times(n))
        parts.append((tone(glide(n, [(0, a), (dur, b)]) * vib, arch(n, 0.5), 0.05),
                      rng.uniform(0.06, 0.12)))
    return concat(parts)


def trill(rng, f):
    """A run of quick down-slurred syllables that swells and fades."""
    k = int(rng.integers(6, 13))
    period = 1 / rng.uniform(10, 15)
    parts = []
    for i in range(k):
        n = secs(0.6 * period)
        contour = np.sin(np.pi * (i + 0.5) / k) ** 0.7
        top = f * rng.uniform(0.97, 1.03)
        parts.append((contour * tone(glide(n, [(0, top), (0.6 * period, top * 0.62)]), arch(n)),
                      0.4 * period))
    return concat(parts)


def carol(rng, f):
    """A robin-like phrase of varied syllables: rises, falls, arches."""
    parts = []
    for _ in range(int(rng.integers(3, 7))):
        dur = rng.uniform(0.1, 0.22)
        n = secs(dur)
        base = f * rng.uniform(0.75, 1.2)
        shape = rng.integers(4)
        if shape == 0:
            pts = [(0, base), (dur, base * 1.3)]
        elif shape == 1:
            pts = [(0, base * 1.3), (dur, base)]
        elif shape == 2:
            pts = [(0, base), (dur * 0.4, base * 1.25), (dur, base * 0.9)]
        else:
            pts = [(0, base), (dur, base * 1.02)]
        wob = 1 + 0.02 * np.sin(2 * np.pi * rng.uniform(25, 40) * times(n))
        parts.append((tone(glide(n, pts) * wob, arch(n, 0.5), 0.12), rng.uniform(0.05, 0.14)))
    return concat(parts)


def chips(rng, f):
    """A few soft, irregular call notes."""
    parts = []
    for _ in range(int(rng.integers(2, 5))):
        n = secs(0.03)
        parts.append((0.7 * tone(glide(n, [(0, f), (0.03, f * 0.8)]), arch(n)),
                      rng.uniform(0.15, 0.45)))
    return concat(parts)


def coo(rng, f):
    """Low, breathy dove coo far away: hoo-HOO-hoo hoo."""
    parts = []
    for dur, level, gap in ((0.22, 0.6, 0.12), (0.45, 1.0, 0.18), (0.22, 0.6, 0.1), (0.3, 0.7, 0)):
        n = secs(dur)
        pitch = glide(n, [(0, f * 0.94), (dur * 0.3, f * 1.03), (dur, f * 0.9)])
        breath = bandpass(np.random.default_rng(int(rng.integers(1 << 31))).standard_normal(n),
                          f * 0.8, f * 2.5) * 0.08
        x = tone(pitch, arch(n, 0.8), 0.15) + breath * arch(n)
        parts.append((level * x, gap * rng.uniform(0.9, 1.2)))
    return concat(parts)


BIRDS = [  # (song, weight, pitch range Hz, distance range)
    (carol, 4, (2100, 3000), (0.1, 0.5)),
    (whistle, 2, (2700, 3500), (0.2, 0.6)),
    (trill, 2, (4000, 5000), (0.3, 0.8)),
    (chips, 2, (4200, 5200), (0.0, 0.4)),
    (coo, 1, (440, 560), (0.7, 0.9)),
]


def birds(rng, length=48.0):
    """Five resident birds, each with its own voice, place and distance, calling at
    irregular intervals; no two calls are rendered alike."""
    loop_n = secs(length)
    singers = []
    for song, weight, (lo, hi), (dlo, dhi) in BIRDS:
        singers.append({"song": song, "weight": weight, "f": rng.uniform(lo, hi),
                        "pan": rng.uniform(-0.8, 0.8), "dist": rng.uniform(dlo, dhi)})
    weights = np.array([s["weight"] for s in singers], dtype=float)
    dry = np.zeros((loop_n + secs(4), 2))
    send = np.zeros_like(dry)
    t, last = rng.uniform(0, 1.5), None
    while t < length:
        pick = rng.choice(len(singers), p=weights / weights.sum())
        if pick == last and singers[pick]["song"] is not carol:
            continue
        s = singers[pick]
        call = s["song"](rng, s["f"] * rng.uniform(0.96, 1.04))
        dist = np.clip(s["dist"] + rng.normal(0, 0.05), 0, 1)
        call = lowpass(call, 8000 - 4500 * dist, 2) * (1 - 0.65 * dist) * rng.uniform(0.75, 1.0)
        x = pan(call, s["pan"] + rng.normal(0, 0.05))
        at = secs(t)
        place(dry, x, at)
        place(send, x * (0.2 + 0.8 * dist), at)
        t += len(call) / SR + rng.uniform(1.5, 5.0)
        last = pick
    ir = impulse_response(rng, 2.0, 1.2, 0.6, predelay=0.02)
    out = wrap(with_reverb(dry, send, ir, 0.5), loop_n)
    breeze = shaped_noise(loop_n, rng, lambda f: 1 / (1 + (f / 350) ** 2) / np.sqrt(f), 2)
    sway = 1 + 0.5 * smooth_random(loop_n, rng, 0.15)
    return out + 0.004 * breeze * np.clip(sway, 0.2, None)[:, None]


# --- crickets --------------------------------------------------------------------------


def cricket_chirp(rng, carrier, pulses):
    """One chirp: a few 18 ms sine pulses 34 ms apart, each falling slightly in pitch."""
    pulse_n, gap_n = secs(0.018), secs(0.016)
    parts = []
    for i in range(pulses):
        f = glide(pulse_n, [(0, carrier * 1.01), (0.018, carrier * 0.99)])
        level = 0.75 + 0.25 * np.sin(np.pi * (i + 0.5) / pulses)
        parts.append((level * tone(f, arch(pulse_n, 1.5)), gap_n / SR))
    return concat(parts)


def owl(rng):
    """Distant tawny-style hoot: hoo ... hu-hoooo."""
    parts = []
    for dur, f0, gap in ((0.45, 410, 0.9), (0.18, 395, 0.08), (0.9, 420, 0)):
        n = secs(dur)
        pitch = glide(n, [(0, f0 * 0.97), (dur * 0.2, f0 * 1.02), (dur, f0 * 0.95)])
        wav = 1 + 0.01 * np.sin(2 * np.pi * 5 * times(n))
        parts.append((tone(pitch * wav, arch(n, 0.7) ** 1.5, 0.1), gap))
    return concat(parts)


def frog(rng):
    """A soft two-part croak: a pulsed low voiced sound."""
    parts = []
    for _ in range(int(rng.integers(2, 4))):
        dur = rng.uniform(0.18, 0.28)
        n = secs(dur)
        f0 = line(n, [(0, 190), (dur, 160)]) * rng.uniform(0.9, 1.1)
        body = voiced(f0, [(550, 300, 1.0), (1400, 500, 0.4)], n_harm=12)
        pulses = (0.5 + 0.5 * np.sin(2 * np.pi * 32 * times(n))) ** 2
        parts.append((body * pulses * arch(n, 0.5), rng.uniform(0.25, 0.5)))
    return concat(parts)


def crickets(rng, length=48.0):
    """A handful of field crickets at different distances, each chirping at its own
    steady rate (an exact divisor of the loop, so the rhythm survives the seam),
    resting now and then, over a faint far trill; an owl and a frog drop by."""
    loop_n = secs(length)
    dry = np.zeros((loop_n + secs(3), 2))
    send = np.zeros_like(dry)
    for _ in range(5):
        carrier = rng.uniform(3700, 4600)
        n_chirps = int(rng.integers(55, 85))
        period = length / n_chirps
        phase = rng.uniform(0, period)
        pulses = int(rng.integers(3, 5))
        dist = rng.uniform(0.15, 0.9)
        position = rng.uniform(-0.9, 0.9)
        activity = smooth_random(loop_n, rng, 0.08)
        threshold = rng.uniform(-1.0, -0.2)
        for k in range(n_chirps):
            at = secs(phase + k * period + rng.normal(0, 0.004)) % loop_n
            awake = activity[at] - threshold
            if awake <= 0:
                continue
            level = min(1.0, awake * 2) * (1 - 0.7 * dist) * rng.uniform(0.85, 1.0)
            x = pan(level * cricket_chirp(rng, carrier, pulses), position)
            place(dry, x, at)
            place(send, x * dist, at)
    t = rng.uniform(5, 20)
    for voice, gain, dist_send in ((owl, 0.35, 1.0), (frog, 0.3, 0.7), (frog, 0.25, 0.7)):
        call = lowpass(voice(rng), 2500, 2) * gain
        x = pan(call, rng.uniform(-0.7, 0.7))
        place(dry, x, secs(t))
        place(send, x * dist_send, secs(t))
        t = (t + rng.uniform(10, 18)) % (length - 3)
    ir = impulse_response(rng, 2.5, 1.6, 0.7, predelay=0.025)
    out = wrap(with_reverb(dry, send, ir, 0.6), loop_n)
    far = shaped_noise(loop_n, rng, lambda f: np.exp(-(((f - 3300) / 300) ** 2)), 2)
    far *= (0.6 + 0.4 * np.sin(2 * np.pi * 48 * times(loop_n)))[:, None]
    far *= np.clip(1 + 0.6 * smooth_random(loop_n, rng, 0.1), 0.2, None)[:, None]
    air = shaped_noise(loop_n, rng, lambda f: 1 / (1 + (f / 250) ** 2) / f, 2)
    return out + 0.012 * far + 0.006 * air


# --- rain ------------------------------------------------------------------------------


def drop(rng, f, decay):
    """A tiny resonant tap: a decaying sine with a soft noise click."""
    n = secs(decay * 6)
    t = times(n)
    ping = np.sin(2 * np.pi * f * (1 + 0.15 * t / (decay * 6)) * t) * np.exp(-t / decay)
    click = rng.standard_normal(n) * np.exp(-t / 0.0015)
    return (ping + 0.3 * click) * ramp_in(n, 3)


def rain(rng, length=40.0):
    """Soft steady rain: a warm pink wash that breathes slowly, fine patter on leaves,
    and the occasional heavier drop close by."""
    loop_n = secs(length)
    wash = shaped_noise(loop_n, rng, lambda f: f**-0.5 / (1 + (f / 3500) ** 3)
                        / (1 + (120 / f) ** 2), 2)
    wash *= np.clip(1 + 0.12 * smooth_random(loop_n, rng, 0.08), 0.5, None)[:, None]
    body = shaped_noise(loop_n, rng, lambda f: 1 / (1 + (f / 180) ** 2) / f, 2)
    patter = np.zeros((loop_n + secs(0.5), 2))
    for _ in range(int(55 * length)):
        f = np.exp(rng.uniform(np.log(1200), np.log(4000)))
        x = drop(rng, f, rng.uniform(0.002, 0.006)) * rng.lognormal(-1.5, 0.6)
        place(patter, pan(x, rng.uniform(-1, 1)), int(rng.integers(loop_n)))
    for _ in range(int(2.5 * length)):
        f = np.exp(rng.uniform(np.log(450), np.log(1300)))
        x = lowpass(drop(rng, f, rng.uniform(0.008, 0.02)), 3000) * rng.lognormal(-0.6, 0.4)
        place(patter, pan(x, rng.uniform(-0.9, 0.9)), int(rng.integers(loop_n)))
    patter = wrap(patter, loop_n)
    patter = circular(lambda y: lowpass(y, 5000, 2), patter)
    return 0.3 * wash + 0.12 * body + 0.08 * patter


# --- water -----------------------------------------------------------------------------


def bubble(rng, f0):
    """One trickle bubble: a sine whose pitch rises as it decays (Minnaert-style)."""
    decay = np.clip(0.9 / f0**0.75, 0.004, 0.03)
    n = secs(decay * 5)
    t = times(n)
    freq = f0 * (1 + rng.uniform(0.5, 1.5) * t / (decay * 5))
    return np.sin(phase_of(freq)) * np.exp(-t / decay) * ramp_in(n, 4)


def water(rng, length=40.0):
    """A small brook at the pond's edge: clusters of trickling bubbles, slow soft laps
    against the bank, and a low murmur underneath."""
    loop_n = secs(length)
    density = np.exp(1.1 * smooth_random(loop_n, rng, 0.4))
    density /= density.mean()
    trickle = np.zeros((loop_n + secs(0.2), 2))
    count = int(28 * length)
    starts = rng.choice(loop_n, count, p=density / density.sum())
    for at in starts:
        f0 = np.exp(rng.uniform(np.log(380), np.log(1600)))
        level = rng.lognormal(-1.2, 0.5) * (500 / f0) ** 0.3
        place(trickle, pan(bubble(rng, f0) * level, rng.uniform(-0.6, 0.6)), int(at))
    trickle = wrap(trickle, loop_n)
    laps = np.zeros((loop_n + secs(1.5), 2))
    t = rng.uniform(0, 1)
    while t < length:
        dur = rng.uniform(0.6, 1.2)
        n = secs(dur)
        env = np.sin(np.pi * np.minimum(times(n) / (0.35 * dur), 1) / 2) * np.exp(
            -np.clip(times(n) - 0.35 * dur, 0, None) / (0.25 * dur))
        x = bandpass(rng.standard_normal(n), 150, rng.uniform(500, 900)) * env
        place(laps, pan(x * rng.uniform(0.5, 1.0), rng.uniform(-0.5, 0.5)), secs(t))
        t += rng.uniform(1.8, 3.8)
    laps = wrap(laps, loop_n)
    murmur = shaped_noise(loop_n, rng, lambda f: np.exp(-((np.log(f / 400) / 0.7) ** 2)), 2)
    murmur *= np.clip(1 + 0.3 * smooth_random(loop_n, rng, 0.3), 0.3, None)[:, None]
    mix = 0.5 * trickle + 0.25 * laps + 0.05 * murmur
    ir = impulse_response(rng, 1.0, 0.6, 0.35, predelay=0.008)
    out = wrap(with_reverb(mix, mix, ir, 0.25), loop_n)
    return circular(lambda y: highpass(y, 60, 2), out)
