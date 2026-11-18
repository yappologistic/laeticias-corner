"""People and their work (world and city sets, home steps): wordless crowds in three sizes
and three characters, footsteps on every surface, hooves and carts, the work sounds the
cities' chains of goods name, crowd responses for events, a far chorus and a wedding song.

Voices are never words. A talker is a harmonic voice moving between vowel shapes with
consonant noise between syllables, phrased with falling or rising contours and pauses; the
three characters differ in pace, pitch range, how often people laugh or call out, and the
space they are heard in."""

import numpy as np

import ambience
import ancient
import sounds as sd
from atmos import (band, conv, entry, eq, kernels, noise_burst, resonant_burst, scatter_train,
                   swell, train)
from dsp import (bandpass, formant_gain, lowpass, midi_hz, pan, phase_of, place, ramp_in, secs,
                 times, wobble)
from wildlife import calls, syllable
from weather import k_bubble, k_dust, k_leaf

# --- talkers ---------------------------------------------------------------------------

VOWELS = ((750, 1250, 2500), (550, 1750, 2500), (400, 2000, 2650), (300, 2250, 2950),
          (500, 900, 2400), (350, 800, 2300), (650, 1100, 2450))

# Pace (syllables/s), men's and women's pitch, share of women, intonation range, phrase and
# pause lengths, chance a phrase ends rising, how often people laugh and call out, and the
# space: (room, wet).
CHARACTERS = {
    "latin": dict(rate=(5.0, 6.2), f0=(95, 135), f0w=(180, 240), women=0.4, range=1.0,
                  phrase=(0.7, 1.8), pause=(0.2, 0.8), rise=0.15, laugh=1.0, calls=1.0,
                  room=((1.4, 1.0, 0.5, 0.012), 0.45)),
    "greek": dict(rate=(4.5, 5.4), f0=(100, 150), f0w=(185, 235), women=0.12, range=1.5,
                  phrase=(1.2, 3.0), pause=(0.3, 1.0), rise=0.35, laugh=0.6, calls=0.7,
                  room=((0.9, 0.7, 0.4, 0.01), 0.3)),
    "persian": dict(rate=(3.5, 4.3), f0=(88, 125), f0w=(170, 215), women=0.2, range=0.6,
                    phrase=(1.5, 3.5), pause=(0.6, 1.8), rise=0.05, laugh=0.25, calls=0.35,
                    room=((2.4, 1.8, 0.7, 0.025), 0.55)),
}


def talker(dur, rng, c, f0, female, ceiling=3200.0):
    """One person talking with no words, for `dur` seconds, in character `c`."""
    n = secs(dur)
    t = times(n)
    rate = rng.uniform(*c["rate"])
    k = int(dur * rate) + 3
    onsets = np.cumsum(rng.uniform(0.6, 1.4, k) / rate) - 0.1
    scale = 1.15 if female else 1.0
    vow = rng.integers(len(VOWELS), size=k)
    form = [np.interp(t, onsets, [VOWELS[v][i] * scale for v in vow]) for i in range(3)]
    syll = 0.5 - 0.5 * np.cos(2 * np.pi * np.interp(t, onsets, np.arange(k)))
    stress = np.interp(t, onsets, rng.choice([1.0, 1.0, 1.0, 1.4], k))
    gate = np.zeros(n)
    contour = np.ones(n)
    at = rng.uniform(0, 0.6)
    while at < dur:
        length = rng.uniform(*c["phrase"])
        a, b = secs(at), min(n, secs(at + length))
        if b > a:
            m = b - a
            gate[a:b] = np.sin(np.pi * np.arange(m) / m) ** 0.25
            x = np.arange(m) / m
            fall = 1 + 0.12 * c["range"] * (0.5 - x)
            if rng.random() < c["rise"]:
                fall += 0.25 * c["range"] * np.clip((x - 0.8) / 0.2, 0, 1) ** 2
            contour[a:b] = fall
        at += length + rng.uniform(*c["pause"])
    gate = lowpass(gate, 18, 2)
    pitch = f0 * contour * (1 + 0.3 * c["range"] * (stress - 1)) * wobble(n, rng, 0.006, 25)
    ph = phase_of(pitch)
    voiced = np.zeros(n)
    formants = [(form[0], 90, 1.0), (form[1], 130, 0.6), (form[2], 200, 0.25)]
    for h in range(1, 40):
        fh = h * pitch
        if fh.min() > ceiling:
            break
        voiced += h**-1.1 * (formant_gain(fh, formants) + 0.02) * np.sin(h * ph)
    voiced *= syll * stress
    voiced /= np.std(voiced) + 1e-12
    # Consonants at the syllable onsets: hisses, hushes, stops and breathy 'h's.
    env = {key: np.zeros(n) for key in ("s", "sh", "stop", "h")}
    for o in onsets:
        if o < 0 or rng.random() > 0.6:
            continue
        kind = rng.choice(["s", "sh", "stop", "h"], p=[0.25, 0.15, 0.35, 0.25])
        d = {"s": 0.08, "sh": 0.07, "stop": 0.015, "h": 0.04}[kind]
        m = secs(d)
        place(env[kind], np.hanning(m) * rng.uniform(0.5, 1.0), secs(o))
    noise = rng.standard_normal(n)
    cons = (0.25 * bandpass(noise, 3800, 6500) * env["s"] + 0.25 * bandpass(noise, 1800, 4000) * env["sh"]
            + 0.5 * bandpass(noise, 400, 4000) * env["stop"] + 0.12 * bandpass(noise, 500, 2500) * env["h"])
    return lowpass((voiced + 3.0 * cons) * gate, ceiling, 2)


