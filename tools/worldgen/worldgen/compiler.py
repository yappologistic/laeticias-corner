"""Layout -> layer file data (plan orientation) and its path graph.

The graph is derived from the layout's streets: a node at every polyline vertex, at every crossing
of two streets, where a street ends on another (a T), at named nodes (snapped to the nearest street
within 16 tiles), at stair feet and heads, and at portals (the street end on the layer's edge).
Unnamed nodes are numbered in a fixed order, so the same layout gives the same ids.
"""

from __future__ import annotations

import math

import numpy as np

from plan import world_plan as P

from .coords import to_grid
from .dsl import NO_GROUND, TRANSPARENT, Issue, Layout
from .graph import Edge, Graph, Lane, Node, Port
from .layer import AUX_SHIFT, IMPASSABLE, NO_GROUND as NG_BYTE, TRANSPARENT as TR_BYTE
from .layer import PlanItem, PlanLayer

SNAP = 16  # tiles: how far a named node may be from a street and still join it


def compile_layer(L: Layout) -> tuple[PlanLayer, list[Issue]]:
    issues: list[Issue] = []
    used = sorted({int(t) for t in np.unique(L.T) if t >= 0})
    terrains = sorted(L.terrains[t] for t in used)
    remap = np.full(max(len(L.terrains), 1), TR_BYTE, dtype=np.uint8)
    for t in used:
        remap[t] = terrains.index(L.terrains[t])
    T = np.full(L.T.shape, TR_BYTE, dtype=np.uint8)
    solid = L.T >= 0
    T[solid] = remap[L.T[solid]]
    T[L.T == NO_GROUND] = NG_BYTE
    ground = solid

    level = L.LV.astype(np.int32) + L.base_level
    bad = ground & ((level < 0) | (level > 15))
    if bad.any():
        j, i = np.argwhere(bad)[0]
        issues.append(Issue("V3", "error", L.layer,
                            f"{int(bad.sum())} tiles with a level outside 0..15 (e.g. {level[j, i]})",
                            L.source, (int(i) + L.origin[0], int(j) + L.origin[1])))
    aux = np.zeros(L.T.shape, dtype=np.int32)
    _sea_depth(L)
    has_aux = L.AUX >= 0
    aux[has_aux] = L.AUX[has_aux]
    for f_idx, face in enumerate(L.faces):
        m = (L.FACE == f_idx) & ~has_aux & ground
        if not m.any():
            continue
        for t in np.unique(L.T[m]):
            tid = L.terrains[t]
            faces = L.cat.faces(tid)
            mt = m & (L.T == t)
            if face in faces:
                aux[mt] = faces.index(face)
            else:
                j, i = np.argwhere(mt)[0]
                lvl = "error" if faces else "warning"
                why = f"its faces are {faces}" if faces else "it lists no faces yet (world-tech §6.2)"
                issues.append(Issue("V1", lvl, L.layer,
                                    f"face material {face!r} on terrain {tid!r}, but {why}",
                                    L.source, (int(i) + L.origin[0], int(j) + L.origin[1])))
    # A tile repainted after its face was chosen (a field or road over a bank, land over a
    # river's flow) may hold an index its new terrain has no material for, which the engine
    # draws as a flat fill (QA6 V6-003): it takes its terrain's first material.
    for t in np.unique(L.T[ground]).tolist():
        tid = L.terrains[t]
        if not L.cat.is_water(tid):
            aux[ground & (L.T == t) & (aux >= max(len(L.cat.faces(tid)), 1))] = 0
    Lb = (np.clip(level, 0, 15) | ((aux & 3) << AUX_SHIFT) | np.where(L.IMP, IMPASSABLE, 0))
    Lb = np.where(ground, Lb, 0).astype(np.uint8)

    dused = sorted({int(d) for d in np.unique(L.DIST[ground]) if d >= 0})
    districts = sorted(L.districts[d] for d in dused)
    D = np.zeros(L.T.shape, dtype=np.uint8)
    for d in dused:
        D[(L.DIST == d) & ground] = districts.index(L.districts[d])
    nodist = ground & (L.DIST < 0)
    if nodist.any():
        j, i = np.argwhere(nodist)[0]
        issues.append(Issue("V9", "error", L.layer,
                            f"{int(nodist.sum())} tiles with ground but no district",
                            L.source, (int(i) + L.origin[0], int(j) + L.origin[1])))

    items = [PlanItem(p.id, p.c, p.r, p.pw, p.ph, p.k) for p in L.items if not p.removed]
    pl = PlanLayer(L.origin[0], L.origin[1], L.size[0], L.size[1], terrains, districts,
                   T, Lb, D, items)
    return pl, issues


