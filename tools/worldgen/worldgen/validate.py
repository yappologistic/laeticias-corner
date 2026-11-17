"""Semantic validation of a layer on the composed world (world-tech §3.5, V1-V12).

Every issue names the check, the layer, the object and the tile (local, plan and grid
coordinates), and the source line of the layout call that made it when the layer was compiled in
this run. Checks look only at the target layer's tiles, items and graph, except the budgets
(V10), which count the composed world.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from plan import world_plan as P

from . import bible
from .catalog import Catalog
from .compose import NONE16, World, live_items
from .coords import COLS, ROWS, to_plan
from .dsl import Issue, Layout
from .graph import Graph
from .layer import PlanLayer
from .raster import path_tiles

SLOT_REACH = 24
MAX_ITEMS_CHUNK = 1200
MAX_GLOW_CHUNK = 40
MAX_DEST = 64
MAX_DISTRICTS = 254
HIDDEN_SHARE = 0.25


@dataclass
class Target:
    name: str
    regions: list[str]
    pl: PlanLayer
    graph: Graph
    layout: Layout | None = None
    issues: list[Issue] = field(default_factory=list)


def _rect(pl: PlanLayer):
    return (pl.c0, pl.r0, pl.c0 + pl.w - 1, pl.r0 + pl.h - 1)


def item_walk_tiles(cat: Catalog, it) -> set[tuple[int, int]]:
    """Plan tiles of a placed item that its geometry declares walkable (landmarks only)."""
    return {(it.c + it.pw - 1 - dy, it.r + dx) for dx, dy in cat.walk_tiles(it.id, it.k)}


def no_geometry(world: World, cat: Catalog) -> np.ndarray:
    """Tiles under landmarks the art set has not emitted geometry for yet: whether walkers may
    enter them is unknown until it does, so V5/V7 report such tiles as warnings."""
    out = np.zeros((ROWS, COLS), dtype=bool)
    for _, it in live_items(world):
        d = cat.items.get(it.id)
        if d is not None and d.landmark and d.rise == 0 and it.id not in cat.geom:
            out[it.r:it.r + it.ph, it.c:it.c + it.pw] = True
    return out


def walk_map(world: World, cat: Catalog) -> tuple[np.ndarray, np.ndarray]:
    """(walkable, stair) masks over the whole world, plan orientation. `stair` marks tiles where
    a walker may change level: stairs and ramps, and decks on water (jetties, bridges, fords),
    whose planks stand at the height of the bank they leave from."""
    T = world.T
    ground = T != NONE16
    water_ids = [i for i, t in enumerate(world.terrains) if cat.is_water(t)]
    water = np.isin(T, water_ids)
    imp = (world.L & 0x40) > 0
    walk = ground & ~water & ~imp
    stair = np.zeros_like(walk)
    for _, it in live_items(world):
        d = cat.items.get(it.id)
        if d is None:
            continue
        sl = (slice(it.r, it.r + it.ph), slice(it.c, it.c + it.pw))
        if d.rise > 0:
            walk[sl] = True
            stair[sl] = True
        elif d.walkable:
            walk[sl] = True
            if d.on == "water":
                stair[sl] = True
        else:
            walk[sl] = False
            for dx, dy in cat.walk_tiles(it.id, it.k):
                c, r = it.c + it.pw - 1 - dy, it.r + dx
                walk[r, c] = True
    return walk, stair


def validate(world: World, cat: Catalog, root: Path, tg: Target, graphs: dict[str, Graph],
             built: set[str]) -> list[Issue]:
    out: list[Issue] = list(tg.issues)
    name = tg.name
    rect = _rect(tg.pl)
    origin = (rect[0], rect[1])
    c0, r0, c1, r1 = rect
    sl = (slice(r0, r1 + 1), slice(c0, c1 + 1))
    mine = world.owner[sl] == world.layers.index(name)
    srcs = {}
    if tg.layout is not None:
        for p in tg.layout.items:
            if not p.removed:
                srcs[(p.id, p.c, p.r)] = p.src
    items = [(i, it) for i, it in live_items(world) if it.layer == name]

    def issue(code, msg, at=None, src=None, level="error"):
        out.append(Issue(code, level, name, msg, src or (tg.layout.source if tg.layout else None),
                         at))

    def isrc(it):
        return srcs.get((it.id, it.c, it.r))

    # V1: ids exist; draft and provisional ids reported once each.
    used_t = {world.terrains[t] for t in np.unique(world.T[sl][mine]) if t != NONE16}
    for tid in sorted(used_t):
        t = cat.terrain.get(tid)
        if t is None:
            issue("V1", f"unknown terrain {tid!r}")
        elif t.source != "catalog":
            issue("V1", f"terrain {tid!r} comes from a {t.source} entry ({t.file})",
                  level="warning")
        if tid in cat.pending_faces:
            issue("V1", f"terrain {tid!r} uses stand-in faces from plan/provisional.py; its "
                  "catalog does not list them yet (world-tech §6.2)", level="warning")
    seen = set()
    for _, it in items:
        d = cat.items.get(it.id)
        if d is None:
            issue("V1", f"unknown item {it.id!r}", (it.c, it.r), isrc(it))
        elif d.source != "catalog" and it.id not in seen:
            issue("V1", f"item {it.id!r} comes from a {d.source} entry ({d.file})",
                  (it.c, it.r), isrc(it), level="warning")
        seen.add(it.id)
    for dname in sorted({world.districts[d] for d in np.unique(world.D[sl][mine])
                         if d != NONE16}):
        if "/" not in dname or dname.split("/", 1)[0] not in tg.regions:
            issue("V1", f"district {dname!r} is not '<region>/<name>' of {tg.regions}")

    # V2: overlaps within the layer; items of lower layers dropped by this one.
    for a, b, at in world.overlaps:
        if b.layer == name or a.layer == name:
            if at in item_walk_tiles(cat, a) or at in item_walk_tiles(cat, b):
                continue  # furniture on a landmark's walk tile
            issue("V2", f"{b.id} overlaps {a.id} ({a.layer})", at, isrc(b))
    for it, by in world.dropped:
        if by == name:
            issue("V2", f"{it.id} of layer {it.layer.split('!')[0]} dropped under this layer",
                  (it.c, it.r), level="warning")

    # V3: ground under footprints.
    water_ids = {i for i, t in enumerate(world.terrains) if cat.is_water(t)}
    lv = world.L & 0x0F
    for _, it in items:
        d = cat.items.get(it.id)
        if d is None:
            continue
        levels = set()
        for c, r in it.tiles():
            t = int(world.T[r, c])
            if t == NONE16:
                issue("V3", f"{it.id}: no ground under its footprint", (c, r), isrc(it))
                break
            w = t in water_ids
            if (d.on == "land" and w) or (d.on == "water" and not w):
                issue("V3", f"{it.id} needs {d.on}, stands on {world.terrains[t]}", (c, r),
                      isrc(it))
                break
            levels.add(int(lv[r, c]))
        if len(levels) > 1:
            issue("V3", f"{it.id}: footprint not flat (levels {sorted(levels)})", (it.c, it.r),
                  isrc(it))
    if tg.layout is not None:
        for p, foot, head in tg.layout.stair_edges:
            d = cat.items[p.id]
            low = int(lv[p.r, p.c])
            for (c, r), want, what in ((foot, low, "foot"), (head, low + d.rise, "head")):
                if 0 <= r < ROWS and 0 <= c < COLS and int(lv[r, c]) != want:
                    issue("V3", f"{p.name or p.id}: tile at its {what} is level {int(lv[r, c])}, "
                          f"needs {want} (rise {d.rise})", (c, r), p.src)

    # V4: landmark rects and levels against the city file and the layout's expectations.
    marks, mfile = bible.for_region(root, tg.regions[0])
    if tg.layout is not None:
        placed = [p for p in tg.layout.items if not p.removed]
        for ex in tg.layout.expects:
            hit = [p for p in placed if p.name == ex.landmark or
                   p.id.split(".", 1)[-1] == ex.landmark or p.id == ex.landmark]
            if not hit:
                issue("V4", f"expected landmark {ex.landmark!r} is not placed",
                      (ex.rect.c0, ex.rect.r0), ex.src)
                continue
            p = hit[0]
            if (p.c, p.r, p.c + p.pw - 1, p.r + p.ph - 1) != ex.rect.bounds():
                issue("V4", f"{ex.landmark}: placed at {p.rect.bounds()}, expected "
                      f"{ex.rect.bounds()} (world plan)", (p.c, p.r), ex.src)
            if ex.level is not None:
                got = int(lv[p.r, p.c]) - tg.layout.base_level
                if got != ex.level:
                    issue("V4", f"{ex.landmark}: local level {got}, expected {ex.level}",
                          (p.c, p.r), ex.src)
        if marks:
            readme = Path(root) / "tools/worldgen/regions" / name / "README.md"
            complete = readme.exists() and "Status: complete" in readme.read_text()
            by_id = {p.id.split(".", 1)[-1]: p for p in placed if "." in p.id}
            for lid, m in marks.items():
                p = by_id.get(lid)
                wr = (m.rect[0] + origin[0], m.rect[1] + origin[1], m.rect[2] + origin[0],
                      m.rect[3] + origin[1])
                if p is None:
                    issue("V4", f"landmark {lid!r} ({mfile}:{m.line}) is not placed", wr[:2],
                          level="error" if complete else "warning")
                    continue
                if p.rect.bounds() != wr:
                    bw, bh = wr[2] - wr[0] + 1, wr[3] - wr[1] + 1
                    holds = (p.c <= wr[0] and p.r <= wr[1] and p.c + p.pw - 1 >= wr[2]
                             and p.r + p.ph - 1 >= wr[3])
                    if holds and (p.pw, p.ph) != (bw, bh):
                        # The set models attached parts (a portico, a stair) with the building:
                        # the placement is right if the bible's rect lies inside the footprint.
                        issue("V4", f"{lid}: the set catalog footprint {p.pw} x {p.ph} differs "
                              f"from {mfile}:{m.line} ({bw} x {bh}); placed at local "
                              f"{_local(p.rect.bounds(), origin)}, which holds {m.rect}",
                              (p.c, p.r), p.src, level="warning")
                    else:
                        issue("V4", f"{lid}: placed at local {_local(p.rect.bounds(), origin)}, "
                              f"{mfile}:{m.line} says {m.rect}", (p.c, p.r), p.src)
                if m.level is not None:
                    got = int(lv[p.r, p.c]) - tg.layout.base_level
                    if not (m.level[0] <= got <= m.level[1]):
                        issue("V4", f"{lid}: local level {got}, {mfile}:{m.line} says "
                              f"{m.level[0]}" + (f"..{m.level[1]}" if m.level[1] != m.level[0]
                                                  else ""), (p.c, p.r), p.src)

    walk, stair = walk_map(world, cat)
    unknown = no_geometry(world, cat)
    g = tg.graph
    # V5: every graph edge is walkable along its course, levels change only on stairs/ramps.
    graph_tiles: set[tuple[int, int]] = set()
    for e in g.edges:
        a, b = g.node(e.a), g.node(e.b)
        if a is None or b is None:
            issue("V6", f"edge {e.a} - {e.b}: unknown node")
            continue
        pts = [to_plan(*a.at), *[to_plan(*v) for v in e.via], to_plan(*b.at)]
        course = path_tiles(pts)
        prev = None
        for (c, r) in course:
            if not (0 <= c < COLS and 0 <= r < ROWS):
                continue
            graph_tiles.add((c, r))
            if not walk[r, c]:
                t = world.terrain_id(c, r)
                if unknown[r, c]:
                    issue("V5", f"{e.kind} {e.a} - {e.b} enters a landmark without geometry "
                          "yet (walk tiles unknown)", (c, r), level="warning")
                else:
                    issue("V5", f"{e.kind} {e.a} - {e.b} crosses a tile walkers cannot enter "
                          f"({t}{', impassable' if world.L[r, c] & 0x40 else ''})", (c, r))
                break
            if prev and lv[r, c] != lv[prev[1], prev[0]] and not (stair[r, c] or
                                                                   stair[prev[1], prev[0]]):
                issue("V5", f"{e.kind} {e.a} - {e.b} steps from level {lv[prev[1], prev[0]]} "
                      f"to {lv[r, c]} without a stair or ramp", (c, r))
                break
            prev = (c, r)

    # V6: connected, portals agreed, dest budget.
    parent = {n.id: n.id for n in g.nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in g.edges:
        if e.a in parent and e.b in parent:
            parent[find(e.a)] = find(e.b)
    comps: dict[str, list] = {}
    for n in g.nodes:
        comps.setdefault(find(n.id), []).append(n)
    if len(comps) > 1:
        main = max(comps.values(), key=len)
        for nodes in comps.values():
            if nodes is main:
                continue
            n = nodes[0]
            issue("V6", f"node {n.id!r} ({len(nodes)} node(s)) is not connected to the rest of "
                  "the graph", to_plan(*n.at))
    for n in g.nodes:
        if n.kind != "portal":
            continue
        decl = P.PORTALS.get(n.id)
        at = to_plan(*n.at)
        if decl is None:
            issue("V6", f"portal {n.id!r} is not declared in plan/world_plan.py PORTALS", at)
            continue
        layers, tile, _lvl = decl
        if name not in layers:
            issue("V6", f"portal {n.id!r} belongs to layers {layers}, not {name}", at)
        if tuple(tile) != at:
            issue("V6", f"portal {n.id!r} at {at}, the plan says {tuple(tile)}", at)
        for other in layers:
            if other == name:
                continue
            og = graphs.get(other)
            if og is None:
                issue("V6", f"portal {n.id!r}: layer {other!r} is not built yet", at,
                      level="warning")
            elif og.node(n.id) is None:
                planned = [rid for rid, rt in P.ROUTES.items() if not rt.get("build")
                           and f"{name}:{n.id}" in rt["points"]] if other == "base" else []
                if planned:
                    issue("V6", f"portal {n.id!r}: the base's route {planned[0]!r} is planned, "
                          "not built yet", at, level="warning")
                else:
                    issue("V6", f"portal {n.id!r} is missing from layer {other!r}'s graph", at)
    dests = sum(1 for n in g.nodes if n.kind == "dest")
    if dests > MAX_DEST:
        issue("V10", f"{dests} dest nodes; at most {MAX_DEST} per region")

    # V7: slot spots walkable, free and near the graph.
    spots = []
    if tg.layout is not None:
        for p in tg.layout.items:
            if p.removed:
                continue
            for sid, lst in p.slots.items():
                for (c, r, _f) in lst:
                    spots.append((p, sid, c, r))
            if p.door and not p.slots:
                spots.append((p, "door", *p.door))
    marks = np.full((ROWS, COLS), -1, dtype=np.int32)   # which landmark covers a tile
    for i, it in live_items(world):
        d = cat.items.get(it.id)
        if d is not None and d.landmark and d.rise == 0:
            marks[it.r:it.r + it.ph, it.c:it.c + it.pw] = i
    for p, sid, c, r in spots:
        inside = 0 <= c < COLS and 0 <= r < ROWS
        own = p.c <= c < p.c + p.pw and p.r <= r < p.r + p.ph
        start = [(c, r)]
        if inside and not walk[r, c] and own and not cat.items[p.id].landmark:
            # A seat, a work yard under a shed: used from the walkable tile beside it.
            start = [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                     if 0 <= c + dc < COLS and 0 <= r + dr < ROWS and walk[r + dr, c + dc]]
        art = inside and marks[r, c] >= 0 and not cat.items[p.id].rise
        if not inside or not start or not walk[start[0][1], start[0][0]]:
            if inside and unknown[r, c]:
                issue("V7", f"{p.name or p.id}: slot {sid!r} is inside a landmark without "
                      "geometry yet (walk tiles unknown)", (c, r), p.src, level="warning")
            elif art:
                issue("V7", f"{p.name or p.id}: slot {sid!r} is inside "
                      f"{world.items[marks[r, c]].id} on a tile its geometry does not make "
                      "walkable (art geometry)", (c, r), p.src, level="warning")
            else:
                issue("V7", f"{p.name or p.id}: slot {sid!r} is on a tile walkers cannot enter",
                      (c, r), p.src)
            continue
        if not any(_near_graph(t, graph_tiles, walk, lv, stair) for t in start):
            if art:
                issue("V7", f"{p.name or p.id}: slot {sid!r} is enclosed inside "
                      f"{world.items[marks[r, c]].id} (art geometry: no walk path out)",
                      (c, r), p.src, level="warning")
            else:
                issue("V7", f"{p.name or p.id}: slot {sid!r} is not within {SLOT_REACH} walking "
                      "tiles of the path graph", (c, r), p.src)

    # V8: base terrains never touch; seas at level 0; rivers never run uphill.
    T = world.T[sl].astype(np.int64)
    isbase = np.array([bool(cat.terrain.get(t) and cat.terrain[t].base) for t in world.terrains]
                      + [False])
    Ti = np.where(T == NONE16, len(world.terrains), T)
    b = isbase[Ti]
    for axis, (a_, b_) in ((1, (np.s_[:, 1:], np.s_[:, :-1])), (0, (np.s_[1:, :], np.s_[:-1, :]))):
        clash = b[a_] & b[b_] & (Ti[a_] != Ti[b_]) & (mine[a_] | mine[b_])
        if clash.any():
            j, i = np.argwhere(clash)[0]
            j, i = (j + 1, i) if axis == 0 else (j, i + 1)
            issue("V8", f"{int(clash.sum())} places where two base terrains touch without an "
                  f"overlay, e.g. {world.terrains[Ti[j, i]]}", (i + c0, j + r0))
    sea_ids = [i for i, t in enumerate(world.terrains) if t in ("world.sea", "world.shallows")]
    bad = np.isin(T, sea_ids) & (lv[sl] != 0) & mine
    if bad.any():
        j, i = np.argwhere(bad)[0]
        issue("V8", f"{int(bad.sum())} sea tiles above level 0", (i + c0, j + r0))
    riv = [i for i, t in enumerate(world.terrains) if cat.is_water(t) and i not in sea_ids]
    rm = np.isin(T, riv) & mine
    flow = (world.L[sl] >> 4) & 3
    step = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}  # aux -> plan (dc, dr)
    up = 0
    first = None
    for j, i in np.argwhere(rm):
        dc, dr = step[int(flow[j, i])]
        c, r = i + c0 + dc, j + r0 + dr
        if 0 <= c < COLS and 0 <= r < ROWS and world.T[r, c] in riv and \
                lv[r, c] > lv[j + r0, i + c0]:
            up += 1
            first = first or (c, r)
    if up:
        issue("V8", f"{up} river tiles flow uphill", first)

    # V9: inside the region extents; districts everywhere there is ground.
    if name != "base":
        ext = [P.REGIONS[r][3] for r in tg.regions if r in P.REGIONS]
        if ext:
            ec0 = min(e[0] for e in ext)
            er0 = min(e[1] for e in ext)
            ec1 = max(e[2] for e in ext)
            er1 = max(e[3] for e in ext)
            if c0 < ec0 or r0 < er0 or c1 > ec1 or r1 > er1:
                issue("V9", f"layer rect {rect} leaves its regions' extent "
                      f"{(ec0, er0, ec1, er1)}", (c0, r0))
    nod = mine & (world.T[sl] != NONE16) & (world.D[sl] == NONE16)
    if nod.any():
        j, i = np.argwhere(nod)[0]
        issue("V9", f"{int(nod.sum())} tiles with ground but no district", (i + c0, j + r0))

    # V10: budgets on the composed world.
    counts: dict = {}
    glows: dict = {}
    for _, it in live_items(world):
        tx, ty = it.r, COLS - 1 - (it.c + it.pw - 1)
        k = (tx // P.CHUNK, ty // P.CHUNK)
        counts[k] = counts.get(k, 0) + 1
        d = cat.items.get(it.id)
        if d is not None and d.glow:
            glows[k] = glows.get(k, 0) + 1
    for k, n in sorted(counts.items()):
        if n > MAX_ITEMS_CHUNK:
            issue("V10", f"chunk {k} holds {n} items; at most {MAX_ITEMS_CHUNK}",
                  to_plan(k[0] * P.CHUNK, k[1] * P.CHUNK))
    for k, n in sorted(glows.items()):
        if n > MAX_GLOW_CHUNK:
            issue("V10", f"chunk {k} holds {n} glowing items; at most {MAX_GLOW_CHUNK}",
                  to_plan(k[0] * P.CHUNK, k[1] * P.CHUNK))
    if len(world.districts) > MAX_DISTRICTS:
        issue("V10", f"{len(world.districts)} districts world-wide; at most {MAX_DISTRICTS}")

    # V11: elevation readability (warning).
    wsub = walk[sl] & mine
    total = int(wsub.sum())
    if total:
        lvs = lv.astype(np.int16)
        hidden = np.zeros((ROWS, COLS), dtype=bool)
        for a in range(0, 17):
            for b_ in range(0, 17 - a):
                if a == 0 and b_ == 0:
                    continue
                # Q = P + (a, b) in grid = plan (c - b, r + a); hides P if dL > 0, a+b <= dL+1.
                q = np.full((ROWS, COLS), -99, dtype=np.int16)
                q[:ROWS - a if a else ROWS, b_:] = lvs[a:, :COLS - b_ if b_ else COLS]
                dl = q - lvs
                hidden |= (dl > 0) & (a + b_ <= dl + 1)
        share = float((hidden[sl] & wsub).sum()) / total
        if share > HIDDEN_SHARE:
            issue("V11", f"{share:.0%} of walkable tiles are hidden behind raised ground "
                  f"(at most {HIDDEN_SHARE:.0%})", level="warning")

    # V12: cards and actor kinds named by the region files.
    for rid in tg.regions:
        f = Path(root) / "assets/regions" / f"{rid}.json"
        if not f.exists():
            continue
        doc = json.loads(f.read_text())
        cards = set(doc.get("cards", {}))
        for _, it in items:
            d = cat.items.get(it.id)
            if d and d.card and d.card not in cards and P.REGIONS.get(rid, ("",))[0] != "stretch":
                issue("V12", f"{it.id} names card {d.card!r}, missing from {f.name}",
                      (it.c, it.r), isrc(it))
    return out


def _local(b, origin):
    return (b[0] - origin[0], b[1] - origin[1], b[2] - origin[0], b[3] - origin[1])


def _near_graph(start, graph_tiles, walk, lv, stair) -> bool:
    if start in graph_tiles:
        return True
    seen = {start}
    q = deque([(start, 0)])
    while q:
        (c, r), d = q.popleft()
        if d >= SLOT_REACH:
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c + dc, r + dr)
            if n in seen or not (0 <= n[0] < COLS and 0 <= n[1] < ROWS):
                continue
            if not walk[n[1], n[0]]:
                continue
            if lv[n[1], n[0]] != lv[r, c] and not (stair[n[1], n[0]] or stair[r, c]):
                continue
            if n in graph_tiles:
                return True
            seen.add(n)
            q.append((n, d + 1))
    return False
