"""Sloped ground: a tile whose surface falls one level toward some of its corners
(art-smooth-land.md §3, the slope contract). A shape is nine heights on a 3 x 3 grid over the
tile (corners, edge midpoints, centre) in levels relative to the tile's level L (0 or below, down
to -1), cut into eight triangles fanned round the centre; the engine walks and draws the same
mesh. A sprite is anchored at the top vertex of the tile at level L - 1 (its foot), so every
height in its data is 0..one level.

Slope art is the terrain's own flat art carried onto the mesh pixel by pixel (each pixel samples
the flat tile where its ground point lies, so slopes and flat ground share one field and meet
without a seam), lit by the surface's turn to the sun in steps of the palette, with its data word (normal,
height, sun, snow). Nothing marks a slope's own top or foot, so a hillside of slope tiles reads
as one surface."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from pack import Sprite
from render import dither

N_C, E_C, S_C, W_C = 1, 2, 4, 8            # corner bits: N (0,0), E (16,0), S (16,16), W (0,16)
SUN = np.array([-0.45, 0.28, 0.85]) / np.linalg.norm([-0.45, 0.28, 0.85])
UP_CODE = 15


def _corner_shape(mask: int) -> np.ndarray:
    """Heights [i, j] at u = 8i, v = 8j for a mask of low corners: midpoints and centre are the
    means of what they join, so straight slopes are planes and corners fold along the fan."""
    h = np.zeros((3, 3))
    h[0, 0] = -1.0 * bool(mask & N_C)
    h[2, 0] = -1.0 * bool(mask & E_C)
    h[2, 2] = -1.0 * bool(mask & S_C)
    h[0, 2] = -1.0 * bool(mask & W_C)
    h[1, 0] = (h[0, 0] + h[2, 0]) / 2
    h[2, 1] = (h[2, 0] + h[2, 2]) / 2
    h[1, 2] = (h[2, 2] + h[0, 2]) / 2
    h[0, 1] = (h[0, 0] + h[0, 2]) / 2
    h[1, 1] = (h[0, 0] + h[2, 0] + h[2, 2] + h[0, 2]) / 4
    return h


def _peak(kind: str) -> np.ndarray:
    """Every corner low: a knoll (only the centre stays up) or a ridge along x or y whose line
    stays up to the edge midpoints it continues through (`ridge_x` both, `ridge_x0` only toward
    u = 0, `ridge_x1` only toward u = 16; the same for y). Edge midpoints that are not part of a
    ridge stay low, so the tile meets its neighbours' edges exactly."""
    h = np.full((3, 3), -1.0)
    h[1, 1] = 0.0
    if kind.startswith("ridge_x"):
        h[0, 1] = 0.0 if kind in ("ridge_x", "ridge_x0") else -1.0
        h[2, 1] = 0.0 if kind in ("ridge_x", "ridge_x1") else -1.0
    elif kind.startswith("ridge_y"):
        h[1, 0] = 0.0 if kind in ("ridge_y", "ridge_y0") else -1.0
        h[1, 2] = 0.0 if kind in ("ridge_y", "ridge_y1") else -1.0
    return h


PEAKS = ("knoll", "ridge_x", "ridge_x0", "ridge_x1", "ridge_y", "ridge_y0", "ridge_y1")
SHAPES = {f"c{m}": _corner_shape(m) for m in range(1, 15)} | {k: _peak(k) for k in PEAKS}

# The eight triangles, as grid points (i, j): every one touches the centre.
FAN = [((0, 0), (1, 0), (1, 1)), ((1, 0), (2, 0), (1, 1)), ((2, 0), (2, 1), (1, 1)), ((2, 1), (2, 2), (1, 1)),
       ((2, 2), (1, 2), (1, 1)), ((1, 2), (0, 2), (1, 1)), ((0, 2), (0, 1), (1, 1)), ((0, 1), (0, 0), (1, 1))]


