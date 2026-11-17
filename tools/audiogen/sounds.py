"""Building blocks for the city and world beds and effects: distant wordless voices, animals
and birds, struck stone and metal, steps, hooves and wheels, water, fire, insects and
working machines. Everything is mono unless stated, starts at silence and stays under
CEILING. Loop helpers fold events past the end back onto the start."""

import numpy as np
from scipy import signal

from dsp import (SR, bandpass, circular, glide, highpass, impulse_response, line, lowpass, pan, perc,
                 phase_of, place, ramp_in, secs, shaped_noise, smooth_random, times, voice,
                 with_reverb, wobble, wrap)

CEILING = 7500.0

# --- loop assembly ---------------------------------------------------------------------


class Bed:
    """A stereo loop under construction: dry and reverb-send buffers with room for tails,
    events placed at any time (wrapped modulo the loop), finished through one room."""

    def __init__(self, length, rng, tail=20.0):
        self.n = secs(length)
        self.rng = rng
        self.dry = np.zeros((self.n + secs(tail), 2))
        self.send = np.zeros_like(self.dry)

    def add(self, x, at, position=0.0, dist=0.3, level=1.0):
        """Mix a mono (or stereo) event at time `at` (s, wrapped), farther = duller, quieter
        and wetter."""
        x = lowpass(x, CEILING - 5000 * dist, 2) * level * (1 - 0.6 * dist)
        x = pan(x, position) if x.ndim == 1 else x
        k = secs(at) % self.n
        assert k + len(x) <= len(self.dry), "event longer than the bed's tail room"
        place(self.dry, x, k)
        place(self.send, x * (0.2 + 0.8 * dist), k)

    @staticmethod
    def wet(x, rng, room, wet):
        """Put an already-looping stereo signal into a room, its tail folded onto the start."""
        ir = impulse_response(rng, room[0], room[1], room[2], predelay=room[3])
        return wrap(with_reverb(x, x, ir, wet), len(x))

    def scatter(self, make, count, spread=0.8, dist=(0.3, 0.9), level=(0.6, 1.0)):
        """`count` events from make(rng) at random times, places and distances."""
        for _ in range(count):
            d = self.rng.uniform(*dist)
            self.add(make(self.rng), self.rng.uniform(0, self.n / SR),
                     self.rng.uniform(-spread, spread), d, self.rng.uniform(*level))

    def finish(self, room=(2.0, 1.4, 0.6, 0.02), wet=0.5):
        ir = impulse_response(self.rng, room[0], room[1], room[2], predelay=room[3])
        out = wrap(with_reverb(self.dry, self.send, ir, wet), self.n)
        return circular(lambda y: highpass(y, 30, 2), out)  # bubbles and knocks carry DC


def loop_lowpass(x, freq):
    """Low-pass a whole loop as if it had been playing forever (no click at the seam)."""
    return circular(lambda y: lowpass(y, freq, 2), x)


def loop_noise(n, rng, lo, hi, tilt=0.5, channels=2):
    """Periodic band-limited noise (spectrum f^-tilt between lo and hi)."""
    return shaped_noise(n, rng, lambda f: f**-tilt / (1 + (lo / f) ** 4) / (1 + (f / hi) ** 4),
                        channels)


def swell(n, rng, rate, depth, floor=0.1):
    """A periodic slow level curve around 1 (gusts, waves of cicadas, crowd surges)."""
    return np.clip(1 + depth * smooth_random(n, rng, rate), floor, None)


def wind(n, rng, lo=120.0, hi=1800.0, gust=0.08, depth=0.5, whistle=0.0):
    """Wind over open ground or stone: gusting noise whose colour brightens in the gusts;
    `whistle` adds a faint hollow tone where it passes edges."""
    g = swell(n, rng, gust, depth, 0.15)
    low = loop_noise(n, rng, lo, hi * 0.5, 0.6)
    high = loop_noise(n, rng, hi * 0.4, hi * 1.5, 0.6)
    out = low * g[:, None] + 0.5 * high * (g**2)[:, None]
    if whistle:
        tone = shaped_noise(n, rng, lambda f: np.exp(-(((f - 700) / 25) ** 2)), 2)
        out += whistle * tone * (g**3)[:, None]
    return out


# --- distant voices --------------------------------------------------------------------

VOWELS = ((750, 1250), (550, 1750), (400, 2000), (300, 2300), (500, 900), (350, 800), (650, 1100))