def person(rng, c):
    female = rng.random() < c["women"]
    return rng.uniform(*(c["f0w"] if female else c["f0"])), female


def laugh(rng, c):
    """A burst of laughter: breathy 'ha's falling in pitch."""
    f0, _ = person(rng, c)
    parts = []
    for k in range(int(rng.integers(4, 8))):
        f = f0 * (1.6 - 0.08 * k)
        parts.append((syllable(rng, 0.12, [(0, f), (1, f * 0.9)],
                               [(750, 130, 1.0), (1250, 160, 0.5), (2500, 250, 0.15)], tilt=1.1,
                               breath=0.6, attack=0.01, release=0.05, puff=0.6) * (1 - 0.08 * k),
                      0.19 * k))
    return calls(parts, rng)


def call_out(rng, c):
    """Someone calling out across the street or square: a sung-out 'hey-oh'."""
    f0, _ = person(rng, c)
    dur = rng.uniform(0.45, 0.9)
    f = f0 * rng.uniform(1.6, 2.0)
    return syllable(rng, dur, [(0, f * 0.9), (0.2, f), (1, f * 0.85)],
                    [([(0, 550), (0.3, 750), (1, 500)], 130, 1.0),
                     ([(0, 1750), (0.3, 1200), (1, 900)], 160, 0.5), (2500, 250, 0.15)],
                    tilt=1.0, breath=0.2, attack=0.03, release=0.12, vib=(5.5, 0.012), puff=0.4)


def clap(rng):
    """One clap of cupped hands."""
    return resonant_burst(rng, 0.03, rng.uniform(900, 1800), 2.5, 0.004, 300, 5000)


def clapping(rng, dur, people, shape):
    """`people` clapping, each at their own pace, the whole following envelope `shape`."""
    n = secs(dur)
    out = np.zeros(n + secs(0.1))
    for _ in range(people):
        rate = rng.uniform(3.5, 6.0)
        at = rng.uniform(0, 0.4)
        c = clap(rng) * rng.uniform(0.4, 1.0)
        while at < dur:
            place(out, c * rng.uniform(0.7, 1.0) * shape(at), secs(at))
            at += rng.normal(1 / rate, 0.01)
    return out[:n]


SIZES = (dict(name="a handful", talkers=4, far=0, callers=0, dist=(0.25, 0.5), extras=0.0),
         dict(name="a market", talkers=14, far=8, callers=3, dist=(0.3, 0.8), extras=1.0),
         dict(name="a festival", talkers=28, far=18, callers=6, dist=(0.3, 0.9), extras=1.6))
CROWD_LUFS = (-27.0, -23.5, -20.0)
CROWD_S = 34.0  # shares no factor with the 30 s wind and 32 s nature beds it plays over
# The talkers' voices stop at 3.2 kHz, which left the crowds some 6 dB dull at 1 kHz and 20 dB
# at 4 kHz against long-term speech spectra (voices behind a wall): a shelf and a presence
# lift put back the consonants and the near voices' edge; a dip at 420 Hz takes off the boxiness
# of many vowels piled on one another.
CROWD_EQ = (("peak", 420.0, -3.0, 0.8), ("high", 1300.0, 6.0, 0.7), ("peak", 2700.0, 3.0, 0.9))
CROWD_SURGE = (0.12, 0.16, 0.2)  # how far a crowd's talk swells and ebbs, by size


def crowd(character, level):
    """Wordless people in a street, square or court: a handful talking, a market's worth,
    a festival's worth, each in its character's pace, pitch and space."""
    c = CHARACTERS[character]
    s = SIZES[level]

    def render(rng, length=CROWD_S):
        n = secs(length)
        b = sd.Bed(length, rng, tail=length + 5)  # each talker runs the whole loop
        for _ in range(s["talkers"]):
            f0, female = person(rng, c)
            b.add(talker(length, rng, c, f0, female), rng.uniform(0, length), rng.uniform(-0.85, 0.85),
                  rng.uniform(*s["dist"]), rng.uniform(0.5, 1.0))
        for _ in range(int(round(s["callers"] * c["calls"]))):
            b.add(call_out(rng, c), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.4, 0.8), 0.6)
        for _ in range(int(round((1 + s["talkers"] / 4) * c["laugh"]))):
            b.add(laugh(rng, c), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.7), 0.5)
        if s["extras"]:
            for _ in range(int(40 * s["extras"])):
                b.add(foot(rng, "stone" if character != "persian" else "earth"), rng.uniform(0, length),
                      rng.uniform(-0.9, 0.9), rng.uniform(0.2, 0.7), rng.uniform(0.15, 0.4))
            for _ in range(int(8 * s["extras"])):
                b.add(sd.clink(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.7), 0.25)
            if character == "persian":  # the camp: animals' bells and a horse
                b.add(sd.bells_walking(rng, 10.0, 1050, 1.2), rng.uniform(0, length), -0.5, 0.7, 0.3)
                b.add(lowpass(sd.snort(rng), 2500), rng.uniform(0, length), 0.6, 0.6, 0.4)
        out = b.finish(*c["room"])
        if s["far"]:  # the rest of the crowd, too far to tell apart
            far = sd.Bed(length, rng, tail=length + 5)
            for _ in range(s["far"]):
                f0, female = person(rng, c)
                far.add(talker(length, rng, c, f0, female, 2000.0), rng.uniform(0, length),
                        rng.uniform(-0.9, 0.9), 0.9, rng.uniform(0.5, 1.0))
            out = out + far.finish(*c["room"])
        if level == 2:  # festival: swells of the whole crowd and a little clapping
            for _ in range(2):
                at = rng.uniform(0, length - 4)
                out[secs(at):secs(at) + secs(3.5)] += 0.4 * pan(cheer_voices(rng, c, 3.5, 12), 0)
            claps = clapping(rng, 4.0, 10, lambda a: np.sin(np.pi * a / 4.0))
            k = secs(rng.uniform(0, length - 4))
            out[k:k + len(claps)] += 0.3 * pan(lowpass(claps, 5000), rng.uniform(-0.5, 0.5))
        # The whole crowd's talk swells and ebbs (a story told, a stall's bargain struck).
        out = out * swell(n, rng, 0.06, CROWD_SURGE[level], 0.3)[:, None]
        return eq(out, CROWD_EQ)

    return render


