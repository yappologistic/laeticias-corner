"""The year in sound of every region file: which beds play by season, month and hour, where the
mix changes as the view moves (zones), when placed workplaces sound (timed loops), what the
festivals and the turns of the seasons play, and which calls each habitat gives. Written by
`apply` after `sound.apply` (it needs the measured districts); checked by `check` (the document
alone) and `check_world` (against the composed world). The field list, with one example each,
is `out/reports/world-sound.md`.

What the engine reads, and where this module writes it:

- `theme.ambience.beds` `{file, hours?, months?, weather?}` and `theme.seasons.<s>.ambience.beds`
  (a season's beds replace the plain ones for the hours and months they cover): the place's own
  bed, never a nature bed (those are `theme.sound.nature*`, played beside it).
- `theme.ambience.zones` `{rect, file, gain, hours?, months?}`: harbours, streams, quarries and
  pastures. `months` is new (the engine plays a zone in those calendar months only).
- `theme.ambience.loops` `{item, file, when, hours?, months?}`: `when` `"worked"` plays in
  `hours` (and `months`), new; `always`, `lit` and `afternoon` as before, `months` on any.
- `theme.sound.nature_seasons` `{season: {dawn, dusk, night, day}}` and `nature_snow`
  `{day, night}`; `theme.sound.calls` `[{file, hours, seasons?, months?}]`; `stings.season`.
- events' `ambience`, `sfx`, `sounds` (festivals' music, the turns' cues); roles' `sound.loop`.
"""

from __future__ import annotations

import re
import numpy as np

from plan import world_plan as P

from . import climates as C
from .compose import World, live_items
from .coords import COLS

MONTHS = C.MONTHS
SEASON_MONTHS = {s: MONTHS[3 * i:3 * i + 3] for i, s in enumerate(C.SEASONS)}
DAY, NIGHT = ["05:30", "19:30"], ["19:30", "05:30"]
EVENING, SMALL_HOURS = ["19:30", "23:00"], ["23:00", "05:30"]
HEAR = 20   # tiles: surf is heard this far inland (about half a view at 1x)
# Regions whose life module writes city beds of their own (kept as authored).
AUTHORED = {"rome", "athens", "parsa", "ostia", "brundisium"}

A, R, X, W = "amb/athens/", "amb/rome/", "amb/parsa/", "amb/world/"
SEA_BEDS = {W + "sea.ogg", A + "sea.ogg", R + "river.ogg"}   # beds of open water and harbours
NATURE_FILES = {W + f for f in (
    "dawn_scrub.ogg", "dawn_river.ogg", "dawn_mountain.ogg", "dusk_town.ogg", "dusk_water.ogg",
    "night_scrub.ogg", "night_water.ogg", "night_east.ogg", "night_mountain.ogg",
    "dawn_autumn.ogg", "dawn_winter.ogg", "dusk_autumn.ogg", "dusk_winter.ogg",
    "night_autumn.ogg", "night_cold.ogg", "night_snow.ogg", "day_snow.ogg")}


def bed(file: str, hours=None, months=None) -> dict:
    b = {"file": file}
    if hours:
        b["hours"] = list(hours)
    if months:
        b["months"] = list(months)
    return b


# -- beds ----------------------------------------------------------------------------------------

# Athens' own year (regions/athens/seasons.py), shared by the Greek towns.
GREEK_SEASONS = {
    "spring": [bed(A + "day_cool.ogg", DAY), bed(A + "night_winter.ogg", NIGHT, ["mar"])],
    "autumn": [bed(A + "day_cool.ogg", DAY, ["oct", "nov"]),
               bed(A + "night_winter.ogg", NIGHT, ["nov"])],
    "winter": [bed(A + "day_cool.ogg", DAY), bed(A + "night_winter.ogg", NIGHT)],
}
# Pārsa's own year (regions/parsa/seasons.py), shared by the Persian royal seats.
PERSIAN_SEASONS = {
    "summer": [bed(X + "plain_day_summer.ogg", ["05:30", "19:00"]),
               bed(X + "plain_night.ogg", ["19:00", "05:30"])],
    "autumn": [bed(X + "plain_day_summer.ogg", ["05:30", "19:00"], ["sep"]),
               bed(X + "plain_day_winter.ogg", ["05:30", "19:00"], ["nov"]),
               bed(X + "plain_night_winter.ogg", ["19:00", "05:30"], ["nov"])],
    "winter": [bed(X + "plain_day_winter.ogg", ["05:30", "19:00"]),
               bed(X + "plain_night_winter.ogg", ["19:00", "05:30"])],
    "spring": [bed(X + "plain_night_winter.ogg", ["19:00", "05:30"], ["mar"])],
}
ROMAN_WINTER = {"winter": [bed(R + "day_winter.ogg", DAY)]}


