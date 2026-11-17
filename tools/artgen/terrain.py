"""Ground tiles, cliff faces and cursor diamonds, evaluated per pixel on the tile plane.

Each pixel centre of a tile maps to one point (u, v) of the tile square [0, 16)^2 (u along +x,
v along +y). Textures are functions of (u, v) that repeat every 16 voxels, so any arrangement of
tiles is seamless. Overlay shapes depend on the 4-bit mask only through each edge's own state:
an open edge (same terrain beyond) is fully covered and every inset tapers to zero at a corner
next to an open edge, so neighbouring tiles always agree along their shared edge.
"""

import math

import numpy as np

from pack import Sprite
from palette import EARTH, GLOW, INK, LEAF, PLASTER, POPPY, ROOF, STONE, STRAW, VIOLET, WATER, _rgb
from render import BAYER4, dither
from voxel import hash01, value_noise

N_BIT, E_BIT, S_BIT, W_BIT = 1, 2, 4, 8
TW, TH = 32, 16
GRASS = [LEAF[1], LEAF[2], LEAF[3], LEAF[4], LEAF[5]]
MEADOW = [LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]]


def _grid():
    """Pixel grid of a tile sprite (32x16, anchor at (16, 0)) and its tile-plane coordinates."""
    py, px = np.mgrid[0:TH, 0:TW]
    sx, sy = px - 16 + 0.5, py + 0.5
    u, v = sy + sx / 2, sy - sx / 2
    inside = (u >= 0) & (u < 16) & (v >= 0) & (v < 16)
    return px, py, u, v, inside


def _ramp(colors):
    return np.array([_rgb(c) for c in colors], np.uint8)


def _paint(colors, level, px, py, band=0.55):
    ramp = _ramp(colors)
    idx = np.clip(dither(level, px, py, band), 0, len(ramp) - 1).astype(np.int64)
    return ramp[idx]


def _pnoise(u, v, cells, seed, t=0.0):
    """Value noise tiling every 16 voxels: `cells` lattice cells per tile edge."""
    scale = 16.0 / cells
    return value_noise(u, v, np.full_like(u, t), scale, seed, period=cells)


