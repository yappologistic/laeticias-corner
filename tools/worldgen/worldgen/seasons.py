"""Seasons across the world (docs/design/seasons.md): the calendar, climate resolution, the
catalogs' seasonal fields, the world's flood ranks and ground classes, and the season needs file.

The region side (each region's climate, era, moment, water, harbours, seasonal life and themes)
is `seasonlife.py`; the checks are `seasoncheck.py`; the year in the life and the season maps are
`seasonreport.py`. Data lives in `climates.py`.

Calendar (§1.2): day n is month `n mod 12` (0 = March), season `(n / 3) mod 4`, season day
`n mod 3 + 1`, week day `n mod 4`. Twelve days hold every month with its week day, so any check
over days 0..11 has seen the whole year.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np

from plan import world_plan as P

from . import climates as C
from .compose import NONE16, World, live_items

YEAR = 12


# -- the calendar ------------------------------------------------------------------------------

def month_of(day: int) -> str:
    return C.MONTHS[day % 12]


def season_of(day: int) -> str:
    return C.SEASONS[(day // 3) % 4]


def season_day(day: int) -> int:
    return day % 3 + 1


def day_of(season: str, sday: int) -> int:
    """The first calendar day (0..11) that is this season's day `sday`."""
    return C.SEASONS.index(season) * 3 + sday - 1


def month_index(m: str) -> int:
    return C.MONTHS.index(m)


def season_months(season: str) -> list[str]:
    i = C.SEASONS.index(season) * 3
    return C.MONTHS[i:i + 3]


# -- climates ----------------------------------------------------------------------------------

def raw_climates(root: Path) -> dict[str, dict]:
    """The catalog's climates as written (with `inherits`), by id; the tool's table when the
    catalog has none yet (a first `--seasons` run)."""
    f = Path(root) / "assets/catalog.json"
    doc = json.loads(f.read_text()) if f.exists() else {}
    src = doc.get("climates") or C.CLIMATES
    return {c["id"]: c for c in src}


# Blocks a climate refines key by key over its parent's; every other block it gives replaces the
# parent's whole (its own birds, work, snow and sea, never a mix with the parent's).
MERGED = ("classes", "set_classes", "weather", "water", "grade", "look", "travel")


def _merge(parent: dict, child: dict) -> dict:
    out = copy.deepcopy(parent)
    for k, v in child.items():
        if k in MERGED and isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **copy.deepcopy(v)}
        else:
            out[k] = copy.deepcopy(v)
    out.pop("inherits", None)
    return out


def resolve(raw: dict[str, dict], cid: str, seen: tuple = ()) -> dict:
    """A climate with every key its `inherits` chain gives it."""
    c = raw[cid]
    p = c.get("inherits")
    if p is None or p in seen or p not in raw:
        out = copy.deepcopy(c)
        out.pop("inherits", None)
        return out
    return _merge(resolve(raw, p, seen + (cid,)), c)


def resolved(root: Path) -> dict[str, dict]:
    raw = raw_climates(root)
    return {cid: resolve(raw, cid) for cid in raw}


def lasting_snow(clim: dict) -> int | None:
    """The lowest level snow lies on in every month of the climate (the highest of its twelve
    snow lines), or None where some month has no snow at all: only there may snow be ground."""
    line = clim.get("snow", {}).get("line") or []
    if len(line) != 12 or any(v is None for v in line):
        return None
    return max(line)


def tool_climates() -> dict[str, dict]:
    """The tool's climate table resolved (what `--seasons` writes into the catalog)."""
    raw = {c["id"]: c for c in C.CLIMATES}
    return {cid: resolve(raw, cid) for cid in raw}


def class_row(clim: dict, cls: str, set_item: bool) -> list[str]:
    """The twelve states of a class in a climate. The home climate's classes are its season names
    for the home catalog's own pieces; set pieces placed in the corner's surroundings turn by its
    `set_classes`."""
    if set_item and "set_classes" in clim and cls in clim["set_classes"]:
        return clim["set_classes"][cls]
    return clim.get("classes", {}).get(cls) or ["green"] * 12


