"""Helpers for the small waypoint layers (docs/design/sets/world.md §4, §9.2).

A waypoint town keeps the land it stands on: `ground` copies the base underneath (terrain,
levels, sea and rivers with their flow and depth), so its edges meet the world without a seam.
Then a layout shapes relief (`raise_levels`, `flat`), lays its roads from the plan's portals at the
plan's levels (`portal_street`), places landmarks and kit, and finishes with `finish` (door
steps, the glow budget, face materials). `harbour_lane` makes the town's own lane meet the base
lane of the same port on the same tile. Everything is in the layout's local plan coordinates.
"""

from __future__ import annotations

import numpy as np

from plan import world_plan as P

from . import finish as F
from .compose import NONE16
from .dsl import Layout
from .graph import read_graph
from .shapes import Line, Mask, Rect

SEA = ("world.sea", "world.shallows")


def ground(L: Layout, district: str = "land") -> None:
    """The base below as this layer's ground: terrain ids, levels (local), water flow and sea
    depth. Land faces default to the terrain's first material; relief a layout raises picks its
    own with `level(face=)`."""
    w, h = L.size
    c0, r0 = L.origin
    below = L.below
    T = below.T[r0:r0 + h, c0:c0 + w]
    Lb = below.L[r0:r0 + h, c0:c0 + w]
    idx = {}
    for t in np.unique(T).tolist():
        if t == NONE16:
            continue
        tid = below.terrains[t]
        idx[t] = L._terrain_index(tid, L.source)
    out = np.full((h, w), -1, dtype=np.int16)
    for t, i in idx.items():
        out[T == t] = i
    L.T[:] = out
    L.LV[:] = (Lb & 0x0F).astype(np.int16) - L.base_level
    water = np.zeros((h, w), dtype=bool)
    for t, tid in enumerate(L.terrains):
        if L.cat.is_water(tid):
            water |= L.T == t
    L.AUX[water] = ((Lb[water] >> 4) & 3).astype(np.int8)
    L.district(district, Rect(0, 0, w - 1, h - 1))


def local_portal(L: Layout, pid: str) -> tuple[int, int]:
    """The portal's tile in local coordinates; when the plan's tile is in the neighbouring
    layer (two authored layers touching), the tile across the shared edge on this side."""
    layers, (c, r), _lv = P.PORTALS[pid]
    w, h = L.size
    c, r = c - L.origin[0], r - L.origin[1]
    return min(max(c, 0), w - 1), min(max(r, 0), h - 1)


def portal_level(L: Layout, pid: str) -> int:
    """The plan's level of a portal, local to this layer."""
    return P.PORTALS[pid][2] - L.base_level


def portal_street(L: Layout, pid: str, points, *, width: int = 2, paving: str,
                  kind: str = "road", level: int | None = None):
    """A street from the portal tile (on the layer's edge) through `points`, its tiles at the
    portal's plan level (or `level`), so the base road meets it on the same tile and level."""
    start = local_portal(L, pid)
    pts = [start] + [tuple(p) for p in points]
    lv = portal_level(L, pid) if level is None else level
    L.level(Line(pts, width), lv)
    return L.street(pts, width=width, paving=paving, kind=kind, portal=pid)


