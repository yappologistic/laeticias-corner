"""Render models too large for one voxel grid: landmarks tens of tiles wide and hundreds of
pixels tall.

A big model is a builder function that fills whatever box of the model it is handed; every
shape it draws evaluates only where it meets that box (`Model.box_window`). Rendering runs in
two passes over chunks of a few tiles: the first builds each chunk and keeps only its solid
mask (bit-packed), the second rebuilds each chunk and shades it against the assembled mask, so
ambient occlusion and cast shadows see the whole building. Chunks are ray cast on their own
and composited by depth along the view ray, which gives exactly the image of the whole model;
outlines and quantisation run once on the composite, so chunk borders never show.

The composite also records which footprint tile each pixel's front-most surface stands on, so
the base layer can be cut into pieces (world-tech.md §1.3) that partition the rendered pixels
exactly, and which heights each footprint tile's column holds (the walk-tile headroom check).
"""

import importlib
from dataclasses import dataclass

import numpy as np

from pack import Sprite
from render import (SHADOW_ALPHA, SHADOW_SUN, Occupancy, Shaded, _shadowed, data_word, dither,
                    finish, shade)
from spec import DESIGN_TILE
from voxel import Halo, Model

CHUNK = 4 * DESIGN_TILE          # chunk edge in design units (4 tiles)
AO_MARGIN = 6                    # design units of neighbouring solids every chunk needs


@dataclass(frozen=True)
class BigModel:
    """A builder by reference (so worker processes can import it) and its extent.

    `ref` is (module, function, kwargs as a sorted tuple of pairs); the function takes a Model
    and fills it. The extent (x0, x1, y0, y1, z0, z1) is in design units; z0 < 0 allows
    foundations below the anchor level."""
    ref: tuple
    extent: tuple

    def build(self, box, k) -> Model:
        mod, fn, kw = self.ref
        m = Model.empty(*box, k=k)
        getattr(importlib.import_module(mod), fn)(m, **dict(kw))
        return m


def _chunks(extent):
    x0, x1, y0, y1, z0, z1 = extent
    for cx in range(x0, x1, CHUNK):
        for cy in range(y0, y1, CHUNK):
            yield (cx, min(cx + CHUNK, x1), cy, min(cy + CHUNK, y1), z0, z1)


def _pass_solid(args):
    big, box, k = args
    m = big.build(box, k)
    own = [h for h in m.halos if box[0] <= h.x < box[1] and box[2] <= h.y < box[3]]
    return box, np.packbits(m.mat > 0, axis=2), m.mat.shape[2], own


def _pass_shade(args):
    big, box, k, packed, origin, nz, zmax = args
    m = big.build(box, k)
    ctx = Occupancy(np.unpackbits(packed, axis=2, count=nz).astype(bool), *origin)
    sh = shade(m, ctx, zmax)
    hit = sh.mat > 0
    r, c = np.nonzero(hit)
    return (r + sh.r0, c + sh.c0, sh.mat[hit], sh.level[hit], sh.depth[hit], sh.vx[hit], sh.vy[hit],
            sh.geo[hit])


@dataclass
class BigRender:
    base: Sprite
    glow: Sprite | None
    shadow: Sprite
    tiles: np.ndarray               # (2, H, W): footprint tile (tx, ty) of each base pixel
    column: np.ndarray              # (fw, fh, nz) bool: solid at that height (px) on that tile
    top: int                        # highest solid voxel above the ground, px
    clear: np.ndarray               # (fw, fh): the most room under anything on that tile, px


def _grid_bounds(extent, k):
    x0, x1, y0, y1, z0, z1 = (v * k for v in extent)
    zlo = min(z0, 0) - 2                  # two rows of solid ground under the model
    return x0, x1, y0, y1, zlo, z1


