"""The year in sound (docs/design/seasons.md §3.12, §3.7, §3.10): the cities' seasonal beds that
replace their day and night beds by month, the countryside's nature beds for autumn and winter
(the existing dawn, dusk and night beds are spring and summer: warblers, swifts, bee-eaters,
scops owls and nightjars are migrants gone by October), snow-muffled beds, the seasonal layers
(spring frogs, wind in bare branches, the winter marsh, floodwater), the seasons' work as
positional loops, each civilization's festival sounds, a soft cue for the turn of a season in
each region's mode, and the turn events' own cues.

Instruments by source (cities/*.md): Greek aulos, tympanon and krotala at Dionysiac revels
(vase painting; Euripides, Bacchae 120-134); Roman tibia and lituus (the curved horn of ritual
and processions; Gellius 5.8) and bells at the Saturnalia (tintinnabula; Martial 14); the Persian
court's harp, double pipe, frame drum and women singing and clapping are inferred from the Elamite
musicians who welcome the king on Ashurbanipal's Madaktu relief (7th century BC) and from Greek
writers on the court (Duris in Athenaeus 10.434e: the king dances at the Mithra festival)."""

import numpy as np

import ancient as an
import athens
import people
import sfx as home_sfx
import sounds as sd
import stings
import weather
import wildlife as wl
from atmos import band, entry, kernels, noise_burst, resonant_burst, scatter_train, swell
from dsp import lowpass, midi_hz, pan, place, secs, times

CITY_S = 44.0  # the cities' seasonal beds (their day and night beds are 48 s)
NATURE_S = 32.0


def hz(m):
    return float(midi_hz(m))


# --- small voices ----------------------------------------------------------------------


def sparrow(rng):
    """A house sparrow's 'chilp', two or three of them."""
    out = np.zeros(secs(0.8))
    at = 0.0
    for _ in range(int(rng.integers(2, 4))):
        a = rng.uniform(3000, 3800)
        place(out, sd.chirp(a, a * rng.uniform(0.75, 0.9), rng.uniform(0.05, 0.08), 0.25), secs(at))
        at += rng.uniform(0.12, 0.25)
    return out


def jackdaw(rng):
    """A jackdaw's short metallic 'tchack', once or twice."""
    out = np.zeros(secs(0.7))
    for k in range(int(rng.integers(1, 3))):
        f0 = rng.uniform(900, 1100)
        x = wl.syllable(rng, 0.11, [(0, f0), (0.4, f0 * 1.15), (1, f0 * 0.9)],
                        [(1500, 400, 1.0), (2600, 500, 0.5)], tilt=0.7, breath=0.25, sub=0.2)
        place(out, x, secs(0.28 * k))
    return out


def wren(rng):
    """A wren's loud, fast trilling run, out of all proportion to the bird."""
    return wl.song([(wl.warble(rng, 3500, 6000), 0.03), (wl.trill(rng), 0.0)])


def starling_chatter(rng, dur=2.0):
    """Starlings in a flock: clicks, whistles and wheezes over each other."""
    out = np.zeros(secs(dur + 0.3))
    for _ in range(int(25 * dur)):
        a = rng.uniform(1800, 5500)
        x = sd.chirp(a, a * rng.uniform(0.6, 1.6), rng.uniform(0.02, 0.09), 0.3)
        place(out, x * rng.uniform(0.2, 1.0), secs(rng.uniform(0, dur)))
    return out


def tawny_female(rng):
    """The female tawny owl's sharp 'ke-wick'."""
    return wl.syllable(rng, 0.35, [(0, 1100), (0.3, 1500), (1, 1250)],
                       [(1300, 500, 1.0), (2500, 600, 0.3)], tilt=0.9, breath=0.4, sub=0.15)


def fox_bark(rng):
    return lowpass(wl.bark(rng, 1.5, 0.12), 2200)


def bough_shed(rng):
    """Snow sliding off a bough: a soft thump and a sifting hiss."""
    m = secs(1.4)
    t = times(m)
    thump = resonant_burst(rng, 1.4, 90, 2, 0.08, 40, 600)
    sift = band(m, rng, 800, 5000, 0.3, 1) * np.clip(t / 0.1, 0, 1) * np.exp(-t / 0.4)
    return thump + 0.15 * sift


def axe_far(rng):
    """Someone splitting wood far off: a dull chop and its echo off the hills."""
    x = lowpass(people.chop(rng), 1500)
    out = np.zeros(len(x) + secs(0.5))
    place(out, x, 0)
    place(out, 0.3 * x, secs(0.35))
    return out


def tit_call(rng):
    """A tit's thin 'see-see' among bare twigs."""
    out = np.zeros(secs(0.6))
    for k in range(int(rng.integers(2, 4))):
        place(out, sd.chirp(7000, 6200, 0.06, 0.05) * 0.6, secs(0.13 * k))
    return lowpass(out, 6400)


def plough_call(rng):
    """A ploughman calling to his oxen: a long wordless shout falling away."""
    f0, _ = people.person(rng, people.CHARACTERS["greek"])
    return people.talker(1.2, rng, people.CHARACTERS["greek"], f0 * 1.5, False, 2400.0)


def guard_steps(rng, count=6):
    """A sentry pacing slowly on stone, the spear butt set down at the turn."""
    out = np.zeros(secs(0.9 * count + 1.0))
    for k in range(count):
        place(out, sd.step(rng, "stone"), secs(0.9 * k + abs(rng.normal(0, 0.02))))
    place(out, 0.6 * resonant_burst(rng, 0.2, 700, 6, 0.03), secs(0.9 * count + 0.2))
    return out


# --- the cities' seasonal beds -------------------------------------------------------------


