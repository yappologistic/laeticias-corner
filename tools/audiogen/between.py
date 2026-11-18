"""The land and sea between the cities (81 % of the map): wind in leafy trees by strength,
waves on rocky shores and the open sea by state (the summer meltemi and the winter storms of
the closed sea), small streams, a grazing flock, a rowed boat; and the one-shots the engine
sprinkles over them: a cart passing, a sail filling, owls, wolves far off, a nightingale, a stag
roaring in the autumn rut, geese going over, starlings wheeling, a lark, gulls, drips."""

import numpy as np

import ambience
import people
import sounds as sd
import weather
import wildlife as wl
from atmos import WATER_EQ, band, entry, eq, kernels, noise_burst, resonant_burst, scatter_train, swell
from dsp import glide, lowpass, place, secs, times

# --- wind in leafy trees ----------------------------------------------------------------

TREES = (dict(name="breeze", level=1, rustle=60), dict(name="strong", level=2, rustle=160),
         dict(name="gale", level=3, rustle=320))
TREES_LUFS = (-25.5, -22.0, -18.5)


def wind_trees(level):
    """Wind in a leafy canopy (woods, groves, orchards, spring to autumn): the soft roar of
    the crowns, leaves rustling in the gusts, boughs creaking when it blows hard."""
    p = TREES[level]

    def render(rng, length=31.0):
        n = secs(length)
        air, _, G = weather.wind_core(n, rng, weather.WIND[p["level"]])
        crowns = band(n, rng, 300, 2500, 0.6) * G**1.5
        rustle = np.stack([ambience.crackle(n, rng, p["rustle"] * G[:, k] ** 2, 1500, 6000)
                           for k in range(2)], axis=1)
        layers = {"air": 0.7 * air, "crowns": 0.35 * crowns, "rustle": 0.4 * rustle}
        if level:
            b = sd.Bed(length, rng)
            for _ in range(2 * level):
                b.add(sd.creak_short(rng, rng.uniform(0.6, 1.2), rng.uniform(40, 70)),
                      rng.uniform(0, length), rng.uniform(-0.7, 0.7), 0.5, 0.3)
            layers["boughs"] = 1.5 * b.finish((1.5, 1.0, 0.4, 0.02), 0.3)
        return sd.mix(layers)

    return render


# --- rocky shores and the open sea ----------------------------------------------------------

ROCKS = (dict(name="calm", period=5.0, slap=0.6, suck=0.5, boom=0.0, spray=0.1, wind=0),
         dict(name="moderate", period=7.0, slap=1.0, suck=0.8, boom=0.3, spray=0.4, wind=1),
         dict(name="storm", period=9.0, slap=1.4, suck=0.6, boom=1.0, spray=1.0, wind=3))
SEA_LUFS = (-27.0, -23.5, -20.0)


def sea_rocks(level):
    """Waves on a rocky shore (the Ionian and Aegean capes, the Levant's headlands): water
    slapping into crevices, sucking and gurgling back out, spray; in a storm, booms in the
    sea caves."""
    p = ROCKS[level]

    def render(rng, length=31.0):
        n = secs(length)
        sides = [weather.surf_envelopes(n, np.random.default_rng(rng.integers(1 << 31)),
                                        p["period"], s, 0.2) for s in (0.0, rng.uniform(0.2, 0.5))]
        E = {k: np.stack([sides[0][k], sides[1][k]], axis=1) for k in sides[0]}
        slaps = scatter_train(n, rng, 3.0 * (1 + E["crash"].mean(axis=1) * 6), kernels(weather.k_lap, 10, rng),
                              sigma=0.5)
        suck = np.stack([scatter_train(n, rng, 60 * E["draw"][:, c] + 2,
                                       kernels(lambda r: weather.k_bubble(r, 250, 1200), 8, rng),
                                       channels=1)[:, 0] for c in range(2)], axis=1)
        layers = {
            "slaps": p["slap"] * slaps,
            "wash": 0.5 * band(n, rng, 80, 2500, 0.8) * E["wash"] ** 1.5,
            "suck": p["suck"] * 0.6 * suck,
            "spray": p["spray"] * band(n, rng, 1500, 6000, 0.3) * E["crash"] ** 2,
            "under": 0.3 * band(n, rng, 25, 200, 1.0) * (0.4 + 0.6 * E["wash"]),
        }
        if p["boom"]:  # air slammed out of a sea cave
            boom = np.zeros(n)
            for i in range(max(1, round(length / p["period"]))):
                m = secs(1.0)
                tm = times(m)
                x = np.sin(2 * np.pi * (45 + 25 * np.exp(-tm / 0.08)) * tm) * np.exp(-tm / 0.3)
                place(boom, x * rng.uniform(0.4, 1.0), secs(i * p["period"] + rng.uniform(0, 0.5)) % (n - m))
            layers["boom"] = 0.5 * p["boom"] * np.stack([boom, np.roll(boom, secs(0.02))], axis=1)
        if p["wind"]:
            layers["wind"] = 0.2 * weather.wind_core(n, rng, weather.WIND[p["wind"]],
                                                     weather.WIND_PLACES["sea"])[0]
        return eq(sd.mix(layers), WATER_EQ)

    return render


