"""Previews of real places from the composed world with the land art as the engine draws it
(src/worldview/renderer.cpp `drawTile`): faces stacked one level at a time under the +x and +y
edges, the rim band (`/top`) replacing the uppermost level after the ground, the sea's foot on
the lowest level of a cliff in water, base then overlay then foam. Sprites come from the
committed pages unless a generator function supplies them (`sprites`), so new art is seen in
place before any set is rebuilt. Read-only on the world: it imports tools/worldgen.

    tools/artgen/.venv/bin/python tools/artgen/landpreview.py corner_river --season autumn
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/worldgen"))

from worldgen.build import Builder  # noqa: E402
from worldgen.compose import NONE16, live_items  # noqa: E402
from worldgen.coords import COLS, ROWS, to_grid  # noqa: E402
from worldgen.preview import IsoRenderer, tile_hash  # noqa: E402

sys.path.insert(0, str(ROOT / "tools/artgen"))
import slopes  # noqa: E402
from pack import Sprite  # noqa: E402

# Places worth looking at, plan rects (c0, r0, c1, r1).
PLACES = {
    "anatolia_river": (1029, 264, 1053, 288),   # earth banks and a river falling three levels
    "anatolia_gorge": (1075, 108, 1095, 128),   # rock steps on a river
    "corner_coast": (10, 34, 34, 56),           # the corner's river reaching the sea cliff
    "latium_falls": (363, 203, 383, 223),
    "greece_steps": (875, 198, 897, 218),
    "acropolis_west": (616, 296, 656, 320),     # the Acropolis rock's west end
    "acropolis_south": (660, 308, 698, 334),
    "parsa_terrace": (1180, 336, 1228, 386),    # the terrace's foot and its stairs
    "capitol": (152, 60, 192, 98),              # the Capitol's tufa cliff
    "persian_gates": (1106, 324, 1133, 351),    # the pass through the Zagros
    "taurus": (936, 246, 966, 274),             # mountain slopes
    "apennines": (296, 96, 324, 124),           # a hillside valley
}


def as_pil(sp):
    """A pack.Sprite (or an (image, ox, oy) triple) as (PIL RGBA, ox, oy)."""
    if sp is None or isinstance(sp, tuple):
        return sp
    return Image.fromarray(sp.rgba, "RGBA"), sp.ox, sp.oy


class LandRenderer(IsoRenderer):
    """IsoRenderer with the engine's face rules, seasons and an override for sprite keys."""

    def __init__(self, world, cat, atlas, root, sprites=None, season=None, slope=None):
        super().__init__(world, cat, atlas, root)
        self.sprites = sprites
        self.season = season
        self.slope = slope        # a Slopes, or None for today's stacked faces
        self._got: dict = {}
        self._slopes: dict = {}

    def sprite(self, key):
        if key not in self._got:
            sp = self.sprites(key) if self.sprites else None
            if sp is None and self.season:
                sp = self.atlas.get(f"{key}@{self.season}")
            self._got[key] = as_pil(sp) if sp is not None else self.atlas.get(key)
        return self._got[key]

    def count_interior(self, tid):
        n = 1
        while self.sprite(f"terrain/{tid}/m15/v{n}/f0") is not None:
            n += 1
        return n

    def count(self, prefix):
        n = 0
        while self.sprite(f"{prefix}/v{n}") is not None:
            n += 1
        return n

    def _ops(self, rect, xmin, ymin):
        # Items on slope tiles stand at the surface's height at the tile's centre: the parent
        # asks for each item's shadow first, in this same order, which steps the queue on.
        self._lift = []
        self._cur = -1
        if self.slope:
            c0, r0, c1, r1 = rect
            for _idx, it in live_items(self.w):
                if it.c + it.pw - 1 < c0 or it.c > c1 or it.r + it.ph - 1 < r0 or it.r > r1:
                    continue
                shape = self.slope.shape(it.c + it.pw - 1, it.r) if (it.pw, it.ph) == (1, 1) else None
                self._lift.append(0 if shape is None else
                                  int(round(-float(slopes.height(shape, 8, 8)) * self.lp)))
        return super()._ops(rect, xmin, ymin)

    def item_sprite(self, item_id, k, mask, layer="base"):
        if layer == "shadow":
            self._cur += 1
        sp = super().item_sprite(item_id, k, mask, layer)
        lift = self._lift[self._cur] if self.slope and 0 <= self._cur < len(self._lift) else 0
        return sp if sp is None or not lift else (sp[0], sp[1], sp[2] - lift)

    def terrain_sprites(self, tid, tx, ty, mask, depth):
        out = []
        t = self.cat.terrain.get(tid)
        base = self.cat.drawn_base(tid)
        tb = self.cat.terrain.get(base)
        n = tb.variants if tb else 1
        s = self.sprite(f"terrain/{base}/v{tile_hash(tx, ty, 1) % max(n, 1)}")
        if s is not None:
            out.append(s)
        if t is not None and not t.base:
            o = None
            if mask == 15:          # the interior's looks, picked as the engine does
                n = self.count_interior(tid)
                pick = tile_hash(tx, ty, 1) % n if n > 1 else 0
                o = self.sprite(f"terrain/{tid}/m15/v{pick}/f0") if pick else None
            o = o or self.sprite(f"terrain/{tid}/m{mask}/f0")
            if o is not None:
                out.append(o)
        return out or super().terrain_sprites(tid, tx, ty, mask, depth)

    def fall_ends(self, c, r, side, lv) -> int:
        """Which ends of a fall's edge the falling water goes on past (the contract's `e` bits):
        the tile beyond each end along the edge is water at this level and falls the same way."""
        w = self.w
        # (beyond the s = 0 end, beyond the far end, the step across the edge) in plan offsets
        steps = {"se": ((-1, 0), (1, 0), (0, 1)), "sw": ((0, 1), (0, -1), (-1, 0))}[side]
        out = 0
        for bit, (dc, dr) in zip((1, 2), steps[:2]):
            nc, nr = c + dc, r + dr
            if not (0 <= nc < COLS and 0 <= nr < ROWS) or w.T[nr, nc] == NONE16:
                continue
            if not self.cat.is_water(w.terrains[w.T[nr, nc]]) or (int(w.L[nr, nc]) & 15) != lv:
                continue
            fc, fr = nc + steps[2][0], nr + steps[2][1]
            if 0 <= fc < COLS and 0 <= fr < ROWS and w.T[fr, fc] != NONE16 and (int(w.L[fr, fc]) & 15) < lv:
                out |= bit
        return out

    def _tile_ops(self, c, r, t, lvl, screen):
        w = self.w
        tid = w.terrains[t]
        tx, ty = to_grid(c, r)
        lv = lvl(c, r)
        x, y = screen(c, r, lv)
        aux = (int(w.L[r, c]) >> 4) & 3
        water = self.cat.is_water(tid)
        faces = self.cat.faces(tid)
        mat = None if water else (faces[aux] if aux < len(faces) else None)
        corner = self.slope.corners(c, r) if self.slope else None   # heights N, E, S, W
        ops, tops = [], []
        # (side, neighbour, this tile's corners on the edge as (s = 0 end, s = W end), the
        # neighbour's corners on it in the same order)
        edges = (("se", (c, r + 1), (2, 1), (3, 0)), ("sw", (c - 1, r), (2, 3), (1, 0)))
        for side, (nc, nr), mine, theirs in edges:
            ln = lvl(nc, nr)
            if corner is None:
                hi = lo = lv
                bottom = ln
            else:
                a0, a1 = corner[mine[0]], corner[mine[1]]
                inb = 0 <= nc < COLS and 0 <= nr < ROWS and w.T[nr, nc] != NONE16
                nb = self.slope.corners(nc, nr) if inb else (0, 0, 0, 0)
                hi, lo = max(a0, a1), min(a0, a1)
                b0, b1 = nb[theirs[0]], nb[theirs[1]]
                bottom = min(b0, b1)
                if a0 <= b0 and a1 <= b1:     # the edges meet: no face between them
                    continue
            if hi <= bottom:
                continue
            nt = w.T[nr, nc] if 0 <= nc < COLS and 0 <= nr < ROWS else NONE16
            wet = nt != NONE16 and self.cat.is_water(w.terrains[nt])
            if water and self.sprite(f"edge/world.fall_{side}/mid/e3/f0") is not None:
                # Water over a drop: the falls' lip, sheet and foot, or a one-level cascade.
                drop = lv - bottom
                parts = ["rapid"] if drop == 1 else ["top"] + ["mid"] * (drop - 2) + ["foot"]
                ends = self.fall_ends(c, r, side, lv)
                for b, part in enumerate(parts):
                    sp = self.sprite(f"edge/world.fall_{side}/{part}/e{ends}/f0")
                    op = ("g", x - sp[1], y + b * self.lp - sp[2], sp[0])
                    (tops if part in ("top", "rapid") else ops).append(op)
                rap = self.sprite("terrain/world.river/rapids_e/f0")
                if rap is not None:
                    im = rap[0] if side == "se" else rap[0].transpose(Image.FLIP_LEFT_RIGHT)
                    ox_ = rap[1] if side == "se" else im.width - rap[1]
                    tops.insert(0, ("g", x - ox_, y - rap[2], im))
                continue
            prefix = f"edge/{mat}_{side}" if mat else None
            nv = self.count(prefix) if prefix else 0
            wedge = None if hi == lo else (0 if a0 > a1 else 1)
            top = None
            if nv:
                top = self.sprite(f"{prefix}/top") if wedge is None else None
            first = lv - hi                     # bands start at the tile's own level
            for b in range(first, lv - bottom):
                at = (x, y + b * self.lp)
                if nv:
                    if b == first and top is not None:
                        continue
                    k = tile_hash(tx, ty, 3 + b) % nv
                    if b == first and wedge is not None:
                        nw = self.count(f"{prefix}/w{wedge}") or 1
                        sp = self.sprite(f"{prefix}/w{wedge}/v{tile_hash(tx, ty, 3 + b) % nw}")
                    else:
                        sp = self.sprite(f"{prefix}/v{k}/f0") if b == lv - bottom - 1 and wet else None
                        sp = sp or self.sprite(f"{prefix}/v{k}")
                    ops.append(("g", at[0] - sp[1], at[1] - sp[2], sp[0]))
                else:
                    ops.append(("g", *self._face(side, "water" if water else mat, at[0], at[1], tx, ty, b)))
            if top is not None:
                tops.append(("g", x - top[1], y + first * self.lp - top[2], top[0]))
        mask = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nc, nr = COLS - 1 - (ty + dy), tx + dx
            if 0 <= nc < COLS and 0 <= nr < ROWS and w.T[nr, nc] == t:
                mask |= bit
        ground = self.terrain_sprites(tid, tx, ty, mask, aux)
        shape = self.slope.shape(c, r) if self.slope else None
        if shape:
            base = self.cat.terrain.get(tid)
            interior = base is not None and (base.base or mask == 15)
            look = tile_hash(tx, ty, 1) % 2
            key = (tuple(id(g[0]) for g in ground), shape, look if self.slope.live else 0)
            if key not in self._slopes:
                self._slopes[key] = as_pil(self.slope.lay(ground, shape, tid, look, interior))
            im, ox, oy = self._slopes[key]
            ops.append(("g", x - ox, y + self.lp - oy, im))
        else:
            for im, ox, oy in ground:
                ops.append(("g", x - ox, y - oy, im))
        if water:
            fall_in = 0
            for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
                nc, nr = COLS - 1 - (ty + dy), tx + dx
                if 0 <= nc < COLS and 0 <= nr < ROWS and w.T[nr, nc] != NONE16 and \
                        self.cat.is_water(w.terrains[w.T[nr, nc]]) and lvl(nc, nr) > lv:
                    fall_in |= bit
            pl = self.sprite(f"terrain/world.river/plunge/m{fall_in}/f0") if fall_in else None
            if pl is not None:
                ops.append(("g", x - pl[1], y - pl[2], pl[0]))
        return ops + tops

