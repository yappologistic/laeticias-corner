"""The world set: beds for the connective stretches between the cities (sea, ship, mountains,
road, river, fields, desert night, storm, the mist at the era seams), positional loops and
effects shared by every city (feet, hooves, carts, smiths, looms, braziers, animals, weather),
the seam chime and the motif for arriving home."""

import numpy as np

import ambience
import instruments as ins
import sounds as sd
from dsp import SR, bandpass, glide, lowpass, midi_hz, pan, phase_of, place, secs, times

# --- beds ------------------------------------------------------------------------------


def open_sea(rng, layers=None, length=36.0):
    """Open water out of sight of land: a slow swell washing past, wind over it, a gull."""
    n = secs(length)
    birds = sd.Bed(length, rng)
    birds.scatter(sd.gull, 3, dist=(0.6, 0.9), level=(0.3, 0.45))
    swell = sd.loop_noise(n, rng, 60, 1800, 0.9) * sd.swell(n, rng, 0.12, 0.6, 0.2)[:, None]
    return sd.mix({
        "swell": 0.3 * swell,
        "chop": 0.3 * sd.waves(n, rng, 4.0, 0.6),
        "wind": 0.1 * sd.wind(n, rng, 150, 2500, 0.05, 0.5),
        "birds": 2.5 * birds.finish((2.0, 1.4, 0.7, 0.03), 0.5),
    }, layers)


def ship(rng, layers=None, length=40.0):
    """Close to a ship under sail: timbers creaking as she rolls, the sail filling and
    luffing, rigging tapping, water running along the hull."""
    n = secs(length)
    roll = length / 5  # five rolls a loop: the creaks follow them
    hull = sd.Bed(length, rng)
    for k in range(5):
        for j in range(int(rng.integers(1, 3))):
            hull.add(sd.creak_short(rng, rng.uniform(0.6, 1.1), rng.uniform(45, 80)),
                     k * roll + rng.uniform(0, 1.5) + j * 1.2, rng.uniform(-0.6, 0.6), 0.3, 0.5)
        hull.add(sd.modes(secs(0.15), [rng.uniform(500, 800), 1500], [1.0, 0.3], [0.03, 0.01], rng),
                 k * roll + rng.uniform(2, 4), rng.uniform(-0.5, 0.5), 0.4, 0.3)
    sail = sd.loop_noise(n, rng, 80, 900, 0.8, 1) * sd.swell(n, rng, 0.4, 0.8, 0.05) ** 2
    return sd.mix({
        "water": 0.16 * sd.loop_noise(n, rng, 200, 4000, 0.6) * sd.swell(n, rng, 0.25, 0.4)[:, None],
        "hull": 4.0 * hull.finish((0.8, 0.6, 0.3, 0.01), 0.25),
        "sail": 0.07 * pan(sail, 0.2),
        "wind": 0.08 * sd.wind(n, rng, 200, 2500, 0.08, 0.5),
    }, layers)


def mountain(rng, layers=None, length=36.0):
    """High in the mountains: a cold gusting wind that whistles on the rocks, a raven,
    sheep bells very far down the slope."""
    n = secs(length)
    life = sd.Bed(length, rng)
    life.scatter(sd.raven, 3, dist=(0.5, 0.8), level=(0.3, 0.45))
    pos = rng.uniform(-0.7, 0.7)
    for _ in range(14):
        life.add(sd.bell(rng.uniform(800, 1200), rng, 0.5, "sheet"), rng.uniform(0, length),
                 pos + rng.uniform(-0.1, 0.1), 0.92, rng.uniform(0.1, 0.25))
    return sd.mix({
        "wind": 0.22 * sd.wind(n, rng, 100, 2800, 0.05, 0.8, whistle=0.08),
        "life": 3.0 * life.finish((3.0, 2.2, 1.0, 0.04), 0.6),
    }, layers)


def road(rng, layers=None, length=36.0):
    """A dusty road across open country: dry wind, larks overhead, the bells of a caravan
    and a horse somewhere ahead, a cart far behind."""
    n = secs(length)
    life = sd.Bed(length, rng)
    life.scatter(lambda r: sd.lark(r, r.uniform(2.0, 4.0)), 4, dist=(0.6, 0.85), level=(0.2, 0.35))
    life.add(sd.bells_walking(rng, 14.0, 950, 1.1, jangle=1), rng.uniform(0, length), -0.4, 0.8, 0.4)
    life.add(sd.bells_walking(rng, 6.0, 1500, 1.8), rng.uniform(0, length), 0.5, 0.8, 0.25)
    cart = sd.cart(length, rng, 0.8, 0.6)
    return sd.mix({
        "wind": 0.14 * sd.wind(n, rng, 150, 2200, 0.07, 0.6),
        "life": 1.4 * life.finish((2.0, 1.4, 0.7, 0.02), 0.4),
        "cart": 0.15 * pan(cart, 0.6),
    }, layers)


