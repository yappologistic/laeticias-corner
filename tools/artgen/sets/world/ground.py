"""The world's ground (docs/design/sets/world.md §1), evaluated per pixel like terrain.py: three
bases (sand, steppe, river silt) with eight looks each, the overlays of every biome, the sea in
depth with its swell, shallows over rippled sand, shore foam, rivers with their flow, and the
edge faces that stack under raised ground (limestone, earth, snow, sea cliff, basalt).

Base looks share one gentle tile-periodic ground and differ only in marks kept inside the
tile, so any mix of looks meets without a seam; two looks are greener or stonier in the middle,
so a field of mixed looks breaks into soft patches instead of repeating one tile."""

import math

import numpy as np

import terrain as home
from pack import Sprite
from palette import (ATTIC_ROCK, BASALT, CLAY, EARTH, HAZE, INK, LEAF, LIMESTONE, MARBLE, OLIVE, PINE, PLASTER,
                     POPPY, RUST, SAND, SEA, SHALLOW, SNOW, STEPPE, STONE, STRAW, SUMMER, TIBER, TUFA, VIOLET,
                     WATER, _rgb)
from sets.parsa.ground import _face_grid, _periodic
from voxel import hash01, value_noise

N_BIT, E_BIT, S_BIT, W_BIT = 1, 2, 4, 8
FRAMES_WATER = 4
FLOW_FRAMES = 8

SANDS = SAND
STEPPE_GRASS = [EARTH[1], STEPPE[0], STEPPE[1], STEPPE[2], STEPPE[3], STEPPE[4]]
STEPPE_EARTH = [EARTH[1], EARTH[2], SAND[0], SAND[1], SAND[2]]
SILT = [TUFA[1], TUFA[2], EARTH[2], TUFA[3], TUFA[4], SAND[2]]
GREEN = [PINE[0], LEAF[1], OLIVE[1], LEAF[2], OLIVE[2], LEAF[3]]
LIME_ROCK = [INK, STONE[1], ATTIC_ROCK[1], ATTIC_ROCK[2], ATTIC_ROCK[3], ATTIC_ROCK[4], ATTIC_ROCK[5]]
PALE_ROCK = [STONE[1], ATTIC_ROCK[2], LIMESTONE[3], ATTIC_ROCK[4], LIMESTONE[5], MARBLE[5]]
SNOWS = [STONE[3], SNOW[0], SNOW[1], SNOW[2], PLASTER[4]]
MUD = [INK, PINE[0], OLIVE[0], TUFA[1], OLIVE[1], TIBER[1]]
RIVER = [WATER[0], WATER[1], WATER[2], WATER[3], WATER[4], WATER[5]]
SHALLOWS = [SEA[4], SHALLOW[0], SHALLOW[1], SHALLOW[2], SHALLOW[3], SHALLOW[4]]
BANK = [INK, EARTH[0], EARTH[1], EARTH[2], SAND[1]]
ROAD = [EARTH[0], EARTH[1], EARTH[2], CLAY[1], EARTH[3], SAND[2], SAND[3]]
GRAVEL = [EARTH[1], SAND[0], SAND[1], STONE[3], SAND[2], SAND[3], SAND[4], SAND[5]]
FURROW = [INK, EARTH[0], EARTH[1], CLAY[0], EARTH[2], CLAY[1], EARTH[3]]
SCRUB = [PINE[0], OLIVE[0], OLIVE[1], LEAF[2], OLIVE[2], OLIVE[3]]
LITTER = [INK, EARTH[0], PINE[0], EARTH[1], RUST[0], OLIVE[1], CLAY[1]]
VARNISH = [INK, EARTH[0], STONE[0], RUST[0], EARTH[1], STONE[1]]
SALT = [STONE[3], SAND[3], SNOW[1], PLASTER[3], SNOW[2], PLASTER[4]]
LUSH = [LEAF[1], LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]]
FALLOW = [EARTH[1], SUMMER[0], OLIVE[1], SUMMER[1], STRAW[1], SUMMER[2]]


# ---------------------------------------------------------------- helpers

class _G:
    """A tile grid with shifted plane coordinates (for animation and flow)."""

    def __init__(self, g, du=0.0, dv=0.0):
        self.k, self.px, self.py, self.inside = g.k, g.px, g.py, g.inside
        self.u, self.v = g.u + du, g.v + dv
        self.fine = g.k >= 2


def _window(g, lo=2.5):
    """1 inside the tile, easing to 0 within `lo` units of every edge: variant-only marks and
    tone shifts fade out before an edge, so neighbouring looks always agree there."""
    a = np.clip(np.minimum(g.u, 16 - g.u) / lo, 0, 1)
    b = np.clip(np.minimum(g.v, 16 - g.v) / lo, 0, 1)
    return (a * b) ** 0.8


