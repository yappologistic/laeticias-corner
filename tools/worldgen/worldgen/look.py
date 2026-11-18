"""The look of a region file: `theme.look` (docs/design/look.md §3.5, the region look that
replaces `theme.grading` on the `gpu` path; `grading` stays for the classic path), written into
every region document by `apply` and checked by `check`.

`theme.look`:
- `phases.<dawn|day|dusk|night>`: the lookup's parameters: `wb` (rgb multipliers), `exposure`,
  `shadow_tint` and `high_tint` (rgb 0..1, split toning around 0.5) with `tint` (amount),
  `contrast`, `saturation`, `shoulder` (highlight roll-off 0..1) and optional hue `bands`
  (`terracotta`, `foliage`, `water`, `stone`: `hue` degrees, `sat` and `val` shifts). The values
  start from the tested mock-up parameters (`out/look/mockups/make.py`) and each region's
  direction (§2.2, the city files' §8, world.md §9.1).
- `sky.<phase>`: three stops top → horizon (`#rrggbb`); `sun` and `shade` colours per phase (the
  two lights of §2.3; at night `sun` is the moon); `haze` (`colour`, `strength` at 1×, `toward`,
  `by_zoom` for ½, ¼ and the overview, §2.4); `stars` 0..1.
- `palette`: the §2.2 mid-tone anchors (`large`, `accents`) the art and the grade aim at; `light`
  the region's light character in words.
- `targets`: the §2.1 acceptance numbers per phase for this region (cool share floor 8 % in
  cities, 15 % at home and on coasts).
- `weather`: tendencies per season (`storm`, `fog`, `dust`: chance a day has one) and `air`:
  the regional effects of §2.4 (smoke haze, river or plain mist at dawn, heat shimmer on paving,
  dust motes, night mist over water).
- `lights`: every glowing kind placed in the region with its `colour`, `radius` (tiles), `kind`
  (`lamp`, `torch`, `fire`, `window`, `beacon`) and `flicker` (`hz` range and `depth`, or
  `breathe` for fires; `stagger` for windows lighting one by one at dusk, §3.2 P6).
- `water`: the body colour, `reflect`, the default `sea_state`.
- `backdrop`: for regions on the world's north or east edge, the strip (`world.bd_*`) and the
  span of the edge it covers (§3.2 P0).
- `interiors`: roof-off candidates (§3.3), in order.

`districts[].look` (where the design asks for it): `reflect` (water in the district), `air`
(the region's mist or shimmer where it belongs: river and low districts at dawn, paved squares at
noon), `haze` nudges for harbours.
"""

from __future__ import annotations

import re
from pathlib import Path

from plan import world_plan as P

from . import sound
from .compose import World, live_items

PHASES = ("dawn", "day", "dusk", "night")


def ph(wb, exposure, shadow, high, tint, contrast, sat, shoulder=0.0, bands=None) -> dict:
    out = {"wb": list(wb), "exposure": exposure, "shadow_tint": list(shadow),
           "high_tint": list(high), "tint": tint, "contrast": contrast, "saturation": sat,
           "shoulder": shoulder}
    if bands:
        out["bands"] = bands
    return out