def babble(dur, rng, f0=150.0, rate=4.5, ceiling=2500.0, calling=False):
    """One far-off talker with no words: syllables gliding between random vowel shapes on a
    falling phrase melody, in phrases with pauses. `calling` makes a long sung-out cry (a
    hawker or a herald far away)."""
    n = secs(dur)
    t = times(n)
    # Syllable grid with vowel targets; phrases gate it.
    k = int(dur * rate) + 2
    centres = np.cumsum(rng.uniform(0.6, 1.4, k) / rate)
    f1 = np.interp(t, centres, [VOWELS[i][0] for i in rng.integers(len(VOWELS), size=k)])
    f2 = np.interp(t, centres, [VOWELS[i][1] for i in rng.integers(len(VOWELS), size=k)])
    syll = 0.5 - 0.5 * np.cos(2 * np.pi * np.interp(t, centres, np.arange(k)))
    gate = np.zeros(n)
    at = rng.uniform(0, 0.5)
    while at < dur:
        length = rng.uniform(0.8, 2.6) if not calling else rng.uniform(1.0, 1.8)
        a, b = secs(at), min(n, secs(at + length))
        if b > a:
            gate[a:b] = np.sin(np.pi * np.arange(b - a) / (b - a)) ** 0.3
        at += length + rng.uniform(0.3, 1.6)
    gate = lowpass(gate, 20, 2)
    knots = np.arange(0, dur + 3, 2.0)
    phrase = np.interp(t, knots, rng.uniform(1.0, 1.25, len(knots)))
    pitch = f0 * phrase * (1 + 0.08 * smooth_random(n, rng, 3.0) / 3)
    if calling:
        pitch = f0 * 1.6 * (1 + 0.02 * np.sin(2 * np.pi * 5 * t))
        syll = 0.7 + 0.3 * syll
    ph = phase_of(pitch * wobble(n, rng, 0.004, 30))
    out = np.zeros(n)
    for h in range(1, 24):
        fh = h * pitch
        if fh.min() > ceiling:
            break
        amp = (h**-1.2) * (1 / (1 + ((fh - f1) / 90) ** 2) + 0.5 / (1 + ((fh - f2) / 150) ** 2)
                           + 0.03)
        out += amp * np.sin(h * ph)
    out = lowpass(out * syll * gate, ceiling, 2)
    return out * ramp_in(n, secs(0.05)) * ramp_in(n, secs(0.05))[::-1]


def crowd(length, rng, talkers, f0=(110, 240), ceiling=1800.0, spread=0.8, calling=0):
    """Many far talkers as a seamless stereo murmur (each talker's overrun folded back)."""
    n = secs(length)
    out = np.zeros((n, 2))
    for i in range(talkers + calling):
        x = babble(length + 3, rng, rng.uniform(*f0), rng.uniform(3.5, 5.5), ceiling,
                   calling=i >= talkers)
        x = pan(x * rng.uniform(0.5, 1.0), rng.uniform(-spread, spread))
        buf = np.zeros((n + len(x), 2))
        place(buf, x, secs(rng.uniform(0, length)))
        out += wrap(buf, n)
    return out


def song(notes, rng, f0_scale=1.0, voices=3, vowel="a"):
    """A few voices singing a tune on an open vowel, heard far off through walls: no words.
    `notes` is [(start_s, dur_s, hz)]."""
    end = max(s + d for s, d, _ in notes) + 0.5
    n = secs(end)
    formants = {"a": [(700, 130, 1.0), (1150, 160, 0.5), (2600, 300, 0.1)],
                "o": [(450, 110, 1.0), (850, 150, 0.45), (2500, 300, 0.06)]}[vowel]
    out = np.zeros(n)
    for v in range(voices):
        pitch = np.full(n, notes[0][2])
        env = np.zeros(n)
        for s, d, hz in notes:
            a, b = secs(s + rng.normal(0, 0.02)), secs(s + d)
            a = max(0, a)
            pitch[a:] = hz * f0_scale * (1 + rng.normal(0, 0.004))
            m = max(1, b - a)
            env[a:b] = np.minimum(1, np.arange(m) / secs(0.08)) * np.minimum(
                1, (m - np.arange(m)) / secs(0.1))
        pitch = lowpass(pitch, 12, 1)
        out += voice(pitch, formants, rng, tilt=1.3, jitter=0.004, shimmer=0.06,
                     breath=0.08) * lowpass(env, 30, 2)
    return out / voices


# --- animals and birds -----------------------------------------------------------------


def chirp(f_start, f_end, dur, harm=0.08):
    n = secs(dur)
    ph = phase_of(glide(n, [(0, f_start), (dur, f_end)]))
    return (np.sin(ph) + harm * np.sin(2 * ph)) * np.sin(np.pi * np.arange(n) / n) ** 0.8


