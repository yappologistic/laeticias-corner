"""Checks of the land's form on the composed world, run on every layer's own tiles:

  V18 faces: a raised land tile's face index (the level byte's aux) names one of its terrain's
      face materials (its own, else its base's: the engine's rule), and that material has face
      art on both sides (`edge/<material>_se/v0`, `_sw/v0`); otherwise the engine draws a flat,
      untextured fill (QA6 V6-003)
  V19 straight seams: two natural grounds never meet along one grid row or column for more
      than SEAM_MAX tiles (borders follow the land, not the plan's rectangles: QA6 V6-005);
      paving, earth roads, their verges, formal garden beds, water and the sea may run straight
  V20 markers: every map marker but the home's lies in its region and opens on built ground
  V21 floors: an interior floor (painted plaster) lies only on its building's own walk tiles,
      never past its doors; no base ground shows through paving
  V22 water steps: running water steps down over the edge it flows to (a rapid or a fall across
      the stream), never a level into the sea, and no stream tile juts out as a box
  V23 slopes: slope ground standing a level above a neighbour has art for every slope shape
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import seasons as S
from .catalog import Catalog
from .compose import NONE16, World

SEAM_MAX = 12
NATURAL = {"grass", "steppe", "scrub", "forest", "evergreen", "rock", "sand", "snow", "marsh",
           "crop"}
FORMAL = {"parsa.garden_bed"}
ROAD_WORDS = ("paving", "road", "packed_earth", "gravel", "path", "cobble")     # a paradise's beds are laid out by line and square


def natural_ids(terrains: list[str]) -> np.ndarray:
    return np.array([S.GROUND_OF.get(t) in NATURAL and t not in FORMAL for t in terrains] + [False])


def by_roads(terrains: list[str], T: np.ndarray) -> np.ndarray:
    """Tiles on or beside paving or an earth road: a verge runs as straight as its road."""
    road = np.array([any(k in t for k in ROAD_WORDS) for t in terrains] + [False])[T]
    out = road.copy()
    out[1:, :] |= road[:-1, :]
    out[:-1, :] |= road[1:, :]
    out[:, 1:] |= road[:, :-1]
    out[:, :-1] |= road[:, 1:]
    return out


@lru_cache(maxsize=4)
def face_art(root: str) -> frozenset[str]:
    """Materials with face art on both sides on any atlas page."""
    keys: set[str] = set()
    pages = [Path(root) / "assets/atlas.json"] + sorted((Path(root) / "assets/atlas").glob("*.json"))
    for f in pages:
        if f.name.endswith(".geom.json") or not f.exists():
            continue
        doc = json.loads(f.read_text())
        keys |= {k for k in doc.get("sprites", {}) if k.startswith("edge/")}
    mats = {k.split("/")[1].rsplit("_", 1)[0] for k in keys if k.endswith(("_se/v0", "_sw/v0"))}
    return frozenset(m for m in mats if f"edge/{m}_se/v0" in keys and f"edge/{m}_sw/v0" in keys)


def drops(world: World) -> np.ndarray:
    """Land or water tiles with a face: lower ground (or none) beyond their +x or +y edge, which
    in plan terms are the south (r + 1) and west (c - 1) neighbours."""
    lv = (world.L & 0x0F).astype(np.int16)
    has = world.T != NONE16
    south = np.where(has[1:, :], lv[1:, :], 0)
    west = np.where(has[:, :-1], lv[:, :-1], 0)
    out = np.zeros(lv.shape, dtype=bool)
    out[:-1, :] |= lv[:-1, :] > south
    out[:, 1:] |= lv[:, 1:] > west
    return out & has


def face_issues(world: World, cat: Catalog, root: Path, sl, mine: np.ndarray) -> list[tuple[str, tuple]]:
    """V18 on a layer's own tiles."""
    art = face_art(str(root))
    c0, r0 = sl[1].start, sl[0].start
    T = world.T[sl]
    aux = ((world.L[sl] >> 4) & 3).astype(np.int16)
    faced = drops(world)[sl] & mine
    out = []
    for t in np.unique(T[faced]).tolist():
        tid = world.terrains[t]
        if cat.is_water(tid):
            continue
        faces = cat.faces(tid)
        m = faced & (T == t)
        over = m & (aux >= len(faces))
        if over.any():
            j, i = np.argwhere(over)[0]
            out.append((f"{int(over.sum())} raised tile(s) of {tid} pick face {int(aux[j, i])}, "
                        f"but its faces are {faces}: the engine draws a flat fill",
                        (int(i) + c0, int(j) + r0)))
        for k, mat in enumerate(faces):
            used = m & (aux == k)
            if used.any() and mat not in art:
                j, i = np.argwhere(used)[0]
                out.append((f"{int(used.sum())} raised tile(s) of {tid} use face material {mat}, "
                            f"which has no face art (edge/{mat}_se/v0, _sw/v0)",
                            (int(i) + c0, int(j) + r0)))
    return out