def river(rng, layers=None, length=36.0):
    """A broad river through reed beds: water moving and lapping, reeds rustling in the
    breeze, frogs."""
    n = secs(length)
    water = sd.Bed(length, rng, tail=3.0)
    sd.trickle(water, 60, 300, 1500, dist=(0.2, 0.6), level=0.4)
    frogs = sd.Bed(length, rng)
    for _ in range(6):
        frogs.add(lowpass(ambience.frog(rng), 2500), rng.uniform(0, length), rng.uniform(-0.8, 0.8),
                  rng.uniform(0.4, 0.7), 0.35)
    breeze = sd.swell(n, rng, 0.1, 0.6)
    reeds = ambience.crackle(n, rng, 60 * breeze, 1500, 4500)
    return sd.mix({
        "flow": 0.12 * sd.loop_noise(n, rng, 80, 2000, 0.8) * sd.swell(n, rng, 0.2, 0.2)[:, None],
        "water": water.finish((1.0, 0.8, 0.4, 0.01), 0.3),
        "reeds": 0.08 * np.stack([reeds, np.roll(reeds, secs(7.0))], axis=1),
        "frogs": frogs.finish((1.6, 1.2, 0.5, 0.02), 0.4),
    }, layers)


def fields(rng, layers=None, length=36.0):
    """Farmland and pasture (Latium, the plateaus): larks, wind in grass and pines,
    cowbells far off."""
    n = secs(length)
    life = sd.Bed(length, rng)
    life.scatter(lambda r: sd.lark(r, r.uniform(2.5, 5.0)), 6, dist=(0.5, 0.85), level=(0.2, 0.35))
    pos = rng.uniform(-0.7, 0.7)
    for _ in range(10):
        life.add(sd.bell(rng.uniform(420, 560), rng, 0.8, "sheet"), rng.uniform(0, length),
                 pos + rng.uniform(-0.1, 0.1), 0.88, rng.uniform(0.15, 0.3))
    return sd.mix({
        "wind": 0.13 * sd.wind(n, rng, 200, 3000, 0.06, 0.6),
        "life": 1.5 * life.finish((2.0, 1.5, 0.7, 0.02), 0.4),
    }, layers)


def desert_night(rng, layers=None, length=36.0):
    """Night on the steppe or desert: almost silence, a faint cold wind, a few crickets,
    an owl far off."""
    n = secs(length)
    life = sd.Bed(length, rng)
    sd.crickets(life, 2, level=0.2)
    t = rng.uniform(0, 20)
    for k in range(4):
        life.add(sd.scops_owl(rng), t + k * 3.1, -0.6, 0.85, 0.2)
    return sd.mix({
        "wind": 0.08 * sd.wind(n, rng, 80, 1200, 0.04, 0.7),
        "life": life.finish((3.0, 2.0, 0.9, 0.04), 0.6),
    }, layers)


def thunder(rng, dur=3.6):
    """Distant thunder: a deep rolling rumble with a few cracks smeared by distance."""
    n = secs(dur)
    t = times(n)
    env = np.minimum(1, t / 0.4) * np.exp(-t / (dur / 3))
    env *= 1 + 0.6 * sd.swell(n, rng, 3.0, 0.8, 0.0)
    rumble = lowpass(rng.standard_normal(n), 220, 4) * env
    for _ in range(int(rng.integers(2, 5))):
        at = rng.uniform(0.1, dur / 2)
        k = secs(at)
        m = n - k
        rumble[k:] += 0.5 * lowpass(rng.standard_normal(m), 900, 2) * np.exp(-times(m) / 0.25)
    return lowpass(rumble, 1200)