def raise_levels(L: Layout, shape, top: int, base: int, face: str, steps: float = 1.5) -> None:
    """Raise ground inside `shape`: `base` at its rim rising by a level every `steps` tiles
    inward up to `top` (a tell, an acropolis, a citadel mound), faces of `face`."""
    w, h = L.size
    m = L._mask(shape)
    dist = np.zeros((h, w), dtype=np.int32)
    cur = m.copy()
    k = 0
    while cur.any():
        k += 1
        dist[cur] = k
        nxt = cur.copy()
        nxt[1:, :] &= cur[:-1, :]
        nxt[:-1, :] &= cur[1:, :]
        nxt[:, 1:] &= cur[:, :-1]
        nxt[:, :-1] &= cur[:, 1:]
        cur = nxt
    lv = np.where(m, np.minimum(top, base + (dist - 1) // max(1, int(round(steps)))), 0)
    for v in range(base, top + 1):
        sel = m & (lv == v)
        if sel.any():
            L.level(Mask(0, 0, sel), int(v), face=face)


def flat(L: Layout, shape, level: int, face: str | None = None) -> None:
    L.level(shape, level, face=face)


def harbour_lane(L: Layout, lane_id: str, points, *, port: str, home: str | None = None) -> None:
    """The town's harbour lane from its quay (`points[0]`) to the base lane that serves `port`:
    its last point is that base lane's port tile, so the two lanes meet on one tile."""
    pts = [tuple(p) for p in points]
    meet = base_port_tile(L, port)
    if meet is not None:
        pts.append(meet)
    ports = {home or "quay": 0, port: len(pts) - 1, "start": 0, "end": len(pts) - 1}
    L.lane(lane_id, pts, kind="sea", ports=ports)


def base_port_tile(L: Layout, port: str):
    """The local tile of the base graph's lane port named `port` (the build's base, else the
    committed file; None if absent)."""
    from pathlib import Path
    g = L.graphs.get("base")
    if g is None:
        f = Path(L.cat.root) / "assets/world/layers/base.graph.json"
        if not f.exists():
            return None
        g = read_graph(f.read_text())
    from .coords import to_plan
    for ln in g.lanes:
        for p in ln.ports:
            if p.id == port:
                c, r = to_plan(*ln.points[p.at])
                return c - L.origin[0], r - L.origin[1]
    return None


def river_level(L: Layout, points, cap: int) -> int:
    """A level (local) for a river a town paints along `points`: no higher than the base's river
    where it flows in (the tile beyond the first point) and no higher than `cap`."""
    (ac, ar), (bc, br) = points[0], points[1]
    dc = (ac > bc) - (ac < bc)
    dr = (ar > br) - (ar < br)
    best = cap
    for k in range(1, 4):
        c, r = ac + dc * k, ar + dr * k
        t = L.below_terrain(c, r)
        if t is not None and L.cat.is_water(t) and t not in SEA:
            best = min(best, L.below_level(c, r))
            break
    return best


def finish(L: Layout, prefer_face: str, glow_rank: dict | None = None) -> None:
    F.clear_doors(L, all_slots=True)
    F.glow_cap(L, glow_rank or {}, cap=36)
    F.fit_faces(L, prefer_face)
    # Ground left at or below the layer's base level keeps no face its terrain does not list.
    for t, tid in enumerate(L.terrains):
        allowed = [L.faces.index(f) for f in L.cat.faces(tid) if f in L.faces]
        bad = (L.T == t) & (L.FACE >= 0) & ~np.isin(L.FACE, allowed)
        L.FACE[bad] = -1


def climb(L: Layout, points, z0: int, *, rise: int, paving: str, kind: str = "street",
          item: str = "world.stair_stone") -> int:
    """A path through `points` (axis-parallel runs) climbing `rise` levels from `z0`: on each
    straight stretch long enough, a flight of `item` (2 tiles, rise 1) with its foot and head in
    line, a level a flight. Returns the level the path ends at."""
    from .raster import path_tiles
    pts = [tuple(p) for p in points]
    L.street(pts, width=1, paving=paving, kind=kind)
    path = path_tiles(pts)
    n = len(path)
    z = z0
    i = 0
    lv = [z0] * n

    def step(k):
        return (path[k + 1][0] - path[k][0], path[k + 1][1] - path[k][1])

    while i < n - 1:
        if z - z0 < rise and i + 3 < n and step(i) == step(i + 1) == step(i + 2):
            dc, dr = step(i)
            lv[i + 1] = lv[i + 2] = z
            z += 1
            lv[i + 3] = z
            a, b = path[i + 1], path[i + 2]
            face = {(-1, 0): "east", (1, 0): "west", (0, -1): "south", (0, 1): "north"}[(dc, dr)]
            L.level(Rect(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])), lv[i + 1])
            L.level(Rect(*path[i + 3], *path[i + 3]), z)
            L.stair(item, rect=(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]),
                                max(a[1], b[1])), face=face)
            i += 3
            continue
        lv[i + 1] = z
        L.level(Rect(*path[i + 1], *path[i + 1]), z)
        i += 1
    L.level(Rect(*path[0], *path[0]), z0)
    return z


def pier(L: Layout, item: str, land: tuple[int, int], step: tuple[int, int], n: int) -> list:
    """A jetty or mole of up to n pieces from the land tile `land` (local) out over the water in
    direction `step`, starting on the first water tile, so its planks meet the strand (V16)."""
    def wet(c, r):
        return L.cat.is_water(L.terrain_at(c + L.origin[0], r + L.origin[1]) or "")
    c, r = land
    while not wet(c + step[0], r + step[1]):
        c, r = c + step[0], r + step[1]
        if not (0 <= c < L.size[0] and 0 <= r < L.size[1]):
            return []
    out = []
    for _ in range(n):
        c, r = c + step[0], r + step[1]
        if not (0 <= c < L.size[0] and 0 <= r < L.size[1]) or not wet(c, r):
            break
        out.append(L.place(item, at=(c, r)))
    return out
