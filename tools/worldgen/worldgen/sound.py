"""The sound of a region file: what the engine needs to mix a place, derived from the built world
and the audio manifests (`assets/audio/<set>/manifest.json`; how each family is mixed is
`out/reports/audio-atmosphere.md`, "How the engine should mix").

Written into every region document by `apply` (city files through `lifereport`, the stretches,
seas, seams and towns through `life.write`):

- `theme.sound`: the region's character: `climate` (which nature beds), `crowd` (the voice
  family, `crowd.latin` / `crowd.greek` / `crowd.persian`), `nature` (the dawn, dusk and night
  beds), `stings` (sunrise, nightfall, storm clearing, rainbow, first snow), `wind` (the default
  wind family), `weather` (`heat`, `dust`, `fog`, `snow` where the climate has them), `cicadas`.
- `districts[].sound`: measured on the district's own tiles: rain `surfaces` (shares of stone,
  roof, leaves, water, canvas; the rest is soft ground under the plain rain bed), `wind` family
  and `exposure` 0..1, `water` (`sea.harbour`, `sea.coast` or `river` with `speed`), `steps`
  (the surface feet and hooves sound on), `cart` loop, `crowd` family with `full` (the visible
  people at which the festival level plays at full gain), and `nature` when the district's climate
  differs from the region's (a riverside quarter in a dry city).
- `events[]`: `sfx` (a one-shot when it starts), `ambience` (a loop that follows the cast while
  it runs), `sounds` (more cues: `at` `start`, `end` or a route node).
- `roles[]` that work: `sound` with `loop` (positional while the role works at its place) or
  `oneshot` (on its use frames).
- `theme.ambience.loops`: positional loops on every placed workplace, hearth, fire and fountain
  kind of the region's layer.

Every file or family named here exists in a manifest; `check` proves it, and that no event,
working role or populated district is silent.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from plan import world_plan as P

from .compose import NONE16, World, live_items

CHARACTER = {"rome": "latin", "athens": "greek", "parsa": "persian"}
# Nature beds by climate (manifest tags `mediterranean`, `river_plain`, `mountain`, `east`).
NATURE = {
    "mediterranean": ("amb/world/dawn_scrub.ogg", "amb/world/dusk_town.ogg", "amb/world/night_scrub.ogg"),
    "river_plain": ("amb/world/dawn_river.ogg", "amb/world/dusk_water.ogg", "amb/world/night_water.ogg"),
    "mountain": ("amb/world/dawn_mountain.ogg", "amb/world/dusk_town.ogg", "amb/world/night_mountain.ogg"),
    "east": ("amb/world/dawn_mountain.ogg", "amb/world/dusk_town.ogg", "amb/world/night_east.ogg"),
    "steppe": ("amb/world/dawn_scrub.ogg", "amb/world/dusk_town.ogg", "amb/world/night_east.ogg"),
}
CLIMATE = {
    "rome": "mediterranean", "athens": "mediterranean", "parsa": "east", "corner": "mediterranean",
    "latium_italy": "mediterranean", "greece": "mediterranean", "attica_north": "mediterranean",
    "thrace": "mediterranean", "east_med": "mediterranean", "ionia_lydia": "mediterranean",
    "apennines": "mountain", "arcadia": "mountain", "taurus": "mountain", "zagros": "mountain",
    "anatolia": "steppe", "syrian_steppe": "steppe", "iran_plateau": "east",
    "mesopotamia": "river_plain", "susiana": "river_plain", "babylon": "river_plain",
    "susa": "river_plain", "euphrates_crossing": "river_plain", "ostia": "river_plain",
    "persian_gates": "mountain", "delphi": "mountain", "alban_mount": "mountain",
    "tibur": "mediterranean", "halys": "steppe", "gordion": "steppe", "sardis": "mediterranean",
    "pasargadae": "east", "sidon": "mediterranean",
}
# Weather families by climate (the engine drives their intensity; look.md §3.6).
WEATHER = {"east": ["heat", "dust", "snow"], "steppe": ["heat", "dust", "snow"],
           "river_plain": ["heat", "fog"], "mountain": ["fog", "snow"],
           "mediterranean": ["fog"]}
CICADA_SETS = ("athens", "rome")
# Weather cues every region shares (the engine plays them by the weather's turns and the strike's
# distance: audio-atmosphere.md "Thunder", "Turns of weather").
TURNS = {"front": "sfx/world/gust_front.wav", "calm": "sfx/world/calm_before.wav",
         "drops": "sfx/world/first_drops.wav", "onset": "amb/world/rain_dust.ogg",
         "after": "amb/world/after_rain.ogg", "storm": "amb/world/storm.ogg"}
THUNDER = {"near": ["sfx/world/thunder_near_1.wav", "sfx/world/thunder_near_2.wav",
                    "sfx/world/thunder_near_3.wav"],
           "roll": ["sfx/world/thunder_roll_1.wav", "sfx/world/thunder_roll_2.wav",
                    "sfx/world/thunder_roll_3.wav"],
           "far": ["sfx/world/thunder_far.wav", "sfx/world/thunder_far_2.wav",
                   "sfx/world/thunder_far_3.wav"]}
# Steps and hooves by surface (three variations each, played at random, ±1.5 dB and ±3 % pitch).
STEPS = {s_: [f"sfx/world/step_{s_}_{k}.wav" for k in (1, 2, 3)]
         for s_ in ("stone", "earth", "timber", "stair")}
HOOVES = {"stone": ["sfx/world/hoof.wav"],
          "earth": ["sfx/world/hoof_earth_1.wav", "sfx/world/hoof_earth_2.wav"]}
SNOW_STEPS = {"step": ["sfx/world/step_snow.wav"], "group": "amb/world/snow_walk.ogg"}
# Animal voices by actor kind (the last part of its id), from the world manifest.
VOICES = {"sheep": ["sfx/world/sheep_1.wav", "sfx/world/sheep_2.wav"],
          "goat": ["sfx/world/goat_1.wav", "sfx/world/goat_2.wav"],
          "dog": ["sfx/world/dog_1.wav", "sfx/world/dog_2.wav"], "hound": ["sfx/world/dog_2.wav"],
          "donkey": ["sfx/world/donkey.wav"], "mule": ["sfx/world/donkey.wav"],
          "horse": ["sfx/world/horse_whinny.wav", "sfx/world/horse_blow.wav"],
          "racehorse": ["sfx/world/horse_whinny.wav", "sfx/world/horse_blow.wav"],
          "camel": ["sfx/world/camel_grumble.wav"], "dromedary": ["sfx/world/camel_grumble.wav"],
          "gull": ["sfx/world/gull_call.wav"], "pigeon": ["sfx/world/pigeon_coo.wav"],
          "crow": ["sfx/world/crow_1.wav", "sfx/world/crow_2.wav"],
          "raven": ["sfx/world/crow_1.wav", "sfx/world/crow_2.wav"],
          "stork": ["sfx/world/stork_clatter.wav"], "crane": ["sfx/world/cranes.wav"],
          "cat": ["sfx/cat_2.wav", "sfx/cat_3.wav"],
          "hen": ["sfx/hen_2.wav", "sfx/hen_3.wav"],
          "duck": ["sfx/duck_2.wav", "sfx/duck_3.wav"],
          "owl": ["sfx/world/owl_tawny.wav"], "athens.owl": ["sfx/athens/owl.wav"]}
# Calls the engine sprinkles over a climate's land (one at a time, far, by season and hour).
CALLS = {"mediterranean": [{"file": "sfx/world/cuckoo.wav", "seasons": ["spring"], "hours": ["06:00", "11:00"]},
                           {"file": "sfx/world/crow_2.wav", "hours": ["07:00", "18:00"]}],
         "mountain": [{"file": "sfx/world/crow_1.wav", "hours": ["07:00", "18:00"]},
                      {"file": "sfx/world/cuckoo.wav", "seasons": ["spring"], "hours": ["06:00", "11:00"]}],
         "east": [{"file": "sfx/parsa/hoopoe.wav", "seasons": ["spring", "summer"], "hours": ["06:00", "12:00"]},
                  {"file": "sfx/world/stork_clatter.wav", "seasons": ["spring", "summer"], "hours": ["07:00", "17:00"]}],
         "steppe": [{"file": "sfx/world/crow_1.wav", "hours": ["07:00", "18:00"]}],
         "river_plain": [{"file": "sfx/world/cranes.wav", "seasons": ["autumn", "spring"], "hours": ["06:00", "18:00"]},
                         {"file": "sfx/world/stork_clatter.wav", "seasons": ["spring", "summer"], "hours": ["07:00", "17:00"]}],
         "sea": [{"file": "sfx/world/gull_call.wav", "hours": ["06:00", "19:00"]}]}
# A district's people at which the festival crowd plays at full gain, by area kind.
CROWD_FULL = {"centre": 30, "town": 20, "country": 8, "road": 6}
ANIMALS = {"dog", "cat", "hen", "goose", "goat", "sheep", "pig", "ox", "donkey", "mule", "horse",
           "racehorse", "camel", "dromedary", "pigeon", "gull", "swallow", "stork", "eagle", "crane",
           "swift", "raven", "heron", "duck", "owl", "bee", "butterfly", "gazelle", "hound", "boar",
           "fishing_boat", "reed_boat", "quffa", "kelek", "barge", "merchantman", "trireme"}
PAVED = ("paving", "basalt", "travertine", "marble", "royal", "gravel", "flag", "ashlar",
         "brick", "stone", "slab", "pavement", "terrace")
EARTHY = ("earth", "path", "dirt", "sand", "steppe", "dust", "field", "grass", "meadow")
CANVAS = ("tent", "stall", "awning", "canopy", "pavilion")
HARBOUR_ITEMS = ("mole", "jetty", "quay", "harbour", "emporium", "hexagon", "shipshed")
WINDS = ("open", "street", "sea", "mountain")


# -- manifests ---------------------------------------------------------------------------------

@lru_cache(maxsize=4)
def manifests(root: Path) -> tuple[set[str], dict[str, list[str]]]:
    """(every file listed in a manifest and present, family -> files) over all audio sets."""
    files: set[str] = set()
    fam: dict[str, list[str]] = {}
    for f in sorted((root / "assets/audio").glob("*/manifest.json")):
        for e in json.loads(f.read_text()).get("files", []):
            if (root / "assets/audio" / e["file"]).exists():
                files.add(e["file"])
                if e.get("family"):
                    fam.setdefault(e["family"], []).append(e["file"])
    return files, fam


# -- measuring a district ----------------------------------------------------------------------

def _district_masks(world: World, rid: str) -> dict[str, np.ndarray]:
    out = {}
    for i, name in enumerate(world.districts):
        if name.split("/", 1)[0] == rid:
            out[name.split("/", 1)[1]] = world.D == i
    return out


def _item_cover(world: World, cat) -> dict[str, np.ndarray]:
    """Boolean maps of what stands on each tile: roofs (buildings and landmarks), leaves
    (trees and big plants), canvas (tents, stalls), harbour works."""
    roof = np.zeros(world.D.shape, dtype=bool)
    leaves = np.zeros_like(roof)
    canvas = np.zeros_like(roof)
    harbour = np.zeros_like(roof)
    stairs = np.zeros_like(roof)
    decks = np.zeros_like(roof)
    for _, it in live_items(world):
        d = cat.items.get(it.id)
        if d is None:
            continue
        name = it.id.split(".")[-1]
        sl = (slice(it.r, it.r + it.ph), slice(it.c, it.c + it.pw))
        if d.rise > 0:
            stairs[sl] = True
        if d.walkable and d.on == "water":
            decks[sl] = True
        if any(k in name for k in CANVAS):
            canvas[sl] = True
        elif any(k in name for k in HARBOUR_ITEMS):
            harbour[sl] = True
        elif name.startswith("t_") or "tree" in name or "grove" in name:
            leaves[sl] = True
        elif d.landmark or d.has_door or (d.height or 0) >= 30:
            if d.rise == 0 and not d.walkable:
                roof[sl] = True
    return {"roof": roof, "leaves": leaves, "canvas": canvas, "harbour": harbour, "stairs": stairs,
            "decks": decks}


def measure(world: World, cat, mask: np.ndarray, cover: dict) -> dict:
    """Shares of what rain falls on, water kinds, heights and walking surfaces in `mask`."""
    n = int(mask.sum())
    if n == 0:
        return {}
    T = world.T[mask]
    ids = [world.terrains[t] if t != NONE16 else "" for t in range(len(world.terrains))]
    tid = np.array(ids + [""], dtype=object)[np.where(T == NONE16, len(ids), T)]
    water = np.array([cat.is_water(t) for t in tid])
    sea = np.array(["sea" in t or "shallow" in t for t in tid]) & water
    paved = np.array([any(k in t for k in PAVED) for t in tid]) & ~water
    earthy = np.array([any(k in t for k in EARTHY) for t in tid]) & ~water
    roof = cover["roof"][mask]
    leaves = cover["leaves"][mask] & ~roof
    canvas = cover["canvas"][mask] & ~roof
    stone = paved & ~roof & ~leaves & ~canvas
    lv = (world.L[mask] & 0x0F).astype(float)
    share = lambda m: round(float(m.sum()) / n, 2)
    return {"stairs": int(cover["stairs"][mask].sum()), "decks": int(cover["decks"][mask].sum()),
            "stone": share(stone), "roof": share(roof), "leaves": share(leaves),
            "water": share(water), "canvas": share(canvas), "sea": share(sea),
            "river": share(water & ~sea), "paved": share(paved), "earthy": share(earthy),
            "harbour": share(cover["harbour"][mask]), "level": float(lv.mean()),
            "relief": float(lv.std())}


# -- the region's and districts' sound -----------------------------------------------------------

def climate_of(rid: str) -> str:
    kind, set_, *_ = P.REGIONS.get(rid, ("stretch", "world", None, None, 0))
    if rid in CLIMATE:
        return CLIMATE[rid]
    if kind in ("sea",) or rid.endswith("_sea") or rid in SEAS:
        return "sea"
    return {"rome": "mediterranean", "athens": "mediterranean", "parsa": "east"}.get(set_, "mediterranean")


SEAS = {"tyrrhenian", "adriatic", "ionian_sea", "aegean", "saronic", "persian_gulf"}


def nature(climate: str) -> dict | None:
    if climate not in NATURE:
        return None
    d, u, n = NATURE[climate]
    return {"dawn": d, "dusk": u, "night": n}


def stings(set_: str, rid: str) -> dict:
    if set_ in ("rome", "athens", "parsa"):
        out = {k: f"sfx/{set_}/sting_{k}.wav" for k in ("sunrise", "nightfall", "storm_clear",
                                                         "rainbow")}
        if set_ == "parsa":
            out["first_snow"] = "sfx/parsa/sting_first_snow.wav"
        return out
    # Home's own stings (its rainbow is the catalog's `sfx/rainbow.wav`, in no manifest).
    return {"sunrise": "sfx/sting_sunrise.wav", "nightfall": "sfx/sting_nightfall.wav",
            "storm_clear": "sfx/sting_storm_clear.wav", "first_snow": "sfx/sting_first_snow.wav"}


def district_sound(m: dict, area: str | None, people: bool, char: str | None,
                   climate: str, mountain: bool) -> dict:
    if not m:
        return {}
    built = m["roof"] + m["stone"]
    if m["sea"] >= 0.4:
        wind = "wind.sea"
    elif built >= 0.4:
        wind = "wind.street"
    elif mountain or m["level"] >= 7 or m["relief"] >= 2.0:
        wind = "wind.mountain"
    else:
        wind = "wind.open"
    surfaces = {k: m[k] for k in ("stone", "roof", "leaves", "water", "canvas") if m[k] >= 0.02}
    out: dict = {"surfaces": surfaces, "wind": wind,
                 "exposure": round(float(np.clip(1.0 - m["roof"] * 0.8 + (0.2 if mountain else 0),
                                                 0.2, 1.0)), 2)}
    if m["harbour"] >= 0.01 and m["sea"] >= 0.02:
        out["water"] = {"family": "sea.harbour"}
    elif m["sea"] >= 0.05:
        out["water"] = {"family": "sea.coast"}
    elif m["river"] >= 0.03:
        out["water"] = {"family": "river", "speed": "fast" if mountain else "slow"}
    surface = "stone" if m["paved"] >= m["earthy"] * 0.5 and m["paved"] >= 0.05 else "earth"
    out["steps"] = {"surface": surface, "files": STEPS[surface], "hooves": HOOVES[surface]}
    if m.get("stairs", 0) > 0:
        out["steps"]["stairs"] = STEPS["stair"]
    if m.get("decks", 0) > 0:
        out["steps"]["decks"] = STEPS["timber"]
    out["cart"] = "amb/world/cart.ogg" if surface == "stone" else "amb/world/cart_earth.ogg"
    if people and char:
        out["crowd"] = {"family": f"crowd.{char}", "full": CROWD_FULL.get(area or "", 12)}
    if m["river"] >= 0.12 and climate != "river_plain":
        out["nature"] = nature("river_plain")
    return out


def _falls(world: World, rid: str) -> bool:
    """Whether the region holds a fall: two water tiles side by side on different levels."""
    idx = [i for i, n in enumerate(world.districts) if n.split("/", 1)[0] == rid]
    if not idx:
        return False
    mine = np.isin(world.D, idx)
    water_ids = [i for i, t in enumerate(world.terrains) if "river" in t or t == "water"]
    wet = np.isin(world.T, water_ids) & mine
    lv = world.L & 0x0F
    for a, b in ((wet[:, 1:] & wet[:, :-1], (lv[:, 1:] != lv[:, :-1])),
                 (wet[1:, :] & wet[:-1, :], (lv[1:, :] != lv[:-1, :]))):
        if (a & b).any():
            return True
    return False


# -- events ------------------------------------------------------------------------------------

def _crowd(char: str | None, level: int) -> str:
    return f"amb/world/crowd_{char or 'latin'}_{level}.ogg"


def event_rules(set_: str, char: str | None) -> list[tuple[str, dict]]:
    """(event id pattern, sound fields) in order; a field already set is kept."""
    rite = {"rome": "sfx/rome/acclamation.wav", "athens": "sfx/athens/ololyge.wav",
            "parsa": "sfx/parsa/response.wav"}.get(set_, "sfx/world/hush.wav")
    proc = {"rome": "amb/rome/procession.ogg", "athens": "amb/athens/procession.ogg",
            "parsa": "amb/parsa/procession.ogg"}.get(set_, "amb/world/walk_group.ogg")
    sting = stings(set_, "")
    sting.setdefault("rainbow", sting["storm_clear"])
    amb = lambda f, g=0.8: {"file": f, "gain": g}
    c1, c2, c3 = (amb(_crowd(char, k)) for k in (1, 2, 3))
    return [
        (r"sacrificial_feast", {"sfx": rite, "ambience": c3}),
        (r"feast|saturnalia|vinalia|vestalia|lupercalia|festival", {"ambience": c3}),
        (r"market|grain_dole|ration", {"ambience": c2}),
        (r"arena|ludi_|races|chariot|athlete|torch_race", {"sfx": "sfx/world/cheer.wav",
                                                          "ambience": c2}),
        (r"trial|senate|assembly|law_court|judge", {"ambience": c2,
                                                   "sounds": [{"file": "sfx/world/hush.wav",
                                                               "at": "start"}]}),
        (r"recitation|performer|rhapsode|theatre|dionysia|rehearsal",
         {"ambience": c1, "sounds": [{"file": "sfx/world/applause.wav", "at": "end"}]}),
        (r"mysteries", {"ambience": amb(proc), "sfx": "sfx/world/chorus_far.wav"}),
        (r"sacrifice|offering|bagayadi|prayer|fumigant|purification",
         {"sfx": "sfx/world/hush.wav", "sounds": [{"file": rite, "at": "end"}],
          "ambience": amb("amb/world/brazier.ogg", 0.7)}),
        (r"bonfire|fire_evening", {"ambience": amb("amb/world/bonfire.ogg")}),
        (r"guard_change|hoplites|vigiles|recruit|drill|royal_ride",
         {"ambience": amb("amb/world/march.ogg")}),
        (r"vestals_walk|funeral", {"ambience": amb("amb/world/walk_group.ogg"),
                                          "sounds": [{"file": "sfx/world/hush.wav", "at": "start"}]}),
        (r"wedding", {"sfx": "sfx/world/wedding_song.wav", "ambience": c1}),
        (r"procession|pompa|audience", {"ambience": amb(proc)}),
        (r"summer_storm", {"sfx": "sfx/world/gust_front.wav",
                           "sounds": [{"file": sting["storm_clear"], "at": "end"}]}),
        (r"shower|tishtrya", {"sfx": "sfx/world/first_drops.wav",
                              "sounds": [{"file": sting["storm_clear"], "at": "end"}]}),
        (r"rainbow", {"sfx": sting["rainbow"]}),
        (r"mist|fog", {"ambience": amb("amb/world/fog.ogg")}),
        (r"meltemi|gust", {"ambience": amb("amb/world/wind_sea_3.ogg")}),
        (r"dust", {"ambience": amb("amb/world/dust_1.ogg")}),
        (r"caravan|courier", {"ambience": amb("amb/world/hooves_walk.ogg"),
                              "sfx": "sfx/world/camel_grumble.wav"}),
        (r"olive", {"ambience": amb("amb/world/press.ogg")}),
        (r"reaper|harvest|planting", {"sfx": "sfx/world/sickle.wav"}),
        (r"thresh", {"ambience": amb("amb/world/threshing.ogg")}),
        (r"tablet|graffiti", {"sfx": "sfx/world/stylus.wav"}),
        (r"lamps|torches|lighthouse|beacon", {"sfx": "sfx/world/lamp.wav"}),
        (r"kiln", {"ambience": amb("amb/athens/kiln.ogg" if set_ == "athens"
                                   else "amb/world/hearth.ogg")}),
        (r"crane", {"ambience": amb("amb/rome/treadwheel.ogg")}),
        (r"barge|towing|ship|fleet|trireme|tribute", {"ambience": amb("amb/world/ship.ogg"),
                                                     "sfx": "sfx/world/rope.wav"}),
        (r"night_cart", {"ambience": amb("amb/world/cart.ogg")}),
        (r"fire_alarm", {"ambience": c2, "sfx": "sfx/world/vendor.wav"}),
        (r"dog|hound", {"sfx": "sfx/world/dog_1.wav"}),
        (r"cat_", {"sfx": "sfx/cat_2.wav"}),
        (r"pigeon", {"sfx": "sfx/world/pigeons_up.wav"}),
        (r"starling|swift", {"sfx": "sfx/world/swifts.wav"}),
        (r"stork", {"sfx": "sfx/world/stork_clatter.wav"}),
        (r"owl", {"sfx": "sfx/athens/owl.wav"}),
        (r"flock", {"sfx": "sfx/world/sheep_bells.wav"}),
        (r"water_turn|fountain", {"sfx": "sfx/world/pour.wav", "ambience": c1}),
        (r"memory|apparition|dioscuri|saena|scipio|hut_of_romulus|meton",
         {"sfx": "sfx/world/chorus_far.wav"}),
        (r"woodcut", {"sfx": "sfx/world/chop.wav"}),
        (r"hadrian_site", {"sfx": "sfx/world/hammer.wav"}),
        (r"music|mesomedes", {"sfx": "sfx/athens/lyre.wav" if set_ != "parsa"
                              else "sfx/parsa/audience.wav"}),
        (r"salutatio|quarrel|philosopher|protagoras|symposium|storyteller|dine|guild|customs|"
         r"megarian|visit|road_end|arriv|depart|unload", {"ambience": c1}),
    ]


def wire_event(e: dict, rules, char: str | None) -> None:
    for pat, fields in rules:
        if re.search(pat, e["id"]):
            for k, v in fields.items():
                if k == "sounds":
                    have = {s["file"] for s in e.get("sounds", [])}
                    e.setdefault("sounds", []).extend(s for s in v if s["file"] not in have)
                elif not e.get(k):
                    e[k] = v
            break
    if not event_sound(e):
        size = {"small": 1, "medium": 2, "large": 3}.get(e.get("size"), 1)
        e["ambience"] = {"file": _crowd(char, size), "gain": 0.7}


def event_sound(e: dict) -> bool:
    if e.get("sfx") or e.get("ambience") or e.get("sounds"):
        return True
    return any("emit" in s and isinstance(s["emit"], dict) and s["emit"].get("sfx")
               for s in _steps(e.get("steps", [])))


def _steps(steps):
    for s in steps:
        if not isinstance(s, dict):
            continue
        yield s
        for k in ("pick", "each", "if", "steps", "then", "else"):
            v = s.get(k)
            if isinstance(v, list):
                yield from _steps(v)


# -- working roles -----------------------------------------------------------------------------

WORK_ANIMS = {"work_low", "work_high", "haul", "serve", "stir", "pour", "throw", "write",
              "scrape", "carry_idle"}
# (pattern on the role's id, name and home item, sound); the first that matches.
ROLE_SOUNDS = [
    (r"crane|treadwheel", {"loop": "amb/rome/treadwheel.ogg"}),
    (r"cart|wagon", {"loop": "amb/world/cart.ogg"}),
    (r"caravan|camel|muleteer|driver|drover|mule", {"loop": "amb/world/hooves_walk.ogg"}),
    (r"bak|oven|bread", {"loop": "amb/world/bakery.ogg"}),
    (r"mill|grind|quern", {"loop": "amb/world/mill.ogg"}),
    (r"olive|press|oil", {"loop": "amb/world/press.ogg"}),
    (r"thresh", {"loop": "amb/world/threshing.ogg"}),
    (r"saw|carpent|cedar|timber|shipwright|joiner", {"loop": "amb/world/saw.ogg"}),
    (r"full|dye|cloth|wash", {"loop": "amb/world/fullers.ogg"}),
    (r"weav|loom|spin|wool|yarn", {"loop": "amb/world/loom.ogg"}),
    (r"caster|bronze", {"loop": "amb/world/smith.ogg", "oneshot": "sfx/world/bronze.wav"}),
    (r"smith|forge|armour|shield|metal", {"loop": "amb/world/smith.ogg"}),
    (r"dumper|sherd|testaccio", {"oneshot": "sfx/world/smash.wav"}),
    (r"potter", {"loop": "amb/athens/wheel.ogg"}),
    (r"kiln|stoker|furnace|glass|cook|counter|thermopol|hearth", {"loop": "amb/world/hearth.ogg"}),
    (r"scribe|clerk|tally|write|account|treasur|school|pupil|record|steward|paint",
     {"oneshot": "sfx/world/stylus.wav"}),
    (r"dock|sailor|rower|haul|barge|rope|crew|moor|sledge", {"oneshot": "sfx/world/rope.wav"}),
    (r"brick|clay|dig", {"oneshot": "sfx/world/brick.wav"}),
    (r"mason|carv|sculpt|stone|quarr|chisel|relief", {"oneshot": "sfx/world/chisel.wav"}),
    (r"build|scaffold|labour|site|roof|repair|column|setter|wall|cobbler|workman",
     {"oneshot": "sfx/world/hammer.wav"}),
    (r"reap|harvest|farmer|field|gardener|vine|sickle|plough|planter", {"oneshot": "sfx/world/sickle.wav"}),
    (r"fish", {"oneshot": "sfx/world/fish.wav"}),
    (r"wood|logger|charcoal|chop", {"oneshot": "sfx/world/chop.wav"}),
    (r"water|fountain|fill|aquari|well", {"oneshot": "sfx/world/pour.wav"}),
    (r"porter|carrier|bearer|amphora|warehouse|dump|unload|load|store", {"oneshot": "sfx/world/amphora.wav"}),
    (r"shepherd|herd|flock", {"oneshot": "sfx/world/sheep_bells.wav"}),
    (r"groom|horse|stable|rider", {"oneshot": "sfx/world/horse_blow.wav"}),
    (r"athlete|wrestl|exercis|runner", {"oneshot": "sfx/world/step_earth_1.wav"}),
    (r"sell|shop|stall|vendor|trader|merchant|market|keeper|banker", {"oneshot": "sfx/world/vendor.wav"}),
    (r"priest|magus|vestal|flamen|ritual|altar", {"loop": "amb/world/brazier.ogg"}),
    (r"courtier|servant|attendant|maid|housewife|household|townswoman|slave|woman",
     {"oneshot": "sfx/world/pour.wav"}),
]


def working(role: dict) -> bool:
    return any(s.get("anim") in WORK_ANIMS for rt in role.get("routines", {}).values()
               for s in _steps(rt.get("steps", [])) if "use" in s)


def role_sound(role: dict, chained: set[str]) -> dict | None:
    if not (working(role) or role["id"] in chained):
        return None
    key = " ".join([role["id"], role.get("name", "").lower(),
                    str(role.get("home", {}).get("item", ""))])
    for pat, snd in ROLE_SOUNDS:
        if re.search(pat, key):
            return dict(snd)
    anims = {s.get("anim") for rt in role.get("routines", {}).values()
             for s in _steps(rt.get("steps", [])) if "use" in s}
    if "write" in anims:
        return {"oneshot": "sfx/world/stylus.wav"}
    if "haul" in anims or "carry_idle" in anims:
        return {"oneshot": "sfx/world/amphora.wav"}
    if "pour" in anims:
        return {"oneshot": "sfx/world/pour.wav"}
    if "serve" in anims:
        return {"oneshot": "sfx/world/vendor.wav"}
    return {"oneshot": "sfx/world/hammer.wav"}


# -- positional loops on placed kinds -------------------------------------------------------------

ITEM_LOOPS = [
    (r"bakery|r_bakery", "amb/world/bakery.ogg", "worked"),
    (r"mill", "amb/world/mill.ogg", "worked"),
    (r"press", "amb/world/press.ogg", "worked"),
    (r"threshing", "amb/world/threshing.ogg", "worked"),
    (r"fullonica|dyeworks|dye", "amb/world/fullers.ogg", "worked"),
    (r"loom", "amb/world/loom.ogg", "worked"),
    (r"smithy|forge", "amb/world/smith.ogg", "worked"),
    (r"oven|kiln|glass", "amb/world/hearth.ogg", "lit"),
    (r"brazier|fire_altar|torch|beacon|watchtower", "amb/world/brazier.ogg", "lit"),
    (r"lacus|fountain|nymphae|meta_sudans|iuturnae|krene|basin|spring", "amb/rome/fountain.ogg",
     "always"),
    (r"bath", "amb/rome/baths.ogg", "afternoon"),
    (r"crane", "amb/rome/treadwheel.ogg", "worked"),
    (r"inn|thermopolium|tavern", "amb/world/hearth.ogg", "lit"),
]


def placed_loops(world: World, rid: str, have: list[dict]) -> list[dict]:
    """Loops for every placed kind of the region that has none yet."""
    ids = set()
    names = {n for n in world.districts if n.split("/", 1)[0] == rid}
    idx = {i for i, n in enumerate(world.districts) if n in names}
    for _, it in live_items(world):
        if int(world.D[it.r, it.c]) in idx:
            ids.add(it.id)
    known = {x.get("item") for x in have} | {x.get("slot", "").rsplit(".", 1)[0] for x in have}
    out = []
    for iid in sorted(ids - known):
        name = iid.split(".")[-1]
        for pat, f, when in ITEM_LOOPS:
            if re.search(pat, name):
                out.append({"item": iid, "file": f, "when": when})
                break
    return out


# -- applying ------------------------------------------------------------------------------------

def apply(doc: dict, world: World, cat, root: Path) -> dict:
    """Fill a region document's sound (see the module docstring); keeps what it already names."""
    rid = doc["id"]
    kind, set_, *_ = P.REGIONS.get(rid, ("stretch", "world", None, None, 0))
    char = CHARACTER.get(set_)
    climate = climate_of(rid)
    mountain = climate == "mountain"
    th = doc.setdefault("theme", {})
    snd = th.setdefault("sound", {})
    snd.setdefault("climate", climate)
    if char:
        snd.setdefault("crowd", f"crowd.{char}")
    if nature(climate):
        snd.setdefault("nature", nature(climate))
    from .places import side
    snd.setdefault("stings", stings(side(rid) or set_, rid))
    snd.setdefault("wind", "wind.sea" if climate == "sea" else
                   "wind.mountain" if mountain else "wind.open")
    snd.setdefault("weather", WEATHER.get(climate, []))
    if set_ in CICADA_SETS and climate in ("mediterranean",) and "cicadas" not in th.get("ambience", {}):
        snd.setdefault("cicadas", {"family": "cicadas", "hours": ["09:00", "18:00"],
                                   "seasons": ["summer"], "weather": "clear", "fade_s": 20})
    snd.setdefault("rain", {"family": "rain", "snow": "snow"})
    snd.setdefault("turns", dict(TURNS))
    snd.setdefault("thunder", {k: list(v) for k, v in THUNDER.items()})
    if "snow" in snd["weather"]:
        snd.setdefault("snow_steps", dict(SNOW_STEPS))
    if CALLS.get(climate):
        snd.setdefault("calls", CALLS[climate])
    kinds = {r.get("actor", "") for r in doc.get("roles", [])}
    for d in doc.get("districts", []):
        kinds |= {p.get("actor", "") for p in d.get("populations", [])}
    for g in doc.get("groups", []):
        kinds |= {m.get("actor", "") for m in [g.get("leader", {})] + g.get("members", [])}
    voices = {k: VOICES.get(k) or VOICES[k.split(".")[-1]] for k in sorted(kinds)
              if k and (k in VOICES or k.split(".")[-1] in VOICES)}
    if voices:
        snd.setdefault("voices", voices)
    if _falls(world, rid):
        snd.setdefault("waterfall", "waterfall")
    if kind == "seam":
        snd["seam"] = {"bed": "amb/world/seam.ogg", "chime": "sfx/world/seam.wav", "duck_db": 6}
    masks = _district_masks(world, rid)
    cover = _item_cover(world, cat)
    roles = {r["id"]: r for r in doc.get("roles", [])}
    for d in doc.get("districts", []):
        m = masks.get(d["id"])
        if m is None or not m.any():
            continue
        kinds = [(roles.get(p.get("role"), {}).get("actor") or p.get("actor") or "")
                 for p in d.get("populations", [])]
        people = any(k and k.split(".")[-1] not in ANIMALS for k in kinds)
        ds = district_sound(measure(world, cat, m, cover), d.get("area"), people, char,
                            climate, mountain or d["id"] in ("cliffs", "summit", "woods", "slope"))
        d["sound"] = d.get("sound", {}) | {k: v for k, v in ds.items() if k not in d.get("sound", {})}
    rules = event_rules(set_, char)
    for e in doc.get("events", []):
        wire_event(e, rules, char)
    chained = {st.get("by") for c in doc.get("chains", []) for st in c.get("stages", [])}
    for r in doc.get("roles", []):
        s = role_sound(r, chained)
        if s and "sound" not in r:
            r["sound"] = s
    amb = th.setdefault("ambience", {})
    amb["loops"] = amb.get("loops", []) + placed_loops(world, rid, amb.get("loops", []))
    from . import soundplan
    return soundplan.apply(doc, world, cat, root)