MASONRY = ("basalt", "ashlar", "brick", "travertine")


class Slopes:
    """Which tiles of the world become slopes, by the contract's rule (art-smooth-land.md §3): a
    corner of a tile that may slope is low when a tile touching it stands exactly one level
    lower; a tile with items, or of a terrain that keeps its edges (paving, fields, salt), stays
    flat. Corner heights are absolute levels in the order N, E, S, W."""

    def __init__(self, w, cat, flat_ok, k, lvl, pal):
        self.w, self.cat, self.k, self.lvl, self.pal = w, cat, k, lvl, pal
        self.live = False
        ids = np.array([flat_ok(t) for t in w.terrains] + [False])
        T = np.where(w.T == NONE16, len(w.terrains), w.T)
        # A tile whose face is masonry is a built edge and stays flat (world-qa6.md §3).
        built = np.zeros((len(w.terrains) + 1, 4), bool)
        for i, tid in enumerate(w.terrains):
            for a, f in enumerate(cat.faces(tid)[:4]):
                built[i, a] = f.split(".")[-1] in MASONRY
        aux = ((w.L >> 4) & 3).astype(np.int64)
        self.ok = ids[T] & ~blocked(w, cat) & ~built[T, aux]
        self._c: dict = {}

    def level(self, c, r):
        if not (0 <= c < COLS and 0 <= r < ROWS) or self.w.T[r, c] == NONE16:
            return None
        return int(self.w.L[r, c]) & 15

    def corners(self, c, r):
        if (c, r) in self._c:
            return self._c[(c, r)]
        lv = self.level(c, r)
        if lv is None:
            return (0, 0, 0, 0)
        out = [lv] * 4
        if self.ok[r, c]:
            tx, ty = to_grid(c, r)
            # corner N touches grid (tx-1, ty-1), (tx, ty-1), (tx-1, ty); E: x+1, y-1 ...
            for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
                for dx, dy in ((sx, 0), (0, sy), (sx, sy)):
                    nl = self.level(COLS - 1 - (ty + dy), tx + dx)
                    if nl == lv - 1:
                        out[i] = lv - 1
        self._c[(c, r)] = tuple(out)
        return self._c[(c, r)]

    def _low_lower(self, c, r):
        lv = self.level(c, r)
        cs = self.corners(c, r)
        low = sum(bit for bit, h in zip((1, 2, 4, 8), cs) if h < lv)
        tx, ty = to_grid(c, r)
        lower = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nl = self.level(COLS - 1 - (ty + dy), tx + dx)
            if nl is not None and nl < lv:
                lower |= bit
        return lv, low, lower

    def shape(self, c, r):
        if self.level(c, r) is None:
            return None
        lv, low, lower = self._low_lower(c, r)
        axis = slopes.ridge_axis(low, lower)
        on = (False, False)
        if axis:
            tx, ty = to_grid(c, r)
            steps = ((-1, 0), (1, 0)) if axis == "x" else ((0, -1), (0, 1))
            on = tuple(self._ridge(COLS - 1 - (ty + dy), tx + dx, axis, lv) for dx, dy in steps)
        return slopes.shape_of(low, lower, on)

    def _ridge(self, c, r, axis, lv):
        if self.level(c, r) != lv:
            return False
        _lv, low, lower = self._low_lower(c, r)
        return slopes.ridge_axis(low, lower) == axis

    def lay(self, ground, shape, tid=None, look=0, interior=False):
        """The slope look of a tile: with `live` and an interior tile (or a base), the set build's
        own sprite (setbuild.slope_set, as the engine draws it); otherwise one flat diamond from
        the tile's ground sprites laid on the shape (an overlay's edge over its base, which the
        engine warps)."""
        if self.live and tid and interior:
            return _live_slope(tid, look, shape)
        im = Image.new("RGBA", (32 * self.k, 16 * self.k), (0, 0, 0, 0))
        for g, ox, oy in ground:
            im.alpha_composite(g, (16 * self.k - ox, -oy))
        flat = Sprite(np.asarray(im).copy(), 16 * self.k, 0)
        if not self.live:
            return slopes.slope_sprite(flat, shape, self.k, self.lvl, self.pal)
        set_id = tid.split(".")[0]
        import setbuild
        return slopes.slope_sprite(flat, shape, self.k, self.lvl, self.pal, look, slopes.material_of(tid),
                                   setbuild.slope_rock(set_id, _set_cat(set_id), tid))


