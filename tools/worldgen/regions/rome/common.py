"""Layout helpers shared by the Roman layers (`rome`, `ostia`): stair runs carved into a level
array, irregular lanes grown from the streets, kit that opens on a street, meeting the world at
the layer's edges, named nodes snapped to the streets, and clean-up of kit whose slots cannot be
used. Layouts are loaded by path, so each loads this file by path too.
"""

from __future__ import annotations

import heapq

import numpy as np

from worldgen import rng
from worldgen.dsl import Layout
from worldgen.finish import put, use_tiles
from worldgen.shapes import Mask, Rect

STEP = {"west": (-1, 0), "north": (0, -1), "east": (1, 0), "south": (0, 1)}
STAIR = "rome.stair_travertine"


def mask(L: Layout, shape) -> np.ndarray:
    w, h = L.size
    return shape.mask(0, 0, w, h)


def facing(dc: int, dr: int) -> str:
    """The facing of kit whose front looks along (dc, dr)."""
    return {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(dc, dr)]


def corners(tiles) -> list:
    """The vertices of a 4-connected tile path (its first, last and turning tiles)."""
    keep = [tiles[0]]
    for a, b in zip(tiles[1:], tiles[2:] + [None]):
        if b is not None and (keep[-1][0] == a[0] == b[0] or keep[-1][1] == a[1] == b[1]):
            continue
        keep.append(a)
    return keep


def expand(points) -> list:
    """Every tile of an axis-parallel polyline, in order."""
    out = [tuple(points[0])]
    for (c0, r0), (c1, r1) in zip(points, points[1:]):
        if c0 != c1 and r0 != r1:
            raise ValueError(f"diagonal step {(c0, r0)} -> {(c1, r1)} in a stair run")
        dc, dr = (c1 > c0) - (c1 < c0), (r1 > r0) - (r1 < r0)
        c, r = c0, r0
        while (c, r) != (c1, r1):
            c, r = c + dc, r + dr
            out.append((c, r))
    return out


# --- stair runs ---------------------------------------------------------------------------------
# A run climbs along a path of tiles from its foot (a street tile at `lvl0`): two tiles of flight,
# one tile of landing a level up, and so on. Flights are straight; a run turns only on a landing.

def run_plan(points, lvl0: int, rise: int):
    """[(flight tiles, face, level)], [(landing tile, level)] of a run; raises if it bends in a
    flight or the path is too short."""
    path = expand(points)
    if len(path) < 3 * rise + 1:
        raise ValueError(f"stair run from {path[0]} needs {3 * rise + 1} tiles, has {len(path)}")
    flights, landings = [], []
    for k in range(rise):
        a, b, land = path[3 * k + 1], path[3 * k + 2], path[3 * k + 3]
        prev = path[3 * k]
        d = (a[0] - prev[0], a[1] - prev[1])
        if (b[0] - a[0], b[1] - a[1]) != d:
            raise ValueError(f"stair run bends inside a flight at {a}")
        face = facing(-d[0], -d[1])
        flights.append(([a, b], face, lvl0 + k))
        landings.append((land, lvl0 + k + 1))
    return flights, landings


def carve_run(lv: np.ndarray, points, lvl0: int, rise: int) -> None:
    flights, landings = run_plan(points, lvl0, rise)
    for tiles, _f, k in flights:
        for c, r in tiles:
            lv[r, c] = k
    for (c, r), k in landings:
        lv[r, c] = k


def build_run(L: Layout, points, lvl0: int, rise: int, name: str, paving: str) -> None:
    flights, landings = run_plan(points, lvl0, rise)
    for i, (tiles, face, _k) in enumerate(flights):
        cs, rs = [t[0] for t in tiles], [t[1] for t in tiles]
        L.stair(STAIR, rect=(min(cs), min(rs), max(cs), max(rs)), face=face,
                name=name if i == 0 else f"{name}_{i}")
    for (c, r), _k in landings:
        L.paint(Rect(c, r, c, r), paving)


# --- ways ---------------------------------------------------------------------------------------