def _sea_depth(L: Layout) -> None:
    """Sea tiles a layout painted get the engine's depth band by distance to land (1, 3, 6)."""
    from .base import distance_to
    sea = np.zeros(L.T.shape, dtype=bool)
    for t, tid in enumerate(L.terrains):
        if tid in ("world.sea", "world.shallows"):
            sea |= L.T == t
    todo = sea & (L.AUX < 0)
    if not todo.any():
        return
    land = (L.T >= 0) & ~sea
    for t, tid in enumerate(L.terrains):
        if L.cat.is_water(tid):
            land &= L.T != t
    d = distance_to(land, 8)
    band = np.select([d <= 1, d <= 3, d <= 6], [0, 1, 2], 3).astype(np.int8)
    L.AUX[todo] = band[todo]


# --- graph -----------------------------------------------------------------------------------

def _intersect(a, b, c, d):
    """Parameters (t, u) where segment a-b meets c-d, or None (parallel or apart)."""
    rx, ry = b[0] - a[0], b[1] - a[1]
    sx, sy = d[0] - c[0], d[1] - c[1]
    den = rx * sy - ry * sx
    if den == 0:
        return None
    qx, qy = c[0] - a[0], c[1] - a[1]
    t = (qx * sy - qy * sx) / den
    u = (qx * ry - qy * rx) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return t, u
    return None


def _project(p, pts):
    """Nearest point on a polyline: (distance, position = segment + t, tile)."""
    best = (math.inf, 0.0, tuple(pts[0]))
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ll = dx * dx + dy * dy
        t = 0.0 if ll == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ll))
        q = (a[0] + t * dx, a[1] + t * dy)
        dist = math.hypot(p[0] - q[0], p[1] - q[1])
        if dist < best[0]:
            best = (dist, i + t, (round(q[0]), round(q[1])))
    return best


def _level_rule(L: Layout):
    """same(a, b): whether walkers may go between plan tiles a and b of this layout without a
    stair: the same level, or either tile a stair, ramp or deck (tiles outside the layer are
    not judged here)."""
    from .validate import deck_tiles

    def water_at(c, r):
        t = L.terrain_at(c, r)
        return t is not None and L.cat.is_water(t)

    decks = deck_tiles(L.cat, [p for p in L.items if not p.removed], water_at)

    def same(a, b):
        la, lb = L._local(*a), L._local(*b)
        if la is None or lb is None or a in decks or b in decks:
            return True
        return L.LV[la] == L.LV[lb]
    return same


def _on_floor(L: Layout, tile) -> bool:
    """Whether a tile is a walk tile of the landmark standing on it (not a stair)."""
    loc = L._local(*tile)
    if loc is None or L.OCC[loc] < 0:
        return False
    q = L.items[L.OCC[loc]]
    d = L.cat.items.get(q.id)
    return bool(d and d.landmark and d.rise == 0 and tuple(tile) in L.walk_tiles(q))


def _stair_course(L: Layout, p, foot, head) -> list[tuple[int, int]]:
    """The turning points of a landmark stair's walk from its foot to its head over the walk
    tiles its geometry lists (the engine walks only those; a straight line through the middle
    may cross balustrades or the plain between two flights), with the landings outside the
    foot and head edges to reach them. [] when the stair lists no walk tiles or a straight walk
    already uses only them."""
    walk = L.walk_tiles(p) if L.cat.items[p.id].landmark else set()
    if not walk:
        return []
    inside = {(c, r) for c in range(p.c, p.c + p.pw) for r in range(p.r, p.r + p.ph)}
    foot, head = tuple(foot), tuple(head)

    def edge_row(t):
        """The tiles outside the footprint on the same side as t (a landing row)."""
        if t[1] < p.r or t[1] >= p.r + p.ph:
            return {(c, t[1]) for c in range(p.c - 1, p.c + p.pw + 1)}
        return {(t[0], r) for r in range(p.r - 1, p.r + p.ph + 1)}

    ok = (walk & inside) | edge_row(foot) | edge_row(head) | {foot, head}
    prev, todo = {foot: None}, [foot]
    for t in todo:
        if t == head:
            break
        for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            n = (t[0] + dc, t[1] + dr)
            if n in ok and n not in prev and (n not in inside or n in walk):
                prev[n] = t
                todo.append(n)
    if head not in prev:
        return []
    path = [head]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    path.reverse()
    turns = [path[i] for i in range(1, len(path) - 1)
             if (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]) !=
             (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])]
    return turns