def _sprite(rgb, alpha) -> Sprite:
    rgba = np.zeros((TH, TW, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha
    return Sprite(rgba, 16, 0)


# ---------- stamps: little screen-space marks scattered on a periodic lattice ----------

def _scatter(u, v, cell, seed, density, jitter=0.8, interior=None):
    """For each pixel, offset (dx, dy) in screen px to the nearest scattered point, and its hash.

    Points sit on a jittered lattice with `cell` voxels spacing (cell divides 16). With
    `interior` set, only points at least that far inside the tile are kept, so variant-specific
    marks never cross into a neighbour that might be a different variant.
    """
    best = np.full(u.shape, 1e9, np.float32)
    bdx = np.zeros(u.shape, np.float32)
    bdy = np.zeros(u.shape, np.float32)
    bh = np.zeros(u.shape, np.float32)
    n = int(16 // cell)
    cu, cv = np.floor(u / cell).astype(np.int64), np.floor(v / cell).astype(np.int64)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            iu, iv = cu + du, cv + dv
            ku, kv = iu % n, iv % n
            keep = hash01(ku, kv, seed, 1) < density
            pu = (iu + 0.5 + (hash01(ku, kv, seed, 2) - 0.5) * jitter) * cell
            pv = (iv + 0.5 + (hash01(ku, kv, seed, 3) - 0.5) * jitter) * cell
            if interior is not None:
                keep &= (pu >= interior) & (pu < 16 - interior) & (pv >= interior) & (pv < 16 - interior)
            dx = (u - pu) - (v - pv)
            dy = ((u - pu) + (v - pv)) / 2
            d = dx * dx + 4 * dy * dy
            better = keep & (d < best)
            best = np.where(better, d, best)
            bdx = np.where(better, dx, bdx)
            bdy = np.where(better, dy, bdy)
            bh = np.where(better, hash01(ku, kv, seed, 4), bh)
    return bdx, bdy, bh, best < 1e8


def _tufts(level, u, v, seed, density, cell=4, interior=None, strength=1.0):
    """Grass tufts: a dark notch with a light tip just above it."""
    dx, dy, h, ok = _scatter(u, v, cell, seed, density, interior=interior)
    rx, ry = np.round(dx - 0.5), np.round(dy - 0.5)
    tip = ok & (ry == -1) & ((rx == 0) | ((rx == -1) & (h > 0.5)))
    base = ok & (ry == 0) & (np.abs(rx + 0.5) <= 1.0)
    level = level - base * 1.2 * strength
    return level + tip * 1.3 * strength


# ---------- grass ----------

def _grass_level(u, v):
    patches = _pnoise(u, v, 2, 11) * 0.7 + _pnoise(u, v, 4, 12) * 0.3
    return 2.0 + (patches - 0.5) * 1.6


def grass(variant: int) -> Sprite:
    px, py, u, v, inside = _grid()
    level = _grass_level(u, v)
    level = _tufts(level, u, v, 20, 0.35)                                 # shared, may cross edges
    level = _tufts(level, u, v, 30 + variant, 0.55, cell=2, interior=1.5, strength=0.8)
    rgb = _paint(GRASS, level, px, py)
    # A few variant-specific specks: a clover, a pebble, a fallen petal.
    dx, dy, h, ok = _scatter(u, v, 8, 40 + variant, 0.5, interior=3)
    dot = ok & (np.abs(dx) < 1) & (np.abs(dy) < 0.5)
    rgb = np.where((dot & (h < 0.3))[..., None], _rgb(LEAF[5]), rgb)
    rgb = np.where((dot & (h > 0.85))[..., None], _rgb(STRAW[3]), rgb)
    return _sprite(rgb, inside * 255)


# ---------- overlay shapes ----------

TAPER = 6.0


def _taper(t, open_lo, open_hi):
    """1 along an edge, easing to 0 at ends that meet an open edge (t in [0, 16])."""
    w = np.ones_like(t)
    if open_lo:
        w = w * (1 - np.cos(np.pi * np.clip(t / TAPER, 0, 1))) / 2
    if open_hi:
        w = w * (1 - np.cos(np.pi * np.clip((16 - t) / TAPER, 0, 1))) / 2
    return w


def shape_field(mask: int, u, v, inset: float, radius: float, wobble: float, seed: int):
    """Signed distance-like field, > 0 inside the overlay. Open edges stay fully covered."""
    n, e, s, w = (bool(mask & b) for b in (N_BIT, E_BIT, S_BIT, W_BIT))
    big = np.full_like(u, 1e3)

    def edge_inset(t, lo_open, hi_open, k):
        wob = (value_noise(t, np.zeros_like(t), np.zeros_like(t), 3.0, seed + k) - 0.5) * 2
        return (inset + wobble * wob) * _taper(t, lo_open, hi_open)

    dn = big if n else v - edge_inset(u, w, e, 1)
    ds = big if s else (16 - v) - edge_inset(u, w, e, 2)
    dw = big if w else u - edge_inset(v, n, s, 3)
    de = big if e else (16 - u) - edge_inset(v, n, s, 4)
    f = np.minimum(np.minimum(dn, ds), np.minimum(dw, de))
    r = radius
    for a, b, closed in ((dw, dn, not (w or n)), (de, dn, not (e or n)),
                         (dw, ds, not (w or s)), (de, ds, not (e or s))):
        if closed:
            corner = (a < r) & (b < r)
            f = np.where(corner, np.minimum(f, r - np.hypot(r - a, r - b)), f)
    return f


# ---------- meadow ----------

FLOWER_COLORS = [PLASTER[4], STRAW[3], VIOLET[3], POPPY[1], PLASTER[4], STRAW[2]]


def meadow(mask: int) -> Sprite:
    px, py, u, v, inside = _grid()
    f = shape_field(mask, u, v, 1.4, 5.5, 0.9, 300)
    # Soft border: dither the last voxel so meadow frays into the grass.
    edge_noise = hash01(np.floor(u * 2).astype(np.int64), np.floor(v * 2).astype(np.int64), 301)
    cover = inside & (f > 0.6 * edge_noise)
    level = 2.0 + (_pnoise(u, v, 2, 310) - 0.5) * 1.0
    level = _tufts(level, u, v, 311, 0.5, cell=2, strength=0.8)
    level = _tufts(level, u, v, 312, 0.6, cell=4, strength=1.1)
    rgb = _paint(MEADOW, level, px, py)
    dx, dy, h, ok = _scatter(u, v, 4, 320, 0.8, jitter=0.9)
    head = ok & (np.round(dx - 0.5) == 0) & (np.round(dy - 0.5) == 0)
    under = ok & (np.round(dx - 0.5) == 0) & (np.round(dy - 0.5) == 1)
    colors = np.array([_rgb(c) for c in FLOWER_COLORS], np.uint8)
    pick = colors[np.minimum((h * len(FLOWER_COLORS)).astype(np.int64), len(FLOWER_COLORS) - 1)]
    # Keep flowers off the frayed rim so they never float on plain grass.
    rgb = np.where((under & (f > 1.5))[..., None], _rgb(LEAF[2]), rgb)
    rgb = np.where((head & (f > 1.5))[..., None], pick, rgb)
    return _sprite(rgb, cover * 255)


# ---------- path ----------

PATH = [EARTH[1], EARTH[2], EARTH[3], EARTH[4], EARTH[5]]


def path(mask: int) -> Sprite:
    px, py, u, v, inside = _grid()
    f = shape_field(mask, u, v, 1.6, 5.5, 0.7, 400)
    cover = inside & (f > 0)
    level = 2.3 + (_pnoise(u, v, 4, 410) - 0.5) * 1.0 + (_pnoise(u, v, 8, 411) - 0.5) * 0.5
    # Pebbles: light top, dark underside.
    dx, dy, h, ok = _scatter(u, v, 2, 420, 0.35)
    rx, ry = np.round(dx - 0.5), np.round(dy - 0.5)
    big = h > 0.7
    top = ok & (ry == 0) & ((rx == 0) | (big & (rx == -1)))
    bottom = ok & (ry == 1) & ((rx == 0) | (big & (rx == -1)))
    level = level + top * 1.6 - bottom * 1.4
    # Worn rim: darker earth just inside the border, with a lighter crest before it.
    level = level - np.clip(1.4 - f, 0, 1) * 1.6 + ((f > 1.4) & (f < 2.2)) * 0.5
    rgb = _paint(PATH, level, px, py)
    return _sprite(rgb, cover * 255)


# ---------- cobble ----------

COBBLE = [INK, STONE[1], STONE[2], STONE[3], STONE[4], STONE[5]]


def cobble(mask: int) -> Sprite:
    px, py, u, v, inside = _grid()
    f = shape_field(mask, u, v, 1.2, 4.0, 0.4, 500)
    cover = inside & (f > 0)
    row_h, stone_w = 4.0, 16.0 / 3
    row = np.floor(v / row_h)
    off = (row % 2) * stone_w / 2
    col = np.floor((u + off) / stone_w)
    lu = (u + off) - col * stone_w          # position inside the stone
    lv = v - row * row_h
    key_u = (col % 3).astype(np.int64)
    key_v = (row % 4).astype(np.int64)
    tint = hash01(key_u, key_v, 510)
    # Rounded-rectangle distance to the stone's edge, used for mortar and bevel.
    eu = np.minimum(lu, stone_w - lu)
    ev = np.minimum(lv, row_h - lv)
    edge = np.minimum(eu, ev * 1.2)
    mortar = edge < 0.55
    level = 3.0 + (tint - 0.5) * 1.4
    level = level + ((lu < 1.3) | (lv < 1.1)) * 0.8 - ((stone_w - lu < 1.3) | (row_h - lv < 1.1)) * 0.9
    level = np.where(mortar, 1.0, level)
    level = level - np.clip(1.2 - f, 0, 1) * 1.5
    rgb = _paint(COBBLE, level, px, py, band=0.4)
    # Moss creeping into a few joints.
    moss = mortar & (_pnoise(u, v, 4, 520) > 0.66)
    rgb = np.where(moss[..., None], _rgb(LEAF[2]), rgb)
    return _sprite(rgb, cover * 255)


# ---------- water ----------

WALL = [INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3]]
GLINT_LEN = (0, 1, 3, 1)


def water(mask: int, frame: int, frames: int) -> Sprite:
    px, py, u, v, inside = _grid()
    field = lambda du: shape_field(mask, u - du, v - du, 1.4, 5.5, 0.7, 600)
    f = field(0)
    cover = inside & (f > 0)
    # The water sits a little below the ground: where the shore is just above on screen we
    # look at the earth bank, two pixels tall; elsewhere only a thin lip shows.
    wall1, wall2, shade = field(1) <= 0, field(2) <= 0, field(3) <= 0
    lip = f < 0.6
    depth = np.clip(f / 6, 0, 1)
    level = 3.2 - depth * 1.5 + (_pnoise(u, v, 2, 610) - 0.5) * 0.5
    level = level - shade * 1.0              # the bank's shadow on the water
    dx, dy, h, ok = _scatter(u, v, 4, 620, 0.45, jitter=0.9)
    length = np.array(GLINT_LEN)[(frame * len(GLINT_LEN) // frames + (h * 4).astype(np.int64)) % 4]
    rx, ry = np.round(dx - 0.5), np.round(dy - 0.5)
    glint = ok & (ry == 0) & (np.abs(rx + 0.5) < length / 2) & (f > 2.0)
    level = level + glint * 1.6 + (glint & (np.abs(rx + 0.5) < 1)) * 0.6
    rgb = _paint(WATER, level, px, py)
    rgb = np.where((lip & ~wall2)[..., None], _rgb(WATER[4]), rgb)
    wall_level = np.where(wall1, 3.2, 2.0) - (_pnoise(u, v, 8, 640) - 0.5) * 0.8
    rgb = np.where((wall2 | lip & (f < 0.25))[..., None], _paint(WALL, wall_level, px, py), rgb)
    return _sprite(rgb, cover * 255)


# ---------- cliffs ----------

CLIFF_DEPTH = 34
SOIL = [INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3]]
ROCK = [INK, STONE[0], STONE[1], STONE[2], STONE[3]]


def cliff(face: str) -> Sprite:
    """The earth face under one rim tile: 'se' is the +x face, 'sw' the +y face (sun side).

    Everything is a function of (s, depth) with s the position along the rim, repeating every
    tile, so the faces join seamlessly along the whole rim and at the bottom corner."""
    W, H = TW, 8 + CLIFF_DEPTH + 10
    py, px = np.mgrid[0:H, 0:W]
    sx, sy = px - 16 + 0.5, py + 0.5
    s = 16 - sx if face == "se" else sx + 16      # planes u = 16 and v = 16
    shade = -0.8 if face == "se" else 0.0
    depth = sy - (16 + s) / 2
    flat = np.zeros_like(s)
    on = (s >= 0) & (s < 16) & (depth > 0)
    bottom = CLIFF_DEPTH - 7 * _pnoise(s, flat, 4, 700) - 4 * _pnoise(s, flat, 8, 701)
    on &= depth < bottom
    # Bands: topsoil, clay with a wavy stratum line, then rocky subsoil darkening downward.
    wave = (_pnoise(s, flat, 2, 710) - 0.5) * 3
    clay_top, rock_top = 7 + wave, 17 + wave * 1.3
    level = np.where(depth < clay_top, 2.2, np.where(depth < rock_top, 3.0, 2.2))
    level = level - np.clip((depth - rock_top) / 14, 0, 1) * 1.2 + shade
    rough = hash01(np.floor(s * 2).astype(np.int64) % 32, np.floor(depth).astype(np.int64), 711)
    level = level + (rough - 0.5) * 0.8
    level = level - (np.abs(depth - clay_top) < 0.7) * 1.0 - (np.abs(depth - rock_top) < 0.7) * 0.8
    level = level - (bottom - depth < 1.6) * 1.2                     # dark underside lip
    rgb = _paint(SOIL, level, px, py)
    # Embedded stones, mostly in the lower layers, with a lit top edge.
    from voxel import Rng
    rng = Rng(720)
    for cd in (10, 15.5, 21):
        cs, cd = rng.uniform(0, 16), cd + rng.uniform(-2, 2)
        rx, ry = rng.uniform(2.2, 3.4), rng.uniform(1.5, 2.3)
        for wrap in (-16, 0, 16):
            d = ((s - cs - wrap) / rx) ** 2 + ((depth - cd) / ry) ** 2
            stone = (d < 1) & (depth < bottom - 2)
            lvl = 2.2 + shade + (depth < cd - ry * 0.4) * 1.3 - (depth > cd + ry * 0.5) * 0.9
            rgb = np.where(stone[..., None], _paint(ROCK, lvl, px, py), rgb)
    # Roots dangling from the turf.
    root = np.zeros(s.shape, bool)
    for k in range(3):
        rs = rng.uniform(0, 16)
        length = rng.uniform(4, 11)
        for wrap in (-16, 0, 16):
            path_s = rs + wrap + 1.0 * np.sin(depth * 0.6 + k * 2)
            root |= (np.abs(s - path_s) < 0.5) & (depth > 2) & (depth < 2 + length)
    rgb = np.where(root[..., None], _rgb(EARTH[0]), rgb)
    # Grass lip with blades hanging over the edge.
    col = np.floor(s).astype(np.int64) % 16
    blade = 2.0 + 1.5 * (hash01(col, 740) > 0.55) + 1.0 * (hash01(col, 741) > 0.8)
    lip = depth < blade
    lip_level = 3.0 + shade * 0.8 - depth * 0.45
    rgb = np.where(lip[..., None], _paint(GRASS, lip_level, px, py), rgb)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = on * 255
    return Sprite(rgba, 16, 0)


# ---------- placement cursor ----------

def cursor(ok: bool) -> Sprite:
    px, py, u, v, inside = _grid()
    pad = np.pad(inside, 1)
    border = inside & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    line = _rgb(PLASTER[4]) if ok else _rgb(POPPY[1])
    fill = _rgb(LEAF[6]) if ok else _rgb(ROOF[2])
    rgb = np.where(border[..., None], line, fill)
    alpha = np.where(border, 230, np.where(inside, 72, 0))
    return _sprite(rgb, alpha)


def build(cat: dict, water_frames: int) -> dict[str, Sprite]:
    out = {}
    builders = {"meadow": meadow, "path": path, "cobble": cobble}
    for t in cat["terrain"]:
        tid = t["id"]
        if t.get("base"):
            for n in range(t["variants"]):
                out[f"terrain/{tid}/v{n}"] = grass(n)
        elif tid == "water":
            for m in range(16):
                for fr in range(water_frames):
                    out[f"terrain/water/m{m}/f{fr}"] = water(m, fr, water_frames)
        else:
            for m in range(16):
                out[f"terrain/{tid}/m{m}/f0"] = builders[tid](m)
    out["edge/cliff_se"] = cliff("se")
    out["edge/cliff_sw"] = cliff("sw")
    out["ui/tile_ok"] = cursor(True)
    out["ui/tile_bad"] = cursor(False)
    return out