def free_ground(L: Layout) -> np.ndarray:
    """Tiles with ground, no item, not impassable and not water."""
    water = np.zeros(L.T.shape, dtype=bool)
    for t, name in enumerate(L.terrains):
        if L.cat.is_water(name):
            water |= L.T == t
    return (L.T >= 0) & (L.OCC < 0) & ~L.IMP & ~water


def connect(L: Layout, start, area: np.ndarray, turn: int = 3, reach: int = 40,
            avoid: np.ndarray | None = None):
    """The cheapest 4-step path over free ground of one level from `start` to the nearest street
    tile (turns cost extra, so lanes run straight and jog), or None."""
    h, w = L.T.shape
    ok = free_ground(L) & area
    if avoid is not None:
        ok &= ~avoid
    c0, r0 = start
    if not (0 <= c0 < w and 0 <= r0 < h) or not ok[r0, c0] or L.STREET[r0, c0]:
        return None
    lvl = L.LV[r0, c0]
    best = {}
    q = [(0, c0, r0, -1, None)]
    prev = {}
    while q:
        cost, c, r, d, p = heapq.heappop(q)
        if (c, r, d) in best:
            continue
        best[(c, r, d)] = cost
        prev[(c, r, d)] = p
        if L.STREET[r, c] and L.LV[r, c] == lvl:
            out = [(c, r)]
            k = p
            while k is not None:
                out.append((k[0], k[1]))
                k = prev[k]
            return out[::-1]
        if cost > reach:
            continue
        for nd, (dc, dr) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
            a, b = c + dc, r + dr
            if not (0 <= a < w and 0 <= b < h) or L.LV[b, a] != lvl:
                continue
            if not (ok[b, a] or L.STREET[b, a]):
                continue
            nc = cost + 1 + (turn if d not in (-1, nd) else 0)
            heapq.heappush(q, (nc, a, b, nd, (c, r, d)))
    return None


def lanes(L: Layout, area: np.ndarray, seed: str, spacing: int = 7, paving: str = "",
          turn: int = 3, reach: int = 30, min_len: int = 3) -> list:
    """Narrow lanes into a quarter: seed tiles on a jittered grid about `spacing` apart, each
    joined to the nearest way by the cheapest straight-ish path; dead ends are kept (courtyard
    alleys). Lanes laid earlier serve later seeds, so the net grows like an old town's."""
    h, w = L.T.shape
    js, is_ = np.nonzero(area)
    if js.size == 0:
        return []
    out = []
    seeds = []
    for r in range(int(js.min()), int(js.max()) + 1, spacing):
        for c in range(int(is_.min()), int(is_.max()) + 1, spacing):
            hv = rng.hash64("rome", "lane", seed, c, r)
            cc = c + int(hv % spacing)
            rr = r + int((hv >> 8) % spacing)
            if 0 <= cc < w and 0 <= rr < h and area[rr, cc]:
                seeds.append((rng.hash64("rome", "order", seed, cc, rr), cc, rr))
    for _o, c, r in sorted(seeds):
        path = connect(L, (c, r), area, turn=turn, reach=reach)
        if path is None or len(path) < min_len:
            continue
        if near_other_level(L, path[0], L.LV[path[0][1], path[0][0]]):
            continue
        out.append(L.street(corners(path), width=1, paving=paving))
    return out


def near_other_level(L: Layout, tile, lvl: int, d: int = 2) -> bool:
    """Whether a street of another level passes within `d` tiles: the compiler joins a street
    end to the nearest street within reach whatever its level, so a lane may not stop there."""
    c, r = tile
    h, w = L.T.shape
    sub = (slice(max(r - d, 0), min(r + d + 1, h)), slice(max(c - d, 0), min(c + d + 1, w)))
    return bool((L.STREET[sub] & (L.LV[sub] != lvl)).any())


