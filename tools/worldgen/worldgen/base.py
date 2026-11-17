"""The procedural base layer (world-tech §3.8): the whole world's land and sea from the plan.

Order (every step seeded and a pure function of position and the plan entry it serves):
 1. coasts: land polygons rasterised, outlines roughened by bounded noise, specks removed;
    sea depth bands by distance to land (1, 3, 6 tiles), shallows off low beaches;
 2. relief: plains rise inland to each stretch's plateau, hills by noise, mountain bands on top;
    reserved city and town rects flat at their base level; slopes limited to 2 levels per tile;
 3. rivers: meandered, carved non-increasing from source to mouth, flow written to aux;
 4. routes and sea lanes marked `build` in the plan: A* over a cost grid, painted, graphed;
 5. country: terrain by stretch look and height, fields with plot texture, forests with
    clearings, riparian trees and reeds; mountain tops impassable;
 6. districts: <region>/land, /sea, /road, /reserved, and one per seam.
"""

from __future__ import annotations

import heapq
import math

import numpy as np

from plan import world_plan as P

from . import raster, rng
from .catalog import Catalog
from .coords import COLS, ROWS
from .dsl import Layout, Placed
from .graph import Edge, Graph, Lane, Node, Port

SEED = "base"


# --- array helpers ---------------------------------------------------------------------------

def box_blur(a: np.ndarray, r: int) -> np.ndarray:
    if r <= 0:
        return a.astype(np.float64)
    p = np.pad(a.astype(np.float64), r + 1, mode="edge")
    s = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    out = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
    return out[:a.shape[0], :a.shape[1]] / (k * k)


def _shift(a: np.ndarray, dr: int, dc: int, fill) -> np.ndarray:
    out = np.full_like(a, fill)
    h, w = a.shape
    out[max(dr, 0):h + min(dr, 0), max(dc, 0):w + min(dc, 0)] = \
        a[max(-dr, 0):h + min(-dr, 0), max(-dc, 0):w + min(-dc, 0)]
    return out


N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def distance_to(target: np.ndarray, cap: int) -> np.ndarray:
    """Approximate distance (tiles) from every cell to the nearest target cell, capped."""
    d = np.full(target.shape, cap, dtype=np.int16)
    d[target] = 0
    reached = target.copy()
    front = target.copy()
    for k in range(1, cap):
        grown = np.zeros_like(front)
        for dr, dc in (N8 if k % 2 == 0 else N4):
            grown |= _shift(front, dr, dc, False)
        new = grown & ~reached
        if not new.any():
            break
        d[new] = k
        reached |= new
        front = new
    return d


