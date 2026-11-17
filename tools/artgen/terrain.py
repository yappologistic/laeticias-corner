"""Ground tiles, cliff faces and cursor diamonds, evaluated per pixel on the tile plane.

Each pixel centre of a tile maps to one point (u, v) of the tile square [0, 16)^2 (u along +x,
v along +y). Textures are functions of (u, v) that repeat every 16 voxels, so any arrangement of
tiles is seamless. Overlay shapes depend on the 4-bit mask only through each edge's own state:
an open edge (same terrain beyond) is fully covered and every inset tapers to zero at a corner
next to an open edge, so neighbouring tiles always agree along their shared edge.
"""

import numpy as np

from pack import Sprite
from palette import EARTH, INK, LEAF, PLASTER, POPPY, ROOF, STONE, STRAW, VIOLET, WATER, _rgb
from render import dither
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
    `interior` = (lo, hi) set, only points in [lo, 16 - hi) along both axes are kept, so
    variant-specific marks (which grow up the screen, towards low u and v) never cross into a
    neighbour that might be a different variant. `density` is a number or a function of the
    point's (u, v), so marks can gather into clumps.
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
            pu = (iu + 0.5 + (hash01(ku, kv, seed, 2) - 0.5) * jitter) * cell
            pv = (iv + 0.5 + (hash01(ku, kv, seed, 3) - 0.5) * jitter) * cell
            dens = density(pu % 16, pv % 16) if callable(density) else density
            keep = hash01(ku, kv, seed, 1) < dens
            if interior is not None:
                lo, hi = interior
                keep &= (pu >= lo) & (pu < 16 - hi) & (pv >= lo) & (pv < 16 - hi)
            dx = (u - pu) - (v - pv)
            dy = ((u - pu) + (v - pv)) / 2
            d = dx * dx + 4 * dy * dy
            better = keep & (d < best)
            best = np.where(better, d, best)
            bdx = np.where(better, dx, bdx)
            bdy = np.where(better, dy, bdy)
            bh = np.where(better, hash01(ku, kv, seed, 4), bh)
    return bdx, bdy, bh, best < 1e8


# Hand-drawn marks: rows top to bottom, the bottom row's middle pixel sits on the scattered
# point. Each character is a ramp step relative to the ground under it; '.' leaves it alone.
STEP = {"H": 2.0, "L": 1.0, "D": -1.0, "K": -1.6}