def drop_bad_spots(L: Layout) -> None:
    """Kit whose door or slot spots (off its own footprint) fall outside the layer, on water, on
    no ground, or on a landmark's closed tiles cannot be used: it goes."""
    water = np.zeros(L.T.shape, dtype=bool)
    for t, name in enumerate(L.terrains):
        if L.cat.is_water(name):
            water |= L.T == t
    for p in L.items:
        d = L.cat.items[p.id]
        if p.removed or d.landmark or d.rise:
            continue
        own = set(p.tiles())
        spots = [(sid, c, r) for sid, lst in p.slots.items() for c, r, _f in lst]
        if p.door:
            spots.append(("door", *p.door))
        for sid, c, r in spots:
            if (c, r) in own:
                continue
            loc = L._local(c, r)
            boat = loc is not None and water[loc] and L.cat.slot_kind(p.id, sid) == "mooring"
            bad = loc is None or L.T[loc] < 0 or (water[loc] and not boat) or L.IMP[loc]
            if not bad and L.OCC[loc] >= 0:
                o = L.items[L.OCC[loc]]
                bad = L.cat.items[o.id].landmark and (c, r) not in L.walk_tiles(o)
            if bad:
                L.remove(p)
                break


def drop_unreached(L: Layout, reach: int = 22) -> None:
    """Kit with any slot spot (off its footprint) that no street reaches within `reach` steps of
    one level over open ground goes (V7 asks it of every spot, `clear_doors` of one)."""
    from collections import deque
    water = np.zeros(L.T.shape, dtype=bool)
    for t, name in enumerate(L.terrains):
        if L.cat.is_water(name):
            water |= L.T == t
    open_ = (L.T >= 0) & ~L.IMP & ~water & (L.OCC < 0)
    for p in L.items:
        if p.removed:
            continue
        d = L.cat.items[p.id]
        tiles = L.walk_tiles(p) if d.landmark else (set(p.tiles()) if d.walkable or d.rise else ())
        for c, r in tiles:
            loc = L._local(c, r)
            if loc is not None:
                open_[loc] = True
    h, w = L.T.shape
    dist = np.full((h, w), 999, dtype=np.int32)
    q = deque()
    for j, i in np.argwhere(L.STREET & open_):
        dist[j, i] = 0
        q.append((j, i))
    while q:
        j, i = q.popleft()
        if dist[j, i] >= reach:
            continue
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = j + dj, i + di
            if 0 <= a < h and 0 <= b < w and open_[a, b] and dist[a, b] > dist[j, i] + 1 \
                    and L.LV[a, b] == L.LV[j, i]:
                dist[a, b] = dist[j, i] + 1
                q.append((a, b))
    for p in L.items:
        d = L.cat.items[p.id]
        if p.removed or d.landmark or d.rise:
            continue
        spots = [(sid, c, r) for sid, lst in p.slots.items() for c, r, _f in lst]
        if p.door:
            spots.append(("door", *p.door))
        for sid, c, r in spots:
            locs = [L._local(*t) for t in use_tiles(L, p, sid, c, r)]
            if not any(loc is not None and dist[loc] <= reach for loc in locs):
                L.remove(p)
                break


def beside_street(L: Layout, area: np.ndarray, items: dict, density: float, seed: str) -> list:
    """Kit that opens on a way (workshops, counters, shrines, fountains): tried on free tiles in
    hash order, turned to face the street beside it, kept only where every slot spot off its own
    footprint is a street tile."""
    h, w = L.T.shape
    names = list(items)
    total = sum(items.values())
    js, is_ = np.nonzero(area & (L.OCC < 0) & ~L.STREET)
    cand = sorted(zip(is_.tolist(), js.tolist()), key=lambda t: rng.hash64("rome", seed, *t))
    out = []
    for c, r in cand:
        hv = rng.hash64("rome", seed, "pick", c, r)
        if (hv % 1000) / 1000 >= density:
            continue
        u = ((hv >> 12) % 1000) / 1000 * total
        item = names[-1]
        for n in names:
            u -= items[n]
            if u < 0:
                item = n
                break
        for dc, dr in ((-1, 0), (0, -1), (1, 0), (0, 1)):
            a, b = c + dc, r + dr
            if not (0 <= a < w and 0 <= b < h and L.STREET[b, a] and L.LV[b, a] == L.LV[r, c]):
                continue
            p = put(L, item, (c, r), face=facing(dc, dr))
            if p is None:
                continue
            own = set(p.tiles())
            spots = [(sc, sr) for lst in p.slots.values() for sc, sr, _f in lst
                     if (sc, sr) not in own]
            if p.door and p.door not in own:
                spots.append(p.door)
            if spots and all(L._local(sc, sr) is not None and L.STREET[L._local(sc, sr)]
                             for sc, sr in spots):
                out.append(p)
                break
            L.remove(p)
    return out


