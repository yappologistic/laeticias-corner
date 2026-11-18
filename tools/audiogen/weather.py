"""Weather as a playable instrument (world set): wind in four strengths for open country,
city streets, the sea and high mountains; rain in three intensities with surface layers the
engine adds by what is on screen; thunder; snow, fog and heat; sea state on open coast and in
harbour; rivers and waterfalls; dust wind; fires; and the turns of weather.

Every intensity family is one recipe sampled at its levels, rendered from independent noise
(so two neighbours played together add in power and never phase) and mastered in steps of
3.5 LU, so the engine can cross-fade by intensity at unity gain."""

import numpy as np

import ambience
import sounds as sd
from atmos import (WATER_EQ, band, conv, entry, eq, gusts, kernels, loop_tone, noise_burst,
                   resonant_burst, scatter_train, slow, swell, train)
from dsp import SR, bandpass, lowpass, pan, place, ramp_in, secs, times

BED_S = 30.0  # weather beds: long enough not to be heard repeating under a changing mix
# Rain is heard for minutes on end: its bed and its surface layers get lengths that share no
# factor with each other or with the 30 s wind and 32 s nature beds, so the mix of a rainy
# view never lines up again for hours, and no layer is short enough to be heard cycling.
RAIN_S = 37.0
LAYER_S = (17.0, 19.0)  # surface layers, sparse and dense (cross-faded, so co-prime too)

# --- wind ------------------------------------------------------------------------------

# One recipe, four strengths: the top of the spectrum, the gust rate and depth, the
# buffeting and how much of each variant's character (leaves, whistles, spray) shows.
WIND = (
    # Gust depths keep each bed's loudness range near the quality bar's 2-5 LU (strong and gale
    # a little above it, 5-7 LU: their gusts are the motion); the engine's gust one-shots and
    # the cross-fade between strengths carry the larger swings.
    dict(name="breath", hi=650.0, gust=0.10, depth=0.15, flutter=0.0, top=0.10, char=0.25),
    dict(name="breeze", hi=1200.0, gust=0.12, depth=0.18, flutter=0.04, top=0.22, char=0.6),
    dict(name="strong", hi=2100.0, gust=0.15, depth=0.22, flutter=0.08, top=0.40, char=1.0),
    dict(name="gale", hi=3100.0, gust=0.18, depth=0.26, flutter=0.14, top=0.62, char=1.3),
)
WIND_LUFS = (-29.0, -25.5, -22.0, -18.5)
# Variant: buffeting scale (streets churn, open sea is smooth) and gust depth scale.
WIND_PLACES = {"open": (1.0, 1.0), "street": (1.5, 1.0), "sea": (0.5, 0.85),
               "mountain": (1.2, 1.15)}


def wind_core(n, rng, p, place_=(1.0, 1.0)):
    """Gusting air in three bands that brighten as a gust peaks; the gust reaches the
    right ear a moment after the left, as it crosses the scene."""
    g = gusts(n, rng, p["gust"], p["depth"] * place_[1], flutter=p["flutter"] * place_[0])
    G = np.stack([g, np.roll(g, secs(0.35))], axis=1)
    low = band(n, rng, 35, p["hi"] * 0.45, 0.8) * G
    mid = band(n, rng, p["hi"] * 0.3, p["hi"], 0.6) * G**1.3
    top = band(n, rng, p["hi"] * 0.8, min(p["hi"] * 2.2, 6500), 0.4) * G**1.8
    return low + 0.7 * mid + p["top"] * top, g, G


def whistle(n, rng, g, base, glide, amount, threshold):
    """An edge tone: a narrow whistle whose pitch rises with the gust and which sounds only
    above `threshold`; a little pitch wander makes it breathy rather than pure."""
    wander = 1 + 0.006 * slow(n, rng, 9.0)
    f = base * (1 + glide * (g - 1)) * wander
    amp = np.clip(g - threshold, 0, None) ** 1.5
    tone = np.sin(loop_tone(f, rng)) + 0.15 * np.sin(2 * loop_tone(f, rng))
    return amount * tone * amp


def flap(n, rng, g, amount, threshold):
    """Cloth in the wind (awnings, a sail, a cloak): a fluttering band of noise that flaps
    faster as the gust rises, and now and then snaps taut."""
    rate = 6 + 6 * np.clip(g, 0, 2)
    am = (0.5 + 0.5 * np.sin(loop_tone(rate, rng))) ** 4
    gate = np.clip(g - threshold, 0, None)
    cloth = band(n, rng, 120, 1800, 0.5, 1) * am * gate
    snap = lambda r: noise_burst(r, 0.12, 250, 4000, 0.015) + 0.5 * resonant_burst(
        r, 0.12, 140, 3, 0.03)
    snaps = conv(train(n, rng, 0.35 * gate**2, 0.3), snap(rng))
    return amount * (cloth + 0.6 * snaps)


def wind(level, where):
    p = WIND[level]

    def render(rng, length=BED_S):
        n = secs(length)
        air, g, G = wind_core(n, rng, p, WIND_PLACES[where])
        c = p["char"]
        layers = {"air": air}
        if where == "open":
            grass = band(n, rng, 900, 4500, 0.3) * G**2
            leaves = np.stack([ambience.crackle(n, rng, 40 * c * G[:, k] ** 2, 1800, 6000)
                               for k in range(2)], axis=1)
            layers.update(grass=0.18 * c * grass, leaves=0.5 * c * leaves)
        elif where == "street":
            tones = sum(whistle(n, rng, g, f, 0.25, 0.35, t) for f, t in
                        ((rng.uniform(480, 560), 0.9), (rng.uniform(760, 860), 1.1),
                         (rng.uniform(1150, 1300), 1.3)))
            cloth = flap(n, rng, g, 1.2 * c, 0.7)
            layers.update(whistles=c * pan(tones, -0.3), awnings=pan(cloth, 0.45))
        elif where == "sea":
            spray = band(n, rng, 1500, 6500, 0.3) * G**3
            layers.update(spray=0.08 * c**2 * spray)
        else:  # mountain: the wind whistles over rock and roars down the crags in gusts
            tones = whistle(n, rng, g, rng.uniform(600, 700), 0.45, 0.3, 0.8) + \
                whistle(n, rng, np.roll(g, secs(4.0)), rng.uniform(950, 1100), 0.5, 0.2, 1.0)
            roar = band(n, rng, 25, 220, 1.0) * G**2
            layers.update(whistles=c * pan(tones, 0.35), roar=0.5 * c * roar)
        if p["name"] == "gale":
            layers["buffet"] = 0.6 * band(n, rng, 20, 120, 1.0) * G**2
        return sd.mix(layers)

    return render