def string_of(parts):
    """Join (signal, gap_s) pairs."""
    out = []
    for x, gap in parts:
        out += [x, np.zeros(secs(gap))]
    return np.concatenate(out)


def swallow(rng):
    """Barn swallow twitter: a quick run of liquid chirps and a buzzy rattle."""
    parts = []
    for _ in range(int(rng.integers(6, 14))):
        a = rng.uniform(2500, 4800)
        parts.append((chirp(a, a * rng.uniform(0.7, 1.3), rng.uniform(0.02, 0.06)),
                      rng.uniform(0.01, 0.05)))
    if rng.random() < 0.5:
        n = secs(0.25)
        rattle = chirp(3200, 3000, 0.25) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 45 * times(n))))
        parts.append((lowpass(rattle, 5000), 0.0))
    return string_of(parts)


def swift(rng):
    """A swift's thin scream, softened: a fast trill sliding down, far overhead."""
    dur = rng.uniform(0.4, 0.8)
    n = secs(dur)
    f = glide(n, [(0, rng.uniform(4300, 5200)), (dur, rng.uniform(3300, 3900))])
    am = 0.55 + 0.45 * np.sin(2 * np.pi * rng.uniform(60, 80) * times(n))
    return lowpass(np.sin(phase_of(f)) * am * np.sin(np.pi * np.arange(n) / n) ** 0.5, 5500)


def hoopoe(rng):
    """Hoopoe: a soft, hollow 'hoo-poo-poo', three low notes close together."""
    f = rng.uniform(380, 440)
    parts = []
    for _ in range(3):
        n = secs(0.11)
        x = np.sin(phase_of(glide(n, [(0, f * 0.97), (0.05, f), (0.11, f * 0.96)])))
        parts.append((x * np.sin(np.pi * np.arange(n) / n) ** 1.2, 0.07))
    return lowpass(string_of(parts), 1500)


def scops_owl(rng):
    """Scops owl: one short soft whistled 'tyuu', the patient metronome of a warm night."""
    n = secs(0.3)
    f = rng.uniform(1150, 1250)
    x = np.sin(phase_of(glide(n, [(0, f * 0.96), (0.06, f), (0.3, f * 0.98)])))
    return x * ramp_in(n, secs(0.03)) * np.exp(-np.clip(times(n) - 0.12, 0, None) / 0.07)


def little_owl(rng):
    """Little owl: a plaintive rising-then-falling 'kee-ew'."""
    dur = 0.45
    n = secs(dur)
    f = glide(n, [(0, 1250), (0.12, 1650), (dur, 1150)]) * rng.uniform(0.95, 1.05)
    ph = phase_of(f)
    x = np.sin(ph) + 0.25 * np.sin(2 * ph)
    return lowpass(x * np.sin(np.pi * np.arange(n) / n) ** 0.7, 4000)


def kestrel(rng):
    """Kestrel: a quick ringing 'kee-kee-kee-kee'."""
    parts = []
    for _ in range(int(rng.integers(4, 8))):
        parts.append((chirp(3000, 2700, 0.08, 0.2), 0.06))
    return lowpass(string_of(parts), 5000)


def gull(rng):
    """Gull: a laughing 'kyow' with a raw voiced edge."""
    dur = rng.uniform(0.35, 0.6)
    n = secs(dur)
    f0 = glide(n, [(0, 900), (0.08, 1300), (dur, 750)]) * rng.uniform(0.9, 1.1)
    form = [(1700, 500, 1.0), (3200, 700, 0.4)]
    return lowpass(voice(f0, form, rng, tilt=0.6, jitter=0.01, shimmer=0.1, breath=0.15)
                   * np.sin(np.pi * np.arange(n) / n) ** 0.5, 5000)


def lark(rng, dur=2.5):
    """Skylark high up: an unbroken rush of tiny warbled notes."""
    parts, t = [], 0.0
    while t < dur:
        a = rng.uniform(2600, 4600)
        d = rng.uniform(0.03, 0.09)
        parts.append((chirp(a, a * rng.uniform(0.8, 1.25), d, 0.05) * rng.uniform(0.4, 1), 0.012))
        t += d + 0.012
    return lowpass(string_of(parts), 6000)


def raven(rng):
    """Raven: a deep hollow 'kronk'."""
    dur = 0.32
    n = secs(dur)
    f0 = glide(n, [(0, 330), (0.1, 380), (dur, 300)])
    return lowpass(voice(f0, [(900, 300, 1.0), (1500, 400, 0.6)], rng, tilt=0.8, jitter=0.02,
                         shimmer=0.15, sub=0.3) * np.sin(np.pi * np.arange(n) / n) ** 0.5, 3500)


