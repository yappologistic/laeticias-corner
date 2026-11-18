"""Athens (high summer, 432 BC): music, ambience beds and effects.

Music: kithara leading and aulos answering in heterophony (the same tune at once, each in
its own way), over drones and parallel fourths and fifths only, no modern chords. Day is in
the Dorian octave species (E F G A B C D E, falling tetrachords A G F E), phrased in dactylic
lines (long-short-short, six feet = two bars of 6/4) at 90 bpm. Night is the Lydian species
on the same strings (final C) for a low barbitos, slower, with a far-off aulos; its motif
C F G C is the day's rising E A B E moved into the night mode."""

import numpy as np

import ancient
import score
import sounds as sd
from dsp import SR, lowpass, midi_hz, pan, place, secs

# --- music -----------------------------------------------------------------------------

THEME = [  # four hexameter lines, two 6/4 bars each
    "E4/1 A4/0.5 B4/0.5 C5/1 B4/0.5 A4/0.5 B4/1 C5/0.5 D5/0.5",
    "E5/1 D5/0.5 C5/0.5 B4/1 A4/1 B4/2",
    "C5/1 B4/0.5 A4/0.5 G4/1 A4/0.5 B4/0.5 C5/1 B4/1",
    "A4/1 G4/0.5 F4/0.5 E4/1 F4/1 E4/2",
    "E4/1 A4/0.5 B4/0.5 C5/1 D5/0.5 E5/0.5 F5/1 E5/1",
    "D5/1 C5/0.5 B4/0.5 C5/1 A4/1 B4/2",
    "G4/1 A4/0.5 B4/0.5 C5/1 B4/0.5 A4/0.5 G4/1 F4/1",
    "E4/1 F4/0.5 G4/0.5 A4/1 G4/0.5 F4/0.5 E4/2",
]
THEME_B = [  # the theme again, its turns varied, once the aulos has joined
    "E4/1 A4/0.5 B4/0.5 C5/1 B4/0.5 A4/0.5 B4/1 D5/0.5 C5/0.5",
    "E5/1 D5/0.5 C5/0.5 B4/1 C5/0.5 A4/0.5 B4/2",
    "C5/1 B4/0.5 A4/0.5 G4/1 A4/0.5 B4/0.5 C5/1 A4/1",
    "A4/1 G4/0.5 F4/0.5 E4/1 G4/0.5 F4/0.5 E4/2",
    "E4/1 A4/0.5 B4/0.5 C5/1 D5/0.5 E5/0.5 F5/1 E5/1",
    "D5/1 E5/0.5 D5/0.5 C5/1 A4/1 B4/2",
    "G4/1 A4/0.5 B4/0.5 C5/1 B4/0.5 A4/0.5 G4/1 F4/1",
    "E4/1 G4/0.5 F4/0.5 A4/1 G4/0.5 F4/0.5 E4/2",
]
STRUM = "A3+E4+A4/1 E4/0.5 A4/0.5 A3+E4+A4/1 E4/0.5 A4/0.5 A3+E4/2"
STRUM_G = "G3+D4+G4/1 D4/0.5 G4/0.5 A3+E4+A4/1 E4/0.5 A4/0.5 A3+E4/2"
RETURN = [
    "E4/1 A4/0.5 B4/0.5 C5/1 B4/0.5 A4/0.5 B4/1 C5/0.5 D5/0.5",
    "E5/2 D5/1 C5/1 B4/2",
    "A4/1 G4/0.5 F4/0.5 G4/1 A4/0.5 B4/0.5 C5/2",
    "B4/1 A4/1 G4/1 F4/1 E4/2",
    "r/2 A3+E4/1 r/1 B3+E4/2",
    "A4/1 G4/0.5 F4/0.5 E4/2 r/2",
    "E3+B3/2 G3/1 A3/1 B3/2",
    "A3/2 G3/1 A3/1 B3/1 D4/1",
]
DAY_KITHARA = " | ".join(THEME + THEME_B + [STRUM, STRUM, STRUM, STRUM_G, STRUM, STRUM, STRUM_G,
                                            "A3+E4/2 E3+B3+E4/4"] + RETURN)