# --- rain ------------------------------------------------------------------------------


def k_drop(rng):
    """A raindrop striking: a tiny bright tick."""
    return noise_burst(rng, 0.03, rng.uniform(1100, 2400), rng.uniform(4500, 7000),
                       rng.uniform(0.0015, 0.004))


def k_splat(rng):
    """A bigger drop: a dull pat and a little splash."""
    return noise_burst(rng, 0.06, 300, 2500, 0.006) + 0.4 * noise_burst(rng, 0.06, 1500, 6000,
                                                                        0.015, 0.003)


def k_bubble(rng, lo=600, hi=2500):
    return sd.bubble(rng, float(np.exp(rng.uniform(np.log(lo), np.log(hi)))))


RAIN = (
    dict(name="light", rate=40, hiss=0.07, big=8, body=0.08, run=0),
    dict(name="moderate", rate=200, hiss=0.4, big=22, body=0.25, run=25),
    dict(name="heavy", rate=650, hiss=1.0, big=45, body=0.7, run=70),
)
RAIN_LUFS = (-27.5, -24.0, -20.5)


def rain(level):
    """Rain in the air and on open ground, neutral as to surface: a hiss of countless far
    drops, nearer ticks and pats, and in harder rain the body of the downpour and runoff."""
    p = RAIN[level]

    def render(rng, length=RAIN_S):
        n = secs(length)
        s = swell(n, rng, 0.04, 0.22, 0.4)
        S = s[:, None]
        layers = {
            "hiss": p["hiss"] * band(n, rng, 500, 6500, 0.35) * S,
            "drops": 0.9 * scatter_train(n, rng, p["rate"] * s, kernels(k_drop, 12, rng)),
            "pats": 0.6 * scatter_train(n, rng, p["big"] * s, kernels(k_splat, 8, rng)),
        }
        if p["body"]:
            layers["body"] = p["body"] * band(n, rng, 70, 900, 1.0) * S
        if p["run"]:
            ks = kernels(lambda r: k_bubble(r, 250, 900), 6, rng)
            layers["runoff"] = 0.5 * scatter_train(n, rng, p["run"] * s, ks, spread=0.5)
        return eq(sd.mix(layers), WATER_EQ)

    return render


def k_leaf(rng):
    """A drop on a leaf: a soft high pat and the leaf's flex."""
    return noise_burst(rng, 0.04, rng.uniform(1300, 2200), 5500, rng.uniform(0.002, 0.004)) + \
        0.5 * noise_burst(rng, 0.04, 350, 1300, 0.008)


def k_tile(rng):
    """A drop on a fired roof tile: a dry ceramic tick with a short ring."""
    n = secs(0.04)
    f = rng.uniform(2200, 3800)
    ring = sd.modes(n, [f, f * 1.47], [1.0, 0.4], [0.004, 0.0025], rng)
    return 0.6 * ring + noise_burst(rng, 0.04, 1500, 6500, 0.0015)


def k_stone(rng):
    """A drop on stone paving: a flat splat with a fine spray."""
    return noise_burst(rng, 0.05, 700, 5500, rng.uniform(0.002, 0.003)) + \
        0.35 * noise_burst(rng, 0.05, 2000, 6500, 0.012, 0.002)


def k_water(rng):
    """A drop on still water: a tiny tick and, often, a rising plink."""
    tick = noise_burst(rng, 0.06, 1500, 6000, 0.0015)
    if rng.random() < 0.6:
        place(tick, 0.7 * k_bubble(rng, 900, 3500), 0)
    return tick


def k_canvas(rng):
    """A drop on a taut canvas awning: a soft drum tap."""
    n = secs(0.12)
    f = rng.uniform(180, 380)
    return sd.modes(n, [f, f * 1.6, f * 2.3], [1.0, 0.45, 0.2], [0.04, 0.025, 0.012], rng) + \
        0.3 * noise_burst(rng, 0.12, 300, 2500, 0.004)


def k_dust(rng):
    """A first heavy drop on dry dust: a dull thud and a puff."""
    n = secs(0.12)
    return sd.modes(n, [rng.uniform(80, 160)], [1.0], [0.02], rng) + \
        0.5 * noise_burst(rng, 0.12, 200, 1600, 0.02, 0.002)


# Surface: (kernel, events per second sparse/dense, extra layer at dense).
SURFACES = {
    "leaves": (k_leaf, (35, 260), "drip"),
    "roof": (k_tile, (40, 300), "gutter"),
    "stone": (k_stone, (40, 300), "puddle"),
    "water": (k_water, (35, 280), "fizz"),
    "canvas": (k_canvas, (25, 180), "drum"),
}
SURFACE_LUFS = (-28.0, -24.5)


def surface(kind, dense):
    """Rain on one surface, sparse (light rain) or dense (moderate and heavy), to be added
    over a rain bed by how much of that surface is on screen."""
    make, rates, extra = SURFACES[kind]

    def render(rng, length=LAYER_S[dense]):
        n = secs(length)
        s = swell(n, rng, 0.06, 0.3, 0.4)
        out = scatter_train(n, rng, rates[dense] * s, kernels(make, 16, rng))
        if dense:
            if extra == "drip":  # big drops falling off the leaves
                out += 0.8 * scatter_train(n, rng, 6, kernels(lambda r: k_bubble(r, 500, 1500), 4,
                                                                 rng))
            elif extra == "gutter":  # water running off the eaves
                ks = kernels(lambda r: k_bubble(r, 400, 1400), 6, rng)
                out += 0.3 * pan(scatter_train(n, rng, 60, ks, channels=1)[:, 0], -0.5)
                out += 0.08 * pan(band(n, rng, 500, 3000, 0.5, 1), -0.5)
            elif extra == "puddle":
                out += 0.5 * scatter_train(n, rng, 25, kernels(lambda r: k_bubble(r, 900, 2800), 6,
                                                                  rng))
            elif extra == "fizz":
                out += 0.15 * band(n, rng, 2500, 6500, 0.2) * s[:, None]
            else:  # canvas drumming blurs into a low hum of taps
                out += 0.15 * band(n, rng, 150, 600, 0.8) * s[:, None]
        return out if kind == "canvas" else eq(out, WATER_EQ)

    return render


