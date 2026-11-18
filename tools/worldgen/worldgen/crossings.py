"""V16, crossings: every bridge, ford, pontoon, pier, gate, stair and ramp meets what it joins.

V5 lets walkers change level anywhere on a deck or a stair, which is right for the walk itself
but says nothing about whether the art's ends meet the ground. This rule does, in pixels, the
way the engine draws them:

- **Decks** are the tiles a walker stands on above the ground: a landmark's walk tiles (at the
  item's level plus their `walk_z`) and walkable kit on water (bridges, fords, pontoons, jetties,
  moles: their planks meet the bank at the water's level). Wherever a graph edge steps onto or
  off a deck, the two walking heights may differ by at most half a level (`STEP_PX`): a landing a
  level above or below the deck end is a bridge hanging in the air, whatever V5 allows.
- **Crossings** (bridges, fords, pontoons, a landmark on water) must be joined to the graph at
  two ends or more, and a landmark deck must not end over open water.
- **Stairs and ramps** (kit with `rise`, landmark stairs with `climb`): the tile before the foot
  stands at the stair's level and the tile beyond the head `rise` higher, both walkable and on the
  graph's course (V3 checks the levels of kit stairs only when the layout is compiled; this runs
  on committed files too).
"""

from __future__ import annotations

import numpy as np

from .catalog import Catalog
from .compose import World, live_items
from .coords import COLS, ROWS, to_plan
from .graph import Graph
from .raster import path_tiles

STEP_PX = 8                 # half a level at 16 px: what the art's ramps and kerbs absorb
# A walker going up a stair moves this way in plan (dc, dr), by the geometry's `climb` (grid
# axes: +x = plan south, +y = plan west).
CLIMB = {"+x": (0, 1), "-x": (0, -1), "+y": (-1, 0), "-y": (1, 0)}
# Kit stairs climb toward -y at r0 and turn clockwise with k (art-corrections: one rule).
KIT_CLIMB = ["-y", "+x", "+y", "-x"]
PIERS = ("jetty", "mole")


def _plan_tile(it, dx: int, dy: int) -> tuple[int, int]:
    return it.c + it.pw - 1 - dy, it.r + dx


def decks(world: World, cat: Catalog) -> tuple[dict, dict]:
    """(tile -> walking height in px, tile -> index of the item) for every deck in the world:
    landmark walk tiles anywhere, walkable kit on water."""
    lp = cat.level_px
    water_ids = [i for i, t in enumerate(world.terrains) if cat.is_water(t)]
    water = np.isin(world.T, water_ids)
    height: dict[tuple[int, int], int] = {}
    owner: dict[tuple[int, int], int] = {}
    for i, it in live_items(world):
        d = cat.items.get(it.id)
        if d is None or d.rise > 0:
            continue
        base = world.level(it.c, it.r) * lp
        if d.walkable and d.on == "water":
            for t in it.tiles():
                height[t], owner[t] = base, i
        elif not d.walkable:
            g = cat.geom.get(it.id, {}).get(f"r{it.k}", {})
            z = g.get("walk_z", {})
            for dx, dy in g.get("walk", []):
                c, r = _plan_tile(it, dx, dy)
                if d.on == "water" or water[r, c] or d.landmark:
                    height[(c, r)] = base + int(z.get(f"{dx},{dy}", 0))
                    owner[(c, r)] = i
    return height, owner


def _course(g: Graph):
    for e in g.edges:
        a, b = g.node(e.a), g.node(e.b)
        if a is None or b is None:
            continue
        pts = [to_plan(*a.at), *[to_plan(*v) for v in e.via], to_plan(*b.at)]
        yield e, [(c, r) for c, r in path_tiles(pts) if 0 <= c < COLS and 0 <= r < ROWS]


def _is_crossing(d, cat: Catalog) -> bool:
    """Bridges, fords, pontoons, a landmark on water; gates a road passes through."""
    if any(p in d.id for p in PIERS):
        return False
    if d.on == "water" and (d.walkable or d.landmark):
        return True
    name = d.id.split(".")[-1]
    return name.endswith(("gate", "gates")) and (d.walkable or d.id in cat.geom)