def pigeon(rng):
    """Rock dove: a soft rolling 'oo-roo-coo'."""
    parts = []
    for dur, f in ((0.25, 360), (0.45, 400), (0.3, 340)):
        n = secs(dur)
        am = 0.75 + 0.25 * np.sin(2 * np.pi * 22 * times(n))
        x = np.sin(phase_of(glide(n, [(0, f * 0.95), (dur * 0.4, f), (dur, f * 0.9)])))
        parts.append((x * am * np.sin(np.pi * np.arange(n) / n), 0.05))
    return lowpass(string_of(parts), 1500)


def wingbeats(rng, count=8, rate=9.0):
    """A bird taking off: a few soft whooshing wingbeats."""
    out = np.zeros(secs(count / rate + 0.3))
    for i in range(count):
        n = secs(0.07)
        w = bandpass(rng.standard_normal(n), 400, 2500) * np.hanning(n)
        place(out, w * (1 - 0.5 * i / count), secs(i / rate))
    return out


def ox(rng):
    """An ox lowing far off: a long low moan opening from 'mm' to 'oo'."""
    dur = rng.uniform(1.4, 2.0)
    n = secs(dur)
    f0 = glide(n, [(0, 95), (0.4, 115), (dur, 85)]) * rng.uniform(0.9, 1.1)
    f1 = line(n, [(0, 300), (0.6, 520), (dur, 380)])
    form = [(f1, 160, 1.0), (1000, 300, 0.25)]
    x = voice(f0, form, rng, tilt=1.0, jitter=0.006, shimmer=0.08, breath=0.1, sub=0.15)
    return lowpass(x * np.sin(np.pi * np.arange(n) / n) ** 0.6, 2500)


def snort(rng):
    """A horse's snort: a fluttering blast of air through the nostrils."""
    dur = rng.uniform(0.35, 0.55)
    n = secs(dur)
    flutter = 0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(28, 40) * times(n)) ** 2
    x = bandpass(rng.standard_normal(n), 250, 2200) * flutter * perc(n, 0.02, dur / 3)
    return lowpass(x, 3000)


def camel(rng):
    """A camel's groan: a deep gargled growl that rises and sinks."""
    dur = rng.uniform(1.0, 1.5)
    n = secs(dur)
    f0 = glide(n, [(0, 70), (0.35, 110), (dur, 65)]) * rng.uniform(0.9, 1.1)
    gargle = 1 + 0.4 * np.sin(2 * np.pi * 14 * times(n)) * wobble(n, rng, 0.3, 10)
    x = voice(f0, [(500, 250, 1.0), (1100, 300, 0.5), (2300, 400, 0.15)], rng, tilt=0.7,
              jitter=0.03, shimmer=0.25, breath=0.35, sub=0.6) * gargle
    return lowpass(x * np.sin(np.pi * np.arange(n) / n) ** 0.4, 3000)


def donkey(rng):
    """A donkey's bray: wheezing in on a high note, honking out on a low one, a few times."""
    parts = []
    for _ in range(int(rng.integers(3, 5))):
        for f, dur, br in ((rng.uniform(700, 850), 0.28, 0.6), (rng.uniform(220, 260), 0.38, 0.2)):
            n = secs(dur)
            f0 = glide(n, [(0, f * 0.9), (dur * 0.3, f), (dur, f * 0.85)])
            x = voice(f0, [(900, 300, 1.0), (1700, 400, 0.4)], rng, tilt=0.6, jitter=0.02,
                      shimmer=0.2, breath=br, sub=0.3)
            parts.append((x * np.sin(np.pi * np.arange(n) / n) ** 0.5, 0.02))
    return lowpass(string_of(parts), 3500)


def dog(rng, barks=2):
    """A dog barking a couple of times, somewhere across town."""
    parts = []
    for _ in range(barks):
        dur = rng.uniform(0.14, 0.2)
        n = secs(dur)
        f0 = glide(n, [(0, 380), (0.03, 520), (dur, 330)]) * rng.uniform(0.85, 1.15)
        x = voice(f0, [(800, 300, 1.0), (1600, 400, 0.6)], rng, tilt=0.7, jitter=0.02,
                  shimmer=0.2, breath=0.4, sub=0.2)
        parts.append((x * perc(n, 0.008, dur / 2.5), rng.uniform(0.18, 0.35)))
    return lowpass(string_of(parts), 3500)