def first_drops_bed(rng, length=LAYER_S[0]):
    """The first heavy drops on dry dust, sparse, before the rain proper."""
    n = secs(length)
    return scatter_train(n, rng, 5, kernels(k_dust, 6, rng)) + \
        0.4 * scatter_train(n, rng, 3, kernels(k_splat, 3, rng))


# --- thunder ---------------------------------------------------------------------------


def thunder(rng, dur, near, dark=1.0):
    """Thunder from a channel of lightning: sound from each stretch of the channel arrives
    at its own time, the far parts later and duller, so it rolls. A near strike opens with
    a tearing crack and a deep boom; a distant one is only the low roll. Hills answer."""
    n = secs(dur)
    t = times(n)
    out = np.zeros(n)
    start = 0.0 if near else rng.uniform(0.15, 0.4)
    # Arrivals in clusters (the channel's kinks), thinning and darkening with time.
    at = start + (0.25 if near else 0.0)
    while at < dur * 0.7:
        age = at - start
        cutoff = ((2600 if near else 700) * np.exp(-age / (1.6 if near else 2.2)) + 120) / dark
        m = secs(rng.uniform(0.08, 0.45))
        burst = lowpass(rng.standard_normal(m), cutoff, 2) * np.hanning(m)
        place(out, burst * rng.uniform(0.3, 1.0) * np.exp(-age / (dur * 0.35)), secs(at))
        at += rng.exponential(0.12 if near else 0.2)
    rumble = lowpass(rng.standard_normal(n), 110 / dark ** 0.5, 4)
    swells = 1 + 0.5 * swell(n, rng, 1.5, 0.8, 0.0)
    env = np.clip((t - start) / 0.6, 0, 1) * np.exp(-np.clip(t - start, 0, None) / (dur * 0.3))
    out = out + (1.6 if near else 2.2) * rumble * env * swells
    if near:  # the crack: a ripping of the air, then the boom
        m = secs(0.35)
        tm = times(m)
        rip = np.zeros(m)
        for _ in range(28):
            k = secs(abs(rng.normal(0, 0.08)))
            if k < m - secs(0.01):
                place(rip, noise_burst(rng, 0.01, 800, 6500, 0.0015) * rng.uniform(0.3, 1),
                      k)
        crack = rip + 0.8 * noise_burst(rng, 0.35, 200, 5000, 0.03)
        boom = np.sin(2 * np.pi * (45 + 25 * np.exp(-tm / 0.1)) * tm) * np.exp(-tm / 0.35)
        place(out, 1.2 * crack + 2.0 * boom * ramp_in(m, secs(0.005)), 0)
    # Echoes off hills: duller copies, late.
    echo = np.zeros(n)
    for delay, g in ((rng.uniform(0.7, 1.2), 0.35), (rng.uniform(1.6, 2.4), 0.2)):
        k = secs(delay)
        echo[k:] += g * lowpass(out[: n - k], 500 / dark, 2)
    out = lowpass(out + echo, (5000 if near else 1500) / dark, 2)
    return out * ramp_in(n, secs(dur * 0.35))[::-1]


def thunder_fx(near, dur, dark=1.0):
    return lambda rng: sd.finish_sfx(thunder(rng, dur, near, dark), rng, 0.6, 2.5, fade_out=0.3,
                                     longest=6.0)


# --- snow, fog, heat -------------------------------------------------------------------


def k_crunch(rng, dur=0.16, bright=3500.0):
    """Packed snow giving underfoot: a quick burst of tiny cracks and a soft squeak."""
    n = secs(dur)
    out = np.zeros(n)
    for _ in range(int(rng.integers(60, 110))):
        k = int(rng.beta(1.5, 3.0) * (n - secs(0.004)))
        place(out, noise_burst(rng, 0.004, 500, bright, 0.0007) * rng.uniform(0.2, 1.0), k)
    out += 0.4 * noise_burst(rng, dur, 80, 400, 0.04, 0.01)
    return out * np.sin(np.pi * np.arange(n) / n) ** 0.5


def snow_step(rng):
    """One footfall in fresh snow: heel then toe, each a muffled crunch."""
    out = np.zeros(secs(0.45))
    place(out, k_crunch(rng, 0.16, 3200), 0)
    place(out, 0.7 * k_crunch(rng, 0.13, 3600), secs(rng.uniform(0.12, 0.18)))
    return out


