"""Rome (the Parilia, AD 126): music, ambience beds and effects.

Music: a cithara theme in a Lydian-type diatonic mode on F (F G A B C D E, the tonal world
the Hadrianic hymns are usually transcribed in), doubled heterophonically by a soft tibia
over low drones; a festival middle with sustained hydraulis intervals (fifths and octaves
only) and a distant cornu sounding its open partials. Hymn-like long-short rhythms in
alternating bars of 3 and 4 at 84 bpm. Night: a lyre with long notes, a few tibia sighs,
a faint hydraulis pedal on F and C. The overview motif is F A C on the cithara, answered
by F on the cornu."""

import numpy as np

import ancient
import score
import sounds as sd
from dsp import SR, lowpass, midi_hz, pan, place, secs

# --- music -----------------------------------------------------------------------------

THEME = ["F4/1 A4/1 C5/1", "D5/2 C5/1 A4/1", "B4/2 A4/1", "G4/1.5 A4/0.5 F4/2",
         "A4/2 C5/1", "E5/2 D5/1 C5/1", "D5/2 B4/1", "C5/3 r/1",
         "A4/2 B4/1", "C5/1.5 B4/0.5 A4/1 G4/1", "A4/2 G4/1", "F4/4"]
THEME_B = ["F4/1 A4/1 C5/1", "F5/2 E5/1 D5/1", "C5/2 A4/1", "B4/1.5 C5/0.5 G4/2",
           "A4/1 B4/1 C5/1", "D5/1.5 E5/0.5 C5/2", "D5/2 B4/1", "C5/2 A4/2",
           "G4/2 A4/1", "B4/1.5 A4/0.5 G4/1 E4/1", "G4/2 A4/1", "F4/4"]
TIBIA_B = ["F4/2 C5/1", "D5/2 C5/2", "C5/2 A4/1", "B4/2 G4/2",
           "A4/2 C5/1", "D5/2 C5/2", "D5/2 B4/1", "C5/2 A4/2",
           "G4/3", "B4/2 G4/2", "G4/2 A4/1", "F4/4"]


def arp(root, third, fifth, top):
    """Cithara figures over the organ: a 3-beat and a 4-beat broken chord."""
    return [f"{root}/0.5 {third}/0.5 {fifth}/0.5 {third}/0.5 {root}/0.5 {fifth}/0.5",
            f"{root}/0.5 {third}/0.5 {fifth}/0.5 {top}/0.5 {fifth}/0.5 {third}/0.5 "
            f"{root}/0.5 {fifth}/0.5"]


FEAST = (arp("F4", "A4", "C5", "F5") + arp("G4", "B4", "D5", "G5") + arp("A4", "C5", "E5", "A5")
         + arp("F4", "A4", "C5", "F5") + arp("C4", "E4", "G4", "C5") + ["F4/1 A4/1 C5/1", "F4/4"])
RETURN = ["F4/1 A4/1 C5/1", "D5/2 C5/1 A4/1", "B4/2 A4/1", "G4/1.5 A4/0.5 F4/2",
          "A4/2 C5/1", "E5/2 D5/1 C5/1", "D5/2 B4/1", "C5/4",
          "r/1 A4/1 G4/1", "A4/2 G4/1 E4/1", "F4/3", "r/2 C4/1 E4/1"]
DAY_CITHARA = " | ".join(THEME + THEME_B + FEAST + RETURN)

DRONE_PAIR = ["F3+C4/3", "F3+C4/4"]
DAY_LOW = " | ".join(DRONE_PAIR * 3 + ["C3+G3/3", "C3+G3/4"] + DRONE_PAIR * 2
                     + DRONE_PAIR * 3 + ["C3+G3/3", "C3+G3/4"] + DRONE_PAIR * 2
                     + ["r/3", "r/4"] * 6 + DRONE_PAIR * 5 + ["F3+C4/3", "r/4"])
