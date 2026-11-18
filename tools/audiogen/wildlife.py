"""Nature by climate (world set) and the improved animal voices (world and home sets).

Day and night shifts are made per climate, not per city, so they serve the land between too:
dawn choruses (Mediterranean scrub, river plain, mountain), midday cicadas in three heats,
dusk (town and water) and night (scrub, water, the east, mountain). Animal calls are built
syllable by syllable: a breath before the voice, a voiced body whose pitch, formants, vibrato
and tremolo move through the call, roughness where the animal is hoarse, and a breathy
release, each with variations so repeats never sound copied."""

import numpy as np

import ambience
import sounds as sd
from atmos import band, entry, noise_burst, resonant_burst, slow, swell
from dsp import (formant_noise, glide, line, lowpass, phase_of, place, secs,
                 times, voice)
from weather import WIND, wind_core

NATURE_S = 32.0  # nature beds: sparse events need a longer loop not to be heard repeating

# --- a voiced syllable -----------------------------------------------------------------


def curve(n, dur, pts):
    """(fraction of the syllable, value) points -> per-sample curve, or a scalar as is."""
    if np.isscalar(pts):
        return pts
    return line(n, [(dur * a, v) for a, v in pts])


def syllable(rng, dur, f0, formants, tilt=0.8, jitter=0.01, shimmer=0.1, breath=0.2, sub=0.0,
             attack=0.01, release=0.05, puff=0.0, vib=None, trem=None):
    """One animal syllable. f0 and each formant centre are (fraction, value) point lists
    or scalars; `vib` (rate Hz, depth) wobbles the pitch, `trem` (rate Hz, depth) the
    level; `puff` puts a short breath of air before the voice starts."""
    n = secs(dur)
    t = times(n)
    pitch = np.exp(curve(n, dur, [(a, np.log(v)) for a, v in f0]))
    if vib:
        pitch = pitch * (1 + vib[1] * np.sin(2 * np.pi * vib[0] * t + rng.uniform(0, 6.3)))
    forms = [(curve(n, dur, c), bw, g) for c, bw, g in formants]
    x = voice(pitch, forms, rng, tilt=tilt, jitter=jitter, shimmer=shimmer, breath=breath, sub=sub)
    env = np.clip(t / attack, 0, 1) ** 1.5 * np.clip((dur - t) / release, 0, 1) ** 1.2
    if trem:
        env = env * (1 - trem[1] * (0.5 - 0.5 * np.cos(2 * np.pi * trem[0] * t)))
    x = x * env
    if not puff:
        return x
    lead = secs(0.025)
    mouth = [(float(np.atleast_1d(c)[0]), bw, g) for c, bw, g in forms[:2]]  # at the onset
    air = formant_noise(lead + secs(0.03), mouth, rng)
    air *= np.hanning(len(air)) * puff * np.std(x) / (np.std(air) + 1e-12)
    out = np.zeros(n + lead)
    place(out, air, 0)
    place(out, x, lead)
    return out


def calls(parts, rng, total=None):
    """Join (signal, start_s) parts into one call."""
    end = max(at + len(x) / 44100 for x, at in parts) + 0.05
    out = np.zeros(secs(total or end))
    for x, at in parts:
        place(out, x, secs(at))
    return out


def fx(make, wet=0.15, size=0.5, top=6500.0):
    """An effect: the call in a little air, cut and faded."""
    return lambda rng: sd.finish_sfx(lowpass(make(rng), top, 4), rng, wet, size, fade_out=0.04)


# --- home voices: duck, hen, cat -------------------------------------------------------

DUCK_FORMANTS = [([(0, 700), (0.2, 1050), (1, 820)], 300, 1.0),
                 ([(0, 1400), (0.2, 1750), (1, 1500)], 350, 0.8), (2600, 500, 0.35),
                 (3400, 700, 0.1)]


def quack(rng, dur=0.16, scale=1.0, level=1.0):
    return level * syllable(rng, dur, [(0, 250 * scale), (0.15, 300 * scale), (1, 225 * scale)],
                            DUCK_FORMANTS, tilt=0.6, jitter=0.015, shimmer=0.15, breath=0.25,
                            sub=0.45, attack=0.006, release=0.05, puff=0.4)


def duck_1(rng):
    """A mallard's 'QUAACK-quack', the second softer and lower."""
    return fx(lambda r: calls([(quack(r, 0.17), 0.0), (quack(r, 0.13, 0.93, 0.6), 0.24)], r))(rng)


def duck_2(rng):
    """The duck's laughing run: five quacks, each shorter, lower and softer."""
    def make(r):
        parts, at = [], 0.0
        for k in range(5):
            d = 0.17 - 0.022 * k
            parts.append((quack(r, d, 1.0 - 0.04 * k, 1.0 - 0.15 * k), at))
            at += d + 0.06
        return calls(parts, r)
    return fx(make)(rng)


def duck_3(rng):
    """A drake's soft, hoarse 'raeb-raeb', murmured while dabbling."""
    def raeb(r, lv):
        return lv * syllable(r, 0.14, [(0, 190), (0.3, 210), (1, 170)],
                             [(600, 300, 1.0), (1300, 400, 0.6), (2400, 500, 0.2)], tilt=0.9,
                             jitter=0.025, shimmer=0.2, breath=0.5, sub=0.6, attack=0.015,
                             release=0.05)
    return fx(lambda r: calls([(raeb(r, 1.0), 0.0), (raeb(r, 0.8), 0.22)], r))(rng)


