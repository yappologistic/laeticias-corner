"""Lit nights (graphics plan W1): where each civilization had light after dark, written into the
region files as data the render pipeline reads, checked, and measured.

A region file gets:

- `lights`: `{"version": 1, "profiles": {id: profile}}`. A profile is one way a light burns:
  `kind` (`window`, `door`, `lamp`, `torch`, `brazier`, `fire`, `oven`, `kiln`, `forge`, `altar`,
  `beacon`, `bonfire`, `lantern`), `kelvin` (1700..2600) and its `colour`, `radius` (tiles of
  falloff), `strength` (0..1 at the source), `flicker` (`style` `steady` lamp, `gutter` torch,
  `breathe` brazier or embers, `leap` open fire; `hz` [lo, hi]; `depth` ≤ 0.08, never a full
  ramp step), `hours` (a list of [on, off]; `dusk` and `dawn` follow the season's day, `hh:mm`
  is the game clock; an off time before the on time runs past midnight), `rain` (`sheltered`
  burns on, `dim` at 0.6, `out` until the rain stops), and optionally `festivals` ({festival id:
  strength factor}, `*` for every festival of the region), `only` (a festival id or `event:<id>`:
  lit only on that festival's night or on the days that event happens), `seasons` (lit only in
  these).
- `light_points`: `[tx, ty, item, profile]` or `[tx, ty, item, profile, emitter]`, one light per
  entry, at a placed light-giving item: `(tx, ty)` is the item's origin in grid coordinates (the
  top vertex of its footprint's origin tile, as in the layer file), `item` its id; an emitter
  names one of the item's catalog `emitters` (the light sits at that emitter, else at the
  item's glow). A glowing item no point names keeps its glow sprite dark at night: that is how
  most houses stay unlit and the city keeps a rhythm of pools and shadow.
- `roles[].carries` and `events[].carries`: `{"light": profile, "prop": prop}` for people who
  carry a lamp or torch (the role while its hours of the profile hold; an event's cast while
  the event runs).

`theme.look.lights` (look.py) stays the default look per glowing kind for the overview's far
lights; the points are what lights the 1x city.
"""

from __future__ import annotations

import math
import re

import numpy as np

from plan import world_plan as P

from . import rng
from .compose import NONE16, World, live_items
from .coords import COLS

KINDS = ("window", "door", "lamp", "torch", "brazier", "fire", "oven", "kiln", "forge", "altar",
         "beacon", "bonfire", "lantern")
STYLES = ("steady", "gutter", "breathe", "leap")
RAIN = ("sheltered", "dim", "out")
CHUNK_CAP = 48          # light points per 32 x 32 chunk (the engine's light quads stay cheap)
DUSK, DAWN = 19.0, 5.5  # the measuring clock's dusk and dawn (the engine follows the season)
HHMM = re.compile(r"^([01]\d|2[0-4]):[0-5]\d$")

# Warm colours by colour temperature (flame and lamp light, 1700-2600 K).
KELVIN = {1700: "#ff7b2e", 1800: "#ff8436", 1900: "#ff8c3c", 2000: "#ff9446", 2100: "#ff9b50",
          2200: "#ffa25a", 2300: "#ffa964", 2400: "#ffb070", 2500: "#ffb779", 2600: "#ffbd82"}


def _p(kind, kelvin, radius, strength, style, hz, depth, hours, rain="sheltered", **kw) -> dict:
    return {"kind": kind, "kelvin": kelvin, "colour": KELVIN[kelvin], "radius": radius,
            "strength": strength, "flicker": {"style": style, "hz": list(hz), "depth": depth},
            "hours": [list(h) for h in hours], "rain": rain, **kw}


