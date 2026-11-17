"""Pārsa (Persepolis, spring c. 470 BC): music, ambience beds and effects.

Music: a small court ensemble of the kind the Elamite reliefs show (angular harp, double
pipe, frame drum) plus a long-necked lute and a clapper, in a diatonic mode on D built from
tetrachords (D E F G | A B C D, the Mesopotamian heptatonic tunings), with drones and dyads
in fourths and fifths. No quarter tones, no augmented seconds, no later Persian instruments.
Day and night share the D mode and the four-note motif D E F A."""

import numpy as np

import ambience
import ancient
import score
import sounds as sd
from dsp import SR, bandpass, lowpass, midi_hz, pan, place, secs, shaped_noise, times

# --- music -----------------------------------------------------------------------------

# Harp: the central voice. A (1-8) the motif and its answer; B (9-16) accompanies the pipes;
# C (17-24) leads a lilting triplet song on G; B' (25-32) answers the pipes higher; D (33-40)
# closes with the motif turned downward, and the loop opens it upward again.
DAY_HARP = (
    "D4/0.5 E4/0.5 F4/0.5 A4/2.5 | D3+A3/1 r/0.5 A4/0.5 G4/0.5 F4/0.5 E4/1 "
    "| D4/0.5 E4/0.5 F4/0.5 A4/1 C5/0.5 B4/0.5 A4/0.5 | G4/1.5 F4/0.5 E4/1 D4/1 "
    "| D3+A3/1 A4/0.5 D5/0.5 C5/1 A4/1 | G3+D4/1 G4/0.5 B4/0.5 A4/1 G4/1 "
    "| F3+C4/1 F4/0.5 A4/0.5 G4/0.5 F4/0.5 E4/1 | A3+E4/2 D4+A4/2 "
    # B
    "| D3+A3/2 F4/0.5 E4/0.5 D4/1 | A3+E4/2 r/1 G4/0.5 A4/0.5 "
    "| F3+C4/2 A4/0.5 C5/0.5 D5/1 | G3+D4/2 C5/0.5 A4/0.5 G4/1 "
    "| D3+A3/2 r/2 | G3+D4/2 r/1 A4/1 "
    "| F3+C4/2 C5/0.5 D5/0.5 E5/1 | A3+E4/1 r/0.5 E5/0.5 D5/0.5 C5/0.5 A4/1 "
    # C: triplet lilt on G
    "| G4/2_3 A4/1_3 B4/1 D5/2_3 C5/1_3 B4/1 | A4/2_3 B4/1_3 C5/2_3 B4/1_3 A4/2 "
    "| G4/2_3 A4/1_3 B4/2_3 D5/1_3 E5/1 D5/1 | C5/2_3 B4/1_3 A4/2_3 B4/1_3 G4/2 "
    "| D5/2_3 E5/1_3 F5/1 E5/2_3 D5/1_3 C5/1 | B4/2_3 C5/1_3 D5/2_3 C5/1_3 B4/2_3 A4/1_3 G4/1 "
    "| A4/2_3 B4/1_3 C5/1 B4/2_3 A4/1_3 G4/2_3 F4/1_3 | G4/2_3 F4/1_3 E4/1 D4+A4/2 "
    # B'
    "| D4+A4/2 D5/0.5 E5/0.5 F5/1 | C4+G4/2 r/1 E5/0.5 F5/0.5 "
    "| F3+C4/2 F5/0.5 E5/0.5 D5/1 | G3+D4/2 D5/0.5 C5/0.5 B4/1 "
    "| D4+A4/2 r/1 A4/1 | C4+G4/2 G4/0.5 A4/0.5 C5/1 "
    "| A3+E4/2 F4/0.5 E4/0.5 C4/1 | D3+A3+D4/2 r/2 "
    # D: coda
    "| A4/0.5 F4/0.5 E4/0.5 D4/2.5 | r/1 G4/0.5 F4/0.5 E4/1 D4/1 "
    "| A3+E4/2 r/2 | D4/0.5 E4/0.5 F4/0.5 A4/1 C5/0.5 B4/0.5 G4/0.5 "
    "| r/4 | r/2 D4+A4/2 | D3+A3/2 r/2 | r/2 A3/1 C4/1"
)