def cluck(rng, dur=0.06, f=330.0, level=1.0, rough=0.0):
    return level * syllable(rng, dur, [(0, f), (0.35, f * 1.06), (1, f * 0.9)],
                            [([(0, 450), (0.3, 680), (1, 560)], 250, 1.0), (1350, 400, 0.45),
                             (2900, 600, 0.12)], tilt=0.9, jitter=0.015, shimmer=0.15,
                            breath=0.3, sub=rough, attack=0.006, release=0.025, puff=0.3)


def hen_1(rng):
    """A hen's 'buk… buk-buk… bu-KAAWK'."""
    def make(r):
        kaawk = syllable(r, 0.26, [(0, 400), (0.3, 560), (1, 420)],
                         [([(0, 500), (0.25, 900), (1, 650)], 280, 1.0), (1750, 420, 0.5),
                          (2900, 600, 0.15)], tilt=0.85, jitter=0.02, shimmer=0.18, breath=0.35,
                         sub=0.3, attack=0.02, release=0.08)
        return calls([(cluck(r), 0.0), (cluck(r, f=345, level=0.8), 0.17),
                      (cluck(r, 0.045, 360, 0.7), 0.31), (kaawk, 0.38)], r)
    return fx(make)(rng)


def hen_2(rng):
    """Contented clucking while scratching: four low, soft 'tuk's."""
    def make(r):
        return calls([(cluck(r, r.uniform(0.045, 0.06), r.uniform(280, 310), r.uniform(0.6, 1.0)),
                       k * r.uniform(0.16, 0.2)) for k in range(4)], r)
    return fx(make)(rng)


def hen_3(rng):
    """A settled hen's purring trill, 'krrrr-uk'."""
    def make(r):
        trill = syllable(r, 0.5, [(0, 300), (0.5, 330), (1, 300)],
                         [(520, 260, 1.0), (1300, 400, 0.4)], tilt=1.0, jitter=0.02,
                         shimmer=0.2, breath=0.4, attack=0.04, release=0.1, trem=(24, 0.85))
        return calls([(trill, 0.0), (cluck(r, 0.05, 320, 0.7), 0.55)], r)
    return fx(make)(rng)


def cat_1(rng):
    """A cat's 'mi-aaow': the mouth opening through the call and closing at its end."""
    return fx(lambda r: syllable(
        r, 0.62, [(0, 520), (0.3, 720), (0.7, 640), (1, 470)],
        [([(0, 450), (0.3, 1050), (0.75, 900), (1, 550)], 260, 1.0),
         ([(0, 2100), (0.3, 1650), (1, 1100)], 400, 0.6), (3200, 600, 0.2)],
        tilt=0.95, jitter=0.008, shimmer=0.08, breath=0.15, attack=0.05, release=0.12,
        vib=(5.5, 0.01), puff=0.2))(rng)


def cat_2(rng):
    """A cat's greeting chirrup, 'mrrrp', rolled and rising."""
    return fx(lambda r: syllable(
        r, 0.3, [(0, 420), (0.6, 520), (1, 640)],
        [([(0, 380), (1, 850)], 260, 1.0), ([(0, 1500), (1, 1800)], 400, 0.5)], tilt=1.0,
        jitter=0.01, shimmer=0.1, breath=0.25, attack=0.02, release=0.04, trem=(28, 0.7)))(rng)


def cat_3(rng):
    """A small, high 'mew'."""
    return fx(lambda r: syllable(
        r, 0.28, [(0, 700), (0.4, 820), (1, 650)],
        [([(0, 500), (0.4, 950), (1, 700)], 260, 1.0), (1900, 400, 0.5), (3300, 600, 0.15)],
        tilt=1.0, jitter=0.008, shimmer=0.08, breath=0.15, attack=0.03, release=0.08))(rng)


# --- farm and town animals -------------------------------------------------------------


def sheep(rng, lamb=False):
    """A ewe's quavering 'mbaa' (or a lamb's higher, shorter one)."""
    k = 1.9 if lamb else 1.0
    dur = 0.55 if lamb else 0.85
    return syllable(rng, dur, [(0, 175 * k), (0.15, 230 * k), (0.7, 215 * k), (1, 175 * k)],
                    [([(0, 320), (0.15, 750), (1, 650)], 220, 1.0),
                     ([(0, 1100), (0.15, 1250), (1, 1150)], 300, 0.5), (2600, 450, 0.18)],
                    tilt=0.85, jitter=0.012, shimmer=0.12, breath=0.3, sub=0.1, attack=0.06,
                    release=0.15, vib=(7.5, 0.035), trem=(7.5, 0.35), puff=0.2)


def goat(rng, kid=False):
    """A goat's bleat: nasal, with a deep quaver, 'meh-eh-eh'."""
    k = 1.5 if kid else 1.0
    return syllable(rng, 0.7, [(0, 330 * k), (0.12, 420 * k), (1, 360 * k)],
                    [([(0, 380), (0.12, 600), (1, 520)], 220, 1.0), (1800, 350, 0.55),
                     (2700, 450, 0.2)], tilt=0.75, jitter=0.02, shimmer=0.15, breath=0.25,
                    attack=0.04, release=0.12, vib=(11, 0.06), trem=(11, 0.6), puff=0.2)


