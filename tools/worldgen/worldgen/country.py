"""Country of the base layer (world-tech §3.8 step 5; docs/design/sets/world.md §9.3, §9.5).

Fields near water and roads with plot texture, plants by stretch (clumped into woods with
clearings, sparse in open land, thinning toward the road, none on its verges), riverside trees
and reed beds, flowers on coasts, natural props, peaks on summits. Then the finishing passes:
the glow budget outside towns and a check that every door and slot spot the base places can be
reached from its graph (V7), removing kit that cannot.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from plan import world_plan as P

from . import rng
from .base import CC, RR, SEED, World, box_blur, distance_to, noise
from .coords import COLS, ROWS
from .dsl import Placed

SRC = "plan/world_plan.py"
GLOW_OUTSIDE_TOWNS = 12   # §9.5 budget per chunk
REACH = 24                # V7: walking tiles from the graph


def place(W: World) -> None:
    fields(W)
    plants(W)
    props(W)
    peaks(W)
    glow_cap(W)
    reachable_kit(W)


def _add(W: World, item: str, c: int, r: int, k: int) -> Placed:
    L = W.L
    d = W.cat.items[item]
    k = k % max(d.count, 1) if d.layout != "connect" else 0
    pw, ph = L._plan_size(item, k)
    p = Placed(len(L.items), item, c, r, pw, ph, k, None, SRC)
    L.items.append(p)
    L._occupy(p)
    return p


def fields(W: World) -> None:
    """Ploughland near rivers and roads in farming stretches, in plots with balks between, and
    the stretch's second crop (vines, olives) along the roads."""
    L, land, level = W.L, W.land, W.L.LV
    dist_river = distance_to(W.river, 24)
    dist_road = distance_to(W.road, 24) if W.road is not None else np.full((ROWS, COLS), 24)
    plotn = rng.hash01(CC // 6 + (RR // 4) * 977, RR // 4, rng.hash64(SEED, "plots"))
    zone = noise(16.0, "fieldzone")
    open_ = land & ~W.reserved & ~W.bare & ~W.river & ~L.STREET & (L.OCC < 0) & ~W.marsh & \
        (W.anchors.dist > 1) & (level <= 5) & ~W.forest
    balks = ((CC % 6) == 0) | ((RR % 4) == 0)
    total = 0
    for i, n in enumerate(W.names):
        b = W.biome(i)
        m = (W.stretch == i) & open_
        if not m.any():
            continue
        if b.get("field") and b.get("fields"):
            score = zone + np.clip(1 - dist_river / 18.0, 0, 1) * 0.5 + \
                np.clip(1 - dist_road / 14.0, 0, 1) * 0.4
            thr = np.quantile(score[m], 1 - b["fields"]) if m.sum() > 50 else 9
            fz = m & (score >= thr) & (plotn > 0.2) & ~balks & (dist_road >= 2)
            L.T[fz] = W.tidx(b["field"])
            total += int(fz.sum())
            open_ &= ~fz
        if b.get("vines"):
            vz = m & open_ & (dist_road >= 2) & (dist_road <= 6) & (zone > 0.25) & ~balks
            L.T[vz] = W.tidx(b["vines"])
            open_ &= ~vz
    W.stats["field_tiles"] = total


def plants(W: World) -> None:
    L, land = W.L, W.land
    field_t = {i for i, t in enumerate(L.terrains) if "field" in t or t.endswith("soil")
               or t in ("world.scree", "world.dune", "world.gravel_desert")}
    is_field = np.isin(L.T, list(field_t)) if field_t else np.zeros_like(land)
    road = W.road if W.road is not None else np.zeros_like(land)
    dist_road = distance_to(road, 8)
    dist_river = distance_to(W.river, 4)
    free = land & ~W.reserved & ~W.river & ~W.bare & (L.OCC < 0) & ~L.STREET & \
        (W.anchors.dist > 1) & (L.LV <= 11) & (dist_road >= 3) & ~L.IMP & ~W.keep
    clearing = noise(7.0, "clearing")
    u = rng.hash01(CC, RR, rng.hash64(SEED, "tree"))
    pick = rng.hash01(CC, RR, rng.hash64(SEED, "species"))
    var = rng.hash_grid(CC, RR, rng.hash64(SEED, "variant"))
    # Near the road plants thin to half (§9.5).
    thin = np.where(dist_road < 6, 0.5, 1.0)
    counts: dict[str, int] = {}
    for i, n in enumerate(W.names):
        b = W.biome(i)
        if not b.get("plants"):
            continue
        m = (W.stretch == i) & free
        if not m.any():
            continue
        dens = np.where(W.forest, np.where(clearing < -0.25, 0.04, b.get("forest_density", 0.4)),
                        b.get("open", 0.02))
        dens = np.where(is_field, 0.0, dens) * thin
        hit = m & (u < dens)
        high = b.get("high")
        groups = [(hit & (L.LV < 9), b["plants"])]
        if high:
            groups = [(hit & (L.LV < 9), b["plants"]), (hit & (L.LV >= 9), high)]
        else:
            groups = [(hit, b["plants"])]
        for mask, table in groups:
            items = [k for k in table if k in W.cat.items]
            if not items:
                continue
            cum = np.cumsum([table[k] for k in items]) / sum(table[k] for k in items)
            js, is_ = np.nonzero(mask)
            for j, i_ in zip(js.tolist(), is_.tolist()):
                item = items[min(int(np.searchsorted(cum, pick[j, i_], side="right")),
                                 len(items) - 1)]
                k = int(var[j, i_] % np.uint64(1 << 20))
                if item == "world.p_wildflowers":
                    k = b.get("flowers", 0)
                _add(W, item, i_, j, k)
                counts[item] = counts.get(item, 0) + 1
        # Wildflowers in open land, the stretch's own look.
        if "world.p_wildflowers" in W.cat.items and "flowers" in b:
            fl = (W.stretch == i) & free & (L.OCC < 0) & ~W.forest & ~is_field & \
                (rng.hash01(CC, RR, rng.hash64(SEED, "flowers")) < 0.012)
            for j, i_ in zip(*np.nonzero(fl)):
                _add(W, "world.p_wildflowers", int(i_), int(j), b["flowers"])
                counts["world.p_wildflowers"] = counts.get("world.p_wildflowers", 0) + 1
    # Riverside trees (density 0.4 along the banks) and reed beds at the water.
    bank1 = land & ~W.river & ~W.reserved & (dist_river == 1) & ~L.STREET & (W.anchors.dist > 1) & ~W.keep
    bank2 = land & ~W.river & ~W.reserved & (dist_river == 2) & ~L.STREET & (W.anchors.dist > 1) & ~W.keep
    ur = rng.hash01(CC, RR, rng.hash64(SEED, "reeds"))
    for j, i_ in zip(*np.nonzero(bank1 & (L.OCC < 0) & (ur < 0.3) & (dist_road >= 2))):
        _add(W, "world.t_reeds", int(i_), int(j), int((i_ * 7 + j) % 4))
        counts["world.t_reeds"] = counts.get("world.t_reeds", 0) + 1
    ut = rng.hash01(CC, RR, rng.hash64(SEED, "rivertree"))
    for j, i_ in zip(*np.nonzero((bank2 | bank1) & (L.OCC < 0) & (ut < 0.4) & (dist_road >= 3)
                                 & ~W.bare & (L.LV <= 11))):
        b = W.biome(int(W.stretch[j, i_]))
        item = b.get("river_tree")
        if b.get("river_tree2") and ut[j, i_] < 0.15:
            item = b["river_tree2"]
        if item and item in W.cat.items:
            _add(W, item, int(i_), int(j), int(var[j, i_] % np.uint64(97)))
            counts[item] = counts.get(item, 0) + 1
    # Marsh: dense reeds.
    for j, i_ in zip(*np.nonzero(W.marsh & (L.OCC < 0) & ~L.STREET & ~W.keep & (ur < 0.35))):
        _add(W, "world.t_reeds", int(i_), int(j), int((i_ * 3 + j) % 4))
        counts["world.t_reeds"] = counts.get("world.t_reeds", 0) + 1
    # Coasts: sea squill and sea lavender (look 4).
    coast = W.coast & free & (L.OCC < 0) & (rng.hash01(CC, RR, rng.hash64(SEED, "coastfl")) < 0.03)
    for j, i_ in zip(*np.nonzero(coast)):
        _add(W, "world.p_wildflowers", int(i_), int(j), 4)
        counts["world.p_wildflowers"] = counts.get("world.p_wildflowers", 0) + 1
    W.stats["plants"] = dict(sorted(counts.items()))


def props(W: World) -> None:
    """Boulders, crags, folds and mounds scattered thinly by stretch."""
    L, land = W.L, W.land
    road = W.road if W.road is not None else np.zeros_like(land)
    near_road = distance_to(road, 4) < 4
    u = rng.hash01(CC, RR, rng.hash64(SEED, "props"))
    var = rng.hash_grid(CC, RR, rng.hash64(SEED, "propvar"))
    counts: dict[str, int] = {}
    for i, n in enumerate(W.names):
        b = W.biome(i)
        if not b.get("props"):
            continue
        m = (W.stretch == i) & land & ~W.reserved & ~W.river & (L.OCC < 0) & ~L.STREET & \
            (W.anchors.dist > 1) & ~near_road & ~L.IMP & ~W.keep
        acc = 0.0
        for item, dens in b["props"].items():
            if item not in W.cat.items:
                continue
            hit = m & (u >= acc) & (u < acc + dens)
            acc += dens
            for j, i_ in zip(*np.nonzero(hit)):
                d = W.cat.items[item]
                pw, ph = L._plan_size(item, 0)
                tiles = [(i_ + x, j + y) for y in range(ph) for x in range(pw)]
                if not all(0 <= x < COLS and 0 <= y < ROWS and land[y, x] and L.OCC[y, x] < 0
                           and not L.STREET[y, x] and not W.river[y, x] and not W.reserved[y, x]
                           for x, y in tiles):
                    continue
                lv = int(L.LV[j, i_])
                if any(abs(int(L.LV[y, x]) - lv) > 1 for x, y in tiles):
                    continue
                for x, y in tiles:
                    L.LV[y, x] = lv
                _add(W, item, int(i_), int(j), int(var[j, i_] % np.uint64(1 << 20)))
                counts[item] = counts.get(item, 0) + 1
                if item == "world.sheepfold":
                    from .routes import mark_pasture
                    mark_pasture(W, int(i_) + 1, int(j) + 1)
    W.stats["props"] = dict(sorted(counts.items()))


def peaks(W: World) -> None:
    """A peak sprite on summits of level 11 and above, about every 10 tiles (world.md §4)."""
    L, land = W.L, W.land
    lv = L.LV.astype(np.int16)
    local_max = lv >= np.maximum.reduce([np.roll(np.roll(lv, a, 0), b, 1)
                                          for a in (-3, 0, 3) for b in (-3, 0, 3)])
    cand = land & (lv >= 11) & local_max & ~W.reserved & (W.anchors.dist > 1) & ~W.river
    done = []
    n = 0
    for j, i_ in sorted(zip(*np.nonzero(cand)), key=lambda t: (-lv[t[0], t[1]], t[0], t[1])):
        j, i_ = int(j), int(i_)
        if any(abs(j - a) < 10 and abs(i_ - b) < 10 for a, b in done):
            continue
        b = W.biome(int(W.stretch[j, i_]))
        if not b.get("peaks"):
            continue
        tiles = [(i_ - 1 + x, j - 1 + y) for y in range(3) for x in range(3)]
        if not all(0 <= x < COLS and 0 <= y < ROWS and land[y, x] and L.OCC[y, x] < 0 and
                   not L.STREET[y, x] and not W.river[y, x] for x, y in tiles):
            continue
        top = int(max(L.LV[y, x] for x, y in tiles))
        for x, y in tiles:
            L.LV[y, x] = top
        look = 1 if top >= 13 else 0
        _add(W, "world.peak", i_ - 1, j - 1, look)
        done.append((j, i_))
        n += 1
    W.stats["peaks"] = n


def glow_cap(W: World) -> None:
    """At most GLOW_OUTSIDE_TOWNS glowing base items per chunk (§9.5): spread ones go last."""
    L = W.L
    by_chunk: dict = {}
    for p in L.items:
        if p.removed or not W.cat.items[p.id].glow:
            continue
        k = (p.r // 32, (COLS - 1 - (p.c + p.pw - 1)) // 32)
        by_chunk.setdefault(k, []).append(p)
    removed = 0
    for k, lst in sorted(by_chunk.items()):
        extra = len(lst) - GLOW_OUTSIDE_TOWNS
        if extra <= 0:
            continue
        lst.sort(key=lambda p: (p.id in ("world.royal_station", "rome.mutatio", "world.beacon",
                                         "world.watchtower"),
                                rng.hash64(SEED, "glow", p.c, p.r)))
        for p in lst[:extra]:
            L._remove(p)
            removed += 1
    W.stats["glow_removed"] = removed


def reachable_kit(W: World) -> None:
    """Every door and slot spot of base kit must be walkable and within REACH walking tiles of
    the base graph (V7). Kit whose spots fail is taken out again."""
    L, cat = W.L, W.cat
    walk = W.land & ~W.river & ~L.IMP
    stair = np.zeros_like(walk)
    for p in L.items:
        if p.removed:
            continue
        d = cat.items[p.id]
        for c, r in p.tiles():
            if d.rise > 0:
                walk[r, c] = stair[r, c] = True
            elif d.walkable:
                walk[r, c] = True
                stair[r, c] |= d.on == "water"
            else:
                walk[r, c] = False
    dist = np.full((ROWS, COLS), 99, dtype=np.int16)
    q = deque()
    for j, i in zip(*np.nonzero(L.STREET & walk)):
        dist[j, i] = 0
        q.append((int(j), int(i)))
    lv = L.LV
    while q:
        j, i = q.popleft()
        if dist[j, i] >= REACH:
            continue
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = j + dj, i + di
            if 0 <= a < ROWS and 0 <= b < COLS and walk[a, b] and dist[a, b] > dist[j, i] + 1 \
                    and (lv[a, b] == lv[j, i] or stair[a, b] or stair[j, i]):
                dist[a, b] = dist[j, i] + 1
                q.append((a, b))
    removed: dict[str, int] = {}
    from .routes import access_tiles
    for p in L.items:
        if p.removed:
            continue
        ok = all(any(0 <= x < COLS and 0 <= y < ROWS and dist[y, x] <= REACH for x, y in near)
                 for near in access_tiles(p))
        if not ok:
            L._remove(p)
            removed[p.id] = removed.get(p.id, 0) + 1
    W.stats["unreachable_removed"] = dict(sorted(removed.items()))