def clearance(solid: np.ndarray, x0: int, y0: int, fw: int, fh: int, t: int) -> np.ndarray:
    """(fw, fh): per footprint tile, the highest of its voxel columns' lowest solid (px above the
    ground, `solid` starting at z 0 with its x, y origin at voxel (x0, y0)): the room under an arch
    or a deck; 0 where everything stands on the ground."""
    out = np.zeros((fw, fh), np.int64)
    has = solid.any(axis=2)
    low = np.argmax(solid, axis=2)
    for i in range(fw):
        for j in range(fh):
            a, b = i * t - x0, j * t - y0
            sub_has = has[max(a, 0):max(a + t, 0), max(b, 0):max(b + t, 0)]
            if sub_has.any():
                out[i, j] = int(low[max(a, 0):max(a + t, 0), max(b, 0):max(b + t, 0)][sub_has].max())
    return out


def solid_grid(big: BigModel, k: int, pool):
    """Pass one: the model's solid mask over its whole grid (ground rows below z 0 set) and the
    halos its chunks hold; returns (Occupancy, halos)."""
    gx0, gx1, gy0, gy1, gz0, gz1 = _grid_bounds(big.extent, k)
    occ = np.zeros((gx1 - gx0, gy1 - gy0, gz1 - gz0), bool)
    occ[:, :, :max(0, -gz0)] = True        # solid ground below z = 0
    halos: list[Halo] = []
    for box, packed, nz, own in pool.imap(_pass_solid, [(big, b, k) for b in _chunks(big.extent)]):
        solid = np.unpackbits(packed, axis=2, count=nz).astype(bool)
        i0, j0, l0 = box[0] * k - gx0, box[2] * k - gy0, box[4] * k - gz0
        sub = occ[i0:i0 + solid.shape[0], j0:j0 + solid.shape[1], l0:l0 + nz]
        sub |= solid
        halos += own
    halos.sort(key=lambda h: (h.x, h.y, h.z))
    return Occupancy(occ, gx0, gy0, gz0), halos


def render_big(big: BigModel, k: int, pool, footprint, want_glow=False) -> BigRender:
    """Render a big model with the worker pool; see the module notes."""
    gx0, gx1, gy0, gy1, gz0, gz1 = _grid_bounds(big.extent, k)
    ground, halos = solid_grid(big, k, pool)
    occ = ground.grid
    chunks = list(_chunks(big.extent))

    # Each chunk needs the solids that can shade it: occlusion all round, and everything
    # towards the sun (-x, +y) up to the top of the model.
    from render import SUN
    reach = (gz1 - 0) / SUN[2]
    mx, my = int(np.ceil(-SUN[0] * reach)), int(np.ceil(SUN[1] * reach))
    pad = AO_MARGIN * k
    jobs = []
    for box in chunks:
        bx0, bx1, by0, by1 = box[0] * k, box[1] * k, box[2] * k, box[3] * k
        wx0, wx1, wy0, wy1 = bx0 - pad - mx, bx1 + pad, by0 - pad, by1 + pad + my
        win = ground.window(wx0, wx1, wy0, wy1, gz0, gz1 + pad)
        jobs.append((big, box, k, np.packbits(win, axis=2), (wx0, wy0, gz0), win.shape[2], gz1))

    # Composite by depth into one screen buffer.
    sx = [x - y for x in (gx0, gx1) for y in (gy0, gy1)]
    c0, c1 = int(np.floor(min(sx))), int(np.ceil(max(sx)))
    r0 = int(np.floor((gx0 + gy0) / 2 - gz1))
    r1 = int(np.ceil((gx1 + gy1) / 2 - min(gz0, 0)))
    H, W = r1 - r0, c1 - c0
    mat = np.zeros((H, W), np.uint8)
    level = np.zeros((H, W), np.float32)
    depth = np.full((H, W), -1e9, np.float32)
    vx = np.zeros((H, W), np.int64)
    vy = np.zeros((H, W), np.int64)
    geo = np.zeros((H, W), np.uint32)
    for rr, cc, m, lv, d, x, y, g in pool.imap(_pass_shade, jobs):
        rr, cc = rr - r0, cc - c0
        near = d > depth[rr, cc]
        rr, cc = rr[near], cc[near]
        mat[rr, cc], level[rr, cc], depth[rr, cc] = m[near], lv[near], d[near]
        vx[rr, cc], vy[rr, cc], geo[rr, cc] = x[near], y[near], g[near]
    sh = Shaded(c0, r0, mat, level, depth, mat > 0, depth, vx, vy, geo)
    rgba, glow, ox, oy = finish(sh, k, halos, cull=True)
    base = Sprite(rgba, ox, oy, data_word(sh))
    glow_sprite = None
    if want_glow:
        glow_sprite = Sprite(glow if glow is not None else np.zeros_like(rgba), ox, oy)
    t = DESIGN_TILE * k
    tiles = np.stack([np.floor_divide(vx, t), np.floor_divide(vy, t)])
    # Per footprint tile: which heights above the ground hold solids.
    fw, fh = footprint
    zero = -gz0
    column = np.zeros((fw, fh, gz1), bool)
    for i in range(fw):
        for j in range(fh):
            a, b = i * t - gx0, j * t - gy0
            if a < 0 or b < 0:
                continue
            column[i, j] = occ[a:a + t, b:b + t, zero:].any(axis=(0, 1))[:gz1]
    solid_z = np.nonzero(occ[:, :, zero:].any(axis=(0, 1)))[0]
    top = int(solid_z.max() + 1) if solid_z.size else 0
    clear = clearance(occ[:, :, zero:], gx0, gy0, fw, fh, t)
    return BigRender(base, glow_sprite, _shadow(ground, gz1, k), tiles, column, top, clear)