DAY_TIBIA = " | ".join(["r/3", "r/4"] * 6 + TIBIA_B
                       + ["C5/2 A4/1", "F5/2 E5/1 D5/1", "r/3", "r/4", "C5/2 E5/1",
                          "D5/2 C5/1 B4/1", "A4/2 C5/1", "F4/4", "r/3", "r/4", "A4/2 G4/1", "F4/4"]
                       + ["r/3", "r/4"] * 3 + ["r/3", "r/1 E5/1 D5/1 C5/1", "r/3", "r/4", "F4/3",
                                                 "r/4"])
DAY_ORGAN = " | ".join(["r/3", "r/4"] * 12 + ["F3+C4+F4/7", "G3+D4+G4/7", "A3+E4+A4/7",
                                               "F3+C4+F4/7", "C4+G4+C5/7", "F3+C4+F4/7"]
                       + ["r/3", "r/4"] * 6)
DAY_CORNU = " | ".join(["r/3", "r/4"] * 13 + ["C4/1 F4/2", "C4/1 F4/3"] + ["r/3", "r/4"] * 2
                       + ["F4/1 A4/1 C5/1", "F4/4"] + ["r/3", "r/4"] * 7)
DAY_DRUM = " | ".join(["r/3", "r/4"] * 12 + ["D/1 k/1? k/1?", "D/1 k/1? T/1 k/1?"] * 6
                      + ["r/3", "r/4"] * 6)
DAY_CYMBALS = " | ".join(["r/3", "r/4"] * 12 + ["Y/3", "r/4"] * 6 + ["r/3", "r/4"] * 6)

DAY = {
    "bpm": 84, "meter": [3, 4], "phrase": 14, "tail": 7.0,
    "reverb": (3.5, 2.6, 1.6, 0.03),  # a large stone space: a portico or a basilica
    "parts": {
        "cithara": {"voice": "cithara", "notes": DAY_CITHARA, "gain": 1.0, "pan": -0.1,
                    "spread": 0.4, "send": 0.3, "ring": 4.0, "vel": 0.8},
        "low": {"voice": "cithara", "notes": DAY_LOW, "gain": 0.45, "pan": -0.25, "send": 0.3,
                "ring": 4.0, "strum": 0.04, "vel": 0.6},
        "tibia": {"voice": "tibia", "notes": DAY_TIBIA, "gain": 0.2, "pan": 0.25, "send": 0.35,
                  "vel": 0.75},
        "organ": {"voice": "organ", "notes": DAY_ORGAN, "gain": 0.09, "pan": 0.1, "send": 0.6,
                  "vel": 0.7},
        "cornu": {"voice": "horn", "notes": DAY_CORNU, "gain": 0.07, "pan": 0.5, "send": 1.0,
                  "bright": 0.8, "vel": 0.7},
        "drum": {"voice": "drum", "notes": DAY_DRUM, "gain": 0.3, "pan": -0.35, "send": 0.35,
                 "tune": 82.0, "vel": 0.7},
        "cymbals": {"voice": "drum", "notes": DAY_CYMBALS, "gain": 0.1, "pan": 0.4,
                    "send": 0.5, "tune": 1050.0, "vel": 0.6},
    },
}

NIGHT_LYRE = (
    "F4/1 A4/1 C5/2 | C5/2 D5/1 C5/1 | B4/2 A4/2 | G4/4 "
    "| A4/1 C5/1 E5/2 | D5/2 C5/1 B4/1 | C5/4 | r/4 "
    "| F4/1 G4/1 A4/2 | B4/1 A4/1 G4/2 | A4/2 F4/2 | E4/4 "
    "| F4/1 A4/1 D5/2 | C5/2 B4/1 A4/1 | G4/3 A4/1 | F4/4 "
    "| C5/1 D5/1 E5/2 | F5/2 E5/1 D5/1 | C5/4 | r/2 A4/1 B4/1 "
    "| C5/2 B4/1 A4/1 | G4/2 E4/2 | F4/4 | r/4 "
    "| A3+E4/2 F4/1 G4/1 | A4/2 G4/1 E4/1 | F4/4 | r/2 C4/1 E4/1"
)
NIGHT_ORGAN = ("F3+C4/16 | F3+C4/16 | F3+C4/16 | F3+C4/16 | C3+G3/16 | C3+G3/16 "
               "| F3+C4/16")  # re-sounded every four bars, so the lyre's rests never fall silent
