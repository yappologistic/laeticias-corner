"""The procedural base layer (world-tech §3.8): the whole world's land and sea from the plan.

Order (every step seeded and a pure function of position and the plan entry it serves):
 1. coasts: land polygons rasterised, outlines roughened at three scales (bays and headlands,
    capes, rocks), specks removed, authored inlets kept; rocky islets beside the open-sea lanes;
 2. relief: plains rise inland to each stretch's plateau, hills by noise, headlands raised and
    bays lowered, mountain bands with saddles at their passes, wide gullies on slopes; the height
    grouped into benches and scarps, every level's outline cleaned (plan LANDFORM); reserved city
    rects flat;
 3. rivers: meandering, widening downstream, splitting into deltas; level in reaches with the
    drops gathered into falls, flat valley floors rising in scarps (plan RIVER_FORM), flow
    written to aux;
 4. terrain by stretch (docs/design/sets/world.md §9.3): rock, snow, scree, scrub, forest floor,
    desert, marsh, canals, beaches, margins where two bases meet;
 5. routes and lanes (worldgen.routes): roads graded with ramps, bridges, roadside kit, stations,
    farms, harbours, the graph;
 6. country (worldgen.country): fields, plants and natural props by stretch;
 7. districts: <region>/land, /sea, /road, /farm, /pasture, /reserved, and one per seam.

The base is compiled against the committed layers (like every layer): within a few tiles of an
authored layer's rect it takes that layer's edge levels and coast, so seams stay closed when the
base is regenerated after the cities were built.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from plan import world_plan as P

from . import raster, rng
from .catalog import Catalog
from .coords import COLS, ROWS
from .dsl import PIERS, Layout
from .graph import Graph
from .layer import NO_GROUND, TRANSPARENT, PlanLayer

SEED = "base"
ANCHOR_BAND = 10  # tiles over which the base blends into an authored layer's edge


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


def nearest_value(target: np.ndarray, values: np.ndarray, cap: int) -> tuple[np.ndarray, np.ndarray]:
    """(distance, value of the nearest target cell) for every cell within `cap` (else cap, 0)."""
    d = np.full(target.shape, cap, dtype=np.int16)
    v = np.zeros(target.shape, dtype=np.float64)
    d[target] = 0
    v[target] = values[target]
    reached = target.copy()
    front = target.copy()
    for k in range(1, cap):
        new_any = False
        grown_v = np.zeros_like(v)
        grown = np.zeros_like(front)
        for dr, dc in (N8 if k % 2 == 0 else N4):
            fs = _shift(front, dr, dc, False)
            vs = _shift(v, dr, dc, 0.0)
            take = fs & ~grown
            grown_v[take] = vs[take]
            grown |= fs
        new = grown & ~reached
        if new.any():
            new_any = True
            d[new] = k
            v[new] = grown_v[new]
            reached |= new
            front = new
        if not new_any:
            break
    return d, v


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


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


CC, RR = rng.grid_coords(0, 0, COLS, ROWS)


def noise(scale: float, *key, octaves: int = 3) -> np.ndarray:
    """World fbm in [-1, 1] keyed by the base seed and `key`."""
    return rng.fbm(CC, RR, scale, rng.hash64(SEED, *key), octaves=octaves) * 2 - 1


# --- anchors: the committed authored layers -------------------------------------------------

@dataclass
class Anchors:
    """What the authored layers show at their edges, spread over a band outside each rect."""

    dist: np.ndarray            # Chebyshev distance to the nearest anchored rect (0 inside)
    level: np.ndarray           # that rect's nearest edge tile's level
    water: np.ndarray           # that edge tile is sea (+1), land (0), unknown (-1)
    terrain: list = field(default_factory=list)   # (c, r, terrain id) of edge tiles' outsides
    rects: list = field(default_factory=list)
    piers: list = field(default_factory=list)     # (c, r) of the layers' jetties and moles

    def inside(self) -> np.ndarray:
        return self.dist == 0


def make_anchors(layers: dict[str, PlanLayer], cat: Catalog) -> Anchors:
    B = ANCHOR_BAND
    dist = np.full((ROWS, COLS), 99, dtype=np.int16)
    level = np.zeros((ROWS, COLS), dtype=np.int16)
    water = np.full((ROWS, COLS), -1, dtype=np.int8)
    A = Anchors(dist, level, water)
    for name in sorted(layers):
        pl = layers[name]
        c0, r0, c1, r1 = pl.c0, pl.r0, pl.c0 + pl.w - 1, pl.r0 + pl.h - 1
        A.rects.append((name, (c0, r0, c1, r1)))
        A.piers += [(c, r) for it in pl.items if it.id.split(".")[-1] in PIERS
                    for r in range(it.r, it.r + it.ph) for c in range(it.c, it.c + it.pw)]
        wc0, wr0 = max(c0 - B, 0), max(r0 - B, 0)
        wc1, wr1 = min(c1 + B, COLS - 1), min(r1 + B, ROWS - 1)
        cc, rr = CC[wr0:wr1 + 1, wc0:wc1 + 1], RR[wr0:wr1 + 1, wc0:wc1 + 1]
        ec, er = np.clip(cc, c0, c1), np.clip(rr, r0, r1)
        d = np.maximum(np.abs(cc - ec), np.abs(rr - er)).astype(np.int16)
        t = pl.T[er - r0, ec - c0]
        lv = (pl.L[er - r0, ec - c0] & 0x0F).astype(np.int16)
        sea_idx = [i for i, tid in enumerate(pl.terrains) if tid in ("world.sea", "world.shallows")]
        known = (t != TRANSPARENT) & (t != NO_GROUND)
        sub = (slice(wr0, wr1 + 1), slice(wc0, wc1 + 1))
        better = (d < dist[sub]) & (known | (d == 0))
        dist[sub] = np.where(better, d, dist[sub])
        level[sub] = np.where(better & known, lv, level[sub])
        water[sub] = np.where(better & known, np.isin(t, sea_idx).astype(np.int8),
                              np.where(better, -1, water[sub]))
        # The tiles just outside each edge, with the terrain they face across it.
        for c in range(c0, c1 + 1):
            for r_out, r_in in ((r0 - 1, r0), (r1 + 1, r1)):
                A.terrain.append((c, r_out, pl, c - c0, r_in - r0))
        for r in range(r0, r1 + 1):
            for c_out, c_in in ((c0 - 1, c0), (c1 + 1, c1)):
                A.terrain.append((c_out, r, pl, c_in - c0, r - r0))
    A.terrain = [(c, r, pl.terrains[pl.T[j, i]]) for c, r, pl, i, j in A.terrain
                 if 0 <= c < COLS and 0 <= r < ROWS and pl.T[j, i] not in (TRANSPARENT, NO_GROUND)]
    return A


# --- 1. coasts -------------------------------------------------------------------------------

def make_land(A: Anchors) -> tuple[np.ndarray, np.ndarray]:
    """Land mask and the bays noise (positive where the coast was pushed out: headlands)."""
    raw = np.zeros((ROWS, COLS), dtype=bool)
    for pts in P.LAND.values():
        raw |= poly(pts)
    for pts in P.SEA.values():
        raw &= ~poly(pts)
    inlets = np.zeros_like(raw)
    for pts in P.INLETS.values():
        inlets |= poly(pts)
    raw &= ~inlets
    isl = np.zeros_like(raw)
    for pts in P.ISLANDS.values():
        isl |= poly(pts)
    n = np.zeros((ROWS, COLS))
    bays = None
    for k, (scale, amp) in P.COAST_NOISE.items():
        x = np.clip(noise(scale, "coast", k, octaves=3) * 1.8, -1, 1)
        if bays is None:
            bays = x
        n += amp * x
    # Near authored layers the coast is theirs: no roughening within the anchor band.
    calm = smoothstep((A.dist.astype(np.float64) - 2) / ANCHOR_BAND)
    n *= calm
    n_isl = noise(7.0, "isles") * calm

    def signed(m):
        return distance_to(~m, 14).astype(np.float64) - distance_to(m, 14).astype(np.float64)

    land = (signed(raw) + n > 0) | (signed(isl) + 1.3 * n_isl > 0)
    core_land = distance_to(~(raw | isl), 3) >= 2
    core_sea = distance_to(raw | isl, 3) >= 2
    land = flood(core_land, land)
    sea = flood(core_sea | (~(raw | isl) & ~land), ~land)
    land = ~sea
    land &= ~(inlets & (distance_to(~inlets, 3) >= 1))
    # The authored layers' own edges decide land and sea just outside them.
    edge = (A.dist >= 1) & (A.dist <= 2)
    land = np.where(edge & (A.water == 1), False, np.where(edge & (A.water == 0), True, land))
    return land, bays


def islets(land: np.ndarray, A: Anchors) -> np.ndarray:
    """Rocks and islets beside the open-sea lanes (plan ISLETS): one every `every` tiles of a
    lane's plan line, `offset` tiles to a side, wherever the open sea would otherwise run on
    for screens with nothing in it; never near a coast, an authored layer or a seam."""
    F = P.ISLETS
    far = distance_to(land, F["clear"] + 1) > F["clear"]
    seams = np.zeros_like(land)
    for rid, (kind, _s, _t, rect, _b) in P.REGIONS.items():
        if kind == "seam":
            seams |= rect_mask(rect)
    near_seam = distance_to(seams, 12) < 12
    out = np.zeros_like(land)
    for lid, ln in P.LANES.items():
        if ln["kind"] != "sea":
            continue
        pts = ln["points"]
        walked = 0.0
        for (ac, ar), (bc, br) in zip(pts, pts[1:]):
            length = math.hypot(bc - ac, br - ar)
            if length == 0:
                continue
            nx, ny = -(br - ar) / length, (bc - ac) / length
            t = (F["every"] - walked % F["every"]) if walked else F["every"] / 2
            while t < length:
                k = int(walked + t)
                h = rng.hash64(SEED, "islet", lid, k)
                side = 1 if h % 2 else -1
                off = F["offset"][0] + (h >> 8) % (F["offset"][1] - F["offset"][0] + 1)
                c = int(round(ac + (bc - ac) * t / length + nx * off * side))
                r = int(round(ar + (br - ar) * t / length + ny * off * side))
                t += F["every"]
                if not (4 <= c < COLS - 4 and 4 <= r < ROWS - 4) or not far[r, c] or \
                        near_seam[r, c] or A.dist[r, c] <= ANCHOR_BAND + 4:
                    continue
                rad = F["radius"][0] + ((h >> 16) % 100) / 100 * (F["radius"][1] - F["radius"][0])
                win = (slice(r - 4, r + 5), slice(c - 4, c + 5))
                wob = noise(3.0, "islet_shape")[win] * 0.9
                out[win] |= np.hypot(CC[win] - c, RR[win] - r) + wob <= rad
            walked += length
    return out


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
    # Tiles no rule names take the region of the nearest named tile of their kind (sea or land),
    # so a stray bay never carries a far sea's id (and its theme and art pages).
    for target in (reg, stretch):
        for kind in (land, ~land):
            for _ in range(256):
                todo = (target < 0) & kind
                if not todo.any():
                    break
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    src = np.roll(np.roll(target, dr, axis=0), dc, axis=1)
                    srck = np.roll(np.roll(kind, dr, axis=0), dc, axis=1)
                    take = todo & (src >= 0) & srck & (target < 0)
                    target[take] = src[take]
        # An islet no land rule names takes the region of the water round it (a rock in the Gulf
        # belongs to the Gulf, its climate and its art), never a far sea's.
        for _ in range(64):
            todo = target < 0
            if not todo.any():
                break
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                src = np.roll(np.roll(target, dr, axis=0), dc, axis=1)
                take = todo & (src >= 0) & (target < 0)
                target[take] = src[take]
        target[target < 0] = idx["tyrrhenian"]
    stretch[rect_mask(P.REGIONS["corner"][3]) & land] = corner
    return reg, names, stretch


def town_rects_mask() -> np.ndarray:
    m = np.zeros((ROWS, COLS), dtype=bool)
    for kind, _s, _t, rect, _b in P.REGIONS.values():
        if kind in ("town", "city", "home"):
            m |= rect_mask(rect)
    return m


# --- rivers ----------------------------------------------------------------------------------

@dataclass
class Course:
    id: str
    path: list            # 4-connected tiles, source to mouth
    widths: list          # width per path tile
    mask: np.ndarray      # water tiles of this river (on land)
    flow: dict            # tile -> aux flow direction
    valley: int
    delta_land: np.ndarray | None = None
    sink: bool = False


def _flow_of(dc: int, dr: int) -> int:
    """Aux flow enum from a plan step: 0 = -y (east), 1 = +x (south), 2 = +y (west), 3 = -x."""
    if abs(dc) >= abs(dr):
        return 0 if dc > 0 else 2
    return 1 if dr > 0 else 3


def meander(points, amount: float, key: str, near_town: np.ndarray) -> list[tuple[int, int]]:
    """A sinuous course through the plan's points: a sine of noisy wavelength, fading out at the
    plan's own vertices (towns and mouths stay where the plan puts them) and near town rects."""
    s = rng.hash64(SEED, "meander", key)
    out: list[tuple[float, float]] = []
    total = 0.0
    for (ac, ar), (bc, br) in zip(points, points[1:]):
        length = math.hypot(bc - ac, br - ar)
        if length == 0:
            continue
        nx, ny = -(br - ar) / length, (bc - ac) / length
        n = max(1, int(length))
        for i in range(n):
            t = i / n
            x, y = ac + (bc - ac) * t, ar + (br - ar) * t
            along = total + length * t
            wave = 16.0 + 6.0 * rng.fbm(np.array(along), np.array(0.5), 40.0, s, octaves=1).item()
            phase = 2 * math.pi * along / wave
            jitter = (rng.fbm(np.array(x), np.array(y), 11.0, s ^ 0x55, octaves=2).item() - 0.5)
            taper = min(1.0, min(t, 1 - t) * length / 5.0)
            ci, ri = int(round(x)), int(round(y))
            if 0 <= ci < COLS and 0 <= ri < ROWS and near_town[ri, ci]:
                taper = 0.0
            off = amount * taper * (math.sin(phase) * 0.8 + jitter * 0.8)
            out.append((x + nx * off, y + ny * off))
        total += length
    out.append(tuple(points[-1]))
    pts = []
    for x, y in out:
        p = (int(round(x)), int(round(y)))
        if not pts or pts[-1] != p:
            pts.append(p)
    return raster.path_tiles(pts)