def beds_for(kind: str, flood: list[str], marsh: bool) -> tuple[list[dict], dict]:
    """(plain beds, season beds) of a bed kind. The night of open country is the quiet floor
    `desert_night` (faint wind, a far owl); the season's voices come from the nature beds."""
    country = [bed(W + "fields.ogg", DAY), bed(W + "desert_night.ogg", NIGHT)]
    if kind == "country":
        return country, {}
    if kind == "mountain":
        return [bed(W + "mountain.ogg")], {}
    if kind == "steppe":
        return [bed(W + "road.ogg", DAY), bed(W + "desert_night.ogg", NIGHT)], {}
    if kind == "river":
        seasons: dict = {}
        if flood:
            for s, ms in SEASON_MONTHS.items():
                fm = [m for m in flood if m in ms]
                if fm:
                    seasons.setdefault(s, []).append(bed(W + "flood.ogg", None, fm))
        if marsh:
            seasons.setdefault("winter", []).append(bed(W + "marsh_winter.ogg", DAY))
        return [bed(W + "river.ogg")], seasons
    if kind == "sea":
        return [bed(W + "sea.ogg")], {}
    if kind == "seam":
        return [bed(W + "seam.ogg")], {}
    if kind == "greek_town":
        return [bed(A + "day.ogg", DAY), bed(A + "night.ogg", NIGHT)], GREEK_SEASONS
    if kind == "greek_sanctuary_high":   # Delphi: the sanctuary by day, the cliffs by night
        return ([bed(A + "day.ogg", DAY), bed(W + "mountain.ogg", NIGHT)],
                {s: [b for b in v if b["hours"] == DAY] for s, v in GREEK_SEASONS.items()})
    if kind == "greek_villages":         # Sparta: fields by day, the villages' evenings
        return ([bed(W + "fields.ogg", DAY), bed(A + "night.ogg", NIGHT)],
                {s: [b for b in v if b["hours"] == NIGHT] for s, v in GREEK_SEASONS.items()
                 if any(b["hours"] == NIGHT for b in v)})
    if kind == "roman_city":
        return [bed(R + "day.ogg", DAY), bed(R + "night.ogg", NIGHT)], ROMAN_WINTER
    if kind == "roman_town":             # carts and taverns in the evening, then quiet
        return ([bed(R + "day.ogg", DAY), bed(R + "night.ogg", EVENING),
                 bed(W + "desert_night.ogg", SMALL_HOURS)], ROMAN_WINTER)
    if kind == "persian_seat":
        return ([bed(X + "plain_day.ogg", ["05:30", "19:00"]),
                 bed(X + "plain_night.ogg", ["19:00", "05:30"])], PERSIAN_SEASONS)
    if kind == "harbour_town":           # Sidon: the fleet's harbour is the town
        return [bed(A + "sea.ogg")], {}
    raise KeyError(kind)


# Each region's bed kind, by its own character (the cities keep their authored beds).
BED_KIND = {
    "corner": "country", "seam_dell": "seam", "seam_ionia": "seam", "seam_ionian": "seam",
    "latium_italy": "country", "greece": "country", "attica_north": "country",
    "thrace": "country", "east_med": "country", "ionia_lydia": "country",
    "apennines": "mountain", "arcadia": "mountain", "taurus": "mountain", "zagros": "mountain",
    "anatolia": "steppe", "syrian_steppe": "steppe", "iran_plateau": "steppe",
    "mesopotamia": "river", "susiana": "river",
    "tyrrhenian": "sea", "adriatic": "sea", "ionian_sea": "sea", "aegean": "sea",
    "saronic": "sea", "persian_gulf": "sea",
    "alban_mount": "country", "tibur": "country", "capua": "roman_city",
    "beneventum": "roman_town",
    "corcyra": "greek_town", "olympia": "greek_town", "corinth": "greek_town",
    "eleusis": "greek_town", "delos": "greek_town", "ephesus": "greek_town",
    "sardis": "greek_town", "academy": "country", "delphi": "greek_sanctuary_high",
    "sparta": "greek_villages",
    "halys": "steppe", "gordion": "steppe", "euphrates_crossing": "steppe",
    "persian_gates": "mountain", "susa": "persian_seat", "pasargadae": "persian_seat",
    "babylon": "river", "sidon": "harbour_town",
}


# -- the nature beds, by the sound climate (sound.climate_of) -------------------------------------

def nature_seasons(climate: str) -> dict | None:
    w = lambda f: W + f + ".ogg"
    warm = {"mediterranean": ("dawn_scrub", "dusk_town", "night_scrub"),
            "river_plain": ("dawn_river", "dusk_water", "night_water"),
            "mountain": ("dawn_mountain", "dusk_town", "night_mountain"),
            "east": ("dawn_mountain", "dusk_town", "night_east"),
            "steppe": ("dawn_scrub", "dusk_town", "night_east")}.get(climate)
    if warm is None:
        return None
    autumn = {"mediterranean": ("dawn_autumn", "dusk_autumn", "night_autumn"),
              "river_plain": ("dawn_autumn", "dusk_autumn", "night_autumn"),
              "mountain": ("dawn_mountain", "dusk_autumn", "night_autumn"),
              "east": ("dawn_mountain", "dusk_autumn", "night_east"),
              "steppe": ("dawn_autumn", "dusk_autumn", "night_east")}[climate]
    winter = ("dawn_winter", "dusk_winter",
              "night_mountain" if climate == "mountain" else "night_cold")
    out = {}
    for s, (d, u, n) in (("spring", warm), ("summer", warm), ("autumn", autumn),
                         ("winter", winter)):
        out[s] = {"dawn": w(d), "dusk": w(u), "night": w(n), "day": ""}
    return out


def snows(rid: str) -> bool:
    """Whether snow can lie anywhere in the region in some month (its climate's snow line)."""
    clim = next((c for c in C.CLIMATES if c["id"] == C.REGION_CLIMATE.get(rid)), {})
    line = (clim.get("snow") or {}).get("line") or []
    return any(v is not None for v in line)


# -- calls by habitat ------------------------------------------------------------------------------