def snow_hush(rng, length=BED_S):
    """Snow falling: near silence. A faint low air, now and then snow sliding off a bough,
    a crow far off through the muffled air."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(4):
        m = secs(0.6)
        flump = lowpass(rng.standard_normal(m), 700, 2) * np.hanning(m) ** 2
        life.add(flump, rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.5)
    for _ in range(2):
        life.add(lowpass(crow_far(rng), 1400), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 0.9, 0.2)
    air = band(n, rng, 40, 350, 0.9) * swell(n, rng, 0.04, 0.3)[:, None]
    return sd.mix({"air": 0.5 * air, "life": 2.0 * life.finish((2.5, 1.5, 0.5, 0.03), 0.4)})


def crow_far(rng):
    """A crow cawing twice, far off."""
    out = np.zeros(secs(1.2))
    for k in range(2):
        dur = 0.28
        m = secs(dur)
        f0 = sd.glide(m, [(0, 480), (0.08, 560), (dur, 430)])
        x = sd.voice(f0, [(1100, 400, 1.0), (1800, 500, 0.5)], rng, tilt=0.6, jitter=0.02,
                     shimmer=0.15, breath=0.4, sub=0.25)
        place(out, x * np.sin(np.pi * np.arange(m) / m) ** 0.6, secs(0.45 * k))
    return out


def snow_walk(rng, length=8.0):
    """Two people walking through fresh snow at an easy pace: the soft footfall bed."""
    walk = sd.Bed(length, rng, tail=3.0)
    for who, (pos, steps) in enumerate(((-0.3, 13), (0.35, 12))):
        for k in range(steps):
            walk.add(snow_step(rng) * (1.0 if k % 2 else 0.85), k * length / steps + who * 0.21,
                     pos, 0.3, 0.8)
    return walk.finish((0.8, 0.5, 0.2, 0.01), 0.15)


def drip(rng):
    """A drop falling from a leaf or an eave onto wet ground or into a puddle."""
    x = noise_burst(rng, 0.08, 600, 4000, 0.002)
    if rng.random() < 0.7:
        place(x, 0.8 * k_bubble(rng, 700, 2200), 0)
    return x


def fog(rng, length=BED_S):
    """Fog: still air, sound close and soft. Drops gather on leaves and fall at their own
    pace; a sheep's bell somewhere, muffled."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(26):
        life.add(drip(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.15, 0.6),
                 rng.uniform(0.3, 1.0))
    pos = rng.uniform(-0.6, 0.6)
    for _ in range(5):
        life.add(lowpass(sd.bell(rng.uniform(600, 800), rng, 0.6, "sheet"), 1200),
                 rng.uniform(0, length), pos, 0.9, 0.15)
    air = band(n, rng, 40, 500, 1.0) * swell(n, rng, 0.05, 0.35, 0.3)[:, None]  # fog breathes
    return sd.mix({"air": 0.25 * air, "drips": 3.0 * life.finish((1.2, 0.8, 0.3, 0.01), 0.35)})


def after_rain(rng, length=LAYER_S[0]):
    """After the rain: water dripping from eaves and leaves, a gutter emptying."""
    n = secs(length)
    life = sd.Bed(length, rng, tail=3.0)
    for _ in range(int(3.3 * length)):
        life.add(drip(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.15, 0.6),
                 rng.uniform(0.3, 1.0))
    ks = kernels(lambda r: k_bubble(r, 400, 1300), 5, rng)
    gutter = scatter_train(n, rng, 14 * swell(n, rng, 0.2, 0.6), ks, channels=1)[:, 0]
    return eq(sd.mix({"drips": 3.0 * life.finish((1.0, 0.7, 0.3, 0.01), 0.3),
                      "gutter": 0.5 * pan(gutter, 0.5)}), WATER_EQ)


def fly_pass(rng):
    """A fly droning past: a buzzing wing tone that swells and falls with a Doppler bend."""
    dur = rng.uniform(1.2, 2.2)
    n = secs(dur)
    f = 190 * rng.uniform(0.9, 1.15) * (1 + 0.04 * np.tanh((dur / 2 - times(n)) * 3))
    ph = sd.phase_of(f * (1 + 0.01 * slow(n, rng, 20)))
    tone = sum(np.sin(k * ph) / k for k in range(1, 12))
    return lowpass(tone, 3000, 2) * np.hanning(n) ** 2


def grasshopper(rng):
    """A grasshopper's dry rasp: a few bursts of rapid scratches."""
    out = np.zeros(secs(1.6))
    at = 0.0
    for _ in range(int(rng.integers(3, 7))):
        for k in range(int(rng.integers(8, 14))):
            place(out, noise_burst(rng, 0.006, 3500, 7000, 0.0012) * (0.6 + 0.4 * (k % 2)),
                  secs(at + k * 0.011))
        at += rng.uniform(0.2, 0.3)
    return out


def heat(rng, length=BED_S):
    """The still heat of an afternoon on the plain (Pārsa, Mesopotamia): hardly any air, a
    grasshopper rasping, flies droning past, one far cicada, a dove somewhere."""
    n = secs(length)
    life = sd.Bed(length, rng)
    life.scatter(grasshopper, 7, dist=(0.3, 0.7), level=(0.3, 0.6))
    life.scatter(fly_pass, 4, dist=(0.1, 0.3), level=(0.4, 0.8))
    life.add(sd.cicada(rng, 9.0), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.85, 0.25)
    air = band(n, rng, 60, 1500, 0.8) * swell(n, rng, 0.03, 0.3)[:, None]
    return sd.mix({"air": 0.25 * air, "life": 2.0 * life.finish((1.5, 1.0, 0.4, 0.02), 0.3)})


DUST = (dict(name="dust breeze", wind=2, grit=40, depth=1.0),
        dict(name="dust storm", wind=3, grit=160, depth=1.1))
DUST_LUFS = (-24.0, -20.5)


def dust(level):
    """Wind with sand in it (the Syrian steppe, Mesopotamia, Pārsa's summer): grit hissing
    and ticking against stone and cloth, thickening in the gusts."""
    p = DUST[level]

    def render(rng, length=BED_S):
        n = secs(length)
        air, g, G = wind_core(n, rng, WIND[p["wind"]], (1.0, p["depth"]))
        grit = np.stack([ambience.crackle(n, rng, p["grit"] * G[:, k] ** 2.5, 2200, 6800)
                         for k in range(2)], axis=1)
        hiss = band(n, rng, 1800, 6500, 0.2) * G**3
        layers = {"air": air, "grit": 0.7 * grit, "hiss": 0.05 * (1 + level) * hiss}
        if level:
            layers["cloth"] = pan(flap(n, rng, g, 0.5, 0.8), -0.4)
        return sd.mix(layers)

    return render


# --- sea, rivers, waterfalls -----------------------------------------------------------


def circular_time(n, centre_s):
    length = n / SR
    return (times(n) - centre_s + length / 2) % length - length / 2