def cheer_voices(rng, c, dur, people, rise=True):
    """Many voices shouting together, 'ahh-oh', swelling."""
    n = secs(dur)
    out = np.zeros(n)
    for _ in range(people):
        f0, _ = person(rng, c)
        f = f0 * rng.uniform(1.5, 2.1)
        d = rng.uniform(0.6, 1.0) * dur
        x = syllable(rng, d, [(0, f * 0.9), (0.3, f * (1.12 if rise else 1.0)), (1, f * 0.8)],
                     [([(0, 750), (1, 500)], 130, 1.0), ([(0, 1250), (1, 900)], 160, 0.5),
                      (2500, 250, 0.12)], tilt=1.0, breath=0.35, attack=0.15, release=0.4)
        place(out, x * rng.uniform(0.4, 1.0), secs(rng.uniform(0, dur - d)))
    return lowpass(out, 3500, 2)


# --- feet, hooves, wheels --------------------------------------------------------------


def grains(rng, dur, count, lo, hi):
    out = np.zeros(secs(dur))
    for _ in range(count):
        k = int(rng.beta(1.3, 3.0) * (len(out) - secs(0.004)))
        place(out, noise_burst(rng, 0.004, lo, hi, 0.0008) * rng.uniform(0.2, 1.0), k)
    return out


def foot(rng, surface):
    """One footstep, heel then ball of the foot, on stone, earth, timber, stone steps,
    grass or a gravel path."""
    out = np.zeros(secs(0.35))
    toe_at = rng.uniform(0.05, 0.08)
    for part, lv in (("heel", 1.0), ("toe", 0.6)):
        at = 0.0 if part == "heel" else toe_at
        m = secs(0.12)
        tm = times(m)
        thud = np.sin(2 * np.pi * rng.uniform(80, 130) * tm) * np.exp(-tm / 0.012)
        if surface == "stone":
            x = thud + 0.6 * noise_burst(rng, 0.12, 1000, 5500, 0.002) + \
                0.3 * noise_burst(rng, 0.12, 600, 3000, 0.012, 0.004)
        elif surface == "earth":
            x = 1.2 * np.sin(2 * np.pi * rng.uniform(65, 100) * tm) * np.exp(-tm / 0.018) + \
                0.7 * grains(rng, 0.12, 18, 600, 3000)
        elif surface == "timber":
            f = rng.uniform(140, 220)
            x = sd.modes(m, [f, f * 2.3, f * 3.9], [1.0, 0.5, 0.2], [0.04, 0.02, 0.01], rng) + \
                0.4 * noise_burst(rng, 0.12, 800, 4000, 0.002)
        elif surface == "stair":
            x = 1.3 * thud + 0.5 * noise_burst(rng, 0.12, 1000, 5000, 0.002)
            if part == "toe":
                x = x + 0.5 * noise_burst(rng, 0.12, 800, 3500, 0.03, 0.02)
        elif surface == "grass":
            x = 0.6 * thud + 0.8 * noise_burst(rng, 0.12, 1500, 5000, 0.03, 0.02)
        else:  # path: packed earth and fine gravel
            x = 0.8 * thud + 1.0 * grains(rng, 0.12, 45, 800, 4500)
        place(out, lv * x, secs(at))
    if surface == "timber" and rng.random() < 0.35:
        place(out, 0.15 * sd.creak_short(rng, 0.15, 120), secs(0.05))
    return out


def step_fx(surface):
    return lambda rng: sd.finish_sfx(lowpass(foot(rng, surface), 6000, 4), rng, 0.08, 0.3,
                                     fade_out=0.02)


