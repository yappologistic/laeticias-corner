"""The layout API (world-tech §3.3): a region authored as code in local plan coordinates.

A region source is a module with `build(L: Layout)`. Calls apply in order and later calls win on
the same tiles, except `place`, which reports an error when its footprint is taken. Fillers
(`scatter`, `row`, `houses`, `fields`, `wall`, `river` banks) skip tiles that are taken or
unsuitable. Every random choice is a pure function of (region, seed, tile), so editing one part of
a layout never reshuffles another part.

Coordinates: local plan (c east, r south) from the region's north-west corner; rects are inclusive
(c0, r0, c1, r1). Levels are local: the region's base level is added when compiling. Facings are
compass words ("west", "north", "east", "south").
"""

from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import rng
from .catalog import Catalog
from .coords import FACINGS, PLAN_STEP, where
from .shapes import Line, Mask, Rect, Shape, as_shape

TRANSPARENT = -1
NO_GROUND = -2
_PKG = str(Path(__file__).resolve().parent)


def _src() -> str:
    """file:line of the first caller outside the worldgen package (the layout source line)."""
    f = sys._getframe(1)
    while f is not None and str(Path(f.f_code.co_filename).resolve()).startswith(_PKG):
        f = f.f_back
    if f is None:
        return "?"
    p = Path(f.f_code.co_filename).resolve()
    for anchor in ("tools/worldgen/",):
        s = str(p)
        if anchor in s:
            return s.split(anchor, 1)[1] + f":{f.f_lineno}"
    return f"{p.name}:{f.f_lineno}"


@dataclass
class Issue:
    code: str
    level: str  # "error" | "warning"
    layer: str
    message: str
    src: str | None = None
    at: tuple[int, int] | None = None  # world plan tile

    def text(self, origin: tuple[int, int] | None = None) -> str:
        loc = f" at {where(self.at[0], self.at[1], origin)}" if self.at else ""
        src = f" [{self.src}]" if self.src else ""
        return f"{self.level.upper():7} {self.code:4} {self.layer}: {self.message}{loc}{src}"


@dataclass
class Placed:
    """A placed item, in world plan coordinates (c, r = north-west tile of the footprint)."""

    index: int
    id: str
    c: int
    r: int
    pw: int
    ph: int
    k: int  # rotation k or look
    name: str | None
    src: str
    face: str | None = None
    door: tuple[int, int] | None = None  # derived door tile for kit without geometry
    slots: dict = field(default_factory=dict)  # slot id -> [(c, r, face)]
    removed: bool = False

    @property
    def rect(self) -> Rect:
        return Rect(self.c, self.r, self.c + self.pw - 1, self.r + self.ph - 1)

    def tiles(self):
        for r in range(self.r, self.r + self.ph):
            for c in range(self.c, self.c + self.pw):
                yield c, r


@dataclass
class Street:
    points: list[tuple[int, int]]  # world plan
    width: int
    paving: str
    kind: str
    portal: str | None
    src: str

    def path(self) -> list[tuple[int, int]]:
        return Line(self.points, 1).path()


@dataclass
class LaneSpec:
    id: str
    kind: str
    points: list[tuple[int, int]]
    ports: dict[str, int]
    src: str


@dataclass
class Expect:
    landmark: str
    rect: Rect  # world plan
    level: int | None
    src: str


def _grid_dir_of(dc: int, dr: int) -> int:
    """River flow enum from a plan step: 0 = -y (east), 1 = +x (south), 2 = +y (west), 3 = -x."""
    if abs(dc) >= abs(dr):
        return 0 if dc > 0 else 2
    return 1 if dr > 0 else 3