LOW = ["E3+B3/3 A3+E4/3", "E3+B3/6"]
DAY_LOW = " | ".join(LOW * 8 + ["r/6"] * 8 + LOW * 2 + ["E3+B3/6", "A3+E4/6", "E3+B3/6", "r/3 E3/3"])

AULOS_B = [  # heterophony: the kithara's tune held longer, with the piper's flicks
    "E4/1 A4/1 C5/1.5 A4/0.5 B4/1 D5/1",
    "D5'E5/2 C5/1 A4/1 B4/2",
    "C5/2 A4/1 B4/1 C5/1 B4/1",
    "A4/1 G4/1 E4/1 F4/1 F4'E4/2",
    "E4/1 A4/1 C5/1 E5/1 F5/1 E5/1",
    "D5/2 C5/1 A4/1 B4/2",
    "G4/2 C5/1 A4/1 G4/1 F4/1",
    "E4/1 G4/1 A4/1 F4/1 F4'E4/2",
]
AULOS_FEAST = [  # the festival lines centre on A, the mese, and climb
    "A4/1 C5/0.5 D5/0.5 E5/1 D5/0.5 C5/0.5= D5/1 E5/1",
    "F5/1 E5/0.5 D5/0.5= E5/1 C5/1 B4'A4/2",
    "A4/1 B4/0.5 C5/0.5 D5/1 C5/0.5 B4/0.5= C5/1 A4/1",
    "G4/1 A4/0.5 B4/0.5 C5/1 B4/1 B4'A4/2",
    "E5/1 F5/0.5 E5/0.5= D5/1 E5/0.5 D5/0.5= C5/1 D5/1",
    "E5/1 D5/0.5 C5/0.5= B4/1 C5/1 B4'A4/2",
    "C5/1 B4/0.5 A4/0.5= G4/1 A4/0.5 B4/0.5 C5/1 B4/1",
    "A4/1 G4/0.5 F4/0.5= E4/1 F4/1 F4'E4/2",
]
DAY_AULOS = " | ".join(["r/6"] * 8 + AULOS_B + AULOS_FEAST
                       + ["r/6"] * 4 + ["r/2 C5/2 B4/2", "A4/2 F4'E4/4", "r/6", "r/6"])
DAY_DRONE = " | ".join(["r/6"] * 8 + ["E4/6="] * 8 + ["A3/6="] * 7 + ["E4/6="] * 8 + ["r/6"])

FOOT = "D/1 k/0.5? k/0.5? T/1 k/0.5? k/0.5? D/1 T/1"
DAY_DRUM = " | ".join(["r/6"] * 12 + ["D/1? r/5", "D/1? r/5", "D/1? r/2 D/1? r/2", "D/1? r/5"]
                      + [FOOT] * 7 + ["D/2 r/4"] + ["r/6"] * 8)
DAY_KROTALA = " | ".join(["r/6"] * 16 + ["K/1 K/0.5? K/0.5? " * 3] * 7 + ["K/2 r/4"]
                         + ["r/6"] * 8)

DAY = {
    "bpm": 90, "meter": [6], "phrase": 12, "tail": 5.0,
    "reverb": (1.8, 1.1, 0.6, 0.012),  # a courtyard: walls close by, open sky above
    "parts": {
        "kithara": {"voice": "kithara", "notes": DAY_KITHARA, "gain": 1.0, "pan": -0.15,
                    "spread": 0.4, "send": 0.3, "ring": 3.0, "strum": 0.02, "vel": 0.8},
        "low": {"voice": "kithara", "notes": DAY_LOW, "gain": 0.45, "pan": -0.3, "send": 0.3,
                "ring": 3.5, "strum": 0.03, "vel": 0.6},
        "aulos": {"voice": "aulos", "notes": DAY_AULOS, "gain": 0.2, "pan": 0.25, "send": 0.35,
                  "vel": 0.8},
        "drone": {"voice": "aulos", "notes": DAY_DRONE, "gain": 0.06, "pan": 0.3, "send": 0.35,
                  "vel": 0.7, "legato": True},
        "drum": {"voice": "drum", "notes": DAY_DRUM, "gain": 0.32, "pan": 0.4, "send": 0.25,
                 "tune": 120.0, "vel": 0.7},
        "krotala": {"voice": "drum", "notes": DAY_KROTALA, "gain": 0.35, "pan": -0.45,
                    "send": 0.25, "tune": 1500.0, "vel": 0.7},
    },
}