def goat_bleat(rng):
    """A goat's quavering bleat."""
    dur = rng.uniform(0.5, 0.8)
    n = secs(dur)
    f0 = glide(n, [(0, 330), (0.1, 420), (dur, 360)]) * (1 + 0.06 * np.sin(2 * np.pi * 9 * times(n)))
    x = voice(f0, [(700, 250, 1.0), (1500, 350, 0.5), (2600, 400, 0.15)], rng, tilt=0.8,
              jitter=0.02, shimmer=0.15, breath=0.2)
    return lowpass(x * np.sin(np.pi * np.arange(n) / n) ** 0.5, 4000)


def cricket(rng, carrier=4200.0, pulses=4):
    """One field-cricket chirp."""
    parts = []
    for i in range(pulses):
        n = secs(0.016)
        x = np.sin(phase_of(glide(n, [(0, carrier * 1.01), (0.016, carrier * 0.99)])))
        parts.append((x * np.sin(np.pi * np.arange(n) / n) ** 1.5, 0.017))
    return string_of(parts)


def crickets(bed, count=5, length=None, level=0.5):
    """A few crickets, each at its own steady rate (a divisor of the loop), with rests."""
    length = length or bed.n / SR
    for _ in range(count):
        carrier = bed.rng.uniform(3600, 4700)
        chirps = int(bed.rng.integers(50, 90))
        period = length / chirps
        pos, dist = bed.rng.uniform(-0.9, 0.9), bed.rng.uniform(0.2, 0.9)
        awake = smooth_random(bed.n, bed.rng, 0.06)
        cut = bed.rng.uniform(-1.0, -0.2)
        pulses = int(bed.rng.integers(3, 5))
        for k in range(chirps):
            t = k * period + bed.rng.normal(0, 0.004)
            a = awake[secs(t) % bed.n] - cut
            if a > 0:
                bed.add(cricket(bed.rng, carrier, pulses), t, pos, dist, min(1, 2 * a) * level)


def cicada(rng, dur):
    """One cicada's song: tymbal clicks at a fast pulse rate exciting a resonance near
    5 kHz, ramping up, holding, then winding down; softened to sit under 7.5 kHz."""
    n = secs(dur)
    t = times(n)
    rate = rng.uniform(140, 220)
    clicks = (0.5 + 0.5 * np.sin(2 * np.pi * rate * t)) ** 6
    carrier = bandpass(rng.standard_normal(n), rng.uniform(4300, 4900), rng.uniform(5600, 6400), 3)
    env = np.minimum(1, t / rng.uniform(1.0, 2.5)) * np.minimum(1, (dur - t) / rng.uniform(0.8, 2.0))
    env *= 1 + 0.25 * np.sin(2 * np.pi * rng.uniform(0.3, 0.8) * t)
    return lowpass(carrier * (0.25 + clicks) * np.clip(env, 0, None), 7000, 4)


def cicadas(bed, count, level=1.0, dist=(0.3, 0.95)):
    """A wall of cicadas: overlapping songs that come and go in waves."""
    for _ in range(count):
        dur = bed.rng.uniform(6, 16)
        bed.add(cicada(bed.rng, dur), bed.rng.uniform(0, bed.n / SR), bed.rng.uniform(-0.9, 0.9),
                bed.rng.uniform(*dist), bed.rng.uniform(0.5, 1.0) * level)


# --- struck things ---------------------------------------------------------------------


def modes(n, freqs, amps, decays, rng):
    t = times(n)
    out = np.zeros(n)
    for f, a, d in zip(freqs, amps, decays):
        if f < CEILING:
            out += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.3)) * np.exp(-t / d)
    return out * ramp_in(n, secs(0.0006))


def chisel(rng):
    """A mallet on an iron chisel biting stone: the chisel rings briefly, chips spit."""
    n = secs(0.25)
    f = rng.uniform(2300, 2900)
    ring = modes(n, [f, f * 1.52, f * 2.21], [1.0, 0.5, 0.25], [0.05, 0.03, 0.015], rng)
    thock = modes(n, [rng.uniform(500, 700), 1250], [0.6, 0.3], [0.02, 0.01], rng)
    grit = bandpass(rng.standard_normal(n), 1500, 6000) * perc(n, 0.0005, 0.01)
    return lowpass(0.5 * ring + thock + 0.6 * grit, CEILING)


def wedge(rng):
    """A heavy mallet driving an iron wedge into a split: dull blow, low ring."""
    n = secs(0.4)
    f = rng.uniform(950, 1200)
    ring = modes(n, [f, f * 2.3, f * 3.6], [1.0, 0.4, 0.15], [0.09, 0.04, 0.02], rng)
    blow = modes(n, [140, 260], [1.0, 0.5], [0.04, 0.03], rng)
    grit = bandpass(rng.standard_normal(n), 800, 4000) * perc(n, 0.001, 0.02)
    return lowpass(0.4 * ring + blow + 0.4 * grit, 6000)