def straight_seams(world: World, sl, mine: np.ndarray, limit: int = SEAM_MAX) -> list[tuple[str, tuple]]:
    """V19 on a layer's own tiles: runs of more than `limit` tiles along a row or column where
    the ground differs across the line and both sides are natural ground."""
    nat = natural_ids(world.terrains)
    T = world.T[sl].astype(np.int64)
    T[T == NONE16] = len(world.terrains)
    verge = by_roads(world.terrains, T)
    c0, r0 = sl[1].start, sl[0].start
    out = []
    for axis in (0, 1):
        A = T if axis == 0 else T.T
        M = mine if axis == 0 else mine.T
        V = verge if axis == 0 else verge.T
        diff = (A[:-1] != A[1:]) & nat[A[:-1]] & nat[A[1:]] & (M[:-1] | M[1:]) & \
            ~(V[:-1] | V[1:])
        for y in range(diff.shape[0]):
            row = np.concatenate(([False], diff[y], [False]))
            edges = np.flatnonzero(row[1:] != row[:-1])
            for s, e in zip(edges[::2], edges[1::2]):
                if e - s > limit:
                    a, b = world.terrains[A[y, s]], world.terrains[A[y + 1, s]]
                    at = (int(s) + c0, y + r0) if axis == 0 else (y + c0, int(s) + r0)
                    line = f"rows {at[1]}|{at[1] + 1}" if axis == 0 else f"columns {at[0]}|{at[0] + 1}"
                    out.append((f"{a} meets {b} in a straight line {int(e - s)} tiles long "
                                f"(plan {line}; at most {limit}): break the border with the land",
                                at))
    return out


WAVE = 3.0      # tiles a waved border swings to either side of its straight line
WAVE_SCALE = 5  # tiles along the border per swing
WAVE_MIN = 6    # straight runs longer than this are waved (V19 allows SEAM_MAX: a margin, so
#                 a border with a jog or two still reads as land, not as a ruled line)


def wave_seams(L, context=None, keep: np.ndarray | None = None) -> int:
    """`_wave_once` until no straight natural seam longer than WAVE_MIN is left among this
    layout's free tiles (a swing may leave a shorter straight piece of its own)."""
    total = 0
    for _ in range(4):
        n = _wave_once(L, context, keep)
        if not n:
            break
        total += n
    return total


def visible(L, context=None):
    """What a layout shows in the composed world, padded by a tile all round: (terrain ids,
    their index per tile or -1, levels, the tiles this layout itself shows). `context` is the
    composed world the layout sits in (`L.below` for a town, the committed authored layers for
    the base): its cells show through where this layout paints nothing and hide this layout
    where they lie over it."""
    h, w = L.T.shape
    c0, r0 = L.origin
    ids = list(L.terrains)
    index = {t: i for i, t in enumerate(ids)}
    vis = np.full((h + 2, w + 2), -1, dtype=np.int32)
    lvl = np.zeros((h + 2, w + 2), dtype=np.int32)
    own = np.zeros((h + 2, w + 2), dtype=bool)
    inner = (slice(1, h + 1), slice(1, w + 1))
    mine = L.T >= 0
    vis[inner] = np.where(mine, L.T, -1)
    lvl[inner] = L.LV + L.base_level
    own[inner] = mine
    if context is not None:
        rs = np.clip(np.arange(r0 - 1, r0 + h + 1), 0, context.T.shape[0] - 1)
        cs = np.clip(np.arange(c0 - 1, c0 + w + 1), 0, context.T.shape[1] - 1)
        cT = context.T[np.ix_(rs, cs)]
        cL = (context.L[np.ix_(rs, cs)] & 0x0F).astype(np.int32)
        has = cT != NONE16
        over = has if L.layer == "base" else has & ~np.pad(mine, 1, constant_values=False)
        for t in np.unique(cT[over]).tolist():
            if context.terrains[t] not in index:
                index[context.terrains[t]] = len(ids)
                ids.append(context.terrains[t])
        lut = np.array([index.get(t, -1) for t in context.terrains] + [-1], dtype=np.int32)
        cTi = np.where(has, cT, len(context.terrains)).astype(np.intp)
        vis = np.where(over, lut[cTi], vis)
        lvl = np.where(over, cL, lvl)
        own[inner] = mine & ~over[inner]
    return ids, vis, lvl, own


