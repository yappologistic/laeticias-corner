"""What the land between still lacked (world set): a cricket-free night floor for green country
and every winter night, small towns' day beds by culture (the towns used their capitals' big
murmur), a Levantine harbour, a harbour in winter with its ships laid up, a quarry at work,
and the voices of the new animal kinds (heron, deer outside the rut, boar, dolphin)."""

import numpy as np

import people
import sounds as sd
import wildlife as wl
from atmos import entry, noise_burst, resonant_burst
from dsp import lowpass, pan, place, secs, times

W = "world"

# --- night in green country -------------------------------------------------------------------


def night_country(rng, length=37.0):
    """Night over farmland and pasture, or any winter night: air moving in the grass, a dog
    somewhere far off, a sheep's bell as the flock shifts in its fold, a gate knocking. No
    insects (green country's summer nights get theirs from the nature beds; winter has none)."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(2):
        life.add(sd.dog(rng, int(rng.integers(1, 3))), rng.uniform(0, length),
                 rng.uniform(-0.8, 0.8), 0.92, 0.35)
    for _ in range(2):  # the flock shifting: a few strokes of one bell, then quiet
        t, pos = rng.uniform(0, length), rng.uniform(-0.7, 0.7)
        for _ in range(int(rng.integers(3, 6))):
            life.add(sd.bell(rng.uniform(560, 640), rng, 0.9, "sheet"), t, pos, 0.9,
                     rng.uniform(0.12, 0.22))
            t += rng.uniform(0.3, 1.1)
    life.add(sd.creak_short(rng, 0.5, rng.uniform(55, 75)), rng.uniform(0, length), 0.4, 0.85, 0.3)
    return sd.mix({
        "air": 0.1 * sd.wind(n, rng, 70, 1100, 0.05, 0.6),
        "grass": 0.025 * sd.loop_noise(n, rng, 900, 4500, 0.7) * sd.swell(n, rng, 0.15, 0.6)[:, None],
        "life": 1.3 * life.finish((3.0, 2.0, 0.9, 0.04), 0.6),
    })


# --- small towns by day -----------------------------------------------------------------------

TOWN = {  # culture -> what a small town's day holds besides its people
    "latin": dict(animals=(sd.donkey, wl.hen_2), work="anvil", cart="stone"),
    "greek": dict(animals=(sd.goat_bleat, wl.hen_3), work="stone", cart="earth"),
    "persian": dict(animals=(wl.camel, wl.horse_blow), work="anvil", cart="earth"),
}


def town_day(culture):
    """A small town by day: a handful of people talking in its street, a smith or a mason
    at work down the lane, its animals, a dog, a cart going by, swallows over the roofs."""
    t = TOWN[culture]

    def render(rng, length=41.0):
        n = secs(length)
        life = sd.Bed(length, rng)
        tool = sd.anvil if t["work"] == "anvil" else sd.hammer_stone
        at, pos = rng.uniform(0, length), rng.uniform(-0.7, 0.7)
        for _ in range(3):  # bouts of work with rests between
            for _ in range(int(rng.integers(5, 10))):
                life.add(tool(rng), at, pos + rng.uniform(-0.05, 0.05), 0.75, rng.uniform(0.3, 0.45))
                at += rng.uniform(0.55, 0.8)
            at += rng.uniform(5, 9)
        for make in t["animals"]:
            for _ in range(2):
                life.add(make(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                         rng.uniform(0.5, 0.8), 0.45)
        life.add(sd.dog(rng, 2), rng.uniform(0, length), rng.uniform(-0.8, 0.8), 0.85, 0.35)
        life.scatter(sd.swallow, 5, dist=(0.4, 0.8), level=(0.25, 0.45))
        for _ in range(16):
            life.add(people.foot(rng, "stone" if culture != "persian" else "earth"),
                     rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.6),
                     rng.uniform(0.15, 0.35))
        return sd.mix({
            "people": 0.9 * people.crowd(culture, 0)(rng, length),
            "life": 1.2 * life.finish((1.6, 1.1, 0.5, 0.015), 0.4),
            "cart": 0.12 * pan(sd.cart(length, rng, 0.7, 0.5), rng.uniform(-0.6, 0.6)),
            "air": 0.05 * sd.wind(n, rng, 150, 2200, 0.06, 0.5),
        })

    return render


# --- harbours ---------------------------------------------------------------------------------


def knock(rng, f=None):
    """A wooden knock: a mallet on a hull, a block against a mast, a rope's end on a rail."""
    f = f or rng.uniform(260, 520)
    return sd.modes(secs(0.25), [f, f * 2.3, f * 3.9], [1.0, 0.45, 0.2], [0.05, 0.03, 0.02], rng)