def item_states(clim: dict, spec: dict, set_item: bool = True) -> list[str]:
    """The state an item with seasonal fields shows in each month of a climate (the item's
    `bloom` and `fruit` months win over the class)."""
    cls = spec.get("season_class")
    if not cls:
        return []
    out = list(class_row(clim, cls, set_item))
    for k, state in (("bloom", "bloom"), ("fruit", "fruit")):
        for m in spec.get(k, []):
            out[month_index(m)] = state
    return out


def needed_states(clim: dict, spec: dict, set_item: bool = True) -> set[str]:
    st = set(item_states(clim, spec, set_item))
    if spec.get("snow_look"):
        st.add("snow")
    return st - {spec.get("plain_state"), "gone"}


def lookup_row(clim: dict, raw: dict, name: str) -> list | None:
    """A named factor row (`sailing`, `grain`, `caravan`, `road`, `courier`, `barge`) from a
    climate: its `sea` block, its `travel` block, then its coast's sea climate."""
    if name in clim.get("sea", {}):
        return clim["sea"][name]
    t = clim.get("travel", {})
    if name in t:
        v = t[name]
        return [v] * 12 if isinstance(v, (int, float)) else v
    coast = clim.get("coast")
    if coast and coast in raw:
        sea = resolve(raw, coast).get("sea", {})
        if name in sea:
            return sea[name]
    return None


# -- placements --------------------------------------------------------------------------------

def region_grid(world: World) -> tuple[np.ndarray, list[str]]:
    """Region index per tile (-1 where no district) and the region names."""
    names = sorted({n.split("/", 1)[0] for n in world.districts})
    idx = {n: i for i, n in enumerate(names)}
    lut = np.array([idx[n.split("/", 1)[0]] for n in world.districts] + [-1], dtype=np.int32)
    D = np.where(world.D == NONE16, len(world.districts), world.D)
    return lut[D], names