def surf_envelopes(n, rng, period, shift=0.0, attack=0.12):
    """Envelopes of a train of waves breaking on a shore: the crash, the wash running up
    and the draw-back rattling through pebbles, a whole number of waves per loop."""
    k = max(1, round(n / SR / period))
    env = {name: np.zeros(n) for name in ("build", "crash", "wash", "draw")}
    for i in range(k):
        a = rng.uniform(0.55, 1.0)
        t = circular_time(n, (i + rng.uniform(-0.2, 0.2)) * n / SR / k + shift)
        on = np.clip((t + attack) / attack, 0, 1) ** 2
        env["build"] += a * np.exp(-(((t + 0.18 * period) / (0.1 * period)) ** 2))
        env["crash"] += a * on * np.exp(-np.clip(t, 0, None) / (0.12 * period))
        env["wash"] += a * on * np.exp(-np.clip(t, 0, None) / (0.35 * period))
        env["draw"] += a * np.exp(-(((t - 0.5 * period) / (0.16 * period)) ** 2))
    return env


SEA = (dict(name="calm", attack=0.9, period=4.5, crash=0.15, wash=0.6, draw=0.6, roar=0.0, wind=0),
       dict(name="moderate", attack=0.35, period=7.5, crash=0.6, wash=0.9, draw=0.8, roar=0.15, wind=1),
       dict(name="storm", attack=0.15, period=10.0, crash=1.2, wash=1.0, draw=0.5, roar=0.6, wind=3))
SEA_LUFS = (-27.0, -23.5, -20.0)


def coast(level):
    """Waves on an open shore: calm lapping, a moderate surf, storm breakers booming."""
    p = SEA[level]

    def render(rng, length=BED_S):
        n = secs(length)
        sides = [surf_envelopes(n, np.random.default_rng(rng.integers(1 << 31)), p["period"],
                                s, p["attack"]) for s in (0.0, rng.uniform(0.2, 0.5))]
        E = {k: np.stack([sides[0][k], sides[1][k]], axis=1) for k in sides[0]}
        layers = {
            "build": 0.35 * band(n, rng, 40, 300, 1.0) * E["build"],
            "crash": p["crash"] * band(n, rng, 150, 5000, 0.5) * E["crash"],
            "wash": p["wash"] * band(n, rng, 60, 1500, 0.9) * E["wash"] ** 1.5
            + 0.4 * p["wash"] * band(n, rng, 800, 5500, 0.4) * E["wash"] ** 3,
            "draw": p["draw"] * np.stack([ambience.crackle(n, rng, 400 * E["draw"][:, c], 1500,
                                                           6000) for c in range(2)], axis=1),
            "under": 0.4 * band(n, rng, 25, 200, 1.0) * (0.4 + 0.6 * E["wash"]),
        }
        if p["roar"]:  # white water everywhere: a continuous roar under the breakers
            layers["roar"] = p["roar"] * band(n, rng, 80, 3000, 0.7) * swell(n, rng, 0.1, 0.3)[:, None]
        if level == 2:  # the biggest breakers land with a thump
            thump = np.zeros(n)
            for i in range(max(1, round(length / p["period"]))):
                m = secs(0.8)
                tm = times(m)
                boom = np.sin(2 * np.pi * (55 + 20 * np.exp(-tm / 0.1)) * tm) * np.exp(-tm / 0.25)
                place(thump, boom * rng.uniform(0.5, 1.0),
                      secs(i * p["period"] + rng.uniform(0, 0.3)) % (n - m))
            layers["thump"] = 0.6 * np.stack([thump, thump], axis=1)
        if p["wind"]:
            layers["wind"] = 0.25 * wind_core(n, rng, WIND[p["wind"]], WIND_PLACES["sea"])[0]
        return eq(sd.mix(layers), WATER_EQ)

    return render


HARBOUR = (dict(name="calm", lap=1.5, slap=0.0, knock=0.3, wind=0),
           dict(name="moderate", lap=3.5, slap=0.25, knock=0.8, wind=1),
           dict(name="storm", lap=6.0, slap=0.6, knock=1.5, wind=2))


def k_lap(rng):
    """Water slapping into a hollow under a quay or a hull: a short resonant clop."""
    return resonant_burst(rng, 0.2, rng.uniform(220, 650), rng.uniform(3, 6),
                          rng.uniform(0.03, 0.07)) + 0.5 * noise_burst(rng, 0.2, 150, 1500, 0.06,
                                                                       0.01)


def harbour(level):
    """Inside a harbour: water lapping at the quay and the hulls, moored boats knocking,
    ropes creaking; in a storm, waves slamming the mole and spray over it."""
    p = HARBOUR[level]

    def render(rng, length=BED_S):
        n = secs(length)
        s = swell(n, rng, 0.15, 0.4)
        boats = sd.Bed(length, rng)
        for _ in range(int(6 * p["knock"])):
            f = rng.uniform(160, 420)
            boats.add(sd.modes(secs(0.25), [f, f * 2.2], [1.0, 0.3], [0.05, 0.02], rng),
                      rng.uniform(0, length), rng.uniform(-0.7, 0.7), rng.uniform(0.3, 0.7), 0.6)
        for _ in range(int(3 * p["knock"])):
            boats.add(sd.creak_short(rng, rng.uniform(0.5, 1.0), rng.uniform(50, 80)),
                      rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.25)
        layers = {
            "laps": scatter_train(n, rng, p["lap"] * s, kernels(k_lap, 8, rng), sigma=0.4),
            "water": 0.05 * (1 + level) * band(n, rng, 100, 3500, 0.7) * s[:, None],
            "boats": 2.0 * boats.finish((1.2, 0.9, 0.4, 0.015), 0.3),
        }
        if p["slap"]:  # waves slamming the mole: a thud and a sheet of spray
            hits = sd.Bed(length, rng)
            for _ in range(int(round(length / (8 - 3 * level)))):
                m = secs(1.2)
                tm = times(m)
                thud = np.sin(2 * np.pi * (70 + 30 * np.exp(-tm / 0.05)) * tm) * np.exp(-tm / 0.12)
                spray = bandpass(rng.standard_normal(m), 400, 3000) * np.clip(tm / 0.08, 0, 1) * \
                    np.exp(-tm / 0.35)
                hits.add(thud + 0.6 * spray, rng.uniform(0, length), rng.uniform(-0.6, 0.6), 0.35, 1)
            layers["slams"] = p["slap"] * hits.finish((1.5, 1.0, 0.4, 0.02), 0.3)
        if p["wind"]:
            layers["wind"] = 0.15 * wind_core(n, rng, WIND[p["wind"]], WIND_PLACES["street"])[0]
        return sd.mix(layers)

    return render