def walk_group(rng, length=8.0):
    """A few people walking past on paving, each at their own pace."""
    b = sd.Bed(length, rng, tail=3.0)
    for _ in range(5):
        steps = int(rng.integers(13, 17))
        pos, dist, lv = rng.uniform(-0.8, 0.8), rng.uniform(0.2, 0.6), rng.uniform(0.5, 1.0)
        off = rng.uniform(0, length)
        for k in range(steps):
            b.add(foot(rng, "stone"), off + k * length / steps, pos, dist, lv * (0.85 + 0.15 * (k % 2)))
    return b.finish((1.0, 0.7, 0.3, 0.01), 0.25)


def march(rng, length=8.0):
    """A file of guards or soldiers marching in step on stone: feet together on the beat,
    gear clinking and rattling."""
    b = sd.Bed(length, rng, tail=3.0)
    for _ in range(14):
        pos, dist = rng.uniform(-0.6, 0.6), rng.uniform(0.25, 0.6)
        for k in range(16):
            at = k * length / 16 + rng.normal(0, 0.008)
            b.add(foot(rng, "stone"), at, pos, dist, 0.6 + 0.4 * (k % 2 == 0))
            if rng.random() < 0.3:
                f = rng.uniform(2200, 3800)
                b.add(sd.modes(secs(0.06), [f, f * 1.5], [1.0, 0.4], [0.01, 0.006], rng), at + 0.03,
                      pos, dist, 0.15)
    return b.finish((1.2, 0.9, 0.4, 0.012), 0.3)


def hoof_earth(rng):
    """A hoof on a dirt road: a dull thump and a spatter of earth."""
    m = secs(0.15)
    x = sd.modes(m, [rng.uniform(70, 120), rng.uniform(180, 260)], [1.0, 0.4], [0.03, 0.015], rng)
    return x + 0.5 * grains(rng, 0.15, 14, 500, 2500)


def hooves_walk(rng, length=8.0):
    """A horse or mule walking on paving, its harness bells and tack jingling softly."""
    b = sd.Bed(length, rng, tail=3.0)
    beats = int(round(length / 0.28))
    for k in range(beats):
        at = k * length / beats + rng.normal(0, 0.008)
        b.add(sd.hoof(rng, "stone"), at, 0.1, 0.3, rng.uniform(0.6, 1.0))
        if k % 2 == 0:
            b.add(sd.bell(rng.uniform(1900, 2100), rng, 0.3, "crotal"), at + 0.02, 0.1, 0.35, 0.08)
    b.add(sd.creak_short(rng, 0.4, 90), rng.uniform(0, length), 0.1, 0.3, 0.1)
    return b.finish((0.9, 0.7, 0.3, 0.01), 0.25)


def cart_earth(rng, length=10.0):
    """An ox-cart on a dirt road: solid wooden wheels rumbling and squealing on their
    axle, the frame knocking, the oxen's slow hooves."""
    n = secs(length)
    rumble = band(n, rng, 40, 300, 0.9, 1) * swell(n, rng, 0.8, 0.2)
    grit = ambience.crackle(n, rng, 120 * np.ones(n), 500, 3000)
    b = sd.Bed(length, rng, tail=3.0)
    turns = int(round(length / 2.5))
    for k in range(turns):
        b.add(sd.creak_short(rng, rng.uniform(0.5, 0.8), rng.uniform(150, 240)), k * length / turns, 0.0, 0.3, 0.3)
    for _ in range(6):
        f = rng.uniform(150, 300)
        b.add(sd.modes(secs(0.15), [f, f * 2.4], [1.0, 0.3], [0.03, 0.015], rng), rng.uniform(0, length), 0.0, 0.3, 0.4)
    steps = int(round(length / 0.65))
    for k in range(steps):
        b.add(hoof_earth(rng), k * length / steps, -0.15 if k % 2 else 0.15, 0.35, 0.5)
    return sd.mix({"rumble": 0.25 * pan(rumble, 0), "grit": 0.15 * pan(grit, 0),
                   "parts": b.finish((0.9, 0.7, 0.3, 0.01), 0.2)})


# --- work ------------------------------------------------------------------------------


def mill(rng, length=10.0):
    """A donkey mill at a bakery: the hourglass stone grinding round, grain crunching
    between the stones, the donkey's slow steps, the beam creaking once a turn."""
    n = secs(length)
    turn = length / 2
    t = times(n)
    roll = 1 + 0.25 * np.sin(2 * np.pi * t / turn)
    grind = band(n, rng, 40, 700, 0.9, 1) * roll
    crunch = ambience.crackle(n, rng, 400 * roll, 800, 3500)
    b = sd.Bed(length, rng, tail=3.0)
    for k in range(2):
        b.add(sd.creak_short(rng, 0.9, 60), k * turn + 1.0, 0.2, 0.3, 0.5)
    steps = int(round(length / 0.7))
    for k in range(steps):
        b.add(hoof_earth(rng), k * length / steps, 0.4 * np.sin(2 * np.pi * k / steps * 2), 0.35, 0.35)
    return sd.mix({"grind": 0.35 * pan(grind, 0), "crunch": 0.25 * pan(crunch, 0),
                   "rest": b.finish((0.8, 0.6, 0.3, 0.01), 0.25)})