LUTE_D = "D3/1 D3/0.5 A3/0.5 D3/1 r/1"
LUTE_D2 = "D3/1 D3/0.5 A3/0.5 D3/0.5 A3/0.5 D3/1"
DAY_LUTE = " | ".join(
    ["r/4", "r/4", LUTE_D, LUTE_D, LUTE_D, "G3/1 G3/0.5 D3/0.5 G3/1 r/1",
     "F3/1 F3/0.5 C3/0.5 F3/1 r/1", "A3/1 A3/0.5 E3/0.5 D3/2"]
    + [LUTE_D2, "A3/1 A3/0.5 E3/0.5 A3/1 r/1", "F3/1 F3/0.5 C3/0.5 F3/1 r/1",
       "G3/1 G3/0.5 D3/0.5 G3/1 r/1", LUTE_D2, "G3/1 G3/0.5 D3/0.5 G3/1 r/1",
       "F3/1 F3/0.5 C3/0.5 F3/1 r/1", "A3/1 A3/0.5 E3/0.5 A3/1 r/1"]
    + ["G3/2_3 G3/1_3 D3/2_3 G3/1_3 G3/2_3 G3/1_3 D3/1"] * 7
    + ["D3/2_3 D3/1_3 A3/2_3 D3/1_3 D3/2"]
    + [LUTE_D2, "C3/1 C3/0.5 G3/0.5 C3/1 r/1", "F3/1 F3/0.5 C3/0.5 F3/1 r/1",
       "G3/1 G3/0.5 D3/0.5 G3/1 r/1", LUTE_D2, "C3/1 C3/0.5 G3/0.5 C3/1 r/1",
       "A3/1 A3/0.5 E3/0.5 A3/1 r/1", "D3/2 r/2"]
    + ["D3/2 A3/2", "D3/2 r/2", "A3/2 r/2", "D3/2 r/2", "D3/4", "r/4", "D3/4", "A2/2 r/2"])

# Double pipe: the melody pipe enters at B with a calm stepwise tune; its partner holds the
# drone. Grace notes are quick upper-neighbour flicks, as pipers still ornament today.
DAY_PIPE = " | ".join(
    ["r/4"] * 8
    + ["B4'A4/2 G4/1 A4/1", "F4/1 E4/0.5 F4/0.5 G4/2", "A4/1.5 C5/0.5 B4/1= A4/1=",
       "G4/1 F4/1 E4/2", "D4/1 F4/1 E4/1 G4/1", "F4/1.5 E4/0.5= D4/1 E4/1",
       "F4/1 G4/1 A4/1 C5/0.5 B4/0.5=", "B4'A4/4"]
    + ["r/4", "r/2 D5/2_3 C5/1_3= B4/1", "r/4", "r/2 E5/2_3 D5/1_3= B4/1", "r/4", "r/3 D5/1",
       "r/4", "r/2 A4/2"]
    + ["B4'A4/2 C5/1 B4/0.5 A4/0.5=", "G4/1 F4/0.5 G4/0.5 A4/2", "C5/1.5 D5/0.5= C5/1 A4/1",
       "B4/1 A4/1= G4/2", "F4/1 A4/1 G4/1 F4/1", "E4/1.5 F4/0.5= G4/1 E4/1",
       "F4/1 E4/1 D4/1 E4/0.5 F4/0.5=", "E4'D4/4"]
    + ["r/4"] * 4 + ["A4/2 G4/1 F4/1", "E4/2 D4/2", "r/4", "r/4"])

DAY_DRONE = " | ".join(["r/4"] * 8 + ["D4/4="] * 8 + ["r/4"] * 8 + ["D4/4="] * 8
                       + ["D4/4="] * 2 + ["A3/4="] * 2 + ["D4/4="] * 2 + ["A3/8"])

WALK = "D/1 k/1? D/1 T/0.5 k/0.5?"
DAY_DRUM = " | ".join(
    ["r/4"] * 4 + ["D/1? r/1 D/1? T/0.5? k/0.5?"] * 3 + ["D/1 r/1 D/2"]
    + [WALK] * 7 + ["D/1 k/0.5? k/0.5? D/1 T/1"]
    + ["D/2_3 k/1_3? k/1? D/2_3 k/1_3? T/1"] * 7 + ["D/2_3 k/1_3? k/1? D/2"]
    + ["D/1 k/0.5? k/0.5? D/1 T/0.5 k/0.5?"] * 7 + ["D/2 r/2"]
    + ["D/1? r/3", "r/4", "D/1? r/3"] + ["r/4"] * 5)