_CATS: dict = {}


def _set_cat(set_id):
    import json
    if set_id not in _CATS:
        _CATS[set_id] = json.loads((ROOT / f"assets/sets/{set_id}/catalog.json").read_text())
    return _CATS[set_id]


_LIVE: dict = {}
_FLAT: dict = {}


def _live_flat(key):
    """A set's ground sprite (`terrain/<set>.<id>/…`) from the generator as it is now, or None
    for every other key (those come from the committed pages)."""
    import re
    m = re.fullmatch(r"terrain/((world|parsa|athens|rome)\.\w+)/(v\d+|m\d+(/v\d+)?/f0)", key)
    if not m:
        return None
    if key not in _FLAT:
        import setbuild
        set_id = m[2]
        cat = _set_cat(set_id)
        t = next((x for x in cat["terrain"] if x["id"] == m[1]), None)
        mod = setbuild.load_set(set_id)
        n = getattr(mod.ground, "INTERIOR", {}).get(m[1], 1)
        ok = t is not None and ("fps" not in t) and not (m[4] and int(m[4][2:]) >= n)
        _FLAT[key] = mod.flat([key], cat, 2)[key] if ok else None
    return _FLAT[key]


def _live_slope(tid, look, shape):
    """The set build's slope sprite for (terrain, look, shape), all shapes made at once."""
    import setbuild
    if (tid, look) not in _LIVE:
        set_id = tid.split(".")[0]
        _LIVE[(tid, look)] = setbuild.slope_set(set_id, _set_cat(set_id), tid, look, tuple(slopes.SHAPES), 2)
    return _LIVE[(tid, look)][f"terrain/{tid}/slope/{shape}/v{look}"]


