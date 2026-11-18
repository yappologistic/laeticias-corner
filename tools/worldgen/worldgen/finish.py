"""Layout helpers every region uses: orthogonal ways, detail that gives way, fords, and the
finishing passes run at the end of a layout (door steps, glow budget, face materials, seams).

They only call the public layout API plus the layout's own arrays, so a region's result is the
same whether it writes these steps itself or calls them here.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from . import rng
from .coords import COLS, ROWS
from .dsl import Layout
from .shapes import Line, Mask, Rect


def orth(points):
    """A polyline turned into axis-parallel runs: a diagonal step becomes a jog at its middle.
    Lanes then wander in steps (as they read in isometric view), and every street tile, crossing
    and graph edge lies exactly on the painted way."""
    out = [tuple(points[0])]
    for (c0, r0), (c1, r1) in zip(points, points[1:]):
        if c0 != c1 and r0 != r1:
            if abs(c1 - c0) >= abs(r1 - r0):
                m = (c0 + c1) // 2
                out += [(m, r0), (m, r1)]
            else:
                m = (r0 + r1) // 2
                out += [(c0, m), (c1, m)]
        out.append((c1, r1))
    pts = [p for i, p in enumerate(out) if i == 0 or p != out[i - 1]]
    keep = [pts[0]]
    for a, b in zip(pts[1:], pts[2:] + [None]):
        if b is not None and (keep[-1][0] == a[0] == b[0] or keep[-1][1] == a[1] == b[1]):
            continue
        keep.append(a)
    return keep


def stairstep(points, run: int = 3):
    """A diagonal polyline as small alternating axis runs of about `run` tiles, so a wide way
    can cross a square on the diagonal while every graph edge stays on its painted tiles."""
    out = [tuple(points[0])]
    for (c0, r0), (c1, r1) in zip(points, points[1:]):
        dc, dr = c1 - c0, r1 - r0
        n = max(1, max(abs(dc), abs(dr)) // run)
        for k in range(1, n + 1):
            ca, ra = out[-1]
            cb, rb = c0 + round(dc * k / n), r0 + round(dr * k / n)
            if ca != cb and ra != rb:
                out.append((cb, ra))
            if (cb, rb) != out[-1]:
                out.append((cb, rb))
    return orth(out)


def put(L: Layout, item: str, at, face: str = "west", variant: int = 0):
    """Detail that gives way to anything already there."""
    if L.fits(item, at, face, variant):
        return L.place(item, at=at, face=face, variant=variant)
    return None


def free(L: Layout, rect: Rect) -> Mask:
    """Tiles of a rect (local) with nothing placed and no street."""
    j0, i0 = rect.r0, rect.c0
    occ = L.OCC[j0:rect.r1 + 1, i0:rect.c1 + 1] < 0
    st = ~L.STREET[j0:rect.r1 + 1, i0:rect.c1 + 1]
    return Mask(rect.c0, rect.r0, occ & st)


def fords(L: Layout, streets, item: str = "world.ford") -> None:
    """A walkable deck (ford or slab bridge) on every water tile a way crosses, on the way's own
    line only: connect decks run along one axis, so a wide street narrows to one tile over the
    water (two lanes of decks would draw a hollow frame)."""
    seen = set()
    for s in streets:
        for c, r in Line(s.points, 1).tiles():
            t = L.terrain_at(c, r)
            if (c, r) in seen or t is None or not L.cat.is_water(t):
                continue
            seen.add((c, r))
            L.place(item, at=(c - L.origin[0], r - L.origin[1]))


FOOT_FACE = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}
DECKS = ("world.bridge_arch", "world.bridge_timber", "world.pontoon", "world.ford")


def landings(L: Layout) -> list[str]:
    """Where a street meets a deck over water a level below it (a river sunk below its banks:
    the kit's end pieces ramp down to the water's level), the street steps down to the deck: a
    ramp on four straight street tiles, else a two-tile stone stair, the foot on the deck's end.
    Returns the ends it could not join, for the report."""
    left = []
    for p in list(L.items):
        if p.removed or p.id not in DECKS:
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = L._local(p.c + dc, p.r + dr)
            if nxt is not None and L.OCC[nxt] >= 0 and L.items[L.OCC[nxt]].id == p.id:
                continue  # the run goes on that way
            low = int(L.LV[L._local(p.c, p.r)])
            line = [(p.c + dc * k, p.r + dr * k) for k in range(1, 6)]
            loc = [L._local(*t) for t in line]
            if loc[0] is None or not L.STREET[loc[0]] or int(L.LV[loc[0]]) != low + 1:
                continue
            for item, n in (("world.ramp", 4), ("world.stair_stone", 2)):
                run, head = loc[:n], loc[n] if n < len(loc) else None
                if head is None or any(x is None or not L.STREET[x] or L.OCC[x] >= 0 or
                                       int(L.LV[x]) != low + 1 for x in run + [head]):
                    continue
                # No street may meet the flight from the side (walkers enter a stair only at
                # its foot and head).
                sides = [L._local(t[0] + dr, t[1] + dc) for t in line[:n]] + \
                        [L._local(t[0] - dr, t[1] - dc) for t in line[:n]]
                if any(x is not None and L.STREET[x] for x in sides):
                    continue
                cs = [t[0] - L.origin[0] for t in line[:n]]
                rs = [t[1] - L.origin[1] for t in line[:n]]
                rect = (min(cs), min(rs), max(cs), max(rs))
                L.level(Rect(*rect), low)
                if L.stair(item, rect=rect, face=FOOT_FACE[(dc, dr)]) is not None:
                    break
                L.level(Rect(*rect), low + 1)
            else:
                left.append(f"{p.id} at {(p.c, p.r)}: no straight street to step down on")
    return left


def _beside(c: int, r: int):
    return [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))]


def use_tiles(L: Layout, p, sid: str, c: int, r: int) -> list[tuple[int, int]]:
    """Tiles a walker uses a slot spot from, as V7 counts them: the spot itself; the tiles
    beside it off the footprint when it lies on the item's own footprint (a door in a front
    wall); for a mooring on water (a boat's spot against a quay post), the land beside the spot
    and beside the post."""
    def own(t):
        return p.c <= t[0] < p.c + p.pw and p.r <= t[1] < p.r + p.ph

    if own((c, r)):
        return [t for t in _beside(c, r) if not own(t)]
    t = L.terrain_at(c, r)
    if t is not None and L.cat.is_water(t) and L.cat.slot_kind(p.id, sid) == "mooring":
        near = _beside(c, r)
        near += [n for x in near if own(x) for n in _beside(*x)]
        return [x for x in dict.fromkeys(near) if not own(x)]
    return [(c, r)]


def clear_doors(L: Layout, reach: int = 24, all_slots: bool = False) -> None:
    """Keep every door step and work spot free: small things standing on one go; a building
    standing on another's door step goes instead of the step's owner. Then houses and stalls
    whose spots no street reaches within the actors' last-stretch search go too (with
    `all_slots`, any kit whose slots none of them reaches: kilns, wells, looms boxed in)."""
    for p in [p for p in L.items if not p.removed]:
        spots = [(c, r) for lst in p.slots.values() for c, r, _f in lst]
        if p.door:
            spots.append(p.door)
        for c, r in spots:
            if p.removed or (p.c <= c < p.c + p.pw and p.r <= r < p.r + p.ph):
                continue
            loc = L._local(c, r)
            if loc is None or L.OCC[loc] < 0:
                continue
            other = L.items[L.OCC[loc]]
            od = L.cat.items[other.id]
            if other is p or od.landmark or od.rise or (od.walkable and od.on == "water"):
                continue   # a deck on the spot is the way to it (a stair's foot on a bridge)
            L.remove(other if other.pw * other.ph <= p.pw * p.ph else p)
    # Walking distance from the streets over free ground (same level, no water).
    h, w = L.T.shape
    water = np.zeros(L.T.shape, dtype=bool)
    for t, name in enumerate(L.terrains):
        if L.cat.is_water(name):
            water |= L.T == t
    open_ = (L.T >= 0) & ~L.IMP & ~water & (L.OCC < 0)
    for p in L.items:
        if not p.removed and (L.cat.items[p.id].walkable or L.cat.items[p.id].rise):
            for c, r in p.tiles():
                loc = L._local(c, r)
                if loc is not None:
                    open_[loc] = True
    dist = np.full(L.T.shape, 99, dtype=np.int32)
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
        if p.door is not None:
            spots = [("door", *p.door)]
        elif all_slots and p.slots:
            spots = [(sid, c, r) for sid, lst in p.slots.items() for c, r, _f in lst]
        else:
            continue
        near = {t for sid, c, r in spots for t in use_tiles(L, p, sid, c, r)}
        locs = [L._local(c, r) for c, r in sorted(near)]
        if not any(loc is not None and dist[loc] <= reach for loc in locs):
            L.remove(p)


def glow_cap(L: Layout, rank: dict[str, int], cap: int = 38) -> None:
    """The engine draws at most 40 glowing items per 32 x 32 chunk (V10). Where a town is
    denser than that, the least needed lamps go first: lowest `rank`, then a per-item hash."""
    from .validate import MAX_GLOW_CHUNK
    cap = min(cap, MAX_GLOW_CHUNK)
    by_chunk: dict = {}
    for p in L.items:
        if p.removed or not L.cat.items[p.id].glow:
            continue
        k = (p.r // 32, (COLS - 1 - (p.c + p.pw - 1)) // 32)
        by_chunk.setdefault(k, []).append(p)
    for k, lst in sorted(by_chunk.items()):
        extra = len(lst) - cap
        if extra <= 0:
            continue
        cand = sorted((p for p in lst if p.id in rank),
                      key=lambda p: (rank[p.id], rng.hash64(L.region, "glow", p.c, p.r)))
        for p in cand[:extra]:
            L.remove(p)


def fit_faces(L: Layout, prefer: str) -> None:
    """Each raised tile keeps its face material when its final terrain lists it; otherwise it
    takes `prefer` where the terrain allows it, else the terrain's first face."""
    for t, tid in enumerate(L.terrains):
        allowed = L.cat.faces(tid)
        if not allowed:
            continue
        on = (L.T == t) & (L.LV > 0)
        bad = on & ~np.isin(L.FACE, [L.faces.index(f) for f in allowed if f in L.faces])
        if not bad.any():
            continue
        face = prefer if prefer in allowed else allowed[0]
        for k in np.unique(L.LV[bad]).tolist():
            L.level(Mask(0, 0, bad & (L.LV == k)), int(k), face=face)