OPEN = (dict(name="swell", crests=0.0, wind=1, depth=0.4),
        dict(name="whitecaps", crests=1.0, wind=2, depth=0.5),
        dict(name="storm", crests=2.2, wind=3, depth=0.6))


def sea_open(level):
    """Open water by sea state, heard from a ship or the air above it: a long swell; steady
    whitecaps under a strong steady wind (the meltemi in July and August, the shamal over the
    Gulf); the winter storm of the closed sea, crests breaking all round and the wind howling."""
    p = OPEN[level]

    def render(rng, length=37.0):
        n = secs(length)
        roll = swell(n, rng, 0.12, p["depth"], 0.2)[:, None]
        layers = {
            "swell": 0.6 * band(n, rng, 40, 1200, 0.9) * roll,
            "wind": 0.5 * weather.wind_core(n, rng, weather.WIND[p["wind"]], weather.WIND_PLACES["sea"])[0],
        }
        if p["crests"]:  # crests toppling: hissing bursts here and there
            env = np.zeros((n, 2))
            for c in range(2):
                for _ in range(int(length * 0.6 * p["crests"])):
                    at, d = rng.uniform(0, length), rng.uniform(0.8, 2.2)
                    m = secs(d)
                    tm = times(m)
                    shape = np.clip(tm / 0.15, 0, 1) * np.exp(-tm / (0.35 * d))
                    k = secs(at)
                    idx = (k + np.arange(m)) % n
                    env[idx, c] += shape * rng.uniform(0.4, 1.0)
            layers["crests"] = 0.5 * p["crests"] * band(n, rng, 400, 5500, 0.4) * env
        if level == 2:
            layers["deep"] = 0.4 * band(n, rng, 20, 150, 1.0) * roll ** 2
        return eq(sd.mix(layers), WATER_EQ)

    return render


def stream(rng, length=31.0):
    """A small stream or brook (mountain valleys, the hills' springs): water burbling over
    stones, little drops and runs, close and bright."""
    n = secs(length)
    s = swell(n, rng, 0.25, 0.25)
    ks = kernels(lambda r: weather.k_bubble(r, 500, 2800), 14, rng)
    return eq(sd.mix({
        "burble": scatter_train(n, rng, 220 * s, ks, sigma=0.6, spread=0.6),
        "run": 0.07 * band(n, rng, 300, 4500, 0.5) * s[:, None],
        "drops": 0.5 * scatter_train(n, rng, 6, kernels(weather.drip, 8, rng)),
    }), WATER_EQ)


# --- animals and boats ---------------------------------------------------------------------


def flock(rng, length=16.0):
    """A flock grazing: bells clonking as heads go down, bleats, grass torn, a shepherd's
    whistle now and then."""
    b = sd.Bed(length, rng)
    for _ in range(int(length * 1.6)):
        b.add(sd.bell(rng.uniform(600, 1200), rng, 0.5, "sheet"), rng.uniform(0, length),
              rng.uniform(-0.8, 0.8), rng.uniform(0.3, 0.7), rng.uniform(0.2, 0.5))
    for _ in range(3):
        b.add(wl.sheep(rng, lamb=rng.random() < 0.3), rng.uniform(0, length), rng.uniform(-0.7, 0.7),
              rng.uniform(0.3, 0.6), 0.5)
    for _ in range(int(length * 1.5)):
        b.add(people.grains(rng, 0.15, 25, 600, 3500), rng.uniform(0, length), rng.uniform(-0.6, 0.6),
              0.25, 0.4)
    m = secs(0.7)
    f = glide(m, [(0, 1800), (0.3, 2600), (0.7, 2100)])
    whistle = np.sin(2 * np.pi * np.cumsum(f) / 44100) * np.sin(np.pi * np.arange(m) / m)
    b.add(whistle, rng.uniform(0, length), rng.uniform(-0.5, 0.5), 0.6, 0.2)
    return b.finish((1.5, 1.0, 0.4, 0.02), 0.3)