def donkey(rng):
    """A donkey's bray: a wheezing in-breath on a high note, a honk out on a low one, three
    times, tiring."""
    parts, at = [], 0.0
    for k in range(3):
        inhale = 0.5 * syllable(rng, 0.32, [(0, 850), (0.5, 1050), (1, 900)],
                                [(1100, 400, 1.0), (2300, 500, 0.3)], tilt=0.7, jitter=0.03,
                                shimmer=0.25, breath=1.5, attack=0.05, release=0.06)
        exhale = syllable(rng, 0.45, [(0, 200 - 10 * k), (0.25, 245 - 10 * k), (1, 170)],
                          [(800, 320, 1.0), (1500, 400, 0.6), (2600, 500, 0.2)], tilt=0.55,
                          jitter=0.025, shimmer=0.2, breath=0.3, sub=0.5, attack=0.02,
                          release=0.08)
        parts += [(inhale * (1 - 0.15 * k), at), (exhale * (1 - 0.15 * k), at + 0.3)]
        at += 0.78
    return calls(parts, rng)


def whinny(rng):
    """A horse's whinny: a high call shaking down into a low nicker."""
    call = syllable(rng, 1.15, [(0, 700), (0.1, 1100), (0.5, 940), (0.85, 600), (1, 430)],
                    [(1100, 420, 1.0), (2300, 500, 0.4), (3300, 600, 0.12)], tilt=0.75,
                    jitter=0.02, shimmer=0.15, breath=0.35, attack=0.04, release=0.15,
                    vib=(12, 0.06), trem=(12, 0.45), puff=0.3)
    nicker = syllable(rng, 0.5, [(0, 170), (1, 140)], [(500, 250, 1.0), (1100, 300, 0.3)],
                      tilt=1.0, jitter=0.03, shimmer=0.2, breath=0.5, attack=0.03, release=0.1,
                      trem=(9, 0.9))
    return calls([(call, 0.0), (0.6 * nicker, 1.1)], rng)


def horse_blow(rng):
    """A horse blowing through its nostrils: a fluttering snort, then a soft out-breath."""
    n = secs(0.5)
    t = times(n)
    flutter = (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(28, 38) * t)) ** 2
    snort = resonant_burst(rng, 0.5, 320, 2.5, 0.15) + 0.6 * resonant_burst(rng, 0.5, 950, 3, 0.12)
    snort = snort * flutter * np.clip(t / 0.02, 0, 1)
    blow = noise_burst(rng, 0.45, 200, 1800, 0.18, 0.06)
    return calls([(snort, 0.0), (0.4 * blow, 0.5)], rng)


def camel(rng):
    """A camel grumbling: a deep gargled growl with bubbling in the throat."""
    dur = 1.5
    n = secs(dur)
    gargle = 1 + 0.45 * np.sin(phase_of(14 + 4 * slow(n, rng, 3.0)))
    x = syllable(rng, dur, [(0, 70), (0.35, 105), (1, 65)],
                 [(480, 250, 1.0), (1050, 300, 0.5), (2300, 400, 0.15)], tilt=0.7, jitter=0.03,
                 shimmer=0.25, breath=0.5, sub=0.7, attack=0.1, release=0.25) * gargle
    for _ in range(14):
        place(x, 0.3 * sd.bubble(rng, rng.uniform(180, 480)), secs(rng.uniform(0.1, dur - 0.1)))
    return x


def bark(rng, scale=1.0, dur=0.16):
    return syllable(rng, dur, [(0, 420 * scale), (0.15, 560 * scale), (1, 340 * scale)],
                    [(700 * scale ** 0.5, 300, 1.0), (1400 * scale ** 0.5, 400, 0.7),
                     (2600, 500, 0.3)], tilt=0.65, jitter=0.025, shimmer=0.2, breath=0.5,
                    sub=0.3, attack=0.004, release=0.06, puff=0.3)


def gull_call(rng):
    """A gull's long call: a drawn-out 'kyaaa' and a laughing run of 'ha's."""
    form = [(1800, 500, 1.0), (3000, 700, 0.4)]
    parts = [(syllable(rng, 0.5, [(0, 800), (0.25, 1100), (1, 720)], form, tilt=0.6,
                       jitter=0.012, shimmer=0.12, breath=0.2, sub=0.2, attack=0.03,
                       release=0.1), 0.0)]
    for k in range(5):
        parts.append((0.8 * syllable(rng, 0.11, [(0, 900 - 40 * k), (1, 760 - 40 * k)], form,
                                     tilt=0.6, jitter=0.015, shimmer=0.12, breath=0.25, sub=0.25,
                                     attack=0.01, release=0.04), 0.6 + 0.16 * k))
    return calls(parts, rng)


def pigeon_coo(rng):
    """A pigeon's 'oo-ROO-oo', throaty and soft, the middle note rolling."""
    form = [(400, 200, 1.0), (900, 300, 0.1)]
    parts = [(syllable(rng, 0.22, [(0, 300), (1, 330)], form, tilt=2.0, jitter=0.005,
                       shimmer=0.05, breath=0.1, attack=0.04, release=0.06), 0.0),
             (syllable(rng, 0.42, [(0, 380), (0.3, 430), (1, 360)], form, tilt=2.0,
                       jitter=0.005, shimmer=0.05, breath=0.1, attack=0.05, release=0.1,
                       trem=(19, 0.5)), 0.27),
             (syllable(rng, 0.3, [(0, 330), (1, 280)], form, tilt=2.0, jitter=0.005,
                       shimmer=0.05, breath=0.1, attack=0.04, release=0.1), 0.75)]
    return calls(parts, rng)


def caw(rng, scale=1.0):
    return syllable(rng, 0.3, [(0, 450 * scale), (0.2, 560 * scale), (1, 420 * scale)],
                    [(1200, 500, 1.0), (1900, 600, 0.6), (2900, 600, 0.15)], tilt=0.6,
                    jitter=0.025, shimmer=0.2, breath=0.5, sub=0.35, attack=0.015, release=0.08)