def _wave_once(L, context=None, keep: np.ndarray | None = None) -> int:
    """Break every straight run of more than WAVE_MIN tiles between two natural grounds that
    touches this layout's own visible tiles (V19): along the run the border swings by coherent
    noise, each own tile on the far side of the new line taking the terrain (and, where the
    level step follows the border, the level and face) of the tile across the old line. Only
    free tiles move (no street, item or reserved tile, nothing in `keep`; an impassable tile or
    one beside anything built takes the terrain only), and only to ground their region may
    carry. `context` as in
    `visible`. Returns the number of tiles changed."""
    from plan import world_plan as P
    from . import rng
    h, w = L.T.shape
    c0, r0 = L.origin
    ids, vis, lvl, own = visible(L, context)
    inner = (slice(1, h + 1), slice(1, w + 1))
    free = np.zeros_like(own)
    free[inner] = own[inner] & ~L.STREET & (L.OCC < 0) & ~L.RESERVED
    if keep is not None:
        free[inner] &= ~keep
    nat = natural_ids(ids)
    verge = by_roads(ids, np.where(vis >= 0, vis, len(ids)))

    def sets_ok(tid: str, j: int, i: int) -> bool:
        d = int(L.DIST[j - 1, i - 1])
        if d < 0:
            return True
        rid = L.districts[d].split("/", 1)[0]
        v = P.REGIONS.get(rid)
        if v is None or "." not in tid:
            return True
        return tid.split(".", 1)[0] in {"world", v[1], *P.SEAM_SETS.get(rid, ())}

    base_t = np.array([bool(L.cat.terrain.get(t) and L.cat.terrain[t].base) for t in ids] + [False])

    def bases_ok(t: int, j: int, i: int) -> bool:
        """Two base terrains never touch (V8): a base ground moves only among its own kind."""
        if not base_t[t]:
            return True
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= j + dj < h + 2 and 0 <= i + di < w + 2:
                u = vis[j + dj, i + di]
                if u >= 0 and base_t[u] and u != t:
                    return False
        return True

    moves: dict[tuple[int, int], tuple[int, int, tuple[int, int]]] = {}
    for axis in (0, 1):
        A = vis if axis == 0 else vis.T
        Lv = lvl if axis == 0 else lvl.T
        O = own if axis == 0 else own.T
        V = verge if axis == 0 else verge.T
        Ai = np.where(A >= 0, A, len(ids))
        diff = (A[:-1] != A[1:]) & nat[Ai[:-1]] & nat[Ai[1:]] & (O[:-1] | O[1:]) & \
            ~(V[:-1] | V[1:])
        for y in range(diff.shape[0]):
            row = np.concatenate(([False], diff[y], [False]))
            edges = np.flatnonzero(row[1:] != row[:-1])
            for s, e in zip(edges[::2].tolist(), edges[1::2].tolist()):
                if e - s <= WAVE_MIN:
                    continue
                stepped = bool(np.any(Lv[y, s:e] != Lv[y + 1, s:e]))
                xs = np.arange(s, e)
                # World coordinates along and across the line keep the swing a pure function of
                # where the border lies, whichever layer draws it.
                along = xs + (c0 if axis == 0 else r0) - 1
                across = y + (r0 if axis == 0 else c0) - 1
                n = rng.fbm(along.astype(np.float64), np.full(len(xs), float(across)),
                            WAVE_SCALE, rng.hash64("wave", axis), octaves=1) * 2 - 1
                n = n * 1.8          # one octave spreads to about ±0.55; never clipped, so
                #                       the swing has no flat run at its widest
                # The ends stay on the line, so the waved border meets what it continues.
                taper = np.minimum(1.0, np.minimum(xs - s + 1, e - xs) / 3.0)
                swing = np.rint(n * WAVE * taper).astype(int)
                for x, d in zip(xs.tolist(), swing.tolist()):
                    if d == 0:
                        continue
                    src, far = (y, y + 1) if d > 0 else (y + 1, y)   # the side that grows
                    sj, si = (src, x) if axis == 0 else (x, src)
                    fj, fi = (far, x) if axis == 0 else (x, far)
                    step = 1 if d > 0 else -1
                    for k in range(abs(d)):
                        yy = far + k * step
                        if not 0 <= yy < A.shape[0]:
                            break
                        j, i = (yy, x) if axis == 0 else (x, yy)
                        if not free[j, i] or vis[j, i] != vis[fj, fi] or \
                                not sets_ok(ids[vis[sj, si]], j, i) or \
                                not bases_ok(int(vis[sj, si]), j, i):
                            break
                        moves.setdefault((j, i), (int(vis[sj, si]),
                                                  int(lvl[sj, si] if stepped else lvl[j, i]),
                                                  (sj, si)))
    if not moves:
        return 0
    # Levels move only well away from anything built: a stair's landing, a door step or a
    # street's edge keeps the level it was laid for (the terrain may still move there).
    busy = (L.OCC >= 0) | L.STREET
    for (nc, nr), _kind, _src in L.nodes.values():     # a named place and the way to it
        jc, jr = nc - c0, nr - r0
        busy[max(jr - 1, 0):max(jr + 2, 0), max(jc - 1, 0):max(jc + 2, 0)] = True
    near = busy.copy()
    for dr, dc in N8:
        near |= shift(busy, dr, dc, False)
    applied = 0
    for (j, i), (t, lv_, (sj, si)) in moves.items():
        if not bases_ok(t, j, i):        # an earlier move may have changed a neighbour
            continue
        vis[j, i] = t
        applied += 1
        old_tid, tid = L.terrains[L.T[j - 1, i - 1]], ids[t]
        L.T[j - 1, i - 1] = L._terrain_index(tid, "landform.wave_seams")
        inside = 1 <= sj <= h and 1 <= si <= w and own[sj, si]
        if lv_ != L.LV[j - 1, i - 1] + L.base_level and not L.IMP[j - 1, i - 1] and \
                not near[j - 1, i - 1]:
            # The tile joins the other side whole: its level and its face come with it.
            L.LV[j - 1, i - 1] = lv_ - L.base_level
            L.FACE[j - 1, i - 1] = L.FACE[sj - 1, si - 1] if inside else -1
            L.AUX[j - 1, i - 1] = L.AUX[sj - 1, si - 1] if inside else -1
        elif L.FACE[j - 1, i - 1] >= 0 and L.faces[L.FACE[j - 1, i - 1]] not in L.cat.faces(tid):
            L.FACE[j - 1, i - 1] = -1     # the new ground's own first material
        elif L.AUX[j - 1, i - 1] >= 0:
            # A face chosen by index keeps its material where the new ground has it.
            of, nf = L.cat.faces(old_tid), L.cat.faces(tid)
            k = int(L.AUX[j - 1, i - 1])
            L.AUX[j - 1, i - 1] = nf.index(of[k]) if k < len(of) and of[k] in nf else -1
    return applied


