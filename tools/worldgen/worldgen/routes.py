"""Routes and sea lanes of the base layer (world-tech §3.8 step 4; docs/design/sets/world.md §9.4).

A route is laid in two passes:
 1. ways: an axis-parallel path between its points (A* over slope, water and the plan's
    obstacles, with a turn penalty and a pull toward the straight line, so roads run in long
    straight reaches with jogs, as they read in isometric view); a profile along it that
    changes level only on ramps (a level per ramp of 4 tiles plus a landing), cutting through
    hills and banking over hollows; paving; a ford, bridge or pontoon on every water tile;
 2. kit: markers, stations, watering stops, tombs, graves, terrace walls, watchtowers and
    beacons at the style's spacing, farms every so often with a track to the road, harbours at
    route and lane ends.
The graph gets a node at every route point (routes sharing a point tile meet there), station
and farm junction, an edge per stretch between them whose `via` are the path's corners, and a
track edge to every farm yard. Lanes are A* over sea or river tiles with their ports.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from plan import world_plan as P

from . import rng
from .base import CC, RR, SEED, World, distance_to, flood, noise, rect_mask
from .coords import COLS, ROWS, FACING_NAMES, FACINGS
from .dsl import Placed
from .graph import Edge, Graph, Lane, Node, Port

DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))          # plan steps (dc, dr): east, south, west, north
FACE_OF = {(-1, 0): "west", (0, -1): "north", (1, 0): "east", (0, 1): "south"}
REGIONS_DIR = Path(__file__).resolve().parent.parent / "regions"
RAMP_RUN = 4    # tiles of world.ramp
SRC = "plan/world_plan.py"


def grid(c: int, r: int) -> tuple[int, int]:
    return (r, COLS - 1 - c)


@dataclass
class Way:
    """One laid route: its path tiles (plan), road level per tile, cross-section tiles."""

    id: str
    style: dict
    width: int
    kind: str
    path: list = field(default_factory=list)
    z: list = field(default_factory=list)
    nodes: dict = field(default_factory=dict)     # path index -> (node id, kind)
    skip: set = field(default_factory=set)        # path indices inside a town (no kit)
    near_town: list = field(default_factory=list)  # tiles to the nearest town along the path
    chain: list = field(default_factory=list)      # distance along the road's line per tile
    spec: dict = field(default_factory=dict)


# --- resolving points -----------------------------------------------------------------------

def resolve(point):
    """(tile, portal id or None, world level or None, town layer or None)."""
    if isinstance(point, str):
        layer, pid = point.split(":", 1)
        _layers, tile, level = P.PORTALS[pid]
        return tuple(tile), pid, level, layer
    return tuple(point), None, None, None


def has_layout(layer: str) -> bool:
    return (REGIONS_DIR / layer / "layout.py").exists()


# --- cost grid and A* -----------------------------------------------------------------------

def cost_grid(W: World) -> np.ndarray:
    lv = W.L.LV.astype(np.int16)
    dl = np.zeros(lv.shape)
    for dc, dr in DIRS:
        sh = np.full_like(lv, 0)
        h, w = lv.shape
        sh[max(dr, 0):h + min(dr, 0), max(dc, 0):w + min(dc, 0)] = \
            lv[max(-dr, 0):h + min(-dr, 0), max(-dc, 0):w + min(-dc, 0)]
        dl = np.maximum(dl, np.abs(lv - sh))
    # A little jitter keeps long reaches from ruling straight across the plain; more made the
    # roads zigzag on flat ground, where only the terrain should bend them.
    cost = 1.0 + 0.12 * (noise(5.0, "roadjitter") + 1) + 2.2 * dl + 0.15 * (lv >= 8) * (lv - 7)
    cost = np.where(W.river, cost + 12.0, cost)
    cost = np.where(W.marsh, cost + 2.0, cost)
    cost = np.where(W.land & ~W.L.IMP, cost, np.inf)
    cost = np.where(W.reserved | (W.anchors.dist == 0), np.inf, cost)
    return cost


def astar4(cost: np.ndarray, a, b, allow: np.ndarray | None = None, turn: float = 6.0,
           pull: float = 0.15, margin: int = 40) -> list[tuple[int, int]]:
    """Cheapest 4-connected path from tile a to b with a penalty per turn and per tile of
    distance from the straight line a-b. `allow` opens tiles the cost grid closes (a town's own
    rect for a road through it); the end tiles are always open."""
    c0 = max(min(a[0], b[0]) - margin, 0)
    c1 = min(max(a[0], b[0]) + margin, COLS - 1)
    r0 = max(min(a[1], b[1]) - margin, 0)
    r1 = min(max(a[1], b[1]) + margin, ROWS - 1)
    sub = cost[r0:r1 + 1, c0:c1 + 1].copy()
    if allow is not None:
        al = allow[r0:r1 + 1, c0:c1 + 1]
        sub = np.where(al & ~np.isfinite(sub), 2.0, sub)
    h, w = sub.shape
    ax, ay, bx, by = a[0] - c0, a[1] - r0, b[0] - c0, b[1] - r0
    sub[ay, ax] = min(sub[ay, ax], 2.0) if np.isfinite(sub[ay, ax]) else 2.0
    sub[by, bx] = min(sub[by, bx], 2.0) if np.isfinite(sub[by, bx]) else 2.0
    # Pull toward the line a-b.
    cc, rr = np.meshgrid(np.arange(w), np.arange(h))
    dx, dy = bx - ax, by - ay
    ll = math.hypot(dx, dy) or 1.0
    dev = np.abs(dy * (cc - ax) - dx * (rr - ay)) / ll
    sub = sub + pull * dev
    INF = math.inf
    start = (ay, ax, 4)
    dist = {start: 0.0}
    prev = {}
    heap = [(0.0, start)]
    goal = None
    while heap:
        f, cur = heapq.heappop(heap)
        y, x, d = cur
        d0 = dist[cur]
        if f - (abs(y - by) + abs(x - bx)) > d0 + 1e-9:
            continue
        if (y, x) == (by, bx):
            goal = cur
            break
        for nd, (sx, sy) in enumerate(DIRS):
            ny, nx = y + sy, x + sx
            if not (0 <= ny < h and 0 <= nx < w):
                continue
            k = sub[ny, nx]
            if not np.isfinite(k):
                continue
            ncost = d0 + k + (turn if d != 4 and d != nd else 0.0)
            key = (ny, nx, nd)
            if ncost < dist.get(key, INF):
                dist[key] = ncost
                prev[key] = cur
                heapq.heappush(heap, (ncost + abs(ny - by) + abs(nx - bx), key))
    if goal is None:
        return []
    out = [goal]
    while out[-1] != start:
        out.append(prev[out[-1]])
    out.reverse()
    return [(x + c0, y + r0) for y, x, _ in out]


# --- profile --------------------------------------------------------------------------------

def steps(path) -> list[tuple[int, int]]:
    return [(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]


def straight(st, i: int, n: int) -> bool:
    """Steps i .. i+n-1 all the same direction."""
    return i >= 0 and i + n <= len(st) and all(s == st[i] for s in st[i:i + n])


def profile(path, lv, water, z0, z1, keep: set, landing: int = 0) -> tuple[list, list, int]:
    """Road levels along the path, changing only on ramps: returns (z, ramps, failures), ramps
    as (first ramp index, +1 up / -1 down in travel direction). A ramp occupies 4 straight path
    tiles at the lower level, with the tile before and after it in line (foot and head)."""
    n = len(path)
    st = steps(path)
    h = np.array([lv[r, c] for c, r in path], dtype=np.float64)
    wet = np.array([water[r, c] for c, r in path])
    for i in range(n):
        if wet[i]:
            j = i
            while j < n and wet[j]:
                j += 1
            h[i] = h[i - 1] if i > 0 else (h[j] if j < n else h[i])
    tgt = np.array([np.median(h[max(0, i - 6):i + 7]) for i in range(n)])
    z = [0] * n
    cur = int(z0)
    end = int(z1) if z1 is not None else int(round(tgt[-1]))
    z[0] = cur
    ramps = []
    fails = 0
    i = 0
    run = RAMP_RUN + 1
    while i < n - 1:
        remaining = n - 1 - i
        need = end - cur
        want = 0
        if need and abs(need) * (run + 1) * 2.5 >= remaining - run:
            want = 1 if need > 0 else -1
        else:
            ahead = tgt[i + 2:i + 14]
            if ahead.size:
                m = float(ahead.mean())
                if m >= cur + 0.9:
                    want = 1
                elif m <= cur - 0.9:
                    want = -1
                slack = 2.5 if z1 is not None else 1.0
                if want and abs(end - (cur + want)) * (run + 1) * slack > remaining - run - 2:
                    want = 0
        ok = want and i + run < n and straight(st, i, run) and \
            not any(wet[i:i + run + 1]) and not any(k in keep for k in range(i + 1, i + run))
        if ok:
            low = cur if want > 0 else cur - 1
            for k in range(i + 1, i + run):
                z[k] = low
            cur += want
            z[i + run] = cur
            ramps.append((i + 1, want))
            i += run
            if landing and i < n - 1:
                z[i + 1] = cur   # a landing before the next flight (a wide road's corners)
                i += 1
            continue
        z[i + 1] = cur
        i += 1
    if z1 is not None and z[-1] != end:
        fails += abs(z[-1] - end)
    return z, ramps, fails


# --- laying a way ---------------------------------------------------------------------------

def offset(path, i: int, blocked: np.ndarray | None = None) -> list[tuple[int, int]]:
    """Where the second lane of a wide road lies at path index i: south of an east-west reach,
    east of a north-south one (both at a corner), or the other side where that is blocked."""
    c, r = path[i]
    dirs = set()
    if i + 1 < len(path):
        dirs.add((path[i + 1][0] - c, path[i + 1][1] - r))
    if i > 0:
        dirs.add((c - path[i - 1][0], r - path[i - 1][1]))
    out = []
    for dc, dr in sorted(dirs):
        o = (0, 1) if dc else (1, 0)
        x, y = c + o[0], r + o[1]
        if blocked is not None and 0 <= x < COLS and 0 <= y < ROWS and blocked[y, x]:
            o = (-o[0], -o[1])
        out.append(o)
    return out


def section(path, i: int, width: int, blocked: np.ndarray | None = None) -> list[tuple[int, int]]:
    """Tiles of the road at path index i (see `offset` for the second lane of width 2)."""
    c, r = path[i]
    out = [(c, r)]
    if width >= 2:
        offs = offset(path, i, blocked)
        out += [(c + ox, r + oy) for ox, oy in offs]
        if len(offs) > 1:
            out.append((c + offs[0][0] + offs[1][0], r + offs[0][1] + offs[1][1]))
    return [(x, y) for x, y in dict.fromkeys(out) if 0 <= x < COLS and 0 <= y < ROWS]


def town_of(layer: str | None) -> tuple | None:
    if layer and layer in P.REGIONS:
        return P.REGIONS[layer][3]
    return None


def lay_ways(W: World, g: Graph) -> list[Way]:
    L = W.L
    cost = cost_grid(W)
    ways = []
    water = W.river | ~W.land
    taken: dict[tuple[int, int], tuple[str, int]] = {}   # junction tiles of earlier routes
    W.road = np.zeros((ROWS, COLS), dtype=bool)
    for rid, spec in P.ROUTES.items():
        style = P.ROAD_STYLES[spec["style"]]
        way = Way(rid, style, spec["width"], spec["kind"], spec=spec)
        pts = [resolve(p) for p in spec["points"]]
        path: list = []
        marks: list[int] = []
        levels: dict[int, int] = {}
        for k, ((a, pa, la, ta), (b, pb, lb, tb)) in enumerate(zip(pts, pts[1:])):
            through = ta is not None and ta == tb
            if through and has_layout(ta):
                # A built town carries the road: the route resumes on its far side.
                if path:
                    way_split(W, g, way, path, marks, levels, taken)
                    ways.append(way)
                way = Way(rid, style, spec["width"], spec["kind"], spec=spec)
                path, marks, levels = [], [], {}
                continue
            allow = rect_mask(town_of(ta)) if through else None
            # A route never doubles back over its own way.
            own = np.zeros((ROWS, COLS), dtype=bool)
            for c_, r_ in path[:-1]:
                own[r_, c_] = True
            seg = astar4(np.where(own, np.inf, cost), a, b, allow)
            if not seg:
                W.stats.setdefault("route_failures", []).append(f"{rid}: {a} -> {b}")
                continue
            if through:
                first = len(path) - (1 if path else 0)
            if not path:
                path = list(seg)
                marks.append(0)
            else:
                path += seg[1:]
            marks.append(len(path) - 1)
            if la is not None:
                levels[len(path) - len(seg)] = la
            if lb is not None:
                levels[len(path) - 1] = lb
            if through:
                way.skip |= set(range(first, len(path)))
        if path:
            way_split(W, g, way, path, marks, levels, taken)
            ways.append(way)
        # Later routes leave a road where they meet it instead of running along it.
        cost = np.where(W.road, cost + 25.0, cost)
    return ways


def way_split(W, g, way: Way, path, marks, levels, taken) -> None:
    """Profile, grade, pave and node one continuous way."""
    L = W.L
    if getattr(W, "blocked", None) is None:
        W.blocked = (W.anchors.dist == 0) | ~W.land
        for kind, _s, _t, rect, _b in P.REGIONS.values():
            if kind in ("city", "home"):
                W.blocked |= rect_mask(rect)
    way.path = path
    water = W.river | ~W.land
    keep = set(marks) | {i for i, t in enumerate(path) if t in taken}
    fixed = dict(levels)
    for i in (0, len(path) - 1):
        if path[i] in taken:
            fixed[i] = taken[path[i]][1]
    fixed.setdefault(0, int(L.LV[path[0][1], path[0][0]]))
    # Between two fixed levels (portals, junctions) the profile is laid piece by piece, so a
    # road meets every portal at the plan's level.
    cuts = sorted(fixed) + ([len(path) - 1] if len(path) - 1 not in fixed else [])
    z, ramps, fails = [], [], 0
    for a, b in zip(cuts, cuts[1:]):
        sub = path[a:b + 1]
        zz, rr, ff = profile(sub, L.LV, water, fixed[a], fixed.get(b),
                             {k - a for k in keep if a <= k <= b},
                             landing=1 if way.width >= 2 else 0)
        z += zz if not z else zz[1:]
        ramps += [(i + a, up) for i, up in rr]
        fails += ff
    if len(path) == 1:
        z = [fixed[0]]
    way.z = z
    if fails:
        W.stats.setdefault("profile_failures", []).append(f"{way.id}: {fails} level(s) short")
    style = way.style
    pave = W.tidx(style["paving"])
    for i in range(len(path)):
        for c, r in section(path, i, way.width, W.blocked):
            if water[r, c]:
                continue
            L.LV[r, c] = z[i]
            L.T[r, c] = pave
            L.IMP[r, c] = False
            L.STREET[r, c] = True
            W.road[r, c] = True
    # Shoulders: the ground within two tiles eases toward the road (cuttings and embankments
    # in steps of at most two levels a tile).
    road = np.zeros((ROWS, COLS), dtype=bool)
    zmap = np.zeros((ROWS, COLS), dtype=np.int16)
    for i, (c, r) in enumerate(path):
        for x, y in section(path, i, way.width, W.blocked):
            road[y, x] = True
            zmap[y, x] = z[i]
    soft = ~W.reserved & (W.anchors.dist > 0) & W.land & ~W.river
    for d in (1, 2):
        grown = distance_to(road, d + 1) == d
        js, is_ = np.nonzero(grown & soft & ~W.road)
        for j, i_ in zip(js.tolist(), is_.tolist()):
            near = zmap[max(j - d, 0):j + d + 1, max(i_ - d, 0):i_ + d + 1]
            rmask = road[max(j - d, 0):j + d + 1, max(i_ - d, 0):i_ + d + 1]
            if not rmask.any():
                continue
            zz = int(near[rmask].max())
            L.LV[j, i_] = int(np.clip(L.LV[j, i_], zz - 2 * d, zz + 2 * d))
    # Ramps (two side by side on a wide road).
    for i0, up in ramps:
        dc, dr = path[i0 + 1][0] - path[i0][0], path[i0 + 1][1] - path[i0][1]
        foot = (-dc, -dr) if up > 0 else (dc, dr)
        face = FACE_OF[foot]
        offs = [(0, 0)] + ([offset(path, i0 + 1, W.blocked)[0]] if way.width >= 2 else [])
        low = way.z[i0]
        for off in offs:
            line = [(path[k][0] + off[0], path[k][1] + off[1])
                    for k in range(i0 - 1, i0 + RAMP_RUN + 1)]
            if any(not (0 <= c < COLS and 0 <= r < ROWS) or water[r, c] for c, r in line):
                continue   # that lane is a deck over water here: no ramp on it
            tiles = line[1:-1]
            # The flight, its foot and its head at their levels (a corner's other lane may have
            # been graded by the neighbouring reach).
            for c, r in tiles:
                L.LV[r, c] = low
            lo_end, hi_end = (line[0], line[-1]) if up > 0 else (line[-1], line[0])
            L.LV[lo_end[1], lo_end[0]] = low
            L.LV[hi_end[1], hi_end[0]] = low + 1
            cs = [t[0] for t in tiles]
            rs = [t[1] for t in tiles]
            rect = (min(cs), min(rs), max(cs), max(rs))
            p = L.stair("world.ramp", rect=rect, face=face)
            if p is not None:
                p.src = SRC
            if p is None:
                W.stats.setdefault("ramp_failures", []).append(f"{way.id} at {rect}")
    W.stats.setdefault("ramps", 0)
    W.stats["ramps"] += len(ramps) * (1 if way.width < 2 else 2)
    # Crossings.
    river_of = W.stats.get("_river_of", {})
    for i in range(len(path)):
        for c, r in section(path, i, way.width, W.blocked):
            if not water[r, c] or not W.land[r, c] and not W.river[r, c]:
                continue
            if L.OCC[r, c] >= 0:
                continue
            item = crossing_item(W, way, c, r, river_of)
            if item:
                p = Placed(len(L.items), item, c, r, 1, 1, 0, None, SRC)
                L.items.append(p)
                L.OCC[r, c] = p.index
                W.stats.setdefault("crossings", {}).setdefault(item, 0)
                W.stats["crossings"][item] += 1
    # Nodes at the route's points and where it meets earlier routes.
    for i in marks:
        t = path[i]
        pid = next((pp for pp, v in P.PORTALS.items() if tuple(v[1]) == t), None)
        if t in taken:
            way.nodes[i] = (taken[t][0], None)
        elif pid:
            way.nodes[i] = (pid, "portal")
        else:
            way.nodes[i] = (f"{way.id}_{t[0]}_{t[1]}", None)
        taken.setdefault(t, (way.nodes[i][0], z[i]))
    for i, t in enumerate(path):
        if t in taken and i not in way.nodes:
            way.nodes[i] = (taken[t][0], None)
    way.near_town = near_town_distance(path)
    way.chain = chainage(path)


def chainage(path, tol: float = 2.5) -> list[float]:
    """Distance travelled along the road's line at each path tile: the axis-parallel path
    simplified to the line a traveller follows (jogs and staircases cut), so a zigzag across a
    terrace does not count as extra road. Kit spaced by it keeps a steady rhythm."""
    if len(path) < 2:
        return [0.0] * len(path)
    keep = simplify(list(path), tol)
    index = {t: i for i, t in enumerate(path)}
    knots = sorted({index[t] for t in keep})
    out = [0.0] * len(path)
    done = 0.0
    for a, b in zip(knots, knots[1:]):
        seg = math.hypot(path[b][0] - path[a][0], path[b][1] - path[a][1])
        for i in range(a, b + 1):
            out[i] = done + seg * (i - a) / max(b - a, 1)
        done += seg
    return out


def chain_points(way: "Way", every: float, offset: float, ok=None) -> list[int]:
    """Path indices where the chainage first passes offset, offset + every, ... (each the
    first allowed index at or after its mark; ends and towns skipped by `ok`)."""
    out = []
    mark = offset
    n = len(way.path)
    for i in range(3, n - 2):
        if way.chain[i] >= mark:
            if ok is None or ok(i):
                out.append(i)
                mark = way.chain[i] + every
            elif way.chain[i] >= mark + every / 2:
                mark += every
    return out


def crossing_item(W: World, way: Way, c: int, r: int, river_of: dict) -> str | None:
    rid = river_of.get((c, r))
    if rid == "tigris":
        return "world.pontoon"
    canal = rid is None
    narrow = canal or P.RIVERS.get(rid, {}).get("width", 1) <= 1 or way.kind == "track"
    if narrow or not way.style.get("bridge"):
        return way.style.get("ford", "world.ford")
    return way.style["bridge"]


def near_town_distance(path) -> list[int]:
    """Tiles along the path to the nearest town or city rect (by path distance)."""
    rects = [v[3] for v in P.REGIONS.values() if v[0] in ("town", "city")]
    inside = [any(r0 <= r <= r1 and c0 <= c <= c1 for c0, r0, c1, r1 in rects) or
              any(max(c0 - c, 0, c - c1) + max(r0 - r, 0, r - r1) <= 1
                  for c0, r0, c1, r1 in rects) for c, r in path]
    n = len(path)
    d = [10 ** 6] * n
    last = -10 ** 6
    for i in range(n):
        if inside[i]:
            last = i
        d[i] = i - last
    last = 10 ** 6
    for i in range(n - 1, -1, -1):
        if inside[i]:
            last = i
        d[i] = min(d[i], last - i)
    return d


# --- kit ------------------------------------------------------------------------------------

def free_tile(W: World, c: int, r: int) -> bool:
    L = W.L
    return (0 <= c < COLS and 0 <= r < ROWS and W.land[r, c] and not W.river[r, c] and
            not W.reserved[r, c] and W.anchors.dist[r, c] > 1 and L.OCC[r, c] < 0 and
            not L.STREET[r, c] and not L.IMP[r, c] and not W.keep[r, c])


def access_tiles(p: Placed) -> list[list[tuple[int, int]]] | None:
    """For each door or slot spot of a placed item, the tiles a walker may use it from: the spot
    itself outside the footprint, or the tiles beside it for a spot on the footprint's edge. A
    spot deep inside the footprint is the art's geometry to open (V7 warns) and is skipped."""
    spots = [(c, r) for lst in p.slots.values() for c, r, _f in lst]
    if p.door and not p.slots:
        spots.append(p.door)
    out = []
    for c, r in spots:
        if p.c <= c < p.c + p.pw and p.r <= r < p.r + p.ph:
            near = [(c + a, r + b) for a, b in DIRS
                    if not (p.c <= c + a < p.c + p.pw and p.r <= r + b < p.r + p.ph)]
            if near:
                out.append(near)
        else:
            out.append([(c, r)])
    return out