def ridge_axis(low: int, lower_edges: int) -> str | None:
    """'x' or 'y' when every corner is low and only the two sides across that axis fall (the
    lower edge neighbours as N_C..W_C bits standing for -y, +x, +y, -x)."""
    if low != 15:
        return None
    ys, xs = lower_edges & (N_C | S_C), lower_edges & (E_C | W_C)
    if ys == (N_C | S_C) and not xs:
        return "x"
    if xs == (E_C | W_C) and not ys:
        return "y"
    return None


def shape_of(low: int, lower_edges: int, ridge_on: tuple[bool, bool] = (False, False)) -> str | None:
    """The shape for a tile from its low corners, its lower edge neighbours and, for a ridge,
    whether the neighbours before and after it along the ridge's axis are ridges too (the ridge
    runs on through those edges). None for a flat tile."""
    if low == 0:
        return None
    if low != 15:
        return f"c{low}"
    axis = ridge_axis(low, lower_edges)
    if axis is None or not any(ridge_on):
        return "knoll"
    return f"ridge_{axis}" + ("" if all(ridge_on) else ("0" if ridge_on[0] else "1"))


def height(shape: str, u, v):
    """Surface height in levels (relative to L) at tile point (u, v), 0..16 each: the walker's
    height across the tile is this times the level's pixels, added to L's."""
    h = SHAPES[shape]
    u = np.clip(np.asarray(u, float), 0, 16)
    v = np.clip(np.asarray(v, float), 0, 16)
    out = np.zeros(np.broadcast(u, v).shape)
    done = np.zeros(out.shape, bool)
    for tri in FAN:
        (a, b, c) = [np.array([8.0 * i, 8.0 * j, h[i, j]]) for i, j in tri]
        w0, w1, w2 = _bary(u, v, a, b, c)
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9) & ~done
        out = np.where(inside, w0 * a[2] + w1 * b[2] + w2 * c[2], out)
        done |= inside
    return out


def _bary(u, v, a, b, c):
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    w0 = ((b[1] - c[1]) * (u - c[0]) + (c[0] - b[0]) * (v - c[1])) / d
    w1 = ((c[1] - a[1]) * (u - c[0]) + (a[0] - c[0]) * (v - c[1])) / d
    return w0, w1, 1 - w0 - w1


def _normal(a, b, c, lvl_units):
    """Unit normal (x, y, z up) of a triangle given as (u, v, levels); heights in tile units."""
    p = [np.array([q[0], q[1], q[2] * lvl_units]) for q in (a, b, c)]
    n = np.cross(p[1] - p[0], p[2] - p[0])
    n = n / np.linalg.norm(n)
    return n if n[2] > 0 else -n


@lru_cache(maxsize=None)
def raster(shape: str, k: int, lvl: int):
    """Per sprite pixel of a slope: (inside, u, v, height px above the foot, normal x, y, z,
    (du, dv) per screen row); sprite size 32k x (16k + lvl), anchor (16k, lvl). Pixel centres map to the
    ground point they show; a pixel belongs to the tile when that point lies in [0, 16)^2, the
    flat diamond's own rule, so slope and flat tiles partition the screen exactly."""
    h = SHAPES[shape]
    W, H = 32 * k, 16 * k + lvl
    ox, oy = 16 * k, lvl
    py, px = np.mgrid[0:H, 0:W]
    X = px + 0.5 - ox
    Y = py + 0.5 - oy
    lvl_units = lvl / k                       # a level's height in tile units (16 per edge)
    best = np.full((H, W), -1.0)
    U = np.zeros((H, W)); V = np.zeros((H, W)); Z = np.zeros((H, W)); T = np.full((H, W), -1)
    DU = np.zeros((H, W)); DV = np.zeros((H, W))
    normals = []
    for t, tri in enumerate(FAN):
        a, b, c = [np.array([8.0 * i, 8.0 * j, h[i, j]]) for i, j in tri]
        n = _normal(a, b, c, lvl_units)
        normals.append(n)
        gu, gv = n[0] / -n[2] / lvl_units, n[1] / -n[2] / lvl_units       # levels per unit
        z0 = a[2] - gu * a[0] - gv * a[1]
        # X = k (u - v);  Y = k/2 (u + v) - lvl (1 + z) with z = z0 + gu u + gv v
        m = np.array([[k, -k], [k / 2 - lvl * gu, k / 2 - lvl * gv]])
        det = np.linalg.det(m)
        if det <= 1e-9:
            continue
        inv = np.linalg.inv(m)
        yy = Y + lvl * (1 + z0)
        u = inv[0, 0] * X + inv[0, 1] * yy
        v = inv[1, 0] * X + inv[1, 1] * yy
        w0, w1, w2 = _bary(u, v, a, b, c)
        tol = 1e-9
        # Pixel centres can fall exactly on an edge of a slope (a whole number of pixels from
        # the anchor); one bias for every tile gives each such pixel to exactly one of them.
        ub, vb = u + 1e-7, v + 1e-7
        ok = (w0 >= -tol) & (w1 >= -tol) & (w2 >= -tol) & (ub >= 0) & (ub < 16) & (vb >= 0) & (vb < 16)
        front = ok & (u + v > best)
        best = np.where(front, u + v, best)
        U = np.where(front, u, U); V = np.where(front, v, V)
        Z = np.where(front, z0 + gu * u + gv * v, Z); T = np.where(front, t, T)
        DU = np.where(front, inv[0, 1], DU); DV = np.where(front, inv[1, 1], DV)
    inside = T >= 0
    N = np.array(normals)[np.clip(T, 0, 7)]
    hpx = np.clip(np.round((1 + Z) * lvl), 0, lvl).astype(np.int64)
    return inside, U, V, hpx, N, (DU, DV), (W, H, ox, oy)