# The three city directions and home, from §2.2, the city files' §8 and the mock-ups.
FAMILY = {
    "rome": {
        "phases": {
            "dawn": ph((0.98, 0.88, 0.86), 0.86, (0.34, 0.32, 0.62), (0.66, 0.54, 0.42), 0.28, 0.30, 1.02, 0.2),
            "day": ph((1.0, 0.97, 0.95), 0.95, (0.30, 0.40, 0.70), (0.53, 0.52, 0.50), 0.34, 0.40, 0.96, 0.35,
                      {"terracotta": {"hue": -4, "sat": 0.10, "val": -0.06},
                       "foliage": {"hue": 4, "sat": 0.0, "val": -0.04}}),
            "dusk": ph((1.0, 0.85, 0.68), 0.80, (0.32, 0.30, 0.60), (0.88, 0.68, 0.34), 0.34, 0.34, 1.04, 0.25,
                       {"terracotta": {"hue": 3, "sat": -0.08, "val": 0.0}}),
            "night": ph((0.72, 0.80, 1.0), 0.42, (0.24, 0.28, 0.52), (0.50, 0.52, 0.62), 0.30, 0.22, 0.78),
        },
        "sky": {"dawn": ["#32406e", "#e59b78", "#f8d9b0"], "day": ["#4b86c9", "#a3c9ea", "#eef0ec"],
                "dusk": ["#3c2d55", "#d6703f", "#f4c37a"], "night": ["#0d1330", "#20294d", "#2c3458"]},
        "sun": {"dawn": "#f3c9a0", "day": "#fff6e3", "dusk": "#f2b25e", "night": "#afc3e8"},
        "shade": {"dawn": "#7a6fa8", "day": "#7fa6d8", "dusk": "#6a5a93", "night": "#2a3560"},
        "haze": {"colour": "#f2e3c9", "strength": 0.08, "toward": "west"},
        "stars": 0.55,
        "palette": {"large": {"terracotta": "#b8512f", "terracotta_shade": "#6e2a1e",
                              "terracotta_lit": "#e08a5a", "travertine": "#e6dcc4", "brick": "#9a4a32",
                              "basalt": "#3a3a40"},
                    "accents": {"umbrella_pine": "#3e5b2e", "gilded_bronze": "#d9a93a"}},
        "light": "honey-gold with a warm smoke haze; dusk is Rome's signature, gold not orange",
        "air": {"smoke_haze": {"hours": ["13:00", "18:00"], "strength": 0.05},
                "mist": {"where": "river", "hours": ["05:00", "08:00"], "seasons": ["spring", "autumn"]}},
        "water": {"body": "#3d6f8f", "reflect": True, "sea_state": 0},
    },
    "athens": {
        "phases": {
            "dawn": ph((0.98, 0.88, 0.84), 0.88, (0.40, 0.38, 0.72), (0.70, 0.58, 0.46), 0.26, 0.32, 1.0, 0.2),
            "day": ph((1.02, 1.0, 0.96), 1.0, (0.28, 0.40, 0.76), (0.56, 0.54, 0.48), 0.30, 0.48, 1.04, 0.45,
                      {"foliage": {"hue": -6, "sat": -0.08, "val": 0.02},
                       "water": {"hue": 0, "sat": 0.08, "val": -0.04}}),
            "dusk": ph((1.0, 0.86, 0.72), 0.82, (0.36, 0.30, 0.62), (0.88, 0.64, 0.50), 0.30, 0.32, 1.02, 0.3),
            "night": ph((0.74, 0.82, 1.0), 0.46, (0.24, 0.30, 0.56), (0.50, 0.52, 0.62), 0.28, 0.20, 0.80),
        },
        "sky": {"dawn": ["#3a4a7a", "#f0a878", "#fbe3b8"], "day": ["#3f7fd0", "#8fc3ef", "#f2f4f2"],
                "dusk": ["#40305e", "#d8784a", "#f6c27a"], "night": ["#0c1430", "#1c2a52", "#28365e"]},
        "sun": {"dawn": "#f6c8a0", "day": "#fffbef", "dusk": "#f2b07a", "night": "#b4c8ee"},
        "shade": {"dawn": "#8c84b8", "day": "#6f98d8", "dusk": "#5e4e8c", "night": "#263258"},
        "haze": {"colour": "#eee3cc", "strength": 0.06, "toward": "south-west"},
        "stars": 0.85,
        "palette": {"large": {"marble": "#f1ede3", "marble_shade": "#b7b4c8", "dry_earth": "#c9a465",
                              "limestone": "#a39a8a"},
                    "accents": {"frieze_blue": "#2a5ba8", "frieze_red": "#b2342a", "olive": "#8c9a6b",
                                "sea": "#1f5e8c"}},
        "light": "brilliant and high-contrast, short blue shadows; marble the brightest thing on screen",
        "air": {"haze_toward_sea": {"strength": 0.04},
                "shimmer": {"where": "paving", "hours": ["11:00", "15:00"], "seasons": ["summer"]}},
        "water": {"body": "#1f5e8c", "reflect": True, "sea_state": 1},
    },
    "parsa": {
        "phases": {
            "dawn": ph((0.94, 0.86, 0.92), 0.92, (0.36, 0.32, 0.68), (0.62, 0.53, 0.44), 0.26, 0.30, 1.0, 0.2,
                       {"stone": {"hue": 6, "sat": 0.06, "val": 0.04}}),
            "day": ph((0.98, 0.99, 1.0), 0.94, (0.32, 0.40, 0.70), (0.52, 0.52, 0.52), 0.28, 0.42, 1.08, 0.3,
                      {"foliage": {"hue": 0, "sat": 0.12, "val": 0.0},
                       "stone": {"hue": 0, "sat": -0.06, "val": -0.06}}),
            "dusk": ph((1.0, 0.82, 0.74), 0.80, (0.36, 0.28, 0.58), (0.86, 0.56, 0.46), 0.32, 0.32, 1.02, 0.25,
                       {"stone": {"hue": -8, "sat": 0.06, "val": 0.0}}),
            "night": ph((0.70, 0.78, 1.0), 0.40, (0.22, 0.26, 0.50), (0.48, 0.50, 0.62), 0.30, 0.24, 0.72),
        },
        "sky": {"dawn": ["#2b3a67", "#e8a87c", "#f6d7a7"], "day": ["#4a86c8", "#9cc6e8", "#e9eef0"],
                "dusk": ["#3d2c5a", "#c75b39", "#f2b46d"], "night": ["#0b1026", "#1b2445", "#262f52"]},
        "sun": {"dawn": "#f0c090", "day": "#fff8ec", "dusk": "#e89a70", "night": "#b8ccf2"},
        "shade": {"dawn": "#7e74b0", "day": "#7fa2d0", "dusk": "#5a4682", "night": "#1e2848"},
        "haze": {"colour": "#d8d6e2", "strength": 0.05, "toward": "west"},
        "stars": 1.0,
        "palette": {"large": {"limestone": "#c9b79c", "limestone_shade": "#8e8597", "mud_plaster": "#c8a27a",
                              "paving": "#a89f94"},
                    "accents": {"lapis": "#2648a0", "cinnabar": "#b8322a", "gold": "#d8ae3e",
                                "garden_green": "#4e8a3a"}},
        "light": "crisp mountain air, cool shadows; stone turns honey at dawn and rose at dusk",
        "air": {"mist": {"where": "plain", "hours": ["05:00", "07:30"], "seasons": ["spring"]},
                "dust_motes": {"hours": ["15:00", "19:00"], "seasons": ["summer"]}},
        "water": {"body": "#3f7fa0", "reflect": True, "sea_state": 0},
    },
    "home": {
        "phases": {
            "dawn": ph((0.96, 0.88, 0.88), 0.88, (0.34, 0.34, 0.64), (0.72, 0.58, 0.42), 0.28, 0.30, 1.10, 0.2),
            "day": ph((1.0, 1.0, 0.98), 1.0, (0.32, 0.40, 0.66), (0.56, 0.54, 0.46), 0.26, 0.30, 1.10, 0.3),
            "dusk": ph((1.0, 0.80, 0.62), 0.80, (0.30, 0.32, 0.62), (0.92, 0.62, 0.30), 0.36, 0.34, 1.18, 0.2,
                       {"foliage": {"hue": 0, "sat": -0.20, "val": 0.0}}),
            "night": ph((0.78, 0.82, 1.0), 0.48, (0.26, 0.30, 0.56), (0.54, 0.52, 0.60), 0.28, 0.22, 0.85),
        },
        "sky": {"dawn": ["#384a7a", "#eaa47e", "#f8dcb4"], "day": ["#4a8ad0", "#a6cdee", "#eef2ee"],
                "dusk": ["#3e2e58", "#d8703e", "#f6c07a"], "night": ["#0e1532", "#202c52", "#2c3860"]},
        "sun": {"dawn": "#f4caa0", "day": "#fff6e0", "dusk": "#f6a860", "night": "#b0c4ea"},
        "shade": {"dawn": "#7c74ac", "day": "#7aa4d6", "dusk": "#665494", "night": "#283462"},
        "haze": {"colour": "#e8e2d4", "strength": 0.04, "toward": "north"},
        "stars": 0.8,
        "palette": {"large": {"grass": "#5da54a", "grass_shade": "#3e7a3a", "path": "#c9a46a"},
                    "accents": {"cottage_red": "#b8402f"}},
        "light": "storybook: saturated, soft, the warmest nights",
        "air": {},
        "water": {"body": "#4a8fb0", "reflect": True, "sea_state": 0},
    },
}