RIVER = (dict(name="slow", flow=(70, 1400), bubbles=(150, 700, 35), rush=0.0),
         dict(name="fast", flow=(120, 4000), bubbles=(300, 2600, 400), rush=0.6))
RIVER_LUFS = (-25.5, -22.0)


def river(level):
    """A river: slow, gurgling and lapping at its banks; or fast, rushing over stones."""
    p = RIVER[level]

    def render(rng, length=BED_S):
        n = secs(length)
        lo, hi, rate = p["bubbles"]
        s = swell(n, rng, 0.2, 0.25)
        ks = kernels(lambda r: k_bubble(r, lo, hi), 10, rng)
        layers = {
            "flow": 0.12 * band(n, rng, *p["flow"], 0.8) * s[:, None],
            "bubbles": scatter_train(n, rng, rate * s, ks, sigma=0.6),
        }
        if level == 0:
            layers["laps"] = 0.5 * scatter_train(n, rng, 1.2, kernels(k_lap, 5, rng), sigma=0.4)
        if p["rush"]:
            layers["rush"] = p["rush"] * band(n, rng, 200, 5500, 0.4)
        return eq(sd.mix(layers), WATER_EQ) if p["rush"] else sd.mix(layers)

    return render


def waterfall(level):
    """A waterfall far off (a soft low roar) or close (a broad roar and spray)."""

    def render(rng, length=BED_S):
        n = secs(length)
        s = swell(n, rng, 0.2, 0.3)[:, None]  # spray and roar breathe with the flow
        if level == 0:  # distance takes the top off, not all of it
            return 0.8 * band(n, rng, 40, 1800, 0.9) * s + 0.3 * band(n, rng, 600, 3000, 0.6)
        spray = np.stack([ambience.crackle(n, rng, 900, 1500, 6500) for _ in range(2)], axis=1)
        return band(n, rng, 40, 4500, 0.9) * s + 0.4 * band(n, rng, 30, 250, 1.0) + 0.15 * spray

    return render


# --- fire ------------------------------------------------------------------------------


def k_pop(rng):
    return noise_burst(rng, 0.015, 900, 6000, rng.uniform(0.0015, 0.004))


def k_crack(rng):
    """Wood splitting in the heat: a sharp crack and a short crackle."""
    x = noise_burst(rng, 0.12, 400, 6500, 0.006)
    for _ in range(int(rng.integers(3, 8))):
        place(x, 0.4 * k_pop(rng), secs(rng.uniform(0.005, 0.08)))
    return x


def hearth(rng, length=12.0):
    """A small hearth fire indoors: a soft breathing flame, gentle crackles, sap hissing
    now and then, a log settling."""
    n = secs(length)
    s = swell(n, rng, 0.4, 0.3)
    roar = band(n, rng, 50, 600, 0.9, 1) * s
    pops = conv(train(n, rng, 6 * s, 0.6), k_pop(rng)) + conv(train(n, rng, 4 * s, 0.6), k_pop(rng))
    life = sd.Bed(length, rng, tail=3.0)
    m = secs(1.5)
    hiss = bandpass(rng.standard_normal(m), 1500, 4000) * np.hanning(m) * \
        np.sin(np.pi * np.arange(m) / m)
    life.add(0.15 * hiss, rng.uniform(0, length), 0.1, 0.2)
    settle = sd.modes(secs(0.4), [140, 260], [1.0, 0.4], [0.05, 0.03], rng)
    place(settle, 0.6 * k_crack(rng), secs(0.02))
    life.add(settle, rng.uniform(0, length), -0.1, 0.25, 0.8)
    return sd.mix({"roar": 0.35 * pan(roar, 0.0), "pops": 0.7 * pan(pops, 0.05),
                   "life": life.finish((0.6, 0.4, 0.2, 0.005), 0.2)})


def bonfire(rng, length=12.0):
    """A big festival bonfire (the Parilia): a deep roar that surges as the flames leap,
    thick crackling, wood cracking and embers collapsing."""
    n = secs(length)
    s = swell(n, rng, 0.6, 0.45)
    S = np.stack([s, np.roll(s, secs(0.2))], axis=1)
    roar = band(n, rng, 30, 900, 0.9) * S + 0.3 * band(n, rng, 400, 2500, 0.6) * S**2
    pops = scatter_train(n, rng, 40 * s, kernels(k_pop, 6, rng), sigma=0.7)
    cracks = scatter_train(n, rng, 1.2, kernels(k_crack, 4, rng), sigma=0.4)
    life = sd.Bed(length, rng, tail=3.0)
    for _ in range(2):
        m = secs(1.2)
        fall = lowpass(rng.standard_normal(m), 900, 2) * np.exp(-times(m) / 0.3)
        for _ in range(12):
            place(fall, 0.3 * k_pop(rng), secs(rng.uniform(0, 0.6)))
        life.add(fall, rng.uniform(0, length), rng.uniform(-0.3, 0.3), 0.3, 0.7)
    return sd.mix({"roar": 0.45 * roar, "pops": 0.6 * pops, "cracks": 0.7 * cracks,
                   "embers": life.finish((1.0, 0.7, 0.3, 0.01), 0.25)})


# --- turns of weather (effects) --------------------------------------------------------