# One table for the whole world; a region writes only the profiles its points and carriers use.
PROFILES = {
    # houses: an oil lamp seen through a door or a high window, most out by the second watch
    "window_evening": _p("window", 2000, 1.6, 0.55, "steady", (0.4, 1.2), 0.03,
                         [("dusk", "22:30")], festivals={"*": 1.2}),
    "window_late": _p("window", 2000, 1.6, 0.5, "steady", (0.4, 1.2), 0.03, [("dusk", "01:30")]),
    "window_predawn": _p("window", 2000, 1.4, 0.45, "steady", (0.4, 1.2), 0.03,
                         [("04:00", "dawn")]),
    "door_lamp": _p("door", 1900, 2.2, 0.7, "steady", (4, 7), 0.05, [("dusk", "23:00")], "dim"),
    "symposium": _p("lamp", 2000, 2.4, 0.75, "steady", (3, 6), 0.05, [("20:00", "01:30")],
                    only="event:symposium"),
    "wedding_torches": _p("torch", 1900, 3.0, 0.9, "gutter", (6, 10), 0.08, [("19:00", "22:00")],
                          "out", only="event:wedding"),
    # trade: lamps at shop counters, taverns open late, workshops lit at the bench
    "shop_lamp": _p("lamp", 2000, 2.4, 0.75, "steady", (4, 7), 0.05, [("dusk", "21:30")], "dim"),
    "tavern_lamp": _p("lamp", 1900, 2.6, 0.8, "steady", (4, 7), 0.06, [("dusk", "00:30")], "dim",
                      festivals={"*": 1.3}),
    "bench_lamp": _p("lamp", 2000, 2.0, 0.6, "steady", (4, 7), 0.04, [("dusk", "21:00")]),
    "bath_lamps": _p("window", 2100, 2.2, 0.6, "steady", (2, 4), 0.03, [("dusk", "20:30")]),
    # fires of work: ovens before dawn, kilns while firing, forges at the ends of the day
    "oven_predawn": _p("oven", 1800, 2.4, 0.8, "breathe", (0.8, 1.6), 0.06,
                       [("02:30", "08:00"), ("dusk", "20:00")]),
    "kiln_firing": _p("kiln", 1800, 2.8, 0.9, "breathe", (0.5, 1.2), 0.06,
                      [("03:30", "08:30"), ("dusk", "21:00")]),
    "forge": _p("forge", 1800, 2.6, 0.85, "breathe", (1.5, 3.0), 0.07,
                [("04:30", "07:30"), ("dusk", "20:30")]),
    "glass_furnace": _p("forge", 1800, 2.4, 0.7, "breathe", (1.0, 2.0), 0.05, [("00:00", "24:00")]),
    "charcoal_glow": _p("kiln", 1700, 1.8, 0.45, "breathe", (0.2, 0.6), 0.05, [("00:00", "24:00")]),
    # the sacred: shrine lamps through the night, altar embers, fires never let go out
    "shrine_lamp": _p("lamp", 1900, 1.8, 0.6, "steady", (3, 6), 0.04, [("dusk", "dawn")], "dim",
                      festivals={"*": 1.4}),
    "altar_embers": _p("altar", 1800, 2.0, 0.5, "breathe", (0.3, 0.8), 0.06, [("dusk", "dawn")],
                       "dim", festivals={"*": 2.0}),
    "eternal_fire": _p("fire", 1800, 3.0, 0.85, "leap", (1.5, 3.0), 0.07, [("00:00", "24:00")],
                       festivals={"*": 1.3}),
    "open_fire_altar": _p("fire", 1800, 3.0, 0.85, "leap", (1.5, 3.0), 0.07, [("00:00", "24:00")],
                          "dim", festivals={"*": 1.5}),
    "sanctuary_lamp": _p("lamp", 2100, 2.6, 0.55, "steady", (2, 4), 0.03, [("dusk", "22:00")],
                         festivals={"*": 1.5}),
    "council_lamps": _p("window", 2000, 3.0, 0.7, "steady", (3, 6), 0.04, [("dusk", "dawn")]),
    "hall_lamps": _p("window", 2100, 2.6, 0.6, "steady", (2, 4), 0.03, [("dusk", "21:30")],
                     festivals={"*": 1.5}),
    # palaces and great houses: many lamps on stands, till late
    "palace_lamps": _p("window", 2100, 3.0, 0.75, "steady", (2, 4), 0.03, [("dusk", "23:30")],
                       festivals={"*": 1.4}),
    # gates, walls, guard posts: torches and watch fires burning through the night
    "gate_torch": _p("torch", 1900, 3.4, 0.95, "gutter", (6, 10), 0.08, [("dusk", "dawn")], "dim"),
    "watch_fire": _p("fire", 1800, 3.0, 0.85, "breathe", (0.8, 1.6), 0.07, [("dusk", "dawn")], "dim"),
    "wall_torch": _p("torch", 1900, 3.0, 0.85, "gutter", (6, 10), 0.08, [("dusk", "dawn")], "dim"),
    "brazier": _p("brazier", 1800, 3.2, 0.9, "breathe", (1.0, 2.0), 0.07, [("dusk", "02:00")], "out",
                  festivals={"*": 1.3}),
    "brazier_watch": _p("brazier", 1800, 3.2, 0.9, "breathe", (1.0, 2.0), 0.07, [("dusk", "dawn")],
                        "out", festivals={"*": 1.5}),
    "niche_lamp": _p("lamp", 1900, 2.2, 0.7, "steady", (4, 7), 0.05, [("dusk", "00:00")], "dim"),
    # harbours and roads
    "lighthouse": _p("beacon", 1800, 9.0, 1.0, "leap", (0.5, 1.0), 0.06, [("dusk", "dawn")]),
    "harbour_beacon": _p("beacon", 1800, 5.0, 0.9, "leap", (0.8, 1.6), 0.07, [("dusk", "dawn")], "dim"),
    "station_lamp": _p("lamp", 2000, 2.6, 0.75, "steady", (4, 7), 0.05, [("dusk", "dawn")]),
    "signal_watch": _p("fire", 1800, 2.2, 0.6, "breathe", (0.8, 1.6), 0.07, [("dusk", "dawn")], "out"),
    "camp_fire": _p("fire", 1800, 3.0, 0.8, "leap", (2, 4), 0.08, [("dusk", "23:00")], "out"),
    "hut_hearth": _p("window", 1900, 1.6, 0.5, "steady", (1, 3), 0.04, [("dusk", "21:00")]),
    # festival nights
    "parilia_bonfire": _p("bonfire", 1800, 5.0, 1.0, "leap", (2, 4), 0.08, [("20:00", "00:30")],
                          "out", only="parilia"),
    "saturnalia_tapers": _p("window", 2100, 1.8, 0.6, "steady", (3, 6), 0.04, [("dusk", "01:00")],
                            only="saturnalia"),
    "audience_braziers": _p("brazier", 1800, 3.4, 0.95, "breathe", (1.0, 2.0), 0.07,
                            [("dusk", "01:00")], "out", only="spring_audience"),
    "fire_evening": _p("bonfire", 1800, 4.5, 1.0, "leap", (2, 4), 0.08, [("17:30", "23:00")],
                       "out", only="fire_evening"),
    # carried by people
    "carried_lamp": _p("lantern", 2000, 1.6, 0.6, "steady", (4, 7), 0.05, [("dusk", "dawn")], "out"),
    "carried_torch": _p("torch", 1900, 2.6, 0.85, "gutter", (6, 10), 0.08, [("dusk", "dawn")], "out"),
    "cart_lantern": _p("lantern", 2000, 1.8, 0.65, "steady", (3, 6), 0.05, [("dusk", "dawn")], "dim"),
}