def placements(world: World) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Which climates each placed item and each painted terrain stands in."""
    reg, names = region_grid(world)
    items: dict[str, set[str]] = {}
    for _, it in live_items(world):
        ri = int(reg[it.r, it.c])
        if ri >= 0:
            items.setdefault(it.id, set()).add(C.REGION_CLIMATE.get(names[ri], "med_green"))
    terr: dict[str, set[str]] = {}
    cids = sorted(set(C.REGION_CLIMATE.values()))
    cmap = np.array([cids.index(C.REGION_CLIMATE.get(n, "med_green")) for n in names] + [-1])
    cl = cmap[np.where(reg < 0, len(names), reg)]
    T = world.T
    for ti, tid in enumerate(world.terrains):
        m = T == ti
        if not m.any():
            continue
        for ci in np.unique(cl[m]).tolist():
            if ci >= 0:
                terr.setdefault(tid, set()).add(cids[ci])
    return items, terr


def placed_regions(world: World) -> dict[str, set[str]]:
    """The regions each item is placed in."""
    reg, names = region_grid(world)
    out: dict[str, set[str]] = {}
    for _, it in live_items(world):
        ri = int(reg[it.r, it.c])
        if ri >= 0:
            out.setdefault(it.id, set()).add(names[ri])
    return out


# -- the catalogs ------------------------------------------------------------------------------

SET_DEFAULT = {"world": ["med_green"], "rome": ["med_green"], "athens": ["med_dry"],
               "parsa": ["fars"]}


def season_fields(set_: str, iid: str, spec: dict, where: set[str], clims: dict) -> dict:
    """The seasonal fields an item or terrain gets in its set catalog: the design's states plus
    every state it resolves to where it stands (or in its set's home climate if unplaced)."""
    states = set(spec.get("season_states", []))
    for cid in sorted(where or SET_DEFAULT[set_]):
        states |= needed_states(clims[cid], spec)
    order = [s for s in C.STATES if s in states and s != spec.get("plain_state")]
    out = {"season_class": spec["season_class"], "plain_state": spec["plain_state"],
           "season_states": order}
    for k in ("bloom", "fruit"):
        if k in spec:
            out[k] = spec[k]
    if spec.get("snow_look"):
        out["snow_look"] = True
    return out


def _edit_entry(obj: dict, fields: dict) -> dict:
    for k, v in fields.items():
        obj[k] = v
    return obj


def set_catalog_text(text: str, set_: str, items_where: dict, terr_where: dict,
                     clims: dict) -> str:
    """The set catalog with its seasonal fields written (only those keys, in the file's own
    layout: one entry per line, or the indent-1 pretty layout)."""
    doc = json.loads(text)
    pretty = json.dumps(doc, indent=1, ensure_ascii=False) + "\n" == text
    edits: dict[str, dict] = {}
    for iid, spec in C.SEASON_ITEMS.get(set_, {}).items():
        edits[iid] = season_fields(set_, iid, spec, items_where.get(iid, set()), clims)
    for tid, spec in C.SEASON_TERRAIN.get(set_, {}).items():
        edits[tid] = season_fields(set_, tid, spec, terr_where.get(tid, set()), clims)
    for iid in C.NO_SNOW_CATCH:
        if iid.split(".", 1)[0] == set_:
            edits.setdefault(iid, {})["snow_catch"] = False
    art_edits = {}
    if set_ == "world":
        art_edits["overlays"] = C.ART_OVERLAYS
    if set_ in C.BACKDROP_SNOW:
        art_edits["backdrop_snow"] = C.BACKDROP_SNOW[set_]
    if pretty:
        for sect in ("terrain", "items"):
            for e in doc.get(sect, []):
                if e.get("id") in edits:
                    _edit_entry(e, edits[e["id"]])
        if art_edits:
            doc.setdefault("art", {}).update(art_edits)
        return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    lines = text.split("\n")
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith('{"id": '):
            comma = s.endswith(",")
            body = s[:-1] if comma else s
            obj = json.loads(body)
            if obj.get("id") in edits:
                indent = ln[:len(ln) - len(ln.lstrip())]
                ln = indent + json.dumps(_edit_entry(obj, edits[obj["id"]]),
                                         ensure_ascii=False) + ("," if comma else "")
        elif s.startswith('"art": {') and art_edits:
            comma = s.endswith(",")
            obj = json.loads("{" + (s[:-1] if comma else s) + "}")
            obj["art"].update(art_edits)
            indent = ln[:len(ln) - len(ln.lstrip())]
            ln = indent + '"art": ' + json.dumps(obj["art"], ensure_ascii=False) + \
                ("," if comma else "")
        out.append(ln)
    new = "\n".join(out)
    json.loads(new)   # still a document
    return new


def main_catalog_text(text: str) -> str:
    """`assets/catalog.json` with `calendar` and `climates` written right after `seasons` (one
    climate per line, as the file writes its other lists); everything else as it was."""
    lines = text.split("\n")
    # Drop an earlier copy of the two blocks.
    out: list[str] = []
    skip = False
    for ln in lines:
        if ln.startswith('  "calendar": '):
            continue
        if ln.startswith('  "climates": ['):
            skip = True
            continue
        if skip:
            if ln.startswith("  ]"):
                skip = False
            continue
        out.append(ln)
    start = out.index('  "seasons": [')
    end = next(i for i in range(start + 1, len(out)) if out[i].startswith("  ]"))
    block = ['  "calendar": ' + json.dumps(C.calendar(), ensure_ascii=False) + ",",
             '  "climates": [']
    for i, c in enumerate(C.CLIMATES):
        block.append("    " + json.dumps(c, ensure_ascii=False) +
                     ("," if i + 1 < len(C.CLIMATES) else ""))
    block.append("  ],")
    out[end + 1:end + 1] = block
    new = "\n".join(out)
    json.loads(new)
    return new


def write_catalogs(root: Path, world: World, texts: dict[str, str] | None = None) -> dict[str, str]:
    """The catalogs' seasonal fields. With `texts` ({path: text}) the edit is applied to those
    texts and returned (used to stage the edit on the committed files only); otherwise the files
    in the tree are rewritten."""
    root = Path(root)
    clims = {c["id"]: resolve({x["id"]: x for x in C.CLIMATES}, c["id"]) for c in C.CLIMATES}
    items_where, terr_where = placements(world)
    paths = {"assets/catalog.json": None} | {f"assets/sets/{s}/catalog.json": s
                                             for s in ("world", "rome", "athens", "parsa")}
    out = {}
    for rel, set_ in paths.items():
        text = texts[rel] if texts is not None else (root / rel).read_text()
        new = main_catalog_text(text) if set_ is None else \
            set_catalog_text(text, set_, items_where, terr_where, clims)
        out[rel] = new
        if texts is None and new != text:
            (root / rel).write_text(new)
    return out


# -- the world's seasonal data: flood ranks and ground classes ---------------------------------

FLOOD_GROUND = {"world.alluvium", "world.marsh", "rome.mud_bank", "athens.riverbed",
                "world.field", "rome.field_spring"}
RIVER_TERRAIN = {"world.river": "river", "rome.river_tiber": "river",
                 "athens.riverbed": "stream", "parsa.water_channel": "channel", "water": "pond"}
# Bodies the plan names; anything else is named after its region and kind.
STREAMS = {"anio", "liris", "aufidus", "achelous", "eurotas", "alpheios", "kaystros", "karun",
           "orontes", "kur", "corner_brook"}
GROUND_CLASSES = ["none", "sea", "water", "grass", "crop", "forest", "evergreen", "scrub",
                  "steppe", "marsh", "rock", "sand", "snow", "paved", "earth"]
GROUND_OF = {
    "world.sea": "sea", "world.shallows": "sea", "world.river": "water", "rome.river_tiber": "water",
    "parsa.water_channel": "water", "water": "water", "athens.riverbed": "earth",
    "grass": "grass", "meadow": "grass", "rome.grass_spring": "grass", "world.pasture": "grass",
    "parsa.plain_grass": "grass", "athens.olive_soil": "scrub", "athens.dry_grass": "steppe",
    "world.steppe": "steppe", "world.fallow": "steppe", "world.alluvium": "grass",
    "world.field": "crop", "rome.field_spring": "crop", "athens.field_stubble": "crop",
    "parsa.field_barley": "crop", "rome.vineyard_soil": "crop", "parsa.garden_bed": "crop",
    "world.forest_floor": "forest", "world.scrub": "scrub", "world.marsh": "marsh",
    "rome.mud_bank": "earth", "world.rock": "rock", "world.scree": "rock", "rome.tufa_rock": "rock",
    "athens.rock_limestone": "rock", "parsa.rough_ground": "rock", "world.sand": "sand",
    "world.dune": "sand", "world.gravel_desert": "sand", "world.salt_flat": "sand",
    "world.snow": "snow",
}


def _components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    """4-connected components of a mask, as (c, r) tile lists, in scan order."""
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    H, W = mask.shape
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        stack = [(int(c0), int(r0))]
        seen[r0, c0] = True
        comp = []
        while stack:
            c, r = stack.pop()
            comp.append((c, r))
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                x, y = c + dc, r + dr
                if 0 <= x < W and 0 <= y < H and mask[y, x] and not seen[y, x]:
                    seen[y, x] = True
                    stack.append((x, y))
        out.append(sorted(comp, key=lambda t: (t[1], t[0])))
    return out


def _course_dist(c: float, r: float, pts) -> float:
    best = 1e18
    for (ac, ar), (bc, br) in zip(pts, pts[1:]):
        dc, dr = bc - ac, br - ar
        L = dc * dc + dr * dr or 1
        t = max(0.0, min(1.0, ((c - ac) * dc + (r - ar) * dr) / L))
        x, y = ac + t * dc, ar + t * dr
        best = min(best, (c - x) ** 2 + (r - y) ** 2)
    return best


# Named waters the plan's rivers do not cover, by a point in plan coordinates near each.
WATER_ANCHORS = {"athens": [("eridanos", (612, 242)), ("ilissos", (705, 360))],
                 "parsa": [("parsa_channels", (1165, 360))]}


def _nearest_course(cs: np.ndarray, rs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per tile, the index of the nearest plan river course and the squared distance to it."""
    names = list(P.RIVERS)
    best = np.full(cs.shape, 1e18)
    who = np.full(cs.shape, -1)
    for k, rv in enumerate(names):
        pts = P.RIVERS[rv]["points"]
        for (ac, ar), (bc, br) in zip(pts, pts[1:]):
            dc, dr = bc - ac, br - ar
            L = dc * dc + dr * dr or 1
            t = np.clip(((cs - ac) * dc + (rs - ar) * dr) / L, 0, 1)
            d = (cs - (ac + t * dc)) ** 2 + (rs - (ar + t * dr)) ** 2
            m = d < best
            best[m] = d[m]
            who[m] = k
    return who, best


def water_bodies(world: World) -> list[dict]:
    """Every body of river, stream, channel or pond water, cut by region: its tiles (plan c, r),
    kind, region and name (the plan's river nearest each tile within 16 tiles, else the region's
    named waters, else the region and kind)."""
    reg, names = region_grid(world)
    tid = {t: i for i, t in enumerate(world.terrains)}
    rivers = list(P.RIVERS)
    merged: dict[tuple, dict] = {}
    for terr, kind in RIVER_TERRAIN.items():
        if terr not in tid:
            continue
        rs, cs = np.nonzero(world.T == tid[terr])
        if not len(rs):
            continue
        who, d = _nearest_course(cs.astype(float), rs.astype(float))
        for c, r, k, dd in zip(cs.tolist(), rs.tolist(), who.tolist(), d.tolist()):
            ri = int(reg[r, c])
            if ri < 0:
                continue
            rid = names[ri]
            reach = 40 if kind == "river" else 16
            name = rivers[k] if dd <= reach ** 2 and kind in ("river", "stream") else None
            if name is None and rid in WATER_ANCHORS and kind != "river":
                name = min(WATER_ANCHORS[rid],
                           key=lambda a: (a[1][0] - c) ** 2 + (a[1][1] - r) ** 2)[0]
            kk = "stream" if (name in STREAMS and kind == "river") else kind
            name = name or f"{rid}_{kk}"
            merged.setdefault((rid, name, kk), {"region": rid, "name": name, "kind": kk,
                                                "terrain": terr, "tiles": []})["tiles"].append((c, r))
    out = []
    for key in sorted(merged):
        b = merged[key]
        if len(b["tiles"]) < 4:
            continue
        if b["kind"] == "pond" and len(b["tiles"]) > 400:
            b["kind"] = "lake"
        b["tiles"].sort(key=lambda t: (t[1], t[0]))
        out.append(b)
    return out


def flood_ranks(world: World, bodies: list[dict], clims: dict) -> list[dict]:
    """Low ground beside every body that floods in its climate (seasons.md §3.4): alluvium, marsh,
    mud bank, riverbed and the fields on them, within 12 tiles of the water and at most one level
    above it, ranked 1-3 (1 fills first): by walking distance and height above the water."""
    from collections import deque
    tid = {t: i for i, t in enumerate(world.terrains)}
    ground = np.isin(world.T, [tid[t] for t in FLOOD_GROUND if t in tid])
    lv = (world.L & 0x0F).astype(np.int16)
    reg, names = region_grid(world)
    H, W = world.T.shape
    out = []
    for b in bodies:
        clim = clims[C.REGION_CLIMATE.get(b["region"], "med_green")]
        row = clim.get("water", {}).get(b["kind"], [])
        if "flood" not in row:
            continue
        ri = names.index(b["region"])
        dist = {}
        q = deque()
        for c, r in b["tiles"]:
            q.append((c, r, 0, int(lv[r, c])))
            dist[(c, r)] = 0
        found = {}
        while q:
            c, r, d, src = q.popleft()
            if d >= 12:
                continue
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                x, y = c + dc, r + dr
                if not (0 <= x < W and 0 <= y < H) or (x, y) in dist:
                    continue
                if not ground[y, x] or reg[y, x] != ri or int(lv[y, x]) > src + 1:
                    continue
                dist[(x, y)] = d + 1
                found[(x, y)] = (d + 1, int(lv[y, x]) - src)
                q.append((x, y, d + 1, src))
        # Heights are counted from the lowest flood ground of the body (a river sunk below its
        # banks floods those banks first).
        low = min((u for _, u in found.values()), default=0)
        ranks = {t: 1 if (u == low and d <= 4) else
                 2 if (u == low and d <= 8) or (u == low + 1 and d <= 4) else 3
                 for t, (d, u) in found.items()}
        tiles = sorted(ranks.items(), key=lambda t: (t[0][1], t[0][0]))
        out.append({"region": b["region"], "body": b["name"],
                    "tiles": [[*map(int, _grid(c, r)), k] for (c, r), k in tiles]})
    return out


def _grid(c: int, r: int) -> tuple[int, int]:
    from .coords import to_grid
    return to_grid(c, r)


def ground_classes(world: World, cat) -> np.ndarray:
    """One byte per tile, grid-oriented (pixel (x, y) is grid tile (x, y)): the ground class the
    overview tints by climate and month (GROUND_CLASSES), trees and buildings over their ground."""
    lut = np.zeros(len(world.terrains) + 1, dtype=np.uint8)
    for i, t in enumerate(world.terrains):
        g = GROUND_OF.get(t)
        if g is None:
            d = cat.terrain.get(t) if hasattr(cat, "terrain") else None
            g = "paved" if (d is not None and getattr(d, "extra", {}).get("paved")) or \
                any(k in t for k in ("paving", "road", "gravel", "brick")) else "earth"
        lut[i] = GROUND_CLASSES.index(g)
    T = np.where(world.T < 0, len(world.terrains), world.T)
    plan = lut[T]
    plan[world.D == NONE16] = 0
    trees = {}
    for set_items in C.SEASON_ITEMS.values():
        for iid, spec in set_items.items():
            if spec["season_class"] in ("deciduous", "early_bloom", "vine"):
                trees[iid] = "forest"
            elif spec["season_class"] == "evergreen" and iid.split(".")[-1].startswith("t_"):
                trees[iid] = "evergreen"
    for _, it in live_items(world):
        g = trees.get(it.id)
        if g is None:
            d = cat.items.get(it.id)
            if d is None or d.footprint[0] * d.footprint[1] < 2:
                continue
            g = "paved"
        plan[it.r:it.r + it.ph, it.c:it.c + it.pw] = GROUND_CLASSES.index(g)
    # plan [r, c] -> grid image [y, x] with x = r, y = COLS - 1 - c.
    return np.ascontiguousarray(plan[:, ::-1].T)


def write_world(root: Path, world: World, cat, flood: list[dict]) -> list[Path]:
    """`assets/world/seasons.json` (flood ranks, the ground class legend) and
    `assets/world/groundclass.png`."""
    from PIL import Image
    root = Path(root)
    d = root / "assets/world"
    plan = ground_classes(world, cat)
    img = Image.fromarray(plan, mode="L")
    f_png = d / "groundclass.png"
    img.save(f_png, optimize=True)
    doc = {"version": 1,
           "note": "seasons.md §3.4, §4.5: flood ranks by water body (grid x, y, rank: 1 fills "
                   "first) and the per-tile ground class map the overview tints by climate and "
                   "month",
           "ground": {"file": "groundclass.png", "orientation": "pixel (x, y) is grid tile (x, y)",
                      "classes": GROUND_CLASSES},
           "flood": flood}
    lines = ["{", f' "version": 1,', f' "note": {json.dumps(doc["note"], ensure_ascii=False)},',
             f' "ground": {json.dumps(doc["ground"], ensure_ascii=False)},', ' "flood": [']
    for i, fb in enumerate(flood):
        lines.append("  " + json.dumps(fb, separators=(",", ":")) + ("," if i + 1 < len(flood) else ""))
    lines += [" ]", "}"]
    f_js = d / "seasons.json"
    f_js.write_text("\n".join(lines) + "\n")
    return [f_js, f_png]