def snap_nodes(L: Layout, nodes: dict) -> None:
    """Each named node on the street tile nearest its spot (a node off the streets would be
    joined by a straight edge that may cross houses)."""
    js, is_ = np.nonzero(L.STREET)
    for nid, (c, r) in nodes.items():
        k = int(np.argmin((is_ - c) ** 2 + (js - r) ** 2))
        L.node(nid, (int(is_[k]), int(js[k])))


def meet_edges(L: Layout, lv: np.ndarray, keep: np.ndarray | None = None, depth: int = 6,
               sides: str = "nesw") -> None:
    """Near the edges, levels bend toward the world outside (one level per tile) where a seam of
    cliffs would face the south-west camera: ground outside the north and east edges higher than
    ours, and our ground on the west and south edges higher than the ground outside. Water
    outside is left alone; `keep` marks tiles that must keep their level (portal roads)."""
    h, w = lv.shape
    for i in range(max(w, h)):
        for side, (c, r), (oc, orr), (dc, dr), raise_ in (
                ("n", (i, 0), (i, -1), (0, 1), True), ("e", (w - 1, i), (w, i), (-1, 0), True),
                ("s", (i, h - 1), (i, h), (0, -1), False), ("w", (0, i), (-1, i), (1, 0), False)):
            if side not in sides or not (0 <= c < w and 0 <= r < h):
                continue
            t = L.below_terrain(oc, orr)
            if t is None or L.cat.is_water(t):
                continue
            out = L.below_level(oc, orr)
            for k in range(depth):
                x, y = c + dc * k, r + dr * k
                if not (0 <= x < w and 0 <= y < h) or (keep is not None and keep[y, x]):
                    continue
                if raise_:
                    lv[y, x] = max(lv[y, x], out - k)
                else:
                    lv[y, x] = min(lv[y, x], out + k)


def write_levels(L: Layout, lv: np.ndarray, face_of) -> None:
    """Write a level array to the layer; `face_of(k, mask)` -> [(face, submask)] picks the edge
    material of the raised tiles at level k."""
    for k in range(int(lv.min()), int(lv.max()) + 1):
        if k == 0:
            continue
        m = lv == k
        if not m.any():
            continue
        if k < 0:
            L.level(Mask(0, 0, m), k)
            continue
        for face, sub in face_of(k, m):
            if sub.any():
                L.level(Mask(0, 0, sub), k, face=face)


def grove(L: Layout, area: np.ndarray, seed: str, item: str, step=(3, 2), soil: str | None = None,
          variants: int = 1) -> None:
    """Trees or vines planted in loose rows: rows every `step[1]`, plants every `step[0]`,
    staggered, nudged a tile by hash, one in seven missing; `soil` painted under the rows."""
    m = area & (L.OCC < 0) & ~L.STREET
    if soil:
        L.paint(Mask(0, 0, m), soil)
    js, is_ = np.nonzero(m)
    if js.size == 0:
        return
    w = m.shape[1]
    for r in range(int(js.min()), int(js.max()) + 1, step[1]):
        off = (r // step[1]) % 2 * (step[0] // 2)
        for c in range(int(is_.min()) + off, int(is_.max()) + 1, step[0]):
            hv = rng.hash64("rome", seed, c, r)
            if hv % 7 == 0:
                continue
            at = (c + int(hv >> 8) % 3 - 1, r) if step[0] > 1 else (c, r)
            if 0 <= at[0] < w and m[r, at[0]]:
                put(L, item, at, variant=int(hv >> 16) % variants)