MARKER_VIEW = 10        # tiles round a marker the map's journey opens on (a 1x view's middle)
MARKER_BUILT = 0.06     # share of that view a town's built pieces cover, at least
MARKER_NEAR = 2         # tiles from the marker to the nearest built piece, at most
NATURAL_PROPS = {"world.boulder", "world.crag", "world.peak"}


def built_mask(world: World, cat: Catalog) -> np.ndarray:
    """Tiles under built pieces: everything placed but plants and natural props."""
    from .compose import live_items
    m = np.zeros(world.occ.shape, dtype=bool)
    for _, it in live_items(world):
        d = cat.items.get(it.id)
        if d is None or d.extra.get("season_class") or it.id in NATURAL_PROPS:
            continue
        m[it.r:it.r + it.ph, it.c:it.c + it.pw] = True
    return m


def marker_issues(world: World, cat: Catalog, regions) -> list[tuple[str, tuple]]:
    """V20: the map marker of every named place but the home (the player's own) lies in its
    region and opens on the place: built pieces cover at least MARKER_BUILT of the view round
    it and one stands within MARKER_NEAR tiles (QA6 V6-010)."""
    from plan import world_plan as P
    reg, names = S.region_grid(world)
    built = None
    out = []
    for rid, (c, r), _icon in P.MARKERS:
        if rid not in regions or P.REGIONS[rid][0] == "home":
            continue
        if built is None:
            built = built_mask(world, cat)
        here = names[reg[r, c]] if reg[r, c] >= 0 else None
        if here != rid:
            out.append((f"the map marker of {rid} lies in {here}, not in its own region", (c, r)))
            continue
        k = MARKER_VIEW
        win = built[max(r - k, 0):r + k + 1, max(c - k, 0):c + k + 1]
        near = built[max(r - MARKER_NEAR, 0):r + MARKER_NEAR + 1,
                     max(c - MARKER_NEAR, 0):c + MARKER_NEAR + 1]
        if win.mean() < MARKER_BUILT or not near.any():
            out.append((f"the map marker of {rid} opens on {win.mean():.0%} built ground (at least "
                        f"{MARKER_BUILT:.0%}, a building within {MARKER_NEAR} tiles): move it to "
                        "the place (plan MARKER_AT) or build the place there", (c, r)))
    return out