DAY_CLAPPER = " | ".join(["r/4"] * 16 + ["r/2_3 C/1_3? " * 4] * 8 + ["r/4"] * 16)

DAY = {
    "bpm": 80, "meter": [4], "phrase": 16, "tail": 6.0,
    "reverb": (3.0, 2.0, 1.2, 0.02),  # stone hall with painted walls: about 1.8 s
    "parts": {
        "harp": {"voice": "harp", "notes": DAY_HARP, "gain": 1.0, "pan": -0.1, "spread": 0.5,
                 "send": 0.35, "ring": 4.5, "vel": 0.8},
        "lute": {"voice": "lute", "notes": DAY_LUTE, "gain": 0.9, "pan": 0.35, "send": 0.25,
                 "ring": 2.0, "vel": 0.7},
        "pipe": {"voice": "pipe", "notes": DAY_PIPE, "gain": 0.2, "pan": 0.15, "send": 0.4,
                 "vel": 0.8},
        "drone": {"voice": "pipe", "notes": DAY_DRONE, "gain": 0.07, "pan": 0.2, "send": 0.4,
                  "vel": 0.7, "legato": True},
        "drum": {"voice": "drum", "notes": DAY_DRUM, "gain": 0.4, "pan": -0.3, "send": 0.3,
                 "tune": 88.0, "vel": 0.75},
        "clapper": {"voice": "drum", "notes": DAY_CLAPPER, "gain": 0.55, "pan": 0.45,
                    "send": 0.3, "tune": 1250.0, "vel": 0.7},
    },
}

# Night: the court asleep. Solo harp in free time, a hummed drone of women's voices that
# breathes in and out, and a few distant pipe answers.
NIGHT_HARP = (
    "D4/1 E4/1 F4/1 A4/1 | A4/4 | D3+A3/2 C5/1 A4/1 | G4/2 F4/1 E4/1 "
    "| D4/4 | r/2 F4/1 G4/1 | A4/2 D5/1 C5/1 | A4/4 "
    "| D5/1.5 C5/0.5 A4/1 G4/1 | F4/2 E4/1 F4/1 | G4/1 A4/1 C5/2 | A4/4 "
    "| D4/1 F4/1 E4/1 G4/1 | F4/2 E4/1 D4/1 | C4/1 D4/1 E4/1 F4/1 | D4/4 "
    "| G3+D4/2 B4/1 D5/1 | C5/2 B4/1 A4/1 | G4/4 | r/2 B4/1 C5/1 "
    "| D5/2 E5/1 D5/1 | B4/4 | C5/1 B4/1 A4/1 G4/1 | A4/4 "
    "| A4/1 F4/1 E4/1 D4/1 | D3+A3/4 | r/2 F4/1 E4/1 | D4/4 | r/1 A3/1 C4/1 E4/1 | A3+E4/4"
)

NIGHT_HUM = ("r/8 | D3+A3/12 | D3+A3/12 | D3/12 | r/4 | D3+A3/16 | G3+D4/16 | r/4 | G3/12 | A3/4 "
             "| D3+A3/12 | A3/8")

NIGHT_PIPE = " | ".join(
    ["r/4"] * 11 + ["r/1 C5/1 B4/1= A4/1"] + ["r/4"] * 3 + ["r/1 A4/1 G4/1= F4/1", "E4/2 D4/2"]
    + ["r/4"] * 4 + ["r/1 D5/1 C5/1= B4/1", "A4/4=", "G4/2 A4/2"] + ["r/4"] * 6)

NIGHT = {
    "bpm": 60, "meter": [4], "phrase": 8, "rubato": (0.22, 8), "tail": 10.0,
    "reverb": (5.0, 3.2, 1.8, 0.03),  # the open terrace under the stars
    "parts": {
        "harp": {"voice": "harp", "notes": NIGHT_HARP, "gain": 1.0, "pan": 0.0, "spread": 0.5,
                 "send": 0.7, "ring": 7.0, "vel": 0.72},
        "hum": {"voice": "hum", "notes": NIGHT_HUM, "gain": 0.2, "pan": -0.2, "send": 0.7,
                "voices": 3, "vel": 0.7},
        "pipe": {"voice": "pipe", "notes": NIGHT_PIPE, "gain": 0.06, "pan": 0.4, "send": 0.9,
                 "vel": 0.65},
    },
}


def day(rng):
    return score.render(DAY, rng)