def flood(seed: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Cells of `allowed` 4-connected to `seed` (iterative dilation)."""
    seen = seed & allowed
    while True:
        grown = seen.copy()
        for dr, dc in N4:
            grown |= _shift(seen, dr, dc, False)
        grown &= allowed
        if (grown == seen).all():
            return seen
        seen = grown


def poly(points) -> np.ndarray:
    return raster.poly_mask(points, 0, 0, COLS, ROWS)


def rect_mask(rect) -> np.ndarray:
    m = np.zeros((ROWS, COLS), dtype=bool)
    c0, r0, c1, r1 = rect
    m[max(r0, 0):r1 + 1, max(c0, 0):c1 + 1] = True
    return m


CC, RR = rng.grid_coords(0, 0, COLS, ROWS)


# --- 1. coasts -------------------------------------------------------------------------------

def make_land() -> np.ndarray:
    raw = np.zeros((ROWS, COLS), dtype=bool)
    for pts in P.LAND.values():
        raw |= poly(pts)
    for pts in P.SEA.values():
        raw &= ~poly(pts)
    isl = np.zeros_like(raw)
    for pts in P.ISLANDS.values():
        isl |= poly(pts)
    a = P.COAST_NOISE
    n = rng.fbm(CC, RR, a["scale"], rng.hash64(SEED, "coast"), octaves=5, gain=0.6) * 2 - 1
    n = np.clip(n * 1.8, -1, 1)
    n_isl = rng.fbm(CC, RR, 7.0, rng.hash64(SEED, "isles"), octaves=3) * 2 - 1

    def rough(m, amp, noise):
        sd = distance_to(~m, 12).astype(np.float64) - distance_to(m, 12).astype(np.float64)
        return sd + amp * noise > 0

    land = rough(raw, a["amp"], n) | rough(isl, 1.3, n_isl)
    core_land = distance_to(~(raw | isl), 3) >= 2
    core_sea = distance_to(raw | isl, 3) >= 2
    # Drop specks: land not connected to an authored core, sea pockets cut off from open water.
    land = flood(core_land, land)
    sea = flood(core_sea | (~(raw | isl) & ~land), ~land)
    land = ~sea
    return land


# --- regions ---------------------------------------------------------------------------------

def region_map(land: np.ndarray) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Index per tile into the region list (towns and cities included), and the stretch map
    (which stretch's look applies under a city or town)."""
    names = list(P.REGIONS)
    idx = {n: i for i, n in enumerate(names)}
    reg = np.full((ROWS, COLS), -1, dtype=np.int16)
    stretch = np.full((ROWS, COLS), -1, dtype=np.int16)

    def apply(target, rules):
        for rid, kind, rect in rules:
            m = rect_mask(rect) & (target < 0)
            if kind == "land":
                m &= land
            elif kind == "sea":
                m &= ~land
            target[m] = idx[rid]

    places = [r for r in P.OWNERSHIP if P.REGIONS[r[0]][0] in ("home", "city", "town")]
    others = [r for r in P.OWNERSHIP if P.REGIONS[r[0]][0] not in ("home", "city", "town")]
    seams = [r for r in others if P.REGIONS[r[0]][0] == "seam"]
    rest = [r for r in others if P.REGIONS[r[0]][0] != "seam"]
    for target, with_places in ((reg, True), (stretch, False)):
        if with_places:
            apply(target, places)
        apply(target, seams)
        for band, rid in P.BAND_REGIONS.items():
            m = poly(P.BANDS[band]["poly"]) & land & (target < 0)
            target[m] = idx[rid]
        apply(target, rest)
    corner = idx["corner"]
    stretch[stretch < 0] = idx["tyrrhenian"]
    reg[reg < 0] = idx["tyrrhenian"]
    # The corner's own look applies inside its rect.
    stretch[rect_mask(P.REGIONS["corner"][3]) & land] = corner
    return reg, names, stretch


# --- 2-3. relief and rivers ------------------------------------------------------------------

def meander(points, amount: float, key: str) -> list[tuple[int, int]]:
    """Subdivide a polyline every ~5 tiles and push the new vertices sideways by smooth noise;
    the plan's own vertices stay fixed so rivers still meet towns and mouths."""
    out = [tuple(points[0])]
    s = rng.hash64(SEED, "meander", key)
    for (ac, ar), (bc, br) in zip(points, points[1:]):
        length = math.hypot(bc - ac, br - ar)
        n = max(1, int(length // 5))
        nx, ny = (-(br - ar) / length, (bc - ac) / length) if length else (0.0, 0.0)
        for i in range(1, n):
            t = i / n
            x, y = ac + (bc - ac) * t, ar + (br - ar) * t
            n_ = rng.fbm(np.array(x), np.array(y), 16.0, s, octaves=2).item()
            off = float(np.clip((n_ * 2 - 1) * 2.2, -1, 1)) * amount
            out.append((int(round(x + nx * off)), int(round(y + ny * off))))
        out.append((bc, br))
    return out


def relief(land, reg, names, stretch):
    sea = ~land
    dist = distance_to(sea, 64).astype(np.float64)
    plateau = np.ones((ROWS, COLS))
    ramp = np.full((ROWS, COLS), 6.0)
    amp = np.zeros((ROWS, COLS))
    for i, n in enumerate(names):
        m = stretch == i
        if not m.any():
            continue
        pl, rp, am = P.RELIEF.get(n, (P.REGIONS[n][4] or 1, 6, 0.0))
        plateau[m], ramp[m], amp[m] = pl, rp, am
    # Domain warp: read each stretch's relief settings at a wandering offset, so the borders
    # between stretches (straight rect edges in the plan) never show as straight contours.
    wc = (rng.fbm(CC, RR, 30.0, rng.hash64(SEED, "warp_c"), octaves=3) - 0.5) * 2 * 16
    wr = (rng.fbm(CC, RR, 30.0, rng.hash64(SEED, "warp_r"), octaves=3) - 0.5) * 2 * 16
    ic = np.clip(np.rint(CC + wc), 0, COLS - 1).astype(np.intp)
    ir = np.clip(np.rint(RR + wr), 0, ROWS - 1).astype(np.intp)
    plateau, ramp, amp = (box_blur(box_blur(x[ir, ic], 10), 10) for x in (plateau, ramp, amp))
    hills = (rng.fbm(CC, RR, 22.0, rng.hash64(SEED, "hills"), octaves=4) - 0.5) * 2
    lv = 1 + np.minimum(plateau - 1, dist / ramp) + amp * hills * np.clip(dist / 6, 0, 1)
    bandsoft = np.zeros((ROWS, COLS))
    imp = np.zeros((ROWS, COLS), dtype=bool)
    for bid, b in P.BANDS.items():
        # Work in the band's bounding box (grown by the blur) only.
        bc = [p[0] for p in b["poly"]]
        br = [p[1] for p in b["poly"]]
        c0, c1 = max(min(bc) - 8, 0), min(max(bc) + 8, COLS - 1)
        r0, r1 = max(min(br) - 8, 0), min(max(br) + 8, ROWS - 1)
        win = (slice(r0, r1 + 1), slice(c0, c1 + 1))
        m = raster.poly_mask(b["poly"], c0, r0, c1 - c0 + 1, r1 - r0 + 1)
        soft = box_blur(m, 4) * land[win]
        cc, rc = CC[win], RR[win]
        lo, hi = b["levels"]
        if b.get("cone"):
            pts = np.array(b["poly"], dtype=np.float64)
            mc, mr = pts[:, 0].mean(), pts[:, 1].mean()
            rad = max(np.hypot(pts[:, 0] - mc, pts[:, 1] - mr).mean(), 1.0)
            t = np.clip(1 - np.hypot(cc - mc, rc - mr) / (rad * 1.4), 0, 1)
            blv = lo + (hi - lo) * t ** 1.3
        else:
            n = rng.fbm(cc, rc, b["scale"], rng.hash64(SEED, "band", bid), octaves=4)
            ridge = 1 - np.abs(rng.fbm(cc, rc, b["scale"] * 2.2, rng.hash64(SEED, "ridge", bid),
                                       octaves=3) * 2 - 1)
            blv = lo + (hi - lo) * np.clip(0.55 * n + 0.6 * ridge - 0.15, 0, 1)
        lw = lv[win]
        lv[win] = np.where(soft > 0, np.maximum(lw, lw * (1 - soft) + blv * soft), lw)
        bandsoft[win] = np.maximum(bandsoft[win], soft)
        bi = (soft > 0.6) & (blv * soft >= b["impassable"])
        for (pc, pr), radius in b.get("passes", []):
            bi &= np.hypot(cc - pc, rc - pr) > radius
        imp[win] |= bi
    # Dither the contours so level steps wander like real ones instead of tracing blur lines.
    lv += (rng.fbm(CC, RR, 7.0, rng.hash64(SEED, "contour"), octaves=3) - 0.5) * 1.1
    level = np.where(land, np.clip(np.rint(lv), 1, 15), 0).astype(np.int16)

    reserved = np.zeros((ROWS, COLS), dtype=bool)
    flat = []
    for rid, (kind, _set, _time, rect, base) in P.REGIONS.items():
        if kind in ("city", "home"):
            m = rect_mask(rect)
            reserved |= m
            flat.append((m, base))
        elif kind == "town":
            reserved |= rect_mask(rect)  # no country items; the town's builder shapes the ground

    def flatten():
        for m, base in flat:
            level[m & land] = max(base, 1)

    flatten()
    imp &= ~reserved

    river = np.zeros((ROWS, COLS), dtype=bool)
    flow = np.zeros((ROWS, COLS), dtype=np.int8)
    courses = []
    for rid, rv in P.RIVERS.items():
        pts = meander(rv["points"], rv.get("meander", 1) * 2.0, rid)
        path = raster.path_tiles(pts)
        path = [(c, r) for c, r in path if 0 <= c < COLS and 0 <= r < ROWS]
        m = raster.line_mask(pts, rv["width"], 0, 0, COLS, ROWS) & land
        courses.append((rid, pts, path, m, rv["width"]))
        river |= m
    smooth(level, land, river, courses)
    flatten()
    smooth(level, land, river, courses)
    for rid, pts, path, m, width in courses:
        # Flow per river tile from its nearest course segment.
        js, is_ = np.nonzero(m)
        best = np.full(js.size, np.inf)
        f = np.zeros(js.size, dtype=np.int8)
        for (ac, ar), (bc, br) in zip(pts, pts[1:]):
            dx, dy = bc - ac, br - ar
            ll = max(dx * dx + dy * dy, 1)
            t = np.clip(((is_ - ac) * dx + (js - ar) * dy) / ll, 0, 1)
            d2 = (is_ - ac - t * dx) ** 2 + (js - ar - t * dy) ** 2
            b = d2 < best
            best[b] = d2[b]
            f[b] = (0 if dx > 0 else 2) if abs(dx) >= abs(dy) else (1 if dy > 0 else 3)
        flow[js, is_] = f
    fix_flow(level, river, flow)
    imp &= ~river
    imp |= land & (level >= 13) & ~reserved
    return level, imp, river, flow, reserved, bandsoft, courses


def fix_flow(level, river, flow) -> None:
    """Lower any river tile that sits above the river tile flowing into it, until stable."""
    steps = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}  # aux -> (dr, dc)
    for _ in range(200):
        changed = False
        for f, (dr, dc) in steps.items():
            src = river & (flow == f)
            js, is_ = np.nonzero(src)
            nj, ni = js + dr, is_ + dc
            ok = (nj >= 0) & (nj < ROWS) & (ni >= 0) & (ni < COLS)
            js, is_, nj, ni = js[ok], is_[ok], nj[ok], ni[ok]
            down = river[nj, ni] & (level[nj, ni] > level[js, is_])
            if down.any():
                np.minimum.at(level, (nj[down], ni[down]), level[js[down], is_[down]])
                changed = True
        if not changed:
            return


def carve(level, courses):
    for rid, pts, path, m, width in courses:
        run = 15
        best = {}
        for (c, r) in path:
            if level[r, c] == 0:
                break
            run = min(run, int(level[r, c]))
            best[(c, r)] = run
        if not best:
            continue
        js, is_ = np.nonzero(m)
        keys = np.array(list(best.keys()))
        vals = np.array(list(best.values()))
        for j, i in zip(js.tolist(), is_.tolist()):
            k = np.argmin(np.abs(keys[:, 0] - i) + np.abs(keys[:, 1] - j))
            level[j, i] = min(level[j, i], vals[k])


def smooth(level, land, river, courses):
    """Carve rivers, then limit every land tile to 2 levels above its lowest 4-neighbour."""
    carve(level, courses)
    for _ in range(16):
        lim = level.copy()
        for dr, dc in N4:
            lim = np.minimum(lim, _shift(level, dr, dc, 15) + 2)
        lim = np.where(land, np.maximum(lim, 1), 0)
        if (lim == level).all():
            break
        level[:] = lim
    carve(level, courses)


# --- 4. routes and lanes ---------------------------------------------------------------------

def resolve(point) -> tuple[tuple[int, int], str | None]:
    if isinstance(point, str):
        layer, pid = point.split(":", 1)
        return tuple(P.PORTALS[pid][1]), pid
    return tuple(point), None


def astar(cost: np.ndarray, a, b, diag=True) -> list[tuple[int, int]]:
    """Cheapest 8-connected path from a to b over finite costs (cost of entering a tile)."""
    h, w = cost.shape
    start, goal = (a[1], a[0]), (b[1], b[0])
    dist = {start: 0.0}
    prev = {}
    heap = [(0.0, start)]
    steps = N8 if diag else N4
    while heap:
        _, cur = heapq.heappop(heap)
        if cur == goal:
            break
        d0 = dist[cur]
        for dr, dc in steps:
            nr, nc = cur[0] + dr, cur[1] + dc
            if not (0 <= nr < h and 0 <= nc < w):
                continue
            k = cost[nr, nc]
            if not np.isfinite(k):
                continue
            nd = d0 + k * (1.4142 if dr and dc else 1.0)
            if nd < dist.get((nr, nc), math.inf):
                dist[(nr, nc)] = nd
                prev[(nr, nc)] = cur
                heur = math.hypot(nr - goal[0], nc - goal[1])
                heapq.heappush(heap, (nd + heur, (nr, nc)))
    if goal not in dist:
        return []
    out = [goal]
    while out[-1] != start:
        out.append(prev[out[-1]])
    out.reverse()
    return [(c, r) for r, c in out]


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


def four_connected(points):
    return raster.path_tiles([tuple(p) for p in points])


# --- the build -------------------------------------------------------------------------------

def build_base(cat: Catalog) -> tuple[Layout, Graph, dict]:
    stats: dict = {}
    land = make_land()
    reg, names, stretch = region_map(land)
    level, imp, river, flow, reserved, bandsoft, courses = relief(land, reg, names, stretch)

    L = Layout(layer="base", region="base", set="world", origin=(0, 0), size=(COLS, ROWS),
               base_level=0, catalog=cat, regions=list(P.REGIONS), source="plan/world_plan.py")
    src = "plan/world_plan.py"
    L.LV[:] = level
    L.IMP[:] = imp

    def tidx(t):
        return L._terrain_index(t, src)

    # Base terrain per tile by look.
    terr = np.zeros((ROWS, COLS), dtype=np.int16)
    for i, n in enumerate(names):
        m = (stretch == i) & land
        if not m.any():
            continue
        look = P.STRETCH_LOOK.get(n)
        base = look["base"] if look else "world.steppe"
        terr[m] = tidx(base)
    for rid, base in P.RESERVED_BASE.items():
        terr[rect_mask(P.REGIONS[rid][3]) & land] = tidx(base)

    # Relief overlays.
    noise = rng.fbm(CC, RR, 6.0, rng.hash64(SEED, "rockiness"), octaves=3)
    rock = land & ~reserved & (((level >= 9) & (noise > 0.35)) | ((level >= 7) & (noise > 0.62)))
    scree = land & ~reserved & ~rock & (bandsoft > 0.25) & (bandsoft < 0.7) & (noise > 0.58)
    snow = land & ~reserved & (level >= 12) & (noise > 0.3)
    terr[scree] = tidx("world.scree")
    terr[rock] = tidx("world.rock")
    terr[snow] = tidx("world.snow")

    # Fields near water in farming stretches, with plot texture.
    dist_river = distance_to(river, 24)
    plotn = rng.hash01(CC // 6 + (RR // 4) * 977, RR // 4, rng.hash64(SEED, "plots"))
    fieldzone = rng.fbm(CC, RR, 16.0, rng.hash64(SEED, "fieldzone"), octaves=3)
    for i, n in enumerate(names):
        look = P.STRETCH_LOOK.get(n)
        if not look or not look["fields"] or not look["field"]:
            continue
        m = (stretch == i) & land & ~reserved & ~rock & ~snow & ~scree & (level <= 4)
        if not m.any():
            continue
        score = fieldzone + np.clip(1 - dist_river / 18.0, 0, 1) * 0.35
        thr = np.quantile(score[m], 1 - look["fields"]) if m.sum() > 50 else 2
        fz = m & (score >= thr) & (plotn > 0.22)
        # Paths between plots: plot cells are 6 x 4 with a 1-tile margin left as base.
        fz &= ((CC % 6) != 0) & ((RR % 4) != 0)
        terr[fz] = tidx(look["field"])
    # Marsh where the Mesopotamian rivers reach the gulf.
    near_gulf = rect_mask((1040, 370, 1110, 410)) & land
    marsh = near_gulf & (dist_river < 6) & ~river & (noise > 0.4)
    terr[marsh] = tidx("world.marsh")

    # Transitions: two different base terrains never touch (V8): turn one side into an overlay.
    isbase = np.zeros(len(L.terrains) + 1, dtype=bool)
    for t, tid in enumerate(L.terrains):
        isbase[t] = cat.terrain[tid].base if tid in cat.terrain else False
    tb = np.where(land, terr, -1)
    bmask = land & isbase[np.maximum(tb, 0)]
    conflict = np.zeros_like(land)
    right = bmask[:, 1:] & bmask[:, :-1] & (tb[:, 1:] != tb[:, :-1])
    conflict[:, 1:] |= right
    down = bmask[1:, :] & bmask[:-1, :] & (tb[1:, :] != tb[:-1, :])
    conflict[1:, :] |= down
    if conflict.any():
        alluv = tidx("world.alluvium") if "world.alluvium" in L.terrains else -9
        home = tidx("grass") if "grass" in L.terrains else -9
        js, is_ = np.nonzero(conflict)
        for j, i in zip(js.tolist(), is_.tolist()):
            near = {int(tb[j, i])} | {int(tb[j + dj, i + di]) for dj, di in N4
                                       if 0 <= j + dj < ROWS and 0 <= i + di < COLS}
            if home in near:
                terr[j, i] = tidx("meadow")
            elif alluv in near:
                terr[j, i] = tidx("world.field")
            else:
                terr[j, i] = tidx("world.scree")

    # Water: rivers, sea depth, shallows.
    terr[river] = tidx("world.river")
    L.AUX[river] = flow[river]
    sea = ~land
    dland = distance_to(land, 8)
    depth = np.select([dland <= 1, dland <= 3, dland <= 6], [0, 1, 2], 3).astype(np.int8)
    terr[sea] = tidx("world.sea")
    L.AUX[sea] = depth[sea]
    beach = land & (level <= 1)
    near_beach = distance_to(beach, 3) <= 2
    shallows = sea & near_beach & (dland <= 2)
    terr[shallows] = tidx("world.shallows")
    L.AUX[shallows] = 0
    L.T[:] = terr
    # Coast faces: raised land next to the sea uses its terrain's coast material.
    coast = land & (distance_to(sea, 2) <= 1) & (level >= 2)
    high = land & ~coast & (level >= 7)
    for t, tid in enumerate(L.terrains):
        faces = cat.faces(tid)
        for m, material in ((coast, "world.coast"), (high, "world.rock")):
            if material in faces:
                mt = m & (L.T == t)
                L.AUX[mt] = faces.index(material)

    # Routes.
    g = Graph("base")
    road = np.zeros((ROWS, COLS), dtype=bool)
    nodes: dict[str, Node] = {}
    jitter = rng.fbm(CC, RR, 5.0, rng.hash64(SEED, "roadjitter"), octaves=2)
    for rid, route in P.ROUTES.items():
        if not route.get("build"):
            continue
        cost = 1.0 + 0.6 * jitter + 0.0
        dl = np.zeros_like(cost)
        for dr, dc in N4:
            dl = np.maximum(dl, np.abs(level - _shift(level, dr, dc, 0)))
        cost = cost + 6.0 * dl
        cost = np.where(river, cost + 12.0, cost)
        cost = np.where(land & ~imp, cost, np.inf)
        pts = [resolve(p) for p in route["points"]]
        full: list[tuple[int, int]] = []
        for (a, _), (b, _) in zip(pts, pts[1:]):
            seg = astar(cost, a, b)
            if not seg:
                stats.setdefault("route_failures", []).append(f"{rid}: {a} -> {b}")
                continue
            full += seg if not full else seg[1:]
        if not full:
            continue
        tiles = four_connected(simplify(full, 0.75))
        m = raster.line_mask(tiles, route["width"], 0, 0, COLS, ROWS) & land
        # Keep the river under a crossing and put a ford on it.
        fordm = m & river
        pave = m & ~river
        terr_road = tidx(route["paving"])
        L.T[pave] = terr_road
        L.STREET |= m
        road |= m
        # A route between portals of one level is graded flat at that level; otherwise the
        # carriageway follows its centre line (steps need ramps: task WG4).
        plv = {P.PORTALS[p.split(":", 1)[1]][2] for p in route["points"] if isinstance(p, str)}
        if len(plv) == 1 and all(isinstance(p, str) for p in route["points"]):
            for (c, r) in tiles:
                L.LV[r, c] = next(iter(plv))
        for (c, r) in tiles:
            for dc in range(-(route["width"] // 2), route["width"] - route["width"] // 2):
                for dr in range(-(route["width"] // 2), route["width"] - route["width"] // 2):
                    cc, rr = c + dc, r + dr
                    if 0 <= cc < COLS and 0 <= rr < ROWS and m[rr, cc]:
                        L.LV[rr, cc] = L.LV[r, c]
        for j, i in zip(*np.nonzero(fordm)):
            p = Placed(len(L.items), "world.ford", int(i), int(j), 1, 1, 0, None, src)
            L.items.append(p)
            L.OCC[j, i] = p.index
        ids = []
        for n_, (pt, pid) in enumerate(pts):
            nid = pid or f"{rid}_{n_}"
            nodes.setdefault(nid, Node(nid, (pt[1], COLS - 1 - pt[0]),
                                       "portal" if pid else None))
            ids.append(nid)
        simp = simplify(full, 1.5)
        g.edges.append(Edge(ids[0], ids[-1], route["kind"],
                            [(r, COLS - 1 - c) for c, r in simp[1:-1]]))
    g.nodes = list(nodes.values())
    for lid, lane in P.LANES.items():
        if not lane.get("build"):
            continue
        cost = np.where(sea, 1.0 + 3.0 * (dland <= 1) + 0.4 * jitter, np.inf)
        pts = lane["points"]
        full = []
        marks = [0]
        for a, b in zip(pts, pts[1:]):
            seg = astar(cost, a, b)
            if not seg:
                stats.setdefault("lane_failures", []).append(f"{lid}: {a} -> {b}")
                seg = [a, b]
            full += seg if not full else seg[1:]
            marks.append(len(full) - 1)
        keep = sorted(set(simplify(full, 1.5)) | {full[i] for i in marks}, key=full.index)
        index_of = {i: keep.index(full[marks[i]]) for i in range(len(pts))}
        ports = [Port(pid, index_of[at]) for pid, at in sorted(lane["ports"].items(),
                                                                       key=lambda x: x[1])]
        g.lanes.append(Lane(lid, lane["kind"], [(r, COLS - 1 - c) for c, r in keep], ports))

    # Country items.
    place_country(L, cat, land, stretch, names, reserved, river, road, rock | snow, level)

    # Districts.
    d = np.zeros((ROWS, COLS), dtype=np.int16)
    for i, n in enumerate(names):
        kind = P.REGIONS[n][0]
        m_land = (reg == i) & land
        m_sea = (reg == i) & ~land
        if kind in ("city", "town", "home"):
            if (m_land | m_sea).any():
                d[m_land | m_sea] = L._dist_index(f"{n}/reserved", src)
        elif kind == "seam":
            if (m_land | m_sea).any():
                d[m_land | m_sea] = L._dist_index(f"{n}/mist", src)
        else:
            if m_land.any():
                d[m_land] = L._dist_index(f"{n}/land", src)
            if m_sea.any():
                d[m_sea] = L._dist_index(f"{n}/sea", src)
            mr = m_land & road
            if mr.any():
                d[mr] = L._dist_index(f"{n}/road", src)
    L.DIST[:] = d
    stats["land_tiles"] = int(land.sum())
    stats["items"] = sum(1 for p in L.items if not p.removed)
    return L, g, stats


def place_country(L: Layout, cat: Catalog, land, stretch, names, reserved, river, road, bare,
                  level) -> None:
    src = "plan/world_plan.py"
    free = land & ~reserved & ~river & ~road & ~bare & (L.OCC < 0) & (level <= 11)
    fz = np.zeros_like(free)
    for t, tid in enumerate(L.terrains):
        if tid.endswith("field") or "field_" in tid or tid.endswith("olive_soil") \
                or tid == "world.scree":
            fz |= L.T == t
    free &= ~fz
    forest_n = rng.fbm(CC, RR, 26.0, rng.hash64(SEED, "forest"), octaves=4)
    clearing = rng.fbm(CC, RR, 7.0, rng.hash64(SEED, "clearing"), octaves=3)
    u = rng.hash01(CC, RR, rng.hash64(SEED, "tree"))
    pick = rng.hash01(CC, RR, rng.hash64(SEED, "species"))
    var = rng.hash_grid(CC, RR, rng.hash64(SEED, "variant"))
    dr_ = distance_to(river, 4)
    for i, n in enumerate(names):
        look = P.STRETCH_LOOK.get(n)
        if not look or not look["plants"]:
            continue
        m = (stretch == i) & free
        if not m.any():
            continue
        share = look["forest"]
        thr = np.quantile(forest_n[m], 1 - share) if share > 0 and m.sum() > 50 else 2
        forest = m & (forest_n >= thr)
        dens = np.where(forest, np.where(clearing < 0.38, 0.04, 0.42), 0.012)
        dens = np.where(m & (dr_ <= 2), np.maximum(dens, 0.10), dens)
        hit = m & (u < dens)
        plants = list(look["plants"].items())
        names_ = [p[0] for p in plants]
        cum = np.cumsum([w for _, w in plants]) / sum(w for _, w in plants)
        js, is_ = np.nonzero(hit)
        for j, i_ in zip(js.tolist(), is_.tolist()):
            item = names_[min(int(np.searchsorted(cum, pick[j, i_], side="right")),
                              len(names_) - 1)]
            d = cat.items.get(item)
            if d is None:
                continue
            k = int(var[j, i_] % np.uint64(max(d.count, 1)))
            p = Placed(len(L.items), item, i_, j, 1, 1, k, None, src)
            L.items.append(p)
            L.OCC[j, i_] = p.index
    # Reeds on river banks (tiles beside the water).
    bank = land & ~river & ~reserved & (dr_ == 1) & (L.OCC < 0) & ~road
    reeds = bank & (rng.hash01(CC, RR, rng.hash64(SEED, "reeds")) < 0.22)
    js, is_ = np.nonzero(reeds)
    for j, i_ in zip(js.tolist(), is_.tolist()):
        p = Placed(len(L.items), "world.t_reeds", i_, j, 1, 1, int((i_ * 7 + j) % 4), None, src)
        L.items.append(p)
        L.OCC[j, i_] = p.index