NIGHT_BARBITOS = (
    "C4/1 F4/1 G4/1 C5/1 | C5/3 B4/1 | A4/2 G4/1 F4/1 | G4/4 "
    "| E4/1 F4/1 G4/1 A4/1 | G4/2 F4/1 E4/1 | D4/2 E4/1 F4/1 | E4/4 "
    "| C3+G3/2 E4/1 G4/1 | A4/2 C5/1 B4/1 | A4/1 G4/1 F4/1 E4/1 | F4/4 "
    "| D4/1 F4/1 A4/1 G4/1 | F4/2 E4/1 D4/1 | E4/1 D4/1 C4/2 | C3+G3/4 "
    "| E4/1 G4/1 C5/1 D5/1 | E5/3 D5/1 | C5/2 B4/1 A4/1 | G4/4 "
    "| A4/1 C5/1 B4/1 G4/1 | A4/2 F4/1 G4/1 | E4/2 D4/1 E4/1 | F4/4 "
    "| C3+G3/2 G4/1 F4/1 | E4/2 D4/1 C4/1 | D4/1 E4/1 F4/1 D4/1 | C4/4 "
    "| r/4 | C3+G3/4 | r/2 F3/1 G3/1 | A3/2 B3/2"
)
NIGHT_LOW = ("C3/8 | F2+C3/8 | C3+G3/8 | r/8 | C3/8 | F2+C3/8 | C3+G3/8 | r/8 | r/8 | C3/8 "
             "| F2+C3/8 | C3+G3/8 | r/32")
NIGHT_AULOS = " | ".join(["r/4"] * 3 + ["r/1 E5/1 D5/1= C5/1"] + ["r/4"] * 7
                         + ["r/1 C5/1 A4/1= F4/1"] + ["r/4"] * 7 + ["r/1 D5/1 E5/1= C5/1"]
                         + ["r/4"] * 7 + ["r/1 E4/1 G4/1= E4/1"] + ["r/4"] * 4)

NIGHT = {
    "bpm": 60, "meter": [4], "phrase": 8, "rubato": (0.2, 8), "tail": 8.0,
    "reverb": (1.6, 1.0, 0.5, 0.01),  # close and dry: a courtyard wall away
    "parts": {
        "barbitos": {"voice": "barbitos", "notes": NIGHT_BARBITOS, "gain": 1.0, "pan": 0.05,
                     "spread": 0.4, "send": 0.35, "ring": 7.0, "vel": 0.75},
        "low": {"voice": "barbitos", "notes": NIGHT_LOW, "gain": 0.4, "pan": -0.2, "send": 0.35,
                "ring": 7.0, "vel": 0.55},
        "aulos": {"voice": "aulos", "notes": NIGHT_AULOS, "gain": 0.05, "pan": 0.5, "send": 1.0,
                  "vel": 0.6},
    },
}


def day(rng):
    return score.render(DAY, rng)


def night(rng):
    return score.render(NIGHT, rng)


# --- ambience --------------------------------------------------------------------------


def sculptors(bed, bouts, dist=(0.75, 0.95), level=0.4):
    """Hammer and chisel on marble far off: bouts of blows at a working pace."""
    for _ in range(bouts):
        t, pos = bed.rng.uniform(0, bed.n / SR), bed.rng.uniform(-0.8, 0.8)
        d, pace = bed.rng.uniform(*dist), bed.rng.uniform(0.35, 0.6)
        make = sd.chisel if bed.rng.random() < 0.6 else sd.hammer_stone
        for k in range(int(bed.rng.integers(4, 10))):
            bed.add(make(bed.rng), t + k * pace + bed.rng.normal(0, 0.02), pos, d,
                    level * bed.rng.uniform(0.6, 1.0))