def night(rng):
    return score.render(NIGHT, rng)


# --- ambience --------------------------------------------------------------------------


def far_masons(bed, bouts, dist=(0.8, 0.95), level=0.5):
    """Masons out of sight: bouts of chisel blows, each mason at a steady working pace."""
    for _ in range(bouts):
        t = bed.rng.uniform(0, bed.n / SR)
        pace = bed.rng.uniform(0.38, 0.7)
        pos, d = bed.rng.uniform(-0.8, 0.8), bed.rng.uniform(*dist)
        for k in range(int(bed.rng.integers(4, 12))):
            bed.add(sd.chisel(bed.rng), t + k * pace + bed.rng.normal(0, 0.02), pos, d,
                    level * bed.rng.uniform(0.6, 1.0))


def plain_day(rng, layers=None, length=48.0):
    """The terrace and plain by day: thin dry highland wind, swallows round the columns, a
    far-off chisel ring, a horse's snort and bells now and then, the faintest voices."""
    n = secs(length)
    life = sd.Bed(length, rng)
    life.scatter(sd.swallow, 16, dist=(0.3, 0.8), level=(0.3, 0.7))
    far_masons(life, 5, level=0.35)
    life.scatter(sd.snort, 2, dist=(0.6, 0.8), level=(0.4, 0.6))
    life.scatter(lambda r: sd.bells_walking(r, 3.0, 1450, 1.7), 2, dist=(0.7, 0.9),
                 level=(0.15, 0.25))
    life.add(sd.hoopoe(rng), rng.uniform(0, length), 0.5, 0.6, 0.25)
    return sd.mix({
        "wind": 0.16 * sd.wind(n, rng, 150, 2200, 0.07, 0.6, whistle=0.02),
        "life": 1.6 * life.finish((2.5, 1.5, 0.7, 0.03), 0.4),
        "voices": 0.4 * sd.crowd(length, rng, 5, ceiling=1200),
    }, layers)


def plain_night(rng, layers=None, length=48.0):
    """Night on the terrace: crickets, a scops owl's patient call, wind over stone, a
    guard's slow steps passing, a fire altar crackling somewhere."""
    n = secs(length)
    life = sd.Bed(length, rng)
    sd.crickets(life, 5, level=0.3)
    t = rng.uniform(0, 10)
    for _ in range(2):  # the owl calls in runs, then falls silent for a while
        for k in range(int(rng.integers(6, 10))):
            life.add(sd.scops_owl(rng), t + k * 2.7 + rng.normal(0, 0.05), 0.6, 0.75, 0.3)
        t += rng.uniform(22, 26)
    walk = rng.uniform(0, length)
    for k in range(14):  # a guard crosses the terrace
        life.add(sd.step(rng, "stone"), walk + k * 0.62, -0.7 + 0.1 * k, 0.75, 0.25)
    fire = sd.fire(length, rng, 0.6)
    return sd.mix({
        "wind": 0.1 * sd.wind(n, rng, 100, 1400, 0.05, 0.6, whistle=0.03),
        "life": life.finish((3.0, 2.0, 0.8, 0.03), 0.5),
        "fire": 0.12 * pan(fire, -0.5),
    }, layers)


def channels(rng, layers=None, length=40.0):
    """Close water running in narrow stone channels through the garden, with frogs at
    the edges."""
    n = secs(length)
    water = sd.Bed(length, rng, tail=3.0)
    sd.trickle(water, 140, 450, 2600, dist=(0.05, 0.4), level=0.4)
    frogs = sd.Bed(length, rng)
    t = rng.uniform(0, 8)
    for _ in range(4):
        frogs.add(lowpass(ambience.frog(rng), 2500), t, rng.uniform(-0.8, 0.8), 0.5, 0.35)
        t += rng.uniform(8, 12)
    flow = sd.loop_noise(n, rng, 300, 3500, 0.4) * sd.swell(n, rng, 0.3, 0.15)[:, None]
    return sd.mix({
        "flow": 0.05 * flow,
        "bubbles": water.finish((0.8, 0.6, 0.3, 0.01), 0.25),
        "frogs": frogs.finish((1.5, 1.0, 0.5, 0.02), 0.4),
    }, layers)