def put(W: World, item: str, c: int, r: int, face: str = "west", variant: int = 0,
        level: int | None = None) -> Placed | None:
    """Place a base item with its north-west tile at (c, r) if its footprint is free land and
    every door and slot spot can be reached from a road tile or free ground at its level; the
    footprint and those access tiles are levelled to `level` (or its first tile's level)."""
    L, cat = W.L, W.cat
    d = cat.items.get(item)
    if d is None:
        W.stats.setdefault("unknown_items", set()).add(item)
        return None
    k = L._rot(item, face, variant)
    pw, ph = L._plan_size(item, k)
    tiles = [(c + x, r + y) for y in range(ph) for x in range(pw)]
    if not all(free_tile(W, x, y) for x, y in tiles):
        return None
    lv = level if level is not None else int(L.LV[r, c])
    p = L._new_placed(item, c, r, k, None, SRC, face if d.layout == "rotate" else None)
    level_these = []
    for options in access_tiles(p):
        ok = None
        for x, y in options:
            if not (0 <= x < COLS and 0 <= y < ROWS) or (x, y) in tiles:
                continue
            if L.STREET[y, x] and L.LV[y, x] == lv and L.OCC[y, x] < 0:
                ok = (x, y, False)
                break
            if free_tile(W, x, y) and any(
                    0 <= x + a < COLS and 0 <= y + b < ROWS and L.STREET[y + b, x + a]
                    and L.LV[y + b, x + a] == lv for a, b in DIRS):
                ok = ok or (x, y, True)   # free ground beside a road tile at this level
        if ok is None:
            return None
        if ok[2]:
            level_these.append(ok[:2])
    for x, y in tiles + level_these:
        L.LV[y, x] = lv
    for x, y in level_these:
        W.keep[y, x] = True   # a door step or work spot stays free
    L.items.append(p)
    L._occupy(p)
    return p