def _voronoi(g, cell, seed, jitter=0.85):
    """Tile-periodic Voronoi on the plane: distance to the nearest and second centre (units),
    the nearest centre's hash and its offset (du, dv)."""
    n = int(16 // cell)
    cu, cv = np.floor(g.u / cell).astype(np.int64), np.floor(g.v / cell).astype(np.int64)
    d1 = np.full(g.u.shape, 1e9, np.float32)
    d2 = np.full(g.u.shape, 1e9, np.float32)
    hh = np.zeros(g.u.shape, np.float32)
    ou = np.zeros(g.u.shape, np.float32)
    ov = np.zeros(g.u.shape, np.float32)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            iu, iv = cu + du, cv + dv
            ku, kv = iu % n, iv % n
            pu = (iu + 0.5 + (hash01(ku, kv, seed, 2) - 0.5) * jitter) * cell
            pv = (iv + 0.5 + (hash01(ku, kv, seed, 3) - 0.5) * jitter) * cell
            d = np.hypot(g.u - pu, g.v - pv)
            closer = d < d1
            d2 = np.where(closer, d1, np.minimum(d2, d))
            hh = np.where(closer, hash01(ku, kv, seed, 4), hh)
            ou = np.where(closer, g.u - pu, ou)
            ov = np.where(closer, g.v - pv, ov)
            d1 = np.where(closer, d, d1)
    return d1, d2, hh, ou, ov


def _marks(g, level, seed, density, rows_list, cell=4, interior=None):
    return home._stamps(g, level, seed, density, rows_list, cell=cell, interior=interior)


# Interior looks of the commonest overlays (`terrain/<id>/m15/v<n>/f<k>`, v0 being the plain
# `m15` key): the same ground with its pattern shifted inside the tile and the edge band left
# as it is, so any look meets any neighbour without a seam and a field of mixed looks loses the
# one-tile rhythm (the engine picks a look by tile hash, as it does for base variants).
INTERIOR = {"world.sea": 6, "world.scrub": 4, "world.pasture": 4, "world.rock": 4, "world.forest_floor": 3}
SHIFTS = ((0.0, 0.0), (5.3, 9.1), (10.7, 3.9), (3.1, 12.6), (12.2, 6.8), (7.7, 14.3))


def _interior(g, rgb, paint_shifted, var, seed):
    """Mix a look shifted by SHIFTS[var] into the tile's interior, fading to the plain look in a
    band along every edge (dithered, so the change has no line)."""
    if not var:
        return rgb
    alt = paint_shifted(_G(g, *SHIFTS[var]))
    pick = _window(g, 4.5) > hash01(g.px, g.py, seed + 31 * var)
    return np.where(pick[..., None], alt, rgb)


def _overlay(mask, k, inset, radius, wobble, seed, paint, fray=0.9, var=0):
    """An overlay tile: the shape field of the mask, painted, its rim frayed a little on fine
    grids so overlays meet bases with a natural ragged edge. `var` > 0: an interior look."""
    g = home._grid(k)
    f = home.shape_field(mask, g.u, g.v, inset, radius, wobble, seed, k)
    if g.fine and fray:
        cover = g.inside & (f > fray * hash01(g.px, g.py, seed + 7))
    else:
        cover = g.inside & (f > 0)
    rgb = _interior(g, paint(g, f), lambda gs: paint(gs, f), var, seed)
    return home._sprite(g, rgb, cover * 255)


def _paint(ramp, level, g, band=0.55):
    return home._paint(ramp, level, g.px, g.py, band=band, k=g.k)


TUFTS = (("H.L", ".LL", "DKD"), ("L..", "LH.", "DLD"), (".H.", "LLD", ".D."), ("H.H", "LLL", "DKD"))
TUFTS_FINE = (("H...L", ".L.L.", "L.LH.", ".LLL.", "DDKDD"), ("..H..", "L.L..", ".LL.H", ".LLL.", "D.K.D"),
              ("H..", ".L.", ".LH", "DKD"), (".H.H.", "L.L.L", ".LLL.", "DKDKD"))
STONES = ((".L.", "LDL"), ("HL", "DK"), (".H.", "LLD", ".K."))
SPECKS = (("K",), ("D.K",), ("L",))


def _tufts(g):
    return TUFTS_FINE if g.fine else TUFTS


# ---------------------------------------------------------------- bases (eight looks each)

def steppe(v, k):
    """Pale gold dry grass in tussocks over buff earth, stony flecks. Looks 0-4 differ in where
    their tussocks and stones fall; 5 is greener in the middle, 6 stonier, 7 has a bare patch."""
    g = home._grid(k)
    w = _window(g)
    n = home._pnoise(g.u, g.v, 2, 9101)
    fine = home._pnoise(g.u, g.v, 8, 9102)
    lvl = 2.5 + (n - 0.5) * 0.7 + (fine - 0.5) * 0.6 + (hash01(g.px, g.py, 9103) - 0.5) * 0.7
    earth = (fine < 0.32) & (hash01(g.px // 2, g.py, 9104) < 0.7)
    seed = 9110 + v * 13
    tuft_d = (0.55, 0.45, 0.6, 0.5, 0.4, 0.55, 0.3, 0.25)[v]
    lvl = _marks(g, lvl, seed, tuft_d, _tufts(g), cell=4 if not g.fine else 2, interior=(2.0, 1.0))
    lvl = _marks(g, lvl, seed + 1, 0.35, _tufts(g), cell=4, interior=(2.5, 1.0))
    rgb = _paint(STEPPE_GRASS, lvl, g)
    rgb = np.where(earth[..., None], _paint(STEPPE_EARTH, lvl - 0.3, g), rgb)
    if v == 5:      # greener: spring growth in a damp hollow
        green = (home._pnoise(g.u, g.v, 4, seed + 2) * w > 0.35) & (hash01(g.px, g.py, seed + 3) < 0.75)
        rgb = np.where(green[..., None], _paint(GREEN, lvl - 0.6, g), rgb)
    if v == 7:      # a bare scuffed patch where flocks lie up
        bare = (w * (1 - np.hypot(g.u - 8.5, (g.v - 8) * 1.3) / 6.0)) > 0.25
        rgb = np.where(bare[..., None], _paint(STEPPE_EARTH, 2.4 + (fine - 0.5) * 1.2, g), rgb)
    stone_d = (0.12, 0.18, 0.1, 0.15, 0.2, 0.08, 0.45, 0.2)[v]
    slvl = _marks(g, np.full_like(lvl, 2.0), seed + 4, stone_d, STONES, cell=4, interior=(2.0, 1.5))
    stone = slvl != 2.0
    rgb = np.where(stone[..., None], _paint(PALE_ROCK, slvl + 0.6, g), rgb)
    return home._sprite(g, rgb, g.inside * 255)


def sand(v, k):
    """Warm pale sand: wind ripples on looks 1, 2 and 5, shell and pebble flecks, a darker
    damp patch on 6, a strand line of drift on 7."""
    g = home._grid(k)
    w = _window(g)
    n = home._pnoise(g.u, g.v, 2, 9201)
    fine = home._pnoise(g.u, g.v, 8, 9202)
    lvl = 3.2 + (n - 0.5) * 0.6 + (fine - 0.5) * 0.4 + (hash01(g.px, g.py, 9203) - 0.5) * 0.6
    if v in (1, 2, 5):
        ang = (0.8, -0.5, 1.4)[(1, 2, 5).index(v)]
        r = np.sin((g.u * math.cos(ang) + g.v * math.sin(ang)) * 1.6 + (fine - 0.5) * 4.0)
        lvl = lvl + (r > 0.75) * 0.9 * w - ((r < -0.2) & (r > -0.6)) * 0.6 * w
    if v == 6:
        damp = home._pnoise(g.u, g.v, 4, 9204) * w > 0.38
        lvl = np.where(damp, lvl - 1.1, lvl)
    rgb = _paint(SANDS, lvl, g)
    seed = 9210 + v * 13
    dx, dy, h, ok = home._scatter(g, 2, seed, 0.12, interior=(1.5, 1.0))
    shell = ok & (dx * dx + 4 * dy * dy < (0.5 + h) ** 2 * k)
    rgb = np.where((shell & (h > 0.5))[..., None], _rgb(PLASTER[4]), rgb)
    rgb = np.where((shell & (h <= 0.5))[..., None], _paint([STONE[1], STONE[2], STONE[3]], 1.0 + h * 2 - dy / k, g), rgb)
    if v == 7:
        line = (np.abs(g.u - g.v * 0.3 - 6.0) < 0.6 + (fine - 0.5)) & (w > 0.3) & (hash01(g.px, g.py, seed + 1) < 0.6)
        rgb = np.where(line[..., None], _paint([EARTH[0], EARTH[1], STRAW[0], OLIVE[1]], 1.5 + fine * 2, g), rgb)
    return home._sprite(g, rgb, g.inside * 255)


def alluvium(v, k):
    """Grey-brown river silt with green patches; dried mud cracks on look 3, a puddle-dark
    damp hollow on 6, sprouting weeds on 5 and 7."""
    g = home._grid(k)
    w = _window(g)
    n = home._pnoise(g.u, g.v, 2, 9301)
    fine = home._pnoise(g.u, g.v, 8, 9302)
    lvl = 2.8 + (n - 0.5) * 0.8 + (fine - 0.5) * 0.6 + (hash01(g.px, g.py, 9303) - 0.5) * 0.7
    rgb = _paint(SILT, lvl, g)
    seed = 9310 + v * 13
    green_d = (0.35, 0.5, 0.25, 0.1, 0.45, 0.6, 0.3, 0.55)[v]
    glvl = _marks(g, np.full_like(lvl, 2.0), seed, green_d, _tufts(g), cell=4 if not g.fine else 2,
                  interior=(2.0, 1.0))
    green = glvl != 2.0
    rgb = np.where(green[..., None], _paint(GREEN, glvl + 1.2, g), rgb)
    patch = home._pnoise(g.u, g.v, 4, seed + 1) * w
    if v in (1, 4, 5):
        moss = (patch > 0.42) & (hash01(g.px, g.py, seed + 2) < 0.6)
        rgb = np.where(moss[..., None], _paint(GREEN, 2.0 + fine, g), rgb)
    if v == 3:
        d1, d2, hh, _a, _b = _voronoi(g, 4, seed + 3)
        crack = (d2 - d1 < 0.35) & (w > 0.2)
        lift = (d2 - d1 > 0.35) & (d2 - d1 < 0.8)
        rgb = np.where(lift[..., None], _paint(SILT, lvl + 0.8, g), rgb)
        rgb = np.where(crack[..., None], _paint([INK, TUFA[0], TUFA[1]], lvl - 1.0, g), rgb)
    if v == 6:
        damp = patch > 0.4
        rgb = np.where(damp[..., None], _paint([TUFA[0], TUFA[1], TUFA[2], TIBER[1]], 1.6 + fine, g), rgb)
    return home._sprite(g, rgb, g.inside * 255)


BASES = {"world.sand": sand, "world.steppe": steppe, "world.alluvium": alluvium}


# ---------------------------------------------------------------- water

def _bank(mask, g, inset, radius, wobble, seed):
    field = lambda du: home.shape_field(mask, g.u - du, g.v - du, inset, radius, wobble, seed, g.k)
    return field(0), field(1) <= 0, field(2) <= 0, field(3) <= 0


def sea(mask, frame, k, var=0):
    """The open sea: deep blue under slow swells whose crests catch the light, a scatter of
    sparkles, a little lighter where it laps a shore. Frames loop (the swell moves a quarter
    tile a frame); the engine tints by depth. Nothing in it repeats at the tile's own size
    except the long crest lines, which run on across tiles; breaking crests and sparkles sit
    on finer lattices, and the interior looks shift them (INTERIOR)."""
    g0 = home._grid(k)
    f = home.shape_field(mask, g0.u, g0.v, 1.2, 5.0, 0.8, 9401, k)
    cover = g0.inside & (f > 0.7 * hash01(g0.px, g0.py, 9402)) if g0.fine else g0.inside & (f > 0)
    t = frame / FRAMES_WATER

    def paint(g):
        a = home._pnoise(g.u - 4 * frame, g.v, 4, 9403)
        b = home._pnoise(g.u, g.v + 4 * frame, 4, 9404)
        lvl = 2.2 + (a - 0.5) * 0.45 + (b - 0.5) * 0.45
        # Swell: long low crests running across tiles (two to a tile), bent by a fine warp,
        # moving one tile in 4 frames, lit only where a fine noise lets them break.
        warp = (home._pnoise(g.u, g.v, 8, 9405) - 0.5) * 4.0
        ph = 2 * np.pi * (2 * (g.u + 2 * g.v) / 16.0 + t) + warp
        crest = np.sin(ph)
        breaks = home._pnoise(g.u + 4 * frame, g.v, 8, 9408) > 0.6
        lvl = lvl + (crest > 0.94) * breaks * 0.7 - (crest < -0.9) * 0.2
        # Sparkles that wink on and off, on a fine lattice.
        dx, dy, h, ok = home._scatter(g, 2, 9406, 0.07, jitter=0.95)
        on = np.sin(2 * np.pi * (t + h)) > 0.7
        sp = ok & on & (np.abs(dy) < 0.5) & (np.abs(dx) < 1.0 + k * 0.5 * (h > 0.7))
        shore = np.clip(1.6 - f, 0, 1.6)
        rgb = _paint(SEA, lvl + shore * 0.7, g, band=0.35)
        return np.where(sp[..., None], _rgb(SHALLOW[4]), rgb)
    rgb = _interior(g0, paint(g0), paint, var, 9401)
    rgb = np.where(((f < 0.5) & cover)[..., None], _paint(SHALLOWS, 3.0 + hash01(g0.px, g0.py, 9407), g0), rgb)
    return home._sprite(g0, rgb, cover * 255)


def shallows(mask, frame, k):
    """Turquoise water over sand ripples that show through, sparkles, frames timed with the
    sea's. The rim is soft, so laid over sea it fades into deep water and over sand it reads
    as the wet edge of the beach."""
    g = home._grid(k)
    f = home.shape_field(mask, g.u, g.v, 1.0, 5.0, 0.8, 9501, k)
    soft = np.clip(f / 2.2, 0, 1)
    cover = g.inside & (soft > hash01(g.px, g.py, 9502) * 0.95)
    t = frame / FRAMES_WATER
    fine = home._pnoise(g.u, g.v, 8, 9503)
    rip = np.sin(2 * np.pi * (2 * g.u + 5 * g.v) / 16.0 + (fine - 0.5) * 3.0)
    lvl = 2.4 + (home._pnoise(g.u, g.v, 2, 9504) - 0.5) * 0.8 + (rip > 0.6) * 0.8 - (rip < -0.5) * 0.5
    # Caustic shimmer: a light net drifting with the frames.
    c1 = home._pnoise(g.u - 4 * frame, g.v, 4, 9505)
    c2 = home._pnoise(g.u, g.v - 4 * frame, 4, 9506)
    net = np.abs(c1 - c2) < 0.05
    lvl = lvl + net * 1.0
    dx, dy, h, ok = home._scatter(g, 4, 9507, 0.4, jitter=0.9)
    on = np.sin(2 * np.pi * (t + h)) > 0.5
    sp = ok & on & (np.abs(dy) < 0.5) & (np.abs(dx) < 0.6 + k * 0.5 * (h > 0.5))
    lvl = lvl + np.clip(1.5 - f, 0, 1.5) * 0.6
    rgb = _paint(SHALLOWS, lvl, g, band=0.35)
    rgb = np.where(sp[..., None], _rgb(PLASTER[4]), rgb)
    return home._sprite(g, rgb, cover * 255)


def river(mask, frame, k):
    """Green-blue river water sunk a little below its banks: darker in the middle, silty and
    lighter at the edges, an earth bank showing under the upper shore, a shimmer where it
    meets the bank. Reads at one tile wide (canals)."""
    g = home._grid(k)
    f, wall1, wall2, shade = _bank(mask, g, 1.6, 5.0, 0.7, 9601)
    cover = g.inside & (f > 0)
    t = frame / FRAMES_WATER
    depth = np.clip(f / 5.0, 0, 1)
    lvl = 3.3 - depth * 1.8 + (home._pnoise(g.u, g.v, 2, 9602) - 0.5) * 0.5 - shade * 0.9
    dx, dy, h, ok = home._scatter(g, 4, 9603, 0.4, jitter=0.9)
    half = 2.5 * (0.5 + 0.5 * np.sin(2 * np.pi * (t + h))) - 0.5
    rx, ry = np.round(dx - 0.5), np.round(dy - 0.5)
    glint = ok & (ry == 0) & (np.abs(rx + 0.5) < half) & (f > 1.2)
    lvl = lvl + glint * 1.4
    rgb = _paint(RIVER, lvl, g, band=0.35)
    silt = (f < 1.4) & (f > 0.4) & (hash01(g.px, g.py, 9604) < 0.5)
    rgb = np.where(silt[..., None], _paint([TIBER[2], TIBER[3], SHALLOW[2]], 1.0 + f, g), rgb)
    lip = f < 0.5
    rgb = np.where((lip & ~wall2)[..., None], _rgb(SHALLOW[3]), rgb)
    wall_level = np.where(wall1, 3.0, 1.8) - (home._pnoise(g.u, g.v, 8, 9605) - 0.5) * 0.8
    rgb = np.where((wall2 | lip & (f < 0.25))[..., None], _paint(BANK, wall_level, g), rgb)
    return home._sprite(g, rgb, cover * 255)


def foam(mask, frame, k):
    """Surf on a sea tile along every edge that faces land (mask = land neighbours): a bright
    line where the wave breaks, running up and drawing back over 4 frames, a second fainter
    line behind it and foam dissolving outward. Lines run the full edge so straight coasts
    join from tile to tile."""
    g = home._grid(k)
    t = frame / FRAMES_WATER
    alpha = np.zeros(g.u.shape, np.float32)
    level = np.zeros(g.u.shape, np.float32)
    edges = [(N_BIT, g.v, g.u), (S_BIT, 16 - g.v, g.u), (W_BIT, g.u, g.v), (E_BIT, 16 - g.u, g.v)]
    for bit, d, s in edges:
        if not mask & bit:
            continue
        wob = home._pnoise(s, s * 0, 4, 9701 + bit) - 0.5
        per = home._pnoise(s, s * 0, 4, 9702 + bit)
        reach = 0.7 + 0.9 * (0.5 + 0.5 * math.sin(2 * math.pi * t)) + wob * 0.8
        line = np.abs(d - reach) < 0.45 + 0.25 * per
        back = np.abs(d - (reach + 2.2 + 0.6 * math.sin(2 * math.pi * (t + 0.35)))) < 0.3
        back &= home._pnoise(s + 8 * frame / FRAMES_WATER * 2, s * 0, 8, 9703 + bit) > 0.45
        wash = (d < reach) & (hash01(g.px, g.py, 9704 + frame) < 0.55)
        fizz = (d > reach) & (d < reach + 3.5) & (hash01(g.px // 2, g.py, 9705 + frame) < 0.18 * (1 - (d - reach) / 3.5))
        alpha = np.maximum(alpha, np.where(line, 0.95, np.where(back, 0.6, np.where(wash, 0.55, np.where(fizz, 0.5, 0)))))
        level = np.maximum(level, np.where(line, 3.0, np.where(wash, 2.0, np.where(back | fizz, 2.4, 0))))
    rgb = _paint([SHALLOW[3], SHALLOW[4], SNOW[1], PLASTER[4]], level, g, band=0.3)
    a = (alpha * 255).astype(np.uint8) * g.inside
    return home._sprite(g, rgb, a)


def flow(direction, frame, k):
    """Faint streaks and bubbles scrolling downstream, kept in the middle of the channel.
    `n` flows toward -y (screen up-right), `e` toward +x (screen down-right); the engine
    mirrors them for west and south. Eight frames move the pattern one tile."""
    g = home._grid(k)
    shift = 16.0 * frame / FLOW_FRAMES
    if direction == "n":
        gg = _G(g, 0.0, shift)
        across, along_scale = g.u, (1.0, 0.25)
    else:
        gg = _G(g, -shift, 0.0)
        across, along_scale = g.v, (0.25, 1.0)
    mid = np.clip(1 - np.abs(across - 8.0) / 5.5, 0, 1)
    alpha = np.zeros(g.u.shape, np.float32)
    level = np.zeros(g.u.shape, np.float32)
    for seed, cell, dens, ln in ((9801, 4, 0.45, 2.6), (9802, 2, 0.25, 1.4)):
        n = int(16 // cell)
        cu = np.floor(gg.u / cell).astype(np.int64)
        cv = np.floor(gg.v / cell).astype(np.int64)
        for du in (-1, 0, 1):
            for dv in (-1, 0, 1):
                iu, iv = cu + du, cv + dv
                ku, kv = iu % n, iv % n
                keep = hash01(ku, kv, seed, 1) < dens
                pu = (iu + 0.5 + (hash01(ku, kv, seed, 2) - 0.5) * 0.8) * cell
                pv = (iv + 0.5 + (hash01(ku, kv, seed, 3) - 0.5) * 0.8) * cell
                a, b = (gg.u - pu) * along_scale[0], (gg.v - pv) * along_scale[1]
                if direction == "n":
                    e = (gg.u - pu) ** 2 / 0.12 + (gg.v - pv) ** 2 / (ln * ln)
                else:
                    e = (gg.u - pu) ** 2 / (ln * ln) + (gg.v - pv) ** 2 / 0.12
                hit = keep & (e < 1)
                alpha = np.maximum(alpha, np.where(hit, 0.55 * mid, 0))
                level = np.maximum(level, np.where(hit, 1.0 + (e < 0.4), 0))
    bub = (hash01(np.floor(gg.u * 2).astype(np.int64) % 32, np.floor(gg.v * 2).astype(np.int64) % 32, 9803) < 0.012)
    alpha = np.maximum(alpha, np.where(bub, 0.7 * mid, 0))
    level = np.where(bub, 2.0, level)
    rgb = _paint([SHALLOW[2], SHALLOW[3], SHALLOW[4]], level, g, band=0.2)
    return home._sprite(g, rgb, (alpha * 255).astype(np.uint8) * g.inside)


# ---------------------------------------------------------------- land overlays

def rock(mask, k, var=0):
    """Grey limestone outcrop: a few big weathered slabs, each tilted to the light (lit from the
    upper left), thin dark joints between them, a tuft of grass in the joints, and a dark lower
    lip where the rock stands proud of the ground."""
    g0 = home._grid(k)
    f = home.shape_field(mask, g0.u, g0.v, 1.4, 5.0, 1.2, 9901, k)
    f_lo = home.shape_field(mask, g0.u - 1.2, g0.v - 1.2, 1.4, 5.0, 1.2, 9901, k)
    cover = g0.inside & (f > 0.6 * hash01(g0.px, g0.py, 9902))

    def paint(g):
        n = home._pnoise(g.u, g.v, 4, 9903)
        fine = home._pnoise(g.u, g.v, 16, 9909)
        d1, d2, hh, ou, ov = _voronoi(g, 8, 9904, jitter=0.9)
        joint = (d2 - d1) < 0.32
        tilt = (hh - 0.5) * 0.6 - (ou + ov) * 0.04           # each slab leans its own way; upper-left lit
        lvl = 3.4 + tilt + (n - 0.5) * 1.0 + (fine - 0.5) * 0.6 - joint * 1.2 + ((d2 - d1) < 0.7) * (~joint) * 0.4 \
            + (hash01(g.px, g.py, 9905) - 0.5) * 0.5
        lvl = lvl - (f_lo <= 0) * 1.3             # the shadowed lower rim
        rgb = _paint(LIME_ROCK, lvl, g)
        tuft = joint & (hash01(np.floor(g.u).astype(np.int64) % 16, np.floor(g.v).astype(np.int64) % 16, 9906) < 0.25) \
            & (f > 1.5)
        rgb = np.where(tuft[..., None], _paint(STEPPE_GRASS, 2.0 + hash01(g.px, g.py, 9907) * 2, g), rgb)
        lichen = (n > 0.62) & (hash01(g.px, g.py, 9908) < 0.3) & ~joint
        return np.where(lichen[..., None], _paint([OLIVE[1], OLIVE[2], SAND[2]], 1.0 + fine * 2, g), rgb)
    rgb = _interior(g0, paint(g0), paint, var, 9901)
    return home._sprite(g0, rgb, cover * 255)


def snow(mask, k):
    """Spring snow lying in patches: blue-white with a lit crust, rock showing through on the
    thin rims and in a few holes."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 4, 9911)
        fine = home._pnoise(g.u, g.v, 8, 9912)
        lvl = 2.6 + (n - 0.5) * 1.0 + (fine - 0.5) * 0.6 - np.clip(1.6 - f, 0, 1.6) * 0.7
        rgb = _paint(SNOWS, lvl, g, band=0.3)
        thin = (f < 1.3) | ((n < 0.25) & (fine > 0.5))
        rocky = thin & (hash01(g.px, g.py, 9913) < 0.55)
        return np.where(rocky[..., None], _paint(LIME_ROCK, 2.4 + fine * 2, g), rgb)
    return _overlay(mask, k, 1.8, 5.0, 1.5, 9910, paint, fray=1.2)


def scree(mask, k):
    """Pale angular rubble: broken stones each with a lit and a shaded face, finer grit
    between."""
    def paint(g, f):
        d1, d2, hh, ou, ov = _voronoi(g, 2, 9921, jitter=0.95)
        edge = (d2 - d1) < 0.18
        face = np.where((ou * 0.8 - ov * 0.3) < 0, 1.0, -0.6)
        lvl = 2.8 + (hh - 0.5) * 1.6 + face * 0.7 - edge * 1.6 - np.clip(1 - f, 0, 1)
        return _paint(PALE_ROCK, lvl, g)
    return _overlay(mask, k, 1.4, 4.0, 1.2, 9920, paint, fray=1.4)


def marsh(mask, k):
    """Wet green-black mud with standing pools that hold the sky, sedge tufts between."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 4, 9931)
        fine = home._pnoise(g.u, g.v, 8, 9932)
        lvl = 2.4 + (n - 0.5) * 1.2 + (fine - 0.5) * 0.6 + (hash01(g.px, g.py, 9933) - 0.5) * 0.8
        lvl = _marks(g, lvl, 9934, 0.6, _tufts(g), cell=2 if g.fine else 4, interior=None)
        rgb = _paint(MUD, lvl, g)
        pool = (n > 0.6) & (f > 1.2)
        pool_lvl = 2.0 + (fine - 0.5) * 1.0 + ((np.abs(fine - 0.55) < 0.03) * 1.6)
        rgb = np.where(pool[..., None], _paint([SEA[1], SEA[2], RIVER[2], SHALLOW[1], SHALLOW[3]], pool_lvl, g), rgb)
        rim = (n > 0.55) & (n <= 0.6) & (f > 1.0)
        return np.where(rim[..., None], _paint(MUD, 4.2, g), rgb)
    return _overlay(mask, k, 1.0, 4.0, 1.0, 9930, paint)


def _spines(mask, g):
    """Distance to the road's centre lines: one from each open edge's midpoint to the tile
    centre, so ruts run straight through, turn at corners and stop at dead ends."""
    big = np.full(g.u.shape, 1e3, np.float32)
    du, dv = g.u - 8.0, g.v - 8.0
    d = big
    if mask & N_BIT:
        d = np.minimum(d, np.where(g.v <= 8.0, np.abs(du), np.hypot(du, dv)))
    if mask & S_BIT:
        d = np.minimum(d, np.where(g.v >= 8.0, np.abs(du), np.hypot(du, dv)))
    if mask & W_BIT:
        d = np.minimum(d, np.where(g.u <= 8.0, np.abs(dv), np.hypot(du, dv)))
    if mask & E_BIT:
        d = np.minimum(d, np.where(g.u >= 8.0, np.abs(dv), np.hypot(du, dv)))
    if mask == 0:
        d = np.hypot(du, dv) + 1e2
    return d


def road_earth(mask, k):
    """Packed brown earth: two worn wheel ruts and a hoof lane between them following the road,
    stones pushed out to the verges, the edges fraying into the ground."""
    def paint(g, f):
        d = _spines(mask, g)
        n = home._pnoise(g.u, g.v, 4, 9941)
        fine = home._pnoise(g.u, g.v, 8, 9942)
        lvl = 3.4 + (n - 0.5) * 0.9 + (fine - 0.5) * 0.5 + (hash01(g.px, g.py, 9943) - 0.5) * 0.7
        rut = np.abs(d - 3.0) < 0.55 + 0.2 * fine
        rut_lip = (np.abs(d - 3.0) >= 0.55 + 0.2 * fine) & (np.abs(d - 3.0) < 1.0)
        hoof = d < 0.9
        lvl = lvl - rut * 1.6 + rut_lip * 0.5 - hoof * 0.5 * (hash01(g.px // 2, g.py, 9944) < 0.6)
        lvl = lvl - np.clip(1.5 - f, 0, 1.5) * 1.0
        rgb = _paint(ROAD, lvl, g)
        verge = (d > 4.2) & (f > 0.5)
        slvl = _marks(g, np.full_like(lvl, 2.0), 9945, 0.35, STONES, cell=2 if g.fine else 4)
        stone = (slvl != 2.0) & verge
        return np.where(stone[..., None], _paint(PALE_ROCK, slvl + 0.4, g), rgb)
    return _overlay(mask, k, 1.6, 5.0, 0.9, 9940, paint, fray=1.1)


def road_royal(mask, k):
    """The Royal Road: broad, graded and kept, pale compacted gravel with a raised camber along
    its line, a shallow ditch at each side where the road ends; no ruts."""
    def paint(g, f):
        d = _spines(mask, g)
        n = home._pnoise(g.u, g.v, 4, 9951)
        camber = np.clip(1 - d / 8.0, 0, 1)
        lvl = 3.2 + camber * 0.9 + (n - 0.5) * 0.5 + (hash01(g.px, g.py, 9952) - 0.5) * 1.3
        ditch = (f > 0) & (f < 1.6)
        lvl = lvl - ditch * 1.6 + ((f >= 1.6) & (f < 2.2)) * 0.6
        rgb = _paint(GRAVEL, lvl, g)
        dx, dy, h, ok = home._scatter(g, 2, 9953, 0.12)
        peb = ok & (dx * dx + 4 * dy * dy < 1.2 * k) & (f > 2.0)
        return np.where(peb[..., None], _paint([STONE[1], STONE[2], SAND[1]], 1.0 + h * 2 - dy / k, g), rgb)
    return _overlay(mask, k, 0.8, 3.5, 0.4, 9950, paint, fray=0.6)


def field(mask, k):
    """Ploughland: furrows along the tile's x axis (continuing across tiles), each ridge lit on
    its upper side, clods, a few weeds on the headlands."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 4, 9961)
        row = (g.v + (n - 0.5) * 0.8) % 2.0
        lvl = 2.8 + np.where(row < 0.7, 1.0, np.where(row < 1.3, -0.2, -1.1)) + (n - 0.5) * 0.8 \
            + (hash01(g.px, g.py, 9962) - 0.5) * 0.7
        clod = hash01(np.floor(g.u * 1.3).astype(np.int64) % 21, np.floor(g.v * 1.3).astype(np.int64) % 21, 9963) < 0.06
        lvl = lvl + clod * 1.0 - np.clip(1.2 - f, 0, 1.2)
        rgb = _paint(FURROW, lvl, g)
        weed = (f < 2.0) & (hash01(g.px, g.py, 9964) < 0.12)
        return np.where(weed[..., None], _paint(GREEN, 2.5, g), rgb)
    return _overlay(mask, k, 1.2, 3.0, 0.6, 9960, paint)


def scrub(mask, k, var=0):
    """Grey-green garrigue: low rounded cushions of kermes oak, thyme and sage, lit on top and
    shadowed beneath, bare stony ground between."""
    def paint(g, f):
        fine = home._pnoise(g.u, g.v, 8, 9971)
        base = 3.0 + (fine - 0.5) * 0.8 + (hash01(g.px, g.py, 9972) - 0.5) * 0.7
        rgb = _paint(STEPPE_EARTH, base, g)
        d1, d2, hh, ou, ov = _voronoi(g, 4, 9973, jitter=0.9)
        r = 1.0 + hh * 1.1
        bush = (d1 < r) & (hh > 0.4)
        lit = (ou + ov) < -0.2 * r
        lvl = 2.8 + lit * 1.1 - (d1 > r * 0.75) * 0.7 + (hash01(g.px, g.py, 9974) - 0.5) * 0.9
        shadow = ~bush & (np.hypot(ou - 0.5, ov - 0.5) < r) & (hh > 0.4)
        rgb = np.where(shadow[..., None], _paint(STEPPE_EARTH, base - 1.2, g), rgb)
        rgb = np.where(bush[..., None], _paint(SCRUB, lvl, g), rgb)
        flower = bush & lit & (hh > 0.85) & (hash01(g.px, g.py, 9975) < 0.25)
        rgb = np.where(flower[..., None], _rgb(VIOLET[3]), rgb)
        slvl = _marks(g, np.full_like(base, 2.0), 9976, 0.2, STONES, cell=2 if g.fine else 4)
        stone = (slvl != 2.0) & ~bush
        return np.where(stone[..., None], _paint(PALE_ROCK, slvl + 0.5, g), rgb)
    return _overlay(mask, k, 1.6, 5.0, 1.4, 9970, paint, fray=1.3, var=var)


def forest_floor(mask, k, var=0):
    """Under the trees: dark leaf litter and moss, a fallen twig, a fern, so canopies sit on shade."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 4, 9981)
        fine = home._pnoise(g.u, g.v, 8, 9982)
        lvl = 2.4 + (n - 0.5) * 1.2 + (fine - 0.5) * 0.8 + (hash01(g.px, g.py, 9983) - 0.5) * 1.4
        rgb = _paint(LITTER, lvl, g)
        moss = (n > 0.58) & (hash01(g.px, g.py, 9984) < 0.7)
        rgb = np.where(moss[..., None], _paint(GREEN, 1.6 + fine * 2, g), rgb)
        twig = (np.abs(g.u - 0.5 * g.v - 4.0) < 0.25) & (g.v > 5) & (g.v < 10)
        rgb = np.where(twig[..., None], _paint([INK, EARTH[1], EARTH[3]], 1.0 + (g.v % 2 > 1), g), rgb)
        flvl = _marks(g, np.full_like(lvl, 2.0), 9985, 0.3, _tufts(g), cell=4)
        fern = flvl != 2.0
        return np.where(fern[..., None], _paint(GREEN, flvl + 1.6, g), rgb)
    return _overlay(mask, k, 1.8, 5.0, 1.6, 9980, paint, fray=1.4, var=var)


def dune(mask, k):
    """Wind-built sand: ripples running across, crests lit on the windward side and shadowed in
    the lee, a soft rim."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 2, 9991)
        fine = home._pnoise(g.u, g.v, 8, 9992)
        crest = np.sin(2 * np.pi * (g.u + 3 * g.v) / 16.0 + (n - 0.5) * 6.0)
        lvl = 3.2 + crest * 0.8 + (fine - 0.5) * 0.4 + (np.sin(2 * np.pi * (3 * g.u + 9 * g.v) / 16.0 + n * 9) > 0.7) * 0.5
        lvl = lvl + (np.diff(np.pad(crest, ((0, 0), (1, 0)), mode="edge"), axis=1) > 0.05) * 0.5
        return _paint(SANDS, lvl - np.clip(1.4 - f, 0, 1.4) * 0.6, g)
    return _overlay(mask, k, 2.0, 6.0, 1.6, 9990, paint, fray=1.6)


def gravel_desert(mask, k):
    """Hamada: a pavement of dark desert-varnished pebbles on buff ground."""
    def paint(g, f):
        base = 3.4 + (home._pnoise(g.u, g.v, 4, 10001) - 0.5) * 0.8 + (hash01(g.px, g.py, 10002) - 0.5) * 0.6
        rgb = _paint(SANDS, base - np.clip(1.2 - f, 0, 1.2), g)
        for seed, cell, dens, (r0, r1) in ((10003, 2, 0.75, (0.7, 1.3)), (10004, 1, 0.3, (0.4, 0.7))):
            dx, dy, h, ok = home._scatter(g, cell, seed, dens, jitter=0.95)
            r = (r0 + (r1 - r0) * h) * k
            e = (dx / r) ** 2 + ((dy + 0.2 * r) / (0.6 * r)) ** 2
            body = ok & (e < 1) & (f > 0.6)
            lit = dy + 0.2 * r < -0.2 * r
            rgb = np.where(body[..., None], _paint(VARNISH, 2.2 + lit * 1.8 + (h * 7 % 1 - 0.5), g), rgb)
        return rgb
    return _overlay(mask, k, 1.2, 4.0, 1.0, 10000, paint, fray=1.0)


def salt_flat(mask, k):
    """A white salt crust in polygons, its cracks darker and rimmed with a raised lip."""
    def paint(g, f):
        d1, d2, hh, ou, ov = _voronoi(g, 4, 10011)
        e = d2 - d1
        lvl = 3.4 + (hh - 0.5) * 0.6 - (e < 0.25) * 2.0 + ((e >= 0.25) & (e < 0.6)) * 0.8 \
            + (hash01(g.px, g.py, 10012) - 0.5) * 0.5 - np.clip(1.4 - f, 0, 1.4)
        return _paint(SALT, lvl, g, band=0.3)
    return _overlay(mask, k, 1.4, 5.0, 1.2, 10010, paint, fray=1.2)


def fallow(mask, k):
    """Fields at rest: weedy stubble, a trodden grazing path across, droppings of the flock."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 4, 10021)
        lvl = 2.6 + (n - 0.5) * 1.0 + (hash01(g.px, g.py, 10022) - 0.5) * 0.9
        row = (g.v % 2.0) < 0.9
        lvl = lvl + row * 0.5
        lvl = _marks(g, lvl, 10023, 0.4, _tufts(g), cell=2 if g.fine else 4)
        rgb = _paint(FALLOW, lvl - np.clip(1.2 - f, 0, 1.2), g)
        path = np.abs(((g.u - g.v) % 16.0) - 8.0) < 0.7 + 0.4 * n
        return np.where((path & (f > 1.2))[..., None], _paint(STEPPE_EARTH, 3.0 + n, g), rgb)
    return _overlay(mask, k, 1.4, 4.0, 1.0, 10020, paint)


def pasture(mask, k, var=0):
    """Lush short spring grass with clover and flowers: Thracian meadows, Ionian valleys, the
    high Apennine pastures in April."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 4, 10031)
        lvl = 2.6 + (n - 0.5) * 1.0 + (hash01(g.px, g.py, 10032) - 0.5) * 0.6
        lvl = _marks(g, lvl, 10033, 0.5, _tufts(g), cell=2 if g.fine else 4)
        rgb = _paint(LUSH, lvl - np.clip(1.2 - f, 0, 1.2) * 0.6, g)
        dx, dy, h, ok = home._scatter(g, 2, 10034, 0.18)
        fl = ok & (dx * dx + 4 * dy * dy < 0.6 * k) & (f > 1.0)
        col = np.where((h < 0.4)[..., None], np.array(_rgb(PLASTER[4]), np.uint8),
                       np.where((h < 0.7)[..., None], np.array(_rgb(STRAW[3]), np.uint8),
                                np.array(_rgb(POPPY[1]), np.uint8)))
        return np.where(fl[..., None], col, rgb)
    return _overlay(mask, k, 1.6, 5.0, 1.2, 10030, paint, fray=1.2, var=var)


OVERLAYS = {"world.rock": rock, "world.snow": snow, "world.scree": scree, "world.marsh": marsh,
            "world.road_earth": road_earth, "world.road_royal": road_royal, "world.field": field,
            "world.scrub": scrub, "world.forest_floor": forest_floor, "world.dune": dune,
            "world.gravel_desert": gravel_desert, "world.salt_flat": salt_flat, "world.fallow": fallow,
            "world.pasture": pasture}
WATER_OVERLAYS = {"world.sea": sea, "world.shallows": shallows, "world.river": river}


# ---------------------------------------------------------------- edge faces

def _face(side, k, above):
    px, py, s, d, band, H, W, ox, oy = _face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    return px, py, s, d, band, H, W, ox, oy, shade


def _sprite(rgb, alpha, H, W, ox, oy):
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha * 255
    return Sprite(rgba, ox, oy)


class _P:
    """Pixel coordinates for _paint."""

    def __init__(self, px, py, k):
        self.px, self.py, self.k = px, py, k


def _strata(s, d, W, band, k, v, seed):
    """Bedding of one level for soft faces (earth): beds of uneven thickness that bend a little.
    Near the band's ends the pattern is common to every look, so any two looks stack."""
    n = _periodic(s, d, W, band, 1.3, seed, v)
    t = np.clip(d / band, 0, 1)
    win = np.sin(np.pi * t) ** 2 * np.sin(np.pi * np.clip(s / W, 0, 1))
    off = (hash01(v, seed, 1) - 0.5) * 3.0 * k + 1.2 * k * np.sin(2 * np.pi * t + 6.28 * hash01(v, seed, 2)) \
        + s * (hash01(v, seed, 3) - 0.5) * 0.3
    bed = ((d + (n - 0.5) * 2.5 * k + win * off) % (4 * k)) / (4 * k)
    return n, bed


def _cliff(s, d, W, band, k, v, seed, shade):
    """Natural rock of one level: big facets lit or shaded by which way they turn to the light,
    vertical ribs and joints, and one broken ledge a level (a lit lip over a dark undercut),
    pushed up or down by the facets so ledges never line up into courses. Every term repeats
    across the face width and the band, so faces join side by side and stack."""
    big = _periodic(s, d, W, band, 0.55, seed, v)
    dprof = _periodic(s + 2 * k, d, W, band, 0.55, seed, v) - big
    lit = np.clip(dprof * (-16.0 if shade == 0.0 else 16.0), -1.0, 1.0)
    rib = _periodic(s, d * 0.2, W, band, 1.2, seed + 1, v)
    grain = _periodic(s, d, W, band, 3.0, seed + 2, v)
    bed = (d + (big - 0.5) * 7.0 * k) % band
    broken = _periodic(s, d * 0.3, W, band, 1.4, seed + 3, v) > 0.45
    lip = (bed < 1.0 * k / 2 + 0.5) & broken
    under = (bed >= 0.5 * k + 0.5) & (bed < 1.5 * k) & broken
    joint = (np.abs(rib - 0.5) < 0.025) & (grain > 0.4)
    lvl = 3.2 + shade + lit * 1.0 + (rib - 0.5) * 0.9 + (grain - 0.5) * 0.6 + lip * 1.1 - under * 0.6 - joint * 0.9
    return lvl, lip, under, lit, big


def rock_face(side, v, k, top=False):
    """One level of grey limestone cliff: lit and shaded facets, ribs and joints, a broken ledge
    with a shrub on it here and there; the rim band carries dry grass."""
    above = 6 * k if top else 0
    px, py, s, d, band, H, W, ox, oy, shade = _face(side, k, above)
    on = (d >= 0) & (d < band)
    lvl, lip, under, lit, big = _cliff(s, d, W, band, k, v, 10101, shade)
    pit = hash01(px, py, 10103 + v) < 0.03
    P = _P(px, py, k)
    rgb = _paint(LIME_ROCK, lvl - pit * 0.7, P)
    stain = (_periodic(s, d * 0.25, W, band, 1.0, 10110, v) > 0.7) & ~lip
    rgb = np.where(stain[..., None], _paint([STONE[1], ATTIC_ROCK[1], RUST[0], ATTIC_ROCK[2]], lvl - 0.8, P), rgb)
    shrub = lip & (_periodic(s, d, W, band, 3.0, 10104, v) > 0.74) & on
    grow = np.zeros_like(shrub)
    for dy in range(1, 3 * k):
        grow |= np.roll(shrub, -dy, axis=0) & (hash01(px, py - dy, 10105) < 0.7)
    rgb = np.where(grow[..., None], _paint([PINE[0], OLIVE[0], OLIVE[1], LEAF[2]], 1.8 + shade + hash01(px, py, 10106), P), rgb)
    alpha = on.copy()
    if top:
        rim = (d < 0) & (d >= -above)
        tuft = rim & (np.abs(d) < 2 + 3 * (_periodic(s, d * 0, W, band, 4.0, 10107, v) > 0.6) * (hash01(px, 0, 10108) < 0.6))
        alpha = (on & (d >= 0)) | tuft
        rgb = np.where(tuft[..., None], _paint(STEPPE_GRASS, 2.6 + shade + (hash01(px, py, 10109) - 0.5), P), rgb)
        rgb, alpha = _soften(rgb, alpha, px, py, s, d, W, band, k, v, shade, P, 10130, rock=True)
    return _sprite(rgb, alpha | grow, H, W, ox, oy)


def _soften(rgb, alpha, px, py, s, d, W, band, k, v, shade, P, seed, rock):
    """The uppermost band of a face, which is the whole face where the ground steps one level:
    a rounded, lit shoulder under the rim with grass hanging over it in uneven tufts, and at the
    foot a fan of fallen stones and soil with grass coming through, so a low step reads as a
    slope's broken edge rather than a cut."""
    on = (d >= 0) & (d < band)
    hang = (1.0 + 2.5 * _periodic(s, d * 0, W, band, 3.0, seed, v)) * k
    shoulder = on & (d < hang + k) & ~(d < hang * (hash01(px, 0, seed + 1) < 0.55))
    rgb = np.where(shoulder[..., None], _paint(PALE_ROCK if rock else [EARTH[1], EARTH[2], CLAY[1], EARTH[3], SAND[2]],
                                                3.6 + shade * 0.6 + (hash01(px, py, seed + 2) - 0.5) * 0.6, P), rgb)
    drape = on & (d < hang * (hash01(px, 0, seed + 1) < 0.55))
    rgb = np.where(drape[..., None], _paint(STEPPE_GRASS, 2.4 + shade + (hash01(px, py, seed + 3) - 0.5), P), rgb)
    fan = (2.0 + 2.5 * _periodic(s + 3 * k, d * 0, W, band, 2.0, seed + 4, v)) * k
    foot = on & (d > band - fan)
    stone = foot & (hash01(px // 2, py // 2, seed + 5 + v) < 0.35)
    grass = foot & ~stone & (hash01(px, py, seed + 6) < 0.3)
    rgb = np.where(foot[..., None], _paint([INK, EARTH[0], EARTH[1], EARTH[2], SAND[1]], 2.4 + shade * 0.5 +
                                           (hash01(px, py, seed + 7) - 0.5) * 0.8, P), rgb)
    rgb = np.where(stone[..., None], _paint(PALE_ROCK, 2.6 + shade * 0.6 + (hash01(px, py, seed + 8) - 0.5), P), rgb)
    rgb = np.where(grass[..., None], _paint(STEPPE_GRASS, 2.2 + shade + (hash01(px, py, seed + 9) - 0.5), P), rgb)
    return rgb, alpha


def earth_face(side, v, k, top=False):
    """One level of an earth bank (river terraces, tells, field steps): brown earth in faint
    layers, pebbles and roots, a grassy lip on the rim band."""
    above = 5 * k if top else 0
    px, py, s, d, band, H, W, ox, oy, shade = _face(side, k, above)
    on = (d >= 0) & (d < band)
    n, bed = _strata(s, d, W, band, k, v, 10111)
    layer = bed < 0.2
    pebble = hash01(px // 2, py // 2, 10112 + v) < 0.018
    root = (np.abs(((s * 0.7 + d) % (W / 2)) - 3) < 0.5) & (d < band * 0.4) & (_periodic(s, d, W, band, 2.5, 10113, v) > 0.6)
    lvl = 3.0 + shade + (n - 0.5) * 1.4 - layer * 0.5 + pebble * 1.2 - root * 1.2
    P = _P(px, py, k)
    rgb = _paint([INK, EARTH[0], EARTH[1], EARTH[2], CLAY[1], EARTH[3], SAND[2]], lvl, P)
    rgb = np.where((pebble & on)[..., None], _paint([STONE[1], STONE[2], STONE[3]], 1.2 + shade, P), rgb)
    alpha = on.copy()
    if top:
        tall = hash01(px, 0, 10114 + v) * above * (hash01(px // 3, 0, 10115 + v) < 0.6)
        lip = (d < 2 * k) & (d >= -tall - 1)
        alpha = alpha | lip
        rgb = np.where(lip[..., None], _paint(STEPPE_GRASS, 2.8 + shade + (hash01(px, py, 10116) - 0.5), P), rgb)
        rgb, alpha = _soften(rgb, alpha, px, py, s, d, W, band, k, v, shade, P, 10140, rock=False)
    return _sprite(rgb, alpha, H, W, ox, oy)


def snow_face(side, v, k, top=False):
    """Rock of the high tops with snow lying where it can: on the ledges and the upward-turned
    facets, thinning down the band; the rim band is a snow cornice curling over the edge."""
    above = 5 * k if top else 0
    px, py, s, d, band, H, W, ox, oy, shade = _face(side, k, above)
    on = (d >= 0) & (d < band)
    lvl, lip, under, lit, big = _cliff(s, d, W, band, k, v, 10121, shade)
    P = _P(px, py, k)
    rgb = _paint(LIME_ROCK, lvl - 0.2, P)
    drift = _periodic(s, d, W, band, 1.6, 10122, v)
    lying = (lip | ((d < band * (0.25 + 0.5 * drift)) & (lit > -0.2) & ~under)) & on
    lying &= hash01(px, py, 10125 + v) < 0.92
    rgb = np.where(lying[..., None], _paint(SNOWS, 2.6 + shade * 0.7 + lit * 0.6 + lip * 0.6, P, band=0.3), rgb)
    alpha = on.copy()
    if top:
        drop = (1.5 + 2.5 * _periodic(s, d * 0, W, band, 3.0, 10123, v)) * k
        cornice = (d < drop) & (d >= -above * (0.4 + 0.6 * _periodic(s, d * 0, W, band, 2.0, 10124, v)))
        alpha = alpha | cornice
        rgb = np.where(cornice[..., None], _paint(SNOWS, 3.4 + shade * 0.6 - (d > drop - k) * 1.2, P), rgb)
    return _sprite(rgb, alpha, H, W, ox, oy)


def coast_face(side, v, k, top=False, frame=None):
    """A sea cliff: weathered limestone with a pale salt-stained band; a static level (`frame`
    None) is any upper level, the animated foot (frames 0-3) is the level that meets the sea,
    with a wave-cut notch and surf breaking against it, running up and drawing back."""
    above = 5 * k if top else 0
    px, py, s, d, band, H, W, ox, oy, shade = _face(side, k, above)
    on = (d >= 0) & (d < band)
    lvl, lip, under, lit, n = _cliff(s, d, W, band, k, v, 10131, shade)
    salt = _periodic(s, d * 0.3, W, band, 1.6, 10132, v) > 0.6
    lvl = lvl + salt * 0.5
    P = _P(px, py, k)
    rgb = _paint([INK, STONE[1], ATTIC_ROCK[2], ATTIC_ROCK[3], LIMESTONE[4], ATTIC_ROCK[5], SAND[4]], lvl, P)
    alpha = on.copy()
    if frame is not None:
        t = frame / 4
        notch = (d > band - 3.5 * k) & (d < band - 1.5 * k)
        rgb = np.where(notch[..., None], _paint([INK, STONE[0], STONE[1], SEA[1]], 1.4 + shade + n, P), rgb)
        wet = d > band - 4.5 * k
        rgb = np.where((wet & ~notch)[..., None], _paint([INK, STONE[0], STONE[1], ATTIC_ROCK[2]], lvl - 1.2, P), rgb)
        run = (2.0 + 2.2 * (0.5 + 0.5 * math.sin(2 * math.pi * t)) + (_periodic(s, d * 0, W, band, 2.0, 10133, v) - 0.5) * 2) * k
        surf = (d > band - run) & on
        spray = (d > band - run - 2 * k) & (d <= band - run) & (hash01(px, py, 10134 + frame) < 0.35) & on
        rgb = np.where(surf[..., None], _paint([SHALLOW[3], SHALLOW[4], SNOW[1], PLASTER[4]],
                                               2.2 + hash01(px, py, 10135 + frame) * 1.6, P), rgb)
        rgb = np.where(spray[..., None], _rgb(PLASTER[4]), rgb)
    if top:
        tuft = (d < 0) & (d >= -above) & (np.abs(d) < 2 + 3 * (_periodic(s, d * 0, W, band, 4.0, 10136, v) > 0.55))
        alpha = alpha | tuft
        rgb = np.where(tuft[..., None], _paint(SCRUB, 2.6 + shade + (hash01(px, py, 10137) - 0.5), P), rgb)
    return _sprite(rgb, alpha, H, W, ox, oy)


def basalt_face(side, v, k, top=False):
    """Dark columnar basalt: upright prisms with lit and shaded faces, cross joints, rusty
    weathering bleeding down; the rim band is broken rubble with a little grass."""
    above = 4 * k if top else 0
    px, py, s, d, band, H, W, ox, oy, shade = _face(side, k, above)
    on = (d >= 0) & (d < band)
    width = 3.0 * k
    col = np.floor((s + 0.7 * hash01(np.floor(d / (4 * k)).astype(np.int64), v, 10141) * width) / width)
    a = ((s + 0.7 * hash01(np.floor(d / (4 * k)).astype(np.int64), v, 10141) * width) % width) / width
    facet = np.where(a < 0.45, 0.9, -0.5)
    joint = (a < 0.12) | ((d + hash01(col.astype(np.int64), v, 10142) * 6 * k) % (5 * k) < 1)
    lvl = 2.4 + shade + facet + (hash01(col.astype(np.int64), 10143) - 0.5) * 0.8 - joint * 1.4
    P = _P(px, py, k)
    rgb = _paint([INK, *BASALT], lvl, P)
    rust = (_periodic(s, d, W, band, 1.5, 10144, v) > 0.63) & ~joint
    rgb = np.where(rust[..., None], _paint([BASALT[1], RUST[0], RUST[1]], 1.0 + facet, P), rgb)
    alpha = on.copy()
    if top:
        rub = (d < 0) & (d >= -above) & (hash01(px // 2, py // 2, 10145 + v) < 0.5 + 0.4 * (d > -2 * k))
        alpha = alpha | rub
        rgb = np.where(rub[..., None], _paint([INK, BASALT[1], BASALT[3], OLIVE[1]], 2.0 + shade + hash01(px, py, 10146), P), rgb)
    return _sprite(rgb, alpha, H, W, ox, oy)


FACES = {"world.rock": rock_face, "world.earth": earth_face, "world.snow": snow_face, "world.coast": coast_face,
         "world.basalt": basalt_face}
