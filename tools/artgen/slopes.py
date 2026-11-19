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
from voxel import hash01

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
    vn = _vertex_normals(normals)
    Ns = np.zeros((H, W, 3))
    for t, tri in enumerate(FAN):
        sel = T == t
        if not sel.any():
            continue
        a, b, c = [np.array([8.0 * i, 8.0 * j, 0.0]) for i, j in tri]
        w0, w1, w2 = _bary(U[sel], V[sel], a, b, c)
        Ns[sel] = w0[:, None] * vn[tri[0]] + w1[:, None] * vn[tri[1]] + w2[:, None] * vn[tri[2]]
    Ns[~inside] = (0.0, 0.0, 1.0)
    Ns /= np.linalg.norm(Ns, axis=-1, keepdims=True)
    hpx = np.clip(np.round((1 + Z) * lvl), 0, lvl).astype(np.int64)
    return inside, U, V, hpx, Ns, (DU, DV), (W, H, ox, oy), Z


def _vertex_normals(normals) -> dict:
    """The normal at each of the nine grid points: the mean of the tile's facets meeting there.
    Interpolated across each triangle it rounds the fan's folds into one curved surface; on a
    plane every point keeps the plane's normal, so a hillside of planes stays one even field and
    meets its neighbours with the same light."""
    acc: dict = {}
    for n, tri in zip(normals, FAN):
        for p in tri:
            acc.setdefault(p, []).append(n)
    out = {}
    for p, ns in acc.items():
        m = np.mean(ns, axis=0)
        out[p] = m / np.linalg.norm(m)
    return out


def light(n) -> np.ndarray:
    """The generator's baked sun for a normal (render.py): 0.42 + 0.58 max(0, N.S)."""
    return 0.42 + 0.58 * np.clip(n @ SUN, 0, None)


FLAT = float(light(np.array([0.0, 0.0, 1.0])))

# Ground is lit by the whole sky as well as the sun, so its turn to the sun moves its light far
# less than a wall's: a slope facing away is about one palette step darker than flat ground, a
# slope facing the sun a little lighter (terrain notes §1). `ground_light` is the ratio over flat
# ground the art bakes; the engine tints anything it warps onto a slope by the same function of
# the same per-vertex normal (src/worldview/terrain.hpp `slopeLight`).
GROUND_GAIN = 0.35
GROUND_RANGE = (0.85, 1.12)
STEP_RATIO = 0.12               # light ratio per palette step on ground


def ground_light(n) -> np.ndarray:
    """Light of ground with unit normal `n` over flat ground's: 1 + 0.35 (n.S - up.S), clamped
    to 0.85..1.12."""
    return np.clip(1.0 + GROUND_GAIN * (np.asarray(n) @ SUN - SUN[2]), *GROUND_RANGE)


@lru_cache(maxsize=4)
def steps(pal: tuple) -> tuple[np.ndarray, np.ndarray]:
    """For each palette colour (sorted codes) the index of the colour one step darker and one
    step lighter in its own palette group; a colour at the end of its group stays itself, so
    shading never leaves the material's family (a green-brown floor never turns red-brown)."""
    from palette import GROUPS, _rgb
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
            if j > 0 and cs[j - 1] in where and down[where[c]] == where[c]:
                down[where[c]] = where[cs[j - 1]]
            if j + 1 < len(cs) and cs[j + 1] in where and up[where[c]] == where[c]:
                up[where[c]] = where[cs[j + 1]]
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


def _texel(flat: Sprite, U, V, k):
    """Integer texel (column, row) of the flat art showing ground point (u, v)."""
    fx = np.floor((U - V) * k + flat.ox).astype(np.int64)
    fy = np.floor((U + V) * k / 2 + flat.oy).astype(np.int64)
    return np.clip(fx, 0, flat.rgba.shape[1] - 1), np.clip(fy, 0, flat.rgba.shape[0] - 1)


def _luma_rank(rgba: np.ndarray) -> np.ndarray:
    """Each texel's lightness as its rank among the tile's texels, 0 (darkest) .. 1: shading
    takes the dark texels first going darker and the light ones first going lighter, so a
    slope's light grows out of the ground's own marks instead of a screen pattern."""
    luma = rgba[..., 0] * 0.299 + rgba[..., 1] * 0.587 + rgba[..., 2] * 0.114
    on = rgba[..., 3] > 0
    order = np.argsort(np.where(on, luma, -1).ravel(), kind="stable")
    rank = np.empty(order.size)
    rank[order] = np.arange(order.size)
    first = (~on).sum()
    return np.clip((rank.reshape(luma.shape) - first) / max(on.sum() - 1, 1), 0, 1)