def oars(rng, length=9.0):
    """A boat rowed by a crew: blades catching the water together, the pull, drips off the
    blades on the return, the oars knocking in their tholes."""
    n = secs(length)
    b = sd.Bed(length, rng, tail=3.0)
    strokes = int(round(length / 1.8))
    for k in range(strokes):
        at = k * length / strokes
        for side in (-0.4, 0.4):
            m = secs(0.5)
            catch = band(m, rng, 200, 2500, 0.6, 1) * np.exp(-times(m) / 0.12)
            place(catch, 0.6 * resonant_burst(rng, 0.2, 180, 3, 0.04), 0)  # the blade's knock
            b.add(catch, at + 0.02 * (side > 0), side, 0.3, 0.8)
            b.add(sd.modes(secs(0.12), [rng.uniform(500, 800)], [1.0], [0.02], rng), at + 0.8, side, 0.3, 0.4)
        for _ in range(4):
            b.add(weather.drip(rng), at + rng.uniform(1.0, 1.6), rng.uniform(-0.5, 0.5), 0.3, 0.35)
    water = 0.05 * band(n, rng, 100, 2500, 0.7)
    return b.finish((1.0, 0.7, 0.3, 0.01), 0.2) + water


def cart_pass(rng):
    """An ox-cart going by on a country road: the rumble and the axle's squeal rising, close,
    and falling away."""
    dur = 4.4
    n = secs(dur)
    t = times(n)
    near = np.exp(-(((t - 2.1) / 1.0) ** 2))
    body = sd.cart(dur, rng, 0.7, 1.2)[:n]
    hooves = sd.hoofbeats(rng, dur - 0.5, "walk", "dust")[:n]
    hooves = np.pad(hooves, (0, n - len(hooves)))
    x = (body + 0.5 * hooves) * (0.15 + 0.85 * near)
    return lowpass(x, 2500 + 2500 * float(near.max()))


def sail(rng):
    """A sail losing the wind and filling again: a flutter, a crack as it fills, the sheet
    creaking."""
    n = secs(2.2)
    t = times(n)
    rate = 9 + 5 * np.clip(1 - t / 1.2, 0, 1)
    flutter = band(n, rng, 150, 2000, 0.5, 1) * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / 44100)) ** 4
    flutter *= np.clip(1 - t / 1.25, 0, 1)
    out = 0.6 * flutter
    place(out, noise_burst(rng, 0.3, 120, 3500, 0.05) + 0.6 * resonant_burst(rng, 0.3, 110, 3, 0.08),
          secs(1.25))
    place(out, 0.4 * sd.creak_short(rng, 0.6), secs(1.45))
    return out


def wolves(rng):
    """Wolves howling far off across the mountains on a winter night: a long rising howl,
    others joining, a few yips."""
    out = np.zeros(secs(4.4))
    for k, at in enumerate((0.0, 0.7, 1.4)):
        dur = rng.uniform(2.2, 2.8)
        f = rng.uniform(320, 420) * (1 + 0.15 * k)
        x = wl.syllable(rng, dur, [(0, f * 0.8), (0.15, f * 1.15), (0.7, f * 1.1), (1, f * 0.75)],
                        [(800, 300, 1.0), (1600, 400, 0.3)], tilt=1.1, breath=0.25,
                        attack=0.3, release=0.8, vib=(4.5, 0.01))
        place(out, x * (1.0, 0.7, 0.55)[k], secs(at))
    for _ in range(4):
        y = wl.syllable(rng, 0.15, [(0, 700), (1, 900)], [(1000, 400, 1.0)], tilt=0.9, breath=0.3)
        place(out, 0.4 * y, secs(rng.uniform(2.9, 4.0)))
    return lowpass(out, 2200)