def call(file: str, hours, months=None, seasons=None) -> dict:
    c = {"file": file, "hours": list(hours)}
    if seasons:
        c["seasons"] = list(seasons)
    if months:
        c["months"] = list(months)
    return c


NIGHT_HOURS = ["20:00", "05:00"]
GARDENS = {"academy", "latium_italy", "rome", "parsa", "pasargadae", "tibur", "olympia",
           "ionia_lydia", "sardis", "alban_mount", "corcyra", "ephesus", "capua", "corner"}
STAG_WOODS = {"apennines", "arcadia", "taurus", "thrace", "zagros", "alban_mount"}
WOLF_LAND = {"apennines", "arcadia", "taurus", "zagros", "persian_gates", "delphi", "thrace",
             "anatolia", "iran_plateau", "halys", "gordion"}
GEESE = {"mesopotamia", "susiana", "babylon", "susa", "ostia", "euphrates_crossing"}
STARLINGS = {"rome", "latium_italy", "ostia", "tibur", "alban_mount", "capua", "beneventum"}
FIELDS = {"latium_italy", "greece", "attica_north", "thrace", "ionia_lydia", "east_med",
          "anatolia", "iran_plateau", "tibur", "olympia", "sparta", "eleusis", "corner",
          "capua", "beneventum", "gordion", "halys", "sardis", "pasargadae", "parsa"}


def calls(rid: str, climate: str, coast: bool, woods: bool, people: bool,
          road: bool = False) -> list[dict]:
    """One-shots heard far off, one at a time, by the region's habitat and the calendar."""
    out: list[dict] = []
    land = climate != "sea"
    if land:
        if climate in ("mediterranean", "mountain"):
            out.append(call("sfx/world/cuckoo.wav", ["06:00", "11:00"], ["mar", "apr", "may"]))
        if climate in ("mediterranean", "mountain", "steppe"):
            out.append(call("sfx/world/crow_2.wav" if climate == "mediterranean"
                            else "sfx/world/crow_1.wav", ["07:00", "18:00"]))
        if climate in ("east", "river_plain"):
            out.append(call("sfx/world/stork_clatter.wav", ["07:00", "17:00"],
                            C.months("mar-aug")))
        if climate == "east":
            out.append(call("sfx/parsa/hoopoe.wav", ["06:00", "12:00"], C.months("mar-aug")))
        if climate == "river_plain":
            out.append(call("sfx/world/cranes.wav", ["06:00", "18:00"],
                            ["mar", "oct", "nov"]))
        if rid in FIELDS or climate == "steppe":
            out.append(call("sfx/world/lark.wav", ["06:00", "12:00"], C.months("mar-aug")))
        if woods or climate in ("mediterranean", "mountain", "river_plain"):
            out.append(call("sfx/world/owl_tawny.wav", NIGHT_HOURS))
        if climate in ("mediterranean", "east", "river_plain", "steppe"):
            out.append(call("sfx/world/owl_scops.wav", NIGHT_HOURS, C.months("apr-sep")))
        if rid in GARDENS:
            out.append(call("sfx/world/nightingale.wav", NIGHT_HOURS, ["apr", "may", "jun"]))
        if rid in WOLF_LAND:
            out.append(call("sfx/world/wolves_far.wav", NIGHT_HOURS, ["dec", "jan", "feb"]))
        if rid in STAG_WOODS:
            out.append(call("sfx/world/stag_roar.wav", ["19:00", "06:00"], ["sep", "oct"]))
        if rid in GEESE:
            out.append(call("sfx/world/geese_over.wav", ["07:00", "17:00"], C.months("nov-feb")))
        if rid in STARLINGS:
            out.append(call("sfx/world/starlings.wav", ["16:30", "19:00"], C.months("oct-feb")))
        if people:
            out.append(call("sfx/world/dog_far.wav", ["21:00", "04:00"]))
        if road:
            out.append(call("sfx/world/cart_pass.wav", ["07:00", "18:00"]))
    if coast or not land:
        out.append(call("sfx/world/gull_call.wav", ["06:00", "19:00"]))
        out.append(call("sfx/world/gull_3.wav", ["06:00", "19:00"]))
    if not land:
        out.append(call("sfx/world/sail_flap.wav", ["07:00", "18:00"], C.months("mar-oct")))
    return out


# -- festivals, the turns, work ----------------------------------------------------------------------

