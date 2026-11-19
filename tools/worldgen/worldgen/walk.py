"""V17, the engine's walk rules (with a failing fixture in tests/test_crossings.py): every graph edge's course must be walkable step by step exactly as
the engine walks it (`src/world/world_map.cpp`: the walk bits built in `index`, `floorZ`,
`edgeZ`, `walkNeighbours`, `stairHead`), so no route the data offers is one walkers refuse.

A tile is walkable when it has ground that is neither water nor impassable and nothing stands on
it; or a stair or ramp stands on it (its geometry's walk tiles only, when it lists any); or a
walkable item (a deck when on water); or it is a walk tile of the landmark on it. A step between
two tiles of the same floor item (a stair, a landmark floor with `walk_z`) is always allowed;
otherwise the heights of the two facing edges must agree within half a level, a whole level when
either tile is a deck. A floor's edge height is its `walk_z` above the item's level when listed;
a stair's is its foot's level on the foot side and `rise` higher on the head side, and its sides
cannot be stepped over; anything else stands at its tile's level. The item's level is the level
of its origin tile in the grid (the footprint's smallest tx and ty). A kit stair's head is the
side opposite the one it faces; a landmark stair's head is the end along its catalog axis whose
outside tiles stand `rise` above its foot.
"""

from __future__ import annotations

import numpy as np

from .catalog import Catalog
from .compose import NONE16, World, live_items
from .coords import COLS, ROWS, to_plan
from .graph import Graph
from .raster import path_tiles

# Grid directions (kSteps: +x, +y, -x, -y) as plan steps: grid +x is plan south, grid +y west.
DIRS = [(0, 1), (-1, 0), (0, -1), (1, 0)]
KIT_HEAD = [3, 0, 1, 2]       # a kit stair's head by its rotation (worldgen's stair(face=...))