def goat_bells(bed, flocks=2, level=0.25):
    """Goats grazing on a far hillside: hammered bells clonking now and then."""
    for _ in range(flocks):
        pos = bed.rng.uniform(-0.8, 0.8)
        for _ in range(int(bed.rng.integers(10, 18))):
            bed.add(sd.bell(bed.rng.uniform(700, 1100), bed.rng, 0.5, "sheet"),
                    bed.rng.uniform(0, bed.n / SR), pos + bed.rng.uniform(-0.15, 0.15),
                    bed.rng.uniform(0.75, 0.9), level * bed.rng.uniform(0.4, 1.0))


def city_day(rng, layers=None, length=48.0):
    """Athens by day: a wall of cicadas rising and falling in waves, distant voices, hammer
    and chisel on marble, goat bells on the hills, swallows."""
    n = secs(length)
    bugs = sd.Bed(length, rng)
    sd.cicadas(bugs, 22, level=0.8)
    life = sd.Bed(length, rng)
    sculptors(life, 6)
    goat_bells(life)
    life.scatter(sd.swallow, 10, dist=(0.3, 0.8), level=(0.3, 0.6))
    return sd.mix({
        "cicadas": 1.1 * bugs.finish((1.5, 1.0, 0.5, 0.02), 0.3) * sd.swell(n, rng, 0.05, 0.5)[:, None],
        "life": 1.0 * life.finish((2.0, 1.2, 0.6, 0.02), 0.4),
        "voices": 0.35 * sd.crowd(length, rng, 6, ceiling=1300),
        "air": 0.05 * sd.wind(n, rng, 150, 1500, 0.06, 0.5),
    }, layers)


def agora(rng, layers=None, length=48.0):
    """The Agora: a crowd murmuring and bargaining close by (no words), a herald's long
    call far off, a donkey, feet on the beaten earth."""
    n = secs(length)
    near = sd.crowd(length, rng, 5, f0=(110, 230), ceiling=2600, spread=0.7)
    far = sd.crowd(length, rng, 12, ceiling=1500)
    herald = sd.crowd(length, rng, 0, f0=(120, 140), ceiling=2000, calling=1)
    life = sd.Bed(length, rng)
    life.add(sd.donkey(rng), rng.uniform(0, length - 4), rng.uniform(-0.6, 0.6), 0.6, 0.5)
    for _ in range(40):
        life.add(sd.step(rng, "dust"), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 rng.uniform(0.2, 0.6), rng.uniform(0.2, 0.5))
    bugs = sd.Bed(length, rng)
    sd.cicadas(bugs, 8, level=0.5, dist=(0.5, 0.7))
    surge = sd.swell(n, rng, 0.06, 0.25, 0.3)[:, None]  # bargains struck, a crowd's ebb and flow
    return sd.mix({
        "near": 0.5 * near * surge,
        "far": 0.35 * far,
        "herald": 0.2 * herald,
        "life": life.finish((1.5, 1.0, 0.5, 0.02), 0.35),
        "cicadas": 0.6 * bugs.finish((1.5, 1.0, 0.5, 0.02), 0.3),
    }, layers)


ROW = {  # a trireme's piper keeping the stroke, heard across the water (one figure per stroke)
    "bpm": 90, "meter": [6], "tail": 3.0, "reverb": (1.5, 1.0, 0.5, 0.01),
    "parts": {"aulos": {"voice": "aulos", "gain": 1.0, "pan": 0.0, "send": 0.3, "vel": 0.8,
                        "notes": "A4/1 E4/2 r/3 | A4/1 E4/2 r/3"}},
}