def plan_rivers(land: np.ndarray) -> list[Course]:
    near_town = distance_to(town_rects_mask(), 7) < 7
    courses = []
    for rid, rv in P.RIVERS.items():
        path = meander(rv["points"], rv.get("meander", 1) * 1.6, rid, near_town)
        path = [(c, r) for c, r in path if 0 <= c < COLS and 0 <= r < ROWS]
        if rv.get("delta"):
            # Stop the main course at the first sea tile; the branches fan out from inland.
            for i, (c, r) in enumerate(path):
                if not land[r, c]:
                    path = path[:i + 1]
                    break
        w0 = rv["width"]
        n = len(path)
        widths = [max(1, int(round(w0 * (0.5 + 0.5 * i / max(n - 1, 1))))) for i in range(n)]
        mask = np.zeros((ROWS, COLS), dtype=bool)
        flow: dict = {}
        _paint_course(path, widths, mask, flow)
        delta_land = None
        if rv.get("delta"):
            dl, br = rv["delta"]
            delta_land = np.zeros_like(mask)
            _delta(rid, path, widths, dl, br, land, mask, flow, delta_land)
        mask &= land | (distance_to(land, 2) <= 1)
        courses.append(Course(rid, path, widths, mask, flow, rv.get("valley", 3), delta_land,
                              bool(rv.get("sink"))))
    return courses