# -- checking ------------------------------------------------------------------------------------

def audio_names(doc: dict):
    """(where, name, kind) for every audio file or family a region document names."""
    th = doc.get("theme", {})
    amb = th.get("ambience", {})
    for b in amb.get("beds", []) + amb.get("zones", []) + amb.get("loops", []):
        yield "theme.ambience", b["file"], "file"
    for sid, se in th.get("seasons", {}).items():
        for b in (se.get("ambience") or {}).get("beds", []):
            yield f"theme.seasons.{sid}.ambience", b["file"], "file"
    for f in amb.get("one_shots", {}).values():
        yield "theme.ambience.one_shots", f, "file"
    for k in ("day", "night"):
        if th.get("music", {}).get(k):
            yield "theme.music", th["music"][k], "file"
    if th.get("arrive"):
        yield "theme.arrive", th["arrive"], "file"
    s = th.get("sound", {})
    for k in ("crowd", "wind"):
        if s.get(k):
            yield f"theme.sound.{k}", s[k], "family"
    for k, f in (s.get("nature") or {}).items():
        yield f"theme.sound.nature.{k}", f, "file"
    for sid, ph in (s.get("nature_seasons") or {}).items():
        for k, f in ph.items():
            if f:
                yield f"theme.sound.nature_seasons.{sid}.{k}", f, "file"
    for k, f in (s.get("nature_snow") or {}).items():
        yield f"theme.sound.nature_snow.{k}", f, "file"
    for k, f in s.get("stings", {}).items():
        yield f"theme.sound.stings.{k}", f, "file"
    for w in s.get("weather", []):
        yield "theme.sound.weather", w, "family"
    if s.get("cicadas"):
        yield "theme.sound.cicadas", s["cicadas"]["family"], "family"
    if s.get("seam"):
        yield "theme.sound.seam", s["seam"]["bed"], "file"
        yield "theme.sound.seam", s["seam"]["chime"], "file"
    if s.get("rain"):
        yield "theme.sound.rain", s["rain"]["family"], "family"
        yield "theme.sound.rain", s["rain"]["snow"], "family"
    for k, f in s.get("turns", {}).items():
        yield f"theme.sound.turns.{k}", f, "file"
    for k, fs in s.get("thunder", {}).items():
        for f in fs:
            yield f"theme.sound.thunder.{k}", f, "file"
    for k, v in s.get("snow_steps", {}).items():
        for f in (v if isinstance(v, list) else [v]):
            yield "theme.sound.snow_steps", f, "file"
    for c in s.get("calls", []):
        yield "theme.sound.calls", c["file"], "file"
    for k, fs in s.get("voices", {}).items():
        for f in fs:
            yield f"theme.sound.voices.{k}", f, "file"
    if s.get("waterfall"):
        yield "theme.sound.waterfall", s["waterfall"], "family"
    for d in doc.get("districts", []):
        ds = d.get("sound", {})
        w = f"district {d['id']}"
        if ds.get("wind"):
            yield w, ds["wind"], "family"
        if ds.get("water"):
            yield w, ds["water"]["family"], "family"
        if ds.get("crowd"):
            yield w, ds["crowd"]["family"], "family"
        if ds.get("cart"):
            yield w, ds["cart"], "file"
        for k, f in (ds.get("nature") or {}).items():
            yield w, f, "file"
        for k in ds.get("surfaces", {}):
            yield w, f"rain.{k}", "family"
        st = ds.get("steps", {})
        for k in ("files", "hooves", "stairs", "decks"):
            for f in st.get(k, []):
                yield w, f, "file"
    for e in doc.get("events", []):
        w = f"event {e['id']}"
        if e.get("sfx"):
            yield w, e["sfx"], "file"
        if e.get("ambience"):
            yield w, e["ambience"]["file"], "file"
        for x in e.get("sounds", []):
            yield w, x["file"], "file"
        for st in _steps(e.get("steps", [])):
            if "emit" in st and isinstance(st["emit"], dict) and st["emit"].get("sfx"):
                yield w, st["emit"]["sfx"], "file"
    for r in doc.get("roles", []):
        for k in ("loop", "oneshot"):
            if r.get("sound", {}).get(k):
                yield f"role {r['id']}", r["sound"][k], "file"