def seam(L: Layout, base: str, overlay: str) -> None:
    """Where the layer's `base` meets a different base terrain of the world outside, its edge
    tiles get `overlay`, so two bases never touch (V8) and the meeting reads as a worn margin."""
    w, h = L.size
    edge = []
    for i in range(w):
        edge += [((i, 0), (i, -1)), ((i, h - 1), (i, h))]
    for i in range(h):
        edge += [((0, i), (-1, i)), ((w - 1, i), (w, i))]
    for (c, r), (oc, orr) in edge:
        here = L.terrain_at(c + L.origin[0], r + L.origin[1])
        wc, wr = oc + L.origin[0], orr + L.origin[1]
        if not (0 <= wc < COLS and 0 <= wr < ROWS):
            continue                                   # the world's own edges
        out = L.below_terrain(oc, orr)
        if here == base and out is not None and out != base and L.cat.terrain[out].base:
            L.paint(Rect(c, r, c, r), overlay)


def crossings(L: Layout, inside: np.ndarray | None = None, gap: int = 6) -> list[tuple[int, int]]:
    """Local tiles where two of the layer's streets cross or meet, one per cluster (`gap` apart),
    optionally only where `inside` (a local mask) holds."""
    w, h = L.size
    count = np.zeros((h, w), dtype=np.int16)
    for s in L.streets:
        count += Line(s.points, s.width).mask(L.origin[0], L.origin[1], w, h)
    js, is_ = np.nonzero(count >= 2)
    out: list[tuple[int, int]] = []
    for c, r in sorted(zip(is_.tolist(), js.tolist()), key=lambda t: rng.hash64(L.region, "x", *t)):
        if inside is not None and not inside[r, c]:
            continue
        if all(max(abs(c - a), abs(r - b)) >= gap for a, b in out):
            out.append((c, r))
    return sorted(out, key=lambda t: (t[1], t[0]))