def storm(rng, layers=None, length=36.0):
    """A storm passing over (W1): heavy rain, wind in hard gusts, thunder rolling far off."""
    n = secs(length)
    rain = sd.loop_noise(n, rng, 150, 5000, 0.4) * sd.swell(n, rng, 0.08, 0.3)[:, None]
    sky = sd.Bed(length, rng)
    for _ in range(3):
        sky.add(thunder(rng), rng.uniform(0, length), rng.uniform(-0.6, 0.6), 0.6, 0.9)
    return sd.mix({
        "rain": 0.2 * rain,
        "wind": 0.18 * sd.wind(n, rng, 100, 2500, 0.1, 0.9, whistle=0.04),
        "thunder": 3.0 * sky.finish((3.0, 2.5, 1.0, 0.04), 0.6),
    }, layers)


def seam(rng, layers=None, length=40.0):
    """The mist band between two eras: a soft airy drone on open fifths (A and E), slowly
    breathing, no melody, under the ducked beds."""
    n = secs(length)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for i, m in enumerate((45, 52, 57, 64)):
        f = float(midi_hz(m))
        for side, detune in ((0, -0.15), (1, 0.15)):
            # Whole cycles per loop for every partial and beat, so the seam is invisible.
            fk = round((f + detune) * length) / length
            breath = 0.6 + 0.4 * np.sin(2 * np.pi * (i + 1) * t / length + i)
            out[:, side] += breath * (np.sin(2 * np.pi * fk * t) + 0.2 * np.sin(4 * np.pi * fk * t)) \
                / (1 + i)
    air = sd.loop_noise(n, rng, 300, 3000, 0.8) * sd.swell(n, rng, 0.1, 0.5)[:, None]
    return sd.mix({"drone": 0.2 * out, "air": 0.05 * air}, layers)


# --- positional loops ------------------------------------------------------------------


def cart_loop(rng):
    return sd.cart(8.0, rng, 1.0)


def smith(rng):
    """A smithy at work: the bellows breathing the fire up, then the hammer ringing on
    the anvil in a working rhythm."""
    length = 10.0
    shop = sd.Bed(length, rng, tail=3.0)
    for k in range(4):  # bellows: four breaths
        n = secs(1.0)
        puff = bandpass(rng.standard_normal(n), 150, 1500) * np.sin(np.pi * np.arange(n) / n) ** 2
        shop.add(puff, k * 1.1, -0.3, 0.3, 0.5)
    for k in range(10):  # hammer: a pattern of blows, the last ones lighter
        shop.add(sd.anvil(rng), 5.0 + k * 0.45 + rng.normal(0, 0.01), 0.2, 0.3,
                 0.8 if k % 3 == 0 else 0.5)
    return shop.finish((1.0, 0.8, 0.4, 0.01), 0.3) + 0.15 * pan(sd.fire(length, rng, 0.5), -0.4)


def loom(rng):
    """An upright loom: the shuttle swishing through the shed, the beater packing the weft
    with a soft thud, the heddle rod clacking as the shed changes."""
    length = 8.0
    cycle = length / 4
    shop = sd.Bed(length, rng, tail=2.0)
    for k in range(4):
        n = secs(0.35)
        swish = bandpass(rng.standard_normal(n), 800, 4000) * np.sin(np.pi * np.arange(n) / n) ** 2
        shop.add(swish, k * cycle, -0.4 if k % 2 else 0.4, 0.3, 0.4)
        shop.add(sd.modes(secs(0.2), [120, 260, 700], [1.0, 0.5, 0.2], [0.04, 0.03, 0.01], rng),
                 k * cycle + 0.7, 0.0, 0.3, 0.7)
        shop.add(sd.modes(secs(0.12), [900, 1700], [1.0, 0.4], [0.02, 0.01], rng),
                 k * cycle + 1.3, 0.1, 0.3, 0.4)
    return shop.finish((1.0, 0.8, 0.4, 0.01), 0.3)


def brazier(rng):
    return sd.fire(10.0, rng, 1.0)


# --- effects ---------------------------------------------------------------------------


def step(rng):
    x = sd.step(rng, "stone")
    return sd.finish_sfx(x, rng, 0.1, 0.4, fade_out=0.02)


def hoof(rng):
    return sd.finish_sfx(sd.hoof(rng, "stone"), rng, 0.1, 0.4, fade_out=0.02)


def gallop(rng):
    """A courier at the gallop passing on a road (L6): hoofbeats swelling and fading."""
    x = sd.hoofbeats(rng, 2.5, "gallop", "stone")
    n = len(x)
    return sd.finish_sfx(x * np.sin(np.pi * np.arange(n) / n), rng, 0.2, 0.8)