# Floors drawn only inside a building: painted plaster belongs under its halls' walk tiles.
INTERIOR_FLOORS = {"parsa.paving_red"}


def paved_ids(terrains: list[str]) -> np.ndarray:
    return np.array(["paving" in t or t == "cobble" for t in terrains] + [False])


def paving_holes(T: np.ndarray, lv: np.ndarray, paved: np.ndarray, base: np.ndarray,
                 free: np.ndarray) -> np.ndarray:
    """Base ground showing through paving: a free tile of a base terrain with paving at its own
    level on three or four sides (T holds indices into `paved`/`base`, the last one "none")."""
    n = np.zeros(T.shape, dtype=np.int8)
    P_ = paved[T]
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = np.zeros(T.shape, dtype=bool)
        src = (slice(max(dr, 0), T.shape[0] + min(dr, 0)), slice(max(dc, 0), T.shape[1] + min(dc, 0)))
        dst = (slice(max(-dr, 0), T.shape[0] + min(-dr, 0)), slice(max(-dc, 0), T.shape[1] + min(-dc, 0)))
        nb[dst] = P_[src] & (lv[src] == lv[dst])
        n += nb
    return base[T] & (n >= 3) & free


def floor_issues(world: World, cat: Catalog, sl, mine: np.ndarray) -> list[tuple[str, tuple]]:
    """V21 on a layer's own tiles: an interior floor lies only on walk tiles of the landmark
    whose footprint holds it (never past its doors); no base ground shows through paving."""
    from .compose import live_items
    from .validate import item_walk_tiles
    c0, r0 = sl[1].start, sl[0].start
    out = []
    floor_t = [i for i, t in enumerate(world.terrains) if t in INTERIOR_FLOORS]
    if floor_t:
        on = np.isin(world.T[sl], floor_t) & mine
        if on.any():
            hall = np.zeros(on.shape, dtype=bool)
            for _, it in live_items(world):
                d = cat.items.get(it.id)
                if d is None or not d.landmark:
                    continue
                for c, r in item_walk_tiles(cat, it):
                    if it.c <= c < it.c + it.pw and it.r <= r < it.r + it.ph and \
                            0 <= r - r0 < on.shape[0] and 0 <= c - c0 < on.shape[1]:
                        hall[r - r0, c - c0] = True
            bad = on & ~hall
            if bad.any():
                j, i = np.argwhere(bad)[0]
                out.append((f"{int(bad.sum())} tile(s) of an interior floor "
                            f"({world.terrains[world.T[sl][j, i]]}) outside the walk tiles of the "
                            "building that holds them", (int(i) + c0, int(j) + r0)))
    T = np.where(world.T[sl] == NONE16, len(world.terrains), world.T[sl]).astype(np.intp)
    base = np.array([bool(cat.terrain.get(t) and cat.terrain[t].base) for t in world.terrains]
                    + [False])
    holes = paving_holes(T, (world.L[sl] & 0x0F), paved_ids(world.terrains), base,
                         mine & (world.occ[sl] < 0))
    if holes.any():
        j, i = np.argwhere(holes)[0]
        out.append((f"{int(holes.sum())} tile(s) of base ground showing through paving",
                    (int(i) + c0, int(j) + r0)))
    return out