# The festivals' own music (audio-seasons.md §2, "Instruments and their sources").
KOMOS = {"ambience": {"file": A + "komos.ogg", "gain": 0.85}, "sfx": "sfx/athens/tympanon.wav"}
SATURNALIA = {"ambience": {"file": R + "saturnalia.ogg", "gain": 0.85}}
FEAST = {"ambience": {"file": X + "feast.ogg", "gain": 0.85}}
LITUUS = {"sfx": "sfx/rome/lituus.wav"}
FESTIVAL_SOUNDS = [
    (r"^(city_dionysia|rural_dionysia|lenaia|anthesteria)$", KOMOS),
    (r"^(saturnalia|country_saturnalia)$", SATURNALIA),
    (r"^(harvest_offering|bagayadi_offering|mithrakana)$", FEAST),
    (r"^(lupercalia|october_horse|pompa|parilia_pompa)$", LITUUS),
    (r"olive_harvest$", {"ambience": {"file": W + "olive_harvest.ogg", "gain": 0.8}}),
    (r"^(harvest_in|barley_harvest|levant_harvest|ionian_harvest|thracian_harvest|"
     r"plateau_harvest|susiana_harvest|harvest_home)$",
     {"ambience": {"file": W + "reaping.ogg", "gain": 0.75}}),
]
# The turns' cues (climates.TURNS names what is shown; these are the files recorded for them).
TURN_SOUNDS = {
    "cicadas_begin": {"sfx": "sfx/world/cicada_start.wav"},
    "leaves_turn": {"sfx": "sfx/world/leaves_skitter.wav"},
    "first_frost": {"sfx": "sfx/world/frost_steps.wav"},
    "vintage_begins": {"ambience": {"file": W + "vintage.ogg", "gain": 0.6}},
    "ploughing_begins": {"ambience": {"file": W + "ploughing.ogg", "gain": 0.6}},
    "flood_rising": {"ambience": {"file": W + "flood.ogg", "gain": 0.6}},
    "first_snow": {"ambience": {"file": W + "snow.ogg", "gain": 0.5}},
    "heat_haze": {"ambience": {"file": W + "heat.ogg", "gain": 0.4}},
    "first_dust": {"ambience": {"file": W + "dust_1.ogg", "gain": 0.5}},
}
# Seasonal and field work: the loop follows the worker while the role works (its months are the
# role's populations' `when`).
ROLE_LOOPS = [
    (r"^reaper$|^haymaker$", {"loop": W + "reaping.ogg", "oneshot": "sfx/world/sickle.wav"}),
    (r"^ploughman$", {"loop": W + "ploughing.ogg"}),
    (r"^(grape_picker|vintager)$", {"loop": W + "vintage.ogg"}),
    (r"^(olive_picker|olive_grower|olive_keeper)$", {"loop": W + "olive_harvest.ogg"}),
    (r"^oil_porter$", {"oneshot": "sfx/world/amphora.wav"}),
    (r"^(kiln_man|kiln_worker)$", {"loop": A + "kiln.ogg"}),
    (r"^(rower|boatman|ferryman)$", {"loop": W + "oars.ogg", "oneshot": "sfx/world/rope.wav"}),
    (r"^(palm_climber|resin_tapper)$", {"oneshot": "sfx/world/chop.wav"}),
    (r"^reed_cutter$", {"oneshot": "sfx/world/sickle.wav"}),
]
# Placed kinds that sound (pattern on the item's name part, file, when, hours, months). A kind
# may have several (a threshing floor threshes, then winnows).
WORK = ["07:00", "17:00"]
ITEM_LOOPS = [
    (r"threshing", W + "threshing.ogg", "worked", ["08:00", "17:00"], ["jun", "jul"]),
    (r"threshing", W + "winnowing.ogg", "worked", ["10:00", "18:00"], ["jul", "aug"]),
    (r"^[gpr]_press$", W + "press.ogg", "worked", WORK, ["nov", "dec", "jan"]),
    (r"^[gpr]_press$", W + "vintage.ogg", "worked", WORK, ["sep", "oct"]),
    (r"bakery", W + "bakery.ogg", "worked", ["03:00", "10:00"], None),
    (r"^p_oven$", W + "bakery.ogg", "worked", ["05:00", "10:00"], None),
    (r"windmill|mill$", W + "mill.ogg", "worked", WORK, None),
    (r"fullonica|dyeworks", W + "fullers.ogg", "worked", WORK, None),
    (r"loom", W + "loom.ogg", "worked", ["07:00", "18:00"], None),
    (r"smithy|forge", W + "smith.ogg", "worked", WORK, None),
    (r"^g_wheel$", A + "wheel.ogg", "worked", WORK, None),
    (r"charcoal_kiln", A + "kiln.ogg", "always", None, None),
    (r"^[gp]_kiln$", A + "kiln.ogg", "worked", ["06:00", "18:00"], None),
    (r"crane", R + "treadwheel.ogg", "worked", ["07:00", "16:00"], C.months("mar-nov")),
    (r"shipsheds", W + "saw.ogg", "worked", WORK, C.months("nov-feb")),
    (r"sheepfold", W + "flock.ogg", "worked", ["17:00", "21:00"], None),
    (r"glass", W + "hearth.ogg", "worked", WORK, None),
    (r"brazier|fire_altar|torch|beacon|watchtower", W + "brazier.ogg", "lit", None, None),
    (r"lacus|fountain|nymphae|meta_sudans|iuturnae|krene|basin", R + "fountain.ogg",
     "always", None, None),
    (r"bath", R + "baths.ogg", "afternoon", None, None),
    (r"(^|_)inn$|thermopolium|tavern", W + "hearth.ogg", "lit", None, None),
]
STAND_IN = "sfx/world/seam.wav"   # seasonlife.STAND_IN's one-shot
QUARRIES = ("world.quarry", "athens.pentelikon_quarry")
FESTIVAL_FILES = {A + "komos.ogg", R + "saturnalia.ogg", X + "feast.ogg", "sfx/athens/tympanon.wav",
                  "sfx/rome/lituus.wav"}


def item_loops(iid: str) -> list[tuple[str, str, list | None, list | None]]:
    name = iid.split(".")[-1]
    out, seen = [], set()
    for pat, f, when, hours, months in ITEM_LOOPS:
        if re.search(pat, name) and f not in seen:
            out.append((f, when, hours, months))
            seen.add(f)
            if when not in ("worked",):
                break
    return out