NIGHT_TIBIA = " | ".join(["r/4"] * 7 + ["r/1 E5/1 D5/1= C5/1"] + ["r/4"] * 11 + ["C5/2 r/2"]
                         + ["r/4"] * 3 + ["r/1 A4/1 G4/1= F4/1"] + ["r/4"] * 4)

NIGHT = {
    "bpm": 56, "meter": [4], "phrase": 8, "rubato": (0.2, 8), "tail": 8.0,
    "reverb": (1.8, 1.1, 0.6, 0.012),  # a lamplit room off the peristyle
    "parts": {
        "lyre": {"voice": "lyra", "notes": NIGHT_LYRE, "gain": 1.0, "pan": 0.0, "spread": 0.4,
                 "send": 0.35, "ring": 6.0, "vel": 0.75},
        "organ": {"voice": "organ", "notes": NIGHT_ORGAN, "gain": 0.04, "pan": -0.4,
                  "send": 1.0, "vel": 0.6},
        "tibia": {"voice": "tibia", "notes": NIGHT_TIBIA, "gain": 0.09, "pan": 0.45,
                  "send": 0.8, "vel": 0.6},
    },
}


def day(rng):
    return score.render(DAY, rng)


def night(rng):
    return score.render(NIGHT, rng)


# --- ambience --------------------------------------------------------------------------


def fountain(length, rng, size=1.0):
    """A street fountain (lacus) as a seamless stereo loop: a spout pouring into a stone
    basin, the stream's splash fluttering fast, bubbles and droplets around it."""
    n = secs(length)
    pourn = sd.loop_noise(n, rng, 250, 5000, 0.5) * sd.swell(n, rng, 12.0, 0.35, 0.3)[:, None]
    drops = sd.Bed(length, rng, tail=2.0)
    sd.trickle(drops, 90 * size, 500, 3000, dist=(0.1, 0.4), spread=0.4, level=0.5)
    return 0.25 * pourn + drops.finish((0.8, 0.6, 0.3, 0.01), 0.3)


def builders(bed, bouts, level=0.4, dist=(0.7, 0.92)):
    """Hammers on stone and timber from building sites around the city."""
    for _ in range(bouts):
        t, pos, d = bed.rng.uniform(0, bed.n / SR), bed.rng.uniform(-0.8, 0.8), bed.rng.uniform(*dist)
        pace = bed.rng.uniform(0.4, 0.8)
        make = sd.hammer_stone if bed.rng.random() < 0.6 else sd.wedge
        for k in range(int(bed.rng.integers(3, 9))):
            bed.add(make(bed.rng), t + k * pace + bed.rng.normal(0, 0.02), pos, d,
                    level * bed.rng.uniform(0.6, 1.0))


def roar(length, rng, swells=1.0, size=1.0):
    """A huge crowd far away as a seamless loop: a broad roar that surges and ebbs."""
    n = secs(length)
    body = sd.loop_noise(n, rng, 180, 2200, 0.8) * sd.swell(n, rng, 0.12 * swells, 0.7, 0.2)[:, None]
    babble = sd.crowd(length, rng, 20, f0=(120, 300), ceiling=1600)
    return size * (0.5 * body + 0.6 * babble)


def city_day(rng, layers=None, length=48.0):
    """Rome by day, softened: a dense far murmur, a fountain at the corner, hawkers' sung
    cries (no words), hammering on building sites, a donkey, a crowd's swell from far off."""
    n = secs(length)
    life = sd.Bed(length, rng)
    builders(life, 7)
    life.add(sd.donkey(rng), rng.uniform(0, length - 4), rng.uniform(-0.7, 0.7), 0.7, 0.45)
    life.scatter(sd.swallow, 6, dist=(0.4, 0.8), level=(0.25, 0.5))
    return sd.mix({
        "murmur": 0.4 * sd.crowd(length, rng, 16, ceiling=1500),
        "hawkers": 0.25 * sd.crowd(length, rng, 0, f0=(130, 200), ceiling=2000, calling=3),
        "fountain": 0.3 * pan(fountain(length, rng).mean(axis=1), -0.5),
        "life": life.finish((2.2, 1.5, 0.7, 0.02), 0.4),
        "far": 0.06 * roar(length, rng, 0.6),
    }, layers)