def close_paving_holes(L, context=None) -> int:
    """Pave the free base-ground tiles of a layout that paving encloses (V21), the paving of
    the world round it included (`context` as in `visible`); a paved hole may close the next."""
    total = 0
    for _ in range(64):
        ids, vis, lvl, own = visible(L, context)
        T = np.where(vis >= 0, vis, len(ids)).astype(np.intp)
        base = np.array([bool(L.cat.terrain.get(t) and L.cat.terrain[t].base) for t in ids]
                        + [False])
        paved = paved_ids(ids)
        free = own.copy()
        free[1:-1, 1:-1] &= (L.OCC < 0) & ~L.RESERVED
        holes = paving_holes(T, lvl, paved, base, free)
        if not holes.any():
            break
        for j, i in zip(*np.nonzero(holes)):
            near = [int(T[j + dj, i + di]) for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if paved[T[j + dj, i + di]]]
            L.T[j - 1, i - 1] = L._terrain_index(ids[max(set(near), key=near.count)],
                                                 "landform.close_paving_holes")
        total += int(holes.sum())
    return total


# --- slopes (art contract: out/reports/art-smooth-land.md §3) --------------------------------

# Natural ground whose steps of two levels or more stay cliffs: rock shows its faces.
CLIFF_GROUND = {"world.rock", "athens.rock_limestone", "rome.tufa_rock", "parsa.rough_ground"}
# Faces of built edges: a step whose upper tile carries one of these is a wall, never a slope.
BUILT_FACES = {"world.basalt", "parsa.ashlar", "athens.ashlar", "rome.brick", "rome.travertine"}
N8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


@lru_cache(maxsize=4)
def slope_ground(root: str) -> frozenset[str]:
    """Terrains the art draws as slopes (every set catalog's `art.slopes`)."""
    out: set[str] = set()
    for f in sorted((Path(root) / "assets/sets").glob("*/catalog.json")):
        out |= set(json.loads(f.read_text()).get("art", {}).get("slopes", []))
    return frozenset(out)


def shift(a: np.ndarray, dr: int, dc: int, fill) -> np.ndarray:
    out = np.full_like(a, fill)
    h, w = a.shape
    out[max(dr, 0):h + min(dr, 0), max(dc, 0):w + min(dc, 0)] = \
        a[max(-dr, 0):h + min(-dr, 0), max(-dc, 0):w + min(-dc, 0)]
    return out


def grade(level: np.ndarray, eligible: np.ndarray, water: np.ndarray) -> int:
    """Raise slope ground so no two 8-neighbours of it lie more than a level apart (§3.6): each
    eligible tile rises to one below its highest eligible neighbour, never more than a level
    above water beside it; nothing is lowered, and ground that is not eligible (rock, built or
    authored ground, water) neither moves nor pulls. Returns the tiles raised."""
    lv = level.astype(np.int16)
    wl = np.where(water, lv, 99).astype(np.int16)
    near_water = np.full(lv.shape, 99, dtype=np.int16)
    for dr, dc in N8:
        near_water = np.minimum(near_water, shift(wl, dr, dc, 99))
    cap = np.where(near_water < 99, near_water + 1, 15)
    start = lv.copy()
    for _ in range(16):
        src = np.where(eligible, lv, -1).astype(np.int16)
        top = np.full(lv.shape, -1, dtype=np.int16)
        for dr, dc in N8:
            top = np.maximum(top, shift(src, dr, dc, -1))
        new = np.where(eligible, np.maximum(lv, np.minimum(top - 1, cap)), lv)
        if (new == lv).all():
            break
        lv = new
    level[:] = lv
    return int((lv != start).sum())