def sea(rng, layers=None, length=48.0):
    """Piraeus: small waves on the moles, rigging creaking and tapping, gulls, orders
    shouted (no words), and far out a trireme rowing to its piper."""
    n = secs(length)
    rig = sd.Bed(length, rng)
    for _ in range(14):
        rig.add(sd.creak_short(rng, rng.uniform(0.3, 0.8)), rng.uniform(0, length),
                rng.uniform(-0.7, 0.7), rng.uniform(0.3, 0.6), rng.uniform(0.15, 0.3))
    for _ in range(18):  # halyards tapping a mast
        rig.add(sd.modes(secs(0.12), [rng.uniform(600, 900), 1700], [1.0, 0.3], [0.03, 0.01], rng),
                rng.uniform(0, length), rng.uniform(-0.6, 0.6), 0.5, rng.uniform(0.1, 0.3))
    rig.scatter(sd.gull, 7, dist=(0.4, 0.85), level=(0.3, 0.6))
    row = sd.Bed(length, rng)
    t0 = rng.uniform(0, length)
    piper = score.render(ROW, rng, one_shot=8.0).mean(axis=1)
    for k in range(3):  # the stroke comes and goes as the ship passes beyond the mole
        row.add(piper, t0 + 8 * k, 0.5, 0.92, 0.6)
        for j in range(2):
            row.add(lowpass(sd.slap(rng), 1200), t0 + 8 * k + j * 4 + 0.6, 0.5, 0.92, 0.7)
    shouts = sd.crowd(length, rng, 2, f0=(120, 180), ceiling=2000, calling=2)
    return sd.mix({
        "waves": 0.2 * sd.waves(n, rng, 6.0),
        "rig": rig.finish((1.5, 1.0, 0.5, 0.02), 0.3),
        "row": 0.4 * row.finish((2.5, 1.6, 0.8, 0.03), 0.6),
        "shouts": 0.18 * shouts,
        "wind": 0.04 * sd.wind(n, rng, 200, 2500, 0.08, 0.5),
    }, layers)


def rock(rng, layers=None, length=48.0):
    """The Acropolis plateau: steady wind over the rock and round the columns, a kestrel
    hanging in it, cicadas far below, now and then a chisel."""
    n = secs(length)
    life = sd.Bed(length, rng)
    life.scatter(sd.kestrel, 2, dist=(0.5, 0.7), level=(0.4, 0.5))
    sculptors(life, 2, level=0.3)
    bugs = sd.Bed(length, rng)
    sd.cicadas(bugs, 12, level=0.6, dist=(0.55, 0.7))
    return sd.mix({
        "wind": 0.18 * sd.wind(n, rng, 120, 2600, 0.06, 0.7, whistle=0.05),
        "life": life.finish((2.0, 1.4, 0.7, 0.02), 0.4),
        "cicadas": 1.2 * bugs.finish((1.5, 1.0, 0.5, 0.02), 0.3),
    }, layers)


def symposium(rng):
    """Through a courtyard wall: men singing a slow tune together and an aulos with them."""
    tune = [(0.0, 0.8, 48), (0.8, 0.4, 52), (1.2, 0.8, 53), (2.0, 1.2, 55), (3.2, 0.4, 53),
            (3.6, 0.8, 52), (4.4, 0.8, 50), (5.2, 1.6, 48)]
    x = sd.song([(s, d, float(midi_hz(m))) for s, d, m in tune], rng, voices=4, vowel="a")
    notes = [(s, d, float(midi_hz(m + 12)), 0.7, False, []) for s, d, m in tune]
    pipe = ancient.reed_phrase("aulos", notes, len(x), rng)
    return lowpass(x + 0.3 * pipe / (np.abs(pipe).max() + 1e-9) * np.abs(x).max(), 1600)


def city_night(rng, layers=None, length=48.0):
    """Athens at night: crickets, a dog across town, a symposium singing far off with an
    aulos, a little owl on the rock."""
    n = secs(length)
    life = sd.Bed(length, rng)
    sd.crickets(life, 5, level=0.3)
    for _ in range(2):
        life.add(sd.dog(rng, int(rng.integers(2, 4))), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 0.85, 0.4)
    t = rng.uniform(0, 10)
    for k in range(5):
        life.add(sd.little_owl(rng), t + k * rng.uniform(5, 8), -0.5, 0.7, 0.35)
    party = sd.Bed(length, rng)
    t = rng.uniform(0, length)
    for k in range(3):
        party.add(symposium(rng), t + k * 14, 0.4, 0.9, 0.7)
    return sd.mix({
        "life": life.finish((2.5, 1.6, 0.7, 0.03), 0.45),
        "party": 1.6 * party.finish((1.5, 1.0, 0.5, 0.02), 0.5),
        "air": 0.04 * sd.wind(n, rng, 100, 1200, 0.05, 0.5),
    }, layers)