# The land and sea between (world.md §9.1): each starts from its set's family and changes these.
STRETCH = {
    "latium_italy": {"light": "warm green-gold, soft", "haze": 0.08,
                     "day": {"saturation": 1.0, "contrast": 0.32}},
    "apennines": {"light": "cooler and bluer", "haze": 0.10, "haze_colour": "#d6dce6",
                  "day": {"wb": [0.97, 0.98, 1.02], "shadow_tint": [0.28, 0.38, 0.74]}},
    "greece": {"light": "bright, dry, saturated", "haze": 0.05, "day": {"saturation": 1.08}},
    "attica_north": {"light": "bright, dry, saturated", "haze": 0.05},
    "arcadia": {"light": "bright, with cool shade in the hills", "haze": 0.08,
                "day": {"shadow_tint": [0.28, 0.38, 0.76]}},
    "thrace": {"light": "softer and greener than Attica", "haze": 0.08, "day": {"saturation": 1.0}},
    "ionia_lydia": {"light": "lush and green", "haze": 0.06,
                    "day": {"bands": {"foliage": {"hue": 0, "sat": 0.10, "val": 0.0}}}},
    "east_med": {"light": "bright, a sea haze toward the horizon", "haze": 0.10},
    "anatolia": {"light": "wide, pale gold under a cool sky", "haze": 0.10, "haze_colour": "#e3dfd3",
                 "day": {"wb": [0.98, 0.98, 1.02], "saturation": 0.94}},
    "mesopotamia": {"light": "humid gold, soft contrast, a heavy warm haze", "haze": 0.18,
                    "haze_colour": "#e8d9b8", "day": {"contrast": 0.26, "wb": [1.02, 0.99, 0.94]}},
    "susiana": {"light": "humid gold, soft contrast", "haze": 0.16, "haze_colour": "#e8d9b8",
                "day": {"contrast": 0.28}},
    "syrian_steppe": {"light": "bleached and high-contrast; heat shimmer", "haze": 0.12,
                      "haze_colour": "#ece2cc", "day": {"saturation": 0.86, "contrast": 0.50}},
    "taurus": {"light": "cool mountain light", "haze": 0.08, "haze_colour": "#d8dee8",
               "day": {"shadow_tint": [0.28, 0.38, 0.76]}},
    "zagros": {"light": "crisp, cold blue shadows", "haze": 0.04,
               "day": {"shadow_tint": [0.26, 0.38, 0.80]}},
    "iran_plateau": {"light": "clear, high, slightly cool", "haze": 0.04,
                     "day": {"wb": [0.98, 0.99, 1.02]}},
}
SEA_LOOK = {"light": "deep blue water, bright; a sea haze toward the horizon", "haze": 0.12,
            "haze_colour": "#dce6ee", "day": {"saturation": 1.06,
                                             "bands": {"water": {"hue": 0, "sat": 0.10, "val": -0.06}}}}