def bakery(rng, length=10.0):
    """A bakery at work: dough slapped and kneaded on the board, the peel scraping the oven
    floor, the oven's fire breathing."""
    b = sd.Bed(length, rng, tail=3.0)
    for k in range(8):
        b.add(sd.slap(rng), k * 1.15 + rng.normal(0, 0.03), -0.3, 0.25, rng.uniform(0.6, 1.0))
    m = secs(0.7)
    scrape = bandpass(rng.standard_normal(m), 500, 3000) * np.sin(np.pi * np.arange(m) / m) ** 1.5
    b.add(0.3 * scrape, rng.uniform(0, length), 0.4, 0.3)
    fire = sd.fire(length, rng, 0.4)
    return b.finish((0.9, 0.6, 0.3, 0.01), 0.25) + 0.25 * pan(fire, 0.4)


def press(rng, length=12.0):
    """An olive press: the great beam groaning under its weights, oil trickling into the
    vat, wedges knocked tighter."""
    n = secs(length)
    b = sd.Bed(length, rng, tail=3.0)
    for k in range(2):
        b.add(sd.creak_short(rng, 1.6, rng.uniform(35, 50)), k * 6 + rng.uniform(0, 2), 0.1, 0.3, 0.7)
    for k in range(2):
        f = rng.uniform(250, 400)
        b.add(sd.modes(secs(0.2), [f, f * 2.2], [1.0, 0.4], [0.04, 0.02], rng), k * 6 + 4, -0.2, 0.3, 0.6)
    oil = scatter_train(n, rng, 25, kernels(lambda r: k_bubble(r, 500, 1600), 5, rng), channels=1)[:, 0]
    return b.finish((0.9, 0.7, 0.3, 0.01), 0.25) + 0.4 * pan(oil, 0.3)


def saw(rng, length=8.0):
    """Two sawyers working a long saw through cedar: rasping strokes back and forth."""
    b = sd.Bed(length, rng, tail=2.0)
    strokes = int(round(length / 0.6))
    for k in range(strokes):
        m = secs(0.55)
        tm = times(m)
        teeth = 0.55 + 0.45 * np.sin(2 * np.pi * rng.uniform(60, 90) * tm)
        rasp = bandpass(rng.standard_normal(m), 900, 5000) * teeth
        rasp = rasp * np.sin(np.pi * tm / 0.55) ** 1.2 * (1.0 if k % 2 else 0.8)
        wood = resonant_burst(rng, 0.55, 450, 3, 0.2) * 0.3
        b.add(rasp + wood, k * length / strokes, -0.2 if k % 2 else 0.2, 0.3, 0.8)
    return b.finish((0.8, 0.6, 0.3, 0.01), 0.2)


def threshing(rng, length=12.0):
    """A threshing floor: a sledge dragged round by oxen over the sheaves, straw crunching,
    hooves on the packed earth, chaff hissing."""
    n = secs(length)
    t = times(n)
    gait = 1 + 0.3 * np.sin(2 * np.pi * t / (length / 9))
    crunch = np.stack([ambience.crackle(n, rng, 600 * gait, 500, 3500) for _ in range(2)], axis=1)
    rumble = band(n, rng, 40, 400, 0.9) * gait[:, None]
    b = sd.Bed(length, rng, tail=3.0)
    steps = int(round(length / 0.65))
    for k in range(steps):
        b.add(hoof_earth(rng), k * length / steps, 0.3 * np.sin(2 * np.pi * k / steps), 0.35, 0.5)
    return sd.mix({"crunch": 0.2 * crunch, "rumble": 0.2 * rumble,
                   "chaff": 0.03 * band(n, rng, 1500, 5000, 0.3),
                   "hooves": b.finish((0.8, 0.6, 0.3, 0.01), 0.2)})


def fullers(rng, length=8.0):
    """Fullers treading cloth in their vats: rhythmic sloshing, a foot at a time."""
    b = sd.Bed(length, rng, tail=2.0)
    steps = 16
    for k in range(steps):
        m = secs(0.35)
        slosh = lowpass(rng.standard_normal(m), 1200, 2) * np.exp(-times(m) / 0.08)
        for _ in range(4):
            place(slosh, 0.5 * k_bubble(rng, 300, 1100), secs(rng.uniform(0.02, 0.15)))
        b.add(slosh, k * length / steps + rng.normal(0, 0.02), -0.3 if k % 2 else 0.3, 0.3, 0.8)
    return b.finish((1.0, 0.8, 0.3, 0.012), 0.3)


def chop(rng):
    """An adze or axe biting into cedar: a woody crack and the timber's ring."""
    m = secs(0.35)
    f = rng.uniform(300, 520)
    return sd.modes(m, [f, f * 2.1, f * 3.3], [1.0, 0.5, 0.25], [0.05, 0.025, 0.012], rng) + \
        0.8 * noise_burst(rng, 0.35, 600, 5500, 0.01)


def brick(rng):
    """Wet clay slapped into a brick mould, the wooden frame knocking."""
    out = np.zeros(secs(0.4))
    place(out, sd.slap(rng), 0)
    place(out, 0.5 * sd.modes(secs(0.15), [380, 820], [1.0, 0.4], [0.02, 0.01], rng), secs(0.18))
    return out


def stylus(rng):
    """A scribe's stylus pressing wedges into a wet clay tablet."""
    out = np.zeros(secs(0.5))
    for k in range(int(rng.integers(3, 6))):
        x = noise_burst(rng, 0.06, 1200, 4500, 0.012, 0.004) + 0.4 * noise_burst(rng, 0.06, 200, 900, 0.01)
        place(out, x * rng.uniform(0.6, 1.0), secs(0.09 * k))
    return out