def athens_day_cool(rng, length=CITY_S):
    """Athens from October to May: no cicadas; wind in the olives, goat bells on the hills,
    sparrows and a robin, a plough ox lowing in the fields, sculptors still at work far off,
    voices; the rain-washed quiet of a green season."""
    n = secs(length)
    life = sd.Bed(length, rng)
    athens.goat_bells(life, 2, 0.3)
    athens.sculptors(life, 4)
    for _ in range(int(length / 3)):
        life.add(sparrow(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.7), 0.4)
    wl.singer(life, home_sfx.robin, length, 9.0, rng.uniform(-0.6, 0.6), 0.45, 0.5)
    for _ in range(2):
        life.add(sd.ox(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.85, 0.5)
    life.add(plough_call(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.9, 0.3)
    leaves = np.stack([wl.ambience.crackle(n, rng, 30 * swell(n, rng, 0.07, 0.6), 1500, 5500)
                       for _ in range(2)], axis=1)
    return sd.mix({
        "life": life.finish((2.0, 1.3, 0.6, 0.02), 0.4),
        "olives": 0.1 * leaves,
        "voices": 0.3 * sd.crowd(length, rng, 6, ceiling=1300),
        "air": 0.07 * sd.wind(n, rng, 120, 1600, 0.06, 0.6),
    })


def athens_night_winter(rng, length=CITY_S):
    """An Athenian winter night (November to March): no crickets; wind, a dog across town,
    the little owl on the rock, a symposium far off behind shutters, eaves dripping."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(2):
        life.add(sd.dog(rng, int(rng.integers(2, 4))), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 0.85, 0.4)
    t = rng.uniform(0, 10)
    for k in range(4):
        life.add(sd.little_owl(rng), t + k * rng.uniform(6, 9), -0.5, 0.7, 0.35)
    for _ in range(int(length / 2)):
        life.add(weather.drip(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.4, 0.25)
    party = sd.Bed(length, rng)
    party.add(lowpass(athens.symposium(rng), 900), rng.uniform(0, length), 0.4, 0.95, 0.7)
    return sd.mix({
        "life": life.finish((2.5, 1.6, 0.7, 0.03), 0.45),
        "party": 1.4 * party.finish((1.5, 1.0, 0.5, 0.02), 0.5),
        "air": 0.09 * sd.wind(n, rng, 90, 1400, 0.07, 0.6, whistle=0.02),
    })


def parsa_day_summer(rng, length=CITY_S):
    """The plain of Pārsa from June to September: a hot dry wind, grasshoppers rasping,
    flies, the threshing floors working far off, a horse snorting in the heat."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(int(length / 2.5)):
        life.add(weather.grasshopper(rng), rng.uniform(0, length), rng.uniform(-0.9, 0.9),
                 rng.uniform(0.2, 0.6), 0.5)
    for _ in range(int(length / 8)):
        life.add(weather.fly_pass(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.2, 0.3)
    life.add(lowpass(sd.snort(rng), 2500), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.6, 0.4)
    athens.sculptors(life, 2, level=0.25)
    floor = lowpass(people.threshing(rng, length), 1500)
    return sd.mix({
        "life": life.finish((2.0, 1.2, 0.6, 0.02), 0.35),
        "threshing": 0.35 * floor,
        "air": 0.12 * sd.wind(n, rng, 200, 2400, 0.07, 0.6),
    })


def parsa_day_winter(rng, length=CITY_S):
    """The plain of Pārsa from November to February: a cold wind off the mountain, crows and
    ravens, no swallows; chisels slower on the terrace, an ox, a dog at a farm."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(4):
        life.add(wl.caw(rng, rng.uniform(0.95, 1.15)), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 rng.uniform(0.5, 0.85), 0.45)
    life.add(sd.raven(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.7, 0.4)
    athens.sculptors(life, 3, level=0.3)
    life.add(sd.ox(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.85, 0.45)
    life.add(sd.dog(rng, 2), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.9, 0.3)
    return sd.mix({
        "life": life.finish((2.2, 1.4, 0.6, 0.02), 0.4),
        "air": 0.16 * sd.wind(n, rng, 70, 1300, 0.08, 0.7, whistle=0.03),
    })


def parsa_night_winter(rng, length=CITY_S):
    """A frost-still winter night at Pārsa: almost no air, an owl on the terrace, a guard
    pacing, a fire altar breathing far off, a jackal once."""
    n = secs(length)
    life = sd.Bed(length, rng)
    t = rng.uniform(0, 8)
    for k in range(3):
        life.add(sd.little_owl(rng), t + k * rng.uniform(9, 13), 0.4, 0.7, 0.35)
    life.add(wl.tawny(rng), rng.uniform(0, length), -0.6, 0.85, 0.35)
    life.add(guard_steps(rng), rng.uniform(0, length), rng.uniform(-0.4, 0.4), 0.55, 0.5)
    life.add(lowpass(wl.jackals(rng), 2500), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.3)
    altar = pan(lowpass(sd.fire(length, rng, 0.5), 2000), 0.5)
    return sd.mix({
        "life": life.finish((3.0, 2.0, 0.8, 0.04), 0.5),
        "altar": 0.12 * altar,
        "air": 0.04 * sd.wind(n, rng, 60, 700, 0.05, 0.4),
    })


def rome_day_winter(rng, length=CITY_S):
    """Rome from December to February: no swallows; the city's murmur, hearths crackling in
    the shops, wind in the streets, gutters dripping, jackdaws round the temples, a cart."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(7):
        life.add(jackdaw(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.4, 0.8), 0.45)
    for _ in range(int(length * 0.8)):
        life.add(weather.drip(rng), rng.uniform(0, length), rng.uniform(-0.6, 0.6), rng.uniform(0.2, 0.5), 0.3)
    hearth = pan(sd.fire(length, rng, 0.8), -0.4)
    cart = pan(lowpass(sd.cart(length, rng, 0.8), 1500), 0.6) * swell(n, rng, 0.05, 0.8, 0.0)[:, None]
    return sd.mix({
        "life": life.finish((1.8, 1.2, 0.5, 0.02), 0.4),
        "murmur": 0.45 * sd.crowd(length, rng, 10, ceiling=1600),
        "hearth": 0.12 * hearth,
        "cart": 0.12 * cart,
        "wind": 0.1 * sd.wind(n, rng, 120, 2200, 0.08, 0.6, whistle=0.04),
    })


# --- the countryside's autumn and winter -------------------------------------------------


def air(n, rng, level=0):
    return wl.air(n, rng, level)


def dawn_autumn(rng, length=NATURE_S):
    """An autumn dawn in the south (September to November): robins back from the north,
    starlings in the olives, crows, a wren, a far cockerel; dry leaves stirring."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for k in range(2):
        wl.singer(b, home_sfx.robin, length, 5.0, (-0.5, 0.5)[k], rng.uniform(0.3, 0.6), 0.6)
    t0 = rng.uniform(0, length)
    for k in range(4):
        b.add(starling_chatter(rng, 2.5), t0 + 3 * k, rng.uniform(-0.6, 0.6), 0.6, 0.4)
    for _ in range(3):
        b.add(wl.caw(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.75, 0.4)
    wl.singer(b, wren, length, 11.0, rng.uniform(-0.7, 0.7), 0.4, 0.5)
    b.add(wl.rooster(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.3)
    leaves = np.stack([wl.ambience.crackle(n, rng, 15 * swell(n, rng, 0.08, 0.7), 1200, 5000)
                       for _ in range(2)], axis=1)
    return sd.mix({"birds": 2.5 * b.finish((1.8, 1.2, 0.5, 0.02), 0.4), "leaves": 0.06 * leaves,
                   "air": 0.07 * air(n, rng)})


def dawn_winter(rng, length=NATURE_S):
    """A winter dawn (December to February): a robin, a wren, sparrows at a farm, crows going
    out, a far cockerel; cold, thin, few voices."""
    n = secs(length)
    b = sd.Bed(length, rng)
    wl.singer(b, home_sfx.robin, length, 6.5, rng.uniform(-0.5, 0.5), 0.45, 0.6)
    wl.singer(b, wren, length, 13.0, rng.uniform(-0.7, 0.7), 0.4, 0.5)
    for _ in range(int(length / 5)):
        b.add(sparrow(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.6, 0.35)
    for _ in range(3):
        b.add(wl.caw(rng, 0.95), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.8, 0.4)
    b.add(wl.rooster(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.3)
    return sd.mix({"birds": 2.5 * b.finish((2.2, 1.5, 0.6, 0.03), 0.45), "air": 0.12 * air(n, rng)})


def dusk_autumn(rng, length=NATURE_S):
    """Autumn dusk: starlings gathering to roost in a chattering mass, rooks going over, the
    last crickets slow in the cold, the first tawny owl."""
    n = secs(length)
    b = sd.Bed(length, rng)
    t0 = rng.uniform(0, length)
    for k in range(7):
        b.add(starling_chatter(rng, 3.0), t0 + 3.5 * k, rng.uniform(-0.4, 0.4), 0.55, 0.5)
    for _ in range(4):
        b.add(wl.caw(rng, 0.9), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.7, 0.4)
    sd.crickets(b, 2, level=0.15)
    b.add(wl.tawny(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.8, 0.35)
    return sd.mix({"life": 2.5 * b.finish((1.8, 1.2, 0.5, 0.02), 0.4), "air": 0.1 * air(n, rng)})


def dusk_winter(rng, length=NATURE_S):
    """Winter dusk: jackdaws and rooks going to roost, a robin's ticking alarm, a dog at a
    farm, still cold air."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(9):
        b.add(jackdaw(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.5, 0.85), 0.45)
    for _ in range(3):
        b.add(wl.caw(rng, 0.9), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.75, 0.4)
    tick = lambda r: noise_burst(r, 0.03, 3000, 6000, 0.004)  # noqa: E731
    t0 = rng.uniform(0, length)
    for k in range(10):
        b.add(tick(rng), t0 + 0.6 * k, -0.4, 0.4, 0.4)
    b.add(fox_bark(rng) if rng.random() < 0.5 else sd.dog(rng, 2), rng.uniform(0, length),
          rng.uniform(-0.8, 0.8), 0.95, 0.3)
    return sd.mix({"life": 2.5 * b.finish((2.2, 1.5, 0.6, 0.03), 0.45), "air": 0.07 * air(n, rng)})


def night_autumn(rng, length=NATURE_S):
    """An autumn night: tawny owls calling to each other (the season they hold territory),
    a few slow crickets, a fox barking, dry leaves stirring."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(3):
        at = rng.uniform(0, length)
        b.add(wl.tawny(rng), at, -0.5, 0.65, 0.45)
        b.add(tawny_female(rng), at + rng.uniform(3, 5), 0.5, 0.75, 0.4)
    sd.crickets(b, 2, level=0.2)
    b.add(fox_bark(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.9, 0.3)
    leaves = np.stack([wl.ambience.crackle(n, rng, 10 * swell(n, rng, 0.08, 0.8), 1200, 5000)
                       for _ in range(2)], axis=1)
    return sd.mix({"life": 2.5 * b.finish((2.5, 1.6, 0.6, 0.03), 0.45), "leaves": 0.05 * leaves,
                   "air": 0.05 * air(n, rng)})


def night_cold(rng, length=NATURE_S):
    """A winter night in the lowlands: no insects; an owl, a far dog, drips from the trees,
    a thin wind."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(2):
        b.add(wl.tawny(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.6, 0.85), 0.45)
    b.add(lowpass(sd.dog(rng, 3), 1500), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.3)
    for _ in range(int(length / 1.5)):
        b.add(weather.drip(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.4, 0.3)
    return sd.mix({"life": 2.5 * b.finish((2.8, 2.0, 0.7, 0.04), 0.5), "air": 0.1 * air(n, rng, 1)})


def night_snow(rng, length=NATURE_S):
    """A night under snow: the world muffled almost to silence; a breath of air, a bough
    creaking, an owl very far."""
    n = secs(length)
    b = sd.Bed(length, rng)
    b.add(lowpass(wl.tawny(rng), 1200), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.95, 0.4)
    for _ in range(2):
        b.add(sd.creak_short(rng, rng.uniform(0.5, 0.9)), rng.uniform(0, length),
              rng.uniform(-0.6, 0.6), 0.6, 0.25)
    b.add(bough_shed(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.6, 0.5)
    hush = lowpass(air(n, rng), 600)
    return sd.mix({"life": 2.0 * b.finish((3.0, 2.2, 0.8, 0.04), 0.4), "air": 0.12 * hush})


def day_snow(rng, length=NATURE_S):
    """A day under snow: the land hushed and close; a crow, tits in the bare twigs, a bough
    shedding its load, someone splitting wood far off, meltwater dripping at noon."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(2):
        b.add(wl.caw(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.8, 0.4)
    for _ in range(5):
        b.add(tit_call(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.3)
    for _ in range(2):
        b.add(bough_shed(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.5)
    t0 = rng.uniform(0, length)
    for k in range(4):
        b.add(axe_far(rng), t0 + 1.6 * k, 0.6, 0.9, 0.4)
    for _ in range(int(length / 2)):
        b.add(weather.drip(rng), rng.uniform(0, length), rng.uniform(-0.6, 0.6), 0.35, 0.2)
    hush = lowpass(air(n, rng), 700)
    return sd.mix({"life": 2.0 * b.finish((2.0, 1.4, 0.5, 0.02), 0.35), "air": 0.12 * hush})


# --- seasonal layers ---------------------------------------------------------------------


def frogs_spring(rng, length=NATURE_S):
    """Spring nights by water (March to May): the frogs in full chorus, toads trilling."""
    b = sd.Bed(length, rng)
    for _ in range(48):
        b.add(lowpass(wl.frog_croak(rng), 4000, 2), rng.uniform(0, length), rng.uniform(-0.9, 0.9),
              rng.uniform(0.3, 0.9), rng.uniform(0.3, 0.8))
    for _ in range(6):
        b.add(wl.toad_trill(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.4, 0.8), 0.2)
    n = secs(length)
    chorus = swell(n, rng, 0.05, 0.2, 0.5)[:, None]  # the chorus swells and falls as one
    return 2.5 * b.finish((2.0, 1.4, 0.5, 0.03), 0.4) * chorus


BARE = (dict(name="breeze", level=1), dict(name="strong", level=2))
BARE_LUFS = (-25.5, -22.0)


def wind_bare(level):
    """Wind through bare winter branches (December to February woods): twigs whistling thin
    and high, boughs knocking and creaking, no leaves to rustle."""
    p = BARE[level]

    def render(rng, length=31.0):
        n = secs(length)
        air_, g, _ = weather.wind_core(n, rng, weather.WIND[p["level"]])
        twigs = sum(weather.whistle(n, rng, g, f, 0.4, 0.25, t) for f, t in
                    ((rng.uniform(1300, 1600), 0.9), (rng.uniform(2100, 2500), 1.05),
                     (rng.uniform(900, 1100), 1.2)))
        b = sd.Bed(length, rng)
        for _ in range(int(length * (0.4 + 0.5 * level))):
            f = rng.uniform(250, 600)
            b.add(sd.modes(secs(0.2), [f, f * 2.3], [1.0, 0.3], [0.04, 0.015], rng),
                  rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.7), 0.4)
        for _ in range(2 + 2 * level):
            b.add(sd.creak_short(rng, rng.uniform(0.6, 1.2), rng.uniform(40, 70)),
                  rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.3)
        return sd.mix({"air": air_, "twigs": 0.5 * pan(twigs, 0.2),
                       "boughs": 2.0 * b.finish((1.5, 1.0, 0.4, 0.02), 0.3)})

    return render


def marsh_winter(rng, length=NATURE_S):
    """A Mesopotamian marsh in winter (November to February): geese honking on the reed beds
    and lifting off, ducks dabbling and quacking, wings, the water among the reeds."""
    n = secs(length)
    b = sd.Bed(length, rng)
    for _ in range(5):
        b.add(wl.goose_far(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.4, 0.8), 0.55)
    for _ in range(10):
        b.add(lowpass(wl.quack(rng, rng.uniform(0.1, 0.16), rng.uniform(0.85, 1.1)), 3500),
              rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.7), 0.4)
    for _ in range(3):
        b.add(sd.wingbeats(rng, 12, 7.0), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.4, 0.35)
    for _ in range(int(length / 3)):
        b.add(sd.splash_small(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.4, 0.25)
    g = swell(n, rng, 0.1, 0.5)
    reeds = np.stack([wl.ambience.crackle(n, rng, 40 * g, 1500, 4500) for _ in range(2)], axis=1)
    water = band(n, rng, 80, 1200, 0.9) * swell(n, rng, 0.2, 0.3)[:, None]
    return sd.mix({"life": 2.5 * b.finish((2.0, 1.4, 0.5, 0.03), 0.4), "reeds": 0.07 * reeds,
                   "water": 0.06 * water})


def flood(rng, length=NATURE_S):
    """Floodwater over the low fields (April and May): a broad slow sheet of water lapping at
    banks and stubble, gurgling through the reeds and into the ditches, a heron, frogs."""
    n = secs(length)
    laps = scatter_train(n, rng, 2.2 * swell(n, rng, 0.1, 0.4), kernels(weather.k_lap, 8, rng),
                         sigma=0.4)
    gurgle = scatter_train(n, rng, 25 * swell(n, rng, 0.15, 0.5),
                           kernels(lambda r: weather.k_bubble(r, 200, 900), 10, rng), sigma=0.6)
    b = sd.Bed(length, rng)
    b.add(home_sfx.heron(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.8, 0.4)
    for _ in range(8):
        b.add(wl.frog_croak(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.6, 0.3)
    return sd.mix({"laps": laps, "gurgle": 0.6 * gurgle,
                   "sheet": 0.06 * band(n, rng, 60, 1500, 0.9) * swell(n, rng, 0.08, 0.3)[:, None],
                   "life": 2.0 * b.finish((2.0, 1.4, 0.5, 0.03), 0.4)})


# --- the seasons' work (positional loops) --------------------------------------------------


def work_song(rng, character, length):
    """A worker humming a phrase now and then, far enough off to have no words."""
    c = people.CHARACTERS[character]
    f0, female = people.person(rng, c)
    return people.talker(length, rng, c, f0, female, 2000.0)


def reaping(rng, length=14.0):
    """Reapers in standing grain (June and July; April in Mesopotamia): sickles sweeping
    through the stalks, handfuls laid down, a sheaf bound, someone humming."""
    b = sd.Bed(length, rng, tail=3.0)
    strokes = int(round(length / 1.1))
    for k in range(strokes):
        for who, pos in ((0, -0.3), (1, 0.35)):
            b.add(people.sickle(rng), k * length / strokes + 0.45 * who + rng.normal(0, 0.05), pos,
                  0.3, rng.uniform(0.6, 1.0))
    for _ in range(3):
        b.add(people.grains(rng, 0.5, 80, 300, 2500), rng.uniform(0, length), rng.uniform(-0.5, 0.5),
              0.3, 0.6)
    hum = sd.Bed(length, rng, tail=length + 2)
    hum.add(lowpass(work_song(rng, "latin", 4.0), 1800), rng.uniform(0, length), 0.2, 0.6, 0.5)
    return b.finish((0.8, 0.6, 0.3, 0.01), 0.2) + 0.5 * hum.finish((1.0, 0.7, 0.3, 0.01), 0.3)


def winnowing(rng, length=12.0):
    """A winnowing floor (July and August): grain tossed high from a fan into the wind,
    pattering down, the chaff hissing away."""
    n = secs(length)
    b = sd.Bed(length, rng, tail=3.0)
    tosses = int(round(length / 2.4))
    for k in range(tosses):
        at = k * length / tosses
        m = secs(0.5)
        whoosh = band(m, rng, 400, 3000, 0.5, 1) * np.sin(np.pi * np.arange(m) / m) ** 2
        b.add(whoosh, at, 0.0, 0.3, 0.5)
        b.add(people.grains(rng, 1.2, 160, 1500, 6000), at + 0.6, rng.uniform(-0.3, 0.3), 0.35, 0.7)
    chaff = band(n, rng, 1500, 5500, 0.3) * swell(n, rng, 0.3, 0.6)[:, None]
    return b.finish((0.8, 0.6, 0.3, 0.01), 0.2) + 0.03 * chaff


def vintage(rng, length=16.0):
    """The vintage (September and October): grapes trodden in the vat, feet squelching in
    time, juice running into the trough, a double pipe keeping the treaders' rhythm."""
    n = secs(length)
    b = sd.Bed(length, rng, tail=3.0)
    steps = int(round(length / 0.5))
    for k in range(steps):
        b.add(sd.slap(rng) * rng.uniform(0.6, 1.0), k * length / steps, (-0.2, 0.2)[k % 2], 0.3, 0.7)
    juice = scatter_train(n, rng, 40, kernels(lambda r: weather.k_bubble(r, 300, 1200), 8, rng))
    tune = [(0.0, 0.5, 64), (0.5, 0.5, 67), (1.0, 1.0, 69), (2.0, 0.5, 67), (2.5, 0.5, 64),
            (3.0, 1.0, 62), (4.0, 0.5, 64), (4.5, 0.5, 67), (5.0, 0.5, 69), (5.5, 0.5, 71),
            (6.0, 2.0, 69)]
    pipe = sd.Bed(length, rng, tail=3.0)
    for rep in range(2):
        notes = [(s, d, hz(m), 0.7, k > 0 and d < 1, ()) for k, (s, d, m) in enumerate(tune)]
        pipe.add(an.reed_phrase("aulos", notes, secs(8.5), rng), 8.0 * rep, 0.3, 0.6, 0.35)
    return b.finish((0.8, 0.6, 0.3, 0.01), 0.2) + 0.3 * juice + pipe.finish((1.2, 0.8, 0.4, 0.01), 0.35)


def olive_harvest(rng, length=14.0):
    """The olive harvest (November to January): long poles beating the branches, leaves
    thrashing, olives pattering down onto spread cloths, voices among the trees."""
    b = sd.Bed(length, rng, tail=3.0)
    for _ in range(int(length / 1.4)):
        at, pos = rng.uniform(0, length), rng.uniform(-0.7, 0.7)
        f = rng.uniform(300, 600)
        b.add(sd.modes(secs(0.15), [f, f * 2.6], [1.0, 0.3], [0.03, 0.01], rng), at, pos, 0.4, 0.6)
        b.add(wl.ambience.crackle(secs(0.6), rng, 800, 1500, 5500), at, pos, 0.4, 0.25)
        b.add(people.grains(rng, 0.6, 30, 400, 2500), at + 0.15, pos, 0.4, 0.6)
    voices = 0.25 * sd.crowd(length, rng, 3, ceiling=1600)
    return b.finish((1.0, 0.7, 0.3, 0.01), 0.25) + voices


def ploughing(rng, length=14.0):
    """Ploughing and sowing (October and November): an ox team's slow steps in soft earth,
    the share tearing through the soil, the yoke creaking, the ploughman calling."""
    n = secs(length)
    b = sd.Bed(length, rng, tail=3.0)
    steps = int(round(length / 0.75))
    for k in range(steps):
        b.add(lowpass(people.hoof_earth(rng), 1500), k * length / steps, (-0.15, 0.15)[k % 2], 0.35, 0.6)
    for k in range(int(round(length / 3.5))):
        b.add(sd.creak_short(rng, rng.uniform(0.4, 0.7), rng.uniform(50, 80)), k * 3.5 + 1.0, 0.0, 0.35, 0.3)
    b.add(plough_call(rng), rng.uniform(0, length), 0.3, 0.5, 0.35)
    b.add(sd.ox(rng), rng.uniform(0, length), -0.2, 0.5, 0.3)
    soil = band(n, rng, 80, 1200, 0.9) * (0.7 + 0.3 * np.sin(2 * np.pi * times(n) / (length / steps)))[:, None]
    return b.finish((0.9, 0.6, 0.3, 0.01), 0.2) + 0.06 * soil


# --- festivals -------------------------------------------------------------------------


def komos(rng, length=20.0):
    """A Dionysiac revel going by (the Dionysia, the Lenaia, the Anthesteria, the Rural
    Dionysia): a quick aulos tune, tympanon and krotala, voices calling and laughing."""
    bpm = 132.0
    beat = 60.0 / bpm
    b = sd.Bed(length, rng, tail=16.0)  # the aulos tune is a 15 s phrase
    k = int(round(length / beat))
    for i in range(k):
        at = i * length / k
        stroke = "D" if i % 4 == 0 else ("T" if i % 2 else "k")
        b.add(an.frame_drum(stroke, 0.8 if stroke == "D" else 0.5, rng, 110.0), at, -0.3, 0.4, 0.8)
        if i % 2 == 1:
            b.add(an.clapper(0.5, rng, double=True), at, 0.35, 0.4, 0.6)
    tune = (64, 65, 67, 69, 67, 65, 64, 62, 64, 67, 69, 72, 71, 69, 67, 64)
    notes = [(j * 2 * beat, 2 * beat * 0.95, hz(m), 0.8, j % 4 != 0, ()) for j, m in enumerate(tune)]
    phrase = an.reed_phrase("aulos", notes, secs(len(tune) * 2 * beat + 0.5), rng)
    span = len(tune) * 2 * beat
    for r in range(int(length // span) + 1):
        b.add(phrase, r * span, 0.1, 0.4, 0.45)
    for _ in range(6):
        b.add(people.laugh(rng, people.CHARACTERS["greek"]), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.4)
        b.add(people.call_out(rng, people.CHARACTERS["greek"]), rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.35)
    crowd = 0.25 * sd.crowd(length, rng, 6, ceiling=2200)
    return b.finish((1.2, 0.9, 0.4, 0.015), 0.35) + crowd


def saturnalia(rng, length=20.0):
    """A Saturnalia night in the streets (17-23 December): laughter and greetings, little bells,
    dice rattling in a tavern, a tibia, clapping, the whole street in holiday."""
    c = people.CHARACTERS["latin"]
    b = sd.Bed(length, rng, tail=3.0)
    for _ in range(10):
        b.add(people.laugh(rng, c), rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.7), 0.45)
    for _ in range(6):
        b.add(people.call_out(rng, c), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.5, 0.4)
    for _ in range(14):
        b.add(sd.bell(rng.uniform(1800, 2600), rng, 0.4, "crotal"), rng.uniform(0, length),
              rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.6), 0.3)
    for _ in range(5):
        at, pos = rng.uniform(0, length), rng.uniform(-0.6, 0.6)
        for j in range(int(rng.integers(4, 8))):  # dice shaken in a cup, then thrown
            b.add(sd.clink(rng), at + 0.05 * j, pos, 0.5, 0.25)
    tune = [(0.0, 0.4, 65), (0.4, 0.4, 69), (0.8, 0.8, 72), (1.6, 0.4, 70), (2.0, 0.4, 69),
            (2.4, 1.2, 67), (3.6, 0.4, 65), (4.0, 1.6, 65)]
    notes = [(s, d, hz(m), 0.7, k > 0, ()) for k, (s, d, m) in enumerate(tune)]
    for r in range(3):
        b.add(an.reed_phrase("tibia", notes, secs(6.0), rng), r * 6.5 + rng.uniform(0, 0.5), 0.4, 0.6, 0.35)
    claps = people.clapping(rng, 4.0, 8, lambda a: np.sin(np.pi * a / 4.0))
    b.add(claps, rng.uniform(0, length), -0.3, 0.5, 0.3)
    crowd = 0.35 * sd.crowd(length, rng, 8, ceiling=2000)
    return b.finish((1.4, 1.0, 0.5, 0.012), 0.45) + crowd


def persian_feast(rng, length=24.0):
    """A feast at the court (the harvest offering, Bāgayādi, Mithrakāna): angular harp and
    double pipe over a frame drum, women singing and clapping, the court talking."""
    bpm = 96.0
    beat = 60.0 / bpm
    b = sd.Bed(length, rng, tail=3.0)
    k = int(round(length / beat))
    pattern = "D.kTD.Tk"
    for i in range(k):
        s = pattern[i % len(pattern)]
        if s != ".":
            b.add(an.frame_drum(s, 0.7 if s == "D" else 0.45, rng), i * length / k, -0.35, 0.4, 0.8)
    for i in range(0, k, 2):
        b.add(an.clapper(0.3, rng), i * length / k + beat, 0.4, 0.45, 0.4)
    harp = (62, 65, 67, 69, 67, 65, 64, 62)
    for i in range(int(length / beat)):
        b.add(an.string("harp", hz(harp[i % len(harp)]), 1.6, 0.6, rng), i * beat, 0.2, 0.35, 0.5)
    tune = [(0.0, 1.0, 69), (1.0, 0.5, 70), (1.5, 0.5, 69), (2.0, 1.0, 67), (3.0, 1.0, 65),
            (4.0, 2.0, 62)]
    notes = [(s * beat * 2, d * beat * 2, hz(m), 0.7, j > 0, ()) for j, (s, d, m) in enumerate(tune)]
    for r in range(2):
        b.add(an.reed_phrase("pipe", notes, secs(13 * beat + 0.5), rng), r * 12.5 * beat * 2 % length, 0.0, 0.45, 0.35)
    song = sd.song([(s * beat * 2, d * beat * 2, hz(m - 12)) for s, d, m in tune], rng, 1.0, 4, "o")
    b.add(song, rng.uniform(0, length / 2), -0.2, 0.55, 0.45)
    claps = people.clapping(rng, 6.0, 8, lambda a: np.ones_like(a))
    b.add(claps, rng.uniform(0, length), 0.3, 0.55, 0.3)
    crowd = 0.25 * sd.crowd(length, rng, 6, f0=(90, 200), ceiling=1600)
    return b.finish((2.0, 1.5, 0.6, 0.025), 0.45) + crowd


def tympanon(rng):
    """A tympanon roll and strokes with krotala, the Dionysiac drum flourish."""
    out = np.zeros(secs(3.4))
    for i in range(12):
        place(out, an.frame_drum("R", 0.4 + 0.04 * i, rng, 115.0), secs(0.06 * i))
    for i, s in enumerate("DTkTD"):
        place(out, an.frame_drum(s, 0.8, rng, 115.0), secs(0.9 + 0.36 * i))
        place(out, 0.5 * an.clapper(0.6, rng, double=True), secs(0.9 + 0.36 * i + 0.18))
    return out


def lituus(rng):
    """A lituus call: the curved Roman horn's high, bright partials in a rising signal."""
    out = np.zeros(secs(4.6))
    for at, m, dur in ((0.0, 65, 0.5), (0.6, 72, 0.5), (1.2, 77, 1.4), (2.8, 72, 0.4), (3.3, 77, 1.0)):
        place(out, an.horn(hz(m), dur, 0.8, rng, bright=1.4), secs(at))
    return out


# --- the turn of a season -----------------------------------------------------------------


def rome_season(rng):
    ev = [(0.0, lambda r: 0.3 * an.hydraulis(hz(53), 1.8, 0.4, r))]
    ev += stings.arp("cithara", (65, 72, 69, 77), 0.38, 0.6, 0.2)
    return stings.finish(stings.score(ev, rng), rng)


def athens_season(rng):
    ev = [(0.0, stings.pluck("kithara", 40, 0.55))]
    ev += stings.arp("lyra", (64, 71, 69, 76), 0.38, 0.55, 0.2)
    return stings.finish(stings.score(ev, rng), rng)


def parsa_season(rng):
    ev = [(0.0, lambda r: 0.35 * an.hum(hz(50), 1.8, 0.4, r))]
    ev += stings.arp("harp", (62, 69, 65, 74), 0.38, 0.6, 0.2)
    return stings.finish(stings.score(ev, rng), rng)


def world_season(rng):
    """The open land's turn: a soft fifth on A and E (the seams' drone) under a lute."""
    ev = [(0.0, lambda r: 0.3 * an.hum(hz(45), 1.8, 0.35, r)),
          (0.0, lambda r: 0.25 * an.hum(hz(52), 1.8, 0.3, r))]
    ev += stings.arp("lute", (69, 76, 73, 81), 0.38, 0.55, 0.25)
    return stings.finish(stings.score(ev, rng), rng)


def cicada_start(rng):
    """The first cicada of summer starting up, and two more joining."""
    out = np.zeros(secs(4.1))
    for k, (at, d) in enumerate(((0.0, 3.9), (1.2, 2.7), (2.2, 1.7))):
        x = sd.tymbal(rng, d, "buzz" if k else "pulsed")
        x = x * np.minimum(1, np.arange(len(x)) / secs(0.8))
        place(out, (1.0, 0.6, 0.45)[k] * x, secs(at))
    return out


def leaves_skitter(rng):
    """An autumn gust through dry leaves: a rush, leaves skittering across the ground."""
    n = secs(3.6)
    t = times(n)
    env = np.sin(np.pi * np.clip(t / 3.4, 0, 1)) ** 1.5
    rush = band(n, rng, 150, 2500, 0.6, 1) * env
    skitter = wl.ambience.crackle(n, rng, 400 * env, 1500, 6000)
    return 0.5 * rush + skitter


def frost_steps(rng):
    """The first frost: a few steps crunching over rimed grass in still air."""
    out = np.zeros(secs(3.0))
    for k in range(4):
        place(out, weather.k_crunch(rng, 0.14, 5000), secs(0.6 * k + abs(rng.normal(0, 0.02))))
    return out


# --- files -------------------------------------------------------------------------------

def _bed(render, lufs, purpose, when, where, tags, quality=0, gain=1.0):
    return entry("bed", render, lufs, purpose, gain=gain, when=when, where=where, quality=quality,
                 tags=tags)


ATHENS = {
    "amb/athens/day_cool.ogg": _bed(
        athens_day_cool, -22.0, "Athens without cicadas: wind in the olives, goat bells, sparrows "
        "and a robin, a plough ox far off, chisels, voices.", "day",
        "replaces amb/athens/day.ogg from October to May (theme.seasons)",
        ["season", "autumn", "winter", "spring", "athens"]),
    "amb/athens/night_winter.ogg": _bed(
        athens_night_winter, -23.0, "An Athenian winter night: no crickets; wind, a dog, the little "
        "owl, a symposium behind shutters, eaves dripping.", "night",
        "replaces amb/athens/night.ogg from November to March (theme.seasons)",
        ["season", "winter", "athens"]),
    "amb/athens/komos.ogg": entry(
        "loop", komos, -23.0, "A Dionysiac revel passing: aulos, tympanon and krotala, voices "
        "calling and laughing.", when="event",
        where="follows the cast of the Dionysia, Lenaia, Anthesteria and Rural Dionysia",
        tags=["festival", "athens", "winter", "spring"]),
    "sfx/athens/tympanon.wav": entry(
        "sfx", lambda r: sd.finish_sfx(tympanon(r), r, 0.3, 0.9, fade_out=0.3, longest=3.6), -23.0,
        "A tympanon roll and strokes with krotala (Dionysiac festivals).", gain=0.8,
        tags=["festival", "instrument", "athens"]),
    "sfx/athens/sting_season.wav": entry(
        "sfx", athens_season, -24.0, "A soft cue for the turn of a season, in Athens' Dorian on E "
        "(kithara and lyra).", gain=0.8, tags=["sting", "season", "athens"]),
}
PARSA = {
    "amb/parsa/plain_day_summer.ogg": _bed(
        parsa_day_summer, -22.0, "The plain in summer: hot wind, grasshoppers, flies, threshing far "
        "off, a horse snorting.", "day",
        "replaces amb/parsa/plain_day.ogg from June to September (theme.seasons)",
        ["season", "summer", "parsa", "east"]),
    "amb/parsa/plain_day_winter.ogg": _bed(
        parsa_day_winter, -22.0, "The plain in winter: cold wind, crows and a raven, no swallows, "
        "slow chisels, an ox, a dog.", "day",
        "replaces amb/parsa/plain_day.ogg from November to February (theme.seasons)",
        ["season", "winter", "parsa", "east"]),
    "amb/parsa/plain_night_winter.ogg": _bed(
        parsa_night_winter, -23.0, "A frost-still winter night: an owl, a guard pacing, a fire altar "
        "breathing, a jackal far off.", "night",
        "replaces amb/parsa/plain_night.ogg from November to March (theme.seasons)",
        ["season", "winter", "parsa", "east"], quality=1),
    "amb/parsa/feast.ogg": entry(
        "loop", persian_feast, -23.0, "A court feast: angular harp, double pipe, frame drum, women "
        "singing and clapping, the court talking (Elamite and Greek sources; inferred).",
        when="event", where="follows the harvest offering (June), Bāgayādi (September), "
        "Mithrakāna (November)", tags=["festival", "parsa", "summer", "autumn"]),
    "sfx/parsa/sting_season.wav": entry(
        "sfx", parsa_season, -24.0, "A soft cue for the turn of a season, in Pārsa's D mode "
        "(harp and hummed drone).", gain=0.8, tags=["sting", "season", "parsa"]),
}
ROME = {
    "amb/rome/day_winter.ogg": _bed(
        rome_day_winter, -22.0, "Rome in winter: no swallows; the murmur, hearths in the shops, "
        "wind in the streets, gutters dripping, jackdaws, a cart.", "day",
        "replaces amb/rome/day.ogg from December to February (theme.seasons)",
        ["season", "winter", "rome"]),
    "amb/rome/saturnalia.ogg": entry(
        "loop", saturnalia, -23.0, "A Saturnalia night in the street: laughter, little bells, dice, "
        "a tibia, clapping.", when="event", where="follows the Saturnalia's cast (winter day 1)",
        tags=["festival", "rome", "winter"]),
    "sfx/rome/lituus.wav": entry(
        "sfx", lambda r: sd.finish_sfx(lituus(r), r, 0.35, 1.4, fade_out=0.4, longest=5.2), -23.0,
        "A lituus call: the curved horn of processions and rites (Lupercalia, the October Horse, "
        "the Ludi).", gain=0.8, tags=["festival", "instrument", "rome"]),
    "sfx/rome/sting_season.wav": entry(
        "sfx", rome_season, -24.0, "A soft cue for the turn of a season, in Rome's F lydian-type "
        "mode (cithara and hydraulis).", gain=0.8, tags=["sting", "season", "rome"]),
}

W = "world"
FILES = {}
for _name, _fn, _phase, _seasons, _climates, _desc, _q in (
        ("dawn_autumn", dawn_autumn, "dawn", ["autumn"], ["mediterranean", "river_plain", "steppe"],
         "Autumn dawn: robins, starlings, crows, a wren, a far cockerel, dry leaves.", 0),
        ("dawn_winter", dawn_winter, "dawn", ["winter"], ["mediterranean", "river_plain", "mountain", "east", "steppe"],
         "Winter dawn: a robin, a wren, sparrows, crows, a far cockerel; thin and cold.", 0),
        ("dusk_autumn", dusk_autumn, "dusk", ["autumn"], ["mediterranean", "river_plain", "mountain", "east", "steppe"],
         "Autumn dusk: starlings gathering to roost, rooks, the last slow crickets, an owl.", 0),
        ("dusk_winter", dusk_winter, "dusk", ["winter"], ["mediterranean", "river_plain", "mountain", "east", "steppe"],
         "Winter dusk: jackdaws and rooks to roost, a robin ticking, a dog or a fox far off.", 0),
        ("night_autumn", night_autumn, "night", ["autumn"], ["mediterranean", "river_plain", "mountain"],
         "Autumn night: tawny owls calling to each other, a few slow crickets, a fox, leaves.", 0),
        ("night_cold", night_cold, "night", ["winter"], ["mediterranean", "river_plain", "east", "steppe"],
         "Winter night without snow: no insects; an owl, a far dog, drips, a thin wind.", 0),
        ("night_snow", night_snow, "night", ["winter"], ["mountain", "east", "steppe"],
         "A night under snow: muffled near silence, a breath of air, a bough creaking, a far owl.", 2),
        ("day_snow", day_snow, "day", ["winter"], ["mountain", "east", "steppe"],
         "A day under snow: a crow, tits, a bough shedding its load, wood split far off, drips.", 1)):
    FILES[f"amb/{W}/{_name}.ogg"] = _bed(
        _fn, -23.0, _desc, _phase,
        f"the {_phase} bed in {', '.join(_seasons)} for climates {', '.join(_climates)}"
        + (" while snow lies" if "snow" in _name else ""),
        ["nature", _phase, *_seasons, *_climates], quality=_q)
FILES.update({
    f"amb/{W}/frogs_spring.ogg": _bed(
        frogs_spring, -23.0, "Spring frogs in full chorus, toads trilling, swelling and falling.",
        "night", "a layer by rivers, marshes and ponds on spring nights (March to May), "
        "over the night bed", ["nature", "night", "spring", "water", "layer"]),
    f"amb/{W}/marsh_winter.ogg": _bed(
        marsh_winter, -23.0, "A winter marsh: geese honking and lifting, ducks, wings, reeds.",
        "day", "Mesopotamian and Susianan marshes, Tyrrhenian lagoons, November to February",
        ["nature", "winter", "water", "river_plain"]),
    f"amb/{W}/flood.ogg": _bed(
        flood, -23.0, "Floodwater over the fields: lapping, gurgling into ditches, a heron, frogs.",
        "always", "the flood_rising turn and flooded tiles (April and May: Babylon, Mesopotamia, "
        "Susa, Susiana; the Tiber's high months)", ["water", "flood", "spring"]),
    f"amb/{W}/reaping.ogg": entry(
        "loop", reaping, -25.0, "Reapers in standing grain: sickles, handfuls laid down, a hum.",
        when="worked", where="positional: reapers (June-July; April-May in Mesopotamia)",
        tags=["work", "season", "summer", "harvest"]),
    f"amb/{W}/winnowing.ogg": entry(
        "loop", winnowing, -25.0, "A winnowing floor: grain tossed into the wind, chaff hissing.",
        when="worked", where="positional: threshing floors after the harvest (July-August)",
        tags=["work", "season", "summer", "harvest"]),
    f"amb/{W}/vintage.ogg": entry(
        "loop", vintage, -25.0, "Grapes trodden in the vat to a double pipe, juice running.",
        when="worked", where="positional: grape pickers and treaders (September-October)",
        tags=["work", "season", "autumn", "vintage"]),
    f"amb/{W}/olive_harvest.ogg": entry(
        "loop", olive_harvest, -25.0, "Poles beating olive branches, olives pattering on cloths.",
        when="worked", where="positional: olive pickers (November-January)",
        tags=["work", "season", "winter", "olives"]),
    f"amb/{W}/ploughing.ogg": entry(
        "loop", ploughing, -25.0, "An ox team ploughing: slow steps, the share in the soil, the "
        "yoke creaking, the ploughman's call.", when="worked",
        where="positional: ploughmen and oxen (October-November)",
        tags=["work", "season", "autumn", "ploughing"]),
    f"sfx/{W}/sting_season.wav": entry(
        "sfx", world_season, -24.0, "A soft cue for the turn of a season on the open land (a fifth "
        "on A and E under a lute).", gain=0.8, tags=["sting", "season", "world"]),
    f"sfx/{W}/cicada_start.wav": entry(
        "sfx", wl.fx(cicada_start), -26.0, "The first cicada of summer starting up, two more joining.",
        gain=0.8, tags=["turn", "summer", "insects"]),
    f"sfx/{W}/leaves_skitter.wav": entry(
        "sfx", wl.fx(leaves_skitter), -25.0, "An autumn gust through dry leaves skittering away.",
        gain=0.8, tags=["turn", "autumn", "leaves"]),
    f"sfx/{W}/frost_steps.wav": entry(
        "sfx", wl.fx(frost_steps), -27.0, "Steps crunching over rimed grass in still air.",
        gain=0.7, tags=["turn", "winter", "frost"]),
})
for _lvl, _p in enumerate(BARE):
    FILES[f"amb/{W}/wind_bare_{_lvl + 1}.ogg"] = entry(
        "bed", wind_bare(_lvl), BARE_LUFS[_lvl], f"Wind through bare winter branches, {_p['name']}.",
        when="weather", where="woods and orchards from December to February, by wind strength "
        "(in place of the leafy wind.trees)", family="wind.bare", level=_lvl + 1,
        level_name=_p["name"], tags=["weather", "wind", "trees", "winter"])