def gust_front(rng):
    """A gust front arriving before a storm: the air rising from stillness into a rush
    through trees, leaves and dust whipped up, a shutter knocking, then the wind settling
    strong."""
    dur = 4.6
    n = secs(dur)
    t = times(n)
    g = np.clip((t - 0.4) / 1.6, 0, 1) ** 2 * (1 + 0.5 * np.exp(-(((t - 2.3) / 0.5) ** 2)))
    g = g * (1 + 0.15 * slow(n, rng, 2.0))
    air = lowpass(rng.standard_normal(n), 400, 2) * g + \
        0.6 * bandpass(rng.standard_normal(n), 300, 2500) * g**1.6
    leaves = ambience.crackle(n, rng, 600 * g**2, 1500, 6000)
    knock = np.zeros(n)
    for at in (2.1, 2.55):
        place(knock, sd.modes(secs(0.2), [190, 420], [1.0, 0.5], [0.03, 0.02], rng), secs(at))
    out = air + 0.5 * leaves + 0.3 * knock
    return sd.finish_sfx(out * ramp_in(n, secs(1.2))[::-1], rng, 0.3, 1.5, fade_out=0.3)


def calm_before(rng):
    """The hush before rain: a last breath of wind dies away, leaves settle, and in the
    stillness a far roll of thunder."""
    dur = 4.6
    n = secs(dur)
    t = times(n)
    g = np.exp(-t / 1.0) * (1 + 0.2 * slow(n, rng, 1.5))
    air = lowpass(rng.standard_normal(n), 500, 2) * g
    leaves = ambience.crackle(n, rng, 120 * g**2, 1500, 5500)
    roll = np.zeros(n)
    place(roll, 0.35 * thunder(rng, 2.4, False), secs(2.0))
    return sd.finish_sfx(air + 0.4 * leaves + roll, rng, 0.3, 1.5, fade_out=0.3)


def first_drops(rng):
    """The first drops: a few heavy ones on dust and leaves, quickening into light rain."""
    dur = 4.6
    n = secs(dur)
    t = times(n)
    out = np.zeros(n)
    at = 0.2
    while at < dur - 0.3:
        k = (k_dust, k_leaf, k_stone)[int(rng.integers(3))](rng)
        place(out, k * rng.uniform(0.4, 1.0), secs(at))
        at += rng.exponential(0.6 * np.exp(-at / 1.3) + 0.04)
    hiss = bandpass(rng.standard_normal(n), 800, 6000) * np.clip((t - 2.0) / 2.4, 0, 1) * 0.05
    return sd.finish_sfx(out + hiss, rng, 0.25, 1.2, fade_out=0.4)


# --- files -----------------------------------------------------------------------------

W = "world"
FILES = {}
for _where, _desc in (("open", "open country: grass and leaves rustling in the gusts"),
                      ("street", "city streets: whistling through colonnades, awnings flapping"),
                      ("sea", "over open water: smooth, with spray in strong wind"),
                      ("mountain", "high mountains: whistling over rock, roaring down the crags")):
    for _lvl, _p in enumerate(WIND):
        FILES[f"amb/{W}/wind_{_where}_{_lvl + 1}.ogg"] = entry(
            "bed", wind(_lvl, _where), WIND_LUFS[_lvl], f"Wind, {_p['name']}, {_desc}.",
            when="weather", where=f"wind strength {_lvl + 1}/4 where {_where} dominates the view",
            family=f"wind.{_where}", level=_lvl + 1, level_name=_p["name"],
            # the breath is so smooth that q0's error at the file edges would click
            quality=2 if _lvl == 0 else 0, tags=["weather", "wind", _where])
for _lvl, _p in enumerate(RAIN):
    FILES[f"amb/{W}/rain_{_lvl + 1}.ogg"] = entry(
        "bed", rain(_lvl), RAIN_LUFS[_lvl],
        f"Rain, {_p['name']}: drops on open ground and in the air, no particular surface.",
        when="rain", where=f"under a rain cell of intensity {_lvl + 1}/3; snow replaces it in winter",
        family="rain", level=_lvl + 1, level_name=_p["name"], tags=["weather", "rain"])
for _kind in SURFACES:
    for _d, _name in enumerate(("sparse", "dense")):
        FILES[f"amb/{W}/rain_{_kind}_{_d + 1}.ogg"] = entry(
            "loop", surface(_kind, _d), SURFACE_LUFS[_d],
            f"Rain on {_kind}, {_name} ({'light rain' if _d == 0 else 'moderate and heavy rain'}).",
            when="rain", where=f"added over the rain bed by the share of {_kind} on screen",
            family=f"rain.{_kind}", level=_d + 1, level_name=_name,
            tags=["weather", "rain", "surface", _kind])
FILES.update({
    f"amb/{W}/rain_dust.ogg": entry(
        "loop", first_drops_bed, -27.0, "The first heavy drops on dry dust, sparse.",
        when="rain", where="the first minute of rain on dry ground, then fade to the surface layers",
        tags=["weather", "rain", "surface", "dust", "onset"]),
    f"amb/{W}/after_rain.ogg": entry(
        "loop", after_rain, -25.0, "Dripping from eaves and leaves, a gutter emptying.",
        when="weather", where="for a minute or two after rain stops, fading as the ground dries",
        tags=["weather", "after_rain"]),
    f"amb/{W}/snow.ogg": entry(
        "bed", snow_hush, -26.0, "Snow falling: near silence, a bough shedding, a far crow.",
        when="weather", where="under a snow cell; duck other beds 3 dB (snow muffles)",
        family="snow", level=1, level_name="snowfall", quality=2,  # smooth: q0 edges click
        tags=["weather", "snow"]),
    f"amb/{W}/snow_walk.ogg": entry(
        "loop", snow_walk, -25.0, "Footfalls of two walkers in fresh snow.",
        when="moving", where="positional: walkers on snow-covered ground",
        tags=["weather", "snow", "steps"]),
    f"amb/{W}/fog.ogg": entry(
        "bed", fog, -26.0, "Still fog: drops falling from leaves, a muffled bell.",
        when="weather", where="under fog (dawn valleys, the Tiber mist); duck other beds 3 dB",
        family="fog", level=1, level_name="fog", tags=["weather", "fog"]),
    f"amb/{W}/heat.ogg": entry(
        "bed", heat, -25.0, "Afternoon heat on the plain: grasshoppers, flies, a far cicada.",
        when="afternoon", where="clear summer afternoons in Pārsa, Mesopotamia, the Syrian steppe",
        family="heat", level=1, level_name="still heat", tags=["weather", "heat", "east"]),
})
for _lvl, _p in enumerate(DUST):
    FILES[f"amb/{W}/dust_{_lvl + 1}.ogg"] = entry(
        "bed", dust(_lvl), DUST_LUFS[_lvl], f"Wind with sand in it: {_p['name']}.",
        when="weather", where="dust cells: the Syrian steppe, Mesopotamia, Pārsa in summer",
        family="dust", level=_lvl + 1, level_name=_p["name"], tags=["weather", "dust", "east"])