def forum(rng, layers=None, length=48.0):
    """The Forum: voices close by, an orator declaiming far off under a portico (no
    words), many feet on paving, pigeons on the temple steps."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(90):
        life.add(sd.step(rng, "stone"), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 rng.uniform(0.2, 0.6), rng.uniform(0.15, 0.4))
    life.scatter(sd.pigeon, 8, dist=(0.3, 0.6), level=(0.3, 0.5))
    for _ in range(2):
        life.add(sd.wingbeats(rng, int(rng.integers(6, 12))), rng.uniform(0, length),
                 rng.uniform(-0.6, 0.6), 0.4, 0.4)
    hall = sd.Bed(length, rng)
    t = rng.uniform(0, length)
    for k in range(2):  # he speaks, pauses for effect, goes on
        hall.add(sd.babble(18.0, rng, 115, 3.2, 1800), t + 23 * k, 0.4, 0.85, 0.9)
    return sd.mix({
        "near": 0.45 * sd.crowd(length, rng, 6, f0=(110, 230), ceiling=2600, spread=0.7),
        "far": 0.25 * sd.crowd(length, rng, 10, ceiling=1500),
        "orator": 0.6 * hall.finish((3.0, 2.2, 1.2, 0.04), 0.8),
        "life": life.finish((2.0, 1.6, 0.8, 0.02), 0.4),
    }, layers)


def river(rng, layers=None, length=48.0):
    """The Tiber at the Emporium: water slapping barges' hulls, mooring ropes creaking,
    dockers calling out (no words), gulls."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(60):
        life.add(lowpass(sd.slap(rng), 900), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 rng.uniform(0.2, 0.5), rng.uniform(0.2, 0.5))
    for _ in range(12):
        life.add(sd.creak_short(rng, rng.uniform(0.6, 1.2), rng.uniform(50, 90)),
                 rng.uniform(0, length), rng.uniform(-0.6, 0.6), 0.4, 0.3)
    life.scatter(sd.gull, 6, dist=(0.4, 0.8), level=(0.3, 0.5))
    return sd.mix({
        "water": 0.14 * sd.waves(n, rng, 3.0, 0.7),
        "life": life.finish((1.6, 1.0, 0.5, 0.02), 0.3),
        "dockers": 0.2 * sd.crowd(length, rng, 3, f0=(110, 170), ceiling=2000, calling=3),
    }, layers)


def circus(rng, layers=None, length=48.0):
    """The Circus Maximus during the races, from outside: the roar of a vast crowd rising
    as the teams pass and falling between laps, hooves thundering on the sand."""
    n = secs(length)
    lap = length / 3  # three passes per loop: the roar and the hooves peak together
    t = np.arange(n) / SR
    surge = 0.45 + 0.55 * (0.5 + 0.5 * np.cos(2 * np.pi * (t - lap / 2) / lap)) ** 3
    hooves = sd.Bed(length, rng)
    for k in range(3):
        for j in range(4):  # four teams, a little apart
            run = sd.hoofbeats(rng, 6.0, "gallop", "sand")
            hooves.add(run, (k + 0.5) * lap - 3.0 + j * 0.4 + rng.uniform(0, 0.2), -0.6 + 0.4 * j,
                       0.6, 0.6)
    return sd.mix({
        "roar": roar(length, rng, 1.0) * surge[:, None],
        "hooves": 2.0 * hooves.finish((2.0, 1.5, 0.8, 0.03), 0.5),
    }, layers)


def tavern(rng):
    """A tavern song heard down the street at night: a few voices and a clapping hand."""
    tune = [(0.0, 0.5, 53), (0.5, 0.5, 57), (1.0, 1.0, 60), (2.0, 0.5, 59), (2.5, 0.5, 57),
            (3.0, 1.0, 55), (4.0, 0.5, 57), (4.5, 0.5, 55), (5.0, 1.5, 53)]
    x = sd.song([(s, d, float(midi_hz(m - 12))) for s, d, m in tune], rng, voices=4, vowel="a")
    for k in range(13):
        place(x, 0.15 * np.abs(x).max() * sd.slap(rng)[: len(x) - secs(0.5 * k)], secs(0.5 * k))
    return lowpass(x, 1400)