def light(n) -> np.ndarray:
    """The generator's baked sun for a normal (render.py): 0.42 + 0.58 max(0, N.S)."""
    return 0.42 + 0.58 * np.clip(n @ SUN, 0, None)


FLAT = float(light(np.array([0.0, 0.0, 1.0])))


@lru_cache(maxsize=4)
def _oklab_palette(pal: tuple):
    """Oklab of every palette colour (sorted codes) for shading by neighbours in the palette."""
    rgb = np.array([[(c >> 16) & 255, (c >> 8) & 255, c & 255] for c in pal], float) / 255
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    lms = np.cbrt(lin @ m1.T)
    m2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    return lms @ m2.T


@lru_cache(maxsize=4)
def steps(pal: tuple) -> tuple[np.ndarray, np.ndarray]:
    """For each palette colour (sorted codes) the index of the colour one step darker and one
    step lighter: its neighbour in its own palette group when the set has it, else the nearest
    in hue about one ramp step away in lightness, else itself, so shading keeps the family."""
    from palette import GROUPS, _rgb
    lab = _oklab_palette(pal)
    codes = list(pal)
    where = {c: i for i, c in enumerate(codes)}
    n = len(pal)
    down = np.arange(n)
    up = np.arange(n)
    for ramp in GROUPS.values():
        cs = [(lambda t: (t[0] << 16) | (t[1] << 8) | t[2])(_rgb(h)) for h in ramp]
        for j, c in enumerate(cs):
            if c not in where:
                continue
            if j > 0 and cs[j - 1] in where:
                down[where[c]] = where[cs[j - 1]]
            if j + 1 < len(cs) and cs[j + 1] in where:
                up[where[c]] = where[cs[j + 1]]
    for i in range(n):
        dl = lab[:, 0] - lab[i, 0]
        hue = np.hypot(lab[:, 1] - lab[i, 1], lab[:, 2] - lab[i, 2])
        for want, out in ((-1, down), (1, up)):
            if out[i] != i:
                continue
            ok = (dl * want > 0.035) & (dl * want < 0.16) & (hue < 0.05)
            if ok.any():
                cost = (np.abs(dl) - 0.08) ** 2 + 2.5 * hue ** 2
                out[i] = int(np.argmin(np.where(ok, cost, np.inf)))
    return down, up