def lone_steps(level: np.ndarray, free: np.ndarray) -> int:
    """Single-tile spikes and pits on free ground (three or four of their four neighbours on one
    side of them) take the middle level of those neighbours. Returns the count."""
    n = 0
    for _ in range(4):
        nb = np.stack([shift(level, dr, dc, -1) for dr, dc in N8[:4]])
        valid = nb >= 0
        up = (valid & (nb > level[None])).sum(axis=0)
        down = (valid & (nb < level[None])).sum(axis=0)
        odd = free & ((up >= 3) | (down >= 3))
        if not odd.any():
            break
        med = np.sort(np.where(valid, nb, level[None]), axis=0)[1:3].mean(axis=0)
        level[odd] = np.rint(med[odd]).astype(level.dtype)
        n += int(odd.sum())
    return n


# --- water steps (art contract §4: rapids and falls) ------------------------------------------

FLOW_STEP = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}   # aux -> plan (dr, dc)
SEA = ("world.sea", "world.shallows")


def water_issues(world: World, cat: Catalog, sl, mine: np.ndarray) -> list[tuple[str, tuple]]:
    """V22 on a layer's own tiles: where running water steps down to water it leaves the upper
    tile by the edge it falls over (its flow), so the step reads as a rapid (one level) or a fall
    (more) across the stream, never as a bank inside it; no river steps a single level into the
    sea (its mouth lies at the sea's level, or it falls over a cliff) unless a crossing stands
    within two tiles; no river tile juts out
    with lower ground or water on two or more sides (a box of water in plan)."""
    T = world.T[sl]
    Ti = np.where(T == NONE16, len(world.terrains), T).astype(np.intp)
    water = np.array([cat.is_water(t) for t in world.terrains] + [False])[Ti]
    sea = np.isin(T, [i for i, t in enumerate(world.terrains) if t in SEA])
    run = water & ~sea & mine
    c0, r0 = sl[1].start, sl[0].start
    lv = (world.L[sl] & 0x0F).astype(np.int16)
    flow = ((world.L[sl] >> 4) & 3).astype(np.int8)
    # A crossing at the mouth holds the river at the level it was built for: there the mouth may
    # step a level into the sea.
    from .compose import live_items
    deck = np.zeros(run.shape, dtype=bool)
    for _, it in live_items(world):
        d = cat.items.get(it.id)
        if d is not None and (d.walkable or d.extra.get("crossing")) and d.on in ("water", "any"):
            r, c = it.r - r0, it.c - c0
            deck[max(r - 2, 0):max(r + it.ph + 2, 0), max(c - 2, 0):max(c + it.pw + 2, 0)] = True
    deck_near = deck
    side = np.zeros_like(run)
    into_sea = np.zeros_like(run)
    lower = np.zeros(run.shape, dtype=np.int8)
    for dr, dc in FLOW_STEP.values():
        nlv = shift(np.where(T != NONE16, lv, -1), -dr, -dc, -1)
        nwater = shift(water, -dr, -dc, False)
        nsea = shift(sea, -dr, -dc, False)
        f = next(k for k, v in FLOW_STEP.items() if v == (dr, dc))
        down = run & (nlv >= 0) & (nlv < lv)
        side |= down & nwater & ~nsea & (flow != f)
        into_sea |= down & nsea & (lv - nlv == 1) & ~deck_near
        lower += down.astype(np.int8)
    out = []
    for m, what in ((side, "steps down to water beside it, not over the edge it flows to"),
                    (into_sea, "steps a single level into the sea (let its mouth lie at the "
                               "sea's level, or fall over a cliff)"),
                    (run & (lower >= 2), "juts out with lower ground or water on two sides or "
                                         "more (end the stream at the bank or cliff line)")):
        if m.any():
            j, i = np.argwhere(m)[0]
            out.append((f"{int(m.sum())} running-water tile(s) {what}", (int(i) + c0, int(j) + r0)))
    return out