def city_night(rng, layers=None, length=48.0):
    """Rome at night: carts rumbling in over the basalt (banned by day), oxen, a shout, a
    dog, a tavern song far off, a fountain at the corner."""
    n = secs(length)
    carts = np.zeros((n, 2))
    for phase in (0.0, 2.5):  # two carts drifting across the street as they roll
        angle = np.pi / 4 + 0.6 * np.sin(2 * np.pi * np.arange(n) / n + phase)
        carts += sd.cart(length, rng, rng.uniform(0.8, 1.2))[:, None] * np.stack(
            [np.cos(angle), np.sin(angle)], axis=1)
    life = sd.Bed(length, rng)
    life.scatter(sd.ox, 2, dist=(0.6, 0.8), level=(0.35, 0.45))
    life.add(sd.dog(rng, 3), rng.uniform(0, length), -0.7, 0.85, 0.4)
    life.add(sd.babble(1.5, rng, 140, 4, 2000, calling=True), rng.uniform(0, length), 0.6, 0.8, 0.5)
    life.add(tavern(rng), rng.uniform(0, length), 0.5, 0.9, 0.6)
    sd.crickets(life, 3, level=0.15)
    return sd.mix({
        "carts": 0.06 * carts,
        "life": 1.5 * life.finish((2.2, 1.5, 0.7, 0.03), 0.45),
        "fountain": 0.15 * pan(fountain(length, rng).mean(axis=1), 0.4),
    }, layers)


def lacus(rng):
    return fountain(12.0, rng)


def baths(rng):
    """Inside a bath hall: splashes, a plunge, a bucket poured, voices, all ringing in the
    vault."""
    length = 16.0
    hall = sd.Bed(length, rng)
    for _ in range(14):
        hall.add(sd.splash_small(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.8))
    hall.add(sd.pour(rng, 1.4), rng.uniform(0, length), -0.4, 0.4, 0.6)
    voices = sd.crowd(length, rng, 6, f0=(110, 240), ceiling=2200)
    return (hall.finish((4.0, 3.0, 1.8, 0.04), 0.9)
            + sd.Bed.wet(voices, rng, (4.0, 3.0, 1.8, 0.04), 0.35))


def treadwheel(rng):
    """A treadwheel crane at work: men stepping in the wheel, its axle groaning each turn,
    the pawl clacking, the rope taking the strain."""
    length = 12.0
    rig = sd.Bed(length, rng)
    for k in range(int(length / 0.55)):
        rig.add(sd.step(rng, "wood"), k * 0.55 + rng.normal(0, 0.02), -0.2, 0.3, 0.5)
    for k in range(4):
        rig.add(sd.creak_short(rng, 1.2, rng.uniform(40, 60)), k * 3.0 + 0.3, 0.1, 0.3, 0.6)
    for k in range(int(length / 0.75)):
        rig.add(sd.modes(secs(0.06), [900, 2100], [1.0, 0.3], [0.012, 0.006], rng), k * 0.75 + 0.2,
                0.3, 0.3, 0.35)
    return rig.finish((1.2, 0.9, 0.4, 0.01), 0.3)


# The pompa passing (procession to the Circus or a sacrifice): tibia over a drone, cymbals
# and the frame drum of the cults; four pairs of 3 and 4 beats at 84 bpm (20 s), loopable.
PROCESSION = {
    "bpm": 84, "meter": [3, 4], "phrase": 14, "tail": 4.0, "offset": 0.5,
    "reverb": (2.0, 1.4, 0.8, 0.02),
    "parts": {
        "tibia": {"voice": "tibia", "gain": 0.5, "pan": 0.1, "send": 0.3, "vel": 0.85,
                  "notes": " | ".join(TIBIA_B[:8])},
        "drone": {"voice": "tibia", "gain": 0.15, "pan": 0.15, "send": 0.3, "vel": 0.7,
                  "legato": True, "notes": " | ".join(["F4/3=", "F4/4="] * 4)},
        "drum": {"voice": "drum", "gain": 0.6, "pan": -0.2, "send": 0.25, "tune": 82.0, "vel": 0.8,
                 "notes": " | ".join(["D/1 k/1? k/1?", "D/1 k/1? T/1 k/1?"] * 4)},
        "cymbals": {"voice": "drum", "gain": 0.2, "pan": 0.35, "send": 0.4, "tune": 1050.0,
                    "vel": 0.6, "notes": " | ".join(["Y/3", "r/2 Y/2?"] * 4)},
    },
}