def site(rng, layers=None, length=48.0):
    """The Hall of a Hundred Columns going up: chisels at several paces, mallets driving
    wedges, ropes creaking on the shear-legs, an ox lowing, workers calling (no words)."""
    n = secs(length)
    work = sd.Bed(length, rng)
    far_masons(work, 14, dist=(0.25, 0.75), level=0.6)
    for _ in range(4):
        t, pos = rng.uniform(0, length), rng.uniform(-0.7, 0.7)
        for k in range(int(rng.integers(3, 6))):
            work.add(sd.wedge(rng), t + k * rng.uniform(1.0, 1.3), pos, 0.5, 0.7)
    for _ in range(5):
        work.add(sd.creak_short(rng, rng.uniform(0.5, 1.1), rng.uniform(60, 110)),
                 rng.uniform(0, length), rng.uniform(-0.5, 0.5), 0.5, 0.25)
    work.scatter(sd.ox, 2, dist=(0.6, 0.8), level=(0.35, 0.45))
    calls = sd.crowd(length, rng, 3, f0=(110, 170), ceiling=2000, calling=2)
    return sd.mix({
        "work": work.finish((1.8, 1.2, 0.6, 0.02), 0.35),
        "calls": 0.3 * calls,
        "wind": 0.03 * sd.wind(n, rng, 150, 1800, 0.07, 0.5),
    }, layers)


def stone_drop(rng):
    """A raindrop on paving: a tiny bright tick."""
    m = secs(0.02)
    return bandpass(rng.standard_normal(m), 1500, 6000) * np.exp(-times(m) / 0.0025)


def rain(rng, layers=None, length=40.0):
    """A spring shower on stone and young leaves, with drains gurgling at the outfalls."""
    n = secs(length)
    wash = shaped_noise(n, rng, lambda f: f**-0.4 / (1 + (f / 4000) ** 3) / (1 + (150 / f) ** 2), 2)
    wash *= sd.swell(n, rng, 0.06, 0.15)[:, None]
    drops = sd.Bed(length, rng, tail=1.0)
    for _ in range(int(40 * length)):
        drops.add(stone_drop(rng), rng.uniform(0, length), rng.uniform(-0.9, 0.9),
                  rng.uniform(0.1, 0.8), rng.uniform(0.1, 0.6))
    drain = sd.Bed(length, rng, tail=2.0)
    for spot in (-0.6, 0.45):
        sd.trickle(drain, 25, 180, 700, dist=(0.2, 0.4), spread=0.1, level=0.5)
        for _ in range(int(length / 1.3)):  # a spout dripping into a puddle
            drain.add(sd.bubble(rng, rng.uniform(600, 900)), rng.uniform(0, length), spot, 0.3, 0.3)
    return sd.mix({
        "wash": 0.13 * wash,
        "drops": 3.0 * drops.finish((1.0, 0.8, 0.4, 0.01), 0.3),
        "drain": drain.finish((1.2, 0.8, 0.4, 0.01), 0.3),
    }, layers)


# A delegation climbing the stair behind its usher: drum walking, pipes, clapper; a positional
# loop of exactly 8 bars at 80 bpm (24 s).
PROCESSION = {
    "bpm": 80, "meter": [4], "phrase": 16, "tail": 4.0,
    "reverb": (2.0, 1.4, 0.8, 0.02),
    "parts": {
        "pipe": {"voice": "pipe", "gain": 0.5, "pan": 0.0, "send": 0.3, "vel": 0.8,
                 "notes": "A4/2 G4/1 A4/1 | F4/1 G4/1 A4/2 | C5/1 B4/1 A4/1 G4/1 | A4/4 "
                          "| D5/2 C5/1 A4/1 | B4/1 A4/1 G4/2 | F4/1 E4/1 F4/1 G4/1 | E4'D4/4"},
        "drone": {"voice": "pipe", "gain": 0.15, "pan": 0.1, "send": 0.3, "vel": 0.7,
                  "legato": True, "notes": " | ".join(["D4/4="] * 8)},
        "drum": {"voice": "drum", "gain": 0.8, "pan": -0.1, "send": 0.25, "tune": 88.0,
                 "vel": 0.8, "notes": " | ".join(["D/1 k/0.5? k/0.5? D/1 T/1"] * 7 + ["D/1 k/1? D/2"])},
        "clapper": {"voice": "drum", "gain": 0.4, "pan": 0.2, "send": 0.25, "tune": 1250.0,
                    "vel": 0.7, "notes": " | ".join(["r/1 C/1? r/1 C/1?"] * 8)},
    },
}


def procession(rng):
    return score.render(PROCESSION, rng)