SLOPE_SHAPES = tuple(f"c{m}" for m in range(1, 15)) + (
    "knoll", "ridge_x", "ridge_x0", "ridge_x1", "ridge_y", "ridge_y0", "ridge_y1")


@lru_cache(maxsize=4)
def slope_art(root: str) -> dict[str, frozenset[str]]:
    """The slope shapes each terrain has art for (`terrain/<id>/slope/<shape>/v0`)."""
    out: dict[str, set[str]] = {}
    pages = [Path(root) / "assets/atlas.json"] + sorted((Path(root) / "assets/atlas").glob("*.json"))
    for f in pages:
        if f.name.endswith(".geom.json") or not f.exists():
            continue
        for k in json.loads(f.read_text()).get("sprites", {}):
            parts = k.split("/")
            if len(parts) == 5 and parts[0] == "terrain" and parts[2] == "slope" and parts[4] == "v0":
                out.setdefault(parts[1], set()).add(parts[3])
    return {t: frozenset(v) for t, v in out.items()}


def slope_issues(world: World, cat: Catalog, root: Path, sl, mine: np.ndarray) -> list[tuple[str, tuple]]:
    """V23 on a layer's own tiles: every slope ground (the catalogs' `art.slopes`) standing a
    level above a neighbour, where it draws as a slope, has art for every slope shape."""
    slope, art = slope_ground(str(root)), slope_art(str(root))
    T = world.T[sl]
    lv = (world.L[sl] & 0x0F).astype(np.int16)
    has = T != NONE16
    step = np.zeros(T.shape, dtype=bool)
    for dr, dc in N8:
        nl = shift(np.where(has, lv, -9), dr, dc, -9)
        step |= nl == lv - 1
    c0, r0 = sl[1].start, sl[0].start
    out = []
    for t in np.unique(T[step & mine & has]).tolist():
        tid = world.terrains[t]
        if tid not in slope:
            continue
        missing = [s for s in SLOPE_SHAPES if s not in art.get(tid, frozenset())]
        if missing:
            j, i = np.argwhere(step & mine & (T == t))[0]
            out.append((f"{tid} draws as slopes here, but has no art for {missing[:4]}"
                        f"{' …' if len(missing) > 4 else ''} (terrain/{tid}/slope/<shape>/v0)",
                        (int(i) + c0, int(j) + r0)))
    return out


def slope_tiles(world: World, cat: Catalog, root: Path) -> np.ndarray:
    """Tiles that may slope (art contract §3.1): slope ground with nothing on it that needs flat
    ground (what rides a slope is a one-tile piece that is no landmark, deck, stair or building
    and not on water) and no masonry face (a built edge). A step of one level onto or off such a
    tile is walkable (§3.2): the surface meets the other tile along their shared edge."""
    from .compose import live_items
    cached = getattr(world, "_slope_tiles", None)
    if cached is not None:
        return cached
    slope = slope_ground(str(root))
    ids = [i for i, t in enumerate(world.terrains) if t in slope]
    ok = np.isin(world.T, ids)
    aux = (world.L >> 4) & 3
    for i in ids:
        faces = cat.faces(world.terrains[i])
        for k, mat in enumerate(faces):
            if mat in BUILT_FACES:
                ok &= ~((world.T == i) & (aux == k))
    for _, it in live_items(world):
        d = cat.items.get(it.id)
        rides = d is not None and it.pw * it.ph == 1 and not d.landmark and not d.walkable and \
            not d.rise and not d.has_door and d.on != "water"
        if not rides:
            ok[it.r:it.r + it.ph, it.c:it.c + it.pw] = False
    world._slope_tiles = ok     # one world, asked once per region by the life checks
    return ok


def step_ok(lv, stair, slope, a, b) -> bool:
    """A walker's step from plan tile a to b: level, a stair or deck, or one level by a slope."""
    la, lb = int(lv[a[1], a[0]]), int(lv[b[1], b[0]])
    if la == lb or stair[a[1], a[0]] or stair[b[1], b[0]]:
        return True
    return abs(la - lb) == 1 and slope is not None and bool(slope[a[1], a[0]] or slope[b[1], b[0]])