def loop_entry(iid: str, f: str, when: str, hours, months) -> dict:
    e = {"item": iid, "file": f, "when": when}
    if hours:
        e["hours"] = list(hours)
    if months:
        e["months"] = list(months)
    return e


# -- what the world holds ------------------------------------------------------------------------

_CACHE: dict[tuple[str, int], tuple[World, object]] = {}


def _cached(key: str, world: World, make):
    """One value per composed world (worlds are not hashable; the entry keeps its world alive so
    the id is not reused)."""
    k = (key, id(world))
    if k not in _CACHE or _CACHE[k][0] is not world:
        if len(_CACHE) > 8:
            _CACHE.clear()
        _CACHE[k] = (world, make(world))
    return _CACHE[k][1]


def _sea_near(world: World):
    """(sea tiles, tiles within HEAR of the sea) over the plan."""
    sea_ids = [i for i, t in enumerate(world.terrains) if t in ("world.sea", "world.shallows")]
    sea = np.isin(world.T, sea_ids)
    near = sea.copy()
    # Chebyshev dilation by doubling steps: 1, 2, 4, 8, then the rest.
    step, done = 1, 0
    while done < HEAR:
        k = min(step, HEAR - done)
        grown = near.copy()
        grown[k:, :] |= near[:-k, :]
        grown[:-k, :] |= near[k:, :]
        near = grown
        grown = near.copy()
        grown[:, k:] |= near[:, :-k]
        grown[:, :-k] |= near[:, k:]
        near = grown
        done += k
        step *= 2
    return sea, near


def sea_near(world: World):
    return _cached("sea", world, _sea_near)


def _placed(world: World) -> dict[str, list]:
    """Region -> [(item id, r, c, ph, pw)] of every live item, by the district under its origin."""
    out: dict[str, list] = {}
    for _, it in live_items(world):
        d = int(world.D[it.r, it.c])
        if d < len(world.districts):
            out.setdefault(world.districts[d].split("/", 1)[0], []).append(
                (it.id, it.r, it.c, it.ph, it.pw))
    return out


def placed(world: World, rid: str) -> list:
    return _cached("placed", world, _placed).get(rid, [])


def facts(world: World, rid: str) -> dict:
    """What the checks need of a region from the world: whether the sea is within hearing of its
    tiles and of each district, the placed items and the marsh tiles."""
    _sea, near = sea_near(world)
    names = {i: n.split("/", 1)[1] for i, n in enumerate(world.districts)
             if n.split("/", 1)[0] == rid}
    mine = np.isin(world.D, list(names)) if names else np.zeros(world.D.shape, dtype=bool)
    districts = {n: bool((near & (world.D == i)).any()) for i, n in names.items()}
    marsh_ids = [i for i, t in enumerate(world.terrains) if t == "world.marsh"]
    n = int(mine.sum())
    return {"hears_sea": bool((near & mine).any()), "districts": districts,
            "sea_share": round(float((near & mine).sum()) / n, 3) if n else 0.0,
            "items": {p[0] for p in placed(world, rid)}, "near": near,
            "marsh": int(np.isin(world.T, marsh_ids)[mine].sum())}


ROCKY = 0.6   # share of a coast's shore tiles raised (level 2 and up) or rock


def rocky(world: World, rid: str, district: str) -> float:
    """Share of the shore along a district's sea that is raised above the beach or is rock."""
    name = f"{rid}/{district}"
    if name not in world.districts:
        return 0.0
    sea, _near = sea_near(world)
    s = sea & (world.D == world.districts.index(name))
    g = s.copy()
    g[1:] |= s[:-1]
    g[:-1] |= s[1:]
    g[:, 1:] |= s[:, :-1]
    g[:, :-1] |= s[:, 1:]
    water = np.isin(world.T, [i for i, t in enumerate(world.terrains)
                              if t in ("world.sea", "world.shallows", "world.river", "water",
                                       "rome.river_tiber", "parsa.water_channel")])
    shore = g & ~water & (world.T < len(world.terrains))
    if not shore.any():
        return 0.0
    rock = np.isin(world.T, [i for i, t in enumerate(world.terrains)
                             if any(k in t for k in ("rock", "scree", "crag", "cliff"))])
    return float((((world.L & 0x0F) >= 2) | rock)[shore].mean())


def rect_hears_sea(rect: list[int], near: np.ndarray) -> bool:
    """Whether a grid rect [x0, y0, x1, y1] (inclusive) lies within hearing of the sea."""
    x0, y0, x1, y1 = rect
    r0, r1 = max(0, x0), min(near.shape[0] - 1, x1)
    c0, c1 = max(0, COLS - 1 - y1), min(near.shape[1] - 1, COLS - 1 - y0)
    return bool(near[r0:r1 + 1, c0:c1 + 1].any())


def _grid(c0, r0, c1, r1) -> list[int]:
    return [int(r0), int(COLS - 1 - c1), int(r1), int(COLS - 1 - c0)]