# Rules: item id pattern -> [(profile, share, emitter or None)]. Each glowing item draws once per
# rule group: the first entries of a group share one hash bucket (exclusive), so a house is
# lit early, late or before dawn, never twice. `None` profile leaves the bucket dark.
HOUSE = [("window_evening", 0.34), ("window_late", 0.08), ("window_predawn", 0.06)]
RULES: list[tuple[str, list[list[tuple]]]] = [
    # --- Athens -------------------------------------------------------------------------------
    (r"^athens\.g_house$", [HOUSE, [("door_lamp", 0.2)], [("symposium", 0.08)]]),
    (r"^athens\.g_house_two$", [HOUSE, [("door_lamp", 0.12)]]),
    (r"^athens\.g_house_small$", [HOUSE, [("door_lamp", 0.06)]]),
    (r"^athens\.g_shrine$", [[("shrine_lamp", 1.0)]]),
    (r"^athens\.g_kiln$", [[("kiln_firing", 1.0)]]),
    (r"^athens\.g_forge$", [[("forge", 1.0)]]),
    (r"^athens\.g_workshop$", [[("bench_lamp", 0.5)]]),
    (r"^athens\.g_brazier$", [[("brazier", 1.0)]]),
    (r"^athens\.g_lamp$", [[("niche_lamp", 1.0)]]),
    (r"^athens\.g_wall_tower$", [[("watch_fire", 0.3)]]),
    (r"^athens\.dipylon$", [[("gate_torch", 1.0, "torch_a")], [("gate_torch", 1.0, "torch_b")]]),
    (r"^athens\.great_altar$", [[("altar_embers", 1.0, "fire")]]),
    (r"^athens\.parthenon$", [[("sanctuary_lamp", 1.0)]]),
    (r"^athens\.tholos$", [[("council_lamps", 1.0)]]),
    (r"^athens\.old_bouleuterion$", [[("hall_lamps", 1.0)]]),
    (r"^athens\.stoa_poikile$", [[("hall_lamps", 1.0)]]),
    (r"^athens\.simon_shop$", [[("shop_lamp", 1.0)]]),
    (r"^athens\.harbour$", [[("harbour_beacon", 1.0, "beacon")]]),
    (r"^athens\.delphi_apollo$", [[("sanctuary_lamp", 1.0)]]),
    (r"^athens\.delos_sanctuary$", [[("sanctuary_lamp", 1.0)]]),
    # --- Rome ---------------------------------------------------------------------------------
    (r"^rome\.r_insula(_corner|_low)?$", [[("window_evening", 0.36), ("window_late", 0.12),
                                            ("window_predawn", 0.08)]]),
    (r"^rome\.r_domus$", [HOUSE, [("door_lamp", 0.45)]]),
    (r"^rome\.r_taberna$", [[("shop_lamp", 0.45)]]),
    (r"^rome\.r_thermopolium$", [[("tavern_lamp", 0.8)]]),
    (r"^rome\.r_bakery$", [[("oven_predawn", 1.0)]]),
    (r"^rome\.r_glass$", [[("glass_furnace", 1.0)]]),
    (r"^rome\.r_smithy$", [[("forge", 1.0)]]),
    (r"^rome\.r_compitum$", [[("shrine_lamp", 1.0)], [("parilia_bonfire", 0.5)]]),
    (r"^rome\.r_bath_small$", [[("bath_lamps", 1.0)]]),
    (r"^rome\.r_lamp$", [[("niche_lamp", 1.0)]]),
    (r"^rome\.r_brazier$", [[("brazier_watch", 1.0)]]),
    (r"^rome\.r_altar$", [[("altar_embers", 1.0)]]),
    (r"^rome\.r_vigiles$", [[("gate_torch", 1.0)]]),
    (r"^rome\.mutatio$", [[("station_lamp", 1.0)]]),
    (r"^rome\.vesta$", [[("eternal_fire", 1.0, "smoke")]]),
    (r"^rome\.vestals$", [[("hall_lamps", 1.0)]]),
    (r"^rome\.(domus_flavia|domus_augustana)$", [[("palace_lamps", 1.0)], [("gate_torch", 1.0)]]),
    (r"^rome\.suburban_villa$", [[("palace_lamps", 1.0)]]),
    (r"^rome\.castra_praetoria$", [[("gate_torch", 1.0)]]),
    (r"^rome\.portus_lighthouse$", [[("lighthouse", 1.0)]]),
    (r"^rome\.(curia|capitolium|pantheon|iseum|synagogue|latiaris)$", [[("sanctuary_lamp", 1.0)]]),
    (r"^rome\.(trajan_markets|agrippa_baths|trajan_baths|pompey_theatre|saepta)$",
     [[("hall_lamps", 1.0)]]),
    # --- Parsa --------------------------------------------------------------------------------
    (r"^parsa\.p_house$", [HOUSE, [("door_lamp", 0.16)]]),
    (r"^parsa\.p_house_small$", [HOUSE]),
    (r"^parsa\.p_workshop$", [[("bench_lamp", 0.5)]]),
    (r"^parsa\.p_kiln$", [[("kiln_firing", 1.0)]]),
    (r"^parsa\.p_oven$", [[("oven_predawn", 1.0)]]),
    (r"^parsa\.p_fire_altar$", [[("open_fire_altar", 1.0, "fire")], [("fire_evening", 1.0)]]),
    (r"^parsa\.p_incense$", [[("altar_embers", 1.0)]]),
    (r"^parsa\.p_brazier$", [[("brazier_watch", 1.0, "fire")]]),
    (r"^parsa\.p_torch$", [[("wall_torch", 1.0, "flame")]]),
    (r"^parsa\.p_tent$", [[("camp_fire", 0.6)]]),
    (r"^parsa\.fort_tower$", [[("wall_torch", 0.5, "torch")]]),
    (r"^parsa\.gate_all_lands$", [[("gate_torch", 1.0, "torch_w")], [("gate_torch", 1.0, "torch_e")]]),
    (r"^parsa\.garrison$", [[("brazier_watch", 1.0, "brazier")]]),
    (r"^parsa\.(tacara|hadish|harem|susa_palace)$", [[("palace_lamps", 1.0)]]),
    (r"^parsa\.apadana$", [[("audience_braziers", 1.0, "incense_l")],
                           [("audience_braziers", 1.0, "incense_r")]]),
    (r"^parsa\.pavilion$", [[("palace_lamps", 1.0)]]),
    (r"^parsa\.(road_station|royal_road_head)$", [[("station_lamp", 1.0)]]),
    (r"^parsa\.halys_gates$", [[("gate_torch", 1.0, "fire")]]),
    (r"^parsa\.gates_station$", [[("station_lamp", 1.0)], [("signal_watch", 1.0, "beacon")]]),
    # --- the world between --------------------------------------------------------------------
    (r"^world\.(royal_station|inn)$", [[("station_lamp", 1.0)]]),
    (r"^world\.watchtower$", [[("watch_fire", 0.5, "fire")]]),
    (r"^world\.beacon$", [[("signal_watch", 0.5, "fire")]]),
    (r"^world\.charcoal_kiln$", [[("charcoal_glow", 1.0)]]),
    (r"^world\.(fish_hut|reed_hut)$", [[("hut_hearth", 0.6)]]),
    (r"^world\.tent_black$", [[("camp_fire", 0.7)]]),
]
# Glowing items left dark on purpose: a statue's gleam is the sun's, not a lamp's; arenas and
# circuses held their games by day.
DARK = {"athens.promachos", "rome.colossus", "rome.colosseum", "rome.circus_maximus",
        "rome.trajan_column", "rome.tiber_island", "rome.emporium"}