def nightingale(rng):
    """A nightingale in the dark (April to June): a run of rich repeated notes, a long
    swelling whistle, a liquid chuckle."""
    out = np.zeros(secs(4.2))
    at = 0.0
    for _ in range(int(rng.integers(5, 8))):  # 'jug-jug-jug'
        place(out, wl.note([(0, 1800), (1, 1500)], 0.05, 0.3) * 0.8, secs(at))
        at += 0.09
    at += 0.25
    for k in range(4):  # 'piu piu piu', swelling
        place(out, wl.note([(0, 2800), (0.5, 3400), (1, 3000)], 0.22, 0.05) * (0.4 + 0.2 * k), secs(at))
        at += 0.3
    at += 0.15
    place(out, 0.7 * wl.trill(rng), secs(at))
    return out


def stag(rng):
    """A red deer stag roaring in the autumn rut (mountain woods, September and October):
    deep belling groans, three, the last breaking off."""
    out = np.zeros(secs(4.4))
    at = 0.0
    for k in range(3):
        dur = rng.uniform(0.9, 1.3) * (0.7 if k == 2 else 1.0)
        f = rng.uniform(110, 140)
        x = wl.syllable(rng, dur, [(0, f * 0.8), (0.3, f * 1.1), (1, f * 0.7)],
                        [([(0, 350), (0.4, 520), (1, 300)], 150, 1.0), (1100, 300, 0.3)],
                        tilt=0.8, breath=0.4, sub=0.5, attack=0.08, release=0.25)
        place(out, x, secs(at))
        at += dur + rng.uniform(0.2, 0.4)
    return lowpass(out, 2000)


def geese_over(rng):
    """A skein of geese going over high (winter on the marshes; cranes' cousins): honking in
    a ragged chorus that passes and fades."""
    out = np.zeros(secs(4.6))
    for _ in range(9):
        place(out, wl.goose_far(rng) * rng.uniform(0.4, 1.0), secs(rng.uniform(0, 2.4)))
    t = times(len(out))
    return out * np.sin(np.pi * np.clip(t / 4.4, 0, 1)) ** 0.8


def starlings(rng):
    """A starling murmuration wheeling at dusk (Rome and Latium, October to February): the
    rush of thousands of wings swelling as the flock turns overhead, the chatter beneath."""
    n = secs(4.2)
    t = times(n)
    env = np.exp(-(((t - 1.9) / 0.9) ** 2)) + 0.5 * np.exp(-(((t - 3.1) / 0.5) ** 2))
    wings = band(n, rng, 250, 3000, 0.5, 1) * env
    flutter = (0.7 + 0.3 * np.sin(2 * np.pi * 14 * t)) * env
    chatter = np.zeros(n)
    for _ in range(80):
        a = rng.uniform(2000, 5500)
        place(chatter, sd.chirp(a, a * rng.uniform(0.6, 1.5), rng.uniform(0.02, 0.07), 0.3) * rng.uniform(0.2, 1),
              secs(rng.uniform(0.2, 3.9)))
    return 0.8 * wings * flutter + 0.25 * chatter


def drip_fx(rng):
    """One drop from a leaf or an eave (the event layer over rain and after it)."""
    x = np.zeros(secs(0.3))
    place(x, weather.drip(rng), 0)
    return x


# --- files -------------------------------------------------------------------------------

W = "world"
FILES = {}
for _lvl, _p in enumerate(TREES):
    FILES[f"amb/{W}/wind_trees_{_lvl + 1}.ogg"] = entry(
        "bed", wind_trees(_lvl), TREES_LUFS[_lvl], f"Wind in leafy trees, {_p['name']}.",
        when="weather", where="woods, groves and orchards in view (spring to autumn; wind.bare in "
        "winter), by wind strength: breeze from 0.25, strong from 0.55, gale from 0.85",
        family="wind.trees", level=_lvl + 1, level_name=_p["name"], tags=["weather", "wind", "trees"])
for _lvl, _p in enumerate(ROCKS):
    FILES[f"amb/{W}/sea_rocks_{_lvl + 1}.ogg"] = entry(
        "bed", sea_rocks(_lvl), SEA_LUFS[_lvl], f"Waves on a rocky shore, {_p['name']}.",
        where=f"sea state {_lvl + 1}/3 where the view holds rocky coast (cliffs, capes, islands)",
        family="sea.rocks", level=_lvl + 1, level_name=_p["name"], tags=["sea", "coast", "rocks"])