def shade(rgb: np.ndarray, shift: np.ndarray, pal: tuple, where: np.ndarray) -> np.ndarray:
    """Move each pixel's colour `shift` palette steps (negative darker), whole steps only, where
    `where` holds (the rest is returned as it is)."""
    codes = np.asarray(pal)
    code = (rgb[..., 0].astype(np.int64) << 16) | (rgb[..., 1].astype(np.int64) << 8) | rgb[..., 2]
    idx = np.clip(np.searchsorted(codes, code), 0, len(codes) - 1)
    if not (codes[idx] == code)[where].all():
        raise ValueError("slopes.shade: a colour outside the palette")
    shift = np.where(where, shift, 0)
    down, up = steps(pal)
    for _ in range(int(np.abs(shift).max(initial=0))):
        idx = np.where(shift < 0, down[idx], np.where(shift > 0, up[idx], idx))
        shift = shift - np.sign(shift)
    out = np.stack([(codes[idx] >> 16) & 255, (codes[idx] >> 8) & 255, codes[idx] & 255], -1)
    return out.astype(np.uint8)


def _extend(rgba: np.ndarray) -> np.ndarray:
    """The flat art with its edge pixels carried outward into the transparent corners, so a
    ground point on the tile's very edge always finds a colour (a slope maps pixel centres to
    ground points by its own rule, which can land a hair outside the flat raster)."""
    out = rgba.copy()
    for _ in range(4):
        hole = out[..., 3] < 255
        if not hole.any():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(np.roll(out, dy, 0), dx, 1)
            take = hole & (src[..., 3] == 255)
            out[take] = src[take]
            hole &= ~take
    return out


def _sample(rgba: np.ndarray, ox, oy, U, V, k):
    fx = np.clip(np.floor((U - V) * k + ox), 0, rgba.shape[1] - 1).astype(np.int64)
    fy = np.clip(np.floor((U + V) * k / 2 + oy), 0, rgba.shape[0] - 1).astype(np.int64)
    return rgba[fy, fx]


def slope_sprite(flat: Sprite, shape: str, k: int, lvl: int, pal: tuple, gain: float = 1.0) -> Sprite:
    """The flat tile `flat` (a ground diamond, anchor (16k, 0)) laid on `shape` and lit. Where
    a slope turns away and one screen row covers more than a row of the flat art, the pixel
    takes the commonest of three samples down its footprint instead of one, so foreshortened
    ground keeps its marks instead of breaking into noise."""
    inside, U, V, hpx, N, (DU, DV), (W, H, ox, oy) = raster(shape, k, lvl)
    art = _extend(flat.rgba)
    mid = _sample(art, flat.ox, flat.oy, U, V, k)
    lo = _sample(art, flat.ox, flat.oy, U - DU / 3, V - DV / 3, k)
    hi = _sample(art, flat.ox, flat.oy, U + DU / 3, V + DV / 3, k)
    same = (lo == hi).all(-1)
    src = np.where(same[..., None], lo, mid)
    py, px = np.mgrid[0:H, 0:W]
    lit = light(N.reshape(-1, 3)).reshape(H, W)
    s = (lit / FLAT - 1.0) / 0.10 * gain
    whole = dither(s, px, py, 0.3)
    rgb = shade(src[..., :3], whole.astype(np.int64), pal, inside)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = np.where(inside[..., None], rgb, 0)
    rgba[..., 3] = inside * 255
    codes = np.clip(np.round(N * 15 + 15), 0, 30).astype(np.uint32)
    snow = (N[..., 2] > 0.55)
    word = (codes[..., 0] << 11) | (codes[..., 1] << 16) | (hpx.astype(np.uint32) << 21) | np.uint32(1 << 30) \
        | (snow.astype(np.uint32) << 31)
    data = np.where(inside, word, 0).astype(np.uint32)
    return Sprite(rgba, ox, oy, data)


def palette_codes(colours) -> tuple:
    """Sorted colour codes of a palette given as hex strings."""
    out = set()
    for h in colours:
        h = h.lstrip("#")
        out.add(int(h, 16))
    return tuple(sorted(out))


def check_flat(k: int, lvl: int) -> bool:
    """A sanity check: with no low corner the raster is the flat diamond lifted one level."""
    import terrain as home
    SHAPES["_flat"] = np.zeros((3, 3))
    inside = raster("_flat", k, lvl)[0]
    del SHAPES["_flat"]
    raster.cache_clear()
    g = home._grid(k)
    return bool((inside[:16 * k] == g.inside).all() and not inside[16 * k:].any())