for _lvl, _p in enumerate(SEA):
    FILES[f"amb/{W}/sea_coast_{_lvl + 1}.ogg"] = entry(
        "bed", coast(_lvl), SEA_LUFS[_lvl], f"Waves on an open shore, {_p['name']}.",
        where=f"sea state {_lvl + 1}/3 (0-1 calm, 2 moderate, 3 storm) where the view holds coast",
        family="sea.coast", level=_lvl + 1, level_name=_p["name"], tags=["sea", "coast"])
for _lvl, _p in enumerate(HARBOUR):
    FILES[f"amb/{W}/sea_harbour_{_lvl + 1}.ogg"] = entry(
        "bed", harbour(_lvl), SEA_LUFS[_lvl],
        f"Inside a harbour, {_p['name']}: lapping at quays and hulls, boats knocking.",
        where=f"sea state {_lvl + 1}/3 in harbour zones (Piraeus, Ostia, the Emporium, Brundisium)",
        family="sea.harbour", level=_lvl + 1, level_name=_p["name"], tags=["sea", "harbour"])
for _lvl, _p in enumerate(RIVER):
    FILES[f"amb/{W}/river_{_lvl + 1}.ogg"] = entry(
        "bed", river(_lvl), RIVER_LUFS[_lvl], f"A river, {_p['name']}.",
        where="river tiles in view: slow on the plains (Tiber, Euphrates), fast in the mountains",
        family="river", level=_lvl + 1, level_name=_p["name"], tags=["water", "river"])
for _lvl, _name in enumerate(("far", "close")):
    FILES[f"amb/{W}/waterfall_{_lvl + 1}.ogg"] = entry(
        "bed", waterfall(_lvl), (-26.0, -22.0)[_lvl], f"A waterfall, {_name}.",
        where="by distance to a waterfall: far beyond 12 tiles, close within 6",
        family="waterfall", level=_lvl + 1, level_name=_name, tags=["water", "waterfall"])
FILES.update({
    f"amb/{W}/hearth.ogg": entry(
        "loop", hearth, -26.0, "A small hearth fire: soft flame, gentle crackles, a log settling.",
        when="lit", where="positional: hearths and ovens in houses, inns, the home cottage",
        tags=["fire", "hearth"]),
    f"amb/{W}/bonfire.ogg": entry(
        "loop", bonfire, -23.0, "A big bonfire: surging roar, thick crackling, wood cracking.",
        when="lit", where="positional: festival bonfires (the Parilia), camp fires of caravans",
        tags=["fire", "bonfire", "festival"]),
    f"sfx/{W}/thunder_roll_1.wav": entry("sfx", thunder_fx(False, 5.0), -24.0,
                                         "Rolling thunder, 15 to 40 tiles away.", gain=0.9,
                                         tags=["weather", "thunder", "far"]),
    f"sfx/{W}/thunder_roll_2.wav": entry("sfx", thunder_fx(False, 4.6), -24.0,
                                         "Rolling thunder, a second roll.", gain=0.9,
                                         tags=["weather", "thunder", "far"]),
    f"sfx/{W}/thunder_roll_3.wav": entry("sfx", thunder_fx(False, 5.0), -25.0,
                                         "Rolling thunder, a long low roll.", gain=0.9,
                                         tags=["weather", "thunder", "far"]),
    f"sfx/{W}/thunder_far_2.wav": entry("sfx", thunder_fx(False, 4.0, 2.0), -26.0,
                                        "A far rumble of thunder beyond the hills (with thunder_far).",
                                        gain=0.9, tags=["weather", "thunder", "far"]),
    f"sfx/{W}/thunder_far_3.wav": entry("sfx", thunder_fx(False, 3.6, 2.2), -26.0,
                                        "A far rumble, very low (with thunder_far).", gain=0.9,
                                        tags=["weather", "thunder", "far"]),
    f"sfx/{W}/thunder_near_1.wav": entry("sfx", thunder_fx(True, 5.0), -21.0,
                                         "A near strike: a crack, a boom, a long roll (rare).",
                                         gain=0.8, tags=["weather", "thunder", "near"]),
    f"sfx/{W}/thunder_near_2.wav": entry("sfx", thunder_fx(True, 5.0), -21.0,
                                         "A near strike, a second crack (rare).",
                                         gain=0.8, tags=["weather", "thunder", "near"]),
    f"sfx/{W}/thunder_near_3.wav": entry("sfx", thunder_fx(True, 4.6), -22.0,
                                         "A near strike, a third crack, softer (rare).",
                                         gain=0.8, tags=["weather", "thunder", "near"]),
    f"sfx/{W}/gust_front.wav": entry("sfx", gust_front, -22.0,
                                     "A gust front arriving: stillness rising into a rush.",
                                     tags=["weather", "wind", "turn"]),
    f"sfx/{W}/calm_before.wav": entry("sfx", calm_before, -26.0,
                                      "The hush before rain: wind dying, a far roll.",
                                      tags=["weather", "rain", "turn"]),
    f"sfx/{W}/first_drops.wav": entry("sfx", first_drops, -25.0,
                                      "The first heavy drops quickening into light rain.",
                                      tags=["weather", "rain", "turn"]),
    f"sfx/{W}/step_snow.wav": entry("sfx", lambda rng: sd.finish_sfx(snow_step(rng), rng, 0.1,
                                                                     0.4, fade_out=0.02),
                                    -27.0, "One footfall in fresh snow.", gain=0.6,
                                    tags=["steps", "snow"]),
})