def rides(d) -> bool:
    """Whether an item may stand on a slope (the contract's rule): one tile, not walked on or
    over, no door, no stair: plants, rocks and small props, which stand at the centre's height."""
    return d is not None and tuple(d.footprint) == (1, 1) and not (d.landmark or d.walkable or d.rise
                                                                    or d.has_door or d.on == "water")


def blocked(w, cat) -> np.ndarray:
    """Tiles an item keeps flat."""
    keep = np.array([not rides(cat.items.get(it.id)) for it in w.items] + [False])
    return keep[np.where(w.occ < 0, len(w.items), w.occ)]


# Rock keeps its cliffs (art-smooth-land.md §3.6): it may slope where a step is one level, but
# the grading never raises it.
ROCK = {"world.rock", "world.scree", "world.snow", "athens.rock_limestone", "rome.tufa_rock", "parsa.rough_ground"}


def regrade(w, cat, eligible, rect, passes=8):
    """A copy of the world with the natural ground in `rect` graded to one level per neighbour
    (the world builder's pass, art-smooth-land.md §3.6): an eligible tile is raised to one below
    its highest eligible neighbour (eight around), water and every other tile staying as they are, so
    hillsides become runs of slopes and true cliffs remain where the terrain keeps its edges."""
    import copy
    out = copy.copy(w)
    out.L = w.L.copy()
    c0, r0, c1, r1 = rect
    T = w.T
    ok = np.zeros(T.shape, bool)
    ids = np.array([eligible(t) for t in w.terrains] + [False])
    sl = (slice(max(r0 - 2, 0), r1 + 3), slice(max(c0 - 2, 0), c1 + 3))
    ids = ids & np.array([t not in ROCK for t in w.terrains] + [False])
    ok[sl] = ids[np.where(T[sl] == NONE16, len(w.terrains), T[sl])]
    ok &= ~blocked(w, cat)
    wet = np.array([cat.is_water(t) for t in w.terrains] + [False])[np.where(T == NONE16, len(w.terrains), T)]
    lv0 = (w.L & 15).astype(np.int64)
    cap = np.full(T.shape, 99)        # a bank rises at most one level over the water beside it
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            cap = np.minimum(cap, np.where(np.roll(np.roll(wet, dr, 0), dc, 1),
                                           np.roll(np.roll(lv0, dr, 0), dc, 1) + 1, 99))
    cap = np.maximum(cap, lv0)
    for _ in range(passes):
        lv = (out.L & 15).astype(np.int64)
        mine = np.where(ok, lv, 0)
        hi = lv.copy()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                hi = np.maximum(hi, np.roll(np.roll(mine, dr, 0), dc, 1))
        want = np.where(ok, np.minimum(np.maximum(lv, hi - 1), cap), lv)
        if (want == lv).all():
            break
        out.L = ((out.L & 0xF0) | want.astype(np.uint8)).astype(w.L.dtype)
    return out