def harbour_levant(rng, length=43.0):
    """A Phoenician harbour (Sidon): small waves slapping the stone moles, hulls creaking at
    their ropes, shipwrights' mallets, sailors calling across the water (no words), gulls, a
    sail shaken out."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(55):
        life.add(lowpass(sd.slap(rng), 1000), rng.uniform(0, length), rng.uniform(-0.9, 0.9),
                 rng.uniform(0.2, 0.55), rng.uniform(0.2, 0.45))
    for _ in range(10):
        life.add(sd.creak_short(rng, rng.uniform(0.6, 1.3), rng.uniform(45, 85)),
                 rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.45, 0.3)
    at, pos = rng.uniform(0, length), rng.uniform(-0.6, 0.6)
    for _ in range(3):  # a shipwright caulking a hull: bouts of mallet blows
        for _ in range(int(rng.integers(6, 11))):
            life.add(knock(rng, rng.uniform(300, 360)), at, pos, 0.65, rng.uniform(0.35, 0.5))
            at += rng.uniform(0.4, 0.6)
        at += rng.uniform(6, 10)
    life.scatter(sd.gull, 7, dist=(0.35, 0.8), level=(0.3, 0.5))
    return sd.mix({
        "water": 0.13 * sd.waves(n, rng, 4.0, 0.7),
        "life": life.finish((1.8, 1.2, 0.6, 0.02), 0.35),
        "sailors": 0.22 * sd.crowd(length, rng, 3, f0=(105, 165), ceiling=2000, calling=3),
    })


def harbour_winter(rng, length=47.0):
    """A harbour in winter (November to February, the sea closed): the ships laid up and
    roped, hulls groaning slowly, blocks knocking against masts in the wind, small cold
    waves, a gull or two; no oars, almost no voices."""
    n = secs(length)
    life = sd.Bed(length, rng)
    for _ in range(30):
        life.add(lowpass(sd.slap(rng), 800), rng.uniform(0, length), rng.uniform(-0.9, 0.9),
                 rng.uniform(0.3, 0.6), rng.uniform(0.15, 0.35))
    for _ in range(14):
        life.add(sd.creak_short(rng, rng.uniform(0.9, 1.8), rng.uniform(35, 60)),
                 rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(0.4, 0.7), 0.3)
    for _ in range(4):  # gusts set loose blocks knocking: two or three, then still
        at, pos, f = rng.uniform(0, length), rng.uniform(-0.8, 0.8), rng.uniform(380, 600)
        for _ in range(int(rng.integers(2, 4))):
            life.add(knock(rng, f * rng.uniform(0.97, 1.03)), at, pos, 0.6, rng.uniform(0.2, 0.35))
            at += rng.uniform(0.35, 0.9)
    life.scatter(sd.gull, 3, dist=(0.5, 0.85), level=(0.25, 0.4))
    life.add(sd.babble(2.5, rng, 120, 4.0, 1800), rng.uniform(0, length), 0.5, 0.85, 0.35)
    return sd.mix({
        "water": 0.11 * sd.waves(n, rng, 5.0, 0.6),
        "wind": 0.1 * sd.wind(n, rng, 120, 2000, 0.07, 0.6),
        "life": life.finish((2.0, 1.4, 0.6, 0.02), 0.4),
    })


# --- a quarry ---------------------------------------------------------------------------------


def split(rng):
    """A block coming free along its wedges: a dull crack and the rumble of stone settling."""
    crack = resonant_burst(rng, 0.6, rng.uniform(140, 200), 2.0, 0.12)
    rumble = noise_burst(rng, 1.4, 60, 600, 0.45, 0.02)
    out = np.zeros(secs(1.6))
    place(out, crack, 0)
    place(out, 0.6 * rumble, secs(0.05))
    return out


def quarry(rng, length=23.0):
    """A quarry face at work (Tibur's travertine, Pentelikon's marble): picks and chisels
    dressing blocks, a row of wedges driven in turn, a block splitting free, grit trickling,
    a call to stand clear."""
    life = sd.Bed(length, rng)
    for _ in range(70):
        life.add(sd.chisel(rng), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                 rng.uniform(0.2, 0.6), rng.uniform(0.25, 0.5))
    at = rng.uniform(0, length)
    for _ in range(3):  # wedges along a line, struck in turn, each a little higher
        for k in range(6):
            life.add(sd.wedge(rng), at, -0.3 + 0.1 * k, 0.35, 0.55)
            at += rng.uniform(0.45, 0.6)
        at += rng.uniform(2.5, 4.0)
    life.add(split(rng), rng.uniform(0, length), 0.2, 0.4, 0.8)
    for _ in range(25):
        life.add(noise_burst(rng, 0.25, 1500, 6000, 0.08), rng.uniform(0, length),
                 rng.uniform(-0.5, 0.5), 0.35, 0.12)
    life.add(sd.babble(1.6, rng, 130, 4.0, 2000, calling=True), rng.uniform(0, length), -0.4,
             0.6, 0.5)
    return life.finish((1.2, 0.9, 0.5, 0.01), 0.3)


# --- animal voices ----------------------------------------------------------------------------


def croak(rng, dur, f, level=1.0):
    """A grey heron's harsh 'fraank': a low, very rough voice from a long neck."""
    return level * wl.syllable(
        rng, dur, [(0, f * 0.9), (0.15, f * 1.15), (1, f * 0.8)],
        [([(0, 550), (0.2, 900), (1, 650)], 280, 1.0), (1400, 380, 0.55), (2500, 500, 0.2)],
        tilt=0.75, jitter=0.04, shimmer=0.35, breath=0.45, sub=0.8, attack=0.012, release=0.12,
        puff=0.4)