# District factors: busy centres keep more lamps burning, the countryside goes to bed early.
AREA_FACTOR = {"centre": 1.15, "town": 1.0, "road": 0.8, "country": 0.6, "wild": 0.5, "sea": 0.8}
# Who carries light (roles by id in any city; event casts by event id).
CARRIED_ROLES = {
    "night_walker": ("carried_lamp", "lamp"), "reveller": ("carried_lamp", "lamp"),
    "vigil": ("carried_lamp", "lantern"), "night_cart": ("cart_lantern", "lantern"),
    "night_unloader": ("carried_torch", "torch"), "wall_watch": ("carried_torch", "torch"),
    "spearman": ("carried_torch", "torch"), "patron": ("carried_lamp", "lamp"),
    "camp_guard": ("carried_torch", "torch"), "carter": ("cart_lantern", "lantern"),
}
CARRIED_EVENTS = {
    "torch_race": ("carried_torch", "torch"), "wedding": ("carried_torch", "torch"),
    "parilia_bonfires": ("carried_torch", "torch"), "funeral": ("carried_torch", "torch"),
    "night_carts": ("cart_lantern", "lantern"), "fire_evening": ("carried_torch", "torch"),
    "torches_lit": ("carried_torch", "torch"), "lamps_lit": ("carried_lamp", "lamp"),
}


