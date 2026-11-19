"""Where walkers may be (docs/design/draw-order.md §5.2): the placed world's walkability rules,
checked against the engine walk model (`walk.EngineWalk`) over the whole composed world, and the
world-wide walkability report.

The engine model is the only idea of walkability here: a tile is walkable and a step between two
4-neighbours is allowed exactly as `src/world/world_map.cpp` decides. On top of it the world is
cut into walk components (tiles joined by allowed steps); a component is **reached** when a node
of some layer's graph lies in it (walkers travel the joined graphs, so a place no graph reaches
is one no walker sent there can get to).

Rules (codes `W-<rule>` after draw-order.md §5.2; all errors):

- `W-V3`  every footprint tile of an item at one level, walk tiles included (a landmark's floor
          that steps is drawn by its `walk_z`, never by the ground under it).
- `W-S3`  a placed stair or ramp meets the levels it joins: beyond its head walkable tiles at
          `foot + rise` and none at another level, before its foot walkable tiles at its level
          and none at another.
- `W-D1`  every walkable item on water (a deck) is reached, and every walkable tile of land it
          touches meets it by an allowed step (a mole's end at a quay a level higher than the
          planks is a deck hanging in the air).
- `W-D2`  a walkable item stands on water only if it is a crossing (bridge, ford, pontoon,
          jetty, mole, quay, pier): plants and reeds never become decks.
- `W-W5`  every walk tile of a placed item (a landmark's floor, a kit's yard, a stair's treads)
          is reached: no sealed courtyard, no stair to nowhere.
- `W-L1`  every slot spot stands where its user may stand: on a walkable tile, or (a slot used
          `on` its own item, a seat, a counter) on its own footprint beside a walkable tile;
          never under another item (a layout collision) and never inside its own item's
          non-walk tile otherwise (art geometry).
- `W-L2`  every slot spot's standing tile is reached.
- `W-L3`  a mooring spot is on water worked from a reached tile beside it; other spots are
          never on water.
- `W-G1`  the two ends of every graph edge lie in one walk component.
- `W-G2`  every graph node stands on a walkable tile; an edge never runs under an item that
          gives walkers no walk tile there (V17 refuses the step; this names the item).
- `W-O2`  every ship and barge lane runs on water, and under an item only where the item's
          geometry declares the clearance (`pass` per tile, else `under`, px) its tallest boat
          needs in its lowest form (`BOAT_PX`); a sea-going ship's lane passes no bridge.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from plan import world_plan as P
from plan.art_pending import ART

from .catalog import Catalog
from .compose import NONE16, World, live_items
from .coords import COLS, ROWS, to_grid, to_plan
from .dsl import PIERS, deck_kit
from .graph import Graph
from .raster import path_tiles
from .walk import DIRS, EngineWalk, _walk_of

BLOCK = -(1 << 30)          # edge height of a stair's side: no step over it
# How tall a boat stands above the water (px) when no catalog height says so: what an arch must
# clear for a lane to pass under it.
BOAT_H = 40
STEP4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class Finding:
    code: str
    layer: str
    msg: str
    at: tuple[int, int]
    region: str = ""
    item: str = ""
    slot: str = ""
    level: str = "error"
    index: int = -1          # the world item the finding is about, when it is about one


class Walkable:
    """The engine walk model with its components over one composed world."""

    def __init__(self, world: World, cat: Catalog, graphs: dict[str, Graph]):
        self.w, self.cat, self.graphs = world, cat, graphs
        self.ew: EngineWalk = _walk_of(world, cat)
        ew = self.ew
        lp = cat.level_px
        lv = (world.L & 0x0F).astype(np.int32)
        # Edge height per direction (DIRS index): ground at its level, floors and stairs by the
        # engine's edge_z (BLOCK where a stair's side is a parapet).
        ez = [lv * lp for _ in range(4)]
        for r, c in zip(*np.nonzero(ew.floor)):
            for gd in range(4):
                z = ew.edge_z((int(c), int(r)), gd)
                ez[gd][r, c] = BLOCK if z is None else z
        walk, floor, deck, occ = ew.walk, ew.floor, ew.deck, ew.occ
        self.lv = lv

        def allowed(a_sl, b_sl, gd):
            za, zb = ez[gd][a_sl], ez[(gd + 2) % 4][b_sl]
            tol = np.where(deck[a_sl] | deck[b_sl], lp, lp // 2)
            ok = (za != BLOCK) & (zb != BLOCK) & (np.abs(za - zb) <= tol)
            same = floor[a_sl] & floor[b_sl] & (occ[a_sl] == occ[b_sl])
            return walk[a_sl] & walk[b_sl] & (ok | same)

        # east: plan (c, r) -> (c + 1, r) is DIRS index 3; south: (c, r + 1) is index 0.
        self.east = allowed(np.s_[:, :-1], np.s_[:, 1:], DIRS.index((1, 0)))
        self.south = allowed(np.s_[:-1, :], np.s_[1:, :], DIRS.index((0, 1)))
        self.comp = self._components()
        self.reached: set[int] = set()
        for g in graphs.values():
            for n in g.nodes:
                c, r = to_plan(*n.at)
                if 0 <= c < COLS and 0 <= r < ROWS and self.comp[r, c] >= 0:
                    self.reached.add(int(self.comp[r, c]))

    def _components(self) -> np.ndarray:
        comp = np.full((ROWS, COLS), -1, dtype=np.int32)
        walk, east, south = self.ew.walk, self.east, self.south
        n = 0
        for r0, c0 in zip(*np.nonzero(walk)):
            if comp[r0, c0] >= 0:
                continue
            comp[r0, c0] = n
            q = deque([(int(c0), int(r0))])
            while q:
                c, r = q.popleft()
                for nc, nr, ok in ((c + 1, r, c + 1 < COLS and east[r, c]),
                                   (c - 1, r, c > 0 and east[r, c - 1]),
                                   (c, r + 1, r + 1 < ROWS and south[r, c]),
                                   (c, r - 1, r > 0 and south[r - 1, c])):
                    if ok and comp[nr, nc] < 0:
                        comp[nr, nc] = n
                        q.append((nc, nr))
            n += 1
        return comp

    def can_step(self, a, b) -> bool:
        (ac, ar), (bc, br) = a, b
        if ar == br and abs(ac - bc) == 1:
            return bool(self.east[ar, min(ac, bc)])
        if ac == bc and abs(ar - br) == 1:
            return bool(self.south[min(ar, br), ac])
        return False

    def is_reached(self, t) -> bool:
        c, r = t
        return 0 <= c < COLS and 0 <= r < ROWS and int(self.comp[r, c]) in self.reached


def _inside(t) -> bool:
    return 0 <= t[0] < COLS and 0 <= t[1] < ROWS


def _plan(it, dx: int, dy: int) -> tuple[int, int]:
    return it.c + it.pw - 1 - dy, it.r + dx


def _region_of(world: World, t) -> str:
    c, r = t
    if not _inside(t):
        return ""
    d = int(world.D[r, c])
    return "" if d == NONE16 else world.districts[d].split("/", 1)[0]


def _slot_def(cat: Catalog, iid: str, sid: str) -> dict:
    d = cat.items.get(iid)
    for s in d.extra.get("slots", []) if d else []:
        if isinstance(s, dict) and s.get("id") == sid:
            return s
    return {}


# Boat heights over the water by kind, px, from the art's models (art-smooth-land.md §8), in
# the lowest form a boat takes to pass a bridge (the barge with its mast lowered); sea-going
# ships never pass a bridge at all.
BOAT_PX = {"rome.barge": 27, "rome.merchantman": 105, "athens.trireme": 89,
           "athens.merchant": 93, "athens.fishing": 47, "world.fishing_boat": 63,
           "world.phoenician": 103, "world.reed_boat": 61, "world.kelek": 31, "world.quffa": 26}
SEA_GOING = {"rome.merchantman", "athens.trireme", "athens.merchant", "world.phoenician"}
NO_PASSAGE = 10 ** 6


def boat_heights(root, cat: Catalog) -> dict[str, int]:
    """Lane (`<layer>:<id>`, as tokens name it) -> the tallest boat any region's tokens sail on
    it, in px above the water (an actor kind's `h`, else BOAT_H)."""
    import json
    from pathlib import Path
    kinds: dict[str, int] = {}
    for f in sorted((Path(root) / "assets/sets").glob("*/catalog.json")):
        for a in json.loads(f.read_text()).get("actors", []):
            if isinstance(a, dict) and "id" in a:
                kinds[a["id"]] = NO_PASSAGE if a["id"] in SEA_GOING else \
                    int(a.get("h") or BOAT_PX.get(a["id"], BOAT_H))
    out: dict[str, int] = {}
    for f in sorted((Path(root) / "assets/regions").glob("*.json")):
        for tok in json.loads(f.read_text()).get("lanes_tokens", []):
            lane, who = tok.get("lane"), tok.get("actor")
            if isinstance(lane, str):
                out[lane] = max(out.get(lane, 0), kinds.get(who, BOAT_H))
    return out


def _clearance(it, geo: dict, t) -> int | None:
    """The clearance over plan tile t, px above the water: the geometry's per-tile `pass`
    (rows by grid dy; 255 open sky, 0 nothing passes), else its `under` per piece or for the
    whole item; None when undeclared."""
    dx, dy = t[1] - it.r, it.c + it.pw - 1 - t[0]
    passing = geo.get("pass")
    if isinstance(passing, list) and 0 <= dy < len(passing) and 0 <= dx < len(passing[dy]):
        return int(passing[dy][dx])
    under = geo.get("under")
    if not isinstance(under, list):
        return under
    for (px, py, pw, ph), u in zip(geo.get("pieces", []), under):
        if px <= dx < px + pw and py <= dy < py + ph:
            return int(u)
    return min(under) if under else None


def lane_tiles(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Tiles a boat's keel passes over between lane points (plan): its centre moves on straight
    lines through tile centres, so a diagonal that only grazes a corner is not counted."""
    out: list[tuple[int, int]] = []
    for (c0, r0), (c1, r1) in zip(points, points[1:]):
        n = max(1, 5 * max(abs(c1 - c0), abs(r1 - r0)))
        for k in range(n + 1):
            t = (int(c0 + 0.5 + (c1 - c0) * k / n), int(r0 + 0.5 + (r1 - r0) * k / n))
            if not out or out[-1] != t:
                out.append(t)
    return out or [tuple(p) for p in points[:1]]


def scan(world: World, cat: Catalog, graphs: dict[str, Graph], root=None,
         wk: Walkable | None = None) -> list[Finding]:
    """Every finding of the rules above over the whole composed world."""
    wk = wk or Walkable(world, cat, graphs)
    ew, lp, lv, items = wk.ew, cat.level_px, wk.lv, world.items
    water = ew.water
    out: list[Finding] = []

    cur = [-1]

    def add(code, layer, msg, at, item="", slot=""):
        out.append(Finding(code, layer, msg, at, _region_of(world, at), item=item, slot=slot,
                           index=cur[0] if item else -1))

    def owner_layer(t) -> str:
        o = int(world.owner[t[1], t[0]])
        return world.layers[o] if 0 <= o < len(world.layers) else ""

    def g(t) -> str:
        return f"grid {to_grid(*t)}"

    for i, it in live_items(world):
        d = cat.items.get(it.id)
        if d is None:
            continue
        cur[0] = i
        tiles = [t for t in it.tiles() if _inside(t) and world.T[t[1], t[0]] != NONE16]
        own = set(tiles)
        at = g((it.c + it.pw - 1, it.r))
        geo = cat.geometry(it.id, it.k)
        walk_t = {_plan(it, dx, dy) for dx, dy in geo.get("walk", [])}
        basin = {_plan(it, dx, dy) for dx, dy in geo.get("water", [])}
        wet_item = any(water[r, c] for c, r in tiles)
        # W-V3: one level under the whole footprint (items on water rise from the water).
        lvs = sorted({int(lv[r, c]) for c, r in tiles})
        if len(lvs) > 1 and d.rise == 0 and d.on != "water" and not wet_item:
            off = next(t for t in tiles if int(lv[t[1], t[0]]) != lvs[0])
            add("W-V3", it.layer, f"{it.id} at {at}: footprint over levels {lvs} (one level; a "
                "floor that steps is the art's walk_z)", off, it.id)
        if d.walkable and d.rise == 0 and wet_item:
            if not deck_kit(d):
                add("W-D2", it.layer, f"{it.id} at {at} is walkable and stands on water: only "
                    "crossings and piers carry walkers over water", (it.c, it.r), it.id)
            else:
                if not any(wk.is_reached(t) for t in tiles):
                    add("W-D1", it.layer, f"{it.id} at {at}: a deck no graph reaches",
                        (it.c, it.r), it.id)
                for t in tiles:
                    for dc, dr in STEP4:
                        n = (t[0] + dc, t[1] + dr)
                        if n in own or not _inside(n) or not ew.walk[n[1], n[0]] or \
                                water[n[1], n[0]] or ew.deck[n[1], n[0]] or wk.can_step(t, n):
                            continue
                        za = ew.edge_z(t, DIRS.index((dc, dr)))
                        zb = ew.edge_z(n, DIRS.index((-dc, -dr)))
                        diff = "" if za is None or zb is None else f" ({abs(za - zb)} px)"
                        add("W-D1", it.layer, f"{it.id} at {g(t)}: the land at {g(n)} meets the "
                            f"deck with a step walkers refuse{diff}", n, it.id)
        # W-W5: an item's walk area (floor tiles, a stair's treads) is reached.
        area = [t for t in tiles if ew.walk[t[1], t[0]] and (t in walk_t or d.rise > 0)]
        sealed = [t for t in area if not wk.is_reached(t)]
        if sealed:
            add("W-W5", it.layer, f"{it.id} at {at}: {len(sealed)} of {len(area)} walk tiles no "
                f"graph reaches (first {g(sealed[0])})", sealed[0], it.id)
        # W-S3: a stair's head and foot meet the levels it joins.
        if d.rise > 0:
            h = ew.head.get(i)
            if h is None:
                add("W-S3", it.layer, f"{it.id} at {at}: neither end stands {d.rise} level(s) "
                    "above the other (no head the engine can find)", (it.c, it.r), it.id)
            else:
                foot_z, head_z = ew.level[i] * lp, (ew.level[i] + d.rise) * lp
                for gd, want, what in ((h, head_z, "head"), ((h + 2) % 4, foot_z, "foot")):
                    dc, dr = DIRS[gd]
                    beyond = [(c + dc, r + dr) for c, r in area if (c + dc, r + dr) not in own]
                    good, bad = [], []
                    for n in beyond:
                        if not _inside(n) or not ew.walk[n[1], n[0]]:
                            continue
                        z = ew.edge_z(n, (gd + 2) % 4)
                        tol = lp if ew.deck[n[1], n[0]] else lp // 2
                        (good if z is not None and abs(z - want) <= tol else bad).append((n, z))
                    if bad or not good:
                        n, z = bad[0] if bad else ((beyond or [(it.c, it.r)])[0], None)
                        got = f"level {z / lp:g}" if z is not None else "no walkable tile"
                        add("W-S3", it.layer, f"{it.id} at {at}: its {what} side wants level "
                            f"{want // lp}, finds {got} at {g(n)}"
                            + (f" ({len(bad)} tile(s) off)" if bad else ""), n, it.id)
        # W-L1, W-L2, W-L3: slot spots.
        for sid, spots in geo.get("slots", {}).items():
            sdef = _slot_def(cat, it.id, sid)
            for s in spots:
                t = _plan(it, s["t"][0], s["t"][1])
                if not _inside(t):
                    add("W-L1", it.layer, f"{it.id}.{sid} spot off the map", (it.c, it.r),
                        it.id, sid)
                    continue
                c, r = t
                o = int(ew.occ[r, c])
                wet = bool(water[r, c]) or t in basin
                if sdef.get("kind") == "mooring" and wet:
                    near = [(c + a, r + b) for a, b in STEP4]
                    near += [(n[0] + a, n[1] + b) for n in near if n in own for a, b in STEP4]
                    if not any(_inside(n) and ew.walk[n[1], n[0]] and wk.is_reached(n)
                               for n in near):
                        add("W-L3", it.layer, f"{it.id}.{sid} mooring at {g(t)}: no reached "
                            "quay tile beside it", t, it.id, sid)
                    continue
                if wet and not ew.walk[r, c]:
                    add("W-L3", it.layer, f"{it.id}.{sid} spot at {g(t)} is on water", t,
                        it.id, sid)
                    continue
                stand = [t] if ew.walk[r, c] else []
                if not stand:
                    if o >= 0 and o != i:
                        add("W-L1", owner_layer(t) or it.layer, f"{it.id}.{sid} spot at {g(t)} "
                            f"lies under {items[o].id} (a layout collision)", t, it.id, sid)
                        continue
                    # A slot used on its own item (a seat, a throne, a counter) is reached from
                    # a walkable tile beside it.
                    if t in own and (sdef.get("where") == "on" or s.get("z", 0) > 0):
                        stand = [(c + a, r + b) for a, b in STEP4
                                 if _inside((c + a, r + b)) and ew.walk[r + b, c + a]]
                    if not stand:
                        why = "inside its own footprint on a tile its geometry does not make " \
                              "walkable (art geometry)" if t in own else \
                              "on a tile walkers cannot enter"
                        add("W-L1", it.layer, f"{it.id}.{sid} spot at {g(t)} is {why}", t,
                            it.id, sid)
                        continue
                if not any(wk.is_reached(x) for x in stand):
                    add("W-L2", it.layer, f"{it.id}.{sid} spot at {g(t)} stands on walk ground "
                        "no graph reaches", t, it.id, sid)

    cur[0] = -1
    # Graphs: nodes on walkable tiles, edges never under an item, edge ends in one component.
    for name, gr in graphs.items():
        for n in gr.nodes:
            t = to_plan(*n.at)
            if _inside(t) and not ew.walk[t[1], t[0]]:
                o = int(ew.occ[t[1], t[0]])
                what = items[o].id if o >= 0 else (world.terrain_id(*t) or "no ground")
                add("W-G2", name, f"node {n.id} at {g(t)} stands on a tile walkers cannot "
                    f"enter ({what})", t, items[o].id if o >= 0 else "")
        for e in gr.edges:
            a, b = gr.node(e.a), gr.node(e.b)
            if a is None or b is None:
                continue
            pts = [to_plan(*a.at), *[to_plan(*v) for v in e.via], to_plan(*b.at)]
            course = [t for t in path_tiles(pts) if _inside(t)]
            if not course:
                continue
            for t in course:
                o = int(ew.occ[t[1], t[0]])
                if o >= 0 and not ew.walk[t[1], t[0]]:
                    add("W-G2", name, f"{e.kind} {e.a} - {e.b} runs under {items[o].id} at "
                        f"{g(t)}, which gives walkers no walk tile there", t, items[o].id)
                    break
            ta, tb = course[0], course[-1]
            ca, cb = int(wk.comp[ta[1], ta[0]]), int(wk.comp[tb[1], tb[0]])
            if ca >= 0 and cb >= 0 and ca != cb:
                add("W-G1", name, f"{e.kind} {e.a} - {e.b}: its ends lie in two walk components "
                    "(no walk joins them)", tb)

    # Lanes: on water; under an item only through its declared clearance.
    heights = boat_heights(root, cat) if root is not None else {}
    for name, gr in graphs.items():
        for ln in gr.lanes:
            need = heights.get(f"{name}:{ln.id}", BOAT_H)
            told: set = set()
            for t in lane_tiles([to_plan(*p) for p in ln.points]):
                if not _inside(t):
                    continue
                c, r = t
                o = int(ew.occ[r, c])
                geo = cat.geometry(items[o].id, items[o].k) if o >= 0 else {}
                if not water[r, c]:
                    if t not in {_plan(items[o], a, b) for a, b in geo.get("water", [])} \
                            and "dry" not in told:
                        told.add("dry")
                        add("W-O2", name, f"lane {ln.id} ({ln.kind}) crosses {g(t)}, which is "
                            f"not water ({world.terrain_id(c, r)})", t)
                    continue
                if o < 0 or o in told:
                    continue
                d = cat.items.get(items[o].id)
                if d is None or not (d.walkable or d.landmark):
                    continue        # a buoy, a fish trap, a mooring post: floats beside
                under = _clearance(items[o], geo, t)
                if d.id.split(".")[-1] in PIERS or d.id.split(".")[-1] == "t_reeds":
                    told.add(o)
                    add("W-O2", name, f"lane {ln.id} ({ln.kind}) runs over {d.id} at {g(t)}: "
                        "boats lie beside a pier or a reed bed, never over it", t, d.id)
                elif under is None or int(under) < need:
                    told.add(o)
                    clear = "declares no clearance (`pass`)" if under is None else \
                        f"clears {under} px, and a sea-going ship passes no bridge" \
                        if need >= NO_PASSAGE else f"clears {under} px, its boats need {need}"
                    add("W-O2", name, f"lane {ln.id} ({ln.kind}) passes under {d.id} at {g(t)}, "
                        f"which {clear}", t, d.id)
    return out


_CACHE: list = []


def findings(world: World, cat: Catalog, graphs: dict[str, Graph], root=None) -> list[Finding]:
    """`scan` once per composed world and set of graphs (a full check validates every layer on
    the same ones), with faults the art lane owns (plan/art_pending.py) as warnings."""
    key = (id(world), tuple(sorted((k, id(v)) for k, v in graphs.items())))
    if _CACHE and _CACHE[0] == key:
        return _CACHE[1]
    wk = Walkable(world, cat, graphs)
    out = scan(world, cat, graphs, root, wk)
    for f in out:
        why = ART.get((f.code, f.item, f.slot)) or ART.get((f.code, f.item, ""))
        if why:
            f.level = "warning"
            f.msg += f" [art: {why}]"
    _CACHE[:] = [key, out, wk]
    return out


def stale_art(found: list[Finding]) -> list[tuple]:
    """Entries of plan/art_pending.py that no finding matches any more: the art has landed and
    the entry must go, so the list never outlives its faults."""
    used = {(f.code, f.item, f.slot) for f in found} | {(f.code, f.item, "") for f in found}
    return sorted(k for k in ART if k not in used)


@dataclass
class RegionStats:
    walk: int = 0
    item_walk: int = 0
    item_unreached: int = 0
    ground_off: int = 0
    slots: int = 0
    nodes: int = 0
    lanes: int = 0


def stats(world: World, cat: Catalog, graphs: dict[str, Graph],
          wk: Walkable | None = None) -> dict:
    """Per region: walk tiles, those on items and how many of them no graph reaches, walkable
    ground in components no graph reaches (country benches, islets: walkers only wander there),
    slot spots and graph nodes checked, edges by kind."""
    if wk is None:
        key = (id(world), tuple(sorted((k, id(v)) for k, v in graphs.items())))
        wk = _CACHE[2] if _CACHE and _CACHE[0] == key else Walkable(world, cat, graphs)
    ew = wk.ew
    reached = np.isin(wk.comp, np.array(sorted(wk.reached), dtype=np.int32))
    dist = world.D
    names = np.array([d.split("/", 1)[0] for d in world.districts] + [""])
    reg = names[np.where(dist == NONE16, len(world.districts), dist)]
    out: dict[str, RegionStats] = {}
    # Walk areas of items: floors and treads, decks, the walk tiles of kit and landmarks; a
    # walkable plant or threshing floor on land is ground.
    solid = np.array([not (cat.items.get(it.id) and cat.items[it.id].walkable)
                      for it in world.items] + [False])
    on_item = ew.walk & (ew.floor | ew.deck | solid[np.where(ew.occ >= 0, ew.occ, -1)])
    for rid in sorted(set(reg[ew.walk].tolist()) - {""}):
        m = reg == rid
        s = out.setdefault(rid, RegionStats())
        s.walk = int((ew.walk & m).sum())
        s.item_walk = int((on_item & m).sum())
        s.item_unreached = int((on_item & m & ~reached).sum())
        s.ground_off = int((ew.walk & ~on_item & m & ~reached).sum())
    for _, it in live_items(world):
        geo = cat.geometry(it.id, it.k)
        for spots in geo.get("slots", {}).values():
            for sp in spots:
                t = _plan(it, sp["t"][0], sp["t"][1])
                rid = _region_of(world, t)
                if rid:
                    out.setdefault(rid, RegionStats()).slots += 1
    edges: dict[str, dict[str, int]] = {}
    for name, gr in graphs.items():
        for n in gr.nodes:
            rid = _region_of(world, to_plan(*n.at))
            if rid:
                out.setdefault(rid, RegionStats()).nodes += 1
        for e in gr.edges:
            a = gr.node(e.a)
            rid = _region_of(world, to_plan(*a.at)) if a else ""
            if rid:
                edges.setdefault(rid, {}).setdefault(e.kind, 0)
                edges[rid][e.kind] += 1
        for ln in gr.lanes:
            rid = _region_of(world, to_plan(*ln.points[0])) if ln.points else ""
            if rid:
                out.setdefault(rid, RegionStats()).lanes += 1
    return {"regions": out, "edges": edges, "components": int(wk.comp.max()) + 1,
            "reached": len(wk.reached)}


def report_md(st: dict) -> str:
    """The walkability table (Markdown) for out/worldgen/walkable.md and the world report."""
    kinds = sorted({k for e in st["edges"].values() for k in e})
    head = ["region", "walk tiles", "item walk areas", "unreached", "ground off-graph",
            "slot spots", "nodes", "lanes"] + kinds
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    tot = RegionStats()
    tk: dict[str, int] = {}
    for rid, s in sorted(st["regions"].items()):
        e = st["edges"].get(rid, {})
        lines.append("| " + " | ".join([rid] + [str(x) for x in (
            s.walk, s.item_walk, s.item_unreached, s.ground_off, s.slots, s.nodes, s.lanes)]
            + [str(e.get(k, 0)) for k in kinds]) + " |")
        for f in ("walk", "item_walk", "item_unreached", "ground_off", "slots", "nodes", "lanes"):
            setattr(tot, f, getattr(tot, f) + getattr(s, f))
        for k in kinds:
            tk[k] = tk.get(k, 0) + e.get(k, 0)
    lines.append("| **all** | " + " | ".join(str(x) for x in (
        tot.walk, tot.item_walk, tot.item_unreached, tot.ground_off, tot.slots, tot.nodes,
        tot.lanes)) + " | " + " | ".join(str(tk[k]) for k in kinds) + " |")
    return "\n".join(lines) + "\n" + \
        f"\n{st['components']} walk components world-wide, {st['reached']} of them reached by " \
        "a graph node.\n"


def stretch_regions() -> set[str]:
    return {rid for rid, v in P.REGIONS.items() if v[0] == "stretch"}