# --- effects ---------------------------------------------------------------------------


def horn(rng):
    """The guard's long natural horn at the change of guard, from the far end of the
    terrace: open partials only (D3, A3, D4), swelling and dying away."""
    out = np.zeros(secs(6.0))
    for at, m, dur, vel in ((0.0, 57, 0.6, 0.7), (0.65, 62, 1.5, 0.9), (2.3, 57, 0.4, 0.6),
                            (2.75, 62, 1.9, 0.85)):
        place(out, ancient.horn(float(midi_hz(m)), dur, vel, rng, bright=0.7), secs(at))
    return sd.finish_sfx(lowpass(out, 2400, 2), rng, wet=0.8, size=2.0, fade_out=0.3)


def camel(rng):
    return sd.finish_sfx(sd.camel(rng), rng, 0.15)


def horse_bells(rng):
    return sd.finish_sfx(sd.bells_walking(rng, 2.2, 1450, 1.8), rng, 0.2, fade_out=0.3)


def hoopoe(rng):
    x = np.concatenate([sd.hoopoe(rng), np.zeros(secs(0.5)), sd.hoopoe(rng)])
    return sd.finish_sfx(x, rng, 0.25)


def stork(rng):
    """A white stork clattering its bill on the nest: a wooden rattle that speeds up and
    slows down."""
    out = np.zeros(secs(2.4))
    t = 0.0
    while t < 2.0:
        rate = 9 + 12 * np.sin(np.pi * t / 2.0)
        place(out, sd.modes(secs(0.03), [1700, 2900], [1.0, 0.4], [0.006, 0.004], rng)
              * (0.5 + 0.5 * np.sin(np.pi * t / 2.0)), secs(t))
        t += 1 / rate
    return sd.finish_sfx(lowpass(out, 5000), rng, 0.2)


def chant(rng):
    """The magus at the fire altar at dawn: two low voices intoning on one tone with small
    turns, hummed (Herodotus: chanted without pipes). Wordless."""
    tune = ((0.0, 0.9, 50), (0.9, 0.5, 52), (1.4, 0.9, 50), (2.3, 0.5, 48), (2.8, 1.4, 50))
    x = sd.song([(s, d, float(midi_hz(m))) for s, d, m in tune], rng, voices=2, vowel="o")
    return sd.finish_sfx(lowpass(x, 2500), rng, 0.4, 1.2, fade_out=0.3)


AUDIENCE = {  # P1: the soft drum and harp phrase as a delegation is presented
    "bpm": 80, "meter": [4], "tail": 3.0, "reverb": (2.5, 1.8, 1.0, 0.02),
    "parts": {
        "harp": {"voice": "harp", "gain": 1.0, "pan": 0.0, "send": 0.35, "ring": 3.0, "vel": 0.8,
                 "notes": "r/0.5 D4/0.5 E4/0.5 F4/0.5 A4/2 | D3+A3+D4/4"},
        "drum": {"voice": "drum", "gain": 0.6, "pan": -0.2, "send": 0.3, "tune": 88.0, "vel": 0.7,
                 "notes": "D/1 k/1? T/1 k/1? | D/4"},
    },
}

ARRIVE = {  # fast travel / era caption: the world-map motif D E F A on the harp over a drone
    "bpm": 80, "meter": [4], "tail": 3.0, "reverb": (3.0, 2.0, 1.2, 0.02),
    "parts": {
        "harp": {"voice": "harp", "gain": 1.0, "pan": 0.0, "spread": 0.4, "send": 0.4,
                 "ring": 3.5, "vel": 0.8, "notes": "D4/0.5 E4/0.5 F4/0.5 A4/2.5 | D3+A3+D4/4"},
        "drone": {"voice": "pipe", "gain": 0.12, "pan": 0.2, "send": 0.4, "vel": 0.7,
                  "notes": "D4/6 r/2"},
        "drum": {"voice": "drum", "gain": 0.4, "pan": -0.2, "send": 0.3, "tune": 88.0, "vel": 0.6,
                 "notes": "r/4 | D/4"},
    },
}


def phrase(piece, rng, keep):
    """Render a short score as a one-shot: unwrap it (no loop), keep `keep` seconds."""
    x = score.render(dict(piece, tail=0.0, reverb=piece["reverb"]), rng, one_shot=keep)
    return sd.finish_sfx(x.mean(axis=1) * np.sqrt(2), rng, 0.0, fade_out=0.6)