def sickle(rng):
    """A sickle sweeping through a handful of standing barley."""
    m = secs(0.45)
    swish = bandpass(rng.standard_normal(m), 1500, 5500) * np.sin(np.pi * np.arange(m) / m) ** 2
    return 0.5 * swish + 0.8 * grains(rng, 0.45, 60, 900, 4000)


def amphora(rng):
    """An amphora set down on stone: a deep clay thunk and a short ring."""
    m = secs(0.5)
    return sd.modes(m, [rng.uniform(160, 210), rng.uniform(400, 460), rng.uniform(880, 980)],
                    [1.0, 0.5, 0.3], [0.05, 0.04, 0.06], rng) + 0.3 * noise_burst(rng, 0.5, 300, 2500, 0.006)


def smash(rng):
    """A used amphora broken up for the sherd mound: a crash and shards skittering."""
    out = np.zeros(secs(1.2))
    place(out, noise_burst(rng, 0.4, 200, 5000, 0.06), 0)
    place(out, 0.8 * amphora(rng), 0)
    for _ in range(30):
        place(out, 0.4 * sd.clink(rng) * rng.uniform(0.3, 1.0), secs(abs(rng.normal(0.1, 0.25))))
    return out


def fish(rng):
    """A fish slapped down on the stone of the market counter, and a flop."""
    out = np.zeros(secs(0.6))
    place(out, lowpass(noise_burst(rng, 0.15, 200, 3000, 0.02), 2500, 2), 0)
    place(out, 0.4 * lowpass(noise_burst(rng, 0.1, 200, 2500, 0.015), 2500, 2), secs(0.3))
    return out


def bronze(rng):
    """A hammer tapping a bronze shield blank: a bright, ringing tap."""
    m = secs(0.8)
    f = rng.uniform(900, 1200)
    return sd.modes(m, [f, f * 2.4, f * 3.7, f * 5.1], [1.0, 0.6, 0.35, 0.15], [0.3, 0.18, 0.1, 0.05], rng) + \
        0.3 * noise_burst(rng, 0.8, 1500, 6000, 0.003)


def watering(rng):
    """Laeticia's watering can: a slosh as she tips it, a shower of fine drops on soil and
    leaves, the last drips."""
    dur = 2.2
    n = secs(dur)
    t = times(n)
    out = np.zeros(n)
    place(out, 0.5 * lowpass(rng.standard_normal(secs(0.25)), 900, 2) * np.hanning(secs(0.25)), 0)
    flow = np.clip((t - 0.2) / 0.15, 0, 1) * np.clip((1.75 - t) / 0.2, 0, 1)
    drops = conv(train(n, rng, 260 * flow, 0.5), k_leaf(rng)) + conv(train(n, rng, 140 * flow, 0.5), k_dust(rng))
    hiss = bandpass(rng.standard_normal(n), 600, 4000) * flow * 0.06
    out = out + 0.6 * drops + hiss
    for at in (1.85, 2.0):
        place(out, 0.4 * k_bubble(rng, 900, 1800), secs(at))
    return out


def fx(make, wet=0.1, size=0.4, fade=0.04):
    """An effect in a little air, at most 4 s long (the room's tail is faded out by then)."""
    return lambda rng: sd.finish_sfx(make(rng), rng, wet, size, fade_out=fade, longest=4.0)


# --- crowd responses, songs ------------------------------------------------------------

LATIN, GREEK, PERSIAN = (CHARACTERS[k] for k in ("latin", "greek", "persian"))


def applause(rng):
    """A crowd applauding: clapping rises, holds and thins."""
    dur = 3.2
    return clapping(rng, dur, 28, lambda a: min(1.0, a / 0.3) * min(1.0, (dur - a) / 1.2))


def cheer(rng):
    """A crowd cheering: voices shouting up together over clapping."""
    out = cheer_voices(rng, LATIN, 3.0, 30)
    claps = clapping(rng, 3.0, 12, lambda a: min(1.0, a / 0.5) * min(1.0, (3.0 - a) / 1.0))
    return out + 0.3 * claps[: len(out)]


def hush(rng):
    """A crowd falling quiet: the murmur drops away under a few 'shh's."""
    dur = 3.4
    n = secs(dur)
    t = times(n)
    out = np.zeros(n)
    for _ in range(8):
        f0, female = person(rng, LATIN)
        out += talker(dur, rng, LATIN, f0, female) * rng.uniform(0.3, 0.6)
    out *= np.clip((2.2 - t) / 1.6, 0, 1) ** 1.5
    for _ in range(4):
        m = secs(rng.uniform(0.4, 0.7))
        sh = bandpass(rng.standard_normal(m), 2000, 5500) * np.sin(np.pi * np.arange(m) / m) ** 1.5
        place(out, 0.6 * sh, secs(rng.uniform(0.4, 1.6)))
    return out


def acclamation(rng):
    """Rome: a crowd's rhythmic acclamation, three wordless two-beat shouts ('ho-HEY')."""
    out = np.zeros(secs(3.4))
    for k in range(3):
        place(out, cheer_voices(rng, LATIN, 0.35, 20, False), secs(0.95 * k))
        place(out, 1.2 * cheer_voices(rng, LATIN, 0.5, 20), secs(0.95 * k + 0.35))
    return out