def chisel(rng):
    return sd.finish_sfx(sd.chisel(rng), rng, 0.15, 0.5, fade_out=0.02)


def hammer(rng):
    return sd.finish_sfx(sd.hammer_stone(rng), rng, 0.15, 0.5, fade_out=0.02)


def pour(rng):
    return sd.finish_sfx(sd.pour(rng), rng, 0.15, 0.5)


def dog_far(rng):
    """One dog barks, another answers far away (W10)."""
    out = np.zeros(secs(3.0))
    place(out, sd.dog(rng, 2), 0)
    place(out, 0.4 * lowpass(sd.dog(rng, 2), 1500), secs(1.4))
    return sd.finish_sfx(out, rng, 0.4, 1.5)


def sheep_bells(rng):
    """A flock moving along a track (L1): bells clonking, a bleat or two."""
    out = np.zeros(secs(3.6))
    for _ in range(20):
        place(out, sd.bell(rng.uniform(700, 1300), rng, 0.4, "sheet") * rng.uniform(0.3, 1.0),
              secs(rng.uniform(0, 2.6)))
    place(out, 0.5 * sd.goat_bleat(rng), secs(rng.uniform(0.4, 2.0)))
    return sd.finish_sfx(out, rng, 0.3, 1.0)


def rope(rng):
    """A rope taking the strain on a bollard or a towing mast (R6)."""
    out = sd.creak_short(rng, 1.4, 55)
    return sd.finish_sfx(lowpass(out, 3000), rng, 0.15)


def thunder_far(rng):
    return sd.finish_sfx(thunder(rng), rng, 0.5, 2.0, fade_out=0.4)


def swifts(rng):
    """Swifts screaming round the roofs at dusk (W4), a passing group."""
    out = np.zeros(secs(2.5))
    for _ in range(6):
        place(out, sd.swift(rng) * rng.uniform(0.4, 1.0), secs(rng.uniform(0, 1.6)))
    return sd.finish_sfx(out, rng, 0.3, 1.0)


def crane_call(rng):
    """One crane's bugling call: a rolling, trumpeting 'krroo'."""
    dur = rng.uniform(0.5, 0.7)
    n = secs(dur)
    f0 = glide(n, [(0, 700), (0.1, 820), (dur, 680)]) * rng.uniform(0.9, 1.1)
    roll = 1 + 0.3 * np.sin(2 * np.pi * 28 * times(n))
    x = np.sin(phase_of(f0)) + 0.5 * np.sin(2 * phase_of(f0)) + 0.2 * np.sin(3 * phase_of(f0))
    return x * roll * np.sin(np.pi * np.arange(n) / n) ** 0.5


def cranes(rng):
    """A skein of cranes passing high over (W3), bugling to one another."""
    out = np.zeros(secs(3.5))
    for _ in range(8):
        place(out, crane_call(rng) * rng.uniform(0.4, 1.0), secs(rng.uniform(0, 2.7)))
    return sd.finish_sfx(lowpass(out, 3500), rng, 0.5, 1.5)


def gull(rng):
    x = np.concatenate([sd.gull(rng), np.zeros(secs(0.15)), sd.gull(rng)])
    return sd.finish_sfx(x, rng, 0.3, 1.0)


def pigeons_up(rng):
    """Pigeons bursting up from a plaza (W13): a clatter of wings."""
    out = np.zeros(secs(2.0))
    for _ in range(7):
        place(out, sd.wingbeats(rng, int(rng.integers(6, 10)), rng.uniform(8, 11))
              * rng.uniform(0.4, 1.0), secs(rng.uniform(0, 0.5)))
    return sd.finish_sfx(out, rng, 0.2, 0.8)


def lamp(rng):
    """A clay oil lamp lit from a taper (W11): a tiny breath of flame catching."""
    n = secs(0.6)
    t = times(n)
    catch = bandpass(rng.standard_normal(n), 300, 3000) * np.minimum(1, t / 0.05) * np.exp(-t / 0.15)
    tick = bandpass(rng.standard_normal(n), 2000, 6000) * np.exp(-t / 0.004)
    return sd.finish_sfx(catch + 0.3 * tick, rng, 0.1)


def vendor(rng):
    """A vendor's cry across a market (W12), sung out with no words."""
    return sd.finish_sfx(sd.babble(1.6, rng, 160, 4, 2200, calling=True), rng, 0.3, 1.0)