def cuckoo(rng):
    """A cuckoo far across the valley: two falling fluty notes, twice."""
    parts = []
    for k in range(2):
        for at, f, d in ((0.0, 700, 0.17), (0.3, 580, 0.26)):
            n = secs(d)
            ph = phase_of(glide(n, [(0, f * 1.01), (d, f * 0.98)]))
            x = (np.sin(ph) + 0.08 * np.sin(2 * ph)) * np.sin(np.pi * np.arange(n) / n) ** 0.7
            parts.append((x, at + 0.95 * k))
    return lowpass(calls(parts, rng), 2500, 2)


def stork_clatter(rng):
    """A stork clattering its bill: hollow wooden knocks through the throat pouch, speeding
    up and slowing down."""
    out = np.zeros(secs(2.6))
    t = 0.0
    while t < 2.2:
        rate = 8 + 15 * np.sin(np.pi * t / 2.2)
        lv = 0.4 + 0.6 * np.sin(np.pi * t / 2.2)
        f = rng.uniform(950, 1250)
        knock = sd.modes(secs(0.04), [f, f * 2.1], [1.0, 0.35], [0.004, 0.002], rng)
        knock = knock + 0.8 * resonant_burst(rng, 0.04, 620, 4, 0.006)
        place(out, knock * lv * rng.uniform(0.8, 1.0), secs(t))
        t += 1 / rate
    return out


# --- birds and insects for the beds ----------------------------------------------------


def note(f_pts, dur, harm=0.08, power=0.8):
    """One whistled bird note gliding through (fraction, Hz) points."""
    n = secs(dur)
    ph = phase_of(glide(n, [(dur * a, f) for a, f in f_pts]))
    return (np.sin(ph) + harm * np.sin(2 * ph)) * np.sin(np.pi * np.arange(n) / n) ** power


def song(parts):
    return np.concatenate([np.concatenate([x, np.zeros(secs(g))]) for x, g in parts])


def fluty(rng, base):
    """A thrush-like song: a few rich, fluting notes with glides, then a soft twitter."""
    parts = []
    for _ in range(int(rng.integers(3, 6))):
        f = base * rng.uniform(0.8, 1.6)
        parts.append((note([(0, f), (0.4, f * rng.uniform(0.9, 1.25)), (1, f * rng.uniform(0.75, 1.1))],
                           rng.uniform(0.1, 0.3), 0.15), rng.uniform(0.03, 0.09)))
    for _ in range(int(rng.integers(3, 8))):
        f = rng.uniform(3000, 4800)
        parts.append((0.35 * note([(0, f), (1, f * rng.uniform(0.8, 1.2))], rng.uniform(0.03, 0.05)),
                      0.015))
    return song(parts)


def warble(rng, lo=2500, hi=5200):
    """A warbler's quick, varied run of notes."""
    parts, t = [], 0.0
    stop = rng.uniform(1.0, 2.4)
    while t < stop:
        f = rng.uniform(lo, hi)
        d = rng.uniform(0.03, 0.08)
        parts.append((note([(0, f), (1, f * rng.uniform(0.75, 1.3))], d) * rng.uniform(0.5, 1),
                      rng.uniform(0.01, 0.04)))
        t += d + 0.025
    return song(parts)


def trill(rng):
    """A bright trill: one note repeated fast, swelling."""
    f = rng.uniform(3000, 5000)
    rate = rng.uniform(12, 22)
    k = int(rng.uniform(0.8, 2.0) * rate)
    return song([(note([(0, f * 1.05), (1, f * 0.95)], 0.6 / rate) * (0.4 + 0.6 * i / k),
                  0.4 / rate) for i in range(k)])


def scratchy(rng):
    """A scrub warbler's dry, scratchy rattle."""
    dur = rng.uniform(0.8, 1.6)
    n = secs(dur)
    rough = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rng.uniform(35, 55) * times(n)))
    x = note([(0, rng.uniform(3000, 4000)), (1, rng.uniform(2600, 3400))], dur, 0.3, 0.4)
    return lowpass(x * rough, 5500, 2)


def turtle_dove(rng):
    """A turtle dove's soft purring 'turrr-turrr-turrr'."""
    return song([(note([(0, 520), (0.5, 560), (1, 500)], 0.55, 0.05) *
                  (0.5 + 0.5 * np.sin(2 * np.pi * 30 * times(secs(0.55)))), 0.25)
                 for _ in range(3)])


def chukar(rng):
    """A rock partridge calling from the slope: 'chuk chuk chuk-ar'."""
    form = [(1300, 500, 1.0), (2300, 600, 0.4)]
    parts = [(syllable(rng, 0.08, [(0, 650), (1, 600)], form, tilt=0.7, jitter=0.02, shimmer=0.15,
                       breath=0.4, sub=0.3, attack=0.005, release=0.03), 0.2 * k) for k in range(3)]
    parts.append((syllable(rng, 0.22, [(0, 640), (0.4, 820), (1, 600)], form, tilt=0.7,
                           jitter=0.02, shimmer=0.15, breath=0.4, sub=0.3, attack=0.01,
                           release=0.06), 0.62))
    return calls(parts, rng)


def rooster(rng):
    """A cockerel crowing far off at first light."""
    return syllable(rng, 1.3, [(0, 420), (0.12, 560), (0.3, 520), (0.75, 600), (1, 380)],
                    [([(0, 650), (0.3, 1000), (1, 800)], 300, 1.0), (1700, 450, 0.5),
                     (2700, 500, 0.2)], tilt=0.7, jitter=0.02, shimmer=0.15, breath=0.3, sub=0.25,
                    attack=0.05, release=0.25, trem=(16, 0.15))