def potters(rng, layers=None, length=40.0):
    """The Kerameikos: kick wheels turning, clay slapped and wedged, a kiln roaring in
    its yard, fired pots clinking as they are stacked."""
    n = secs(length)
    work = sd.Bed(length, rng)
    for _ in range(30):
        work.add(sd.slap(rng), rng.uniform(0, length), rng.uniform(-0.7, 0.7), rng.uniform(0.3, 0.7),
                 rng.uniform(0.3, 0.7))
    for _ in range(4):
        t = rng.uniform(0, length)
        for k in range(int(rng.integers(3, 7))):
            work.add(sd.clink(rng), t + k * rng.uniform(0.4, 0.9), rng.uniform(-0.6, 0.6), 0.5, 0.35)
    wheels = sum(pan(sd.wheel(length, rng, rpm), p) for rpm, p in ((105, -0.5), (125, 0.3)))
    return sd.mix({
        "wheels": 0.3 * wheels,
        "kiln": 0.25 * pan(sd.kiln(length, rng), 0.6),
        "work": 2.5 * work.finish((1.2, 0.9, 0.4, 0.01), 0.3),
        "voices": 0.2 * sd.crowd(length, rng, 3, ceiling=1500),
    }, layers)


def wheel(rng):
    return sd.wheel(8.0, rng)


def kiln(rng):
    return sd.kiln(12.0, rng)


# The Panathenaic procession passing: aulos and kithara in a hymn line, krotala and drum on
# the dactyls; three hexameter lines (6 bars of 6/4 at 90 bpm = 24 s), loopable.
PROCESSION = {
    "bpm": 90, "meter": [6], "phrase": 12, "tail": 4.0, "offset": 0.5,
    "reverb": (1.6, 1.1, 0.6, 0.015),
    "parts": {
        "aulos": {"voice": "aulos", "gain": 0.45, "pan": 0.1, "send": 0.3, "vel": 0.85,
                  "notes": " | ".join(AULOS_FEAST[:4] + AULOS_FEAST[6:])},
        "kithara": {"voice": "kithara", "gain": 0.8, "pan": -0.2, "send": 0.3, "ring": 2.5,
                    "strum": 0.02, "vel": 0.75,
                    "notes": " | ".join([STRUM, STRUM, STRUM, STRUM_G, STRUM, "A3+E4/2 E3+B3+E4/4"])},
        "drum": {"voice": "drum", "gain": 0.5, "pan": 0.3, "send": 0.25, "tune": 120.0,
                 "vel": 0.75, "notes": " | ".join([FOOT] * 6)},
        "krotala": {"voice": "drum", "gain": 0.45, "pan": -0.4, "send": 0.25, "tune": 1500.0,
                    "vel": 0.7, "notes": " | ".join(["K/1 K/0.5? K/0.5? " * 3] * 6)},
    },
}


def procession(rng):
    return score.render(PROCESSION, rng)


# --- effects ---------------------------------------------------------------------------