def procession(rng):
    return score.render(PROCESSION, rng)


# --- effects ---------------------------------------------------------------------------

TIBIA = {  # the piper at a sacrifice: the tibicen plays so no ill-omened sound is heard
    "bpm": 84, "meter": [3, 4], "tail": 2.0, "reverb": (2.2, 1.6, 0.9, 0.02),
    "parts": {"tibia": {"voice": "tibia", "gain": 1.0, "pan": 0.0, "send": 0.3, "vel": 0.85,
                        "notes": "F4/1 A4/1 C5/1 | D5/2 C5/1= B4/1 | C5'A4/3 | r/4"},
              "drone": {"voice": "tibia", "gain": 0.3, "pan": 0.0, "send": 0.3, "vel": 0.7,
                        "legato": True, "notes": "F4/10 | r/4"}},
}
CORNU = {  # a cornu's call from the arena: open partials of a horn on F
    "bpm": 84, "meter": [4], "tail": 3.0, "reverb": (3.5, 2.6, 1.6, 0.04),
    "parts": {"cornu": {"voice": "horn", "gain": 1.0, "pan": 0.0, "send": 0.8, "bright": 0.85,
                        "vel": 0.8, "notes": "C4/1 F4/1 A4/1 C5/1 | A4/0.5 F4/0.5 C4/1 F4/2 | r/4"}},
}
HYDRAULIS = {  # the water organ on a game day: sustained fifths and octaves, as at the arena
    "bpm": 84, "meter": [4], "tail": 3.0, "reverb": (3.5, 2.6, 1.6, 0.04),
    "parts": {"organ": {"voice": "organ", "gain": 1.0, "pan": 0.0, "send": 0.7, "vel": 0.8,
                        "notes": "F3+C4+F4/2 G3+D4+G4/2 | F3+C4+F4+C5/3 r/1 | r/4"}},
}
ARRIVE = {  # the overview motif: F A C on the cithara, answered by F on a far cornu
    "bpm": 84, "meter": [4], "tail": 3.0, "reverb": (3.5, 2.6, 1.6, 0.03),
    "parts": {"cithara": {"voice": "cithara", "gain": 1.0, "pan": 0.0, "spread": 0.4,
                          "send": 0.35, "ring": 4.0, "vel": 0.85, "notes": "F4/1 A4/1 C5/2 | r/4"},
              "cornu": {"voice": "horn", "gain": 0.25, "pan": 0.3, "send": 1.0, "bright": 0.8,
                        "vel": 0.75, "notes": "r/2.5 F4/3 r/2.5"}},
}


def phrase(piece, rng, keep):
    """A short score as a one-shot (not a loop), mono."""
    x = score.render(piece, rng, one_shot=keep)
    return sd.finish_sfx(x.mean(axis=1) * np.sqrt(2), rng, 0.0, fade_out=0.5)


def tibia(rng):
    return phrase(TIBIA, rng, 5.5)


def cornu(rng):
    return phrase(CORNU, rng, 5.8)


def hydraulis(rng):
    return phrase(HYDRAULIS, rng, 5.8)


def arrive(rng):
    return phrase(ARRIVE, rng, 5.5)


def sistrum(rng):
    """A sistrum shaken at the Iseum: three strokes of jangling discs."""
    x = ancient.sistrum(0.9, rng, shakes=3, spacing=0.28)
    return sd.finish_sfx(x, rng, 0.35, 1.2)


# --- files -----------------------------------------------------------------------------