def chime(rng):
    """The era seam: three soft glass-and-bell tones on open fifths (A, E, A)."""
    out = np.zeros(secs(3.0))
    for at, m in ((0.0, 69), (0.25, 76), (0.5, 81)):
        place(out, ins.glass(float(midi_hz(m)), 2.8, 0.6, rng), secs(at))
        place(out, 0.4 * ins.bell(float(midi_hz(m)), 2.5, 0.5, rng), secs(at))
    return sd.finish_sfx(out, rng, 0.5, 1.5, fade_out=0.4)


def arrive_home(rng):
    """Arriving home: the corner's own motif (A B C# A) on the music box over a felt-piano
    D major ninth, in the corner's D lydian."""
    out = np.zeros(secs(4.6))
    for at, m in ((0.0, 81), (0.42, 83), (0.83, 85), (1.25, 81)):
        place(out, ins.tine(float(midi_hz(m)), 3.0, 0.75, rng), secs(at))
    for i, m in enumerate((50, 57, 66, 69, 73, 76)):
        place(out, 0.5 * ins.felt_piano(float(midi_hz(m)), 2.6, 0.45, rng), secs(1.25 + 0.05 * i))
    return sd.finish_sfx(out, rng, 0.35, 1.2, fade_out=0.5)


# --- files -----------------------------------------------------------------------------

BED_Q = 1  # world beds are long-playing backgrounds: q1 keeps the set near its 6 MB budget