def hour(s: str, dusk: float = DUSK, dawn: float = DAWN) -> float:
    if s == "dusk":
        return dusk
    if s == "dawn":
        return dawn
    hh, mm = s.split(":")
    return int(hh) + int(mm) / 60


def lit_at(profile: dict, h: float) -> bool:
    for a, b in profile["hours"]:
        ha, hb = hour(a), hour(b)
        if (ha <= h < hb) if ha <= hb else (h >= ha or h < hb):
            return True
    return False


def region_of(world: World, it) -> str | None:
    d = int(world.D[it.r, it.c])
    return None if d == NONE16 else world.districts[d].split("/", 1)[0]


def _rules(iid: str):
    for pat, groups in RULES:
        if re.search(pat, iid):
            return groups
    return None


def grid_origin(it) -> tuple[int, int]:
    """The item's origin in grid coordinates (the layer file's anchor)."""
    return it.r, COLS - 1 - (it.c + it.pw - 1)


def points_for(world: World, cat, rid: str, areas: dict[str, str]) -> list[list]:
    """The light points of one region, deterministic, at most CHUNK_CAP per chunk."""
    pts = []
    for _, it in live_items(world):
        d = cat.items.get(it.id)
        if d is None or not d.glow or it.id in DARK or region_of(world, it) != rid:
            continue
        groups = _rules(it.id)
        if groups is None:
            continue
        di = int(world.D[it.r, it.c])
        factor = AREA_FACTOR.get(areas.get(world.districts[di].split("/", 1)[-1], "town"), 1.0)
        tx, ty = grid_origin(it)
        emitters = d.extra.get("emitters") or {}
        for gi, group in enumerate(groups):
            u = (rng.hash64(rid, "light", it.id, it.c, it.r, gi) % 10000) / 10000
            acc = 0.0
            for entry in group:
                prof, share = entry[0], entry[1]
                em = entry[2] if len(entry) > 2 else None
                # Landmarks and fires are lit as they are; only the share-drawn kinds vary.
                acc += min(1.0, share * (factor if share < 1.0 else 1.0))
                if u < acc:
                    if em is not None and em not in emitters:
                        em = None
                    pts.append([tx, ty, it.id, prof] + ([em] if em else []))
                    break
    return _cap(pts)