AULOS_SOLO = {  # a piper at a sacrifice or a courtyard door
    "bpm": 90, "meter": [6], "tail": 2.0, "reverb": (1.5, 1.0, 0.5, 0.012),
    "parts": {"aulos": {"voice": "aulos", "gain": 1.0, "pan": 0.0, "send": 0.3, "vel": 0.85,
                        "notes": "E4/1 A4/0.5 B4/0.5 C5/1 B4/0.5 A4/0.5= B4/1 G4/1 | F4'E4/3 r/3"},
              "drone": {"voice": "aulos", "gain": 0.25, "pan": 0.0, "send": 0.3, "vel": 0.7,
                        "legato": True, "notes": "E4/9 r/3"}},
}
LYRE = {  # a lyre swept with the plectrum, then a few notes, as at a school or a party
    "bpm": 90, "meter": [6], "tail": 2.0, "reverb": (1.2, 0.8, 0.4, 0.01),
    "parts": {"lyra": {"voice": "lyra", "gain": 1.0, "pan": 0.0, "send": 0.3, "ring": 2.5,
                       "strum": 0.025, "vel": 0.8,
                       "notes": "E3+B3+E4+A4/1.5 B4/0.5 A4/0.5 G4/0.5 A4/1 E4/2 | r/6"}},
}
ARRIVE = {  # the overview motif: a rising kithara figure E A B E, the aulos holding E
    "bpm": 90, "meter": [6], "tail": 3.0, "reverb": (1.8, 1.2, 0.6, 0.012),
    "parts": {"kithara": {"voice": "kithara", "gain": 1.0, "pan": 0.0, "spread": 0.4,
                          "send": 0.35, "ring": 3.5, "strum": 0.02, "vel": 0.85,
                          "notes": "E4/1 A4/0.5 B4/0.5 E5/4 | E3+B3+E4/6"},
              "aulos": {"voice": "aulos", "gain": 0.15, "pan": 0.2, "send": 0.35, "vel": 0.7,
                        "legato": True, "notes": "r/2 E4/6 r/4"}},
}


def phrase(piece, rng, keep):
    """A short score as a one-shot (not a loop), mono."""
    x = score.render(piece, rng, one_shot=keep)
    return sd.finish_sfx(x.mean(axis=1) * np.sqrt(2), rng, 0.0, fade_out=0.5)


def aulos(rng):
    return phrase(AULOS_SOLO, rng, 6.0)


def lyre(rng):
    return phrase(LYRE, rng, 4.5)


def arrive(rng):
    return phrase(ARRIVE, rng, 5.5)


def owl(rng):
    x = np.concatenate([sd.little_owl(rng), np.zeros(secs(1.1)), sd.little_owl(rng)])
    return sd.finish_sfx(x, rng, 0.3, 1.0)


def trireme(rng):
    """A trireme's timbers working as she rolls: hull creaks and an oar knocking in its
    leather strap."""
    out = np.zeros(secs(3.0))
    for at in (0.0, 0.9, 1.6):
        place(out, 0.7 * sd.creak_short(rng, rng.uniform(0.5, 0.9), rng.uniform(50, 80)), secs(at))
    for at in (0.5, 2.0):
        place(out, sd.modes(secs(0.2), [220, 480], [1.0, 0.4], [0.04, 0.02], rng), secs(at))
    return sd.finish_sfx(lowpass(out, 3000), rng, 0.2)


def oars(rng):
    """Oars in time (S4): three strokes, each a splash and the knock of the oar on its pin,
    with the piper's two-note call."""
    out = np.zeros(secs(5.0))
    piper = score.render(ROW, rng, one_shot=4.0).mean(axis=1)
    place(out, 0.3 * piper / (np.abs(piper).max() + 1e-9), 0)
    for k in range(3):
        t = 0.6 + 1.33 * k
        for j in range(5):  # a bank of oars never enters quite together
            place(out, 0.4 * sd.slap(rng), secs(t + rng.normal(0, 0.02)))
            place(out, 0.2 * sd.modes(secs(0.1), [300, 650], [1.0, 0.4], [0.02, 0.01], rng),
                  secs(t - 0.25 + rng.normal(0, 0.015)))
    return sd.finish_sfx(lowpass(out, 4000), rng, 0.3, 1.0)


# --- files -----------------------------------------------------------------------------