def reed_chatter(rng):
    """A reed warbler's chatter: little two- and three-note figures repeated, harsh and
    sweet by turns."""
    parts = []
    for _ in range(int(rng.integers(3, 6))):
        motif = [(rng.uniform(2200, 4800), rng.uniform(0.03, 0.06)) for _ in range(int(rng.integers(2, 4)))]
        for _ in range(int(rng.integers(2, 4))):
            for f, d in motif:
                parts.append((note([(0, f), (1, f * 0.85)], d, 0.3), 0.02))
            parts.append((np.zeros(1), rng.uniform(0.04, 0.12)))
    return lowpass(song(parts), 5500, 2)


def bee_eater(rng):
    """A bee-eater's liquid, rolling 'prrup'."""
    d = 0.18
    n = secs(d)
    f = rng.uniform(2400, 2900)
    return note([(0, f * 0.95), (0.5, f), (1, f * 0.9)], d, 0.1) * \
        (0.45 + 0.55 * np.sin(2 * np.pi * 42 * times(n)) ** 2)


def chough(rng):
    """A chough's ringing 'chee-ow' off the crags."""
    return syllable(rng, 0.32, [(0, 1500), (0.3, 1900), (1, 1200)],
                    [(2200, 600, 1.0), (3400, 700, 0.3)], tilt=0.5, jitter=0.01, shimmer=0.1,
                    breath=0.15, attack=0.02, release=0.08)


def kingfisher(rng):
    return note([(0, 5200), (1, 4600)], 0.12, 0.05) * 0.6


def goose_far(rng):
    """Geese honking as they pass, far off."""
    return calls([(syllable(rng, 0.2, [(0, 380), (0.3, 450), (1, 360)],
                            [(800, 300, 1.0), (1500, 400, 0.5)], tilt=0.7, jitter=0.02,
                            shimmer=0.15, breath=0.3, sub=0.3, attack=0.01, release=0.06), 0.25 * k)
                  for k in range(int(rng.integers(3, 6)))], rng)


def nightjar(rng, dur=6.0):
    """A nightjar's churr: a long dry trill of clicks, switching pitch now and then."""
    n = secs(dur)
    t = times(n)
    rate = np.where((t // rng.uniform(1.2, 2.2)) % 2 == 0, 30.0, 38.0)
    clicks = (0.5 + 0.5 * np.sin(phase_of(rate))) ** 6
    tone = np.sin(phase_of(np.where(rate > 33, 1150.0, 950.0)))
    env = np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 0.5)
    return lowpass(tone * clicks * env, 3000, 2)


def tawny(rng):
    """A tawny owl: a long 'hoo', a pause, a quavering 'hu-hu-hooo'."""
    parts = [(note([(0, 470), (0.2, 500), (1, 460)], 0.5, 0.05, 1.2), 0.0)]
    parts.append((0.7 * note([(0, 440), (1, 430)], 0.12, 0.05, 1.0), 1.6))
    parts.append((0.8 * note([(0, 450), (1, 440)], 0.12, 0.05, 1.0), 1.8))
    n = secs(1.1)
    q = note([(0, 470), (0.2, 510), (1, 450)], 1.1, 0.05, 1.0) * \
        (0.7 + 0.3 * np.sin(2 * np.pi * 7 * times(n)))
    parts.append((q, 2.05))
    return lowpass(calls(parts, rng), 1800, 2)


def frog_croak(rng, f=None):
    """A marsh frog's croak: a quick run of throaty pulses, 'brekeke'."""
    f = f or rng.uniform(700, 1300)
    k = int(rng.integers(4, 10))
    rate = rng.uniform(12, 20)
    pulses = []
    for i in range(k):
        m = secs(0.04)
        p = resonant_burst(rng, 0.04, f, 6, 0.008) + 0.5 * np.sin(2 * np.pi * f / 2 * times(m)) * \
            np.exp(-times(m) / 0.01)
        pulses.append((p * (0.6 + 0.4 * np.sin(np.pi * i / k)), 1 / rate - 0.04))
    return song(pulses)


def toad_trill(rng, dur=None):
    """A toad's long, even trill by the water."""
    dur = dur or rng.uniform(3, 7)
    n = secs(dur)
    t = times(n)
    f = rng.uniform(1100, 1500)
    am = (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(16, 22) * t)) ** 3
    env = np.minimum(1, t / 0.3) * np.minimum(1, (dur - t) / 0.3)
    return np.sin(2 * np.pi * f * t) * am * env


def jackals(rng):
    """Jackals far off: wailing howls rising and breaking into yips, several voices."""
    parts = []
    for v in range(int(rng.integers(3, 5))):
        at = rng.uniform(0, 1.5)
        dur = rng.uniform(1.2, 2.2)
        top = rng.uniform(800, 1100)
        parts.append((syllable(rng, dur, [(0, top * 0.55), (0.4, top), (0.8, top * 0.85), (1, top * 0.6)],
                               [(1100, 500, 1.0), (2200, 600, 0.3)], tilt=0.9, jitter=0.01,
                               shimmer=0.1, breath=0.3, attack=0.2, release=0.3, vib=(6, 0.02)),
                      at))
        for k in range(int(rng.integers(3, 7))):
            parts.append((0.6 * syllable(rng, 0.08, [(0, top), (1, top * 0.8)],
                                         [(1300, 500, 1.0)], tilt=0.8, breath=0.3, attack=0.01,
                                         release=0.03), at + dur + 0.12 * k))
    return lowpass(calls(parts, rng), 2500, 2)