def side_tiles(way: Way, i: int, side: int, gap: int = 1):
    """(c, r, face toward the road, along-direction) of the tile `gap` beyond the road's edge
    at path index i, on side +1 (right of travel) or -1 (left)."""
    path = way.path
    j = min(i, len(path) - 2)
    dc, dr = path[j + 1][0] - path[j][0], path[j + 1][1] - path[j][1]
    c, r = path[i]
    # Right of travel in plan (c east, r south): (dc, dr) -> (-dr, dc).
    nx, ny = (-dr, dc) if side > 0 else (dr, -dc)
    extra = (way.width - 1) if (nx > 0 or ny > 0) else 0
    x, y = c + nx * (gap + extra), r + ny * (gap + extra)
    face = FACE_OF[(-nx, -ny)]
    return x, y, face, (dc, dr), (nx, ny)


def place_beside(W: World, way: Way, i: int, side: int, item: str, gap: int = 1,
                 variant: int = 0) -> Placed | None:
    """An item standing beside the road at path index i, its front toward the road (or another
    facing when that one leaves a slot spot out of reach)."""
    L = W.L
    x, y, face, (dc, dr), (nx, ny) = side_tiles(way, i, side, gap)
    d = W.cat.items.get(item)
    if d is None:
        return None
    faces = [face] + [f for f in ("west", "north", "east", "south") if f != face] \
        if d.layout == "rotate" else [face]
    for f in faces:
        k = L._rot(item, f, variant)
        pw, ph = L._plan_size(item, k)
        # The footprint's road-facing edge on (x, y), centred along the road.
        if nx:
            c0 = x if nx > 0 else x - pw + 1
            r0 = y - (ph - 1) // 2
        else:
            r0 = y if ny > 0 else y - ph + 1
            c0 = x - (pw - 1) // 2
        p = put(W, item, c0, r0, f, variant, level=way.z[i])
        if p:
            return p
    return None