def _paint_course(path, widths, mask, flow) -> None:
    for i, (c, r) in enumerate(path):
        nc, nr = path[min(i + 1, len(path) - 1)]
        pc, pr = path[max(i - 1, 0)]
        f = _flow_of(nc - pc, nr - pr)
        w = widths[i]
        a = (w - 1) // 2
        for rr in range(r - a, r - a + w):
            for cc in range(c - a, c - a + w):
                if 0 <= rr < ROWS and 0 <= cc < COLS:
                    mask[rr, cc] = True
                    flow.setdefault((cc, rr), f)


def _delta(rid, path, widths, length, branches, land, mask, flow, delta_land) -> None:
    """Distributaries fanning out over the last `length` tiles, marsh and sand between them."""
    if len(path) < length + 2:
        return
    src = path[-length - 1]
    mouth = path[-1]
    dc, dr = mouth[0] - src[0], mouth[1] - src[1]
    ll = math.hypot(dc, dr) or 1.0
    ux, uy = dc / ll, dr / ll
    px, py = -uy, ux
    spread = length * 0.7
    st = rng.stream(SEED, "delta", rid)
    ends = [mouth]
    for b in range(1, branches):
        side = 1 if b % 2 else -1
        k = (b + 1) // 2
        ex = mouth[0] + px * spread * side * k / max(1, branches // 2) + ux * 2
        ey = mouth[1] + py * spread * side * k / max(1, branches // 2) + uy * 2
        mid = (src[0] + (ex - src[0]) * 0.5 + px * side * st.randint(0, 2),
               src[1] + (ey - src[1]) * 0.5 + py * side * st.randint(0, 2))
        pts = [src, (int(round(mid[0])), int(round(mid[1]))), (int(round(ex)), int(round(ey)))]
        bp = [(c, r) for c, r in raster.path_tiles(pts) if 0 <= c < COLS and 0 <= r < ROWS]
        # Carry on straight until the branch reaches the sea.
        c, r = bp[-1] if bp else src
        for _ in range(8):
            if not land[r, c]:
                break
            c, r = int(round(c + ux)), int(round(r + uy))
            if not (0 <= c < COLS and 0 <= r < ROWS):
                break
            bp += raster.path_tiles([bp[-1], (c, r)])[1:]
        bw = max(1, widths[-1] - 1)
        _paint_course(bp, [bw] * len(bp), mask, flow)
        ends.append(bp[-1] if bp else mouth)
    hull = [src] + sorted(ends, key=lambda e: (e[0] - src[0]) * px + (e[1] - src[1]) * py)
    delta_land |= raster.poly_mask(hull, 0, 0, COLS, ROWS) & land & ~mask


# --- 2. relief -------------------------------------------------------------------------------

def relief(land, stretch, names, bays, courses, A: Anchors):
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
    wc = noise(30.0, "warp_c") * 16
    wr = noise(30.0, "warp_r") * 16
    ic = np.clip(np.rint(CC + wc), 0, COLS - 1).astype(np.intp)
    ir = np.clip(np.rint(RR + wr), 0, ROWS - 1).astype(np.intp)
    plateau, ramp, amp = (box_blur(box_blur(x[ir, ic], 10), 10) for x in (plateau, ramp, amp))
    hills = noise(P.LANDFORM["hills_scale"], "hills", octaves=4)
    lv = 1 + np.minimum(plateau - 1, dist / ramp) + amp * hills * np.clip(dist / 6, 0, 1)
    # Headlands stand up from the sea, bays stay low with beaches.
    shore = np.clip(1 - dist / 6.0, 0, 1)
    lv += np.clip(bays, 0, 1) * 2.6 * shore
    lv = np.where((bays < -0.15) & (dist <= 4), np.minimum(lv, 1 + dist * 0.35), lv)
    bandsoft = np.zeros((ROWS, COLS))
    imp = np.zeros((ROWS, COLS), dtype=bool)
    for bid, b in P.BANDS.items():
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
        passable = np.zeros_like(m)
        for (pc, pr), radius, saddle in b.get("passes", []):
            dpass = np.hypot(cc - pc, rc - pr) / radius
            cap = saddle + np.clip(dpass - 0.35, 0, None) * (hi - saddle) * 1.6
            blv = np.minimum(blv, cap)
            passable |= dpass < 1.0
        lw = lv[win]
        lv[win] = np.where(soft > 0, np.maximum(lw, lw * (1 - soft) + blv * soft), lw)
        for (pc, pr), radius, saddle in b.get("passes", []):
            dpass = np.hypot(cc - pc, rc - pr) / radius
            lv[win] = np.where(dpass < 1.0, np.minimum(lv[win], saddle + dpass * 1.5), lv[win])
        bandsoft[win] = np.maximum(bandsoft[win], soft)
        bi = (soft > 0.6) & (blv * soft >= b["impassable"]) & ~passable
        imp[win] |= bi
    # Gullies: wide ridged-noise valleys cut where the ground slopes.
    g = P.GULLIES
    sm = box_blur(lv, 3)
    gy, gx = np.gradient(sm)
    slope = np.clip(np.hypot(gx, gy) * 2.5, 0, 1)
    ridged = (1 - np.abs(noise(g["scale"], "gully", octaves=3))) ** g["sharp"]
    lv -= g["depth"] * ridged * slope * np.clip(lv - 1.5, 0, 1)
    # Authored layers' edges: blend into their levels over the anchor band, where the benches
    # fade into plain rounding so the edge level holds exactly.
    has = (A.dist >= 1) & (A.dist <= ANCHOR_BAND) & (A.water != 1)
    w = smoothstep((A.dist.astype(np.float64) - 1) / ANCHOR_BAND)
    lv = np.where(has, A.level * (1 - w) + lv * w, lv)
    # Mountain bands are benched more loosely, so their summits keep their levels.
    calm = np.where(A.dist <= ANCHOR_BAND, w, 1.0) * (1 - 0.6 * np.clip(bandsoft * 1.5, 0, 1))
    level = terraced(lv, land, calm)

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
    fixed = (A.dist <= 1) | np.any([m for m, _ in flat], axis=0)
    clean(level, land, fixed)
    imp &= ~reserved
    river, water_level, floor = river_levels(level, land, courses, A)
    limit_steps(level, land)
    flatten()
    level[river] = np.minimum(level[river], water_level[river])
    clean(level, land, fixed | river | floor)
    limit_steps(level, land)
    level[river] = np.minimum(level[river], water_level[river])
    unpimple(level, land & ~river & ~fixed)
    ring = (A.dist == 1) & land & (A.water == 0) & ~river
    level[ring] = A.level[ring]
    flow = np.zeros((ROWS, COLS), dtype=np.int8)
    for co in courses:
        for (c, r), f in co.flow.items():
            if river[r, c]:
                flow[r, c] = f
    fix_flow(level, river, flow)
    imp &= ~river
    imp |= land & (level >= 13) & ~reserved
    return level, imp, river, flow, reserved, bandsoft


def terraced(h: np.ndarray, land: np.ndarray, calm: np.ndarray) -> np.ndarray:
    """Integer levels from the continuous height, grouped into benches (plan LANDFORM): within
    each bench the riser takes only a share of the run, so the steps of a slope gather into one
    scarp. `calm` (0..1) widens the riser back to plain rounding (0) near authored edges."""
    F = P.LANDFORM
    B = F["bench"]
    # A phase and the same phase plus one bench give the same benches, so it wraps freely.
    phase = np.mod((noise(F["phase_scale"], "bench_phase", octaves=2) + 1) * 2 * B, B)
    x = (h - 1 + phase) / B
    k = np.floor(x)
    rw = F["riser"] + (1 - F["riser"]) * (1 - np.clip(calm, 0, 1))
    f = np.clip((x - k - 0.5) / rw + 0.5, 0, 1)
    h2 = (k + f) * B - phase + 1
    return np.where(land, np.clip(np.rint(h2), 1, 15), 0).astype(np.int16)


def dilate(m: np.ndarray, r: int) -> np.ndarray:
    """Grow a mask by r tiles, alternating 4- and 8-neighbour steps (an octagon, not a box)."""
    for k in range(r):
        g = m.copy()
        for dr, dc in (N4 if k % 2 == 0 else N8):
            g |= _shift(m, dr, dc, False)
        m = g
    return m


def erode(m: np.ndarray, r: int) -> np.ndarray:
    return ~dilate(~m, r)


def clean(level: np.ndarray, land: np.ndarray, fixed: np.ndarray) -> None:
    """Every level's outline opened and closed (plan LANDFORM `open`): no spur, island, notch or
    hole narrower than 2 * open + 1 tiles; a bench narrower than `min_bench` joins the level
    above it (one taller scarp instead of two steps). Outlines stay nested; `fixed` tiles keep
    their level. The sea counts as neither high nor low ground, so headlands keep their rims."""
    F = P.LANDFORM
    r, wb = F["open"], F["min_bench"]
    out = np.where(land, 1, 0).astype(np.int16)
    prev = land.copy()
    for k in range(2, 16):
        raw = land & (level >= k)
        if not raw.any() and not (fixed & (level >= k)).any():
            break
        m = dilate(erode(raw | ~land, r), r) & land
        m = erode(dilate(m, r), r) & land
        m &= prev
        if m.any():
            # A bench too narrow to stand on joins the scarp above it; the joined edge is
            # opened once more so it leaves no single-tile teeth.
            m |= prev & ~m & (distance_to(~prev, wb + 1) + distance_to(m, wb + 1) <= wb)
            m = dilate(erode(m | ~land, 1), 1) & prev
        m = (m | (fixed & (level >= k))) & ~(fixed & (level < k)) & land
        out[m] = k
        prev = m
    level[:] = out


def unpimple(level: np.ndarray, free: np.ndarray) -> None:
    """A tile above or below four neighbours that share one level takes theirs (V14)."""
    for _ in range(3):
        n = _shift(level, 1, 0, -1)
        same = (n >= 0) & (n == _shift(level, -1, 0, -1)) & (n == _shift(level, 0, 1, -1)) & \
            (n == _shift(level, 0, -1, -1)) & (n != level) & free
        if not same.any():
            return
        level[same] = n[same]


def limit_steps(level: np.ndarray, land: np.ndarray) -> None:
    """No land tile more than LANDFORM `max_step` levels above its lowest 4-neighbour (lowering
    only, so rivers and coasts are never raised)."""
    top = P.LANDFORM["max_step"]
    for _ in range(16):
        lim = level.copy()
        for dr, dc in N4:
            lim = np.minimum(lim, _shift(level, dr, dc, 15) + top)
        lim = np.where(land, np.maximum(lim, 1), 0)
        if (lim == level).all():
            return
        level[:] = lim


def river_levels(level, land, courses, A: Anchors):
    """Each river's water level along its course and its valley (plan RIVER_FORM): level for at
    least `reach` tiles; where the ground falls faster, the drops ahead within one reach gather
    into one fall here; inside an authored layer the layer's water level holds and caps the
    river below it. Land within a third of the river's `valley` takes the water's level (a flat
    floor), then rises at most two levels a tile to the country. Returns (river tiles, water
    level per tile, valley floor tiles); delta land lies flat at its river's mouth level."""
    reach = P.RIVER_FORM["reach"]
    water = np.full((ROWS, COLS), 99, dtype=np.int16)
    river = np.zeros((ROWS, COLS), dtype=bool)
    floor = np.zeros((ROWS, COLS), dtype=bool)
    for co in courses:
        seq = []
        for (c, r) in co.path:
            if A.dist[r, c] == 0:
                seq.append((c, r, int(A.level[r, c]), True))
                continue
            if not land[r, c]:
                break
            seq.append((c, r, int(level[r, c]), False))
        if not seq:
            continue
        caps = np.minimum.accumulate(np.array([s[2] for s in seq]))
        fixed = [s[3] for s in seq]
        z = np.zeros(len(seq), dtype=np.int16)
        cur = int(caps[0])
        for i in range(len(seq)):
            if fixed[i]:
                cur = int(caps[i])
            elif caps[i] < cur:
                # Gather the drops of the next reach, short of an authored layer ahead (the
                # river meets it at its own level there).
                j = i + 1
                while j < min(len(seq), i + reach) and not fixed[j]:
                    j += 1
                cur = int(caps[i:j].min())
            z[i] = cur
        if co.delta_land is not None:
            # A delta lies low and flat: its reach is at the shore's level from where it forks.
            fork = max(0, len(seq) - P.RIVERS[co.id]["delta"][0])
            z[fork:] = np.where(np.array(fixed[fork:]), z[fork:], np.minimum(z[fork:], 1))
        free = [i for i in range(len(seq)) if not fixed[i]]
        on = co.mask & land & (A.dist > 0)
        if not free or not on.any():
            continue
        # Every tile within the river's half-width of a path tile takes the lowest level of
        # the path tiles that reach it, so a fall crosses the whole width on one line instead
        # of leaving slivers of the upper reach beside the lower one.
        mine = np.full((ROWS, COLS), 99, dtype=np.int16)
        for i in free:
            c, r = seq[i][0], seq[i][1]
            rad = co.widths[min(i, len(co.widths) - 1)] // 2 + 1
            win = (slice(max(r - rad, 0), r + rad + 1), slice(max(c - rad, 0), c + rad + 1))
            mine[win] = np.minimum(mine[win], z[i])
        keys = np.array([(seq[i][0], seq[i][1]) for i in free])
        vals = z[free]
        js, is_ = np.nonzero(on & (mine == 99))
        for j, i in zip(js.tolist(), is_.tolist()):
            k = int(np.argmin(np.abs(keys[:, 0] - i) + np.abs(keys[:, 1] - j)))
            mine[j, i] = int(vals[k])
        water[on] = np.minimum(water[on], mine[on])
        river |= on
        if co.delta_land is not None:
            dl = co.delta_land & land & (A.dist > 0)
            level[dl] = np.minimum(level[dl], max(int(z[-1]), 1))
            floor |= dl
        if co.valley > 0:
            dv, wl = nearest_value(on, water.astype(np.float64), co.valley + 1)
            near = (dv <= co.valley) & land & ~on & (A.dist > 0)
            fw = max(1, co.valley // 3)
            allowed = wl + np.maximum(0, dv - fw) * 2
            level[near] = np.minimum(level[near], np.maximum(allowed[near], 1)).astype(np.int16)
            floor |= near & (dv <= fw)
    level[river] = np.minimum(level[river], water[river])
    return river, water, floor


def fix_flow(level, river, flow) -> None:
    """Lower any river tile that sits above the river tile flowing into it, until stable."""
    steps = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}  # aux -> (dr, dc)
    for _ in range(300):
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



# --- 4. terrain ------------------------------------------------------------------------------

@dataclass
class World:
    """Everything the later steps (routes, country, districts) read from the generated land."""

    L: Layout
    cat: Catalog
    land: np.ndarray
    reg: np.ndarray
    names: list
    stretch: np.ndarray
    reserved: np.ndarray
    river: np.ndarray
    level: np.ndarray
    bandsoft: np.ndarray
    forest: np.ndarray = None
    bare: np.ndarray = None
    coast: np.ndarray = None
    marsh: np.ndarray = None
    road: np.ndarray = None
    farm: np.ndarray = None
    pasture: np.ndarray = None
    anchors: Anchors = None
    blocked: np.ndarray = None
    keep: np.ndarray = None     # door steps and work spots of placed kit: nothing stands there
    stats: dict = field(default_factory=dict)

    def tidx(self, t: str) -> int:
        return self.L._terrain_index(t, "plan/world_plan.py")

    def biome(self, i: int) -> dict:
        return P.BIOMES.get(self.names[i], {})


def terrain(W: World) -> None:
    L, land, level, reserved = W.L, W.land, W.level, W.reserved
    terr = np.zeros((ROWS, COLS), dtype=np.int16)
    forest_n = noise(26.0, "forest", octaves=4)
    rocky = noise(6.0, "rockiness")
    patch = noise(9.0, "patches")
    W.forest = np.zeros((ROWS, COLS), dtype=bool)
    rock = np.zeros_like(land)
    snow = np.zeros_like(land)
    scree = np.zeros_like(land)
    scrub = np.zeros_like(land)
    floor = np.zeros((ROWS, COLS), dtype=np.int16) - 1
    desert = np.zeros_like(land)
    gravel = np.zeros_like(land)
    dune = np.zeros_like(land)
    dist_sea = distance_to(~land, 8)
    hillness = level - box_blur(level, 6)
    for i, n in enumerate(W.names):
        m = (W.stretch == i) & land
        if not m.any():
            continue
        b = W.biome(i)
        terr[m] = W.tidx(b.get("base", "world.steppe"))
        free = m & ~reserved & ~W.river
        if b.get("rock"):
            rock |= free & (((level >= b["rock"] + 1) & (rocky > -0.3)) |
                            ((level >= b["rock"]) & (rocky > 0.25)))
        if b.get("snow"):
            snow |= free & (level >= b["snow"]) & (rocky > -0.4)
        scree |= free & (W.bandsoft > 0.25) & (W.bandsoft < 0.7) & (rocky > 0.18)
        if b.get("scrub"):
            hills = free & ((hillness > 0.3) | (level >= 3))
            if hills.sum() > 50:
                thr = np.quantile(patch[hills], 1 - b["scrub"])
                scrub |= hills & (patch >= thr)
        share = b.get("forest", 0)
        if share > 0 and free.sum() > 50:
            thr = np.quantile(forest_n[free], 1 - share)
            fm = free & (forest_n >= thr) & (level <= 11)
            W.forest |= fm
            if b.get("floor"):
                floor[fm & (forest_n >= thr + 0.04)] = W.tidx(b["floor"])
        if b.get("desert_from"):
            edge = b["desert_from"] + noise(14.0, "desert") * 6
            desert |= m & (RR > edge + 4)
            gravel |= m & (RR > edge) & (RR <= edge + 4)
            dune |= m & (RR > edge + 4) & (patch > 0.35)
    for rid, base in P.RESERVED_BASE.items():
        terr[rect_mask(P.REGIONS[rid][3]) & land] = W.tidx(base)
    terr[desert] = W.tidx("world.sand")
    terr[gravel & ~reserved] = W.tidx("world.gravel_desert")
    terr[dune & ~reserved] = W.tidx("world.dune")
    fl = floor >= 0
    terr[fl] = floor[fl]
    terr[scrub & ~W.forest] = W.tidx("world.scrub")
    terr[scree & ~rock] = W.tidx("world.scree")
    terr[rock] = W.tidx("world.rock")
    terr[snow] = W.tidx("world.snow")
    W.bare = rock | snow
    # Marsh: deltas, sinks, the low river banks of the south, the Pontine shore.
    dist_river = distance_to(W.river, 8)
    marsh = np.zeros_like(land)
    marsh_n = noise(5.0, "marsh")
    for co in W_courses(W):
        if co.delta_land is not None:
            marsh |= co.delta_land & (marsh_n > -0.4)
        if co.sink:
            end = co.path[-1]
            marsh |= (np.hypot(CC - end[0], RR - end[1]) < 4.5) & land & ~W.river
    for i, n in enumerate(W.names):
        if W.biome(i).get("marsh"):
            m = (W.stretch == i) & land & ~reserved & ~W.river
            marsh |= m & (dist_river <= 3) & (level <= 1) & (marsh_n > 0.15) & (RR > 330)
    marsh |= rect_mask((256, 226, 300, 252)) & land & (dist_sea <= 3) & (marsh_n > -0.1)
    marsh &= ~reserved & ~W.bare
    terr[marsh] = W.tidx("world.marsh")
    W.marsh = marsh
    # Beaches: a strip of dunes along low bay shores.
    beach = land & (dist_sea <= 1) & (level <= 1) & ~reserved & ~W.river & ~marsh & \
        (noise(12.0, "beach") > -0.1)
    terr[beach] = W.tidx("world.dune")
    W.coast = land & (dist_sea <= 2)
    L.T[:] = terr
    canals(W)
    margins(W)


def W_courses(W: World):
    return W.stats.get("_courses", [])


def canals(W: World) -> None:
    """Irrigation canals on the flat alluvium: straight 1-tile cuts off the rivers, every few
    rows, kept only where they draw from a river (docs/design/sets/world.md §9.3)."""
    L, land = W.L, W.land
    dist_river = distance_to(W.river, 30)
    out = np.zeros_like(land)
    for i, n in enumerate(W.names):
        spec = W.biome(i).get("canals")
        if not spec:
            continue
        every, keep = spec
        m = (W.stretch == i) & land & ~W.reserved & ~W.river & (W.level == 1) & \
            (dist_river >= 1) & (dist_river <= 26)
        off = (rng.hash01(CC // 24, RR // every, rng.hash64(SEED, "canal_off")) * every).astype(int)
        line = ((RR % every) == off) & (noise(10.0, "canal") > -keep)
        out |= m & line
    # Keep only canal pieces that touch a river.
    touch = out & (distance_to(W.river, 2) <= 1)
    out = flood(touch, out)
    if out.any():
        L.T[out] = W.tidx("world.river")
        L.AUX[out] = 0  # level water: the flow streaks just run east
        W.river |= out
        W.stats["canal_tiles"] = int(out.sum())


def margins(W: World) -> None:
    """Two base terrains never touch (V8): where they do, one side becomes its margin overlay
    (plan MARGIN), in a ragged band, so the meeting reads as a worn edge. The same against the
    authored layers' edge tiles."""
    L, cat = W.L, W.cat
    isbase = np.array([bool(cat.terrain.get(t) and cat.terrain[t].base) for t in L.terrains]
                      + [False])
    T = np.where(W.land, L.T, len(L.terrains))
    T = np.where(T < 0, len(L.terrains), T)
    b = isbase[T]
    conflict = np.zeros_like(W.land)
    right = b[:, 1:] & b[:, :-1] & (T[:, 1:] != T[:, :-1])
    conflict[:, 1:] |= right
    conflict[:, :-1] |= right
    down = b[1:, :] & b[:-1, :] & (T[1:, :] != T[:-1, :])
    conflict[1:, :] |= down
    conflict[:-1, :] |= down
    for c, r, tid in W.anchors.terrain:
        t = cat.terrain.get(tid)
        if t and t.base and b[r, c] and L.terrains[T[r, c]] != tid:
            conflict[r, c] = True
    # Grow the band a little where noise says so, then give each tile its own margin.
    wide = conflict | ((distance_to(conflict, 3) <= 1) & (noise(4.0, "margin") > 0.2) & b)
    js, is_ = np.nonzero(wide & b)
    for j, i in zip(js.tolist(), is_.tolist()):
        tid = L.terrains[T[j, i]]
        L.T[j, i] = W.tidx(P.MARGIN.get(tid, "world.scrub"))


def water_and_faces(W: World, flow: np.ndarray) -> None:
    L, cat, land = W.L, W.cat, W.land
    river = W.river
    natural = river & (L.T != W.tidx("world.river"))
    L.T[natural] = W.tidx("world.river")
    L.AUX[natural] = flow[natural]
    sea = ~land
    dland = distance_to(land, 8)
    depth = np.select([dland <= 1, dland <= 3, dland <= 6], [0, 1, 2], 3).astype(np.int8)
    L.T[sea] = W.tidx("world.sea")
    L.AUX[sea] = depth[sea]
    low = land & (W.level <= 1)
    near_low = distance_to(low, 3) <= 2
    shallows = sea & near_low & (dland <= 2)
    L.T[shallows] = W.tidx("world.shallows")
    L.AUX[shallows] = 0
    # Canals join the rivers at the rivers' level: no water runs up into them.
    fix_flow(L.LV, river, L.AUX)
    # Faces: raised land at the sea uses its terrain's coast material, high ground rock.
    coast = land & (distance_to(sea, 2) <= 1) & (W.level >= 2)
    high = land & ~coast & (W.level >= 7)
    for t, tid in enumerate(L.terrains):
        faces = cat.faces(tid)
        # A sea cliff of a terrain without a coast face shows its rock, never a bank of earth.
        cliff = next((f for f in faces if f == "world.coast"), None) or \
            next((f for f in faces if f.endswith((".rock", ".tufa"))), None)
        for m, material in ((coast, cliff), (high, "world.rock")):
            if material in faces:
                mt = m & (L.T == t)
                L.AUX[mt] = faces.index(material)


# --- districts -------------------------------------------------------------------------------

def districts(W: World) -> None:
    L, land, reg = W.L, W.land, W.reg
    src = "plan/world_plan.py"
    d = np.zeros((ROWS, COLS), dtype=np.int16)
    for i, n in enumerate(W.names):
        kind = P.REGIONS[n][0]
        m_land = (reg == i) & land
        m_sea = (reg == i) & ~land
        if not (m_land | m_sea).any():
            continue
        if kind in ("city", "town", "home"):
            d[m_land | m_sea] = L._dist_index(f"{n}/reserved", src)
        elif kind == "seam":
            d[m_land | m_sea] = L._dist_index(f"{n}/mist", src)
        else:
            if m_land.any():
                d[m_land] = L._dist_index(f"{n}/land", src)
            if m_sea.any():
                d[m_sea] = L._dist_index(f"{n}/sea", src)
            for mask, part in ((W.pasture, "pasture"), (W.farm, "farm"), (W.road, "road")):
                if mask is None:
                    continue
                mm = m_land & mask
                if mm.any():
                    d[mm] = L._dist_index(f"{n}/{part}", src)
    L.DIST[:] = d


# --- the build -------------------------------------------------------------------------------

def build_base(cat: Catalog, layers: dict[str, PlanLayer] | None = None) -> tuple[Layout, Graph, dict]:
    from . import country, routes
    anchors = make_anchors(layers or {}, cat)
    land, bays = make_land(anchors)
    isle = islets(land, anchors)
    land |= isle
    reg, names, stretch = region_map(land)
    courses = plan_rivers(land)
    level, imp, river, flow, reserved, bandsoft = relief(land, stretch, names, bays, courses,
                                                         anchors)
    L = Layout(layer="base", region="base", set="world", origin=(0, 0), size=(COLS, ROWS),
               base_level=0, catalog=cat, regions=list(P.REGIONS), source="plan/world_plan.py")
    L.LV[:] = level
    L.IMP[:] = imp
    W = World(L, cat, land, reg, names, stretch, reserved, river, L.LV, bandsoft,
              anchors=anchors)
    W.stats["_courses"] = courses
    W.keep = np.zeros((ROWS, COLS), dtype=bool)
    terrain(W)
    L.T[isle] = W.tidx("world.rock")   # bare rock: gulls, not farms
    water_and_faces(W, flow)
    g = Graph("base")
    routes.build(W, g)
    routes.lanes(W, g)
    country.place(W)
    districts(W)
    drop_unreached_kit(W, g, layers or {})
    W.stats.pop("_courses")
    W.stats["land_tiles"] = int(land.sum())
    W.stats["items"] = sum(1 for p in L.items if not p.removed)
    return L, g, W.stats


# Base kit the graph names (relay stations: their nodes), and kit that is the way itself, stays
# whatever the walk check says; the validators report it instead.
KEEP_KIT = ("world.royal_station", "rome.mutatio")


def drop_unreached_kit(W: World, g: Graph, layers: dict[str, PlanLayer]) -> None:
    """Take out base kit (folds, wells, shrines, graves, towers) that walkers cannot use by the
    engine's own walk model over the composed world: a walk tile or slot spot no graph reaches
    (W-W5, W-L2), or a spot another item covers (W-L1). Placement checks reach by its own
    simpler rules; this is the last word, so the base never ships a sealed fold."""
    from . import compiler, compose, walkable
    L, cat = W.L, W.cat
    removed: dict[str, int] = {}
    for _ in range(4):
        pl, _issues = compiler.compile_layer(L)
        seq = [(n, pl if n == "base" else layers[n]) for n, _r, _g in P.LAYERS
               if n == "base" or n in layers]
        world = compose.compose(seq)
        by_pos = {(p.id, p.c, p.r): p for p in L.items if not p.removed}
        drop = set()
        for f in walkable.scan(world, cat, {"base": g}):
            if f.code not in ("W-W5", "W-L1", "W-L2") or f.index < 0:
                continue
            it = world.items[f.index]
            d = cat.items.get(it.id)
            if it.layer != "base" or d is None or it.id in KEEP_KIT or d.rise or d.walkable \
                    or d.landmark:
                continue
            p = by_pos.get((it.id, it.c, it.r))
            if p is not None:
                drop.add(p.index)
        if not drop:
            break
        for i in sorted(drop):
            L._remove(L.items[i])
            removed[L.items[i].id] = removed.get(L.items[i].id, 0) + 1
    W.stats["unwalkable_removed"] = dict(sorted(removed.items()))