def _stamps(level, u, v, seed, density, kinds, cell=4, interior=(3.0, 1.0)):
    """Scatter `kinds` of marks (each also drawn mirrored) over the tile."""
    kinds = list(kinds) + [tuple(row[::-1] for row in k) for k in kinds]
    dx, dy, h, ok = _scatter(u, v, cell, seed, density, interior=interior)
    rx, ry = np.floor(dx + 0.5), np.floor(dy + 0.5)
    pick = np.minimum((h * len(kinds)).astype(np.int64), len(kinds) - 1)
    out = level.copy()
    for i, rows in enumerate(kinds):
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != ".":
                    hit = ok & (pick == i) & (ry == r - len(rows) + 1) & (rx == c - len(row) // 2)
                    out = np.where(hit, level + STEP[ch], out)
    return out


# ---------- grass ----------

GRASS_LEVEL = 2.0
TUFTS = (("H.L", ".LL", "DKD"), ("L..", "LH.", "DLD"), (".H.", "LLD", ".D."))
BLADES = (("H",  "L"), ("H.", ".L"), ("L.H", "L.L"))
SHADE_BLADES = (("D", "K"), ("D.", ".D"), ("D.D", "K.D"))
SPECKS = ((".L.", "LDL"), ("K",), ("D.K",))
# Per variant: densities of tufts and specks, a clump of light blades and a clump of shadowy
# blades (peak density, 0 for none), and a sparse sprinkle of single pixels one step lighter
# (+) or darker (-) over the whole tile. Variants are picked at random per tile, so sprinkles
# and clumps add up to irregular, gentle patches across a field.
GRASS_VARIANTS = (
    (0.2, 0.08, 0.0, 0.0, 0.0),
    (0.12, 0.0, 0.45, 0.0, 0.07),
    (0.1, 0.1, 0.0, 0.32, -0.06),
    (0.16, 0.04, 0.25, 0.0, 0.03),
)


def _clump(seed, peak):
    """Density field for marks gathering in one soft blob inside the tile."""
    cu, cv = 5 + 6 * float(hash01(seed, 1)), 5 + 6 * float(hash01(seed, 2))
    return lambda u, v: peak * np.clip(1 - np.hypot(u - cu, v - cv) / 5.5, 0, 1) + 0.03 * peak


def grass(variant: int) -> Sprite:
    px, py, u, v, inside = _grid()
    tufts, specks, light, shade, sprinkle = GRASS_VARIANTS[variant]
    seed = 30 + variant * 10
    grain = hash01(px, py, seed + 5) < abs(sprinkle)
    level = GRASS_LEVEL + np.sign(sprinkle) * grain
    level = _stamps(level, u, v, seed, tufts, TUFTS)
    level = _stamps(level, u, v, seed + 2, specks, SPECKS, cell=4)
    if light:
        level = _stamps(level, u, v, seed + 3, _clump(seed + 3, light), BLADES, cell=2,
                        interior=(2.0, 1.0))
    if shade:
        level = _stamps(level, u, v, seed + 4, _clump(seed + 4, shade), SHADE_BLADES, cell=2,
                        interior=(2.0, 1.0))
    return _sprite(_paint(GRASS, level, px, py), inside * 255)


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

FLOWER_COLORS = [PLASTER[4], STRAW[3], STRAW[2], PLASTER[3], VIOLET[3], STRAW[3], POPPY[1], PLASTER[4]]
MEADOW_TUFTS = (("H..", "L.H", "LLL", "DLD"), (".H.", "HL.", "LLL", ".D."), ("L.H", "L.L", "DLD"))


def meadow(mask: int) -> Sprite:
    px, py, u, v, inside = _grid()
    f = shape_field(mask, u, v, 1.4, 5.5, 0.9, 300)
    # Soft border: dither the last voxel so meadow frays into the grass.
    edge_noise = hash01(np.floor(u * 2).astype(np.int64), np.floor(v * 2).astype(np.int64), 301)
    cover = inside & (f > 0.6 * edge_noise)
    level = 2.0 + (_pnoise(u, v, 2, 310) - 0.5) * 0.6
    # Taller, lighter growth than lawn grass. The meadow has no per-tile variants, so marks may
    # cross into the next meadow tile (the pattern repeats exactly) and stay irregular inside.
    level = _stamps(level, u, v, 311, 0.2, MEADOW_TUFTS, cell=2, interior=None)
    level = _stamps(level, u, v, 312, 0.12, BLADES, cell=2, interior=None)
    rgb = _paint(MEADOW, level, px, py)
    # Wildflowers dense enough to read as a texture: every meadow tile is the same sprite, so
    # sparse bright dots would line up into rows across a large patch.
    dx, dy, h, ok = _scatter(u, v, 2, 320, 0.3, jitter=0.95)
    rx, ry = np.floor(dx + 0.5), np.floor(dy + 0.5)
    head = ok & (rx == 0) & (ry == -1)
    stem = ok & (rx == 0) & (ry == 0)
    colors = np.array([_rgb(c) for c in FLOWER_COLORS], np.uint8)
    pick = colors[np.minimum((h * len(FLOWER_COLORS)).astype(np.int64), len(FLOWER_COLORS) - 1)]
    # Keep flowers off the frayed rim so they never float on plain grass.
    rgb = np.where((stem & (f > 1.5))[..., None], _rgb(LEAF[2]), rgb)
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
    dx, dy, h, ok = _scatter(u, v, 2, 420, 0.2)
    rx, ry = np.round(dx - 0.5), np.round(dy - 0.5)
    big = h > 0.7
    top = ok & (ry == 0) & ((rx == 0) | (big & (rx == -1)))
    bottom = ok & (ry == 1) & ((rx == 0) | (big & (rx == -1)))
    level = level + top * 1.3 - bottom * 1.2
    # Worn rim: darker earth just inside the border, with a lighter crest before it.
    level = level - np.clip(1.4 - f, 0, 1) * 1.6 + ((f > 1.4) & (f < 2.2)) * 0.5
    rgb = _paint(PATH, level, px, py)
    return _sprite(rgb, cover * 255)


# ---------- cobble ----------

# Each cobble picks one ramp: three parts warm grey, two cool grey, one sandstone.
WARM_GREY = [STONE[1], STONE[2], PLASTER[1], STONE[4], PLASTER[2]]
COOL_GREY = [STONE[0], STONE[1], STONE[2], STONE[3], STONE[4]]
SANDSTONE = [EARTH[1], EARTH[2], EARTH[3], EARTH[4], EARTH[5]]
COBBLE_RAMPS = (WARM_GREY,) * 3 + (COOL_GREY,) * 2 + (SANDSTONE,)
MORTAR = [INK, EARTH[0], EARTH[1]]


def _cells(u, v, cell, seed, jitter=0.8):
    """Tile-periodic Voronoi cells: distance to the nearest and second nearest centre, the
    offset (du, dv) from the nearest centre and its hash."""
    n = int(16 // cell)
    f1 = np.full(u.shape, 1e9, np.float32)
    f2 = np.full(u.shape, 1e9, np.float32)
    bdu, bdv, bh = (np.zeros(u.shape, np.float32) for _ in range(3))
    cu, cv = np.floor(u / cell).astype(np.int64), np.floor(v / cell).astype(np.int64)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            iu, iv = cu + du, cv + dv
            ku, kv = iu % n, iv % n
            ou = u - (iu + 0.5 + (hash01(ku, kv, seed, 2) - 0.5) * jitter) * cell
            ov = v - (iv + 0.5 + (hash01(ku, kv, seed, 3) - 0.5) * jitter) * cell
            d = np.hypot(ou, ov)
            nearer = d < f1
            f2 = np.where(nearer, f1, np.minimum(f2, d))
            f1 = np.where(nearer, d, f1)
            bdu = np.where(nearer, ou, bdu)
            bdv = np.where(nearer, ov, bdv)
            bh = np.where(nearer, hash01(ku, kv, seed, 4), bh)
    return f1, f2, bdu, bdv, bh


def cobble(mask: int) -> Sprite:
    px, py, u, v, inside = _grid()
    f = shape_field(mask, u, v, 1.2, 4.0, 0.4, 500)
    cover = inside & (f > 0)
    f1, f2, du, dv, h = _cells(u, v, 4.0, 510)
    mortar = (f2 - f1) < 0.5
    # Each stone: lit on its sun side (-u, +v), shaded on the far side, a few lighter flecks.
    side = (-du * 0.45 + dv * 0.28) / np.maximum(f1, 1e-3)
    rim = np.clip((f1 - 0.6) / 1.4, 0, 1)
    level = 2.3 + (h * 13 % 1 - 0.5) * 0.5 + side * rim * 1.3
    level = level - np.clip(1.2 - f, 0, 1) * 1.2
    ramp = np.minimum((h * len(COBBLE_RAMPS)).astype(np.int64), len(COBBLE_RAMPS) - 1)
    rgb = np.zeros(u.shape + (3,), np.uint8)
    for i, colors in enumerate(COBBLE_RAMPS):
        rgb = np.where((ramp == i)[..., None], _paint(colors, level, px, py, band=0.4), rgb)
    joint = 1.0 - np.clip(1.2 - f, 0, 1)
    rgb = np.where(mortar[..., None], _paint(MORTAR, joint, px, py), rgb)
    # Moss creeping into a few joints.
    moss = mortar & (_pnoise(u, v, 4, 520) > 0.68)
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

CLIFF_DEPTH = 35
SOIL = [INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3], EARTH[4]]
ROCK = [INK, STONE[0], STONE[1], STONE[2], STONE[3], STONE[4]]
# The face repeats every tile along the rim, so everything is placed by hand on one period
# with uneven spacing and sizes, and built from a few smooth harmonics instead of noise teeth.
# Underside: (harmonic, amplitude, phase) lifting the bottom, and hanging drips (s, length, width).
CLIFF_UNDERSIDE = ((1, 1.6, 0.7), (2, 0.9, 2.3), (3, 0.5, 4.1))
CLIFF_DRIPS = ((3.4, 2.2, 2.6), (9.2, 1.2, 1.4), (13.1, 1.8, 1.8))
# Strata lines: (mean depth, (harmonic, amplitude, phase) ...).
CLIFF_STRATA = ((8.0, ((1, 1.6, 0.4), (2, 0.6, 1.9))), (17.0, ((1, 2.0, 2.2), (3, 0.5, 0.3))))
# Embedded stones: (s, depth, rx, ry).
CLIFF_STONES = ((12.3, 20.5, 3.1, 2.1), (3.0, 12.5, 1.5, 1.0), (7.0, 25.5, 1.1, 0.8))
# Roots dangling from the turf: (s, length, wiggle phase).
CLIFF_ROOTS = ((5.0, 9.0, 0.0), (13.7, 14.0, 4.0))
# Grass tufts hanging over the lip: (s, length, half-width).
CLIFF_TUFTS = ((1.6, 3.0, 1.6), (7.9, 4.5, 1.2), (12.4, 2.0, 2.2))


def _wave(s, terms):
    return sum(a * np.sin(2 * np.pi * k * s / 16 + p) for k, a, p in terms)


def _wrapped(s, s0):
    """Signed distance along the rim from s to s0, taking the shorter way round the period."""
    return (s - s0 + 8) % 16 - 8


def cliff(face: str) -> Sprite:
    """The earth face under one rim tile: 'se' is the +x face, 'sw' the +y face (sun side).

    Everything is a function of (s, depth) with s the position along the rim, repeating every
    tile, so the faces join seamlessly along the whole rim and at the bottom corner."""
    W, H = TW, 8 + CLIFF_DEPTH + 10
    py, px = np.mgrid[0:H, 0:W]
    sx, sy = px - 16 + 0.5, py + 0.5
    s = 16 - sx if face == "se" else sx + 16      # planes u = 16 and v = 16
    shade = -0.9 if face == "se" else 0.0
    # Depth in whole pixels below each column's first face pixel: measured from the exact rim
    # line it would step by half a pixel per column and every band would turn into teeth.
    first_row = np.floor((16 + s) / 2 - 0.5) + 1
    depth = py - first_row + 0.5
    on = (s >= 0) & (s < 16) & (depth > 0)
    # A ragged, tapering underside: smooth lumps plus a few hanging drips.
    bottom = CLIFF_DEPTH - 3.0 - _wave(s, CLIFF_UNDERSIDE)
    for s0, length, width in CLIFF_DRIPS:
        bottom = bottom + length * np.clip(1 - np.abs(_wrapped(s, s0)) / width, 0, 1) ** 1.5
    on &= depth < bottom
    # Bands: dark topsoil, a lighter clay band, then stony subsoil darkening downward.
    (d1, w1), (d2, w2) = CLIFF_STRATA
    line1, line2 = d1 + _wave(s, w1), d2 + _wave(s, w2)
    level = np.where(depth < line1, 2.2, np.where(depth < line2, 3.2, 2.4))
    level = level - np.clip((depth - line2) / 12, 0, 1) * 1.0 + shade
    # Streaky grain along the strata (short horizontal dashes, not per-pixel static).
    grain = hash01(np.floor(s * 0.6).astype(np.int64) % 10, np.floor(depth).astype(np.int64), 711)
    level = level + (grain > 0.82) * (depth > line1 + 1) * 0.7 - (grain < 0.12) * 0.7
    level = level - (np.abs(depth - line1) < 0.6) * 1.1 - (np.abs(depth - line2) < 0.6) * 0.9
    level = level - (bottom - depth < 1.8) * 1.3                       # dark underside lip
    # The turf overhangs: an even band of shadow just under the grass (no ink speckles).
    lip = 2.8 + _wave(s, ((2, 0.6, 1.0), (5, 0.4, 3.0)))
    under_turf = (depth > lip) & (depth < lip + 2.0)
    level = np.where(under_turf, 1.2 + shade * 0.3, level)
    rgb = _paint(SOIL, level, px, py)
    # Stones of different sizes, each with a lit top, a dark base and a dark seam around it.
    for cs, cd, rx, ry in CLIFF_STONES:
        d = (_wrapped(s, cs) / rx) ** 2 + ((depth - cd) / ry) ** 2
        seam = (d < 1.45) & (d >= 1) & (depth < bottom - 1)
        rgb = np.where(seam[..., None], _paint(SOIL, level - 1.0, px, py), rgb)
        stone = (d < 1) & (depth < bottom - 1)
        lvl = 2.5 + shade + (depth < cd - ry * 0.35) * 1.2 - (depth > cd + ry * 0.4) * 0.9
        lvl = lvl + (_wrapped(s, cs) < -rx * 0.4) * (0.6 if face == "sw" else -0.3)
        rgb = np.where(stone[..., None], _paint(ROCK, lvl, px, py), rgb)
    # Thin pale roots curling down from the turf.
    for rs, length, ph in CLIFF_ROOTS:
        path_s = rs + 1.4 * np.sin(depth * 0.7 + ph) * np.clip(depth / 5, 0, 1)
        body = (depth > lip) & (depth < lip + length) & (depth < bottom - 1)
        root = body & (np.abs(_wrapped(s, path_s)) < 0.5)
        rgb = np.where(root[..., None], _paint(SOIL, np.full_like(level, 4.6 + shade), px, py), rgb)
    # Grass lip with a few tufts hanging over the edge.
    hang = np.zeros_like(s)
    for ts, length, half in CLIFF_TUFTS:
        hang = np.maximum(hang, length * np.clip(1 - np.abs(_wrapped(s, ts)) / half, 0, 1) ** 0.7)
    turf = depth < lip + hang
    turf_level = np.where(depth > lip, 3.3 - (depth - lip) * 0.25, 3.4 - depth * 0.3) + shade * 0.7
    rgb = np.where(turf[..., None], _paint(GRASS, turf_level, px, py), rgb)
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