def heron_1(rng):
    """One heron's croak as it lifts off the reeds."""
    return croak(rng, rng.uniform(0.38, 0.5), rng.uniform(170, 210))


def heron_2(rng):
    """Two croaks, the second shorter: a heron disturbed, flying off downriver."""
    return wl.calls([(croak(rng, 0.42, rng.uniform(180, 205)), 0.0),
                     (croak(rng, 0.28, rng.uniform(160, 185), 0.8), rng.uniform(0.7, 1.0))], rng)


def bark_deer(rng, f, level=1.0):
    """A deer's alarm bark: a gruff, breathy 'bah' from the woods' edge."""
    return level * wl.syllable(
        rng, rng.uniform(0.16, 0.22), [(0, f * 1.1), (0.25, f * 1.2), (1, f * 0.75)],
        [(650, 300, 1.0), (1250, 350, 0.6), (2400, 500, 0.25)], tilt=0.7, jitter=0.03,
        shimmer=0.25, breath=0.7, sub=0.35, attack=0.006, release=0.08, puff=0.5)


def deer_1(rng):
    """A deer barking three times at something in the trees (all year, dawn and dusk)."""
    f = rng.uniform(260, 320)
    return wl.calls([(bark_deer(rng, f * rng.uniform(0.97, 1.03), (1.0, 0.85, 0.75)[k]),
                      k * rng.uniform(1.1, 1.5)) for k in range(3)], rng)


def deer_2(rng):
    """Two barks and a snort as the deer bounds away."""
    f = rng.uniform(280, 340)
    snort = noise_burst(rng, 0.3, 300, 2500, 0.08, 0.01)
    return wl.calls([(bark_deer(rng, f), 0.0), (bark_deer(rng, f * 0.95, 0.8), 1.2),
                     (0.5 * snort, 2.1)], rng)


def grunt(rng, f, level=1.0):
    """A wild boar's short grunt: a low nasal pulse through a wet snout."""
    return level * wl.syllable(
        rng, rng.uniform(0.1, 0.16), [(0, f), (0.4, f * 1.15), (1, f * 0.85)],
        [(380, 200, 1.0), (900, 300, 0.4), (2000, 400, 0.12)], tilt=0.8, jitter=0.04,
        shimmer=0.3, breath=0.5, sub=0.6, attack=0.01, release=0.05)


def snuffle(rng, dur):
    """The snout rooting in leaf litter: wet sniffs and rustles."""
    out = np.zeros(secs(dur))
    for _ in range(int(dur * 7)):
        place(out, noise_burst(rng, 0.12, 400, 3500, 0.03, 0.005) * rng.uniform(0.2, 0.5),
              secs(rng.uniform(0, dur - 0.15)))
    return out


def boar_1(rng):
    """A boar rooting at night: a string of soft grunts over sniffing in the leaves."""
    f = rng.uniform(75, 95)
    parts = [(snuffle(rng, 2.6), 0.0)]
    t = 0.2
    for _ in range(int(rng.integers(5, 8))):
        parts.append((grunt(rng, f * rng.uniform(0.92, 1.08), rng.uniform(0.6, 1.0)), t))
        t += rng.uniform(0.25, 0.45)
    return wl.calls(parts, rng)


def boar_2(rng):
    """A boar startled: a hard snort and quick grunts as it crashes off."""
    f = rng.uniform(85, 105)
    snort = resonant_burst(rng, 0.35, 420, 2.5, 0.1) + noise_burst(rng, 0.35, 300, 3000, 0.09, 0.005)
    parts = [(0.8 * snort, 0.0)]
    t = 0.45
    for _ in range(4):
        parts.append((grunt(rng, f * rng.uniform(1.0, 1.15)), t))
        t += rng.uniform(0.14, 0.22)
    return wl.calls(parts, rng)