def derive_graph(L: Layout) -> tuple[Graph, list[Issue]]:
    issues: list[Issue] = []
    streets = L.streets
    bps: list[list[tuple[float, tuple[int, int]]]] = []
    for s in streets:
        pts = s.points if len(s.points) > 1 else s.points * 2
        bps.append([(float(i), tuple(p)) for i, p in enumerate(pts)])
    polys = [s.points if len(s.points) > 1 else s.points * 2 for s in streets]
    extra: list[tuple[tuple[int, int], tuple[int, int], str]] = []  # tile, tile, kind

    for i in range(len(streets)):
        for j in range(i + 1, len(streets)):
            for si, (a, b) in enumerate(zip(polys[i], polys[i][1:])):
                for sj, (c, d) in enumerate(zip(polys[j], polys[j][1:])):
                    hit = _intersect(a, b, c, d)
                    if hit:
                        t, u = hit
                        tile = (round(a[0] + t * (b[0] - a[0])), round(a[1] + t * (b[1] - a[1])))
                        bps[i].append((si + t, tile))
                        bps[j].append((sj + u, tile))
    same_level = _level_rule(L)
    # T-junctions: a street end near another street joins it. An end that already lies on a
    # street is joined there by the crossing above; otherwise it joins only the nearest street
    # within reach (joining every street within reach drew short diagonal edges across
    # whatever stood between two lanes that both start on a third), and only one at its own
    # level: streets on two levels meet only through a stair, a ramp or a deck.
    for i, s in enumerate(streets):
        for end in (polys[i][0], polys[i][-1]):
            near = []
            for j, o in enumerate(streets):
                if j == i:
                    continue
                dist, pos, tile = _project(end, polys[j])
                if dist <= o.width / 2 + 1 and same_level(tuple(end), tile):
                    near.append((dist, j, pos, tile))
            if not near or min(near)[0] < 1e-9:
                continue
            dist, j, pos, tile = min(near)
            bps[j].append((pos, tile))
            if tile != tuple(end):
                extra.append((tuple(end), tile, s.kind))

    named: dict[tuple[int, int], tuple[str, str]] = {}  # tile -> (id, kind)
    want: list[tuple[tuple[int, int], str]] = []  # named tiles that must join the streets
    for nid, (at, kind, src) in L.nodes.items():
        named[tuple(at)] = (nid, kind)
        want.append((tuple(at), nid))
    # A landing shared by two stairs (the head of one is the foot of the next) is joined by the
    # stair edges themselves; snapping it to the nearest street would skip the flights.
    ends: dict[tuple[int, int], int] = {}
    for p, foot, head in L.stair_edges:
        for tile in (foot, head):
            ends[tuple(tile)] = ends.get(tuple(tile), 0) + 1
    for p, foot, head in L.stair_edges:
        base = p.name or f"{p.id}@{p.c},{p.r}"
        for tile, tag in ((foot, "foot"), (head, "head")):
            named.setdefault(tuple(tile), (f"{base}.{tag}", None))
            # An end inside a landmark (the stair lands on its floor) is reached by the stair
            # alone: snapping it to the nearest street would cut across the flight or the walls.
            if ends[tuple(tile)] == 1 and not _on_floor(L, tile):
                want.append((tuple(tile), named[tuple(tile)][0]))
        extra.append((tuple(foot), tuple(head), "stair", _stair_course(L, p, foot, head)))
    for p, slot, nid, src in L.links:
        spots = p.slots.get(slot)
        if not spots:
            issues.append(Issue("V7", "error", L.layer,
                                f"link: {p.name or p.id} has no slot {slot!r}", src, (p.c, p.r)))
            continue
        if nid not in L.nodes:
            issues.append(Issue("V6", "error", L.layer, f"link: unknown node {nid!r}", src))
            continue
        tile = tuple(spots[0][:2])
        if tile not in named:
            named[tile] = (f"{p.name or p.id}.{slot}", "door" if slot == "door" else None)
        extra.append((tile, tuple(L.nodes[nid][0]), "track"))

    on_street = {t for lst in bps for _, t in lst}
    for tile, nid in want:
        if tile in on_street:
            continue
        best = (math.inf, None, None)
        for j, pts in enumerate(polys):
            dist, pos, proj = _project(tile, pts)
            if dist < best[0]:
                best = (dist, j, (pos, proj))
        if best[1] is not None and best[0] <= SNAP:
            pos, proj = best[2]
            bps[best[1]].append((pos, proj))
            if proj != tile:
                extra.append((tile, proj, streets[best[1]].kind if streets[best[1]].kind != "road"
                              else "track"))

    # Portals: the street end on the layer edge.
    portal_tiles: dict[tuple[int, int], str] = {}
    c0, r0 = L.origin
    c1, r1 = c0 + L.size[0] - 1, r0 + L.size[1] - 1
    for s in streets:
        if not s.portal:
            continue
        ends = [tuple(s.points[0]), tuple(s.points[-1])]
        on_edge = [e for e in ends if e[0] in (c0, c1) or e[1] in (r0, r1)]
        if not on_edge:
            issues.append(Issue("V6", "error", L.layer,
                                f"portal {s.portal!r}: neither end of its street is on the layer "
                                "edge", s.src, ends[0]))
            continue
        end = on_edge[0]
        decl = P.PORTALS.get(s.portal)
        plan_tile = tuple(decl[1]) if decl else end
        outside = not (c0 <= plan_tile[0] <= c1 and r0 <= plan_tile[1] <= r1)
        if outside and abs(plan_tile[0] - end[0]) + abs(plan_tile[1] - end[1]) == 1:
            # The plan's tile is the neighbouring layer's edge tile: the portal is one node of
            # both layers (world-tech §2.5), so this layer's node stands there too, a step
            # across its edge from its street's end.
            portal_tiles[plan_tile] = s.portal
            extra.append((end, plan_tile, s.kind))
        else:
            portal_tiles[end] = s.portal

    ids: dict[tuple[int, int], str] = {}
    kinds: dict[tuple[int, int], str | None] = {}
    order: list[tuple[int, int]] = []

    def node_for(tile):
        if tile not in ids:
            if tile in portal_tiles:
                ids[tile], kinds[tile] = portal_tiles[tile], "portal"
            elif tile in named:
                ids[tile], kinds[tile] = named[tile]
            else:
                ids[tile], kinds[tile] = f"n{len(ids)}", None
            order.append(tile)
        return ids[tile]

    g = Graph(L.layer)
    seen_edges = set()
    for s, lst, pts in zip(streets, bps, polys):
        lst.sort(key=lambda x: x[0])
        chain = []
        for pos, tile in lst:
            if chain and chain[-1][1] == tile:
                continue
            chain.append((pos, tile))
        for (pa, ta), (pb, tb) in zip(chain, chain[1:]):
            a, b = node_for(ta), node_for(tb)
            via = [tuple(pts[v]) for v in range(len(pts)) if pa < v < pb
                   and tuple(pts[v]) not in (ta, tb)]
            key = (min(a, b), max(a, b))
            if key in seen_edges:
                continue
            seen_edges.add(key)
            g.edges.append(Edge(a, b, s.kind, [to_grid(*p) for p in via]))
    for ta, tb, kind, *course in extra:
        a, b = node_for(ta), node_for(tb)
        key = (min(a, b), max(a, b))
        if a != b and key not in seen_edges:
            seen_edges.add(key)
            via = course[0] if course and course[0] else []
            g.edges.append(Edge(a, b, kind, [to_grid(*t) for t in via]))
    for tile in named:
        node_for(tile)
    for a, b, kind, via, src in L.edges:
        if a not in L.nodes or b not in L.nodes:
            issues.append(Issue("V6", "error", L.layer, f"edge {a} - {b}: unknown node", src))
            continue
        ta, tb = tuple(L.nodes[a][0]), tuple(L.nodes[b][0])
        na, nb = node_for(ta), node_for(tb)
        key = (min(na, nb), max(na, nb))
        if key not in seen_edges:
            seen_edges.add(key)
            g.edges.append(Edge(na, nb, kind, [to_grid(*p) for p in via]))
    for tile in order:
        g.nodes.append(Node(ids[tile], to_grid(*tile), kinds[tile]))
    for ln in L.lanes:
        g.lanes.append(Lane(ln.id, ln.kind, [to_grid(*p) for p in ln.points],
                            [Port(pid, at) for pid, at in sorted(ln.ports.items(),
                                                                 key=lambda x: (x[1], x[0]))]))
    return g, issues