def check(world: World, cat: Catalog, layer: str, graph: Graph, walk: np.ndarray,
          all_graphs: dict[str, Graph] | None = None) -> list[tuple[str, str, tuple | None]]:
    """[(level, message, plan tile)] for the target layer's crossings and its graph's steps."""
    lp = cat.level_px
    out: list[tuple[str, str, tuple | None]] = []
    height, owner = decks(world, cat)
    items = world.items
    lv = world.L & 0x0F
    water_ids = [i for i, t in enumerate(world.terrains) if cat.is_water(t)]
    water = np.isin(world.T, water_ids)

    def ground_h(t):
        return height.get(t, int(lv[t[1], t[0]]) * lp)

    stairs = {t for _, it in live_items(world)
              if (d_ := cat.items.get(it.id)) is not None and d_.rise > 0 for t in it.tiles()}

    def name(i):
        return items[i].id

    # Steps of the graph onto and off decks.
    on_graph: set[tuple[int, int]] = set()
    node_tiles = {to_plan(*n.at) for g in list((all_graphs or {}).values()) + [graph]
                  for n in g.nodes if n.kind == "dest"}
    entries: dict[int, set] = {}
    for g in list((all_graphs or {}).values()) + [graph]:
        for _, course in _course(g):
            on_graph.update(course)
    seen = set()
    graphs = dict(all_graphs or {})
    graphs[layer] = graph
    steps = [(e, course) for g in graphs.values() for e, course in _course(g)]
    for e, course in steps:
        for a, b in zip(course, course[1:]):
            da, db = owner.get(a), owner.get(b)
            if da == db:
                continue
            for deck, land, i in ((a, b, da), (b, a, db)):
                if i is None or items[i].layer != layer:
                    continue
                entries.setdefault(i, set()).add(land)
                if land in owner and _same_crossing(items, owner[land], i):
                    continue
                if land in stairs:
                    continue  # a stair's own foot and head are checked below
                if (deck, land) in seen:
                    continue
                seen.add((deck, land))
                hd, hl = height[deck], ground_h(land)
                d_i = cat.items.get(name(i))
                wet = d_i is not None and (d_i.on == "water" or bool(water[deck[1], deck[0]]))
                if abs(hd - hl) > STEP_PX:
                    what = name(owner[land]) + "'s deck" if land in owner else \
                        f"the ground (level {int(lv[land[1], land[0]])})"
                    # On dry land a landmark's floor may carry its own steps (art geometry).
                    out.append(("error" if wet else "warning",
                                f"{name(i)}: its deck end stands at {hd} px, {what} it "
                                f"meets at {hl} px ({hd - hl:+d} px): the landing is not joined "
                                f"({e.kind} {e.a} - {e.b})", land))

    # Crossings joined at both ends; landmark decks that end over water.
    for i, it in live_items(world):
        if it.layer != layer:
            continue
        d = cat.items.get(it.id)
        if d is None or not _is_crossing(d, cat):
            continue
        group = _crossing_group(items, owner, i, cat)
        ends = set()
        for j in group:
            ends |= {t for t in entries.get(j, set()) if owner.get(t) not in group}
        # A walkway that ends at a place of its own (a pier's head, a landing stage) counts that
        # node as an end.
        ends |= {t for t in node_tiles if owner.get(t) in group}
        if i == min(group):
            if not ends:
                out.append(("error", f"{it.id}: a crossing no graph edge uses", (it.c, it.r)))
            elif len(ends) < 2:
                out.append(("error", f"{it.id}: joined to the graph at one end only "
                            f"({sorted(ends)[0]})", (it.c, it.r)))
        if d.landmark and d.on == "water":
            mine = {t for t, j in owner.items() if j == i}
            for c, r in mine:
                nb = [(dc, dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                      if (c + dc, r + dr) in mine]
                if len(nb) != 1:
                    continue  # not the end of a walkway (an island's quay runs along its edge)
                n = (c - nb[0][0], r - nb[0][1])
                if n in owner or not (0 <= n[0] < COLS and 0 <= n[1] < ROWS):
                    continue
                if water[n[1], n[0]]:
                    out.append(("error", f"{it.id}: its walkway ends over open water at "
                                f"{(c, r)} (the art spans less than the gap)", n))

    # Connect crossings and piers run along one axis: a piece with neighbours of its own kind on
    # both axes draws a crossroads of decks, and a run two wide reads as a hollow frame.
    runs = {(it.id, it.c, it.r) for _, it in live_items(world)
            if (d_ := cat.items.get(it.id)) is not None and d_.layout == "connect"}
    for i, it in live_items(world):
        if it.layer != layer:
            continue
        d = cat.items.get(it.id)
        if d is None or d.layout != "connect" or d.on != "water":
            continue
        ew = {(it.id, it.c + 1, it.r), (it.id, it.c - 1, it.r)} & runs
        ns = {(it.id, it.c, it.r + 1), (it.id, it.c, it.r - 1)} & runs
        if ew and ns:
            out.append(("error", f"{it.id}: joins pieces on both axes (a run laid more than one "
                        "tile wide draws as a frame): lay it one tile wide", (it.c, it.r)))

    # Stairs and ramps: the landing before the foot and beyond the head. Flights laid side by
    # side (a three-wide marble stair, a two-lane ramp) share their landings: the path may meet
    # any of them.
    flights = _flights(world, cat)
    met: dict[int, set] = {}
    pending: list = []
    for i, it in live_items(world):
        if it.layer != layer:
            continue
        d = cat.items.get(it.id)
        if d is None or d.rise <= 0:
            continue
        g = cat.geom.get(it.id, {}).get(f"r{it.k}", {})
        climb = g.get("climb") or (KIT_CLIMB[it.k % 4] if not d.landmark else None)
        if climb not in CLIMB:
            continue
        dc, dr = CLIMB[climb]
        low = int(lv[it.r, it.c])
        tiles = list(it.tiles())
        if dc:
            edge_lo = min(c for c, _ in tiles) if dc > 0 else max(c for c, _ in tiles)
            edge_hi = max(c for c, _ in tiles) if dc > 0 else min(c for c, _ in tiles)
            feet = [(edge_lo - dc, r) for r in range(it.r, it.r + it.ph)]
            heads = [(edge_hi + dc, r) for r in range(it.r, it.r + it.ph)]
        else:
            edge_lo = min(r for _, r in tiles) if dr > 0 else max(r for _, r in tiles)
            edge_hi = max(r for _, r in tiles) if dr > 0 else min(r for _, r in tiles)
            feet = [(c, edge_lo - dr) for c in range(it.c, it.c + it.pw)]
            heads = [(c, edge_hi + dr) for c in range(it.c, it.c + it.pw)]
        level = "warning" if d.landmark else "error"
        for row, want, what in ((feet, low * lp, "foot"), (heads, (low + d.rise) * lp, "head")):
            row = [t for t in row if 0 <= t[0] < COLS and 0 <= t[1] < ROWS]
            used = [t for t in row if t in on_graph]
            if used:
                met.setdefault(flights[i], set()).add(what)
            pending.append((i, it, level, what, climb, row))
            for t in used:
                if not walk[t[1], t[0]]:
                    out.append((level, f"{it.id}: the landing at its {what} is not walkable", t))
                elif abs(ground_h(t) - want) > STEP_PX:
                    out.append((level, f"{it.id}: the landing at its {what} stands at "
                                f"{ground_h(t)} px, the stair's {what} at {want} px", t))
    told = set()
    for i, it, level, what, climb, row in pending:
        if what not in met.get(flights[i], set()) and (flights[i], what) not in told:
            told.add((flights[i], what))
            out.append((level, f"{it.id}: no path meets its {what} ({climb} climb)",
                        row[0] if row else (it.c, it.r)))
    return out


def _flights(world: World, cat: Catalog) -> dict[int, int]:
    """Stair item -> the smallest index of the flight it belongs to (same id, rotation and level,
    touching side by side)."""
    st = {}
    for i, it in live_items(world):
        d = cat.items.get(it.id)
        if d is not None and d.rise > 0:
            for t in it.tiles():
                st[t] = i
    parent = {i: i for i in set(st.values())}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    items = world.items
    for (c, r), i in st.items():
        for n in ((c + 1, r), (c, r + 1)):
            j = st.get(n)
            if j is not None and j != i and items[i].id == items[j].id and \
                    items[i].k == items[j].k and world.level(c, r) == world.level(*n):
                parent[find(i)] = find(j)
    return {i: find(i) for i in parent}


def _same_crossing(items, a: int, b: int) -> bool:
    """Two pieces of one run of connect kit (a bridge of several tiles) are one deck."""
    return items[a].id == items[b].id


def _crossing_group(items, owner, i: int, cat: Catalog) -> set[int]:
    """The items whose decks touch item i's, transitively (a run of kit pieces; an island and
    its bridges): one crossing, joined at its outer ends."""
    group, todo = {i}, [i]
    by_item: dict[int, list] = {}
    for t, j in owner.items():
        by_item.setdefault(j, []).append(t)
    while todo:
        j = todo.pop()
        for c, r in by_item.get(j, []):
            for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                k = owner.get(n)
                if k is not None and k not in group:
                    d = cat.items.get(items[k].id)
                    if d is not None and d.on == "water":
                        group.add(k)
                        todo.append(k)
    return group