def check(doc: dict, files: set[str], families: dict) -> list[tuple[str, str, str]]:
    """[(level, where, message)]: names that exist in no manifest; silent events, working roles
    and populated districts; the year's beds, festivals and loops (`soundplan.check`)."""
    from . import soundplan
    out = soundplan.check(doc)
    for where, name, kind in audio_names(doc):
        if kind == "file" and name not in files:
            out.append(("error", where, f"sound {name!r} is in no audio manifest"))
        if kind == "family" and name not in families:
            out.append(("error", where, f"sound family {name!r} is in no audio manifest"))
    for e in doc.get("events", []):
        if not event_sound(e):
            out.append(("error", f"event {e['id']}", "is silent (no sfx, ambience or sounds)"))
    loops = doc.get("theme", {}).get("ambience", {}).get("loops", [])
    looped = {x.get("item") for x in loops} | {x.get("slot") for x in loops}
    chained = {st.get("by") for c in doc.get("chains", []) for st in c.get("stages", [])}
    for r in doc.get("roles", []):
        if (working(r) or r["id"] in chained) and not r.get("sound"):
            home = r.get("home", {})
            if home.get("item") not in looped and f"{home.get('item')}.{home.get('slot')}" not in looped:
                out.append(("error", f"role {r['id']}", "works without a sound (no `sound`, no loop "
                            "on its place)"))
    for d in doc.get("districts", []):
        if d.get("populations") and not (d.get("sound", {}).get("crowd") or
                                         d.get("sound", {}).get("surfaces") is not None):
            out.append(("error", f"district {d['id']}", "is populated but has no sound"))
    return out