def audience(rng):
    return phrase(AUDIENCE, rng, 4.5)


def arrive(rng):
    return phrase(ARRIVE, rng, 5.0)


# --- files -----------------------------------------------------------------------------

# name -> how to render it, its level, and what the engine and region file need to know.
# lufs: integrated for loops, loudest 100 ms for effects. gain: suggested playback gain.
FILES = {
    "music/parsa/day.ogg": dict(
        kind="music", render=day, piece=DAY, lufs=-18.0, quality=4, gain=1.0, when="day",
        purpose="Day piece: angular harp, long-necked lute, double pipe, frame drum and "
                "clapper in a D mode; harp motif, pipe song, lilting triplet middle on G."),
    "music/parsa/night.ogg": dict(
        kind="music", render=night, piece=NIGHT, lufs=-18.0, quality=4, gain=1.0, when="night",
        purpose="Night piece: solo harp in free time, hummed drone of women's voices, far "
                "pipe answers; same D mode and motif as the day."),
    "amb/parsa/plain_day.ogg": dict(
        kind="bed", render=plain_day, lufs=-22.0, quality=2, gain=1.0, when="day",
        where="everywhere in the region",
        purpose="Thin dry wind, swallows, far chisels, a horse's snort and bells, faint voices."),
    "amb/parsa/plain_night.ogg": dict(
        kind="bed", render=plain_night, lufs=-23.0, quality=2, gain=1.0, when="night",
        where="everywhere in the region",
        purpose="Crickets, a scops owl's runs, wind over stone, a guard's steps, a fire altar."),
    "amb/parsa/channels.ogg": dict(
        kind="bed", render=channels, lufs=-22.0, quality=2, gain=0.7, when="always",
        where="zone: the paradise garden and the canal",
        purpose="Close water in narrow stone channels, frogs at the edges."),
    "amb/parsa/site.ogg": dict(
        kind="bed", render=site, lufs=-22.0, quality=2, gain=0.8, when="day",
        where="zone: hall_100 building site and the quarry",
        purpose="Chisels, mallets on wedges, rope creak, an ox, workers calling without words."),
    "amb/parsa/rain.ogg": dict(
        kind="bed", render=rain, lufs=-21.0, quality=2, gain=1.0, when="rain",
        where="everywhere while it rains (replaces nothing: mix over the day/night bed)",
        purpose="Spring shower on paving and leaves, drains gurgling at the outfalls."),
    "amb/parsa/procession.ogg": dict(
        kind="loop", render=procession, piece=PROCESSION, lufs=-23.0, quality=2, gain=0.8,
        when="event", where="positional: follows the delegation (P1) up the stair",
        purpose="A delegation's drum, double pipe and clapper walking past (8 bars, 80 bpm)."),
    "sfx/parsa/horn.wav": dict(kind="sfx", render=horn, lufs=-23.0, gain=1.0,
                               purpose="Long natural horn call at the change of guard (P8)."),
    "sfx/parsa/camel.wav": dict(kind="sfx", render=camel, lufs=-23.0, gain=0.9,
                                purpose="A camel's groan (caravans, L7)."),
    "sfx/parsa/horse_bells.wav": dict(kind="sfx", render=horse_bells, lufs=-25.0, gain=0.9,
                                      purpose="Bronze bells on a walking horse (couriers, grooms)."),
    "sfx/parsa/hoopoe.wav": dict(kind="sfx", render=hoopoe, lufs=-26.0, gain=0.8,
                                 purpose="Hoopoe's 'hoo-poo-poo' in the garden."),
    "sfx/parsa/stork.wav": dict(kind="sfx", render=stork, lufs=-25.0, gain=0.8,
                                purpose="White stork clattering its bill on a nest (P12)."),
    "sfx/parsa/chant.wav": dict(kind="sfx", render=chant, lufs=-25.0, gain=0.9,
                                purpose="The magus intoning at the fire altar at dawn (P2), wordless."),
    "sfx/parsa/audience.wav": dict(kind="sfx", render=audience, lufs=-21.0, gain=1.0,
                                   purpose="Soft harp and drum phrase as a delegation is presented (P1)."),
    "sfx/parsa/arrive.wav": dict(kind="sfx", render=arrive, lufs=-20.0, gain=1.0,
                                 purpose="Arrival motif (fast travel, era caption): harp D E F A."),
}