def hammer_stone(rng):
    """A hammer dressing a stone block: a hard, short knock with a grainy edge."""
    n = secs(0.18)
    f = rng.uniform(900, 1400)
    knock = modes(n, [f, f * 1.7, f * 2.6], [1.0, 0.6, 0.3], [0.02, 0.012, 0.008], rng)
    body = modes(n, [180, 320], [0.6, 0.3], [0.03, 0.02], rng)
    grit = bandpass(rng.standard_normal(n), 1500, 6000) * perc(n, 0.0005, 0.008)
    return lowpass(knock + body + 0.5 * grit, CEILING)


def anvil(rng):
    """A smith's hammer on a small anvil: a bright, ringing clang."""
    n = secs(0.9)
    f = rng.uniform(1500, 1700)
    ring = modes(n, [f, f * 1.48, f * 2.06, f * 2.9, f * 3.7], [1.0, 0.7, 0.45, 0.3, 0.15],
                 [0.35, 0.25, 0.15, 0.08, 0.05], rng)
    hit = bandpass(rng.standard_normal(n), 2000, 6000) * perc(n, 0.0003, 0.004)
    return lowpass(ring + 0.4 * hit, CEILING)


def bell(freq, rng, ring=1.2, kind="crotal"):
    """Small animal bells. 'crotal': a cast closed jingle bell (horse, camel), warm and
    ringing; 'sheet': a hammered iron bell (goat, sheep), hollow and clanky."""
    n = secs(ring * 2.5)
    if kind == "crotal":
        ratios, amps, taus = (1, 2.04, 2.76, 3.9), (1.0, 0.5, 0.25, 0.12), (1.0, 0.5, 0.3, 0.18)
    else:
        ratios, amps, taus = (1, 1.42, 2.1, 2.66, 3.4), (1.0, 0.8, 0.6, 0.4, 0.2), (0.4, 0.3, 0.2,
                                                                                    0.15, 0.1)
    x = modes(n, [freq * r for r in ratios], amps, [ring * t for t in taus], rng)
    clap = bandpass(rng.standard_normal(n), 1500, 5000) * perc(n, 0.0005, 0.004)
    return lowpass(x + 0.2 * clap, CEILING) * ramp_in(n, secs(0.2))[::-1]


def bells_walking(rng, dur, freq, rate=1.6, kind="crotal", jangle=2):
    """Bells hung on a walking animal: struck on each stride, sometimes twice."""
    out = np.zeros(secs(dur + 3))
    t = rng.uniform(0, 0.2)
    while t < dur:
        for j in range(int(rng.integers(1, jangle + 1))):
            place(out, bell(freq * rng.uniform(0.98, 1.02), rng, 1.0, kind) * rng.uniform(0.4, 1.0),
                  secs(t + 0.06 * j))
        t += 1 / rate * rng.uniform(0.85, 1.15)
    return out


# --- feet, hooves, wheels --------------------------------------------------------------


def step(rng, surface="stone"):
    """One footstep (sandal or bare foot): heel then the ball of the foot."""
    n = secs(0.16)
    out = np.zeros(n)
    bright = {"stone": 3500, "dust": 1500, "wood": 2500}[surface]
    for at, lev in ((0.0, 1.0), (rng.uniform(0.04, 0.07), 0.6)):
        m = secs(0.06)
        tm = times(m)
        thud = np.sin(2 * np.pi * rng.uniform(90, 140) * tm) * np.exp(-tm / 0.012)
        scuff = bandpass(rng.standard_normal(m), 600, bright) * np.exp(-tm / 0.01)
        place(out, lev * (thud + 0.5 * scuff) * ramp_in(m, 8), secs(at))
    return lowpass(out, bright + 1000)


def hoof(rng, surface="stone"):
    """One hoof on paving (a hollow clop) or on sand (a muffled thump)."""
    n = secs(0.12)
    if surface == "sand":
        x = modes(n, [70, 130], [1.0, 0.4], [0.03, 0.02], rng)
        return lowpass(x + 0.3 * lowpass(rng.standard_normal(n), 800) * perc(n, 0.001, 0.02), 1500)
    f = rng.uniform(550, 750)
    x = modes(n, [f, f * 1.9, f * 3.1], [1.0, 0.5, 0.2], [0.018, 0.01, 0.006], rng)
    thud = modes(n, [110], [0.7], [0.02], rng)
    return lowpass(x + thud + 0.3 * bandpass(rng.standard_normal(n), 1000, 4000) * perc(n, 0.0005,
                                                                                         0.004), 5000)