def ololyge(rng):
    """Athens: the women's ritual cry at the moment of sacrifice, a high trilling call
    taken up by several voices."""
    parts = []
    for v in range(6):
        f = rng.uniform(650, 900)
        d = rng.uniform(1.4, 2.2)
        parts.append((syllable(rng, d, [(0, f * 0.9), (0.2, f), (1, f * 0.85)],
                               [(800, 130, 1.0), (1200, 160, 0.4), (2800, 250, 0.1)], tilt=1.0,
                               breath=0.2, attack=0.1, release=0.3, vib=(11, 0.06), trem=(11, 0.6)),
                      rng.uniform(0, 0.9)))
    return lowpass(calls(parts, rng), 4000, 2)


def response(rng):
    """Pārsa: a court's measured response, many low voices in near unison on two notes of
    the city's mode (D, then A below)."""
    n = secs(3.2)
    out = np.zeros(n)
    for _ in range(18):
        f0 = float(midi_hz(50)) * rng.uniform(0.99, 1.01)
        a = syllable(rng, 1.0, [(0, f0), (1, f0)], [(700, 120, 1.0), (1100, 160, 0.45), (2500, 250, 0.08)],
                     tilt=1.3, breath=0.2, attack=0.12, release=0.25)
        b = syllable(rng, 1.4, [(0, f0 * 0.75), (1, f0 * 0.74)], [(450, 110, 1.0), (800, 150, 0.45),
                                                                   (2500, 250, 0.06)],
                     tilt=1.3, breath=0.2, attack=0.12, release=0.5)
        at = rng.normal(0.1, 0.03)
        place(out, a * rng.uniform(0.6, 1.0), secs(max(0.0, at)))
        place(out, b * rng.uniform(0.6, 1.0), secs(max(0.0, at + 1.05)))
    return lowpass(out, 2500, 2)


def chorus_far(rng):
    """A chorus singing far off, a hymn on an open vowel heard across the city: men and
    boys an octave apart, on the white-key tones every city's mode shares."""
    tune = ((0.0, 0.55, 57), (0.55, 0.55, 60), (1.1, 0.8, 62), (1.9, 0.45, 64), (2.35, 0.45, 62),
            (2.8, 0.5, 60), (3.3, 0.6, 62))
    notes = [(s, d, float(midi_hz(m))) for s, d, m in tune]
    x = sd.song(notes, rng, voices=6, vowel="a") + 0.5 * sd.song(notes, rng, 2.0, voices=4, vowel="o")
    return lowpass(x, 2000, 2) * ramp_in(len(x), secs(0.5))  # the voices' onsets would spike


def wedding_song(rng):
    """A wedding procession passing: voices singing a lively tune, a pipe weaving round it,
    hands clapping on the beat (white-key tones, at home in every city's mode)."""
    beat = 0.36
    tune = (64, 67, 69, 67, 64, 62, 64, 67, 69, 71)
    notes = [(k * beat, beat * 0.95, float(midi_hz(m))) for k, m in enumerate(tune)]
    x = sd.song(notes, rng, voices=5, vowel="a")
    pipe = ancient.reed_phrase("pipe", [(s, d, h * 2, 0.6, k > 0, ()) for k, (s, d, h) in enumerate(notes)],
                               len(x), rng)
    out = x + 0.25 * pipe
    for k in range(len(tune)):
        for _ in range(5):
            place(out, 0.25 * clap(rng), secs(k * beat + abs(rng.normal(0, 0.012))))
    return lowpass(out, 4500, 2)


# --- files -----------------------------------------------------------------------------

W = "world"
FILES = {}
for _surface in ("stone", "earth", "timber", "stair"):
    for _k in range(3):
        FILES[f"sfx/{W}/step_{_surface}_{_k + 1}.wav"] = entry(
            "sfx", step_fx(_surface), -28.0, f"One footstep on {_surface}, variation {_k + 1}.",
            gain=0.6, tags=["steps", _surface])