_WORLD = None


def world():
    """(world, catalog, atlas), composed once from the committed layers."""
    global _WORLD
    if _WORLD is None:
        b = Builder(ROOT, write=False)
        b.load_committed()
        _WORLD = (b.composed(), b.cat, b.atlas)
    return _WORLD


def render(rect, sprites=None, season=None, scale=1, slope=None) -> Image.Image:
    w, cat, atlas = world()
    im = LandRenderer(w, cat, atlas, ROOT, sprites, season, slope).render(rect, scale)
    return crop(im)


def crop(im: Image.Image, bg=(30, 34, 46)) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(int)
    ys, xs = np.nonzero(np.abs(a - bg).sum(2) > 6)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)) if len(xs) else im


def side_by_side(a: Image.Image, b: Image.Image, gap=12, bg=(30, 34, 46)) -> Image.Image:
    out = Image.new("RGB", (a.width + b.width + gap, max(a.height, b.height)), bg)
    out.paste(a, (0, 0))
    out.paste(b, (a.width + gap, 0))
    return out


def slope_ok(cat, w):
    """Slope eligibility of each terrain id (the catalogs' `art.slopes`) and, per tile, whether its
    face is masonry (a built edge stays flat: world-qa6.md §3)."""
    import json
    ids = set()
    for p in sorted((ROOT / "assets/sets").glob("*/catalog.json")):
        ids |= set(json.loads(p.read_text()).get("art", {}).get("slopes", ()))
    return lambda t: t in ids