SEAM_LOOK = {"light": "a band of mist between two times", "haze": 0.30, "haze_colour": "#e8eaf0",
             "day": {"saturation": 0.86, "contrast": 0.24}}
# Weather tendencies by climate: the chance a day of each season brings a storm, fog or dust.
TENDENCY = {
    "mediterranean": {"spring": (0.05, 0.12, 0.0), "summer": (0.06, 0.02, 0.02),
                      "autumn": (0.12, 0.12, 0.0), "winter": (0.10, 0.18, 0.0)},
    "river_plain": {"spring": (0.05, 0.20, 0.05), "summer": (0.03, 0.05, 0.12),
                    "autumn": (0.06, 0.20, 0.05), "winter": (0.06, 0.30, 0.0)},
    "mountain": {"spring": (0.10, 0.25, 0.0), "summer": (0.15, 0.10, 0.0),
                 "autumn": (0.12, 0.30, 0.0), "winter": (0.10, 0.30, 0.0)},
    "east": {"spring": (0.08, 0.10, 0.08), "summer": (0.02, 0.02, 0.25),
             "autumn": (0.04, 0.08, 0.12), "winter": (0.06, 0.10, 0.0)},
    "steppe": {"spring": (0.08, 0.06, 0.10), "summer": (0.04, 0.0, 0.25),
               "autumn": (0.05, 0.06, 0.15), "winter": (0.06, 0.12, 0.02)},
    "sea": {"spring": (0.06, 0.05, 0.0), "summer": (0.04, 0.03, 0.0),
            "autumn": (0.15, 0.05, 0.0), "winter": (0.15, 0.08, 0.0)},
}
# §2.1: (p2, median, p98, mean saturation %, share above 55 %, warm, cool floor) per phase.
TARGETS = {
    "day": {"p2": [20, 45], "median": [100, 135], "p98": [205, 230], "sat_mean": [33, 48],
            "sat_high": [8, 30]},
    "dawn": {"p2": [10, 30], "median": [70, 125], "p98": [180, 215], "sat_mean": [30, 45],
             "sat_high": [0, 25], "warm": [35, 75], "cool_min": 7},
    "dusk": {"p2": [8, 25], "median": [45, 85], "p98": [165, 215], "sat_mean": [38, 55],
             "sat_high": [0, 40], "warm": [55, 80], "cool_min": 8},
    "night": {"p2": [4, 14], "median": [22, 45], "p98_lights_only": 200, "sat_mean": [18, 35],
              "sat_high": [0, 10], "cool_unlit_min": 50},
}
# Lights by kind of glowing piece (§3.2 P6): colour, radius in tiles, flicker.
LIGHTS = [
    (r"lighthouse", "beacon", "#ffb45a", 8.0, {"breathe": [0.5, 1.0], "depth": 0.10}),
    (r"beacon|watchtower", "beacon", "#ffa04a", 4.0, {"breathe": [0.8, 1.6], "depth": 0.15}),
    (r"brazier|fire_altar|altar|bonfire|hearth|kiln|oven|furnace|vesta|forge|charcoal",
     "fire", "#ff8a3c", 3.5, {"breathe": [1.0, 2.0], "depth": 0.15}),
    (r"torch|gate|wall|tower|station|camp", "torch", "#ff9a4a", 3.0, {"hz": [6, 9], "depth": 0.12}),
    (r"lamp|lantern|compitum|shrine|reed_hut|inn", "lamp", "#ffc27a", 2.5, {"hz": [6, 9], "depth": 0.08}),
    (r"house|insula|domus|taberna|thermopol|shop|villa|farm|hut|bath", "window", "#ffd08a", 1.5,
     {"stagger": ["18:00", "20:00"], "depth": 0.03}),
]
INTERIORS = {"parsa": ["parsa.apadana"], "athens": ["athens.parthenon"]}
# Backdrop strips along the world's far edges (world.md §11; the world page's `world.bd_*`).
BACKDROP_NORTH = {"corner": "world.bd_alps", "seam_dell": "world.bd_alps",
                  "latium_italy": "world.bd_alps", "apennines": "world.bd_alps",
                  "adriatic": "world.bd_far_hills", "greece": "world.bd_pindos",
                  "thrace": "world.bd_pontic", "anatolia": "world.bd_pontic",
                  "iran_plateau": "world.bd_plateau"}