FILES.update({
    f"amb/{W}/walk_group.ogg": entry("loop", walk_group, -25.0, "A few people walking past on paving.",
                                     when="moving", where="positional: groups of walkers on stone",
                                     tags=["steps", "stone", "group"]),
    f"amb/{W}/march.ogg": entry("loop", march, -24.0, "A file of guards marching in step, gear clinking.",
                                when="moving", where="positional: guard changes, soldiers, the march (P8)",
                                tags=["steps", "stone", "march"]),
    f"sfx/{W}/hoof_earth_1.wav": entry("sfx", fx(hoof_earth), -26.0,
                                       "One hoof on a dirt road.", gain=0.7, tags=["hooves", "earth"]),
    f"sfx/{W}/hoof_earth_2.wav": entry("sfx", fx(hoof_earth), -26.0, "One hoof on a dirt road, variation 2.",
                                       gain=0.7, tags=["hooves", "earth"]),
    f"amb/{W}/hooves_walk.ogg": entry("loop", hooves_walk, -25.0,
                                      "A horse or mule walking on paving, harness jingling.",
                                      when="moving", where="positional: ridden or led horses and mules",
                                      tags=["hooves", "stone"]),
    f"amb/{W}/cart_earth.ogg": entry("loop", cart_earth, -25.0,
                                     "An ox-cart on a dirt road: rumble, axle squeal, slow hooves.",
                                     when="moving", where="positional: carts on unpaved roads and tracks",
                                     tags=["cart", "earth"]),
})
for _name, _fn, _desc, _where in (
        ("mill", mill, "A donkey mill grinding grain.", "rome_bread, parsa_bread: the mill slot while worked"),
        ("bakery", bakery, "Kneading, the peel in the oven, the fire.", "bread chains: the bakery slot while worked"),
        ("press", press, "An olive press: the beam groaning, oil trickling.", "rome_oil, athens_oil: the press while worked"),
        ("saw", saw, "Two sawyers working a long saw through cedar.", "parsa_cedar, building sites: a saw slot while worked"),
        ("threshing", threshing, "A threshing floor: sledge, straw, oxen.", "threshing events (Pārsa L3) and grain chains"),
        ("fullers", fullers, "Fullers treading cloth in their vats.", "rome_cloth, parsa_wool: the fullery while worked")):
    FILES[f"amb/{W}/{_name}.ogg"] = entry("loop", _fn, -25.0, _desc, when="worked",
                                          where=f"positional: {_where}", tags=["work", _name])
for _name, _fn, _lufs, _desc in (
        ("chop", chop, -25.0, "An adze or axe biting into cedar (carpenters, parsa_cedar)."),
        ("brick", brick, -26.0, "Clay slapped into a brick mould (brick chains)."),
        ("stylus", stylus, -30.0, "A stylus pressing a clay tablet (parsa_tablets)."),
        ("sickle", sickle, -27.0, "A sickle through barley (reapers L2)."),
        ("amphora", amphora, -25.0, "An amphora set down on stone (oil, wine, grain chains)."),
        ("smash", smash, -24.0, "An amphora broken for the sherd mound (rome_testaccio)."),
        ("fish", fish, -27.0, "A fish slapped on the counter (fish chains)."),
        ("bronze", bronze, -26.0, "A hammer tapping a bronze shield blank (athens_shields).")):
    FILES[f"sfx/{W}/{_name}.wav"] = entry("sfx", fx(_fn), _lufs, _desc, gain=0.7, tags=["work", _name])
for _name, _fn, _lufs, _desc in (
        ("applause", applause, -22.0, "A crowd applauding (theatre, recitations, a verdict)."),
        ("cheer", cheer, -21.0, "A crowd cheering (races, a victor, a festival peak)."),
        ("hush", hush, -24.0, "A crowd falling quiet (a sacrifice, an orator rising)."),
        ("chorus_far", chorus_far, -24.0, "A chorus singing far off (A5, A7 hymns, festivals)."),
        ("wedding_song", wedding_song, -23.0, "A wedding procession singing and clapping (A7, R10).")):
    FILES[f"sfx/{W}/{_name}.wav"] = entry("sfx", fx(_fn, 0.35, 1.2, 0.5), _lufs, _desc, gain=0.9,
                                          tags=["event", "crowd" if _name in ("applause", "cheer", "hush") else "song"])
for _ch, _set in (("latin", "rome"), ("greek", "athens"), ("persian", "parsa")):
    for _lvl, _s in enumerate(SIZES):
        FILES[f"amb/{W}/crowd_{_ch}_{_lvl + 1}.ogg"] = entry(
            "bed", crowd(_ch, _lvl), CROWD_LUFS[_lvl], f"Wordless {_ch} crowd, {_s['name']}.",
            when="day", where=f"count-driven by visible people ({_set} and its region): "
            f"1 up to ~5, 2 up to ~20, 3 beyond; gain = min(1, sqrt(count / full))",
            family=f"crowd.{_ch}", level=_lvl + 1, level_name=_s["name"],
            tags=["crowd", _ch, _set])

ROME = {"sfx/rome/acclamation.wav": entry("sfx", fx(acclamation, 0.4, 1.3, 0.5), -21.0,
                                          "A crowd's rhythmic acclamation (the emperor, a victor, the pompa).",
                                          gain=0.9, tags=["event", "crowd", "ritual"])}
ATHENS = {"sfx/athens/ololyge.wav": entry("sfx", fx(ololyge, 0.35, 1.2, 0.5), -23.0,
                                          "The women's ritual cry at a sacrifice (A1, the feast).",
                                          gain=0.8, tags=["event", "ritual"])}
PARSA = {"sfx/parsa/response.wav": entry("sfx", fx(response, 0.5, 1.8, 0.5), -23.0,
                                         "The court's measured response (audiences, offerings).",
                                         gain=0.8, tags=["event", "ritual"])}
HOME = {}
for _surface in ("grass", "path"):
    for _k in range(3):
        HOME[f"sfx/step_{_surface}_{_k + 1}.wav"] = entry(
            "sfx", step_fx(_surface), -29.0, f"Laeticia's footstep on {_surface}, variation {_k + 1}.",
            gain=0.6, tags=["steps", "laeticia", _surface])
HOME["sfx/watering.wav"] = entry("sfx", fx(watering), -25.0, "Laeticia's watering can over a bed.",
                                 gain=0.8, tags=["laeticia", "water", "work"])