def _old_slopes(rev: str):
    """slopes.py as it was at git revision `rev`, as a module (for before/after previews)."""
    import importlib.util
    import shutil
    import subprocess
    import tempfile
    src = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:tools/artgen/slopes.py"], check=True,
                         capture_output=True, text=True).stdout
    d = Path(tempfile.mkdtemp(prefix="lc-slopes-"))
    f = d / f"slopes_{rev.replace('/', '_')}.py"
    f.write_text(src)
    spec_ = importlib.util.spec_from_file_location(f.stem, f)
    mod = importlib.util.module_from_spec(spec_)
    try:
        spec_.loader.exec_module(mod)
    finally:
        shutil.rmtree(d)
    return mod


def render_slopes(rect, module=slopes, season=None) -> Image.Image:
    """`rect` with every eligible one-level step drawn as a slope by `module`'s art."""
    global slopes
    w, cat, atlas = world()
    from palette import REGION_COLOURS, palette_for
    pal = slopes.palette_codes(sorted(set(palette_for(None)).union(*REGION_COLOURS.values())))
    keep = slopes
    slopes = module
    try:
        sl = Slopes(w, cat, slope_ok(cat, w), 2, cat.level_px, pal)
        sl.live = module is keep
        im = LandRenderer(w, cat, atlas, ROOT, _live_flat if sl.live else None, None, sl).render(rect, 1)
    finally:
        slopes = keep
    im = crop(im)
    return season_look(im, season) if season else im


_SEASON = {}


def season_look(im: Image.Image, season: str) -> Image.Image:
    """The shader path's season by ramp states, by colour (autumn: leaves turn, grass dries;
    winter: dormant): each pixel's palette-group ramp and step swapped for its state's."""
    import json
    if not _SEASON:
        doc = json.loads((ROOT / "assets/atlas/ramps.json").read_text())
        byid = {e["id"]: e for e in doc["ramps"]}
        for st in ("dry", "turn", "dormant"):
            m = {}
            for e in doc["ramps"]:
                if not e["name"].startswith("pal.") or st not in e.get("states", {}):
                    continue
                to = byid[e["states"][st]]["colours"]
                for i, c in enumerate(e["colours"]):
                    m[int(c[1:], 16)] = int(to[min(i, len(to) - 1)][1:], 16)
            _SEASON[st] = m
    a = np.asarray(im.convert("RGB")).astype(np.int64)
    code = a[..., 0] << 16 | a[..., 1] << 8 | a[..., 2]
    out = code.copy()
    order = ("dry", "turn") if season == "autumn" else ("dormant",) if season == "winter" else ()
    for st in order:
        for c, to in _SEASON[st].items():
            out[code == c] = to
    rgb = np.stack([out >> 16 & 255, out >> 8 & 255, out & 255], -1).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("place", choices=sorted(PLACES))
    ap.add_argument("--season")
    ap.add_argument("--out", default=str(ROOT / "out/artgen/smooth"))
    ap.add_argument("--compare", metavar="REV", help="slopes before (slopes.py at REV) | after (the working copy)")
    ap.add_argument("--scales", default="1", help="comma list of 1, 0.5, 0.25 (box filtered)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if not a.compare:
        render(PLACES[a.place], season=a.season).save(out / f"{a.place}.png")
        return 0
    before = render_slopes(PLACES[a.place], _old_slopes(a.compare), a.season)
    after = render_slopes(PLACES[a.place], slopes, a.season)
    tag = f"_{a.season}" if a.season else ""
    for sc in a.scales.split(","):
        f = float(sc)
        pair = [im if f == 1 else im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))),
                                            Image.BOX) for im in (before, after)]
        name = f"{a.place}{tag}" + ("" if f == 1 else f"_{sc.replace('.', '')}")
        side_by_side(*pair).save(out / f"{name}.png", optimize=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