FILES = {
    "music/athens/day.ogg": dict(
        kind="music", render=day, piece=DAY, lufs=-18.0, quality=4, gain=1.0, when="day",
        purpose="Day piece: kithara theme in the Dorian species on E in dactylic lines, aulos "
                "joining in heterophony, a festival middle on A with krotala and drum."),
    "music/athens/night.ogg": dict(
        kind="music", render=night, piece=NIGHT, lufs=-18.0, quality=4, gain=1.0, when="night",
        purpose="Night piece: solo barbitos in the Lydian species on C (free time), a far aulos "
                "answering four times."),
    "amb/athens/day.ogg": dict(
        kind="bed", render=city_day, lufs=-22.0, quality=2, gain=1.0, when="day",
        where="everywhere in the region",
        purpose="Cicadas in waves, distant voices, hammer and chisel on marble, goat bells, swallows."),
    "amb/athens/agora.ogg": dict(
        kind="bed", render=agora, lufs=-22.0, quality=2, gain=0.8, when="day",
        where="zone or count-driven: the Agora (vendors and customers, full = 12)",
        purpose="Close crowd murmur and bargaining without words, a herald far off, a donkey, feet."),
    "amb/athens/sea.ogg": dict(
        kind="bed", render=sea, lufs=-22.0, quality=2, gain=0.8, when="always",
        where="zone: Piraeus harbours and the Long Walls' sea end",
        purpose="Small waves, rigging creak and halyard taps, gulls, shouted orders, a trireme "
                "rowing to its piper far out."),
    "amb/athens/rock.ogg": dict(
        kind="bed", render=rock, lufs=-22.0, quality=2, gain=0.8, when="day",
        where="zone: the Acropolis plateau",
        purpose="Wind over the rock, a kestrel, cicadas far below, an occasional chisel."),
    "amb/athens/night.ogg": dict(
        kind="bed", render=city_night, lufs=-23.0, quality=2, gain=1.0, when="night",
        where="everywhere in the region",
        purpose="Crickets, a dog across town, a symposium singing far off with an aulos, a little owl."),
    "amb/athens/potters.ogg": dict(
        kind="bed", render=potters, lufs=-22.0, quality=2, gain=0.8, when="day",
        where="zone: the Kerameikos potters' quarter",
        purpose="Kick wheels, clay slapped and wedged, a kiln roaring, pots clinking."),
    "amb/athens/procession.ogg": dict(
        kind="loop", render=procession, piece=PROCESSION, lufs=-23.0, quality=2, gain=0.8,
        when="event", where="positional: follows the Panathenaic procession (A1)",
        purpose="Aulos and kithara hymn with drum and krotala walking past (6 bars, 90 bpm)."),
    "amb/athens/wheel.ogg": dict(
        kind="loop", render=wheel, lufs=-25.0, quality=2, gain=0.7, when="worked",
        where="positional: a potter's wheel slot while it is used",
        purpose="A potter's kick wheel turning, hands on wet clay."),
    "amb/athens/kiln.ogg": dict(
        kind="loop", render=kiln, lufs=-25.0, quality=2, gain=0.7, when="firing",
        where="positional: a kiln while firing (A4)",
        purpose="A wood-fired kiln roaring through its flue, the firebox crackling."),
    "sfx/athens/aulos.wav": dict(kind="sfx", render=aulos, lufs=-21.0, gain=1.0,
                                 purpose="An aulos phrase over its drone pipe (sacrifice, A10, A1)."),
    "sfx/athens/lyre.wav": dict(kind="sfx", render=lyre, lufs=-22.0, gain=1.0,
                                purpose="A lyre swept with the plectrum and a few notes (symposium, school)."),
    "sfx/athens/owl.wav": dict(kind="sfx", render=owl, lufs=-25.0, gain=0.9,
                               purpose="Athena's little owl calling on the rock at night (H3)."),
    "sfx/athens/trireme.wav": dict(kind="sfx", render=trireme, lufs=-24.0, gain=0.9,
                                   purpose="A trireme's timbers creaking, an oar knocking (ships)."),
    "sfx/athens/oars.wav": dict(kind="sfx", render=oars, lufs=-23.0, gain=0.9,
                                purpose="A bank of oars in time with the piper's call (S4)."),
    "sfx/athens/arrive.wav": dict(kind="sfx", render=arrive, lufs=-20.0, gain=1.0,
                                  purpose="Arrival motif (fast travel, era caption): kithara E A B E."),
}