for _lvl, _p in enumerate(OPEN):
    FILES[f"amb/{W}/sea_open_{_lvl + 1}.ogg"] = entry(
        "bed", sea_open(_lvl), SEA_LUFS[_lvl], f"Open water, {_p['name']}.",
        where=f"sea state {_lvl + 1}/3 over open sea: 2 for the meltemi (Aegean, July-August "
        "afternoons), the bora and the shamal; 3 for the closed sea's winter storms",
        family="sea.open", level=_lvl + 1, level_name=_p["name"], tags=["sea", "open"])
FILES.update({
    f"amb/{W}/stream.ogg": entry(
        "bed", stream, -23.0, "A small stream burbling over stones.", where="streams and brooks "
        "(narrow river tiles in hills and mountains, springs); river_1/2 for the broad rivers",
        tags=["water", "stream"]),
    f"amb/{W}/flock.ogg": entry(
        "loop", flock, -25.0, "A flock grazing: bells, bleats, grass torn, a shepherd's whistle.",
        when="always", where="positional: herds of sheep and goats (pastures, drove roads)",
        tags=["animal", "flock", "sheep"]),
    f"amb/{W}/oars.ogg": entry(
        "loop", oars, -25.0, "A crew rowing: blades catching together, drips, oars in the tholes.",
        when="moving", where="positional: rowed boats and galleys under oars (rivers, harbours, "
        "calm seas)", tags=["ship", "oars"]),
})
for _name, _fn, _lufs, _desc, _tags in (
        ("cart_pass", cart_pass, -25.0, "An ox-cart passing on a country road, rising and fading.",
         ["cart", "road"]),
        ("sail_flap", sail, -25.0, "A sail luffing and filling again with a crack, the sheet creaking.",
         ["ship", "sail"]),
        ("owl_tawny", wl.tawny, -25.0, "A tawny owl's long hoot and quavering answer (woods, all year; "
         "most in autumn).", ["animal", "owl", "night"]),
        ("owl_scops", lambda r: wl.calls([(sd.scops_owl(r), 2.7 * k) for k in range(2)], r), -26.0,
         "A scops owl's patient single note, twice (warm months, April to September).",
         ["animal", "owl", "night", "summer"]),
        ("wolves_far", wolves, -26.0, "Wolves howling far off across the mountains (winter nights).",
         ["animal", "wolf", "night", "winter", "mountain"]),
        ("nightingale", nightingale, -26.0, "A nightingale's song in the dark (April to June nights: "
         "the Academy, Latium's gardens, Pārsa's paradise).", ["animal", "bird", "night", "spring"]),
        ("stag_roar", stag, -25.0, "A stag roaring in the autumn rut (mountain woods, September-October).",
         ["animal", "deer", "autumn", "mountain"]),
        ("geese_over", geese_over, -25.0, "A skein of geese going over, honking (winter marshes and "
         "lagoons).", ["animal", "bird", "winter", "water"]),
        ("starlings", starlings, -24.0, "A starling murmuration wheeling overhead at dusk (Rome and "
         "Latium, October-February).", ["animal", "bird", "autumn", "winter", "dusk"]),
        ("lark", lambda r: sd.lark(r, 2.6), -27.0, "A skylark singing high over the fields.",
         ["animal", "bird", "day", "fields"]),
        ("gull_3", lambda r: wl.calls([(wl.gull_call(r)[: secs(0.7)], 0.0), (sd.gull(r), 0.6)], r),
         -24.0, "Gulls calling, a third variation (harbours, coasts, ships).", ["animal", "gull"])):
    FILES[f"sfx/{W}/{_name}.wav"] = entry("sfx", wl.fx(_fn), _lufs, _desc, gain=0.8, tags=_tags)
for _k in range(3):
    FILES[f"sfx/{W}/drip_{_k + 1}.wav"] = entry(
        "sfx", wl.fx(drip_fx, 0.1, 0.3), -28.0, f"One drop from a leaf or an eave, variation {_k + 1}.",
        gain=0.6, tags=["weather", "rain", "drip"])