class Layout:
    def __init__(self, *, layer: str, region: str, set: str, origin: tuple[int, int],
                 size: tuple[int, int], base_level: int, catalog: Catalog,
                 regions: list[str] | None = None, source: str = ""):
        self.layer = layer
        self.region = region
        self.set = set
        self.origin = tuple(origin)
        self.size = tuple(size)
        self.base_level = base_level
        self.cat = catalog
        self.regions = list(regions or [region])
        self.source = source
        w, h = self.size
        self.T = np.full((h, w), TRANSPARENT, dtype=np.int16)
        self.LV = np.zeros((h, w), dtype=np.int16)
        self.AUX = np.full((h, w), -1, dtype=np.int8)
        self.FACE = np.full((h, w), -1, dtype=np.int16)
        self.IMP = np.zeros((h, w), dtype=bool)
        self.DIST = np.full((h, w), -1, dtype=np.int16)
        self.OCC = np.full((h, w), -1, dtype=np.int32)
        self.STREET = np.zeros((h, w), dtype=bool)
        self.RESERVED = np.zeros((h, w), dtype=bool)
        self.terrains: list[str] = []
        self.faces: list[str] = []
        self.districts: list[str] = []
        self.items: list[Placed] = []
        self.streets: list[Street] = []
        self.nodes: dict[str, tuple[tuple[int, int], str, str]] = {}  # id -> (at, kind, src)
        self.links: list[tuple[Placed, str, str, str]] = []
        self.edges: list[tuple[str, str, str, list, str]] = []
        self.stair_edges: list[tuple[Placed, tuple[int, int], tuple[int, int]]] = []
        self.lanes: list[LaneSpec] = []
        self.expects: list[Expect] = []
        self.moves: dict[str, tuple[Rect, str, str]] = {}  # landmark -> (rect, why, src)
        self.views: dict[str, Rect] = {}
        self.sightlines: dict[str, np.ndarray] = {}  # name -> local mask (V15)
        self.issues: list[Issue] = []
        self.below = None  # the composed committed layers under this one (compose.World)
        self.graphs: dict = {}  # the graphs of the layers known to the build (fresh or committed)

    # -- helpers ------------------------------------------------------------------------------

    def _err(self, code: str, msg: str, src: str, at=None, level: str = "error") -> None:
        self.issues.append(Issue(code, level, self.layer, msg, src, at))

    def _world(self, shape) -> Shape:
        return as_shape(shape).shifted(*self.origin)

    def _mask(self, shape) -> np.ndarray:
        w, h = self.size
        return self._world(shape).mask(self.origin[0], self.origin[1], w, h)

    def _local(self, c: int, r: int) -> tuple[int, int]:
        """World plan -> array index (j, i), or None outside the layer."""
        i, j = c - self.origin[0], r - self.origin[1]
        if 0 <= i < self.size[0] and 0 <= j < self.size[1]:
            return j, i
        return None

    def _terrain_index(self, terrain: str, src: str) -> int:
        if terrain not in self.terrains:
            if terrain not in self.cat.terrain:
                self._err("V1", f"unknown terrain {terrain!r}", src)
            self.terrains.append(terrain)
        return self.terrains.index(terrain)

    def _district_name(self, name: str, src: str) -> str:
        full = name if "/" in name else f"{self.region}/{name}"
        if full.split("/", 1)[0] not in self.regions:
            self._err("V1", f"district {full!r} is not in this layer's regions {self.regions}", src)
        return full

    def terrain_at(self, c: int, r: int) -> str | None:
        """Terrain id at a world plan tile of this layer (None if transparent or outside)."""
        loc = self._local(c, r)
        if loc is None or self.T[loc] < 0:
            return None
        return self.terrains[self.T[loc]]

    def _rot(self, item, face: str, variant: int) -> int:
        d = self.cat.items[item]
        if d.layout == "rotate":
            k = FACINGS[face] % max(d.count, 1)
            if d.landmark and k not in d.rotations:
                k = d.rotations[0]
            return k
        if d.layout == "connect":
            return 0
        return variant % max(d.count, 1)

    def _plan_size(self, item: str, k: int) -> tuple[int, int]:
        fx, fy = self.cat.items[item].footprint_k(k)
        return fy, fx  # plan width = grid y extent, plan height = grid x extent

    def _suitable(self, item: str, c: int, r: int, pw: int, ph: int) -> bool:
        """Free, inside, ground of the right kind, flat, not street or reserved, passable."""
        d = self.cat.items[item]
        lv = None
        for rr in range(r, r + ph):
            for cc in range(c, c + pw):
                loc = self._local(cc, rr)
                if loc is None or self.OCC[loc] >= 0 or self.STREET[loc] or self.RESERVED[loc]:
                    return False
                t = self.T[loc]
                if t < 0 or self.IMP[loc]:
                    return False
                water = self.cat.is_water(self.terrains[t])
                if (d.on == "land" and water) or (d.on == "water" and not water):
                    return False
                if lv is None:
                    lv = self.LV[loc]
                elif self.LV[loc] != lv:
                    return False
        return True

    def _occupy(self, p: Placed) -> None:
        for c, r in p.tiles():
            loc = self._local(c, r)
            if loc is not None:
                self.OCC[loc] = p.index

    def _door_and_slots(self, p: Placed) -> None:
        """Slots from geometry (rotated footprint coords -> plan), else a derived front door."""
        geo = self.cat.slots(p.id, p.k)
        d = self.cat.items[p.id]
        if geo:
            # Footprint offset (dx south, dy west) from the origin tile (north-east corner).
            ne_c = p.c + p.pw - 1
            for sid, spots in geo.items():
                p.slots[sid] = [(ne_c - s["t"][1], p.r + s["t"][0], s.get("face")) for s in spots]
            if "door" in p.slots:
                p.door = p.slots["door"][0][:2]
        elif d.layout == "rotate" and p.face and d.has_door:
            dc, dr = PLAN_STEP[p.face]
            mid_c = p.c + (p.pw - 1) // 2
            mid_r = p.r + (p.ph - 1) // 2
            if dc < 0:
                p.door = (p.c - 1, mid_r)
            elif dc > 0:
                p.door = (p.c + p.pw, mid_r)
            elif dr < 0:
                p.door = (mid_c, p.r - 1)
            else:
                p.door = (mid_c, p.r + p.ph)

    def _new_placed(self, item, c, r, k, name, src, face) -> Placed:
        pw, ph = self._plan_size(item, k)
        p = Placed(len(self.items), item, c, r, pw, ph, k, name, src, face)
        self._door_and_slots(p)
        return p

    # -- what lies below -----------------------------------------------------------------------
    # Read-only views of the committed layers under this one (at least the base), in local
    # coordinates, so a layer can follow the generated coast, rivers and levels at its edges.

    def below_terrain(self, c: int, r: int) -> str | None:
        if self.below is None:
            return None
        return self.below.terrain_id(c + self.origin[0], r + self.origin[1])

    def below_level(self, c: int, r: int) -> int:
        """World level below, minus this region's base level (so it compares with local levels)."""
        if self.below is None:
            return 0
        return self.below.level(c + self.origin[0], r + self.origin[1]) - self.base_level

    def below_where(self, pred) -> Shape:
        """Local shape of the tiles whose terrain below satisfies pred(terrain_id)."""
        w, h = self.size
        if self.below is None:
            return Mask(0, 0, np.zeros((h, w), dtype=bool))
        sub = self.below.T[self.origin[1]:self.origin[1] + h, self.origin[0]:self.origin[0] + w]
        ok = np.array([bool(pred(t)) for t in self.below.terrains] + [False])
        idx = np.where(sub == 0xFFFF, len(self.below.terrains), sub)
        return Mask(0, 0, ok[idx])

    def coast_below(self) -> Shape:
        """Land tiles below that touch the sea (4-neighbours): where sea cliffs and beaches go."""
        w, h = self.size
        sea = self.sea_below().mask(0, 0, w, h)
        land = self.land_below().mask(0, 0, w, h)
        near = np.zeros_like(sea)
        near[1:, :] |= sea[:-1, :]
        near[:-1, :] |= sea[1:, :]
        near[:, 1:] |= sea[:, :-1]
        near[:, :-1] |= sea[:, 1:]
        return Mask(0, 0, land & near)

    def land_below(self) -> Shape:
        return self.below_where(lambda t: not self.cat.is_water(t))

    def sea_below(self) -> Shape:
        return self.below_where(lambda t: t in ("world.sea", "world.shallows"))

    # -- ground -------------------------------------------------------------------------------

    def fill(self, terrain: str, level: int = 0, district: str | None = None) -> None:
        src = _src()
        self.T[:] = self._terrain_index(terrain, src)
        self.LV[:] = level
        if district:
            self.DIST[:] = self._dist_index(district, src)

    def paint(self, shape, terrain: str) -> None:
        src = _src()
        self.T[self._mask(shape)] = self._terrain_index(terrain, src)

    def no_ground(self, shape) -> None:
        """Open sky: the tile has no ground at all (the home island's rim, chasms)."""
        self.T[self._mask(shape)] = NO_GROUND

    def level(self, shape, level: int, face: str | None = None) -> None:
        src = _src()
        m = self._mask(shape)
        self.LV[m] = level
        if face:
            if face not in self.faces:
                self.faces.append(face)
            self.FACE[m] = self.faces.index(face)

    def impassable(self, shape) -> None:
        self.IMP[self._mask(shape)] = True

    def _dist_index(self, name: str, src: str) -> int:
        full = self._district_name(name, src)
        if full not in self.districts:
            self.districts.append(full)
        return self.districts.index(full)

    def district(self, name: str, shape) -> None:
        src = _src()
        self.DIST[self._mask(shape)] = self._dist_index(name, src)

    def transparent(self, shape) -> None:
        m = self._mask(shape)
        self.T[m] = TRANSPARENT
        for p in self.items:
            if not p.removed and any(m[loc] for loc in map(lambda t: self._local(*t), p.tiles())
                                     if loc is not None):
                self._remove(p)

    def _remove(self, p: Placed) -> None:
        p.removed = True
        for c, r in p.tiles():
            loc = self._local(c, r)
            if loc is not None and self.OCC[loc] == p.index:
                self.OCC[loc] = -1

    # -- things -------------------------------------------------------------------------------

    def place(self, item: str, *, rect=None, at: tuple[int, int] | None = None,
              face: str = "west", variant: int = 0, name: str | None = None) -> Placed | None:
        """Place one item. `at` is the footprint's north-west tile; `rect` the whole footprint
        (checked against the catalog footprint after rotation)."""
        src = _src()
        if item in self.cat.retired:
            self._err("V1", f"{item!r} is a retired stand-in; use {self.cat.retired[item]}", src)
            return None
        if item not in self.cat.items:
            self._err("V1", f"unknown item {item!r}", src,
                      at=(self.origin[0] + (at or rect)[0], self.origin[1] + (at or rect)[1]))
            return None
        if face not in FACINGS:
            self._err("V1", f"{item}: facing {face!r} is not one of {list(FACINGS)}", src)
            return None
        k = self._rot(item, face, variant)
        pw, ph = self._plan_size(item, k)
        if rect is not None:
            rr = as_shape(rect)
            if (rr.w, rr.h) != (pw, ph):
                self._err("V4", f"{name or item}: rect {rr.w} x {rr.h} does not match the catalog "
                          f"footprint {pw} x {ph} (east-west x north-south, facing {face})", src,
                          at=(self.origin[0] + rr.c0, self.origin[1] + rr.r0))
                return None
            c, r = rr.c0, rr.r0
        elif at is not None:
            c, r = at
        else:
            raise TypeError("place() needs rect= or at=")
        c, r = c + self.origin[0], r + self.origin[1]
        p = self._new_placed(item, c, r, k, name, src, face)
        for cc, rr_ in p.tiles():
            loc = self._local(cc, rr_)
            if loc is None:
                self._err("V9", f"{name or item}: footprint leaves the layer", src, at=(cc, rr_))
                return None
            if self.OCC[loc] >= 0:
                other = self.items[self.OCC[loc]]
                if (cc, rr_) in self.walk_tiles(other):
                    continue  # furniture on a landmark's walk tile (world-tech §1.13)
                self._err("V2", f"{name or item} overlaps {other.name or other.id} "
                          f"(placed at {other.src})", src, at=(cc, rr_))
                return None
        self.items.append(p)
        self._occupy(p)
        return p

    def fits(self, item: str, at: tuple[int, int], face: str = "west", variant: int = 0) -> bool:
        """Whether `place(item, at=at, face=face)` would stand on free, flat, suitable ground
        off the streets (for detail that should give way rather than fail)."""
        if item not in self.cat.items or face not in FACINGS:
            return False
        k = self._rot(item, face, variant)
        pw, ph = self._plan_size(item, k)
        return self._suitable(item, at[0] + self.origin[0], at[1] + self.origin[1], pw, ph)

    def walk_tiles(self, p: Placed) -> set[tuple[int, int]]:
        """World plan tiles of a placed landmark that its geometry file declares walkable."""
        if not self.cat.items[p.id].landmark:
            return set()
        ne_c = p.c + p.pw - 1
        return {(ne_c - dy, p.r + dx) for dx, dy in self.cat.walk_tiles(p.id, p.k)}

    def remove(self, p: Placed) -> None:
        """Take a placed item out again (a layout thinning its own fillers)."""
        if not p.removed:
            self._remove(p)

    def _try_place(self, item: str, c: int, r: int, k: int, face: str | None, src: str,
                   name: str | None = None) -> Placed | None:
        pw, ph = self._plan_size(item, k)
        if not self._suitable(item, c, r, pw, ph):
            return None
        p = self._new_placed(item, c, r, k, name, src, face)
        self.items.append(p)
        self._occupy(p)
        return p

    def _pick_variant(self, item: str, h: int) -> tuple[int, str | None]:
        d = self.cat.items[item]
        if d.layout == "rotate":
            faces = [f for f, k in FACINGS.items() if k < max(d.count, 1)] or ["west"]
            face = faces[h % len(faces)]
            return FACINGS[face], face
        if d.layout == "connect":
            return 0, None
        return h % max(d.count, 1), None

    def scatter(self, shape, items: dict[str, float], density: float, *, min_gap: int = 1,
                seed: str, clump: float = 0.0) -> list[Placed]:
        """Sprinkle items over a shape: each tile draws once (per-tile hash) against `density`.

        `clump` (0..1) modulates the density by smooth noise (about 8 tiles across), so woods
        get thickets and clearings instead of an even sprinkle; the mean density is kept."""
        src = _src()
        items = {k: v for k, v in items.items() if self._known_item(k, src)}
        if not items:
            return []
        ws = self._world(shape)
        c0, r0, c1, r1 = ws.bounds()
        m = ws.mask(c0, r0, c1 - c0 + 1, r1 - r0 + 1)
        cc, rr = rng.grid_coords(c0, r0, c1 - c0 + 1, r1 - r0 + 1)
        seedv = rng.hash64(self.region, seed)
        u = rng.hash01(cc, rr, seedv)
        if clump > 0:
            n = rng.fbm(cc, rr, 9.0, seedv ^ 0x77, octaves=3)
            mod = np.clip(1 + clump * (n - 0.5) * 5.0, 0, None)
            u = u / np.maximum(mod, 1e-6)
        pick = rng.hash01(cc, rr, seedv ^ 0x5151)
        var = rng.hash_grid(cc, rr, seedv ^ 0xA5A5)
        hits = np.argwhere(m & (u < density))
        total = sum(items.values())
        names = list(items)
        cum = np.cumsum([items[n] / total for n in names])
        out = []
        for j, i in hits:
            c, r = int(cc[j, i]), int(rr[j, i])
            item = names[min(int(np.searchsorted(cum, pick[j, i], side="right")), len(names) - 1)]
            if min_gap > 1 and self._near_occupied(c, r, min_gap - 1):
                continue
            k, face = self._pick_variant(item, int(var[j, i] % np.uint64(1 << 30)))
            p = self._try_place(item, c, r, k, face, src)
            if p:
                out.append(p)
        return out

    def _known_item(self, item: str, src: str) -> bool:
        if item in self.cat.retired:
            self._err("V1", f"{item!r} is a retired stand-in; use {self.cat.retired[item]}", src)
            return False
        if item in self.cat.items:
            return True
        self._err("V1", f"unknown item {item!r}", src)
        return False

    def _near_occupied(self, c: int, r: int, d: int) -> bool:
        j0, i0 = r - self.origin[1], c - self.origin[0]
        sub = self.OCC[max(j0 - d, 0):j0 + d + 1, max(i0 - d, 0):i0 + d + 1]
        return bool((sub >= 0).any())

    def row(self, line, item: str, every: int, *, face: str = "west",
            offset: int = 0) -> list[Placed]:
        src = _src()
        if not self._known_item(item, src):
            return []
        ln = self._world(line)
        path = ln.path() if isinstance(ln, Line) else ln.tiles()
        k = self._rot(item, face, 0)
        out = []
        for idx in range(offset, len(path), max(every, 1)):
            c, r = path[idx]
            p = self._try_place(item, c, r, k, face, src)
            if p:
                out.append(p)
        return out

    def wall(self, line, kit: str, *, tower: str | None = None, every: int = 8,
             gates: list[tuple[int, int, str]] = ()) -> list[Placed]:
        """A wall of a connect-layout kit along a line; towers every `every` tiles; gates at the
        given local tiles (the gate item is turned to face across the wall)."""
        src = _src()
        ln = self._world(line)
        path = ln.path() if isinstance(ln, Line) else ln.tiles()
        gate_at = {(c + self.origin[0], r + self.origin[1]): g for c, r, g in gates}
        out = []
        for idx, (c, r) in enumerate(path):
            p = None
            if (c, r) in gate_at:
                prev = path[idx - 1] if idx > 0 else path[min(idx + 1, len(path) - 1)]
                along_ns = prev[0] == c
                item = gate_at[(c, r)]
                if not self._known_item(item, src):
                    continue
                face = "west" if along_ns else "north"
                p = self._try_place(item, c, r, self._rot(item, face, 0), face, src)
                if p is None:
                    self._err("V2", f"gate {item} cannot stand on the wall here", src, at=(c, r))
            elif tower and idx % every == 0:
                if self._known_item(tower, src):
                    p = self._try_place(tower, c, r, self._rot(tower, "west", 0), "west", src)
            else:
                if self._known_item(kit, src):
                    p = self._try_place(kit, c, r, 0, None, src)
            if p:
                out.append(p)
        return out

    # -- ways and water -----------------------------------------------------------------------

    def street(self, points: list[tuple[int, int]], *, width: int, paving: str | None,
               kerb: str | None = None, kind: str = "street", portal: str | None = None) -> Street:
        """A way: paints `paving` and makes graph edges. `paving=None` keeps the ground as it is
        (a way over a bridge's deck or a landmark's floor, whose water or paving stays)."""
        src = _src()
        wpts = [(c + self.origin[0], r + self.origin[1]) for c, r in points]
        line = Line(wpts, width)
        w, h = self.size
        m = line.mask(self.origin[0], self.origin[1], w, h)
        if kerb:
            grown = Line(wpts, width + 2).mask(self.origin[0], self.origin[1], w, h) & ~m
            self.T[grown & ~self.STREET] = self._terrain_index(kerb, src)
        if paving is not None:
            self.T[m] = self._terrain_index(paving, src)
        self.STREET |= m
        s = Street(wpts, width, paving, kind, portal, src)
        self.streets.append(s)
        return s

    def stair(self, item: str, *, rect, face: str, name: str | None = None) -> Placed | None:
        """A stair or ramp: its foot is on the `face` side, its head on the opposite side."""
        p = self.place(item, rect=rect, face=face, name=name)
        if p is None:
            return None
        dc, dr = PLAN_STEP[face]
        mid_c = p.c + (p.pw - 1) // 2
        mid_r = p.r + (p.ph - 1) // 2
        if dc:
            foot = (p.c - 1, mid_r) if dc < 0 else (p.c + p.pw, mid_r)
            head = (p.c + p.pw, mid_r) if dc < 0 else (p.c - 1, mid_r)
            span = [(foot[0], rr) for rr in range(p.r, p.r + p.ph)], \
                [(head[0], rr) for rr in range(p.r, p.r + p.ph)]
        else:
            foot = (mid_c, p.r - 1) if dr < 0 else (mid_c, p.r + p.ph)
            head = (mid_c, p.r + p.ph) if dr < 0 else (mid_c, p.r - 1)
            span = [(cc, foot[1]) for cc in range(p.c, p.c + p.pw)], \
                [(cc, head[1]) for cc in range(p.c, p.c + p.pw)]
        foot, head = self._landing(foot, span[0]), self._landing(head, span[1])
        p.slots.setdefault("foot", [(foot[0], foot[1], None)])
        p.slots.setdefault("head", [(head[0], head[1], None)])
        self.stair_edges.append((p, foot, head))
        return p

    def _landing(self, tile, edge) -> tuple[int, int]:
        """Where a stair ends inside a landmark (a portico, a platform), the landing is the
        landmark's walk tile along the stair's end nearest its middle."""
        loc = self._local(*tile)
        if loc is None or self.OCC[loc] < 0:
            return tile
        walk = self.walk_tiles(self.items[self.OCC[loc]])
        if not walk or tile in walk:
            return tile
        on_edge = [t for t in edge if t in walk]
        if not on_edge:
            return tile
        return min(on_edge, key=lambda t: (abs(t[0] - tile[0]) + abs(t[1] - tile[1]), t))

    def river(self, points: list[tuple[int, int]], *, width: int, terrain: str = "world.river",
              banks: dict[str, float] | None = None, seed: str = "") -> None:
        """Paint a river; flow (aux) follows the points from source to mouth."""
        src = _src()
        self._watercourse(points, width, terrain, src)
        if banks:
            wpts = [(c + self.origin[0], r + self.origin[1]) for c, r in points]
            w, h = self.size
            water = Line(wpts, width).mask(self.origin[0], self.origin[1], w, h)
            band = Line(wpts, width + 2).mask(self.origin[0], self.origin[1], w, h) & ~water
            js, is_ = np.nonzero(band)
            seedv = rng.hash64(self.region, "banks", seed)
            for item, density in banks.items():
                if not self._known_item(item, src):
                    continue
                cc = is_ + self.origin[0]
                rr = js + self.origin[1]
                u = rng.hash01(cc, rr, seedv ^ rng.hash64(item))
                for c, r in zip(cc[u < density].tolist(), rr[u < density].tolist()):
                    k, face = self._pick_variant(item, (c * 7 + r * 13) & 0xFFFF)
                    self._try_place(item, c, r, k, face, src)

    def channel(self, points: list[tuple[int, int]], *, terrain: str, width: int = 1) -> None:
        self._watercourse(points, width, terrain, _src())

    def _watercourse(self, points, width, terrain, src) -> None:
        wpts = [(c + self.origin[0], r + self.origin[1]) for c, r in points]
        w, h = self.size
        m = Line(wpts, width).mask(self.origin[0], self.origin[1], w, h)
        self.T[m] = self._terrain_index(terrain, src)
        # Flow per tile: direction of the nearest segment.
        js, is_ = np.nonzero(m)
        if js.size == 0:
            return
        cx = is_ + self.origin[0] + 0.5
        cy = js + self.origin[1] + 0.5
        best = np.full(js.size, np.inf)
        flow = np.zeros(js.size, dtype=np.int8)
        for (ac, ar), (bc, br) in zip(wpts, wpts[1:]):
            dx, dy = bc - ac, br - ar
            ll = max(dx * dx + dy * dy, 1)
            t = np.clip(((cx - ac - 0.5) * dx + (cy - ar - 0.5) * dy) / ll, 0, 1)
            d2 = (cx - (ac + 0.5 + t * dx)) ** 2 + (cy - (ar + 0.5 + t * dy)) ** 2
            better = d2 < best
            best[better] = d2[better]
            flow[better] = _grid_dir_of(dx, dy)
        self.AUX[js, is_] = flow

    def lane(self, lane_id: str, points: list[tuple[int, int]], *, kind: str,
             ports: dict[str, int]) -> None:
        wpts = [(c + self.origin[0], r + self.origin[1]) for c, r in points]
        self.lanes.append(LaneSpec(lane_id, kind, wpts, dict(ports), _src()))

    # -- graph names --------------------------------------------------------------------------

    def node(self, node_id: str, at: tuple[int, int], *, kind: str = "dest") -> None:
        self.nodes[node_id] = ((at[0] + self.origin[0], at[1] + self.origin[1]), kind, _src())

    def edge(self, a: str, b: str, *, kind: str = "road",
             via: list[tuple[int, int]] = ()) -> None:
        """An explicit edge between two named nodes, for ways over ground this layer does not
        paint (the home region the engine writes, a transparent seam)."""
        self.edges.append((a, b, kind, [(c + self.origin[0], r + self.origin[1]) for c, r in via],
                           _src()))

    def link(self, placed: Placed | None, slot: str, node_id: str) -> None:
        if placed is not None:
            self.links.append((placed, slot, node_id, _src()))

    # -- checks and previews ------------------------------------------------------------------

    def expect(self, landmark: str, *, rect, level: int | None = None) -> None:
        self.expects.append(Expect(landmark, self._world(rect), level, _src()))

    def moved(self, landmark: str, *, rect, why: str) -> None:
        """Declare that a landmark stands off its city-file rect on purpose (V4 then reports the
        move as a warning with the reason, instead of an error)."""
        self.moves[landmark] = (self._world(rect), why, _src())

    def view(self, name: str, rect) -> None:
        self.views[name] = self._world(rect)

    def sightline(self, name: str, shape) -> None:
        """Mark a monumental approach (V15): nothing of the connective world's rustic kit and no
        placeholder may stand in it, only the region's own set and the home set."""
        self.sightlines[name] = self._mask(shape)

    # -- district filler and fields -----------------------------------------------------------

    def houses(self, shape, kit: dict[str, float], *, front: list[Street], gap: float = 0.1,
               seed: str) -> list[Placed]:
        """Fill a district with kit houses.

        Walks the frontage of the given streets in order, both sides, and stands houses with their
        front (door) to the street, keeping about `gap` of the frontage free as alleys. Then it
        fills the block interior with the smaller pieces, each facing a free tile that is still
        reachable from a street, and finally removes any house whose door became unreachable.
        """
        src = _src()
        kit = {k: v for k, v in kit.items() if self._known_item(k, src)}
        if not kit:
            return []
        region_m = self._mask(shape)
        st_m = np.zeros_like(self.STREET)
        w, h = self.size
        for s in front:
            st_m |= Line(s.points, s.width).mask(self.origin[0], self.origin[1], w, h)
        st = rng.stream(self.region, "houses", seed)
        order = sorted(kit, key=lambda k: -kit[k])
        placed: list[Placed] = []
        doors: set[tuple[int, int]] = set()

        def inside(c, r):
            loc = self._local(c, r)
            return loc is not None and region_m[loc] and not st_m[loc]

        def fits(p: Placed) -> bool:
            if not all(inside(c, r) for c, r in p.tiles()):
                return False
            if any((c, r) in doors for c, r in p.tiles()):
                return False
            if not self._suitable(p.id, p.c, p.r, p.pw, p.ph):
                return False
            return p.door is not None and self._local(*p.door) is not None

        # Frontage, in walking order along each street: the first tile off the paving.
        frontage: list[tuple[int, int, str]] = []
        seen = set()
        for s in front:
            for (c, r) in s.path():
                for face, (dc, dr) in PLAN_STEP.items():
                    # A house on side (dc, dr) of the street faces back toward it.
                    for dist in range(1, s.width + 2):
                        cc, rr = c + dc * dist, r + dr * dist
                        loc = self._local(cc, rr)
                        if loc is None or not st_m[loc]:
                            break
                    else:
                        continue
                    if inside(cc, rr) and (cc, rr) not in seen:
                        seen.add((cc, rr))
                        back = {"west": "east", "east": "west", "north": "south", "south": "north"}
                        frontage.append((cc, rr, back[face]))

        for (c, r, face) in frontage:
            if self.OCC[self._local(c, r)] >= 0 or (c, r) in doors:
                continue
            if st.chance(gap):
                # An alley: keep this tile and two behind it free for the block interior.
                dc, dr = PLAN_STEP[face]
                for d in range(3):
                    loc = self._local(c - dc * d, r - dr * d)
                    if loc is not None and region_m[loc]:
                        self.RESERVED[loc] = True
                continue
            first = st.weighted(kit)
            for item in [first] + [k for k in order if k != first]:
                p = self._house_at(item, c, r, face, src)
                if p is not None and fits(p):
                    self._commit(p)
                    placed.append(p)
                    doors.add(p.door)
                    break

        # Interior: smaller pieces facing reachable free tiles.
        small = sorted(kit, key=lambda k: self._area(k))[:max(1, (len(kit) + 1) // 2)]
        js, is_ = np.nonzero(region_m & ~st_m)
        cand = sorted(zip((is_ + self.origin[0]).tolist(), (js + self.origin[1]).tolist()),
                      key=lambda t: rng.hash64(self.region, seed, t[0], t[1]))
        reach = self._reachable(region_m, st_m)
        for (c, r) in cand:
            if self.OCC[self._local(c, r)] >= 0 or st.chance(gap):
                continue
            for item in small:
                done = False
                for face in ("west", "north", "east", "south"):
                    p = self._house_at(item, c, r, face, src, anchor_front=False)
                    if p is None or not fits(p) or p.door not in reach:
                        continue
                    self._commit(p)
                    placed.append(p)
                    doors.add(p.door)
                    reach = self._reachable(region_m, st_m)
                    done = True
                    break
                if done:
                    break

        # Drop houses whose doors are cut off, until stable.
        while True:
            reach = self._reachable(region_m, st_m)
            lost = [p for p in placed if not p.removed and p.door not in reach]
            if not lost:
                break
            for p in lost:
                self._remove(p)
                doors.discard(p.door)
        self.RESERVED[region_m] = False
        return [p for p in placed if not p.removed]

    def _area(self, item: str) -> int:
        fx, fy = self.cat.items[item].footprint
        return fx * fy

    def _house_at(self, item: str, c: int, r: int, face: str, src: str,
                  anchor_front: bool = True) -> Placed | None:
        """A candidate house with its front edge on tile (c, r), facing `face`."""
        d = self.cat.items[item]
        k = self._rot(item, face, 0) if d.layout == "rotate" else 0
        pw, ph = self._plan_size(item, k)
        dc, dr = PLAN_STEP[face]
        # Front row/column contains (c, r); the body extends away from the street.
        if dc < 0:
            c0, r0 = c, r - (ph - 1) // 2
        elif dc > 0:
            c0, r0 = c - pw + 1, r - (ph - 1) // 2
        elif dr < 0:
            c0, r0 = c - (pw - 1) // 2, r
        else:
            c0, r0 = c - (pw - 1) // 2, r - ph + 1
        return self._new_placed(item, c0, r0, k, None, src, face if d.layout == "rotate" else None)

    def _commit(self, p: Placed) -> None:
        p.index = len(self.items)
        self.items.append(p)
        self._occupy(p)

    def _reachable(self, region_m: np.ndarray, st_m: np.ndarray) -> set[tuple[int, int]]:
        """Free walkable tiles of the block reachable from its streets (4-steps, same level)."""
        h, w = region_m.shape
        free = (region_m | st_m) & (self.OCC < 0) & (self.T >= 0) & ~self.IMP
        water = np.zeros_like(free)
        for t, name in enumerate(self.terrains):
            if self.cat.is_water(name):
                water |= self.T == t
        free &= ~water | st_m
        seen = np.zeros_like(free)
        q = deque()
        for j, i in np.argwhere(st_m & free):
            seen[j, i] = True
            q.append((j, i))
        while q:
            j, i = q.popleft()
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = j + dj, i + di
                if 0 <= a < h and 0 <= b < w and free[a, b] and not seen[a, b] \
                        and self.LV[a, b] == self.LV[j, i]:
                    seen[a, b] = True
                    q.append((a, b))
        js, is_ = np.nonzero(seen)
        return set(zip((is_ + self.origin[0]).tolist(), (js + self.origin[1]).tolist()))

    def fields(self, shape, crop: str, *, plot: tuple[int, int] = (4, 3), path: str | None = None,
               seed: str) -> None:
        """Divide a shape into plots of about `plot` (w, h) tiles, with 1-tile paths between them
        when `path` is given. Plot sizes wobble by a tile and about one plot in five lies fallow,
        so fields read as worked land, not a grid. `crop` is a terrain, or an item planted in rows.
        """
        src = _src()
        is_terrain = crop in self.cat.terrain
        if not is_terrain and not self._known_item(crop, src):
            return
        ws = self._world(shape)
        c0, r0, c1, r1 = ws.bounds()
        m = ws.mask(c0, r0, c1 - c0 + 1, r1 - r0 + 1)
        seedv = rng.hash64(self.region, "fields", seed)
        st = rng.Stream(seedv)
        gap = 1 if path else 0
        cols = []
        c = c0
        while c <= c1:
            wdt = max(2, plot[0] + st.randint(-1, 1))
            cols.append((c, min(c + wdt - 1, c1)))
            c += wdt + gap
        rows = []
        r = r0
        while r <= r1:
            hgt = max(2, plot[1] + st.randint(-1, 1))
            rows.append((r, min(r + hgt - 1, r1)))
            r += hgt + gap
        pidx = self._terrain_index(path, src) if path else None
        cidx = self._terrain_index(crop, src) if is_terrain else None
        k_item = 0
        for (pr0, pr1) in rows:
            for (pc0, pc1) in cols:
                fallow = rng.hash64(seedv, pc0, pr0) % 5 == 0
                for rr in range(pr0, pr1 + 1):
                    for cc in range(pc0, pc1 + 1):
                        if not m[rr - r0, cc - c0]:
                            continue
                        loc = self._local(cc, rr)
                        if loc is None or self.T[loc] < 0 or self.OCC[loc] >= 0 or self.STREET[loc]:
                            continue
                        if self.cat.is_water(self.terrains[self.T[loc]]):
                            continue
                        if fallow:
                            continue
                        if is_terrain:
                            self.T[loc] = cidx
                        elif (rr - pr0) % 2 == 0:
                            k, face = self._pick_variant(crop, k_item)
                            k_item += 1
                            self._try_place(crop, cc, rr, k, face, src)
        if pidx is not None:
            for (pr0, pr1) in rows:
                self._paint_if(m, c0, r0, Rect(c0, pr1 + 1, c1, pr1 + 1), pidx)
            for (pc0, pc1) in cols:
                self._paint_if(m, c0, r0, Rect(pc1 + 1, r0, pc1 + 1, r1), pidx)

    def _paint_if(self, m, mc0, mr0, rect: Rect, idx: int) -> None:
        for rr in range(rect.r0, rect.r1 + 1):
            for cc in range(rect.c0, rect.c1 + 1):
                if not (0 <= rr - mr0 < m.shape[0] and 0 <= cc - mc0 < m.shape[1]):
                    continue
                if not m[rr - mr0, cc - mc0]:
                    continue
                loc = self._local(cc, rr)
                if loc is None or self.T[loc] < 0 or self.OCC[loc] >= 0 or self.STREET[loc]:
                    continue
                if self.cat.is_water(self.terrains[self.T[loc]]):
                    continue
                self.T[loc] = idx