def _shadow(occ: Occupancy, zmax: int, k: int) -> Sprite:
    """Cast shadow and contact darkening on the ground plane, as render.render_shadow, from
    the assembled solid mask (the ground rows themselves excluded)."""
    solid = occ.grid.copy()
    zero = -occ.z0
    solid[:, :, :zero] = False
    gx0, gy0 = occ.x0, occ.y0
    nx, ny = solid.shape[:2]
    reach = max(zmax, 0) / SHADOW_SUN[2]
    xs = [gx0, gx0 + nx - SHADOW_SUN[0] * reach]
    ys = [gy0 - SHADOW_SUN[1] * reach, gy0 + ny]
    sxs = [x - y for x in xs for y in ys]
    sys_ = [(x + y) / 2 for x in xs for y in ys]
    c0, c1 = int(np.floor(min(sxs))), int(np.ceil(max(sxs)))
    r0, r1 = int(np.floor(min(sys_))), int(np.ceil(max(sys_)))
    py, px = np.mgrid[r0:r1, c0:c1]
    sx, sy = px + 0.5, py + 0.5
    gx, gy = (sy + sx / 2).ravel(), (sy - sx / 2).ravel()
    grid = Occupancy(solid, occ.x0, occ.y0, occ.z0)
    cast = np.zeros(gx.size, bool)
    step = 1 << 18
    for a in range(0, gx.size, step):
        o = np.stack([gx[a:a + step], gy[a:a + step], np.full(min(step, gx.size - a), 0.05)], 1)
        cast[a:a + step] = _shadowed(grid, o.astype(np.float32), zmax, SHADOW_SUN)
    layer = solid[:, :, zero:zero + 3 * k].any(axis=2)
    r = 2 * k
    lp = np.pad(layer, r + 1)
    contact = np.zeros(gx.size, np.float32)
    fi = np.floor(gx).astype(np.int64) - gx0 + r + 1
    fj = np.floor(gy).astype(np.int64) - gy0 + r + 1
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            i, j = fi + dx, fj + dy
            ok = (i >= 0) & (i < lp.shape[0]) & (j >= 0) & (j < lp.shape[1])
            contact[ok] += lp[i[ok], j[ok]] * (1.0 / (1 + (abs(dx) + abs(dy)) / k))
    lvl = np.maximum(cast * 1.9, np.clip(contact / (3.0 * k * k), 0, 1) * 3.0)
    q = np.clip(dither(lvl.reshape(py.shape), px, py), 0, 3).astype(np.int64)
    rgba = np.zeros(py.shape + (4,), np.uint8)
    rgba[..., 3] = np.array(SHADOW_ALPHA, np.uint8)[q]
    return Sprite(rgba, -c0, -r0)