def hoofbeats(rng, dur, gait="walk", surface="stone"):
    """A four-legged rhythm: a walk (four even beats) or a gallop (three-beat rushes)."""
    out = np.zeros(secs(dur + 0.5))
    if gait == "walk":
        times_ = np.arange(0, dur, 0.28)
    else:
        times_ = np.concatenate([[c, c + 0.07, c + 0.15] for c in np.arange(0, dur, 0.42)])
    for t in times_:
        place(out, hoof(rng, surface) * rng.uniform(0.6, 1.0), max(0, secs(t + rng.normal(0, 0.008))))
    return out


def cart(length, rng, speed=1.0, rumble=1.0):
    """Iron-rimmed wheels on stone paving as a seamless loop: a low rumble, a knock at each
    joint between stones, and the axle's creak."""
    n = secs(length)
    out = loop_noise(n, rng, 40, 400, 0.8, 1) * rumble * 0.6
    beat = 0.33 / speed
    k = int(round(length / beat))
    for i in range(k):
        t = i * length / k + rng.normal(0, 0.01)
        x = modes(secs(0.1), [rng.uniform(150, 260), rng.uniform(500, 800)], [1.0, 0.4],
                  [0.03, 0.012], rng) * rng.uniform(0.4, 1.0)
        place(out, x[: n - secs(t) % n], secs(t) % n)
    turns = int(round(length / (1.6 / speed)))
    for i in range(turns):
        t = i * length / turns
        place(out, 0.25 * creak_short(rng)[: n - secs(t) % n], secs(t) % n)
    return loop_lowpass(out, 3000)


def creak_short(rng, dur=0.35, f=None):
    """Wood or rope under strain: stick-slip pulses at a slowly changing rate."""
    n = secs(dur)
    rate = glide(n, [(0, f or rng.uniform(70, 140)), (dur, (f or 100) * rng.uniform(0.7, 1.4))])
    pulses = (np.sin(phase_of(rate)) > 0.97).astype(float)
    x = signal.lfilter([1.0], [1, -1.6, 0.8], pulses)  # a resonant wooden body
    x = bandpass(x, 300, 2500) * np.sin(np.pi * np.arange(n) / n) ** 0.5
    return x / (np.abs(x).max() + 1e-9)


# --- water and fire --------------------------------------------------------------------


def bubble(rng, f0):
    """One Minnaert bubble: a sine rising in pitch as it rings out."""
    dur = 6.0 / f0 * 30
    n = secs(min(dur, 0.06))
    t = times(n)
    return np.sin(2 * np.pi * f0 * (1 + 3 * t / 0.06) * t) * np.exp(-t / (0.004 + 8 / f0)) * ramp_in(n, 3)


def trickle(bed, rate, lo, hi, dist=(0.1, 0.5), spread=0.6, level=0.5):
    """A stream of bubbles from water running over stone (rate per second)."""
    for _ in range(int(rate * bed.n / SR)):
        f = np.exp(bed.rng.uniform(np.log(lo), np.log(hi)))
        bed.add(bubble(bed.rng, f), bed.rng.uniform(0, bed.n / SR), bed.rng.uniform(-spread, spread),
                bed.rng.uniform(*dist), bed.rng.uniform(0.2, 1.0) * level)


def waves(n, rng, period=7.0, size=1.0):
    """Small waves on a shore as a seamless stereo loop: each wave breaks with a soft wash
    and draws back hissing over pebbles. The wave count is a whole number per loop."""
    k = max(1, int(round(n / SR / period)))
    env = np.zeros(n)
    for i in range(k):
        c = (i + rng.uniform(-0.15, 0.15)) * n / k
        t = (np.arange(n) - c) / SR
        t = (t + n / SR / 2) % (n / SR) - n / SR / 2
        env += rng.uniform(0.6, 1.0) * np.exp(-np.clip(t, 0, None) / (period * 0.3)) * (t > -0.6) \
            * np.minimum(1, (t + 0.6) / 0.6)
    wash = loop_noise(n, rng, 150, 3500, 0.7) * env[:, None]
    draw = loop_noise(n, rng, 1500, 6000, 0.3) * (np.roll(env, secs(period * 0.25)) ** 2)[:, None]
    under = loop_noise(n, rng, 30, 250, 1.0) * (0.4 + 0.6 * env)[:, None]
    return size * (wash + 0.25 * draw + 0.5 * under)