def bat(rng):
    """A bat hawking overhead: a few soft wing flutters and tiny ticks."""
    out = np.zeros(secs(0.6))
    for k in range(int(rng.integers(3, 7))):
        place(out, noise_burst(rng, 0.01, 4500, 6400, 0.001), secs(0.08 * k))
    out += 0.3 * sd.wingbeats(rng, 5, 12)[: len(out)]
    return out




CICADAS = (dict(name="warm", count=4, kinds=("pulsed", "phrase"), dist=(0.6, 0.9), wall=0.0),
           dict(name="hot", count=10, kinds=("pulsed", "phrase", "buzz"), dist=(0.35, 0.9),
                wall=0.25),
           dict(name="blazing", count=22, kinds=("buzz", "buzz", "pulsed", "phrase"),
                dist=(0.25, 0.9), wall=0.6))
CICADA_LUFS = (-28.0, -24.5, -21.0)


def cicadas(level):
    """Midday cicadas, a layer over the climate's day bed: a few far voices on a warm day,
    a chorus in the heat, a pulsing wall in the blazing afternoon."""
    p = CICADAS[level]

    def render(rng, length=30.0):
        n = secs(length)
        bugs = sd.Bed(length, rng)
        for _ in range(p["count"]):
            kind = p["kinds"][int(rng.integers(len(p["kinds"])))]
            dur = rng.uniform(5, 14)
            bugs.add(sd.tymbal(rng, dur, kind), rng.uniform(0, length), rng.uniform(-0.9, 0.9),
                     rng.uniform(*p["dist"]), rng.uniform(0.5, 1.0))
        out = bugs.finish((1.5, 1.0, 0.5, 0.02), 0.3)
        if p["wall"]:  # a hundred far cicadas blur into a pulsing band
            wall = band(n, rng, 3800, 6500, 0.2) * (swell(n, rng, 0.08, 0.4)[:, None]) * \
                (0.75 + 0.25 * np.sin(2 * np.pi * 7 * times(n)))[:, None]
            out = out + p["wall"] * 0.08 * wall
        return out

    return render


# --- beds ------------------------------------------------------------------------------


def singer(bed, make, length, every, pos, dist, level):
    """One bird singing from a fixed perch, a phrase every `every` seconds (jittered)."""
    t = bed.rng.uniform(0, every)
    while t < length:
        bed.add(make(bed.rng), t, pos + bed.rng.uniform(-0.05, 0.05), dist, level)
        t += every * bed.rng.uniform(0.7, 1.4)


def air(n, rng, level=0):
    return wind_core(n, rng, WIND[level])[0]