FILES = {
    "amb/world/sea.ogg": dict(
        # q2: at q1 the encoder's error at the file edges clicks against the smooth swell
        kind="bed", render=open_sea, lufs=-23.0, quality=2, gain=1.0, when="always",
        where="stretches: Tyrrhenian, Adriatic, Ionian, Aegean seas, the Gulf",
        purpose="Open water: a slow swell, wind over it, a far gull."),
    "amb/world/ship.ogg": dict(
        kind="bed", render=ship, lufs=-23.0, quality=BED_Q, gain=0.8, when="always",
        where="positional: near a ship token under way (or count-driven by ships in view)",
        purpose="Timbers creaking as she rolls, the sail filling and luffing, water along the hull."),
    "amb/world/mountain.ogg": dict(
        kind="bed", render=mountain, lufs=-23.0, quality=BED_Q, gain=1.0, when="always",
        where="stretches: Apennines, Zagros",
        purpose="Cold gusting wind whistling on rock, a raven, far sheep bells."),
    "amb/world/road.ogg": dict(
        kind="bed", render=road, lufs=-23.0, quality=BED_Q, gain=1.0, when="day",
        where="stretches: Anatolian plateau, Syrian steppe, the Royal Road",
        purpose="Dry wind, larks, a caravan's and a horse's bells ahead, a cart far behind."),
    "amb/world/river.ogg": dict(
        kind="bed", render=river, lufs=-23.0, quality=BED_Q, gain=1.0, when="always",
        where="stretches: Ionia-Lydia, Mesopotamia; river tiles anywhere",
        purpose="A broad river lapping, reeds rustling, frogs."),
    "amb/world/fields.ogg": dict(
        kind="bed", render=fields, lufs=-23.0, quality=BED_Q, gain=1.0, when="day",
        where="stretches: Latium-Italy, mainland Greece countryside, Iranian plateau",
        purpose="Larks, wind in grass and pines, cowbells far off."),
    "amb/world/desert_night.ogg": dict(
        kind="bed", render=desert_night, lufs=-23.0, quality=BED_Q, gain=1.0, when="night",
        where="stretches at night: steppe, plateaus, desert, open country",
        purpose="Near silence: a faint cold wind, a few crickets, a far owl."),
    "amb/world/storm.ogg": dict(
        kind="bed", render=storm, lufs=-21.0, quality=BED_Q, gain=1.0, when="weather",
        where="weather: a storm cell (W1), mixed over the stretch's bed",
        purpose="Heavy rain, hard gusts, thunder rolling far off."),
    "amb/world/seam.ogg": dict(
        kind="bed", render=seam, lufs=-23.0, quality=BED_Q, gain=0.7, when="always",
        where="the mist bands at the era seams (all other beds duck 6 dB)",
        purpose="A soft airy drone on open fifths (A, E), breathing, with no melody."),
    "amb/world/cart.ogg": dict(
        kind="loop", render=cart_loop, lufs=-25.0, quality=BED_Q, gain=0.8, when="moving",
        where="positional: any cart or wagon while it moves (night carts R1)",
        purpose="Iron-rimmed wheels on paving: rumble, joint knocks, axle creak."),
    "amb/world/smith.ogg": dict(
        kind="loop", render=smith, lufs=-25.0, quality=BED_Q, gain=0.8, when="worked",
        where="positional: a smithy slot while worked",
        purpose="Bellows breathing the fire up, then the hammer on the anvil."),
    "amb/world/loom.ogg": dict(
        kind="loop", render=loom, lufs=-26.0, quality=BED_Q, gain=0.7, when="worked",
        where="positional: a loom slot while worked (weavers in every city)",
        purpose="Shuttle swish, beater thud, heddle clack."),
    "amb/world/brazier.ogg": dict(
        kind="loop", render=brazier, lufs=-26.0, quality=BED_Q, gain=0.7, when="lit",
        where="positional: braziers, fire altars, hearths, bonfires (R12)",
        purpose="A small fire crackling over a low breathy roar."),
    "sfx/world/step.wav": dict(kind="sfx", render=step, lufs=-28.0, gain=0.6,
                               purpose="One footstep on stone (step frames of walkers)."),
    "sfx/world/hoof.wav": dict(kind="sfx", render=hoof, lufs=-26.0, gain=0.7,
                               purpose="One hoof on paving (step frames of horses, mules, oxen)."),
    "sfx/world/gallop.wav": dict(kind="sfx", render=gallop, lufs=-24.0, gain=0.9,
                                 purpose="A rider at the gallop passing (couriers, L6)."),
    "sfx/world/chisel.wav": dict(kind="sfx", render=chisel, lufs=-26.0, gain=0.7,
                                 purpose="A mallet on a chisel biting stone (mason use frames)."),
    "sfx/world/hammer.wav": dict(kind="sfx", render=hammer, lufs=-26.0, gain=0.7,
                                 purpose="A hammer dressing stone (builders, sculptors)."),
    "sfx/world/pour.wav": dict(kind="sfx", render=pour, lufs=-26.0, gain=0.8,
                               purpose="Water poured from a jar (water carriers, fountains A9)."),
    "sfx/world/dog_far.wav": dict(kind="sfx", render=dog_far, lufs=-25.0, gain=0.8,
                                  purpose="A dog barks and another answers far away (W10)."),
    "sfx/world/sheep_bells.wav": dict(kind="sfx", render=sheep_bells, lufs=-25.0, gain=0.8,
                                      purpose="A flock with bells and a bleat moving along a track (L1)."),
    "sfx/world/rope.wav": dict(kind="sfx", render=rope, lufs=-26.0, gain=0.8,
                               purpose="A rope creaking under strain (towed barges R6, moorings)."),
    "sfx/world/thunder_far.wav": dict(kind="sfx", render=thunder_far, lufs=-22.0, gain=1.0,
                                      purpose="Distant thunder (W1)."),
    "sfx/world/swifts.wav": dict(kind="sfx", render=swifts, lufs=-27.0, gain=0.7,
                                 purpose="Swifts screaming round the roofs at dusk (W4)."),
    "sfx/world/cranes.wav": dict(kind="sfx", render=cranes, lufs=-25.0, gain=0.8,
                                 purpose="Cranes bugling high overhead on migration (W3)."),
    "sfx/world/gull.wav": dict(kind="sfx", render=gull, lufs=-25.0, gain=0.8,
                               purpose="A gull's laughing calls (harbours, ships, S2)."),
    "sfx/world/pigeons_up.wav": dict(kind="sfx", render=pigeons_up, lufs=-25.0, gain=0.8,
                                     purpose="Pigeons bursting up from a plaza (W13)."),
    "sfx/world/lamp.wav": dict(kind="sfx", render=lamp, lufs=-30.0, gain=0.6,
                               purpose="An oil lamp catching from a taper (lamplighter, W11)."),
    "sfx/world/vendor.wav": dict(kind="sfx", render=vendor, lufs=-25.0, gain=0.8,
                                 purpose="A vendor's sung-out cry with no words (W12, markets)."),
    "sfx/world/seam.wav": dict(kind="sfx", render=chime, lufs=-22.0, gain=1.0,
                               purpose="The soft chime when the era caption appears at a seam."),
    "sfx/world/arrive_home.wav": dict(kind="sfx", render=arrive_home, lufs=-20.0, gain=1.0,
                                      purpose="Arriving home: the corner's motif on the music box."),
}