PRIORITY = {"window": 0, "door": 1, "lamp": 2}


def _cap(pts: list[list]) -> list[list]:
    """Keep at most CHUNK_CAP points per chunk; windows go first, then doors, by hash."""
    by: dict = {}
    for p in pts:
        by.setdefault((p[0] // P.CHUNK, p[1] // P.CHUNK), []).append(p)
    drop = set()
    for k, lst in by.items():
        extra = len(lst) - CHUNK_CAP
        if extra > 0:
            order = sorted(lst, key=lambda p: (PRIORITY.get(PROFILES[p[3]]["kind"], 9),
                                               rng.hash64("cap", *p)))
            drop |= {id(p) for p in order[:extra]}
    return sorted((p for p in pts if id(p) not in drop), key=lambda p: (p[1], p[0], p[2], p[3]))


def apply(doc: dict, world: World, cat) -> dict:
    """Write `lights`, `light_points` and the carriers into a region document."""
    rid = doc["id"]
    if rid not in P.REGIONS or P.REGIONS[rid][0] == "home":
        return doc
    areas = {d["id"]: d.get("area", "town") for d in doc.get("districts", [])}
    festivals = {f["id"] for f in doc.get("festivals", [])}
    events = {e["id"] for e in doc.get("events", [])}
    pts = [p for p in points_for(world, cat, rid, areas)
           if _only_ok(PROFILES[p[3]].get("only"), festivals, events)]
    used = {p[3] for p in pts}
    for r in doc.get("roles", []):
        r.pop("carries", None)
        if r["id"] in CARRIED_ROLES and _night_role(r):
            prof, prop = CARRIED_ROLES[r["id"]]
            r["carries"] = {"light": prof, "prop": prop}
            used.add(prof)
    for e in doc.get("events", []):
        e.pop("carries", None)
        if e["id"] in CARRIED_EVENTS and e.get("cast"):
            prof, prop = CARRIED_EVENTS[e["id"]]
            e["carries"] = {"light": prof, "prop": prop}
            used.add(prof)
    if not used:
        doc.pop("lights", None)
        doc.pop("light_points", None)
        return doc
    doc["lights"] = {"version": 1, "profiles": {k: PROFILES[k] for k in sorted(used)}}
    doc["light_points"] = pts
    return doc


def _only_ok(only: str | None, festivals: set[str], events: set[str]) -> bool:
    if only is None:
        return True
    return only[6:] in events if only.startswith("event:") else only in festivals


def _night_role(r: dict) -> bool:
    """A role out between dusk and dawn for at least one block."""
    for b in r.get("schedule", []):
        hs = b.get("hours")
        if not hs:
            continue
        a, z = hour(hs[0]), hour(hs[1])
        if a > z or z > 20.0 or a < 5.0:
            return True
    return False


# -- checking ------------------------------------------------------------------------------------

def check(doc: dict, world: World, cat) -> list[tuple[str, str, str]]:
    """[(level, where, message)]: profiles in range, every point at a placed light-giving item or
    one of its emitters, no two lights of a kind on one tile, carriers' profiles known, and every
    populated district lit at dusk."""
    out = []
    lights = doc.get("lights")
    pts = doc.get("light_points", [])
    if lights is None:
        if pts:
            out.append(("error", "light_points", "points without `lights` profiles"))
        return out
    profs = lights.get("profiles", {})
    festivals = {f["id"] for f in doc.get("festivals", [])}
    events = {e["id"] for e in doc.get("events", [])}
    broken = set()
    for pid, p in profs.items():
        probs = profile_problems(p, festivals, events)
        out += [("error", f"lights.profiles.{pid}", m) for m in probs]
        if probs:
            broken.add(pid)
    placed = {}
    for _, it in live_items(world):
        placed[(*grid_origin(it), it.id)] = it
    seen = set()
    lit_dusk = set()
    for i, pt in enumerate(pts):
        where = f"light_points[{i}]"
        if not (isinstance(pt, list) and len(pt) in (4, 5) and all(isinstance(x, int) for x in pt[:2])
                and all(isinstance(x, str) for x in pt[2:])):
            out.append(("error", where, f"needs [tx, ty, item, profile(, emitter)], has {pt!r}"))
            continue
        tx, ty, iid, pid = pt[:4]
        if pid not in profs:
            out.append(("error", where, f"profile {pid!r} is not in lights.profiles"))
            continue
        d = cat.items.get(iid)
        it = placed.get((tx, ty, iid))
        if d is None or it is None:
            out.append(("error", where, f"no {iid} has its origin at ({tx}, {ty})"))
            continue
        if not d.glow:
            out.append(("error", where, f"{iid} gives no light (no glow layer)"))
        em = pt[4] if len(pt) == 5 else None
        if em is not None and em not in (d.extra.get("emitters") or {}):
            out.append(("error", where, f"{iid} has no emitter {em!r}"))
        key = (tx, ty, em, profs[pid]["kind"])
        if key in seen:
            out.append(("error", where, f"a second {profs[pid]['kind']} light on {iid} at ({tx}, {ty})"))
        seen.add(key)
        if pid not in broken and lit_at(profs[pid], 20.5) and "only" not in profs[pid]:
            lit_dusk.add(int(world.D[it.r, it.c]))
    for e in doc.get("roles", []) + doc.get("events", []):
        c = e.get("carries")
        if c is not None and c.get("light") not in profs:
            out.append(("error", f"{e['id']}.carries", f"profile {c.get('light')!r} is not in "
                        "lights.profiles"))
    rid = doc["id"]
    built: dict[int, int] = {}
    for it in placed.values():
        cd = cat.items.get(it.id)
        if cd is not None and cd.has_door:
            di = int(world.D[it.r, it.c])
            built[di] = built.get(di, 0) + 1
    for dd in doc.get("districts", []):
        if dd.get("area") not in ("centre", "town") or not dd.get("populations"):
            continue
        name = f"{rid}/{dd['id']}"
        if name not in world.districts:
            continue
        di = world.districts.index(name)
        if built.get(di) and di not in lit_dusk:
            out.append(("error", f"district {dd['id']}", "a populated district with no light at dusk"))
    return out


def profile_problems(p: dict, festivals: set[str], events: set[str]) -> list[str]:
    bad = []
    if p.get("kind") not in KINDS:
        bad.append(f"kind {p.get('kind')!r} is not one of {list(KINDS)}")
    if not (isinstance(p.get("kelvin"), int) and 1700 <= p["kelvin"] <= 2600):
        bad.append("kelvin needs 1700..2600 (warm flame and lamp light)")
    if not (isinstance(p.get("colour"), str) and re.match(r"^#[0-9a-f]{6}$", p["colour"])):
        bad.append(f"colour needs '#rrggbb', has {p.get('colour')!r}")
    if not 0 < p.get("radius", 0) <= 12:
        bad.append("radius needs 0..12 tiles")
    if not 0 < p.get("strength", 0) <= 1:
        bad.append("strength needs 0..1")
    f = p.get("flicker", {})
    if f.get("style") not in STYLES:
        bad.append(f"flicker style {f.get('style')!r} is not one of {list(STYLES)}")
    if not 0 <= f.get("depth", -1) <= 0.08:
        bad.append("flicker depth needs 0..0.08 (never a full ramp step)")
    hz = f.get("hz")
    if not (isinstance(hz, list) and len(hz) == 2 and 0 < hz[0] <= hz[1] <= 12):
        bad.append("flicker hz needs [lo, hi] within 0..12")
    hours = p.get("hours")
    if not (isinstance(hours, list) and hours):
        bad.append("hours needs a list of [on, off]")
    else:
        for h in hours:
            if not (isinstance(h, list) and len(h) == 2 and
                    all(x in ("dusk", "dawn") or (isinstance(x, str) and HHMM.match(x)) for x in h)):
                bad.append(f"hours entry {h!r} needs [on, off] as 'hh:mm', 'dusk' or 'dawn'")
            elif h[0] == h[1]:
                bad.append(f"hours entry {h!r} never burns")
    if p.get("rain") not in RAIN:
        bad.append(f"rain {p.get('rain')!r} is not one of {list(RAIN)}")
    for k, v in p.get("festivals", {}).items():
        if k != "*" and k not in festivals:
            bad.append(f"festival {k!r} is not one of the region's")
        if not 0.5 <= v <= 2.5:
            bad.append(f"festival factor {v} needs 0.5..2.5")
    only = p.get("only")
    if only is not None:
        if only.startswith("event:"):
            if only[6:] not in events:
                bad.append(f"only: event {only[6:]!r} is not one of the region's")
        elif only not in festivals:
            bad.append(f"only: festival {only!r} is not one of the region's")
    for s in p.get("seasons", []):
        if s not in ("spring", "summer", "autumn", "winter"):
            bad.append(f"season {s!r} is unknown")
    return bad