def dawn_scrub(rng, length=NATURE_S):
    """Dawn in Mediterranean scrub and olive country: thrushes fluting from the treetops,
    warblers, a scratchy rattle in the bushes, turtle doves purring, a partridge on the
    slope and a cockerel far off at a farm."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for k in range(2):
        singer(b, lambda r: fluty(r, 1900), length, 6.0, (-0.5, 0.45)[k], rng.uniform(0.3, 0.6), 0.8)
    for k in range(2):
        singer(b, warble, length, 3.5, rng.uniform(-0.8, 0.8), rng.uniform(0.4, 0.7), 0.6)
    singer(b, scratchy, length, 5.0, rng.uniform(-0.6, 0.6), 0.35, 0.4)
    singer(b, trill, length, 9.0, rng.uniform(-0.8, 0.8), 0.6, 0.5)
    singer(b, turtle_dove, length, 11.0, rng.uniform(-0.7, 0.7), 0.6, 0.5)
    b.add(chukar(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.8, 0.5)
    b.add(rooster(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.35)
    return sd.mix({"birds": 2.5 * b.finish((1.8, 1.2, 0.5, 0.02), 0.4), "air": 0.06 * air(n, rng)})


def dawn_river(rng, length=NATURE_S):
    """Dawn on a river plain (the Tiber's banks, Mesopotamia): reed warblers chattering, a
    flock of bee-eaters, doves, the last frogs, a kingfisher, geese passing far off."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for k in range(2):
        singer(b, reed_chatter, length, 4.5, (-0.4, 0.5)[k], rng.uniform(0.3, 0.5), 0.6)
    t0 = rng.uniform(0, length)
    for k in range(8):
        b.add(bee_eater(rng), t0 + rng.uniform(0, 4), rng.uniform(-0.3, 0.6), 0.6, 0.5)
    singer(b, turtle_dove, length, 13.0, rng.uniform(-0.7, 0.7), 0.6, 0.45)
    for _ in range(5):
        b.add(frog_croak(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.6, 0.3)
    for _ in range(3):
        b.add(kingfisher(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.4, 0.5)
    b.add(goose_far(rng), rng.uniform(0, length), rng.uniform(-0.6, 0.6), 0.95, 0.4)
    water = band(n, rng, 80, 1500, 0.8) * swell(n, rng, 0.2, 0.3)[:, None]
    return sd.mix({"birds": 2.5 * b.finish((1.8, 1.2, 0.5, 0.02), 0.4), "water": 0.03 * water})


def dawn_mountain(rng, length=NATURE_S):
    """Dawn high in the mountains: a wren's loud trills among rocks, choughs off the crags,
    a cuckoo across the valley, partridges, a raven, a stream below, cold air."""
    n = secs(length)
    b = sd.Bed(length, rng)
    singer(b, lambda r: song([(warble(r, 3000, 5500), 0.05), (trill(r), 0.0)]), length, 8.0,
           rng.uniform(-0.6, 0.6), 0.35, 0.6)
    for _ in range(4):
        b.add(chough(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.6, 0.5)
    for _ in range(2):
        b.add(cuckoo(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.9, 0.5)
    for _ in range(2):
        b.add(chukar(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.75, 0.45)
    b.add(sd.raven(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.7, 0.4)
    stream = band(n, rng, 200, 4000, 0.5) * swell(n, rng, 0.3, 0.2)[:, None]
    return sd.mix({"birds": 2.5 * b.finish((2.5, 1.8, 0.7, 0.03), 0.5), "stream": 0.02 * stream,
                   "air": 0.08 * air(n, rng)})


def dusk_town(rng, length=NATURE_S):
    """Dusk over a town: swallows twittering low, swifts screaming round the roofs, a
    thrush's last song, the first crickets, bats flickering."""
    n = secs(length)
    b = sd.Bed(length, rng)
    b.scatter(sd.swallow, 8, dist=(0.3, 0.7), level=(0.4, 0.8))
    b.scatter(sd.swift, 6, dist=(0.5, 0.8), level=(0.3, 0.6))
    singer(b, lambda r: fluty(r, 1800), length, 9.0, rng.uniform(-0.6, 0.6), 0.6, 0.6)
    b.scatter(bat, 10, dist=(0.2, 0.5), level=(0.2, 0.4))
    sd.crickets(b, 3, level=0.25)
    return sd.mix({"life": 2.5 * b.finish((1.6, 1.1, 0.5, 0.02), 0.35), "air": 0.05 * air(n, rng)})


def dusk_water(rng, length=NATURE_S):
    """Dusk by water: the frogs starting up, a last reed warbler, ducks settling, crickets."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(14):
        b.add(frog_croak(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.4, 0.8), 0.4)
    singer(b, reed_chatter, length, 10.0, rng.uniform(-0.6, 0.6), 0.5, 0.45)
    for _ in range(2):
        b.add(lowpass(quack(rng, 0.14, 0.95), 3000), rng.uniform(0, length), rng.uniform(-0.6, 0.6), 0.7, 0.4)
    sd.crickets(b, 2, level=0.25)
    water = band(n, rng, 80, 1200, 0.9) * swell(n, rng, 0.2, 0.3)[:, None]
    return sd.mix({"life": 2.5 * b.finish((1.6, 1.1, 0.5, 0.02), 0.35), "water": 0.03 * water})


def night_scrub(rng, length=NATURE_S):
    """A warm night in scrub country: crickets, a scops owl's patient note, a nightjar
    churring, a tawny owl once, a dog far off."""
    n = secs(length)
    b = sd.Bed(length, rng)
    sd.crickets(b, 6, level=0.45)
    pos = rng.uniform(-0.7, 0.7)
    t0 = rng.uniform(0, length)
    for k in range(10):
        b.add(sd.scops_owl(rng), t0 + 2.7 * k, pos, 0.7, 0.35)
    for _ in range(2):
        b.add(nightjar(rng, rng.uniform(5, 8)), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.6, 0.25)
    b.add(tawny(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.75, 0.4)
    b.add(lowpass(sd.dog(rng, 2), 1500), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.25)
    return sd.mix({"life": 2.5 * b.finish((2.5, 1.6, 0.6, 0.03), 0.45), "air": 0.04 * air(n, rng)})


def night_water(rng, length=NATURE_S):
    """Night by marsh or river: a frog chorus, toads trilling, wind in the reeds, the water."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(32):
        b.add(lowpass(frog_croak(rng), 4000, 2), rng.uniform(0, length), rng.uniform(-0.9, 0.9), rng.uniform(0.3, 0.9),
              rng.uniform(0.3, 0.7))
    for _ in range(4):
        b.add(toad_trill(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.5, 0.8), 0.15)
    g = swell(n, rng, 0.1, 0.5)
    reeds = np.stack([ambience.crackle(n, rng, 50 * g, 1500, 4500) for _ in range(2)], axis=1)
    water = band(n, rng, 80, 1200, 0.9) * swell(n, rng, 0.2, 0.3)[:, None]
    return sd.mix({"life": 2.5 * b.finish((2.0, 1.4, 0.5, 0.03), 0.4), "reeds": 0.04 * reeds,
                   "water": 0.03 * water})


def night_east(rng, length=NATURE_S):
    """Night on the eastern plains and steppe: jackals wailing far off, crickets, a little
    owl, dry air."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(2):
        b.add(jackals(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.5)
    sd.crickets(b, 4, level=0.2)
    for _ in range(4):
        b.add(sd.little_owl(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.75, 0.3)
    return sd.mix({"life": 2.5 * b.finish((3.0, 2.0, 0.7, 0.04), 0.5), "air": 0.06 * air(n, rng)})


def night_mountain(rng, length=NATURE_S):
    """Night in the mountains: owls calling across the valley, a stream, cold breath of
    wind, a fox barking far off."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(3):
        b.add(tawny(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.6, 0.9), 0.45)
    b.add(lowpass(bark(rng, 1.5, 0.12), 1800), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.3)
    sd.crickets(b, 1, level=0.2)
    stream = band(n, rng, 200, 4000, 0.5) * swell(n, rng, 0.3, 0.2)[:, None]
    return sd.mix({"life": 2.5 * b.finish((3.0, 2.2, 0.8, 0.04), 0.5), "stream": 0.025 * stream,
                   "air": 0.08 * air(n, rng)})


# --- files -----------------------------------------------------------------------------

W = "world"
FILES = {}
for _name, _fn, _when, _climate, _where, _desc in (
        ("dawn_scrub", dawn_scrub, "dawn", "mediterranean",
         "dawn in Latium, the Greek countryside, Ionia, the corner's borderland",
         "Dawn chorus in scrub and olive country."),
        ("dawn_river", dawn_river, "dawn", "river_plain",
         "dawn on the Tiber banks, Mesopotamia, Susiana, river tiles",
         "Dawn on a river plain: reed warblers, bee-eaters, doves, the last frogs."),
        ("dawn_mountain", dawn_mountain, "dawn", "mountain",
         "dawn in the Apennines, Arcadia, the Taurus, the Zagros",
         "Dawn in the mountains: a wren, choughs, a far cuckoo, partridges."),
        ("dusk_town", dusk_town, "dusk", "mediterranean",
         "dusk over towns and cities and the open country around them",
         "Dusk: swallows, swifts, a last thrush, the first crickets, bats."),
        ("dusk_water", dusk_water, "dusk", "river_plain",
         "dusk by rivers, marshes, harbours with reed beds",
         "Dusk by water: frogs starting, a last reed warbler, ducks settling."),
        ("night_scrub", night_scrub, "night", "mediterranean",
         "night in Mediterranean country (Italy, Greece, Ionia); towns at their edges",
         "A warm night: crickets, a scops owl, a nightjar, a tawny owl, a far dog."),
        ("night_water", night_water, "night", "river_plain",
         "night by rivers and marshes (Tiber, Euphrates, Tigris, the Gulf's reeds)",
         "Night by water: a frog chorus, toads trilling, reeds, lapping."),
        ("night_east", night_east, "night", "east",
         "night on the steppe and plateaus of the east (Syria, Mesopotamia, Persia)",
         "Night in the east: jackals far off, crickets, a little owl, dry air."),
        ("night_mountain", night_mountain, "night", "mountain",
         "night in the mountains (Apennines, Taurus, Zagros)",
         "Night in the mountains: owls across the valley, a stream, a far fox.")):
    FILES[f"amb/{W}/{_name}.ogg"] = entry("bed", _fn, -23.0, _desc, when=_when, where=_where,
                                          tags=["nature", _when, _climate])
for _lvl, _p in enumerate(CICADAS):
    FILES[f"amb/{W}/cicadas_{_lvl + 1}.ogg"] = entry(
        "bed", cicadas(_lvl), CICADA_LUFS[_lvl], f"Midday cicadas, {_p['name']}.",
        when="day", where="layer over the day bed in Mediterranean summer from mid-morning to "
        "late afternoon in clear weather, level by heat (Athens' theme `cicadas`)",
        family="cicadas", level=_lvl + 1, level_name=_p["name"],
        tags=["nature", "insects", "summer", "mediterranean"])

_ANIMALS = (
    ("sheep_1", lambda r: sheep(r), -24.0, "A ewe's quavering bleat."),
    ("sheep_2", lambda r: sheep(r, lamb=True), -24.0, "A lamb's bleat."),
    ("goat_1", lambda r: goat(r), -24.0, "A goat's nasal, quavering bleat."),
    ("goat_2", lambda r: goat(r, kid=True), -24.0, "A kid's higher bleat."),
    ("donkey", donkey, -23.0, "A donkey braying: wheeze in, honk out, three times."),
    ("horse_whinny", whinny, -23.0, "A horse's whinny shaking down into a nicker."),
    ("horse_blow", horse_blow, -25.0, "A horse blowing a fluttering snort."),
    ("camel_grumble", camel, -24.0, "A camel's gargled grumble with throat bubbles."),
    ("dog_1", lambda r: calls([(bark(r), 0.0), (0.85 * bark(r, 0.95), 0.32)], r), -23.0,
     "A dog barking twice."),
    ("dog_2", lambda r: calls([(bark(r, 1.45, 0.11) * (1 - 0.15 * k), 0.2 * k) for k in range(3)], r),
     -24.0, "A small dog's three yaps."),
    ("gull_call", gull_call, -24.0, "A gull's long call and laughing run."),
    ("pigeon_coo", pigeon_coo, -26.0, "A pigeon's throaty 'oo-ROO-oo'."),
    ("crow_1", lambda r: calls([(caw(r) * (1 - 0.1 * k), 0.42 * k) for k in range(3)], r), -24.0,
     "A crow cawing three times."),
    ("crow_2", lambda r: calls([(caw(r, 1.15), 0.0), (0.8 * caw(r, 1.1), 0.38)], r), -24.0,
     "A crow cawing twice, higher."),
    ("cuckoo", cuckoo, -26.0, "A cuckoo far across the valley, twice."),
    ("stork_clatter", stork_clatter, -24.0, "A stork clattering its bill on the nest."),
)
for _name, _fn, _lufs, _desc in _ANIMALS:
    FILES[f"sfx/{W}/{_name}.wav"] = entry("sfx", fx(_fn), _lufs, _desc, gain=0.8,
                                          tags=["animal", _name.split("_")[0]])

# Home: the duck, hen and cat each get variations; variation 1 replaces the catalog's file.
HOME = {}
for _name, _fn, _lufs, _desc in (
        ("duck_2", duck_2, -21.0, "The duck's laughing run of quacks."),
        ("duck_3", duck_3, -22.0, "A drake's soft hoarse murmur."),
        ("hen_2", hen_2, -22.0, "A hen's contented clucks while scratching."),
        ("hen_3", hen_3, -22.0, "A settled hen's purring trill."),
        ("cat_2", cat_2, -22.0, "The cat's greeting chirrup."),
        ("cat_3", cat_3, -22.0, "A small, high mew.")):
    HOME[f"sfx/{_name}.wav"] = entry("sfx", _fn, _lufs, _desc, gain=1.0,
                                     tags=["animal", "voice", _name.split("_")[0], "variation"])