def fire(length, rng, size=1.0):
    """A small fire or brazier as a seamless loop: a low breathy roar and crackling pops."""
    n = secs(length)
    roar = loop_noise(n, rng, 60, 700, 0.8, 1) * swell(n, rng, 0.5, 0.3)
    pops = np.zeros(n + secs(0.1))
    for _ in range(int(length * 9 * size)):
        m = secs(rng.uniform(0.003, 0.012))
        x = bandpass(rng.standard_normal(m), 800, 6000) * np.hanning(m) * rng.lognormal(0, 0.6)
        place(pops, x, secs(rng.uniform(0, length)))
    pops = wrap(pops, n)
    return loop_lowpass(0.5 * roar + 0.6 * pops, CEILING)


def pour(rng, dur=1.6):
    """Water poured from a jar into a basin: a gurgling stream whose pitch rises as the
    vessel fills."""
    n = secs(dur)
    t = times(n)
    stream = bandpass(rng.standard_normal(n), 400, 3000) * (0.6 + 0.4 * swell(n, rng, 6, 0.6))
    out = 0.3 * stream
    at = 0.0
    while at < dur - 0.1:
        f = 300 + 900 * at / dur + rng.uniform(-80, 80)
        place(out, 0.8 * bubble(rng, f), secs(at))
        at += rng.exponential(0.025)
    env = np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.2)
    return lowpass(out * env, 5000)


def mix(layers, out=None):
    """Sum named stereo layers; with `out` (a dict), also hand back each layer so a bed's
    balance can be measured layer by layer."""
    if out is not None:
        out.update(layers)
    return sum(layers.values())


def finish_sfx(x, rng, wet=0.2, size=0.6, fade_out=0.05, longest=5.8):
    """An effect in a little air: a touch of reverb (mono), trimmed below -60 dB, faded."""
    ir = impulse_response(rng, size, size * 0.8, size * 0.4, predelay=0.01).mean(axis=1)
    y = wet * signal.oaconvolve(x, ir)
    y[: len(x)] += x
    peak = np.max(np.abs(y))
    loud = np.nonzero(np.abs(y) > peak * 1e-3)[0]
    y = highpass(y[: min(loud[-1] + 1, secs(longest))], 25, 2)
    n = len(y)
    return y * ramp_in(n, secs(0.002)) * ramp_in(n, secs(fade_out))[::-1]


# --- workshops -------------------------------------------------------------------------


def wheel(length, rng, rpm=110.0):
    """A potter's kick wheel as a seamless loop: the heavy stone flywheel's low hum and
    the bearing's soft rub once a turn, with wet hands on clay hissing above it."""
    n = secs(length)
    turns = max(1, int(round(length * rpm / 60)))
    f_turn = turns / length
    t = times(n)
    hum = loop_noise(n, rng, 40, 300, 1.0, 1) * (0.7 + 0.3 * np.sin(2 * np.pi * f_turn * t))
    rub = loop_noise(n, rng, 200, 900, 0.5, 1) * (0.5 + 0.5 * np.sin(2 * np.pi * f_turn * t)) ** 6
    hands = loop_noise(n, rng, 800, 4000, 0.3, 1) * swell(n, rng, 0.5, 0.6)
    return loop_lowpass(0.6 * hum + 0.4 * rub + 0.12 * hands, 5000)


def slap(rng):
    """Wet clay slapped down or wedged on a board."""
    n = secs(0.15)
    x = lowpass(rng.standard_normal(n), 1800) * perc(n, 0.001, 0.02)
    return x + 0.5 * modes(n, [160, 330], [1.0, 0.4], [0.03, 0.015], rng)


def clink(rng):
    """Two fired pots touching: a short ceramic tick."""
    n = secs(0.2)
    f = rng.uniform(1600, 2600)
    return modes(n, [f, f * 1.6, f * 2.3], [1.0, 0.5, 0.25], [0.03, 0.02, 0.01], rng)


def kiln(length, rng):
    """A wood-fired kiln as a seamless loop: a deep turbulent roar breathing through the
    flue, with the crackle of the firebox."""
    n = secs(length)
    roar = loop_noise(n, rng, 30, 500, 1.1, 1) * swell(n, rng, 0.25, 0.25)
    breath = loop_noise(n, rng, 200, 1500, 0.6, 1) * swell(n, rng, 0.8, 0.5)
    return loop_lowpass(roar + 0.25 * breath, 3000) + 0.4 * fire(length, rng, 0.5)


def splash_small(rng):
    """A hand or a body moving in a pool: a slosh of water and a few bubbles."""
    n = secs(0.5)
    out = bandpass(rng.standard_normal(n), 300, 3000) * perc(n, 0.01, 0.08)
    for _ in range(int(rng.integers(3, 8))):
        place(out, 0.5 * bubble(rng, rng.uniform(400, 1500)), secs(rng.uniform(0.0, 0.3)))
    return lowpass(out, 5000)