def kit(W: World, g: Graph, ways: list[Way]) -> None:
    for way in ways:
        st = way.style
        n = len(way.path)
        ok = [i not in way.skip and way.near_town[i] >= 3 for i in range(n)]
        occupied_at = set()

        def spaced(every, offset=0, near=None):
            """Path indices every `every` tiles of chainage (offset), skipping the ends and
            towns."""
            return chain_points(way, every, offset,
                                lambda i: ok[i] and (near is None or near(i)))

        side = 1
        # Stations (Persian relay stations, Roman mutationes, Greek shrines).
        if st.get("station"):
            item, every = st["station"]
            st_spots = W.stats.setdefault("_station_spots", [])
            for i in spaced(every, every // 2):
                for di in (0, 2, -2, 4, -4, 6, -6):
                    j = i + di
                    if not (0 < j < n - 1) or not ok[j] or j in occupied_at:
                        continue
                    jc, jr = way.path[j]
                    if any(abs(jc - a) + abs(jr - b) < every * 0.7 for a, b in st_spots):
                        continue   # the road doubles back: keep stations apart on the ground too
                    p = place_beside(W, way, j, side, item) or place_beside(W, way, j, -side, item)
                    if p:
                        st_spots.append((jc, jr))
                        occupied_at.add(j)
                        kind = "station" if item in ("world.royal_station", "rome.mutatio") \
                            else None
                        if kind:
                            jc, jr = way.path[j]
                            way.nodes.setdefault(j, (f"{way.id}_station_{jc}_{jr}", "station"))
                            stations(W).append((way.id, j, p))
                        W.stats.setdefault("stations", {}).setdefault(item, 0)
                        W.stats["stations"][item] += 1
                        side = -side
                        break
        # Watering stops between stations.
        if st.get("stop"):
            items, every = st["stop"]
            for i in spaced(every * 2, every // 2 + every):
                for di in (0, 1, -1, 2, -2):
                    j = i + di
                    if not (0 < j < n - 2) or not ok[j]:
                        continue
                    p1 = place_beside(W, way, j, side, items[0])
                    if p1:
                        place_beside(W, way, j + 1, side, items[1])
                        W.stats["stops"] = W.stats.get("stops", 0) + 1
                        side = -side
                        break
        # Markers: milestones or herms, alternating sides.
        if st.get("marker"):
            item, every = st["marker"]
            for k, i in enumerate(spaced(every, every // 3)):
                s = 1 if k % 2 == 0 else -1
                if place_beside(W, way, i, s, item) or place_beside(W, way, i, -s, item):
                    W.stats.setdefault("markers", {}).setdefault(item, 0)
                    W.stats["markers"][item] += 1
        # Roman tombs: thick near towns, sparse elsewhere, pine and cypress beside them.
        if st.get("tombs"):
            items, near_every, far_every, near_within = st["tombs"]
            i = 4
            k = 0
            mark = 0.0
            while i < n - 3:
                if way.chain[i] < mark:
                    i += 1
                    continue
                if i not in way.skip and way.near_town[i] >= 2:
                    item = items[k % len(items)]
                    s = 1 if k % 2 == 0 else -1
                    p = place_beside(W, way, i, s, item)
                    if p:
                        W.stats["tombs"] = W.stats.get("tombs", 0) + 1
                        trees = st.get("tomb_trees", [])
                        for t, di in zip(trees, (-2, 2)):
                            j = min(max(i + di, 0), n - 1)
                            place_beside(W, way, j, s, t, variant=k)
                    k += 1
                mark = way.chain[i] + (near_every if way.near_town[i] <= near_within
                                       else far_every)
                i += 1
        # Greek graves in the last tiles before a town.
        if st.get("graves"):
            items, within = st["graves"]
            for i in range(2, n - 2, 2):
                if i in way.skip or not (2 <= way.near_town[i] <= within):
                    continue
                item = items[0] if (i // 2) % 4 else items[-1]
                if place_beside(W, way, i, 1 if (i // 2) % 2 else -1, item):
                    W.stats["graves"] = W.stats.get("graves", 0) + 1
        # Terrace walls where a Greek road runs along a slope.
        if st.get("slope_wall"):
            for i in range(2, n - 2):
                if not ok[i]:
                    continue
                for s in (1, -1):
                    x, y, *_ = side_tiles(way, i, s)
                    if free_tile(W, x, y) and W.L.LV[y, x] < way.z[i] and \
                            put(W, st["slope_wall"], x, y, level=int(W.L.LV[y, x])):
                        W.stats["terrace_walls"] = W.stats.get("terrace_walls", 0) + 1
        # Persian watchtowers at passes and river gates, beacons on heights.
        if st.get("watch"):
            watch_points(W, way)
        if st.get("beacon"):
            item, every = st["beacon"]
            for i in spaced(every, every // 2):
                beacon_near(W, way, i, item)
        # Cypress pairs (the Pasargadae road).
        if way.spec.get("rows"):
            item, every = way.spec["rows"]
            for i in spaced(every, 2):
                for s in (1, -1):
                    place_beside(W, way, i, s, item, gap=1, variant=i)
        # Farms every so often.
        farms(W, g, way)
        if way.spec.get("end"):
            end_place(W, g, way, way.spec["end"])


def stations(W: World) -> list:
    return W.stats.setdefault("_stations", [])


def watch_points(W: World, way: Way) -> None:
    """A watchtower where the road enters a pass or reaches a crossing, at most one per 30."""
    passes = [(pc, pr, rad) for b in P.BANDS.values() for (pc, pr), rad, _s in b.get("passes", [])]
    last = -99
    for i, (c, r) in enumerate(way.path):
        if i in way.skip or i - last < 30 or way.near_town[i] < 4:
            continue
        at_pass = any(math.hypot(c - pc, r - pr) < rad * 1.3 for pc, pr, rad in passes)
        nxt = way.path[min(i + 3, len(way.path) - 1)]
        at_river = W.river[nxt[1], nxt[0]] and not W.river[r, c]
        if not (at_pass or at_river):
            continue
        for s in (1, -1):
            if place_beside(W, way, i, s, "world.watchtower", gap=2):
                W.stats["watchtowers"] = W.stats.get("watchtowers", 0) + 1
                last = i
                break


def beacon_near(W: World, way: Way, i: int, item: str) -> None:
    c, r = way.path[i]
    best = None
    for dr in range(-6, 7):
        for dc in range(-6, 7):
            x, y = c + dc, r + dr
            if abs(dc) + abs(dr) < 3 or not free_tile(W, x, y):
                continue
            if any(W.L.STREET[y + a, x + b] for a in (-1, 0, 1) for b in (-1, 0, 1)
                   if 0 <= y + a < ROWS and 0 <= x + b < COLS):
                continue
            key = (int(W.L.LV[y, x]), -abs(dc) - abs(dr))
            if best is None or key > best[0]:
                best = (key, x, y)
    if best and put(W, item, best[1], best[2]):
        W.stats["beacons"] = W.stats.get("beacons", 0) + 1


# --- farms, harbours, charcoal --------------------------------------------------------------

def family_at(W: World, c: int, r: int) -> str | None:
    return W.biome(int(W.stretch[r, c])).get("hamlet")


def farms(W: World, g: Graph, way: Way) -> None:
    """Farms along the road: one by the road every HAMLET_EVERY tiles of chainage
    (HAMLET_NEAR_EVERY within HAMLET_NEAR of a town), and back-country farms between them up a
    longer track, twice as far apart; each at the first place past its mark where it fits."""
    n = len(way.path)
    for k, (start, lengths, far, near_every) in enumerate((
            (P.HAMLET_EVERY / 2, None, P.HAMLET_EVERY, P.HAMLET_NEAR_EVERY),
            (P.HAMLET_EVERY, (12, 15, 9), 2 * P.HAMLET_EVERY, P.HAMLET_EVERY))):
        side = (1 if rng.hash64(SEED, "farmside", way.id) % 2 else -1) * (-1 if k else 1)
        mark = start
        i = 3
        while i < n - 6:
            if way.chain[i] < mark or i in way.skip or way.near_town[i] < 8:
                i += 1
                continue
            c, r = way.path[i]
            fam = family_at(W, c, r)
            if fam and hamlet(W, g, way, i, side, fam, lengths):
                side = -side
                near = way.near_town[i] <= P.HAMLET_NEAR
                mark = way.chain[i] + (near_every if near else far)
            i += 2


# Where the farm's pieces stand round its yard: (dc, dr, facing toward the yard), for the full
# yard (11 x 11 of level ground) and the small one (7 x 7) of a farm on a narrow bench.
YARD_SPOTS = {5: [(0, -3, "south"), (0, 3, "north"), (-3, 0, "east"), (3, 0, "west"),
                  (-3, -3, "east"), (3, 3, "west"), (3, -3, "west"), (-3, 3, "east")],
              3: [(0, -2, "south"), (0, 2, "north"), (-2, 0, "east"), (2, 0, "west")]}


def hamlet(W: World, g: Graph, way: Way, i: int, side: int, fam: str,
           lengths: tuple | None = None) -> bool:
    """A yard off the road with farm kit around it, a track (of the first of `lengths` that
    fits) to the road and its crop beyond."""
    L = W.L
    st = rng.stream(SEED, "hamlet", way.id, i)
    lengths = lengths or (st.randint(5, 8), 4, 10, 13)
    for radius, (lo, hi), s, ln in [(rad, span, s, ln) for rad, span in ((5, (3, 6)), (3, (2, 3)))
                                    for s in (side, -side) for ln in dict.fromkeys(lengths)]:
        length_ = max(ln, radius + 1)
        x0, y0, face, (dc, dr), (nx, ny) = side_tiles(way, i, s, 1)
        yard_c, yard_r = x0 + nx * length_, y0 + ny * length_
        area = [(yard_c + a, yard_r + b) for a in range(-radius, radius + 1)
                for b in range(-radius, radius + 1)]
        track = [(x0 + nx * k, y0 + ny * k) for k in range(0, length_)]
        if not all(free_tile(W, x, y) for x, y in track + area):
            continue
        if any(abs(int(L.LV[y, x]) - way.z[i]) > 2 for x, y in track):
            continue   # a long track stays on the bench the road runs on
        # The farm stands at the road's level: only where the ground is near it already.
        zr = way.z[i]
        if abs(int(np.median([L.LV[y, x] for x, y in area])) - zr) > (2 if radius > 3 else 3):
            continue
        lv = zr
        for x, y in area + track:
            L.LV[y, x] = lv
        tt = W.tidx(way.style.get("track", "world.road_earth"))
        yard = [(yard_c + a, yard_r + b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        for x, y in track + yard:
            L.T[y, x] = tt
            L.STREET[y, x] = True
        kitd = dict(P.HAMLETS[fam])
        k = st.randint(lo, hi)
        placed = []
        for (a, b, f) in YARD_SPOTS[radius]:
            if len(placed) >= k:
                break
            if (a, b) == (-nx * abs(a or b), -ny * abs(a or b)):
                continue  # the track's side of the yard stays open
            item = st.weighted(kitd)
            d = W.cat.items.get(item)
            if d is None:
                continue
            kk = L._rot(item, f, st.randint(0, 3))
            pw, ph = L._plan_size(item, kk)
            cx, cy = yard_c + a, yard_r + b
            # Front edge toward the yard.
            fc, fr = {"south": (0, 1), "north": (0, -1), "east": (1, 0), "west": (-1, 0)}[f]
            c0 = cx - (pw - 1) // 2 if fc == 0 else (cx - pw + 1 if fc > 0 else cx)
            r0 = cy - (ph - 1) // 2 if fr == 0 else (cy - ph + 1 if fr > 0 else cy)
            p = put(W, item, c0, r0, f, st.randint(0, 5), level=lv)
            if p:
                placed.append(p)
        if len(placed) < 2:
            continue
        W.farm = W.farm if W.farm is not None else np.zeros((ROWS, COLS), dtype=bool)
        for x, y in area:
            W.farm[y, x] = True
        if any(p.id == "world.sheepfold" for p in placed):
            mark_pasture(W, yard_c, yard_r)
            W.stats["pastures"] = W.stats.get("pastures", 0) + 1
        crop(W, fam, (yard_c, yard_r), radius, (nx, ny), lv, st)
        # Graph: a junction on the road and a track to the yard.
        jc, jr = way.path[i]
        jid = way.nodes.get(i, (f"{way.id}_farm_{jc}_{jr}", None))[0]
        way.nodes.setdefault(i, (jid, None))
        yid = f"{way.id}_yard_{yard_c}_{yard_r}"
        g.nodes.append(Node(yid, grid(yard_c, yard_r), None))
        W.stats.setdefault("_tracks", []).append((jid, yid, [grid(*way.path[i])]))
        W.stats["farms"] = W.stats.get("farms", 0) + 1
        W.stats.setdefault("farm_forms", {}).setdefault(radius, 0)
        W.stats["farm_forms"][radius] += 1
        return True
    return False


def crop(W: World, fam: str, yard, radius: int, n, lv: int, st) -> None:
    """The farm's vineyard, olive grove, field or flock's fold beyond its yard, on free ground
    within a level of the yard (the plot follows the ground; nothing is levelled for it)."""
    plots = P.FARM_PLOTS.get(fam)
    if not plots:
        return
    soil, plant, step = plots[st.randint(0, len(plots) - 1)]
    L = W.L
    nx, ny = n
    tx, ty = (ny, nx) if nx else (1, 0)   # across the normal
    if soil == "pasture":
        for d in range(radius + 2, radius + 7):
            for a in (0, -3, 3):
                c = yard[0] + nx * d + tx * a
                r = yard[1] + ny * d + ty * a
                if put(W, plant, c - 1, r - 1, level=int(L.LV[r, c])):
                    mark_pasture(W, c, r)
                    W.stats["pastures"] = W.stats.get("pastures", 0) + 1
                    return
        return
    tiles = []
    for d in range(radius + 2, radius + 8):
        for a in range(-3, 4):
            x = yard[0] + nx * d + tx * a
            y = yard[1] + ny * d + ty * a
            if free_tile(W, x, y) and abs(int(L.LV[y, x]) - lv) <= 1:
                tiles.append((x, y, d, a))
    if len(tiles) < 12:
        return
    if soil:
        t = W.tidx(soil)
        for x, y, _d, _a in tiles:
            L.T[y, x] = t
    if plant:
        for x, y, d, a in tiles:
            if (d - radius) % step[1] == 0 and (a + 3) % step[0] == 0 and L.OCC[y, x] < 0:
                put(W, plant, x, y, variant=st.randint(0, 3))
    W.stats.setdefault("crops", {}).setdefault(plant or soil, 0)
    W.stats["crops"][plant or soil] += 1


def mark_pasture(W: World, c: int, r: int, radius: int = 8) -> None:
    W.pasture = W.pasture if W.pasture is not None else np.zeros((ROWS, COLS), dtype=bool)
    m = (np.abs(CC - c) <= radius) & (np.abs(RR - r) <= radius) & W.land & ~W.road & ~W.river
    W.pasture |= m


def end_place(W: World, g: Graph, way: Way, what: str) -> None:
    """Where a route ends without a town: a fishing hamlet, a harbour, charcoal burners."""
    i = len(way.path) - 2
    fam = {"fishing": "fishing", "harbour": "fishing", "charcoal": "charcoal"}[what]
    for di in range(0, 12):
        j = i - di
        if j < 2:
            break
        if hamlet(W, g, way, j, 1, fam, (3,)) or hamlet(W, g, way, j, -1, fam, (3,)):
            break
    if what in ("fishing", "harbour"):
        c, r = way.path[-1]
        harbour(W, g, c, r, f"{way.id}_harbour", mole=(what == "harbour"))


def harbour(W: World, g: Graph, c: int, r: int, name: str, mole: bool = False) -> tuple | None:
    """A jetty (or a mole with a beacon) from the shore tile nearest (c, r) straight out to sea,
    and a fishing lane from its head to grounds offshore."""
    L = W.L
    sea = ~W.land
    best = None
    for dr in range(-10, 11):
        for dc in range(-10, 11):
            x, y = c + dc, r + dr
            if not (0 <= x < COLS and 0 <= y < ROWS) or not W.land[y, x] or W.reserved[y, x]:
                continue
            for sx, sy in DIRS:
                run = 0
                while run < 6 and 0 <= y + sy * (run + 1) < ROWS and 0 <= x + sx * (run + 1) < COLS \
                        and sea[y + sy * (run + 1), x + sx * (run + 1)]:
                    run += 1
                if run >= 4:
                    key = (abs(dc) + abs(dr), dc, dr, sx, sy)
                    if best is None or key < best[0]:
                        best = (key, x, y, sx, sy)
    if best is None:
        return None
    _, x, y, sx, sy = best
    item = "world.mole" if mole else "world.jetty"
    n = 4 if mole else 3
    tiles = [(x + sx * k, y + sy * k) for k in range(1, n + 1)]
    for tx, ty in tiles:
        if L.OCC[ty, tx] < 0:
            p = Placed(len(L.items), item, tx, ty, 1, 1, 0, None, SRC)
            L.items.append(p)
            L.OCC[ty, tx] = p.index
    if mole:
        for dx, dy in ((sy, sx), (-sy, -sx), (-sx, -sy)):
            if put(W, "world.beacon", x + dx, y + dy):
                break
    head = tiles[-1]
    # Fishing grounds: straight out, then wherever open sea is.
    gx, gy = head
    for _ in range(18):
        nx_, ny_ = gx + sx, gy + sy
        if not (0 <= nx_ < COLS and 0 <= ny_ < ROWS) or not sea[ny_, nx_]:
            break
        gx, gy = nx_, ny_
    pts = raster_line(head, (gx, gy))
    if len(pts) >= 4:
        g.lanes.append(Lane(f"{name}_fishing", "sea", [grid(*p) for p in [pts[0], pts[-1]]],
                            [Port("home", 0, f"{item}:mooring"), Port("grounds", 1),
                             Port("start", 0), Port("end", 1)]))
    W.stats.setdefault("harbours", []).append((name, item, (x, y)))
    W.stats.setdefault("_harbour_nodes", []).append((name, (x, y)))
    return head


def raster_line(a, b):
    n = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
    return [(round(a[0] + (b[0] - a[0]) * t / max(n, 1)), round(a[1] + (b[1] - a[1]) * t / max(n, 1)))
            for t in range(n + 1)]


# --- graph ----------------------------------------------------------------------------------

def graph_edges(W: World, g: Graph, ways: list[Way]) -> None:
    have = {n.id for n in g.nodes}
    for way in ways:
        idx = sorted(way.nodes)
        if not idx:
            continue
        for i in (0, len(way.path) - 1):
            if i not in way.nodes:
                way.nodes[i] = (f"{way.id}_{way.path[i][0]}_{way.path[i][1]}", None)
        idx = sorted(way.nodes)
        for i in idx:
            nid, kind = way.nodes[i]
            if nid not in have:
                g.nodes.append(Node(nid, grid(*way.path[i]), kind))
                have.add(nid)
        for a, b in zip(idx, idx[1:]):
            via = corners(way.path[a:b + 1])
            na, nb = way.nodes[a][0], way.nodes[b][0]
            if na != nb:
                g.edges.append(Edge(na, nb, way.kind, [grid(*p) for p in via]))
    for a, b, via in W.stats.pop("_tracks", []):
        g.edges.append(Edge(a, b, "track"))


def corners(path) -> list:
    """The interior turning points of an axis-parallel path."""
    out = []
    for p, q, s in zip(path, path[1:], path[2:]):
        if (q[0] - p[0], q[1] - p[1]) != (s[0] - q[0], s[1] - q[1]):
            out.append(q)
    return out


# --- entry points ---------------------------------------------------------------------------

def build(W: World, g: Graph) -> None:
    river_of = {}
    for co in W.stats.get("_courses", []):
        js, is_ = np.nonzero(co.mask)
        for j, i in zip(js.tolist(), is_.tolist()):
            river_of.setdefault((i, j), co.id)
    W.stats["_river_of"] = river_of
    ways = lay_ways(W, g)
    kit(W, g, ways)
    graph_edges(W, g, ways)
    W.stats["route_tiles"] = {}
    for way in ways:
        W.stats["route_tiles"][way.id] = W.stats["route_tiles"].get(way.id, 0) + \
            len([i for i in range(len(way.path)) if i not in way.skip])
    W.stats.pop("_river_of")
    W.stats.pop("_stations", None)
    W.stats.pop("_station_spots", None)


def lanes(W: World, g: Graph) -> None:
    sea = ~W.land
    dland = distance_to(W.land, 3)
    jitter = noise(5.0, "lanejitter")
    for lid, lane in P.LANES.items():
        if lane["kind"] == "river":
            cost = np.where(W.river | (sea & (dland <= 2)), 1.0 + 0.2 * (jitter + 1), np.inf)
        else:
            cost = np.where(sea, 1.0 + 3.0 * (dland <= 1) + 0.4 * (jitter + 1), np.inf)
        pts = [snap_water(W, tuple(p), lane["kind"]) for p in lane["points"]]
        full: list = []
        marks = [0]
        for a, b in zip(pts, pts[1:]):
            seg = astar8(cost, a, b)
            if not seg:
                W.stats.setdefault("lane_failures", []).append(f"{lid}: {a} -> {b}")
                seg = [a, b]
            full += seg if not full else seg[1:]
            marks.append(len(full) - 1)
        keep = sorted(set(simplify(full, 1.5)) | {full[i] for i in marks}, key=full.index)
        index_of = {i: keep.index(full[marks[i]]) for i in range(len(pts))}
        ports = [Port(pid, index_of[at]) for pid, at in sorted(lane["ports"].items(),
                                                                key=lambda x: (x[1], x[0]))]
        ports += [Port("start", 0), Port("end", len(keep) - 1)]
        g.lanes.append(Lane(lid, lane["kind"], [grid(*p) for p in keep], ports))
        W.stats.setdefault("lane_tiles", {})[lid] = len(full)
        if lane.get("harbour") is not None:
            c, r = pts[lane["harbour"]]
            harbour(W, g, c, r, lid, mole=True)


def snap_water(W: World, p, kind: str):
    """The plan's lane point, or the nearest sea (river) tile to it within 8 tiles when it fell
    on land after the coast was roughened."""
    water = W.river | ~W.land if kind == "river" else ~W.land
    c, r = p
    if water[r, c]:
        return p
    best = None
    for dr in range(-8, 9):
        for dc in range(-8, 9):
            x, y = c + dc, r + dr
            if 0 <= x < COLS and 0 <= y < ROWS and water[y, x]:
                key = (dc * dc + dr * dr, dc, dr)
                if best is None or key < best[0]:
                    best = (key, (x, y))
    return best[1] if best else p


def astar8(cost: np.ndarray, a, b, margin: int = 60) -> list[tuple[int, int]]:
    """Cheapest 8-connected path over finite costs inside the a-b box grown by `margin`; the end
    tiles are always open (a lane may start in a harbour on a town's tile)."""
    c0 = max(min(a[0], b[0]) - margin, 0)
    c1 = min(max(a[0], b[0]) + margin, COLS - 1)
    r0 = max(min(a[1], b[1]) - margin, 0)
    r1 = min(max(a[1], b[1]) + margin, ROWS - 1)
    sub = cost[r0:r1 + 1, c0:c1 + 1].copy()
    h, w = sub.shape
    start, goal = (a[1] - r0, a[0] - c0), (b[1] - r0, b[0] - c0)
    sub[start] = sub[goal] = 1.0
    fin = np.isfinite(sub)
    dist = {start: 0.0}
    prev = {}
    heap = [(0.0, start)]
    while heap:
        f, cur = heapq.heappop(heap)
        if cur == goal:
            break
        d0 = dist[cur]
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if not dr and not dc:
                    continue
                nr, nc = cur[0] + dr, cur[1] + dc
                if not (0 <= nr < h and 0 <= nc < w) or not fin[nr, nc]:
                    continue
                nd = d0 + sub[nr, nc] * (1.4142 if dr and dc else 1.0)
                if nd < dist.get((nr, nc), math.inf):
                    dist[(nr, nc)] = nd
                    prev[(nr, nc)] = cur
                    heapq.heappush(heap, (nd + math.hypot(nr - goal[0], nc - goal[1]), (nr, nc)))
    if goal not in dist:
        return []
    out = [goal]
    while out[-1] != start:
        out.append(prev[out[-1]])
    out.reverse()
    return [(c + c0, r + r0) for r, c in out]


def simplify(points, tol=1.5):
    """Douglas-Peucker on a list of tiles; keeps both ends."""
    if len(points) < 3:
        return list(points)
    (ac, ar), (bc, br) = points[0], points[-1]
    dx, dy = bc - ac, br - ar
    ll = math.hypot(dx, dy) or 1.0
    dmax, imax = -1.0, 0
    for i, (c, r) in enumerate(points[1:-1], 1):
        d = abs(dy * (c - ac) - dx * (r - ar)) / ll
        if d > dmax:
            dmax, imax = d, i
    if dmax <= tol:
        return [points[0], points[-1]]
    left = simplify(points[:imax + 1], tol)
    return left[:-1] + simplify(points[imax:], tol)