class EngineWalk:
    def __init__(self, world: World, cat: Catalog):
        self.w, self.cat = world, cat
        self.lp = cat.level_px
        T = world.T
        water_ids = [i for i, t in enumerate(world.terrains) if cat.is_water(t)]
        self.water = np.isin(T, water_ids)
        self.walk = (T != NONE16) & ~self.water & ((world.L & 0x40) == 0)
        self.floor = np.zeros_like(self.walk)
        self.deck = np.zeros_like(self.walk)
        self.occ = np.full(T.shape, -1, dtype=np.int32)
        self.items = world.items
        self.level = {}
        self.head = {}
        self.walk_z = {}
        for i, it in live_items(world):
            d = cat.items.get(it.id)
            if d is None:
                continue
            ox, oy = it.c + it.pw - 1, it.r          # the grid origin (smallest tx, ty) in plan
            self.level[i] = world.level(ox, oy)
            g = cat.geometry(it.id, it.k)
            walk = {(it.c + it.pw - 1 - dy, it.r + dx) for dx, dy in g.get("walk", [])}
            zs = {(it.c + it.pw - 1 - int(k.split(",")[1]), it.r + int(k.split(",")[0])): z
                  for k, z in g.get("walk_z", {}).items()}
            for c, r in it.tiles():
                if not (0 <= c < COLS and 0 <= r < ROWS) or T[r, c] == NONE16:
                    continue
                self.occ[r, c] = i
                if d.rise > 0:
                    ok = not walk or (c, r) in walk
                    self.walk[r, c] = ok
                    self.floor[r, c] = ok
                elif d.walkable:
                    self.walk[r, c] = True
                    self.deck[r, c] = bool(self.water[r, c])
                elif (c, r) in walk:
                    self.walk[r, c] = True
                    self.floor[r, c] = (c, r) in zs
                else:
                    self.walk[r, c] = False
                if (c, r) in zs:
                    self.walk_z[(c, r)] = zs[(c, r)]
            if d.rise > 0:
                self.head[i] = self._head(i, it, d)

    def _head(self, i, it, d) -> int | None:
        if d.layout == "rotate" and not d.landmark:
            return KIT_HEAD[it.k % 4]
        foot, up = self.level[i], self.level[i] + d.rise

        def score(gd):
            dc, dr = DIRS[gd]
            if dc:
                edge = it.c + it.pw if dc > 0 else it.c - 1
                tiles = [(edge, r) for r in range(it.r, it.r + it.ph)]
            else:
                edge = it.r + it.ph if dr > 0 else it.r - 1
                tiles = [(c, edge) for c in range(it.c, it.c + it.pw)]
            s = 0
            for c, r in tiles:
                if 0 <= c < COLS and 0 <= r < ROWS and self.w.T[r, c] != NONE16:
                    lv = self.w.level(c, r)
                    s += 1 if lv == up else -1 if lv == foot else 0
            return s

        axis = d.axis or "y"
        if d.layout == "rotate" and it.k % 2 == 1:
            axis = "y" if axis == "x" else "x"
        a = 0 if axis == "x" else 1
        fwd, back = score(a), score(a + 2)
        if fwd != back and max(fwd, back) > 0:
            return a if fwd > back else a + 2
        return None

    def edge_z(self, t, gd) -> int | None:
        c, r = t
        if not self.floor[r, c]:
            return self.w.level(c, r) * self.lp
        i = int(self.occ[r, c])
        if t in self.walk_z:
            return self.level[i] * self.lp + self.walk_z[t]
        d = self.cat.items[self.items[i].id]
        h = self.head.get(i)
        if d.rise > 0 and h is not None:
            if gd == h:
                return (self.level[i] + d.rise) * self.lp
            if gd == (h + 2) % 4:
                return self.level[i] * self.lp
            return None                      # the sides of a stair are parapets
        return self.level[i] * self.lp

    def step(self, a, b) -> str | None:
        """Why the engine refuses the step a -> b (4-neighbours), or None."""
        for t in (a, b):
            if not self.walk[t[1], t[0]]:
                return "a tile walkers cannot enter"
        gd = DIRS.index((b[0] - a[0], b[1] - a[1]))
        if self.floor[a[1], a[0]] and self.floor[b[1], b[0]] and \
                self.occ[a[1], a[0]] == self.occ[b[1], b[0]]:
            return None
        za, zb = self.edge_z(a, gd), self.edge_z(b, (gd + 2) % 4)
        if za is None or zb is None:
            return "over a stair's side"
        tol = self.lp if (self.deck[a[1], a[0]] or self.deck[b[1], b[0]]) else self.lp // 2
        if abs(za - zb) > tol:
            return f"a step of {abs(za - zb)} px"
        return None

    def art_step(self, a, b) -> bool:
        """A refused step of at most a level onto a landmark's own floor or tread, whose height
        is the art's `walk_z` (the tread's middle on a stair): the art's or the engine's rule to
        settle, not the layout's."""
        gd = DIRS.index((b[0] - a[0], b[1] - a[1]))
        za, zb = self.edge_z(a, gd), self.edge_z(b, (gd + 2) % 4)
        if za is None or zb is None or abs(za - zb) > self.lp:
            return False
        return any(t in self.walk_z and self.cat.items[self.items[int(self.occ[t[1], t[0]])].id].landmark
                   for t in (a, b))


_LAST: list = []


def _walk_of(world: World, cat: Catalog) -> EngineWalk:
    """One EngineWalk per composed world (a full check validates every layer on the same one)."""
    if not _LAST or _LAST[0] is not world:
        _LAST[:] = [world, EngineWalk(world, cat)]
    return _LAST[1]


def check(world: World, cat: Catalog, graph: Graph, ew: EngineWalk | None = None):
    """[(message, plan tile, level)] for every edge of `graph` the engine would refuse: an error,
    or a warning when only a landmark's own `walk_z` makes the step (`EngineWalk.art_step`)."""
    ew = ew or _walk_of(world, cat)
    out = []
    for e in graph.edges:
        a, b = graph.node(e.a), graph.node(e.b)
        if a is None or b is None:
            continue
        pts = [to_plan(*a.at), *[to_plan(*v) for v in e.via], to_plan(*b.at)]
        course = [t for t in path_tiles(pts) if 0 <= t[0] < COLS and 0 <= t[1] < ROWS]
        if len(course) == 1 and not ew.walk[course[0][1], course[0][0]]:
            out.append((f"{e.kind} {e.a} - {e.b} stands on a tile walkers cannot enter",
                        course[0], "error"))
            continue
        for p, q in zip(course, course[1:]):
            why = ew.step(p, q)
            if why:
                art = ew.art_step(p, q)
                out.append((f"{e.kind} {e.a} - {e.b}: the engine refuses the step {p} -> {q} "
                            f"({why}" + (": the landmark's walk_z (art geometry; the engine could "
                                         "take a stair's edges from its foot and head)" if art
                                         else "") + ")", q, "warning" if art else "error"))
                break
    return out