def night_posts(L: Layout, item: str, anchors, *, ring: int = 2, gap: int = 5,
                cap: int = 36) -> list:
    """Light-giving detail (a lamp in a niche, a brazier, a wall torch) beside each anchor tile
    (local), where a light is wanted after dark: on a free tile within `ring`, never within `gap`
    of another light of its kind, and never filling a chunk past `cap` glowing items (V10)."""
    from .validate import MAX_GLOW_CHUNK
    cap = min(cap, MAX_GLOW_CHUNK - 2)
    glow: dict = {}
    mine = []
    for p in L.items:
        if p.removed or not L.cat.items[p.id].glow:
            continue
        k = (p.r // 32, (COLS - 1 - (p.c + p.pw - 1)) // 32)
        glow[k] = glow.get(k, 0) + 1
        if p.id == item:
            mine.append((p.c - L.origin[0], p.r - L.origin[1]))
    keep = set()        # door steps and slot spots stay free (clear_doors would drop the house)
    for p in L.items:
        if p.removed:
            continue
        if p.door is not None:
            keep.add(p.door)
        keep |= {(c, r) for lst in p.slots.values() for c, r, _f in lst}
    placed = []
    for ac, ar in anchors:
        if any(max(abs(ac - a), abs(ar - b)) < gap for a, b in mine):
            continue
        cand = sorted(((dc, dr) for dr in range(-ring, ring + 1) for dc in range(-ring, ring + 1)
                       if (dc, dr) != (0, 0)),
                      key=lambda d: (max(abs(d[0]), abs(d[1])),
                                     rng.hash64(L.region, item, ac + d[0], ar + d[1])))
        for dc, dr in cand:
            at = (ac + dc, ar + dr)
            wc, wr = at[0] + L.origin[0], at[1] + L.origin[1]
            k = (wr // 32, (COLS - 1 - wc) // 32)
            if glow.get(k, 0) >= cap or (wc, wr) in keep or not L.fits(item, at):
                continue
            p = L.place(item, at=at)
            if p is not None:
                glow[k] = glow.get(k, 0) + 1
                mine.append(at)
                placed.append(p)
                break
    return placed