FILES = {
    "music/rome/day.ogg": dict(
        kind="music", render=day, piece=DAY, lufs=-18.0, quality=4, gain=1.0, when="day",
        purpose="Day piece: cithara theme in a Lydian-type mode on F in bars of 3 and 4, tibia in "
                "heterophony, a festival middle with hydraulis fifths and a far cornu."),
    "music/rome/night.ogg": dict(
        kind="music", render=night, piece=NIGHT, lufs=-18.0, quality=4, gain=1.0, when="night",
        purpose="Night piece: a lyre with long notes in free time, tibia sighs, a faint hydraulis "
                "pedal on F and C."),
    "amb/rome/day.ogg": dict(
        kind="bed", render=city_day, lufs=-22.0, quality=2, gain=1.0, when="day",
        where="everywhere in the region",
        purpose="Dense far murmur, a corner fountain, hawkers' sung cries, hammering, a donkey, "
                "a crowd's far swell."),
    "amb/rome/forum.ogg": dict(
        kind="bed", render=forum, lufs=-22.0, quality=2, gain=0.8, when="day",
        where="zone or count-driven: the Forum Romanum and the imperial fora",
        purpose="Close voices, an orator declaiming far off under a portico, feet on paving, pigeons."),
    "amb/rome/river.ogg": dict(
        kind="bed", render=river, lufs=-22.0, quality=2, gain=0.8, when="always",
        where="zone: the Tiber banks and the Emporium",
        purpose="Water slapping barges, mooring ropes creaking, dockers calling out, gulls."),
    "amb/rome/circus.ogg": dict(
        kind="bed", render=circus, lufs=-21.0, quality=2, gain=0.8, when="event",
        where="near the Circus Maximus during races (R5); gain by distance",
        purpose="A vast crowd's roar surging as the teams pass (three laps a loop), hooves on sand."),
    "amb/rome/night.ogg": dict(
        kind="bed", render=city_night, lufs=-23.0, quality=2, gain=1.0, when="night",
        where="everywhere in the region",
        purpose="Carts rolling over basalt, oxen, a shout, a dog, a tavern song far off, a fountain."),
    "amb/rome/procession.ogg": dict(
        kind="loop", render=procession, piece=PROCESSION, lufs=-23.0, quality=2, gain=0.8,
        when="event", where="positional: follows the pompa or a sacrifice procession",
        purpose="Tibia over its drone with drum and cymbals walking past (4 pairs of 3+4, 84 bpm)."),
    "amb/rome/fountain.ogg": dict(
        kind="loop", render=lacus, lufs=-25.0, quality=2, gain=0.7, when="always",
        where="positional: each street fountain (lacus) and nymphaeum",
        purpose="A spout pouring into a stone basin."),
    "amb/rome/baths.ogg": dict(
        kind="loop", render=baths, lufs=-25.0, quality=2, gain=0.7, when="afternoon",
        where="positional: bath buildings while open (R3)",
        purpose="Splashes, a poured bucket and voices ringing in a vaulted hall."),
    "amb/rome/treadwheel.ogg": dict(
        kind="loop", render=treadwheel, lufs=-25.0, quality=2, gain=0.7, when="worked",
        where="positional: a treadwheel crane while it lifts (R7)",
        purpose="Men stepping in the wheel, the axle groaning, the pawl clacking."),
    "sfx/rome/tibia.wav": dict(kind="sfx", render=tibia, lufs=-21.0, gain=1.0,
                               purpose="A tibia phrase over its drone at a sacrifice."),
    "sfx/rome/cornu.wav": dict(kind="sfx", render=cornu, lufs=-23.0, gain=0.9,
                               purpose="A cornu call from the arena on a game day, far off."),
    "sfx/rome/hydraulis.wav": dict(kind="sfx", render=hydraulis, lufs=-23.0, gain=0.9,
                                   purpose="Water-organ chords from the Colosseum on a game day."),
    "sfx/rome/sistrum.wav": dict(kind="sfx", render=sistrum, lufs=-24.0, gain=0.9,
                                 purpose="A sistrum shaken at the Iseum."),
    "sfx/rome/arrive.wav": dict(kind="sfx", render=arrive, lufs=-22.0, gain=1.0,
                                purpose="Arrival motif (fast travel, era caption): cithara F A C, cornu F."),
}