def slope_sprite(flat: Sprite, shape: str, k: int, lvl: int, pal: tuple, seed: int = 0,
                 material: str = "soil", rock: tuple = ()) -> Sprite:
    """The flat tile `flat` (a ground diamond, anchor (16k, 0)) laid on `shape` and lit.

    - Each pixel shows the flat art's texel at its ground point. Where a slope turns toward the
      viewer one texel spans more than one screen row; those rows take a neighbouring texel of
      the same ground instead of repeating it (a jitter along the row's own direction, as large
      as the stretch), so the ground keeps its grain instead of being combed into streaks. Where
      it turns away and a row spans several texels, the commonest of three samples is taken.
    - Light: `ground_light` of the normal smoothed over the tile (`raster`), in whole palette
      steps inside each colour's group; the fraction between steps goes to the texels by their
      own lightness, so shade sits in the ground's hollows and light on its tops.
    - The ground's own marks of a slope by `material` (`_details`), different for each `seed`
      (look); steep ground breaks into the `rock` ramp (dark to light) where the material would.
    """
    inside, U, V, hpx, N, (DU, DV), (W, H, ox, oy), Z = raster(shape, k, lvl)
    art = _extend(flat.rgba)
    py, px = np.mgrid[0:H, 0:W]
    # Rows per texel: a flat diamond steps 1/k of a unit in u and v per screen row.
    per_row = np.hypot(DU, DV) * k / np.sqrt(2)
    stretch = np.where(per_row > 1e-6, 1 / np.maximum(per_row, 1e-6), 1)
    j = (hash01(px, py, 7101 + seed) - 0.5) * np.clip(stretch - 1, 0, 2)
    ju, jv = U + j * DU, V + j * DV
    jx, jy = _texel(flat, ju, jv, k)
    lx, ly = _texel(flat, U - DU / 3, V - DV / 3, k)
    hx, hy = _texel(flat, U + DU / 3, V + DV / 3, k)
    lo, hi = art[ly, lx], art[hy, hx]
    squeeze = (stretch < 0.95) & (lo == hi).all(-1)
    tx, ty = np.where(squeeze, lx, jx), np.where(squeeze, ly, jy)
    src = art[ty, tx]
    rank = _luma_rank(art)[ty, tx]
    grain = hash01(tx, ty, 7103 + seed)
    s = (ground_light(N.reshape(-1, 3)).reshape(H, W) - 1.0) / STEP_RATIO
    whole = np.floor(s + 0.75 * rank + 0.25 * grain).astype(np.int64)
    marks, stone = _details(material, seed, inside, U, V, Z, N, px, py)
    rgb = shade(src[..., :3], whole + marks, pal, inside)
    if rock and stone.any():
        ramp = np.array([[int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)] for c in rock], np.uint8)
        rgb[stone > 0] = ramp[np.clip(stone[stone > 0] - 1, 0, len(ramp) - 1)]
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


# ---------------------------------------------------------------- the marks of a slope

def material_of(tid: str) -> str:
    """How a terrain wears a slope: `grass` (sheep-worn terracettes along the contours, soil and
    rock breaking through where it is steep), `soil` (rills washed down the fall line), `sand`
    (wind ripples along the contours), `rock` (ledges along the contours, cracks and scree
    streaks down the fall line), `forest` (litter washed into a few rills, roots and stones
    where steep) or `snow` (smooth; rock where steep)."""
    name = tid.split(".")[-1]
    if "snow" in name:
        return "snow"
    if any(w in name for w in ("rock", "scree", "rough")):
        return "rock"
    if "sand" in name or "dune" in name:
        return "sand"
    if "forest" in name:
        return "forest"
    if any(w in name for w in ("grass", "steppe", "pasture", "scrub")):
        return "grass"
    return "soil"


# Per material: contour spacing (levels, 0 = none), how much of each contour shows, rill
# spacing (tile units, 0 = none), how much of each rill shows, the steepness (rise over run)
# from which rock breaks through (0 = never).
MARKS = {
    "grass":  (0.30, 0.42, 0.0, 0.0, 0.70),
    "soil":   (0.0, 0.0, 2.4, 0.45, 0.0),
    "sand":   (0.20, 0.55, 0.0, 0.0, 0.0),
    "rock":   (0.30, 0.45, 4.2, 0.22, 0.55),
    "forest": (0.0, 0.0, 3.4, 0.30, 0.80),
    "snow":   (0.0, 0.0, 0.0, 0.0, 0.80),
}


