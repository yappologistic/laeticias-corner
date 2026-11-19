"""Ambience beds: birds, crickets, rain and water. Each is a seamless stereo loop: beds
are periodic noise built in the frequency domain, events are scattered over the loop
and their tails folded back onto its start."""

import numpy as np
from scipy import signal

from dsp import (SR, bandpass, circular, glide, gust_curve, highpass, impulse_response, line,
                 lowpass, pan, phase_of, place, ramp_in, secs, shaped_noise, smooth_random,
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
    irregular intervals (no two calls rendered alike), over a floor that never drops out: a
    chorus of many birds far off in the hedges and trees, and leaves stirring in a light breeze
    (the bed used to fall to near silence between calls, a 10 LU range, and read as the quiet
    spot of the home's day)."""
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
        t += len(call) / SR + rng.uniform(1.0, 3.5)
        last = pick
    # The far chorus: many small voices from every side, dull with distance, mostly reverb.
    t = 0.0
    while t < length:
        song, _, (lo, hi), _ = BIRDS[int(rng.integers(4))]
        call = song(rng, rng.uniform(lo, hi))
        call = lowpass(call, 3200, 2) * rng.uniform(0.2, 0.35)
        x = pan(call, rng.uniform(-1, 1))
        place(dry, 0.3 * x, secs(t))
        place(send, x, secs(t))
        t += rng.exponential(0.3)
    ir = impulse_response(rng, 2.0, 1.2, 0.6, predelay=0.02)
    out = wrap(with_reverb(dry, send, ir, 0.5), loop_n)
    breeze = shaped_noise(loop_n, rng, lambda f: 1 / (1 + (f / 350) ** 2) / np.sqrt(f), 2)
    sway = gust_curve(loop_n, rng, 0.12, 0.5)
    leaves = shaped_noise(loop_n, rng, lambda f: (f / 900) / (1 + (f / 900) ** 2.5), 2)
    stir = gust_curve(loop_n, rng, 0.2, 0.8) ** 1.5
    return (out + 0.03 * breeze * sway[:, None]
            + 0.016 * leaves * (stir / stir.mean())[:, None])


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


# --- seasonal and night beds -----------------------------------------------------------


def scatter(rng, length, voices, gaps, spread=0.8):
    """Calls from `voices` [(song, pitch_hz, distance 0..1)] at random gaps over a loop,
    as dry and reverb-send buffers; the caller wraps the tails."""
    dry = np.zeros((secs(length + 6), 2))
    send = np.zeros_like(dry)
    t = rng.uniform(0, gaps[0])
    while t < length:
        song, f, dist = voices[int(rng.integers(len(voices)))]
        call = song(rng, f * rng.uniform(0.96, 1.04))
        call = lowpass(call, 7500 - 5000 * dist, 2) * (1 - 0.7 * dist) * rng.uniform(0.75, 1.0)
        x = pan(call, rng.uniform(-spread, spread))
        place(dry, x, secs(t))
        place(send, x * (0.3 + 0.7 * dist), secs(t))
        t += len(call) / SR + rng.uniform(*gaps)
    return dry, send


def crackle(n, rng, rate, lo, hi, grain=0.004):
    """Dry-leaf rustle for a loop: band-limited periodic noise gated by a sparse train of
    tiny random hits whose rate (per second) follows the curve `rate`."""
    hits = (rng.random(n) < rate / SR) * rng.lognormal(0, 0.4, n)
    win = np.exp(-np.arange(secs(grain * 5)) / secs(grain))
    env = wrap(signal.oaconvolve(hits, win), n)
    noise = shaped_noise(n, rng, lambda f: 1 / (1 + (lo / f) ** 4) / (1 + (f / hi) ** 4))
    return noise * env


def wind(n, rng, low, high, gust_hz, depth, channels=2):
    """Periodic wind: band-limited noise that swells and falls with slow random gusts."""
    air = shaped_noise(n, rng, lambda f: f**-0.5 / (1 + (low / f) ** 4) / (1 + (f / high) ** 2),
                       channels)
    gusts = gust_curve(n, rng, gust_hz, depth)
    return air * (gusts[:, None] if channels == 2 else gusts), gusts


def skitter(rng):
    """A single dry leaf tumbling a short way across the ground: irregular tiny scrapes."""
    out = np.zeros(secs(1.0))
    at = 0.0
    for k in range(int(rng.integers(6, 12))):
        g = secs(rng.uniform(0.008, 0.022))
        grain = bandpass(rng.standard_normal(g), 1800, 5500) * np.hanning(g)
        place(out, grain * rng.uniform(0.4, 1.0) * (1 - 0.05 * k), secs(at))
        at += rng.uniform(0.03, 0.09)
    return out


def autumn(rng, length=60.0):
    """Autumn day: wind moving through drying leaves in slow gusts, the rustle crisp and
    following each gust, a few distant birds, now and then a leaf skittering past."""
    n = secs(length)
    air, gusts = wind(n, rng, 120, 900, 0.06, 0.6)
    leaves = np.stack([crackle(n, rng, 40 * gusts**2, 1400, 4500) for _ in range(2)], axis=1)
    voices = [(whistle, 2900, 0.7), (chips, 4400, 0.6), (coo, 480, 0.85), (carol, 2400, 0.75)]
    dry, send = scatter(rng, length, voices, (5.0, 11.0))
    for _ in range(5):
        x = pan(skitter(rng) * rng.uniform(0.15, 0.3), rng.uniform(-0.7, 0.7))
        place(dry, x, secs(rng.uniform(0, length)))
    ir = impulse_response(rng, 2.0, 1.2, 0.6, predelay=0.02)
    calls = wrap(with_reverb(dry, send, ir, 0.5), n)
    out = 0.05 * air + 0.5 * leaves + calls
    return circular(lambda y: lowpass(highpass(y, 60, 2), 6000, 4), out)


def winter(rng, length=60.0):
    """Winter day (also the snow bed): a soft, cold wind with a faint hollow whistle,
    sparse small-bird calls far off, everything muffled as if by snow."""
    n = secs(length)
    air, gusts = wind(n, rng, 150, 1400, 0.05, 0.5)
    whistle_band = shaped_noise(n, rng, lambda f: np.exp(-((f - 750) / 60) ** 2), 2)
    whistle_band *= (np.clip(gusts - 1.0, 0, None) ** 2)[:, None]
    voices = [(chips, 4300, 0.65), (chips, 3800, 0.75), (whistle, 3000, 0.8)]
    dry, send = scatter(rng, length, voices, (7.0, 15.0))
    ir = impulse_response(rng, 2.5, 1.4, 0.5, predelay=0.03)
    calls = wrap(with_reverb(dry, send, ir, 0.6), n)
    out = 0.06 * air + 0.004 * whistle_band + 0.8 * calls
    return circular(lambda y: lowpass(highpass(y, 60, 2), 5000, 2), out)


def tree_frog(rng, f):
    """A tree frog's bout: a run of short buzzy 'krek' notes."""
    parts = []
    for _ in range(int(rng.integers(5, 11))):
        n = secs(rng.uniform(0.025, 0.035))
        t = times(n)
        buzz = (0.5 + 0.5 * np.sin(2 * np.pi * 160 * t)) ** 2
        parts.append((tone(np.full(n, f * rng.uniform(0.98, 1.02)), buzz * arch(n, 0.8), 0.2),
                      rng.uniform(0.11, 0.16)))
    return concat(parts)


def night_spring(rng, length=60.0):
    """Spring night: a light breeze and, very far off, a few tree frogs calling in bouts,
    answering one another; no crickets yet."""
    n = secs(length)
    air, _ = wind(n, rng, 80, 600, 0.05, 0.4)
    voices = [(tree_frog, f, d) for f, d in ((1900, 0.85), (2150, 0.9), (1750, 0.9), (2300, 0.95))]
    dry, send = scatter(rng, length, voices, (0.8, 3.5), spread=0.9)
    ir = impulse_response(rng, 3.0, 1.8, 0.8, predelay=0.03)
    frogs = wrap(with_reverb(dry, send, ir, 0.7), n)
    out = 0.05 * air + 0.5 * frogs
    return circular(lambda y: lowpass(highpass(y, 50, 2), 5000, 2), out)


def creak(rng):
    """A bare branch creaking in the cold: stick-slip pulses of slowly changing rate
    ringing the wood's resonances."""
    dur = rng.uniform(0.5, 1.0)
    n = secs(dur)
    rate = glide(n, [(0, rng.uniform(35, 55)), (dur * 0.5, rng.uniform(70, 110)),
                     (dur, rng.uniform(40, 60))])
    cycle = np.cumsum(rate) / SR
    hits = np.diff(np.floor(cycle), prepend=0.0) * rng.lognormal(0, 0.3, n)
    m = secs(0.04)
    tm = times(m)
    body = sum(a * np.sin(2 * np.pi * f * tm) * np.exp(-tm / d)
               for f, a, d in ((420, 1.0, 0.012), (760, 0.7, 0.009), (1180, 0.4, 0.006),
                               (1750, 0.2, 0.004)))
    return signal.oaconvolve(hits, body)[:n] * arch(n, 0.7)


def night_winter(rng, length=60.0):
    """Winter night: near silence. A faint low wind, and once in a while a branch
    creaking somewhere in the cold."""
    n = secs(length)
    air, _ = wind(n, rng, 70, 450, 0.04, 0.6)
    dry = np.zeros((n + secs(4), 2))
    send = np.zeros_like(dry)
    for k in range(4):
        x = pan(creak(rng) * rng.uniform(0.5, 1.0), rng.uniform(-0.7, 0.7))
        at = secs(length * (k + rng.uniform(0.1, 0.8)) / 4)
        place(dry, x, at)
        place(send, x, at)
    ir = impulse_response(rng, 2.5, 1.5, 0.6, predelay=0.03)
    creaks = wrap(with_reverb(dry, send, ir, 0.6), n)
    out = 0.06 * air + 0.06 * creaks
    return circular(lambda y: lowpass(highpass(y, 45, 2), 4000, 2), out)


def waterfall(rng, length=32.0):
    """A small waterfall close by: a steady broad fall with a slow surge, dense bright
    splashing where it lands, and no rumble below 80 Hz."""
    n = secs(length)
    fall = shaped_noise(n, rng, lambda f: f**-0.3 / (1 + (f / 3000) ** 2) / (1 + (250 / f) ** 2),
                        2)
    fall *= np.clip(1 + 0.08 * smooth_random(n, rng, 0.3), 0.5, None)[:, None]
    splash = np.zeros((n + secs(0.2), 2))
    for _ in range(int(90 * length)):
        f0 = np.exp(rng.uniform(np.log(500), np.log(2500)))
        x = bubble(rng, f0) * rng.lognormal(-1.6, 0.6) * (600 / f0) ** 0.3
        place(splash, pan(x, rng.uniform(-0.8, 0.8)), int(rng.integers(n)))
    splash = wrap(splash, n)
    spray = np.stack([crackle(n, rng, np.full(n, 300.0), 1500, 6000, 0.002) for _ in range(2)],
                     axis=1)
    out = 0.3 * fall + 0.25 * splash + 0.1 * spray
    ir = impulse_response(rng, 0.8, 0.5, 0.3, predelay=0.006)
    out = wrap(with_reverb(out, out, ir, 0.2), n)
    return circular(lambda y: lowpass(highpass(y, 80, 4), 7000, 4), out)