def _chunks(mask: np.ndarray, cell: int, least: int, pad: int):
    """Grid rects of a mask's tiles, one per `cell` × `cell` block holding at least `least`."""
    rows, cols = np.nonzero(mask)
    blocks: dict[tuple[int, int], list] = {}
    for r, c in zip(rows.tolist(), cols.tolist()):
        blocks.setdefault((r // cell, c // cell), []).append((r, c))
    out = []
    for key in sorted(blocks):
        pts = blocks[key]
        if len(pts) < least:
            continue
        rs = [p[0] for p in pts]
        cs = [p[1] for p in pts]
        out.append(_grid(max(0, min(cs) - pad), max(0, min(rs) - pad),
                         min(mask.shape[1] - 1, max(cs) + pad), min(mask.shape[0] - 1, max(rs) + pad)))
    return out


def _merge(rects: list[list[int]], gap: int = 2) -> list[list[int]]:
    """Grid rects merged where they touch (within `gap` tiles)."""
    out = [list(r) for r in rects]
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and \
                        b[1] - gap <= a[3]:
                    out[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    out.pop(j)
                    changed = True
                    break
            if changed:
                break
    return sorted(out)


def zones(doc: dict, world: World, rid: str) -> list[dict]:
    """The zones this module adds: harbours and their oars, streams in the mountains, quarries
    at work, flocks on their pastures."""
    out = []
    idx = {n.split("/", 1)[1]: i for i, n in enumerate(world.districts)
           if n.split("/", 1)[0] == rid}
    _sea, near = sea_near(world)
    if rid not in AUTHORED:
        for d in doc.get("districts", []):
            if d.get("sound", {}).get("water", {}).get("family") != "sea.harbour" or d["id"] not in idx:
                continue
            m = world.D == idx[d["id"]]
            rows, cols = np.nonzero(m)
            rect = _grid(cols.min(), rows.min(), cols.max(), rows.max())
            if not rect_hears_sea(rect, near):
                continue
            if BED_KIND.get(rid) != "harbour_town":
                out.append({"rect": rect, "file": A + "sea.ogg", "gain": 0.8})
            out.append({"rect": rect, "file": W + "oars.ogg", "gain": 0.5,
                        "hours": ["06:30", "17:30"], "months": C.months("mar-oct")})
    if BED_KIND.get(rid) == "mountain":
        river_ids = [i for i, t in enumerate(world.terrains) if t == "world.river"]
        mine = np.isin(world.D, list(idx.values()))
        streams = np.isin(world.T, river_ids) & mine
        for rect in _chunks(streams, 24, 6, 2):
            out.append({"rect": rect, "file": W + "stream.ogg", "gain": 0.8})
    for iid, r, c, ph, pw in placed(world, rid):
        if iid in QUARRIES:
            out.append({"rect": _grid(c - 2, r - 2, c + pw + 1, r + ph + 1),
                        "file": X + "site.ogg", "gain": 0.7, "hours": WORK})
    pastures = [z["rect"] for z in doc.get("zones", []) if z.get("kind") == "pasture"]
    for rect in _merge(pastures):
        out.append({"rect": rect, "file": W + "flock.ogg", "gain": 0.6,
                    "hours": ["07:00", "18:30"]})
    return out


# -- applying ------------------------------------------------------------------------------------

def _force(e: dict, fields: dict) -> None:
    """Give an event these sounds; a different one-shot it had plays at its end instead."""
    old = e.get("sfx")
    for k, v in fields.items():
        e[k] = dict(v) if isinstance(v, dict) else v
    if old and "sfx" in fields and old != fields["sfx"]:
        have = {s["file"] for s in e.get("sounds", [])}
        if old not in have:
            e.setdefault("sounds", []).append({"file": old, "at": "end"})


# Music where no city's piece plays (out/reports/audio-music-world.md §2.5): the travelling
# themes of the land and sea between, and the towns' pieces, day and night. Regions sharing a
# piece (neighbouring stretches, a family's towns) are heard as one: the engine keeps it playing
# across them. The seams have none (their drone is their music).
_TRAVEL = {"italy": ("latium_italy", "apennines"),
           "greece": ("greece", "arcadia", "attica_north", "thrace", "ionia_lydia"),
           "sea": ("tyrrhenian", "adriatic", "ionian_sea", "saronic", "aegean", "persian_gulf"),
           "levant": ("anatolia", "taurus", "east_med", "syrian_steppe"),
           "mesopotamia": ("mesopotamia", "susiana"),
           "iran": ("iran_plateau", "zagros")}
_TOWNS = {"rome/town_forum": ("ostia", "capua"), "rome/town_hills": ("tibur", "beneventum"),
          "rome/town_shrine": ("alban_mount", "brundisium"),
          "athens/town_polis": ("corinth", "olympia", "ephesus"),
          "athens/town_march": ("academy", "sparta"),
          "athens/town_sanctuary": ("delphi", "delos"),
          "athens/town_harbour": ("eleusis", "corcyra"),
          "parsa/town_court": ("susa", "pasargadae"), "parsa/town_caravan": ("persian_gates", "halys"),
          "parsa/town_west": ("sardis", "sidon"),
          "parsa/town_river": ("babylon", "euphrates_crossing", "gordion")}
MUSIC = {rid: {"day": f"music/world/travel_{k}_day.ogg", "night": f"music/world/travel_{k}_night.ogg"}
         for k, rids in _TRAVEL.items() for rid in rids}
MUSIC.update({rid: {"day": f"music/{k}_day.ogg", "night": f"music/{k}_night.ogg"}
              for k, rids in _TOWNS.items() for rid in rids})


def apply(doc: dict, world: World, cat, root) -> dict:
    from . import sound
    from .places import side as side_of
    rid = doc["id"]
    kind, set_, *_ = P.REGIONS.get(rid, ("stretch", "world", None, None, 0))
    side = side_of(rid) or set_
    climate = sound.climate_of(rid)
    th = doc.setdefault("theme", {})
    amb = th.setdefault("ambience", {})
    amb.setdefault("loops", [])   # beds, loops, zones: the order the files have always had
    seasons = th.setdefault("seasons", {})
    if rid in MUSIC:
        th["music"] = dict(MUSIC[rid])
    f = facts(world, rid)
    # Beds: the place's own, by season and hour.
    if rid not in AUTHORED:
        clim = next((c for c in C.CLIMATES if c["id"] == C.REGION_CLIMATE.get(rid)), {})
        rows = (clim.get("water") or {}).get("river") or []
        flood = [MONTHS[i] for i, lv in enumerate(rows) if lv == "flood"]
        plain, by_season = beds_for(BED_KIND[rid], flood, f["marsh"] > 40)
        amb["beds"] = plain
        for s in C.SEASONS:
            e = seasons.setdefault(s, {})
            if by_season.get(s):
                e["ambience"] = {"beds": [dict(b) for b in by_season[s]]}
            else:
                e.pop("ambience", None)
    # Zones.
    have = {(z["file"], tuple(z["rect"])) for z in amb.get("zones", [])}
    new = [z for z in zones(doc, world, rid)
           if (z["file"], tuple(z["rect"])) not in have]
    if new:
        amb["zones"] = amb.get("zones", []) + new
    # Loops on placed kinds: every one that sounds, timed; a role that works the item with a loop
    # of the same file is its sound instead.
    worked = {(r.get("home", {}).get("item"), r.get("sound", {}).get("loop"))
              for r in doc.get("roles", []) if r.get("sound", {}).get("loop")}
    loops = []
    keep = [x for x in amb.get("loops", []) if "item" not in x]
    for iid in sorted(f["items"]):
        for file, when, hours, months in item_loops(iid):
            if (iid, file) not in worked:
                loops.append(loop_entry(iid, file, when, hours, months))
    amb["loops"] = keep + loops
    # The sound character: nature by season and snow, calls, the season's sting.
    snd = th.setdefault("sound", {})
    ns = nature_seasons(climate)
    if ns:
        snd["nature_seasons"] = ns
        if snows(rid):
            snd["nature_snow"] = {"day": W + "day_snow.ogg", "night": W + "night_snow.ogg"}
        else:
            snd.pop("nature_snow", None)
    leaves = max([d.get("sound", {}).get("surfaces", {}).get("leaves", 0)
                  for d in doc.get("districts", [])] or [0])
    people = kind in ("city", "town", "home") or any(
        r.get("id") in ("townsfolk", "farmer", "shepherd") for r in doc.get("roles", []))
    road = any(d.get("area") == "road" for d in doc.get("districts", []))
    snd["calls"] = calls(rid, climate, f["sea_share"] >= 0.25, leaves >= 0.05, people, road)
    if "stings" in snd and rid != "corner":
        snd["stings"]["season"] = (f"sfx/{side}/sting_season.wav"
                                   if side in ("rome", "athens", "parsa")
                                   else "sfx/world/sting_season.wav")
    # Shores: waves on rocks where most of a coast's shore stands raised or is rock.
    for d in doc.get("districts", []):
        w = d.get("sound", {}).get("water")
        if w and w.get("family") == "sea.coast" and rocky(world, rid, d["id"]) >= ROCKY:
            w["family"] = "sea.rocks"
    # Mountain streams play as zones; the district's water family stays for real rivers only.
    if BED_KIND.get(rid) == "mountain":
        for d in doc.get("districts", []):
            w = d.get("sound", {}).get("water")
            if w and w.get("family") == "river":
                d["sound"].pop("water")
    # Festivals, turns and work.
    for e in doc.get("events", []):
        t = e.get("turn")
        if t in TURN_SOUNDS:
            if e.get("sfx") == STAND_IN:   # the stand-in gives way to the recorded cue
                e.pop("sfx")
            for k, v in TURN_SOUNDS[t].items():
                e[k] = dict(v) if isinstance(v, dict) else v
            e.pop("pending_sound", None)
            continue
        for pat, fields in FESTIVAL_SOUNDS:
            if re.search(pat, e["id"]):
                _force(e, fields)
                break
    for r in doc.get("roles", []):
        for pat, s in ROLE_LOOPS:
            if re.search(pat, r["id"]):
                r["sound"] = dict(s)
                break
    return doc


# -- checking ------------------------------------------------------------------------------------

def _hour(s: str) -> float:
    h, m = s.split(":")
    return int(h) + int(m) / 60


def _in(h: float, hours) -> bool:
    if not hours:
        return True
    a, b = _hour(hours[0]), _hour(hours[1])
    return a <= h < b if a <= b else (h >= a or h < b)


def beds_at(doc: dict, season: str, month: str, hour: float, rain: bool = False) -> list[str]:
    """The beds the engine plays (world/soundscape.cpp `plays`): a season's own beds replace the
    plain ones for the hours and months they cover."""
    th = doc.get("theme", {})
    plain = th.get("ambience", {}).get("beds", [])
    own = (th.get("seasons", {}).get(season, {}).get("ambience") or {}).get("beds", [])
    inm = lambda b: not b.get("months") or month in b["months"]
    wet = lambda b: b.get("weather") == "rain"
    out = [b["file"] for b in own if _in(hour, b.get("hours")) and inm(b) and (rain or not wet(b))]
    covered = any(_in(hour, b.get("hours")) and inm(b) and not wet(b) for b in own)
    for b in plain:
        if not _in(hour, b.get("hours")) or (wet(b) and not rain):
            continue
        if wet(b) or not covered:
            out.append(b["file"])
    return out


HOURS = [h / 2 for h in range(48)]


def check(doc: dict) -> list[tuple[str, str, str]]:
    """[(level, where, message)] on the document alone: a bed for every month and hour, no
    nature bed among the place's beds, festival and work loops tied to what exists."""
    out = []
    for s, ms in SEASON_MONTHS.items():
        for m in ms:
            for h in HOURS:
                if not beds_at(doc, s, m, h):
                    out.append(("error", "theme.ambience",
                                f"no bed plays in {m} ({s}) at {int(h):02d}:{int(h % 1 * 60):02d}"))
                    break
    th = doc.get("theme", {})
    for b in th.get("ambience", {}).get("beds", []) + [
            b for e in th.get("seasons", {}).values()
            for b in (e.get("ambience") or {}).get("beds", [])]:
        if b["file"] in NATURE_FILES:
            out.append(("error", "theme.ambience", f"{b['file']} is a nature bed (theme.sound."
                        "nature*): a place's bed beside it would play the same loop twice"))
        for m in b.get("months", []):
            if m not in MONTHS:
                out.append(("error", "theme.ambience", f"{b['file']}: unknown month {m!r}"))
    fests = {f.get("id") for f in doc.get("festivals", [])}
    for e in doc.get("events", []):
        files = [(e.get("ambience") or {}).get("file", ""), e.get("sfx") or ""]
        if not any(f in FESTIVAL_FILES for f in files):
            continue
        t = e.get("trigger") or {}
        if not t:
            out.append(("error", f"event {e['id']}", "festival music on an event with no "
                        "trigger: it would never play"))
        elif t.get("festival") and t["festival"] not in fests:
            out.append(("error", f"event {e['id']}", f"festival music on festival "
                        f"{t['festival']!r}, which the region does not hold"))
        for m in t.get("months", []):
            if m not in MONTHS:
                out.append(("error", f"event {e['id']}", f"unknown month {m!r}"))
    for x in th.get("ambience", {}).get("loops", []) + th.get("ambience", {}).get("zones", []):
        where = f"loop {x.get('item') or x.get('slot')}" if "rect" not in x else f"zone {x.get('file')}"
        # A slot's loop sounds while its role works it (the role's hours); an item's needs its own.
        if "item" in x and x.get("when") == "worked" and not x.get("hours"):
            out.append(("error", where, "a worked loop needs its working hours"))
        hrs = x.get("hours")
        if hrs and (len(hrs) != 2 or not all(re.fullmatch(r"\d\d:\d\d", h) for h in hrs)):
            out.append(("error", where, f"hours {hrs!r} are not [hh:mm, hh:mm]"))
        for m in x.get("months", []):
            if m not in MONTHS:
                out.append(("error", where, f"unknown month {m!r}"))
    for r in doc.get("roles", []):
        lp = r.get("sound", {}).get("loop", "")
        if lp in (W + "reaping.ogg", W + "ploughing.ogg", W + "vintage.ogg",
                  W + "olive_harvest.ogg") and not _populated(doc, r["id"]):
            out.append(("error", f"role {r['id']}", f"{lp} on a role no district holds"))
    return out


def _populated(doc: dict, role: str) -> bool:
    return any(p.get("role") == role for d in doc.get("districts", [])
               for p in d.get("populations", []))


def check_world(doc: dict, f: dict) -> list[tuple[str, str, str]]:
    """[(level, where, message)] against the world's facts (`facts`): no sea or shore sound out
    of hearing of the sea, every placed workplace that has a loop names it, loops on items the
    region holds."""
    out = []
    th = doc.get("theme", {})
    amb = th.get("ambience", {})
    sea_beds = [b["file"] for b in amb.get("beds", []) + [
        b for e in th.get("seasons", {}).values()
        for b in (e.get("ambience") or {}).get("beds", [])] if b["file"] in SEA_BEDS - {R + "river.ogg"}]
    if sea_beds and not f["hears_sea"]:
        out.append(("error", "theme.ambience", f"sea bed {sea_beds[0]} in a region with no sea "
                    f"within {HEAR} tiles"))
    for z in amb.get("zones", []):
        if z["file"] in SEA_BEDS - {R + "river.ogg"} and "near" in f and \
                not rect_hears_sea(z["rect"], f["near"]):
            out.append(("error", f"zone {z['file']}", f"rect {z['rect']} has no sea within "
                        f"{HEAR} tiles"))
    for d in doc.get("districts", []):
        fam = (d.get("sound", {}).get("water") or {}).get("family", "")
        if fam.startswith("sea.") and not f["districts"].get(d["id"], False):
            out.append(("error", f"district {d['id']}", f"{fam} with no sea within {HEAR} tiles"))
    loops = {(x.get("item"), x.get("file")) for x in amb.get("loops", [])}
    by_role = {(r.get("home", {}).get("item"), r.get("sound", {}).get("loop"))
               for r in doc.get("roles", [])}
    for iid in sorted(f["items"]):
        for file, _when, _h, _m in item_loops(iid):
            if (iid, file) not in loops and (iid, file) not in by_role:
                out.append(("error", f"item {iid}", f"is placed here and sounds ({file}), but "
                            "no loop or working role names it"))
    for iid, file in sorted(x for x in loops if x[0]):
        if iid not in f["items"]:
            out.append(("error", f"loop {iid}", f"{file} on an item the region does not hold"))
    return out