def _details(material, seed, inside, U, V, Z, N, px, py):
    """Palette-step marks (a shift per pixel) and rock (0, or 1 + an index on the rock ramp) of
    a slope. Everything stays off a margin along the tile's edges, so a mark never meets a
    neighbour's edge cut short, and is placed by the ground point (u, v), not the screen.
    Contours run on height, rills on the fall line of the smoothed surface; both break into
    pieces by noise, so no line runs ruled across a tile."""
    from voxel import value_noise
    cs, cshow, rs, rshow, steep_at = MARKS.get(material, MARKS["soil"])
    H, W = inside.shape
    marks = np.zeros((H, W), np.int64)
    stone = np.zeros((H, W), np.int64)
    edge = np.minimum(np.minimum(U, 16 - U), np.minimum(V, 16 - V))
    calm = inside & (edge > 1.6)
    nz = np.maximum(N[..., 2], 1e-3)
    tilt = np.hypot(N[..., 0], N[..., 1]) / nz            # rise over run
    dx = np.where(tilt > 1e-6, N[..., 0] / np.maximum(np.hypot(N[..., 0], N[..., 1]), 1e-6), 0)
    dy = np.where(tilt > 1e-6, N[..., 1] / np.maximum(np.hypot(N[..., 0], N[..., 1]), 1e-6), 0)
    sloped = calm & (tilt > 0.2)

    def below(a):               # the pixel one row down (the last row has none)
        out = np.full_like(a, -10 ** 6)
        out[:-1] = a[1:]
        return out

    if cs:
        off = hash01(seed, 7201) * cs
        gap = cs * (0.75 if material == "rock" else 1.0) / np.where(tilt > 0.8, 1.4, 1.0)
        # Contours wander (a slow warp of the height) and break into pieces of uneven length.
        wz = Z + 0.16 * (value_noise(U + 17 * seed, V, 1.0, 4.5, 7202 + seed) - 0.5) * cs / 0.3
        band = np.floor((wz - off) / gap).astype(np.int64)
        line = sloped & (band != below(band)) & np.roll(sloped, -1, 0)
        keep = value_noise(U + 31 * seed, V, band * 3.0, 2.2, 7203 + seed) < cshow
        line &= keep
        lip = np.roll(line, -1, 0) & ~line & sloped        # the row above a contour: its lit tread
        marks -= line
        if material != "sand":
            marks += lip
        else:
            marks += np.roll(line, -2, 0) & ~line & sloped
    if rs:
        a = U * -dy + V * dx                                 # across the fall line
        b = U * dx + V * dy                                  # down it
        a2 = a / rs + hash01(seed, 7205) * 7
        cell = np.floor(a2).astype(np.int64)
        on = np.abs(a2 - cell - 0.25 - 0.5 * hash01(cell, seed, 7207)) * rs < 0.32
        run = value_noise(cell * 5.0, b, seed * 3.0, 2.2, 7209 + seed) < rshow
        rill = sloped & on & run & (tilt > 0.3)
        marks -= rill
        lit = np.roll(rill, -1, 1) & ~rill & sloped          # the lip on the sun's side (left)
        marks += lit
    if steep_at:
        bare = calm & (tilt > steep_at)
        blob = value_noise(U, V, seed * 1.7, 2.3, 7211 + seed)
        want = bare & (blob > 0.78 - 0.30 * np.clip(tilt - steep_at, 0, 1))
        # Rock pieces: lit on the side toward the sun, dark at their foot, a mid body.
        up_ = np.roll(want, 1, 0)
        down_ = np.roll(want, -1, 0)
        left = np.roll(want, 1, 1)
        lightn = 2 + (N @ SUN > 0.8) + (N @ SUN > 0.6)
        body = np.where(want, lightn, 0)
        body = np.where(want & ~up_, lightn + 1, body)      # top edge catches light
        body = np.where(want & ~left, np.maximum(body, lightn + 1), body)
        body = np.where(want & ~down_, 1, body)             # foot in shade
        stone = np.where(want, body + 1, 0)
        foot = np.roll(want, 1, 0) & ~want & calm           # its shadow on the ground below
        marks -= foot
    return marks, stone
