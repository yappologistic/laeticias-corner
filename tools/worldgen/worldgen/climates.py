"""The seasons' data (docs/design/seasons.md): one world calendar of twelve months, the fifteen
climates, which climate each region has, which climates may meet, the turns of the seasons, and
which plants, grounds and walkers change with them.

This module is the source of the catalogs' seasonal fields: `build.sh --seasons` writes
`calendar` and `climates` into `assets/catalog.json` and the seasonal fields of the set catalogs
(`season_class`, `plain_state`, `season_states`, `bloom`, `fruit`, `snow_look`, `snow_catch`,
`art.overlays`, `art.backdrop_snow`), touching nothing else in those files. Everything else in
the tool (region files, checks, reports) reads the catalogs, so the catalog is the contract.

Arrays of twelve run March to February (index 0 = March): one calendar day is one month,
`month = day mod 12` (seasons.md §1.2).
"""

from __future__ import annotations

MONTHS = ["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "jan", "feb"]
MONTH_NAMES = ["March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December", "January", "February"]
SEASONS = ["spring", "summer", "autumn", "winter"]
CLASSES = ["grass", "crop", "deciduous", "early_bloom", "vine", "reed", "wildflower", "evergreen"]
STATES = ["fresh", "green", "dry", "dormant", "bloom", "turn", "bare", "fruit", "ploughed",
          "sprout", "ripe", "stubble", "snow", "gone", "spring", "summer", "autumn", "winter"]
WATER_LEVELS = ["flood", "high", "normal", "low", "dry"]


def months(*names: str) -> list[str]:
    """Month ids from names or 'a-b' spans (wrapping over the year's end: 'nov-feb')."""
    out: list[str] = []
    for n in names:
        if "-" in n:
            a, b = (MONTHS.index(x) for x in n.split("-"))
            i = a
            while True:
                out.append(MONTHS[i])
                if i == b:
                    break
                i = (i + 1) % 12
        else:
            out.append(n)
    return out


def row(spec: str) -> list[str]:
    """Twelve states from the design's letters (seasons.md §2.3), March first."""
    letters = {"F": "fresh", "G": "green", "D": "dry", "O": "dormant", "B": "bloom", "T": "turn",
               "X": "bare", "W": "fruit", "P": "ploughed", "S": "sprout", "R": "ripe",
               "U": "stubble", "N": "gone"}
    out = [letters[c] for c in spec.split()]
    assert len(out) == 12, spec
    return out


def by_month(values: dict[str, float], default: float = 0.0) -> list[float]:
    out = [default] * 12
    for k, v in values.items():
        for m in months(k):
            out[MONTHS.index(m)] = v
    return out


def feel(t: float) -> str:
    return "freezing" if t < 1 else "cold" if t < 7 else "cool" if t < 13 else \
        "mild" if t < 19 else "warm" if t < 25 else "hot"


# -- the calendar ------------------------------------------------------------------------------

# The turns of the seasons (seasons.md §5.3): an event at the first dawn of a season (or of a
# month, where a region names one), with what the engine shows and plays. `fx`/`sfx` name art and
# audio; ones not drawn or recorded yet are listed in assets/world/season-needs.json.
TURNS = {
    "season": {"show": "home", "sfx": "sfx/season.wav",
               "note": "the home corner's own turn: its sting and Laeticia's line"},
    "swallows_return": {"show": "flock", "actor": "world.swift", "sfx": "sfx/world/swifts.wav"},
    "storks_arrive": {"show": "flock", "actor": "world.stork", "sfx": "sfx/world/stork_clatter.wav"},
    "cranes_overhead": {"show": "sky_flock", "fx": "fx/world.crane_flock",
                        "sfx": "sfx/world/cranes.wav"},
    "cicadas_begin": {"show": "emitter", "sound": "cicadas"},
    "first_rains": {"show": "weather", "weather": "front", "sfx": "sfx/world/first_drops.wav"},
    "first_snow": {"show": "weather", "weather": "snow", "sting": "first_snow"},
    "first_frost": {"show": "ground", "ground": "frost"},
    "first_dust": {"show": "weather", "weather": "dust", "fx": "fx/world.dust_puff"},
    "heat_haze": {"show": "look", "look": "shimmer", "fx": "fx/world.shimmer"},
    "flood_rising": {"show": "water", "water": "flood", "ambience": "amb/world/flood.ogg"},
    "snowmelt": {"show": "water", "water": "high", "ambience": "amb/world/river_2.ogg"},
    "braziers_lit": {"show": "item_state", "state": "lit", "ambience": "amb/world/brazier.ogg"},
    "ships_hauled_ashore": {"show": "harbour", "props": ["world.hull_ashore"],
                            "sfx": "sfx/world/rope.wav"},
    "sailing_opens": {"show": "harbour", "sfx": "sfx/world/rope.wav"},
    "storms_return": {"show": "weather", "weather": "storm", "sfx": "sfx/world/thunder_far.wav"},
    "meltemi": {"show": "weather", "weather": "wind", "sfx": "sfx/world/gust_front.wav"},
    "shamal": {"show": "weather", "weather": "dust", "sfx": "sfx/world/gust_front.wav"},
    "vintage_begins": {"show": "work", "work": "vintage", "ambience": "amb/world/press.ogg"},
    "ploughing_begins": {"show": "work", "work": "ploughing", "sfx": "sfx/world/hoof_earth_1.wav"},
    "date_harvest": {"show": "work", "work": "dates_harvest", "sfx": "sfx/world/chop.wav"},
    "flocks_up": {"show": "herd", "sfx": "sfx/world/sheep_bells.wav"},
    "flocks_down": {"show": "herd", "sfx": "sfx/world/sheep_bells.wav"},
    "leaves_turn": {"show": "particles", "fx": "fx/world.leaf"},
    "first_green": {"show": "ground", "ground": "fresh", "sfx": "sfx/world/cuckoo.wav"},
    "court_leaves": {"show": "procession", "sfx": "sfx/parsa/horn.wav"},
}

DAY_SHIFT = [0, 0.3, 0.55, 0.67, 0.6, 0.35, 0.08, -0.22, -0.47, -0.62, -0.55, -0.3]
DAYLIGHT = [12.0, 13.2, 14.2, 14.7, 14.4, 13.4, 12.3, 11.1, 10.1, 9.5, 9.8, 10.8]
# Noon shadow length factor (look.md §2.3's 0.7 at the equinox's neighbours): 0.55 in June,
# 1.15 in December, a cosine between them (seasons.md §3.11).
NOON_SHADOW = [0.85, 0.7, 0.59, 0.55, 0.59, 0.7, 0.85, 1.0, 1.11, 1.15, 1.11, 1.0]


def calendar() -> dict:
    return {
        "rule": "month = day mod 12 (0 = March); season = (day / 3) mod 4; season day = day mod 3 + 1",
        "months": [{"id": m, "name": n, "season": SEASONS[i // 3], "day": i % 3 + 1}
                   for i, (m, n) in enumerate(zip(MONTHS, MONTH_NAMES))],
        "daylight": DAYLIGHT, "day_shift": DAY_SHIFT, "noon_shadow": NOON_SHADOW,
        "wave": {"items": ["06:00", "16:00"], "ground": ["07:00", "09:30", "12:00", "14:30"],
                 "fade_s": 0.8, "pinned_s": 3},
        "turns": TURNS,
    }


# -- the climates ------------------------------------------------------------------------------

def _dress(cold: dict, hot: dict) -> dict:
    return {"cold": by_month(cold), "hot": by_month(hot)}


DRESS_MED = _dress({"mar": 0.35, "nov": 0.35, "dec-feb": 0.7}, {"jun-aug": 0.4})
DRESS_HIGH = _dress({"mar-apr": 0.35, "oct-nov": 0.35, "dec-feb": 0.7}, {"jun-aug": 0.25})
DRESS_HOT = _dress({"nov": 0.2, "dec-feb": 0.5}, {"may": 0.3, "jun-aug": 0.5, "sep": 0.3})
ROAD_WINTER = by_month({"nov": 0.85, "dec-feb": 0.7}, 1.0)
CARAVAN_MOUNTAIN = [0.6, 0.9, 1, 1, 1, 1, 1, 0.9, 0.6, 0.3, 0.2, 0.3]


def _temps(*t: float) -> dict:
    return {"temp": list(t), "feel": [feel(x) for x in t]}


CLIMATES: list[dict] = [
    {"id": "home", "name": "The corner",
     "character": "cool, green and northern: the corner's own seasons",
     "classes": {c: ["spring"] * 3 + ["summer"] * 3 + ["autumn"] * 3 + ["winter"] * 3
                 for c in CLASSES if c != "evergreen"} | {"evergreen": ["green"] * 12},
     # Set pieces standing in the corner's surroundings (reeds by the dell's stream, the
     # world's trees) turn as a cool northern place: their own states, not the home's names.
     "set_classes": {"grass": row("F F F G G G G G G O O O"), "crop": row("S G G G R U P S S S S S"),
                     "deciduous": row("X F G G G G G T T X X X"),
                     "early_bloom": row("B F G G G G G T X X X X"),
                     "vine": row("X F G G G W W T X X X X"), "reed": row("D G G G G G G D D D D D"),
                     "wildflower": row("G B B G G D N N N N N G"), "evergreen": ["green"] * 12},
     # A snowy winter by the corner's own design (its rain falls as snow December to February).
     **_temps(7, 10, 14, 17, 19, 19, 16, 12, 7, 1, -1, 0),
     "snow": {"rule": "home", "line": [None] * 9 + [0, 0, 0], "perma": None,
              "settle": 0.03, "melt": 0.006,
              "note": "winter rain falls as snow (the home catalog's rain_as)"},
     "frost": months("dec-feb"), "frost_hours": ["03:00", "09:00"],
     "water": {"pond": ["high", "high", "high", "normal", "normal", "normal", "normal", "normal",
                        "normal", "normal", "normal", "normal"],
               "ice": {"months": ["jan"], "hours": ["00:00", "12:00"], "rim": True,
                       "note": "rim ice on winter day 2; the middle stays open for the ducks"}},
     "weather": {"spring": {"showers": 0.6, "clouds": 1.2, "wind": 0.35},
                 "summer": {"showers": 0.15, "clouds": 0.6, "wind": 0.2},
                 "autumn": {"showers": 0.7, "clouds": 1.4, "wind": 0.6},
                 "winter": {"showers": 0.5, "clouds": 1.0, "wind": 0.4, "snow": True}},
     "grade": {"spring": [0.98, 1.02, 0.96], "summer": [1.03, 1.0, 0.94],
               "autumn": [1.06, 0.96, 0.86], "winter": [0.9, 0.95, 1.06]},
     "dress": _dress({}, {}),
     "turn_events": {s: "season" for s in SEASONS},
     "fauna": {"swallows": months("apr-sep"), "frogs": months("mar-may"),
               "fireflies": months("jun-sep"), "bees": months("mar-oct")}},

    {"id": "med_green", "name": "Green Mediterranean",
     "character": "a green spring and early summer, gold late summer, a mild wet winter; snow only on the hills",
     "classes": {"grass": row("F F F G D D D G G G G G"), "crop": row("G G G R R U U P P S S G"),
                 "deciduous": row("X F G G G G G G T X X X"),
                 "early_bloom": row("B F G G G G G G T X X B"),
                 "vine": row("X F G G G W W T T X X X"), "reed": row("D G G G G G G G D D D D"),
                 "wildflower": row("G B B D N N N N G G G G"), "evergreen": ["green"] * 12},
     **_temps(11, 14, 18, 22, 25, 25, 21, 17, 12, 9, 8, 9),
     "snow": {"line": [12, None, None, None, None, None, None, None, None, 10, 9, 9], "perma": None,
              "settle": 0.02, "melt": 0.01,
              "lowland": {"months": months("dec-feb"), "chance": 0.2, "settle": True,
                          "melt_by": "12:00", "note": "a rare dusting on a winter morning"},
              "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": [], "frost_hours": ["03:00", "09:00"],
     "wet_floor": {"months": months("nov-mar"), "value": 0.3,
                   "terrain": ["road_earth", "packed_earth", "mud_bank"]},
     "dust": {"months": []},
     "water": {"river": ["high", "normal", "normal", "low", "low", "low", "low", "normal", "high",
                         "flood", "flood", "flood"],
               "river_rank": by_month({"dec-feb": 1}, 0),
               "stream": ["high", "normal", "normal", "low", "low", "low", "low", "normal",
                          "normal", "high", "high", "high"],
               "channel": ["normal"] * 12, "lake": ["normal"] * 12,
               "colour": {"flood": [1.08, 1.0, 0.8], "high": [1.08, 1.0, 0.8],
                          "normal": [1.0, 1.0, 1.0], "low": [0.96, 1.02, 0.92]}},
     "travel": {"road": ROAD_WINTER, "caravan": ROAD_WINTER, "courier": 1,
                "barge": by_month({"nov-mar": 0.5}, 1.0)},
     "weather": {"spring": {"showers": 2, "clouds": 2, "wind": 0.35, "wind_from": "west", "fog": 0.3},
                 "summer": {"showers": 0, "clouds": 1, "wind": 0.3, "storm": 1},
                 "autumn": {"showers": 3, "clouds": 3, "wind": 0.4},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.45, "snow": True},
                 "months": {"sep": {"showers": 1, "clouds": 2}}},
     "grade": {"spring": [0.99, 1.02, 0.97], "summer": [1.04, 1.0, 0.92],
               "autumn": [1.05, 0.97, 0.88], "winter": [0.94, 0.97, 1.04]},
     "look": {"summer": {"haze": 0.25, "warmth": 0.04}, "winter": {"saturation": -0.06, "haze": 0.2}},
     "dress": DRESS_MED, "coast": "sea_west",
     "turn_events": {"spring": "swallows_return", "summer": "cicadas_begin",
                     "autumn": "vintage_begins", "winter": "braziers_lit"},
     "fauna": {"swallows": months("mar-sep"), "swifts": months("apr-aug"),
               "storks": months("mar-aug"), "cranes_pass": months("mar", "oct-nov"),
               "starlings": months("oct-feb"), "geese": months("nov-feb"),
               "cicadas": months("jun-sep"), "frogs": months("mar-may"),
               "nightingales": months("apr-jun"), "fireflies": ["jun"],
               "bees": months("mar-oct"), "lambs": months("jan-mar")},
     "work": {"pruning": months("feb-mar"), "ploughing": months("oct-nov"),
              "harvest": months("jun-jul"), "threshing": ["jul"], "hay": ["jun"],
              "shearing": ["may"], "vintage": months("sep-oct"), "olive": months("nov-dec"),
              "charcoal": months("dec-feb"), "wool": months("dec-feb"),
              "shipyard": months("dec-feb"), "building": by_month({"dec-feb": 0.6}, 1.0)}},

    {"id": "med_dry", "name": "Attic Mediterranean",
     "character": "the driest: hills gold and grey from June to October, green from November to April; snow on the mountains",
     "classes": {"grass": row("F F G D D D D D G G G F"), "crop": row("G G R U U U U P P S G G"),
                 "deciduous": row("F G G G G G G G T X X X"),
                 "early_bloom": row("F G G G G G G G T X B B"),
                 "vine": row("X F G G G W W T T X X X"), "reed": row("D G G G G G G G D D D D"),
                 "wildflower": row("B B D D D D D D G G G B"), "evergreen": ["green"] * 12},
     **_temps(13, 16, 21, 26, 28, 28, 24, 19, 15, 12, 10, 11),
     "snow": {"line": [13, None, None, None, None, None, None, None, None, 11, 9, 10], "perma": None,
              "settle": 0.02, "melt": 0.012,
              "lowland": {"months": months("dec-feb"), "chance": 0.15, "settle": False,
                          "settle_on": ["athens.rock_limestone"], "hours": 2,
                          "note": "flurries that do not settle, but on the Acropolis rock tops for two hours"},
              "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": [], "frost_hours": ["03:00", "09:00"],
     "wet_floor": {"months": months("nov-mar"), "value": 0.3,
                   "terrain": ["road_earth", "packed_earth", "mud_bank"]},
     "dust": {"months": months("jun-oct")},
     "water": {"stream": ["high", "low", "dry", "dry", "dry", "dry", "dry", "dry", "low", "high",
                          "high", "high"],
               "river": ["normal", "normal", "low", "low", "low", "low", "low", "low", "normal",
                         "high", "high", "high"],
               "channel": ["normal"] * 12, "lake": ["normal"] * 12,
               "colour": {"high": [1.02, 1.01, 0.96], "normal": [1.0, 1.0, 1.0]}},
     "travel": {"road": ROAD_WINTER, "caravan": ROAD_WINTER, "courier": 1},
     "weather": {"spring": {"showers": 1, "clouds": 2, "wind": 0.35},
                 "summer": {"showers": 0, "clouds": 1, "wind": 0.5, "wind_from": "north-east",
                            "dust": 1, "storm": 1},
                 "autumn": {"showers": 2, "clouds": 3, "wind": 0.4},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.4, "snow": True},
                 "months": {"jun": {"wind": 0.35, "wind_from": "north"},
                            "sep": {"showers": 0, "clouds": 1, "dust": 1}}},
     "grade": {"spring": [1.0, 1.02, 0.96], "summer": [1.06, 1.01, 0.9],
               "autumn": [1.03, 0.98, 0.92], "winter": [0.93, 0.98, 1.03]},
     "look": {"summer": {"exposure": 0.04, "contrast": 0.05, "saturation": -0.04},
              "winter": {"foliage_saturation": 0.06}},
     "dress": DRESS_MED, "coast": "sea_aegean",
     "turn_events": {"spring": "swallows_return", "summer": "cicadas_begin",
                     "autumn": "vintage_begins", "winter": "braziers_lit"},
     "month_turns": {"oct": "first_rains", "nov": "cranes_overhead"},
     "fauna": {"swallows": months("mar-sep"), "swifts": months("apr-aug"),
               "cranes_pass": months("mar", "oct-nov"), "cicadas": months("jun-sep"),
               "frogs": months("mar-may"), "nightingales": months("apr-jun"),
               "bees": months("mar-oct"), "lambs": months("jan-mar")},
     "work": {"pruning": ["feb"], "ploughing": months("oct-nov"), "harvest": months("may-jun"),
              "threshing": months("jun-jul"), "shearing": months("apr-may"), "vintage": ["sep"],
              "olive": months("nov-jan"), "charcoal": months("dec-feb"),
              "wool": months("dec-feb"), "shipyard": months("dec-feb"),
              "building": by_month({"dec-feb": 0.6}, 1.0)}},

    {"id": "highland", "name": "Mediterranean highland", "inherits": "med_green",
     "character": "beech and oak woods, snowy winters, summer pastures",
     "classes": {"grass": row("O F F F G D D G O O O O"), "crop": row("S G G G R U P S S S S S"),
                 "deciduous": row("X X F G G G G T X X X X"),
                 "early_bloom": row("X B F G G G G T X X X X"),
                 "vine": row("X X F G G G W T X X X X"), "reed": row("D D G G G G G D D D D D"),
                 "wildflower": row("N N B B G D D N N N N N")},
     **_temps(3, 7, 11, 15, 18, 18, 15, 10, 6, 2, 1, 1),
     "snow": {"line": [9, 11, 13, 15, None, None, None, 14, 11, 8, 7, 7], "perma": None,
              "settle": 0.03, "melt": 0.004, "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": months("nov-mar"), "frost_hours": ["03:00", "09:00"],
     "wet_floor": {"months": months("mar-apr", "oct-nov"), "value": 0.3,
                   "terrain": ["road_earth", "packed_earth"]},
     "dust": {"months": []},
     "water": {"stream": ["high", "high", "high", "normal", "low", "low", "low", "normal", "normal",
                          "normal", "normal", "normal"],
               "river": ["high", "high", "high", "normal", "low", "low", "low", "normal", "normal",
                         "normal", "normal", "normal"],
               "ice": {"months": months("dec-feb"), "hours": ["00:00", "11:00"], "margins": True},
               "colour": {"high": [1.0, 1.04, 1.04]}},
     "travel": {"road": [0.7, 0.9, 1, 1, 1, 1, 1, 1, 0.8, 0.5, 0.4, 0.5],
                "caravan": [0.7, 0.9, 1, 1, 1, 1, 1, 1, 0.8, 0.5, 0.4, 0.5], "courier": 1},
     "weather": {"spring": {"showers": 2, "clouds": 3, "wind": 0.4, "fog": 0.5},
                 "summer": {"showers": 1, "clouds": 2, "wind": 0.35, "storm": 2},
                 "autumn": {"showers": 2, "clouds": 3, "wind": 0.4, "fog": 0.6},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.5, "snow": True}},
     "grade": {"spring": [0.98, 1.02, 0.98], "summer": [1.02, 1.0, 0.95],
               "autumn": [1.04, 0.96, 0.88], "winter": [0.9, 0.95, 1.08]},
     "look": {"winter": {"warmth": -0.06, "fog": 0.3}, "autumn": {"fog": 0.3}},
     "dress": _dress({"mar": 0.35, "nov": 0.35, "dec-feb": 0.7}, {"jun-aug": 0.2}),
     "turn_events": {"spring": "snowmelt", "summer": "flocks_up",
                     "autumn": "flocks_down", "winter": "first_snow"},
     "month_turns": {"apr": "swallows_return", "oct": "leaves_turn"},
     "fauna": {"swallows": months("apr-sep"), "eagles": months("mar-feb"),
               "frogs": months("apr-jun"), "bees": months("apr-sep"), "lambs": months("feb-apr"),
               "cicadas": months("jul-aug")},
     "work": {"pruning": ["mar"], "ploughing": months("sep-oct"), "harvest": ["jul"],
              "threshing": ["aug"], "hay": ["jul"], "shearing": ["may"], "vintage": ["sep"],
              "charcoal": months("oct-nov"), "wool": months("dec-feb")},
     "transhumance": {"up": ["may"], "high": months("jun-sep"), "down": ["oct"],
                      "low": months("nov-apr")}},

    {"id": "thracian", "name": "Thracian", "inherits": "med_green",
     "character": "continental north Aegean: cold winters with snow on the plain, green summers",
     "classes": {"grass": row("O F F G G D D G O O O O"), "crop": row("S G G G R U P S S S S S"),
                 "deciduous": row("X F G G G G G T X X X X"),
                 "early_bloom": row("X B F G G G G T X X X X"),
                 "vine": row("X X F G G W W T X X X X"), "reed": row("D D G G G G G D D D D D"),
                 "wildflower": row("N B B G D D N N N N N N")},
     **_temps(6, 11, 16, 21, 24, 24, 20, 15, 10, 6, 4, 5),
     "snow": {"line": [7, None, None, None, None, None, None, None, 9, 4, 2, 3], "perma": None,
              "settle": 0.03, "melt": 0.006, "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": months("nov-mar"), "frost_hours": ["03:00", "09:00"],
     "wet_floor": {"months": months("mar-apr", "nov-feb"), "value": 0.3,
                   "terrain": ["road_earth", "packed_earth"]},
     "dust": {"months": []},
     "water": {"river": ["high", "high", "normal", "normal", "low", "low", "low", "normal",
                         "normal", "high", "high", "high"],
               "ice": {"months": ["jan"], "hours": ["00:00", "10:00"], "margins": True}},
     "travel": {"road": by_month({"nov": 0.8, "dec-feb": 0.6}, 1.0),
                "caravan": by_month({"nov": 0.8, "dec-feb": 0.6}, 1.0), "courier": 1},
     "weather": {"spring": {"showers": 2, "clouds": 3, "wind": 0.35},
                 "summer": {"showers": 1, "clouds": 2, "wind": 0.35},
                 "autumn": {"showers": 2, "clouds": 3, "wind": 0.4},
                 "winter": {"showers": 2, "clouds": 4, "wind": 0.6, "wind_from": "north",
                            "snow": True}},
     "grade": {"spring": [0.98, 1.02, 0.98], "summer": [1.02, 1.0, 0.95],
               "autumn": [1.04, 0.96, 0.88], "winter": [0.9, 0.95, 1.08]},
     "look": {"winter": {"warmth": -0.06, "fog": 0.2}},
     "dress": DRESS_MED, "coast": "sea_aegean",
     "turn_events": {"spring": "storks_arrive", "summer": "cicadas_begin",
                     "autumn": "cranes_overhead", "winter": "first_snow"},
     "fauna": {"storks": months("mar-aug"), "swallows": months("apr-sep"),
               "cranes_pass": months("mar", "oct-nov"), "cicadas": months("jul-aug"),
               "frogs": months("apr-may"), "lambs": months("feb-mar"), "bees": months("apr-sep")},
     "work": {"pruning": ["mar"], "ploughing": months("sep-oct"), "harvest": ["jul"],
              "threshing": ["aug"], "shearing": ["may"], "vintage": ["sep"],
              "charcoal": months("oct-nov"), "wool": months("dec-feb")}},

    {"id": "levant", "name": "Levantine coast", "inherits": "med_dry",
     "character": "a green coast under snowy mountains (the cedars)",
     **_temps(16, 19, 22, 25, 27, 28, 27, 24, 20, 17, 14, 15),
     "snow": {"line": [9, 12, None, None, None, None, None, None, 13, 10, 8, 8], "perma": None,
              "settle": 0.03, "melt": 0.006, "on": ["ground", "evergreen", "backdrop"]},
     "weather": {"spring": {"showers": 1, "clouds": 2, "wind": 0.3},
                 "summer": {"showers": 0, "clouds": 0, "wind": 0.4, "wind_from": "west"},
                 "autumn": {"showers": 1, "clouds": 2, "wind": 0.3},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.45, "snow": True},
                 "months": {"sep": {"showers": 0, "clouds": 1}}},
     "dress": _dress({"mar": 0.2, "nov": 0.2, "dec-feb": 0.5}, {"jun-aug": 0.4}),
     "turn_events": {"spring": "swallows_return", "summer": "cicadas_begin",
                     "autumn": "vintage_begins", "winter": "first_snow"},
     "month_turns": {"oct": "first_rains"}},

    {"id": "anatolian", "name": "Anatolian plateau", "inherits": "med_green",
     "character": "a high continental plateau: long snowy winters, a short green spring, gold steppe summers",
     "classes": {"grass": row("O F F G D D D D O O O O"), "crop": row("S G G G R U P S S S S S"),
                 "deciduous": row("X F G G G G G T X X X X"),
                 "early_bloom": row("X B F G G G G T X X X X"),
                 "vine": row("X X F G G G W T X X X X"), "reed": row("D D G G G G G D D D D D"),
                 "wildflower": row("N B B D N N N N N N N N")},
     **_temps(4, 10, 15, 19, 23, 23, 18, 12, 6, 1, -1, 1),
     "snow": {"line": [8, 11, 14, None, None, None, None, 13, 9, 5, 0, 4], "perma": None,
              "settle": 0.03, "melt": 0.002, "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": months("oct-apr"), "frost_hours": ["03:00", "09:00"],
     "wet_floor": {"months": months("mar-apr", "oct-nov"), "value": 0.3,
                   "terrain": ["road_earth", "packed_earth"]},
     "dust": {"months": []},
     "water": {"river": ["high", "high", "high", "normal", "normal", "low", "low", "normal",
                         "normal", "normal", "normal", "normal"],
               "lake": ["high", "high", "normal", "normal", "normal", "low", "low", "normal",
                        "normal", "normal", "normal", "normal"],
               "ice": {"months": months("dec-feb"), "hours": ["00:00", "11:00"],
                       "all_day": ["jan"], "margins": True},
               "colour": {"high": [1.12, 0.92, 0.8], "normal": [1.06, 0.96, 0.88],
                          "low": [1.04, 0.97, 0.9]}},
     "travel": {"road": by_month({"mar": 0.8, "nov": 0.8, "dec-feb": 0.5}, 1.0),
                "caravan": by_month({"mar": 0.8, "nov": 0.8, "dec-feb": 0.5}, 1.0),
                "courier": 1},
     "weather": {"spring": {"showers": 2, "clouds": 3, "wind": 0.4},
                 "summer": {"showers": 0, "clouds": 2, "wind": 0.55, "shimmer": 1},
                 "autumn": {"showers": 1, "clouds": 2, "wind": 0.4},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.6, "fog": 0.3, "snow": True}},
     "grade": {"spring": [0.98, 1.03, 0.98], "summer": [1.05, 1.0, 0.9],
               "autumn": [1.04, 0.96, 0.88], "winter": [0.88, 0.94, 1.1]},
     "look": {"summer": {"shimmer": 0.5}, "winter": {"exposure": 0.05, "blue_shadows": 0.5}},
     "dress": DRESS_HIGH,
     "turn_events": {"spring": "storks_arrive", "summer": "heat_haze",
                     "autumn": "cranes_overhead", "winter": "first_snow"},
     "fauna": {"storks": months("mar-aug"), "swallows": months("apr-sep"),
               "cranes_pass": months("mar", "oct-nov"), "frogs": months("apr-may"),
               "lambs": months("feb-apr"), "bees": months("apr-sep")},
     "work": {"pruning": ["mar"], "ploughing": months("sep-oct"), "harvest": ["jul"],
              "threshing": ["aug"], "shearing": ["may"], "vintage": ["sep"],
              "charcoal": months("oct-nov"), "wool": months("dec-feb")},
     "transhumance": {"up": ["may"], "high": months("jun-sep"), "down": ["oct"],
                      "low": months("nov-apr")}},

    {"id": "high_mountain", "name": "High mountain", "inherits": "med_green",
     "character": "the Zagros and the Taurus: snow on the heights from November to April, on the peaks into June, none in high summer",
     "classes": {"grass": row("O O F F G G D D O O O O"), "crop": row("S S G G G R U P S S S S"),
                 "deciduous": row("X X F G G G G T X X X X"),
                 "early_bloom": row("X X B F G G G T X X X X"),
                 "vine": row("X X X F G G W T X X X X"), "reed": row("D D D G G G G D D D D D"),
                 "wildflower": row("N N B B D N N N N N N N")},
     **_temps(0, 5, 10, 15, 20, 19, 15, 9, 4, -1, -3, -2),
     "snow": {"line": [10, 12, 14, 15, None, None, None, 15, 12, 9, 7, 8], "perma": None,
              "settle": 0.04, "melt": 0.002, "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": months("oct-apr"), "frost_hours": ["03:00", "09:30"],
     "wet_floor": {"months": months("apr-may", "oct-nov"), "value": 0.3,
                   "terrain": ["road_earth", "packed_earth"]},
     "dust": {"months": []},
     "water": {"stream": ["normal", "high", "high", "high", "normal", "low", "low", "normal",
                          "normal", "normal", "normal", "normal"],
               "river": ["normal", "high", "high", "high", "normal", "low", "low", "normal",
                         "normal", "normal", "normal", "normal"],
               "ice": {"months": months("dec-feb"), "hours": ["00:00", "13:00"], "margins": True,
                       "gorges": True},
               "colour": {"high": [1.0, 1.05, 1.06]}},
     "travel": {"road": CARAVAN_MOUNTAIN, "caravan": CARAVAN_MOUNTAIN, "courier": 1},
     "weather": {"spring": {"showers": 2, "clouds": 3, "wind": 0.45, "fog": 0.5},
                 "summer": {"showers": 1, "clouds": 2, "wind": 0.4},
                 "autumn": {"showers": 1, "clouds": 2, "wind": 0.5, "snow": True},
                 "winter": {"showers": 4, "clouds": 4, "wind": 0.7, "snow": True}},
     "grade": {"spring": [0.96, 1.0, 1.04], "summer": [1.0, 1.0, 1.0],
               "autumn": [1.02, 0.97, 0.92], "winter": [0.86, 0.93, 1.12]},
     "look": {"winter": {"warmth": -0.08, "exposure": 0.04}, "spring": {"fog": 0.3}},
     "dress": DRESS_HIGH,
     "turn_events": {"spring": "snowmelt", "summer": "flocks_up", "autumn": "leaves_turn",
                     "winter": "first_snow"},
     "month_turns": {"oct": "flocks_down"},
     "fauna": {"eagles": months("mar-feb"), "frogs": months("may-jun"),
               "lambs": months("mar-apr"), "bees": months("may-sep")},
     "work": {"ploughing": months("sep-oct"), "harvest": ["aug"], "threshing": ["sep"],
              "hay": ["jul"], "shearing": ["may"], "charcoal": months("oct-nov"),
              "wool": months("dec-feb")},
     "transhumance": {"up": ["may"], "high": months("jun-sep"), "down": ["oct"],
                      "low": months("nov-apr")}},

    {"id": "mesopotamian", "name": "Mesopotamian plain", "inherits": "med_green",
     "character": "a mild green winter, harvest in April and May with the flood, a scorching dusty summer, dates in autumn",
     "classes": {"grass": row("F G D D D D D D G G F F"), "crop": row("G R U U U U U P S S G G"),
                 "deciduous": row("F G G G G G G G G T X F"),
                 "early_bloom": row("F G G G G G G G G T X B"),
                 "vine": row("F G G G W W G T T X X X"), "reed": row("G G G G G G G G G D D G"),
                 "wildflower": row("B B D N N N N N N G G B")},
     **_temps(17, 22, 28, 33, 35, 35, 31, 25, 18, 12, 10, 13),
     "snow": {"line": [None] * 12, "perma": None, "settle": 0.0, "melt": 1.0,
              "note": "never: no snow on Babylon, Susa or the Gulf"},
     "frost": [],
     "wet_floor": {"months": months("dec-feb"), "value": 0.2,
                   "terrain": ["road_earth", "packed_earth", "mud_bank"]},
     "dust": {"months": months("jun-sep")},
     "water": {"river": ["normal", "flood", "flood", "high", "normal", "low", "low", "low",
                         "normal", "normal", "normal", "normal"],
               "river_rank": [0, 2, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0],
               "channel": ["full", "full", "full", "normal", "low", "low", "low", "normal",
                           "normal", "normal", "normal", "normal"],
               "colour": {"flood": [1.12, 0.92, 0.8], "high": [1.1, 0.94, 0.82],
                          "normal": [1.02, 0.99, 0.9], "low": [0.98, 1.0, 0.9]}},
     "travel": {"road": [1] * 12, "caravan": [1] * 12, "courier": 1,
                "barge": by_month({"apr-may": 0.4}, 1.0),
                "hours": {"months": months("jun-aug"),
                          "travel": [["04:00", "09:00"], ["17:00", "23:00"]]}},
     "weather": {"spring": {"showers": 1, "clouds": 2, "wind": 0.3, "fog": 0.2},
                 "summer": {"showers": 0, "clouds": 0, "wind": 0.5, "wind_from": "north-west",
                            "dust": 3, "shimmer": 1},
                 "autumn": {"showers": 0, "clouds": 1, "wind": 0.25},
                 "winter": {"showers": 2, "clouds": 3, "wind": 0.3, "fog": 0.5}},
     "grade": {"spring": [1.0, 1.02, 0.95], "summer": [1.08, 0.98, 0.84],
               "autumn": [1.04, 0.99, 0.9], "winter": [0.96, 0.99, 1.02]},
     "look": {"summer": {"haze": 0.4, "dust": 0.4, "shimmer": 0.4}, "winter": {"fog": 0.3}},
     "dress": DRESS_HOT, "coast": "gulf",
     "turn_events": {"spring": "storks_arrive", "summer": "heat_haze",
                     "autumn": "date_harvest", "winter": "cranes_overhead"},
     "month_turns": {"apr": "flood_rising"},
     "fauna": {"storks": months("mar-aug"), "swallows": months("mar-oct"),
               "cranes_winter": months("dec-feb"), "geese": months("nov-feb"),
               "frogs": months("mar-may"), "bees": months("mar-feb"), "lambs": months("dec-feb")},
     "work": {"ploughing": months("oct-dec"), "harvest": months("apr-may"),
              "threshing": months("may-jun"), "shearing": months("mar-apr"),
              "dates_pollinate": months("mar-apr"), "dates_harvest": months("sep-oct"),
              "canals": months("jul-sep"), "wool": months("dec-feb")}},

    {"id": "steppe", "name": "Syrian steppe", "inherits": "mesopotamian",
     "character": "a brief green flush after the winter rain, bleached the rest of the year",
     "classes": {"grass": row("F G D D D D D D D D G F")},
     **_temps(13, 18, 24, 28, 30, 30, 27, 21, 14, 9, 7, 9),
     "frost": months("dec-feb"), "frost_hours": ["03:00", "07:30"],
     "wet_floor": {"months": [], "value": 0.0, "terrain": []},
     "dust": {"months": months("jun-sep")},
     "weather": {"spring": {"showers": 1, "clouds": 2, "wind": 0.35},
                 "summer": {"showers": 0, "clouds": 0, "wind": 0.45, "dust": 3, "shimmer": 1},
                 "autumn": {"showers": 0, "clouds": 1, "wind": 0.35, "dust": 1},
                 "winter": {"showers": 1, "clouds": 2, "wind": 0.35}},
     "grade": {"spring": [1.0, 1.02, 0.96], "summer": [1.08, 1.0, 0.86],
               "autumn": [1.05, 1.0, 0.9], "winter": [0.96, 0.98, 1.02]},
     "look": {"summer": {"shimmer": 0.6, "contrast": 0.08}},
     "dress": _dress({"nov": 0.2, "dec-feb": 0.5}, {"may": 0.2, "jun-aug": 0.5, "sep": 0.2}),
     "turn_events": {"spring": "first_green", "summer": "heat_haze",
                     "autumn": "cranes_overhead", "winter": "first_frost"},
     "month_turns": {},
     "fauna": {"storks": months("mar-apr", "sep"), "cranes_pass": months("mar", "oct-nov"),
               "lambs": months("jan-mar")},
     "work": {"shearing": months("mar-apr"), "wool": months("dec-feb")},
     "transhumance": {"up": ["feb"], "high": months("feb-apr"), "down": ["may"],
                      "low": months("may-jan"),
                      "note": "out into the steppe's green flush, back to the wells and the river"}},

    {"id": "fars", "name": "Fārs", "inherits": "med_green",
     "character": "Pārsa at 1,600 m: cold bright winters with frost and some snow, a short green spring, hot dry dusty summers",
     "classes": {"grass": row("F F G D D D D D O O O O"), "crop": row("G G G R U U U P S S S S"),
                 "deciduous": row("F F G G G G G G T X X X"),
                 "early_bloom": row("B F G G G G G G T X X B"),
                 "vine": row("X F G G G W W T X X X X"),
                 "wildflower": row("B B G D N N N N N N N G")},
     **_temps(10, 15, 20, 26, 29, 28, 24, 18, 11, 6, 4, 6),
     "snow": {"line": [14, None, None, None, None, None, None, None, 15, 12, 11, 12], "perma": None,
              "settle": 0.02, "melt": 0.004,
              "lowland": {"months": months("dec-feb"), "chance": 0.25, "settle": True,
                          "melt_days": 1, "note": "the plain (level 4) takes snow on a few days "
                          "of deep winter; it melts in a day and never lies into spring"},
              "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": months("dec-feb"), "frost_hours": ["03:00", "09:00"],
     "wet_floor": {"months": months("dec-mar"), "value": 0.3,
                   "terrain": ["road_earth", "packed_earth", "mud_bank"]},
     "dust": {"months": months("jun-sep")},
     "water": {"channel": ["full", "full", "full", "normal", "low", "low", "low", "low", "normal",
                           "normal", "normal", "normal"],
               "river": ["high", "high", "high", "normal", "low", "low", "low", "low", "normal",
                         "normal", "normal", "normal"],
               "ice": {"months": months("dec-feb"), "hours": ["03:00", "11:00"]}},
     "travel": {"road": [1, 1, 1, 1, 1, 1, 1, 0.9, 0.8, 0.7, 0.6, 0.7],
                "caravan": [1, 1, 1, 1, 1, 1, 1, 0.9, 0.8, 0.7, 0.6, 0.7], "courier": 1},
     "weather": {"spring": {"showers": 1, "clouds": 3, "wind": 0.35, "wind_from": "north-west"},
                 "summer": {"showers": 0, "clouds": 1, "wind": 0.45, "dust": 2},
                 "autumn": {"showers": 0, "clouds": 1, "wind": 0.3},
                 "winter": {"showers": 2, "clouds": 4, "wind": 0.4, "snow": True}},
     "grade": {"spring": [0.99, 1.01, 0.98], "summer": [1.06, 1.0, 0.88],
               "autumn": [1.04, 0.98, 0.9], "winter": [0.9, 0.95, 1.08]},
     "look": {"winter": {"haze": -0.4, "stars": 0.2}, "summer": {"dust": 0.3}},
     "dress": DRESS_MED,
     "turn_events": {"spring": "storks_arrive", "summer": "first_dust",
                     "autumn": "ploughing_begins", "winter": "first_frost"},
     "fauna": {"storks": months("mar-aug"), "swallows": months("mar-sep"),
               "cranes_pass": months("mar", "oct-nov"), "frogs": months("mar-may"),
               "nightingales": months("apr-jun"), "bees": months("mar-oct"),
               "lambs": months("feb-mar")},
     "work": {"pruning": months("feb-mar"), "ploughing": months("oct-nov"), "harvest": ["jun"],
              "threshing": months("jun-jul"), "shearing": ["apr"], "vintage": ["sep"],
              "canals": months("aug-sep"), "charcoal": months("nov-feb"),
              "wool": months("nov-feb"), "building": by_month({"dec-feb": 0.6}, 1.0)}},

    {"id": "plateau", "name": "Iranian plateau", "inherits": "fars",
     "character": "the higher plateau north of Pārsa: as Fārs, two weeks later, colder and snowier",
     "classes": {"grass": row("O F F G D D D O O O O O"), "crop": row("S G G G R U P S S S S S"),
                 "deciduous": row("X F G G G G T T X X X X"),
                 "early_bloom": row("X B F G G G G T X X X X"),
                 "vine": row("X X F G G G W T X X X X"),
                 "wildflower": row("N B B D N N N N N N N N")},
     **_temps(7, 12, 17, 22, 25, 24, 20, 13, 7, 2, 0, 2),
     "snow": {"line": [9, 12, 14, None, None, None, None, 15, 10, 7, 5, 6], "perma": None,
              "settle": 0.03, "melt": 0.002, "on": ["ground", "evergreen", "roofs", "backdrop"]},
     "frost": months("oct-apr"),
     "water": {"channel": ["normal", "full", "full", "normal", "low", "low", "low", "low",
                           "normal", "normal", "normal", "normal"],
               "river": ["normal", "high", "high", "normal", "low", "low", "low", "low", "normal",
                         "normal", "normal", "normal"],
               "ice": {"months": months("dec-feb"), "hours": ["00:00", "10:00"], "margins": True}},
     "travel": {"road": [0.8, 1, 1, 1, 1, 1, 1, 0.9, 0.8, 0.6, 0.5, 0.6],
                "caravan": [0.8, 1, 1, 1, 1, 1, 1, 0.9, 0.8, 0.6, 0.5, 0.6], "courier": 1},
     "weather": {"spring": {"showers": 1, "clouds": 3, "wind": 0.35, "wind_from": "north-west"},
                 "summer": {"showers": 0, "clouds": 1, "wind": 0.45, "dust": 2},
                 "autumn": {"showers": 0, "clouds": 1, "wind": 0.3},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.45, "snow": True}},
     "dress": DRESS_HIGH,
     "turn_events": {"spring": "storks_arrive", "summer": "first_dust",
                     "autumn": "ploughing_begins", "winter": "first_snow"},
     "fauna": {"storks": months("apr-aug"), "swallows": months("apr-sep"),
               "cranes_pass": months("mar", "oct-nov"), "frogs": months("apr-may"),
               "bees": months("apr-sep"), "lambs": months("mar-apr")},
     "work": {"pruning": ["mar"], "ploughing": months("sep-oct"), "harvest": ["jul"],
              "threshing": ["aug"], "shearing": ["may"], "vintage": ["sep"],
              "canals": months("aug-sep"), "charcoal": months("oct-feb"),
              "wool": months("nov-feb")}},

    {"id": "sea_west", "name": "Western seas", "inherits": "med_green",
     "character": "the Tyrrhenian, Adriatic and Ionian waters: winter storms, the bora in the Adriatic",
     "sea": {"state": [1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 3, 2],
             "sailing": [0.4, 0.6, 0.9, 1, 1, 1, 0.9, 0.5, 0.25, 0.1, 0.1, 0.1],
             "grain": [0, 0.3, 1, 1, 1, 1, 0.6, 0.2, 0, 0, 0, 0],
             "storms": [0, 0, 0, 0, 0, 0, 1, 2, 2, 3, 3, 2],
             "closed": months("nov-feb"),
             "note": "Vegetius 4.39: closed from 11 November to 10 March; the Navigium Isidis opens it on 5 March"},
     "weather": {"spring": {"showers": 2, "clouds": 2, "wind": 0.35, "wind_from": "west"},
                 "summer": {"showers": 0, "clouds": 1, "wind": 0.3},
                 "autumn": {"showers": 3, "clouds": 3, "wind": 0.5, "storm": 2},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.6, "storm": 3}},
     "turn_events": {"spring": "sailing_opens", "summer": "heat_haze",
                     "autumn": "storms_return", "winter": "ships_hauled_ashore"}},

    {"id": "sea_aegean", "name": "Aegean seas", "inherits": "med_dry",
     "character": "the Aegean and the Saronic gulf: the Etesian north wind (meltemi) in July and August",
     "sea": {"state": [1, 1, 1, 1, 2, 2, 1, 2, 2, 3, 3, 2],
             "sailing": [0.4, 0.6, 0.9, 1, 1, 1, 0.9, 0.5, 0.25, 0.1, 0.1, 0.1],
             "grain": [0, 0.3, 1, 1, 1, 1, 0.6, 0.2, 0, 0, 0, 0],
             "storms": [0, 0, 0, 0, 0, 0, 1, 2, 2, 3, 3, 2],
             "closed": months("nov-feb"),
             "wind": {"months": months("jul-aug"), "hours": ["12:00", "19:00"], "wind": 0.6,
                      "from": "north-east", "name": "meltemi"}},
     "weather": {"spring": {"showers": 1, "clouds": 2, "wind": 0.35},
                 "summer": {"showers": 0, "clouds": 1, "wind": 0.55, "wind_from": "north-east"},
                 "autumn": {"showers": 2, "clouds": 3, "wind": 0.45, "storm": 2},
                 "winter": {"showers": 3, "clouds": 4, "wind": 0.55, "storm": 3},
                 "months": {"jun": {"wind": 0.35, "wind_from": "north"}}},
     "turn_events": {"spring": "sailing_opens", "summer": "meltemi",
                     "autumn": "storms_return", "winter": "ships_hauled_ashore"}},

    {"id": "gulf", "name": "Head of the Gulf", "inherits": "mesopotamian",
     "character": "the head of the Persian Gulf: coastal boats all year, the summer shamal",
     "sea": {"state": [1] * 12, "sailing": [1, 1, 1, 0.6, 0.6, 1, 1, 1, 1, 1, 1, 1],
             "grain": [1] * 12, "storms": [0] * 12, "closed": [],
             "wind": {"months": months("jun-jul"), "hours": ["10:00", "18:00"], "wind": 0.55,
                      "from": "north-west", "name": "shamal", "dust": 3}},
     "weather": {"spring": {"showers": 0, "clouds": 1, "wind": 0.25},
                 "summer": {"showers": 0, "clouds": 0, "wind": 0.5, "wind_from": "north-west",
                            "dust": 3},
                 "autumn": {"showers": 0, "clouds": 1, "wind": 0.25},
                 "winter": {"showers": 1, "clouds": 2, "wind": 0.3}},
     "turn_events": {"spring": "storks_arrive", "summer": "shamal",
                     "autumn": "date_harvest", "winter": "cranes_overhead"},
     "month_turns": {}},
]

# -- regions -----------------------------------------------------------------------------------

# seasons.md §2.1, with the towns the table does not name placed by their land: the Campanian
# and Samnite towns and Kerkyra green; Olympia's Alpheios valley green (Elis is wetter than
# Attica); Sparta Attic-dry under Taygetos; Gordion on the plateau; Sidon on the Levant coast.
# The home region (`corner`) has no region file: its climate is `home` by this table.
REGION_CLIMATE = {
    "corner": "home", "seam_dell": "home",
    "rome": "med_green", "latium_italy": "med_green", "ostia": "med_green",
    "alban_mount": "med_green", "brundisium": "med_green", "tibur": "med_green",
    "capua": "med_green", "beneventum": "med_green", "corcyra": "med_green",
    "olympia": "med_green", "ionia_lydia": "med_green", "ephesus": "med_green",
    "sardis": "med_green", "seam_ionia": "med_green",
    "athens": "med_dry", "attica_north": "med_dry", "academy": "med_dry", "eleusis": "med_dry",
    "corinth": "med_dry", "greece": "med_dry", "delos": "med_dry", "sparta": "med_dry",
    "apennines": "highland", "arcadia": "highland", "delphi": "highland",
    "thrace": "thracian", "east_med": "levant", "sidon": "levant",
    "anatolia": "anatolian", "halys": "anatolian", "gordion": "anatolian",
    # The design's table puts the crossing with Mesopotamia; on this map its rect lies wholly
    # inside Anatolia (the upper Euphrates), so it shares the plateau's winters.
    "euphrates_crossing": "anatolian",
    "zagros": "high_mountain", "taurus": "high_mountain", "persian_gates": "high_mountain",
    "mesopotamia": "mesopotamian", "babylon": "mesopotamian",
    "susiana": "mesopotamian", "susa": "mesopotamian",
    "syrian_steppe": "steppe", "parsa": "fars", "iran_plateau": "plateau", "pasargadae": "plateau",
    "tyrrhenian": "sea_west", "adriatic": "sea_west", "ionian_sea": "sea_west",
    "seam_ionian": "sea_west", "aegean": "sea_aegean", "saronic": "sea_aegean",
    "persian_gulf": "gulf",
}

# Which climates may meet on the map (seasons.md §2.1: seams blend by influence weights). A
# `touch` pair changes at a coast, a plateau edge or a pass, where the land itself changes; a
# `blend` pair grades across a seam or a wide transition (the engine blends looks over it).
# Pairs not listed must not meet.
TOUCH = {
    ("home", "med_green"): "blend", ("home", "sea_west"): "touch",
    ("med_green", "sea_west"): "touch", ("med_green", "highland"): "touch",
    ("med_green", "med_dry"): "blend", ("med_green", "sea_aegean"): "touch",
    ("med_green", "thracian"): "blend", ("med_green", "anatolian"): "touch",
    ("med_green", "levant"): "blend",
    ("med_dry", "sea_aegean"): "touch", ("med_dry", "sea_west"): "touch",
    ("med_dry", "highland"): "touch", ("med_dry", "thracian"): "blend",
    ("highland", "sea_west"): "touch",
    ("thracian", "sea_aegean"): "touch", ("thracian", "anatolian"): "touch",
    ("levant", "sea_aegean"): "touch", ("levant", "anatolian"): "touch",
    ("levant", "high_mountain"): "touch", ("levant", "mesopotamian"): "blend",
    ("levant", "steppe"): "blend",
    ("anatolian", "high_mountain"): "touch", ("anatolian", "mesopotamian"): "touch",
    ("anatolian", "plateau"): "blend",
    ("high_mountain", "plateau"): "touch", ("high_mountain", "fars"): "touch",
    ("high_mountain", "mesopotamian"): "touch",
    ("mesopotamian", "steppe"): "blend", ("mesopotamian", "gulf"): "touch",
    ("mesopotamian", "plateau"): "touch",
    ("steppe", "gulf"): "touch", ("plateau", "fars"): "blend", ("plateau", "gulf"): "touch",
    ("sea_west", "sea_aegean"): "blend",
}


def touch(a: str, b: str) -> str | None:
    return TOUCH.get((a, b)) or TOUCH.get((b, a))


# -- what changes in the sets ------------------------------------------------------------------

def _plant(cls, plain, states, **kw):
    return {"season_class": cls, "plain_state": plain, "season_states": states, **kw}


DECID = ["fresh", "turn", "bare"]
VINE = ["fresh", "fruit", "turn", "bare"]
CROP = ["ploughed", "sprout", "ripe", "stubble"]
# Set items and terrain with seasonal looks (seasons.md §3.1, §3.2, §6.3). `season_states` is
# what the art supplies besides the plain look (the design's `states`, renamed because set
# catalogs already use `states` for slot-state layers such as `lit` and `open`). The lists here
# are the design's; the catalog writer adds every further state the item resolves to in the
# climates where it is placed, so coverage is complete by construction.
SEASON_ITEMS = {
    "world": {
        "world.t_oak": _plant("deciduous", "green", DECID),
        "world.t_oak_zagros": _plant("deciduous", "green", DECID),
        "world.t_beech": _plant("deciduous", "green", DECID),
        "world.t_pistachio": _plant("deciduous", "green", DECID),
        "world.t_tamarisk": _plant("deciduous", "green", ["bloom", "bare"], bloom=months("apr-may")),
        "world.t_fir": _plant("evergreen", "green", ["snow"], snow_look=True),
        "world.t_cedar": _plant("evergreen", "green", ["snow"], snow_look=True),
        "world.t_juniper": _plant("evergreen", "green", ["snow"], snow_look=True),
        "world.t_palm": _plant("evergreen", "green", ["fruit"], fruit=months("aug-oct")),
        "world.t_reeds": _plant("reed", "green", ["dry"]),
        "world.p_wildflowers": _plant("wildflower", "green", ["bloom", "dry"]),
        "world.p_thistle": _plant("grass", "dry", ["green", "dormant"]),
        "world.p_maquis": _plant("evergreen", "green", []),
        "world.t_cork_oak": _plant("evergreen", "green", []),
        "world.t_oleaster": _plant("evergreen", "green", []),
    },
    "rome": {
        "rome.t_plane": _plant("deciduous", "green", DECID),
        "rome.t_poplar": _plant("deciduous", "green", DECID),
        "rome.t_fig": _plant("deciduous", "green", DECID),
        "rome.t_vine": _plant("vine", "green", VINE),
        "rome.r_vine": _plant("vine", "green", VINE),
        "rome.t_rose": _plant("deciduous", "bloom", ["green", "bare"], bloom=["may"]),
        "rome.p_poppy": _plant("wildflower", "bloom", ["green", "dry"]),
        "rome.p_reeds": _plant("reed", "green", ["dry"]),
        "rome.p_acanthus": _plant("wildflower", "green", ["dry"]),
        **{f"rome.{i}": _plant("evergreen", "green", [])
           for i in ("t_stone_pine", "t_cypress", "t_laurel", "t_myrtle", "t_olive", "t_box",
                     "t_oak", "p_cabbage")},
    },
    "athens": {
        "athens.t_plane": _plant("deciduous", "green", DECID),
        "athens.t_poplar": _plant("deciduous", "green", DECID),
        "athens.t_fig": _plant("deciduous", "green", DECID),
        "athens.t_vine": _plant("vine", "green", VINE),
        "athens.t_agnus": _plant("deciduous", "bloom", ["green", "bare"], bloom=["jul"]),
        "athens.t_oleander": _plant("evergreen", "bloom", ["green"], bloom=months("jun-sep")),
        "athens.p_thyme": _plant("evergreen", "green", ["bloom"], bloom=months("may-jun")),
        "athens.p_barley": _plant("crop", "stubble", ["ploughed", "sprout", "green", "ripe"]),
        "athens.p_asphodel": _plant("wildflower", "dry", ["bloom", "green"]),
        "athens.p_reeds": _plant("reed", "green", ["dry"]),
        "athens.p_acanthus": _plant("wildflower", "green", ["dry"]),
        **{f"athens.{i}": _plant("evergreen", "green", [])
           for i in ("t_olive", "t_cypress", "t_pine", "t_myrtle", "t_laurel")},
    },
    "parsa": {
        "parsa.t_plane": _plant("deciduous", "green", DECID),
        "parsa.t_poplar": _plant("deciduous", "green", DECID),
        "parsa.t_willow": _plant("deciduous", "green", DECID),
        "parsa.t_fig": _plant("deciduous", "green", DECID),
        "parsa.t_almond": _plant("early_bloom", "bloom", ["fresh", "green", "turn", "bare"]),
        "parsa.t_pomegranate": _plant("deciduous", "bloom", ["green", "turn", "bare"],
                                      bloom=months("may-jun")),
        "parsa.t_vine": _plant("vine", "green", VINE),
        "parsa.t_date": _plant("evergreen", "green", ["fruit"], fruit=months("aug-oct")),
        "parsa.p_barley": _plant("crop", "green", CROP),
        "parsa.p_wheat": _plant("crop", "green", CROP),
        "parsa.p_lilies": _plant("wildflower", "bloom", ["green", "dry"]),
        "parsa.p_rose": _plant("deciduous", "bloom", ["green", "bare"], bloom=["may"]),
        "parsa.p_steppe": _plant("grass", "fresh", ["dry", "dormant"]),
        "parsa.t_cypress": _plant("evergreen", "green", ["snow"], snow_look=True),
    },
}
SEASON_TERRAIN = {
    "world": {
        "world.steppe": _plant("grass", "dry", ["fresh", "green", "dormant"]),
        "world.pasture": _plant("grass", "green", ["fresh", "dry", "dormant"]),
        "world.alluvium": _plant("grass", "dry", ["green"]),
        "world.scrub": _plant("grass", "dry", ["fresh", "green"]),
        "world.forest_floor": _plant("deciduous", "green", ["turn", "dormant"],
                                     note="leaf litter in the turning months, dormant in winter"),
        "world.field": _plant("crop", "green", CROP),
        "world.fallow": _plant("grass", "dry", ["fresh"]),
        "world.marsh": _plant("reed", "green", ["dry"]),
    },
    "rome": {"rome.grass_spring": _plant("grass", "fresh", ["green", "dry"]),
             "rome.field_spring": _plant("crop", "green", CROP)},
    "athens": {"athens.dry_grass": _plant("grass", "dry", ["fresh", "green"]),
               "athens.field_stubble": _plant("crop", "stubble", ["ploughed", "sprout", "green", "ripe"]),
               "athens.olive_soil": _plant("grass", "dry", ["green"],
                                           note="winter herbs under the olives")},
    "parsa": {"parsa.plain_grass": _plant("grass", "fresh", ["dry", "dormant"]),
              "parsa.field_barley": _plant("crop", "green", CROP)},
}
# Items whose up faces never hold snow (the generator clears their snow-catcher bit).
NO_SNOW_CATCH = ["rome.r_brazier", "rome.r_lamp", "rome.r_lacus", "athens.g_brazier",
                 "athens.g_lamp", "athens.g_kiln", "athens.g_fountain", "parsa.p_brazier",
                 "parsa.p_torch", "parsa.p_fire_altar", "parsa.p_kiln", "parsa.p_oven",
                 "parsa.p_incense", "world.charcoal_kiln", "world.beacon"]
ART_OVERLAYS = ["world.snowcover", "world.ice", "world.flood"]
BACKDROP_SNOW = {"world": ["world.bd_far_hills", "world.bd_alps", "world.bd_pindos",
                           "world.bd_pontic", "world.bd_plateau"]}

# Walker kinds that change dress with the weather (seasons.md §3.6): cold everywhere they live,
# hot for outdoor workers and travellers. Formal and ritual dress (togas, priests, Vestals, the
# king, delegations, kanephoroi) does not follow the weather.
DRESS = {
    "rome.citizen": "both", "rome.working_woman": "cold", "rome.docker": "both",
    "rome.hauler": "both", "rome.carter": "both", "rome.child": "cold", "rome.farmer": "both",
    "rome.shepherd": "both", "rome.freedman": "cold", "rome.enslaved": "both",
    "athens.citizen": "both", "athens.farmer": "both", "athens.herder": "both",
    "athens.enslaved_man": "both", "athens.woman": "cold", "athens.working_woman": "cold",
    "athens.child": "cold", "athens.metic": "cold", "athens.rower": "hot",
    "athens.elder": "cold",
    "parsa.labourer": "both", "parsa.woman_worker": "both", "parsa.guard_mede": "both",
    "parsa.shepherd": "both", "parsa.scribe": "cold", "parsa.farmer": "both",
    "parsa.gardener": "both", "parsa.craftsman": "both", "parsa.groom": "both",
    "parsa.caravan_driver": "both", "parsa.elamite": "both",
    "world.traveller": "both", "world.merchant": "both", "world.muleteer": "both",
    "world.fisher": "both", "world.sailor": "both", "world.logger": "cold",
}