BACKDROP_EAST = {"iran_plateau": "world.bd_plateau", "parsa": "world.bd_plateau"}
COAST_REGIONS = {"ostia", "brundisium", "corcyra", "delos", "ephesus", "sidon", "corinth",
                 "eleusis"}


SEA_FAMILY = {"tyrrhenian": "rome", "adriatic": "rome", "ionian_sea": "rome", "aegean": "athens",
              "saronic": "athens", "east_med": "athens", "persian_gulf": "parsa",
              "seam_ionian": "athens", "seam_ionia": "athens"}


def family_of(rid: str, set_: str) -> str:
    if rid in ("corner", "seam_dell"):
        return "home"
    if set_ in FAMILY:
        return set_
    return SEA_FAMILY.get(rid, "home")


def _deep(d):
    if isinstance(d, dict):
        return {k: _deep(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_deep(v) for v in d]
    return d


def region_look(rid: str, world: World, cat, root: Path) -> dict:
    kind, set_, *_ = P.REGIONS[rid]
    climate = sound.climate_of(rid)
    fam = family_of(rid, set_)
    base = _deep(FAMILY[fam])
    mods = STRETCH.get(rid) or (SEA_LOOK if climate == "sea" else SEAM_LOOK if kind == "seam"
                                else None)
    if climate == "river_plain" and rid not in STRETCH and kind == "town":
        mods = STRETCH["mesopotamia"] if set_ == "parsa" else {"haze": 0.10}
    if climate == "mountain" and rid not in STRETCH and kind == "town":
        mods = {"haze": 0.08, "day": {"shadow_tint": [0.28, 0.38, 0.76]}}
    look = {"phases": base["phases"], "sky": base["sky"], "sun": base["sun"], "shade": base["shade"],
            "haze": base["haze"], "stars": base["stars"], "palette": base["palette"],
            "light": base["light"]}
    if mods:
        look["light"] = mods.get("light", look["light"])
        if "haze" in mods:
            look["haze"]["strength"] = mods["haze"]
        if "haze_colour" in mods:
            look["haze"]["colour"] = mods["haze_colour"]
        for k, v in mods.get("day", {}).items():
            if k == "bands":
                look["phases"]["day"].setdefault("bands", {}).update(v)
            else:
                look["phases"]["day"][k] = v
    if climate == "sea":
        look["stars"] = max(look["stars"], 0.9)
    s = look["haze"]["strength"]
    look["haze"]["by_zoom"] = {"half": round(min(0.5, s + 0.07), 2),
                               "quarter": round(min(0.5, s + 0.14), 2),
                               "overview": round(min(0.5, s + 0.22), 2)}
    cool = 15 if (fam == "home" or climate == "sea" or rid in COAST_REGIONS) else 8
    look["targets"] = _deep(TARGETS) | {"day": TARGETS["day"] | {"cool_min": cool}}
    t = TENDENCY.get(climate, TENDENCY["mediterranean"])
    look["weather"] = {season: {"storm": a, "fog": b, "dust": c} for season, (a, b, c) in t.items()}
    look["air"] = _deep(base["air"]) | ({"night_mist": {"where": "water", "hours": ["22:00", "05:00"]}}
                                        if climate != "sea" else {"sea_mist": {"where": "horizon"}})
    if climate == "mountain":
        look["air"]["fog"] = {"where": "valleys", "hours": ["05:00", "08:00"]}
    look["water"] = _deep(base["water"]) | ({"sea_state": 1, "body": "#1f5e8c"} if climate == "sea"
                                            else {})
    lights = region_lights(world, cat, rid)
    if lights:
        look["lights"] = lights
    c0, r0, c1, r1 = P.REGIONS[rid][3]
    bd = {}
    if r0 <= 0 and rid in BACKDROP_NORTH:
        bd["north"] = {"id": BACKDROP_NORTH[rid], "span": [max(c0, 0), min(c1, 1279)]}
    if c1 >= 1279 and rid in BACKDROP_EAST:
        bd["east"] = {"id": BACKDROP_EAST[rid], "span": [max(r0, 0), min(r1, 447)]}
    if bd:
        look["backdrop"] = bd
    if rid in INTERIORS:
        look["interiors"] = INTERIORS[rid]
    return look


def region_lights(world: World, cat, rid: str) -> dict:
    idx = {i for i, n in enumerate(world.districts) if n.split("/", 1)[0] == rid}
    ids = sorted({it.id for _, it in live_items(world) if int(world.D[it.r, it.c]) in idx
                  and (d := cat.items.get(it.id)) is not None and d.glow})
    out = {}
    for iid in ids:
        name = iid.split(".")[-1]
        for pat, kind, colour, radius, flick in LIGHTS:
            if re.search(pat, name):
                out[iid] = {"kind": kind, "colour": colour, "radius": radius, "flicker": flick}
                break
        else:
            out[iid] = {"kind": "torch", "colour": "#ff9a4a", "radius": 3.0,
                        "flicker": {"hz": [6, 9], "depth": 0.12}}
    return out


def district_look(m: dict, air: dict, set_: str) -> dict:
    out = {}
    if m.get("water", 0) >= 0.02:
        out["reflect"] = True
    a = {}
    if "mist" in air and ((air["mist"]["where"] == "river" and m.get("river", 0) >= 0.05) or
                          (air["mist"]["where"] == "plain" and m.get("relief", 9) < 0.8
                           and m.get("roof", 1) < 0.2)):
        a["mist"] = air["mist"]
    if "shimmer" in air and m.get("paved", 0) >= 0.35:
        a["shimmer"] = air["shimmer"]
    if a:
        out["air"] = a
    if m.get("harbour", 0) >= 0.01:
        out["haze"] = {"toward": "sea", "strength_add": 0.03}
    return out


def apply(doc: dict, world: World, cat, root: Path) -> dict:
    rid = doc["id"]
    if rid not in P.REGIONS:
        return doc
    th = doc.setdefault("theme", {})
    th["look"] = region_look(rid, world, cat, root)
    set_ = P.REGIONS[rid][1]
    masks = sound._district_masks(world, rid)
    cover = sound._item_cover(world, cat)
    for d in doc.get("districts", []):
        m = masks.get(d["id"])
        if m is None or not m.any():
            continue
        dl = district_look(sound.measure(world, cat, m, cover), th["look"]["air"], set_)
        if dl:
            d["look"] = dl
        else:
            d.pop("look", None)
    return doc


# -- checking ------------------------------------------------------------------------------------

HEX = re.compile(r"^#[0-9a-f]{6}$")
RANGES = {"exposure": (0.2, 1.5), "tint": (0.0, 1.0), "contrast": (-1.0, 1.0),
          "saturation": (0.0, 2.0), "shoulder": (0.0, 1.0)}


def check(doc: dict) -> list[tuple[str, str, str]]:
    """[(level, where, message)] for `theme.look` and district looks: schema and ranges."""
    out = []
    look = doc.get("theme", {}).get("look")
    if look is None:
        return [("error", "theme", "has no `look`")]

    def bad(where, msg):
        out.append(("error", f"theme.look.{where}", msg))

    def rgb(where, v, lo, hi):
        if not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and lo <= x <= hi
                                                          for x in v)):
            bad(where, f"needs [r, g, b] in {lo}..{hi}, has {v!r}")

    def colour(where, v):
        if not (isinstance(v, str) and HEX.match(v)):
            bad(where, f"needs a colour '#rrggbb', has {v!r}")

    for p in PHASES:
        q = look.get("phases", {}).get(p)
        if q is None:
            bad(f"phases.{p}", "is missing")
            continue
        rgb(f"phases.{p}.wb", q.get("wb"), 0.3, 1.5)
        rgb(f"phases.{p}.shadow_tint", q.get("shadow_tint"), 0.0, 1.0)
        rgb(f"phases.{p}.high_tint", q.get("high_tint"), 0.0, 1.0)
        for k, (lo, hi) in RANGES.items():
            v = q.get(k)
            if not isinstance(v, (int, float)) or not lo <= v <= hi:
                bad(f"phases.{p}.{k}", f"needs {lo}..{hi}, has {v!r}")
        for name, b in q.get("bands", {}).items():
            if name not in ("terracotta", "foliage", "water", "stone"):
                bad(f"phases.{p}.bands", f"unknown band {name!r}")
            if not (-30 <= b.get("hue", 99) <= 30 and -0.5 <= b.get("sat", 9) <= 0.5
                    and -0.5 <= b.get("val", 9) <= 0.5):
                bad(f"phases.{p}.bands.{name}", "hue -30..30 degrees, sat and val -0.5..0.5")
        stops = look.get("sky", {}).get(p)
        if not (isinstance(stops, list) and len(stops) == 3):
            bad(f"sky.{p}", "needs three stops")
        else:
            for c in stops:
                colour(f"sky.{p}", c)
        colour(f"sun.{p}", look.get("sun", {}).get(p))
        colour(f"shade.{p}", look.get("shade", {}).get(p))
    h = look.get("haze", {})
    colour("haze.colour", h.get("colour"))
    if not 0 <= h.get("strength", -1) <= 0.5:
        bad("haze.strength", "needs 0..0.5")
    zs = [h.get("strength", 0)] + [h.get("by_zoom", {}).get(k, -1) for k in ("half", "quarter", "overview")]
    if any(not 0 <= z <= 0.5 for z in zs) or zs != sorted(zs):
        bad("haze.by_zoom", "half, quarter and overview rise from the 1x strength, within 0..0.5")
    if not 0 <= look.get("stars", -1) <= 1:
        bad("stars", "needs 0..1")
    for season, t in look.get("weather", {}).items():
        if season not in ("spring", "summer", "autumn", "winter"):
            bad("weather", f"unknown season {season!r}")
        for k in ("storm", "fog", "dust"):
            if not 0 <= t.get(k, -1) <= 1:
                bad(f"weather.{season}.{k}", "needs a chance 0..1")
    for iid, l in look.get("lights", {}).items():
        colour(f"lights.{iid}.colour", l.get("colour"))
        if l.get("kind") not in ("lamp", "torch", "fire", "window", "beacon"):
            bad(f"lights.{iid}.kind", f"unknown kind {l.get('kind')!r}")
        if not 0 < l.get("radius", 0) <= 12:
            bad(f"lights.{iid}.radius", "needs 0..12 tiles")
        f = l.get("flicker", {})
        if not 0 <= f.get("depth", -1) <= 0.3:
            bad(f"lights.{iid}.flicker", "depth 0..0.3")
    w = look.get("water", {})
    colour("water.body", w.get("body"))
    if w.get("sea_state") not in (0, 1, 2, 3):
        bad("water.sea_state", "needs 0..3")
    for edge, b in look.get("backdrop", {}).items():
        if edge not in ("north", "east") or not str(b.get("id", "")).startswith("world.bd_"):
            bad(f"backdrop.{edge}", "a world.bd_* strip on the north or east edge")
    for d in doc.get("districts", []):
        for k in d.get("look", {}):
            if k not in ("reflect", "air", "haze"):
                out.append(("error", f"district {d['id']}.look", f"unknown field {k!r}"))
    return out