def blow(rng):
    """A dolphin surfacing: the blowhole's sharp exhalation and a quick in-breath."""
    out = np.zeros(secs(0.6))
    t = times(secs(0.3))
    whoosh = noise_burst(rng, 0.3, 500, 5000, 0.09, 0.004) * (1 + 0.3 * np.sin(2 * np.pi * 40 * t))
    place(out, whoosh, 0)
    place(out, 0.35 * noise_burst(rng, 0.18, 400, 2500, 0.06, 0.03), secs(0.32))
    return out


def dolphin_1(rng):
    """A dolphin breaking the surface: water parting, a blow, the back rolling under."""
    return wl.calls([(0.6 * sd.splash_small(rng), 0.0), (blow(rng), 0.12),
                     (0.5 * sd.splash_small(rng), 0.8)], rng)


def dolphin_2(rng):
    """Two dolphins surfacing one after the other off the bow."""
    return wl.calls([(0.5 * sd.splash_small(rng), 0.0), (blow(rng), 0.1),
                     (0.4 * sd.splash_small(rng), 0.9), (0.7 * blow(rng), 1.3),
                     (0.35 * sd.splash_small(rng), 1.9)], rng)


FILES = {
    f"amb/{W}/night_country.ogg": entry(
        "bed", night_country, -23.0, "Night in green country: air in the grass, a far dog, a sheep's "
        "bell, a gate knocking; no insects.", when="night",
        where="night bed of farmland and pasture (Latium, Greece, Thrace, the corner's country) and "
        "of every region's winter nights", quality=1, tags=["night", "country"]),
    **{f"amb/{W}/town_{c}.ogg": entry(
        "bed", town_day(c), -22.0, f"A small {c.capitalize()} town by day: a handful of people, "
        "work down the lane, its animals, a dog, a cart, swallows.", when="day",
        where=f"day bed of the {c.capitalize()} towns besides the capitals and royal seats",
        quality=1, tags=["town", "day", c]) for c in TOWN},
    f"amb/{W}/harbour_levant.ogg": entry(
        "bed", harbour_levant, -22.0, "A Phoenician harbour: waves on the moles, hulls on their ropes, "
        "shipwrights' mallets, sailors calling, gulls.", when="always",
        where="zone: Sidon's harbours (and any Levantine port)", quality=1,
        tags=["harbour", "sea", "levant"]),
    f"amb/{W}/harbour_winter.ogg": entry(
        "bed", harbour_winter, -22.0, "A harbour in winter: ships laid up, hulls groaning, blocks "
        "knocking in the wind, cold small waves, a gull; no oars.", when="always",
        where="harbour zones from November to February (in place of the busy harbour and the oars)",
        quality=1, tags=["harbour", "sea", "winter"]),
    f"amb/{W}/quarry.ogg": entry(
        "loop", quarry, -24.0, "A quarry at work: picks and chisels, wedges driven in turn, a block "
        "splitting free, grit, a call.", when="worked",
        where="positional: quarries (Tibur's travertine, Pentelikon) in their working hours",
        quality=1, tags=["work", "quarry", "stone"]),
}
for _name, _fn, _lufs, _desc, _tags in (
        ("heron_1", heron_1, -25.0, "A grey heron's croak as it lifts off the reeds.",
         ["animal", "bird", "heron", "water"]),
        ("heron_2", heron_2, -25.0, "A heron croaking twice as it flies off downriver.",
         ["animal", "bird", "heron", "water"]),
        ("deer_1", deer_1, -25.0, "A deer's alarm bark, three times, from the woods' edge (all year).",
         ["animal", "deer"]),
        ("deer_2", deer_2, -25.0, "A deer barking twice and snorting as it bounds away.",
         ["animal", "deer"]),
        ("boar_1", boar_1, -26.0, "A wild boar rooting at night: soft grunts, sniffing in the leaves.",
         ["animal", "boar", "night"]),
        ("boar_2", boar_2, -25.0, "A boar startled: a hard snort and quick grunts.",
         ["animal", "boar"]),
        ("dolphin_1", dolphin_1, -25.0, "A dolphin breaking the surface: a splash, its blow, the back "
         "rolling under.", ["animal", "dolphin", "sea"]),
        ("dolphin_2", dolphin_2, -25.0, "Two dolphins surfacing and blowing one after the other.",
         ["animal", "dolphin", "sea"])):
    # Splashes and blows are broadband: the dolphins stop at 4.5 kHz, as heard across water.
    top = 4500.0 if _name.startswith("dolphin") else 6500.0
    FILES[f"sfx/{W}/{_name}.wav"] = entry("sfx", wl.fx(_fn, top=top), _lufs, _desc, gain=0.8,
                                          tags=_tags)
