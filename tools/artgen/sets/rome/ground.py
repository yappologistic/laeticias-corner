"""Rome's flat sprites, evaluated per pixel like terrain.py: the April ground (rome.md §3.5),
the faces under raised tiles (tufa cliffs of the Capitol, brick substructures of the Palatine,
travertine river embankments with mooring rings, earth banks; world-tech.md §1.6), the set's
effects and its carried goods.

Overlays repeat per tile (the contract gives them masks, not variants), so their patterns are
built to hide the repeat: polygonal basalt from jittered Voronoi cells with stones of several
sizes, travertine slabs whose joints are offset within the tile, brick in herringbone, fields
in rows that run through the tile edge. The base grass has eight variants with spring flowers
(poppies, daisies, clover) gathered in clumps, so a meadow of random variants never shows a
grid."""

import math
import re

import numpy as np

import terrain as home
from pack import Sprite
from palette import (BASALT, BRICK, EARTH, GLOW, INK, LEAF, PLASTER, POPPY, STONE, STRAW, TIBER, TRAVERTINE, TUFA,
                     VIOLET, WATER, CINNABAR, OLIVE, MARBLE, _rgb)
from render import render_base
from sets.parsa.ground import _face_grid, _fx, _overlay, _periodic
from voxel import Model, hash01

FRAMES = {"rome.river_tiber": 4, "rome.steam": 6, "rome.smoke": 6, "rome.fire": 6, "rome.torch_flame": 6,
          "rome.spray": 4, "rome.incense": 6, "rome.dust": 6, "rome.glint": 4, "rome.spout": 4, "rome.sparks": 4,
          "rome.bonfire": 6}

TERRAIN_KEY = re.compile(r"terrain/(rome\.\w+)/(?:v(\d+)|m(\d+)/f(\d+))")
BASE_VARIANTS = 8
BAS = [INK, *BASALT]
TRAV = TRAVERTINE[1:]
JOINT = [INK, STONE[1], STONE[2], PLASTER[1]]


def grass_spring(v, k):
    """April grass: the home lawn's fresh green with spring flowers in clumps: poppies, white
    daisies, yellow clover and a few violets, more of them on the later variants."""
    s = home.grass(v % 4, k, "spring")
    g = home._grid(k)
    rgb = s.rgba[..., :3].copy()
    dens = (0.0, 0.05, 0.02, 0.08, 0.12, 0.04, 0.16, 0.1)[v]
    for seed, colour, cell in ((1401, POPPY[0], 2), (1402, PLASTER[4], 2), (1403, STRAW[3], 2), (1404, VIOLET[2], 4)):
        dx, dy, h, ok = home._scatter(g, cell, seed + v * 7, home._clump(seed + v, dens * 2.2), jitter=0.9,
                                      interior=(2.0, 1.0))
        petal = ok & (np.abs(dx) < 0.6 * k) & (np.abs(dy) < 0.6 * k)
        rgb = np.where(petal[..., None], np.array(_rgb(colour), np.uint8), rgb)
        if seed == 1401:   # poppies get a dark heart and a stem
            rgb = np.where((ok & (np.abs(dx) < 0.6 * k) & (dy > 0.6 * k) & (dy < 1.6 * k))[..., None],
                           np.array(_rgb(LEAF[2]), np.uint8), rgb)
    out = s.rgba.copy()
    out[..., :3] = np.where(g.inside[..., None], rgb, out[..., :3])
    return Sprite(out, s.ox, s.oy)


def basalt_paving(mask, k):
    """A Roman road: polygonal blocks of grey-black basalt (selce) fitted tight, each block a
    worn pillow lit from the upper left, pale joints of grit, and kerbstones (crepidines) of
    tufa along the open edges."""
    def paint(g, f):
        f1, f2, du, dv, h = home._cells(g.u, g.v, 16 / 4, 1411, jitter=0.95, weight=0.6)
        gap = f2 - f1
        height = np.sqrt(np.clip((gap - 0.25) / 1.8, 0, 1))
        hy, hx = np.gradient(height)
        lit = np.clip(-(hx * 0.55 + hy * 0.85) * 2.8, -1.2, 1.2)
        lvl = 2.6 + (h * 13 % 1 - 0.5) * 0.9 + lit + 0.3 * height + (hash01(g.px, g.py, 1412) - 0.5) * 0.3
        rgb = home._paint(BAS, lvl, g.px, g.py, band=0.4, k=k)
        rgb = np.where((gap < 0.28)[..., None], home._paint(JOINT, 1.6 + h, g.px, g.py, k=k), rgb)
        kerb = f < 1.6
        krgb = home._paint([INK, *TUFA], 3.2 + (hash01((g.u + g.v).astype(np.int64) // 3, 0, 1413) - 0.5) * 1.2
                           - (f < 0.4) * 1.5 + ((f > 1.2) & (f < 1.6)) * 0.8, g.px, g.py, k=k)
        return np.where(kerb[..., None], krgb, rgb)
    return _overlay(mask, k, 0.4, 1.5, 0.15, 1410, paint)


def travertine_paving(mask, k):
    """Forum paving: big travertine slabs in staggered rows (the joints offset inside the tile
    so rows do not line up across tiles), each slab its own cream tone with the stone's pits,
    worn smoother where feet pass."""
    def paint(g, f):
        u, v = g.u, g.v
        row = np.floor((v + 2.0) / 5.333)
        a = (u + 3.0 + (row % 3) * 5.333) % 16.0
        joint = (((v + 2.0) % 5.333) < 0.35) | ((a % 8.0) < 0.35)
        h = hash01(row.astype(np.int64) % 3, (a >= 8).astype(np.int64), 1421)
        pit = hash01(g.px // max(1, k // 2), g.py // max(1, k // 2), 1422) < 0.035
        lvl = 4.0 + (h - 0.5) * 1.0 + (home._pnoise(u, v, 4, 1423) - 0.5) * 0.5 - joint * 1.6 - pit * 1.4 \
            - np.clip(1 - f, 0, 1) * 0.8
        return home._paint(TRAV, lvl, g.px, g.py, band=0.4, k=k)
    return _overlay(mask, k, 0.3, 1.2, 0.1, 1420, paint)


def brick_ground(mask, k):
    """Yards in opus spicatum: small bricks set on edge in a herringbone, mortar between."""
    def paint(g, f):
        u, v = g.u, g.v
        blk = (np.floor(u / 2.0) + np.floor(v / 2.0)) % 2
        a = np.where(blk == 0, u, v)
        b = np.where(blk == 0, v, u)
        joint = ((a % 2.0) < 0.3) | (((b + np.floor(a / 2.0)) % 1.0) < 0.22)
        lvl = 3.0 + (hash01(np.floor(u).astype(np.int64), np.floor(v).astype(np.int64), 1431) - 0.5) * 1.1 \
            - joint * 1.6 - np.clip(1 - f, 0, 1)
        return home._paint([INK, *BRICK], lvl, g.px, g.py, k=k)
    return _overlay(mask, k, 0.5, 2.0, 0.2, 1430, paint)


def packed_earth(mask, k):
    return home.path(mask, k)


def tufa_rock(mask, k):
    """The Capitol's tufa: grey-brown volcanic stone in soft lumps with dark pores, grass and
    caper in the cracks."""
    def paint(g, f):
        f1, f2, du, dv, h = home._cells(g.u, g.v, 16 / 3, 1441, jitter=0.9, weight=0.8)
        gap = f2 - f1
        height = np.sqrt(np.clip(gap / 2.5, 0, 1))
        hy, hx = np.gradient(height)
        lit = np.clip(-(hx * 0.55 + hy * 0.85) * 2.2, -1.2, 1.2)
        pore = hash01(g.px, g.py, 1442) < 0.06
        lvl = 3.2 + lit + (h - 0.5) * 0.8 - pore * 1.0 - np.clip(1 - f, 0, 1)
        rgb = home._paint([INK, *TUFA], lvl, g.px, g.py, k=k)
        crack = gap < 0.35
        return np.where(crack[..., None], home._paint([LEAF[1], LEAF[2], LEAF[3]], 1.4 + h, g.px, g.py, k=k), rgb)
    return _overlay(mask, k, 0.9, 3.5, 0.8, 1440, paint)


def field_spring(mask, k):
    """Green wheat in April: dense rows running along u through the tile edges, darker
    furrows, a poppy here and there."""
    def paint(g, f):
        row = (g.v % 2.0) < 1.25
        lvl = np.where(row, 3.2 + (home._pnoise(g.u, g.v, 8, 1451) - 0.5) * 1.4 + (hash01(g.px, g.py, 1452) - 0.5),
                       1.2)
        rgb = home._paint([LEAF[1], LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]], lvl - np.clip(1 - f, 0, 1),
                          g.px, g.py, k=k)
        poppy = row & (hash01(g.px, g.py, 1453) < 0.012)
        return np.where(poppy[..., None], np.array(_rgb(POPPY[0]), np.uint8), rgb)
    return _overlay(mask, k, 1.0, 3.0, 0.5, 1450, paint)


def vineyard_soil(mask, k):
    """Worked brown soil between rows of vines, clods and young green weeds."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 8, 1461)
        furrow = (g.u % 4.0) < 1.2
        lvl = 2.6 + (n - 0.5) * 1.2 + (hash01(g.px, g.py, 1462) - 0.5) * 0.9 - furrow * 0.8 - np.clip(1 - f, 0, 1)
        rgb = home._paint([INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3]], lvl, g.px, g.py, k=k)
        weed = (hash01(g.px // 2, g.py // 2, 1463) < 0.04) & ~furrow
        return np.where(weed[..., None], home._paint([LEAF[2], LEAF[3], LEAF[4]], 1.5 + n, g.px, g.py, k=k), rgb)
    return _overlay(mask, k, 1.0, 4.0, 0.6, 1460, paint)


def river_tiber(mask, frame, frames, k):
    """The "flavus Tiberis": blue water darkening in the channel, carrying drifts of
    yellow-green silt in the current and along the banks, shaded under them, with ripple crests
    catching the sky and glints drifting with the frames."""
    g = home._grid(k)
    field = lambda du: home.shape_field(mask, g.u - du, g.v - du, 0.8, 3.5, 0.5, 1470, k)
    f = field(0)
    cover = g.inside & (f > 0)
    wall1, wall2, shade = field(1) <= 0, field(2) <= 0, field(3) <= 0
    level = home._ripples(g, f, shade, frame, frames)
    swirl = home._pnoise(g.u - frame / frames * 4.0, g.v, 4, 1471) - 0.5
    rgb = home._paint(RIVER, level * 1.15 - 0.2 + swirl * 0.6, g.px, g.py, band=0.2, k=k)
    # The silt: green-brown along the banks only, over clear blue depth, so the Tiber reads as
    # water (drifts in mid-channel repeated tile by tile as an olive motif, QA5 Q5-A-03).
    silt = (f < 1.6) & (hash01(g.px, g.py, 1472) < 0.55) & (level < 3.6)
    rgb = np.where(silt[..., None], home._paint(SILT, level * 0.9 - 0.6 + swirl, g.px, g.py, band=0.2, k=k), rgb)
    lip = f < 0.6
    rgb = np.where((lip & ~wall2)[..., None], np.array(_rgb(TIBER[4]), np.uint8), rgb)
    bank = home._paint([INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3]], np.where(wall1, 3.2, 2.0), g.px, g.py, k=k)
    rgb = np.where((wall2 | lip & (f < 0.25))[..., None], bank, rgb)
    return home._sprite(g, rgb, cover * 255)


RIVER = [WATER[0], WATER[1], WATER[2], WATER[3], WATER[4], WATER[5], PLASTER[4]]
SILT = [WATER[1], TIBER[0], TIBER[1], TIBER[2], TIBER[3]]


def mud_bank(mask, k):
    """The Tiber's mud banks: wet brown-grey mud, drying paler higher up, reeds and bird feet."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 6, 1481)
        lvl = 2.4 + (n - 0.5) * 1.4 + np.clip(f / 6, 0, 1) * 0.8 + (hash01(g.px, g.py, 1482) - 0.5) * 0.6
        rgb = home._paint([INK, EARTH[0], STONE[1], EARTH[1], STONE[2], EARTH[2]], lvl, g.px, g.py, k=k)
        dx, dy, h, ok = home._scatter(g, 2, 1483, 0.3, jitter=0.9)
        reed = ok & (np.abs(dx) < 0.5 * k) & (dy < 0) & (dy > -(2 + h * 3) * k)
        return np.where(reed[..., None], home._paint([OLIVE[1], OLIVE[2], STRAW[1], OLIVE[3]], 2.0 + h * 2 - dy * 0.1,
                                                     g.px, g.py, k=k), rgb)
    return _overlay(mask, k, 1.0, 4.0, 0.8, 1480, paint)


TERRAIN = {"rome.basalt_paving": basalt_paving, "rome.travertine_paving": travertine_paving,
           "rome.brick_ground": brick_ground, "rome.packed_earth": packed_earth, "rome.tufa_rock": tufa_rock,
           "rome.field_spring": field_spring, "rome.vineyard_soil": vineyard_soil, "rome.mud_bank": mud_bank}


# ---------------------------------------------------------------- faces

def _face_sprite(rgb, alpha, H, W, ox, oy):
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha * 255
    return Sprite(rgba, ox, oy)


def tufa_face(side, v, k, top=False):
    """One level of the Capitol's tufa cliff (the Tarpeian rock): soft grey-brown beds with
    lit lips and dark undercuts, pores, caper and grass on the ledges."""
    above = 4 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = _face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    on = (d >= 0) & (d < band)
    n = _periodic(s, d, W, band, 1.6, 1501, v)
    bed = (d + (n - 0.5) * 3 * k) % (4 * k)
    lip, under = bed < 1.2, bed > 4 * k - 1.4
    pore = hash01(px, py, 1502 + v) < 0.07
    lvl = 3.0 + shade + (n - 0.5) * 1.2 + lip * 1.0 - under * 1.3 - pore * 0.9
    rgb = home._paint([INK, *TUFA], lvl, px, py, k=k)
    plant = (_periodic(s, d, W, band, 3.0, 1503, v) > 0.7) & lip
    rgb = np.where(plant[..., None], home._paint([LEAF[1], LEAF[2], LEAF[3]], 2.0 + shade, px, py, k=k), rgb)
    alpha = on.copy()
    if top:
        tuft = (d < 0) & (d >= -above) & (hash01(px, 0, 1504 + v) < 0.5)
        alpha = alpha | tuft
        rgb = np.where(tuft[..., None], home._paint(home.GRASS, 2.6 + shade, px, py, k=k), rgb)
    return _face_sprite(rgb, alpha, H, W, ox, oy)


def brick_face(side, v, k, top=False):
    """One level of brick-faced concrete (the Palatine substructures, the Aventine retaining
    walls): thin red bricks in courses, a bonding course of pale tiles, putlog holes; a
    travertine coping on the top band."""
    above = 2 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = _face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    on = (d >= (-above if top else 0)) & (d < band)
    row = np.floor(d / 2).astype(np.int64)
    a = (s + (row % 2) * 3) % W
    mortar = (d % 2) < 0.8
    brick = (a % 6) < 0.8
    bond = (d % (8 * k)) < 2
    putlog = (np.abs((s % (W / 2)) - W / 4) < 1.2) & (np.abs(d - band * 0.5) < 1.2) & (v % 2 == 0)
    lvl = 3.0 + shade + (hash01(row, np.floor(a / 6).astype(np.int64), 1511 + v) - 0.5) * 0.9 + mortar * 1.1 \
        - brick * 0.4 + bond * 0.9 - putlog * 2.4
    lvl = np.where(d < 0, 4.2 + shade, lvl)
    rgb = home._paint([INK, *BRICK], lvl, px, py, k=k)
    rgb = np.where((d < 0)[..., None], home._paint(TRAV, 3.4 + shade, px, py, k=k), rgb)
    return _face_sprite(rgb, on, H, W, ox, oy)


def travertine_face(side, v, k, top=False):
    """One level of travertine embankment (the Tiber quays): big blocks with drafted edges, a
    bronze mooring ring on some, damp darkening; the top band a coping course."""
    above = 2 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = _face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    on = (d >= (-above if top else 0)) & (d < band)
    course = np.floor(d / (4 * k)).astype(np.int64)
    a = (s + np.where(course % 2 == 0, 0, W // 2)) % W
    joint = ((d % (4 * k)) < 1) | (a < 1) | (np.abs(a - W // 2) < 1)
    lvl = 3.4 + shade + (hash01(course, (a >= W // 2).astype(np.int64), v, 1521) - 0.5) * 0.8 - 1.5 * joint \
        - 0.4 * (hash01(px, py, 1522) < 0.05)
    lvl = np.where(d < 0, 4.2 + shade, lvl)
    rgb = home._paint([INK, *TRAVERTINE], lvl, px, py, k=k)
    ring = (v % 2 == 1) & (np.abs(np.hypot(s - W * 0.5, d - band * 0.55) - 1.6 * k) < 0.7)
    rgb = np.where(ring[..., None], home._paint(["#6b4a1a", "#9a7226", "#c99d36"], 1.5, px, py, k=k), rgb)
    return _face_sprite(rgb, on, H, W, ox, oy)


def earth_face(side, v, k, top=False):
    """One level of an earth bank: brown earth with faint layers and stones, grass on the lip."""
    above = 4 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = _face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    on = (d >= 0) & (d < band)
    n = _periodic(s, d, W, band, 1.6, 1531, v)
    layer = (d + n * 2 * k) % (3 * k) < 1
    pebble = hash01(px // 2, py // 2, 1532 + v) < 0.02
    lvl = 3.0 + shade + (n - 0.5) * 1.4 - layer * 0.5 + pebble * 1.2
    rgb = home._paint([INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3], EARTH[4]], lvl, px, py, k=k)
    alpha = on.copy()
    if top:
        tall = hash01(px, 0, 1533 + v) * above * (hash01(px // 3, 0, 1534 + v) < 0.6)
        lip = (d < 2 * k) & (d >= -tall - 1)
        alpha = alpha | lip
        rgb = np.where(lip[..., None], home._paint(home.GRASS, 2.8 + shade + (hash01(px, py, 1535) - 0.5), px, py,
                                                   k=k), rgb)
    return _face_sprite(rgb, alpha, H, W, ox, oy)


FACES = {"tufa": tufa_face, "brick": brick_face, "travertine": travertine_face, "earth": earth_face}


# ---------------------------------------------------------------- effects

def fx(fid, f, n, k):
    rng = np.random.Generator(np.random.PCG64([sum(map(ord, fid)), 3]))
    pts = []
    t = f / n
    if fid in ("rome.fire", "rome.torch_flame", "rome.bonfire"):
        s = {"rome.fire": 1.0, "rome.torch_flame": 0.6, "rome.bonfire": 1.8}[fid]
        for i in range(12 if fid != "rome.bonfire" else 20):
            h, a = rng.uniform(0, 1), rng.uniform(-1, 1)
            ph = (h + t) % 1.0
            col = (GLOW[2], GLOW[1], GLOW[0], CINNABAR[3])[min(3, int(ph * 4))]
            pts.append((a * (1 - ph) * 3 * s, -ph * 10 * s, col, (1.6 - ph) * s))
        return _fx(pts, (int(16 * s) + 4, int(14 * s) + 4), k)
    if fid in ("rome.smoke", "rome.steam", "rome.incense"):
        cols = {"rome.smoke": (STONE[2], STONE[3], PLASTER[1]), "rome.steam": (PLASTER[3], PLASTER[4], STONE[5]),
                "rome.incense": (STONE[3], STONE[4], VIOLET[3])}[fid]
        size = {"rome.smoke": 1.0, "rome.steam": 1.3, "rome.incense": 0.6}[fid]
        for i in range(16):
            h = ((i / 16) + t) % 1.0
            pts.append((h * h * 8 * size + math.sin(h * 6 + i) * 1.2, -h * 30 * size, cols[i % 3],
                        (0.8 + h * 2.2) * size))
        return _fx(pts, (int(26 * size) + 4, int(34 * size) + 4), k)
    if fid == "rome.dust":                # stone dust over the building site
        for i in range(12):
            x0, y0 = rng.uniform(-7, 7), rng.uniform(-6, 0)
            pts.append((x0 + t * rng.uniform(-3, 3), y0 - t * 7, (MARBLE[5], MARBLE[4], PLASTER[3])[i % 3], 0.6))
        return _fx(pts, (22, 18), k)
    if fid in ("rome.spray", "rome.spout"):  # a fountain's jet and the spout of a street basin
        for i in range(8):
            ph = ((i / 8) + t) % 1.0
            if fid == "rome.spout":
                pts.append((ph * 5, -6 + 7 * ph * ph, (WATER[4], WATER[5], PLASTER[4])[i % 3], 0.6))
            else:
                a = rng.uniform(-1, 1)
                pts.append((a * ph * 6, -4 * ph * (1 - ph) * 10, (WATER[4], WATER[5])[i % 2], 0.6))
        return _fx(pts, (16, 14), k)
    if fid == "rome.glint":               # sun glitter on the river, sparks appearing and fading
        for i in range(7):
            x, y = rng.uniform(-14, 14), rng.uniform(-8, 0)
            if math.sin((t + rng.uniform(0, 1)) * 2 * math.pi) > 0.3:
                pts.append((x, y, (PLASTER[4], TIBER[5])[i % 2], 0.6))
        pts.append((0, 0, TIBER[4], 0.4))
        return _fx(pts, (32, 12), k)
    if fid == "rome.sparks":
        for i in range(6):
            a, ph = rng.uniform(-1, 1), (rng.uniform(0, 1) + t) % 1.0
            pts.append((a * ph * 5, -3 * ph + ph * ph * 4, (GLOW[2], GLOW[1])[i % 2], 0.5))
        return _fx(pts, (14, 10), k)
    raise KeyError(fid)


# ---------------------------------------------------------------- goods

def amphora(m, x, y, z, kind="dressel20", lying=False):
    """Roman transport amphorae by origin: the globular Dressel 20 of Baetican oil, the slender
    Dressel 2-4 of wine, the cylindrical African, the carrot-shaped Eastern."""
    from arch import ellipsoid, rod
    if kind == "dressel20":
        ellipsoid(m, (x, y, z + 3.2), (2.4, 2.4, 2.6), "clay", 0.2)
        rod(m, (x, y, z + 5.4), (x, y, z + 6.6), 0.8, "clay", 0.3)
        rod(m, (x, y, z + 0.4), (x, y, z + 1.2), 0.4, "clay", 0.0)
    elif kind == "wine":
        rod(m, (x, y, z + 1.2), (x, y, z + 6.0), 1.4, "terracotta", 0.2)
        rod(m, (x, y, z), (x, y, z + 1.4), 0.4, "terracotta", 0.0)
        rod(m, (x, y, z + 6.0), (x, y, z + 7.8), 0.6, "terracotta", 0.3)
        for s in (-1, 1):
            rod(m, (x, y + s * 0.6, z + 7.4), (x, y + s * 1.4, z + 5.8), 0.3, "terracotta", 0.2)
    elif kind == "african":
        rod(m, (x, y, z + 1.0), (x, y, z + 6.5), 1.5, "clay", 0.1)
        rod(m, (x, y, z), (x, y, z + 1.0), 0.6, "clay", 0.0)
    else:
        rod(m, (x, y, z + 0.2), (x, y, z + 6.0), 1.6, "giallo", 0.1)
        rod(m, (x, y, z + 6.0), (x, y, z + 7.0), 0.5, "giallo", 0.3)


GOODS = ("goods_oil_amphora", "goods_wine_amphora", "goods_grain_sack", "goods_bread", "goods_marble",
         "goods_bricks", "goods_cloth", "goods_fish", "goods_water_jug")


def _goods_model(name, k, n=1):
    from arch import ellipsoid, rod, slab
    m = Model.empty(-12, 12, -12, 12, 0, 16, k=k)
    offs = [(0.0, 0.0), (0.0, 5.0), (5.0, 2.5)][:n]
    for i, (ox, oy) in enumerate(offs):
        if name == "goods_oil_amphora":
            amphora(m, ox, oy, 0.0, "dressel20")
        elif name == "goods_wine_amphora":
            amphora(m, ox, oy, 0.0, "wine")
        elif name == "goods_grain_sack":
            ellipsoid(m, (ox, oy, 2.2), (2.6, 2.0, 2.2), "wool", 0.1)
            rod(m, (ox, oy - 0.8, 4.2), (ox, oy + 0.8, 4.2), 0.5, "straw", 0.2)
        elif name == "goods_bread":    # round loaves scored in eight on a board
            slab(m, ox - 3.0, ox + 3.0, oy - 2.2, oy + 2.2, 0.0, 0.6, "wood_light", 0.1)
            for j in range(3):
                ellipsoid(m, (ox - 1.6 + j * 1.6, oy + (j % 2) * 0.8 - 0.4, 1.3), (1.2, 1.2, 0.7), "ochre", 0.3)
        elif name == "goods_marble":
            slab(m, ox - 3.0, ox + 3.0, oy - 2.0, oy + 2.0, 0.0, 3.4, "marble",
                 tone=lambda X, Y, Z: 0.3 * (Z > 2.8) - 0.1)
        elif name == "goods_bricks":
            for j in range(3):
                slab(m, ox - 2.6, ox + 2.6, oy - 2.6, oy + 2.6, j * 0.9, j * 0.9 + 0.7, "brick", tone=0.1 * j)
        elif name == "goods_cloth":
            slab(m, ox - 2.6, ox + 2.6, oy - 2.0, oy + 2.0, 0.0, 2.2, ("cinnabar", "saffron", "eblue")[i % 3], 0.2)
            slab(m, ox - 2.6, ox + 2.6, oy - 2.0, oy + 2.0, 2.2, 2.7, "linen", 0.2)
        elif name == "goods_fish":
            ellipsoid(m, (ox, oy, 1.4), (2.8, 2.2, 1.2), "straw", -0.1)
            for j in range(3):
                ellipsoid(m, (ox - 1.0 + j, oy, 2.6), (1.6, 0.4, 0.4), "metal", 0.5)
        elif name == "goods_water_jug":
            ellipsoid(m, (ox, oy, 2.4), (1.7, 1.7, 2.0), "clay", 0.2)
            rod(m, (ox, oy, 4.2), (ox, oy, 5.4), 0.7, "clay", 0.3)
        else:
            raise KeyError(name)
    return m


def goods(key, k):
    m_ = re.fullmatch(r"goods/rome\.(\w+?)(?:/s(\d))?", key)
    model = _goods_model(m_[1], k, int(m_[2] or 1))
    rgba, _g, ox, oy = render_base(model)
    return Sprite(rgba, ox, oy)


# ---------------------------------------------------------------- dispatch

def build(keys, cat, k):
    out = {}
    for key in keys:
        if m := TERRAIN_KEY.fullmatch(key):
            tid, var, mask, frame = m.groups()
            if var is not None:
                out[key] = grass_spring(int(var), k)
            elif tid == "rome.river_tiber":
                out[key] = river_tiber(int(mask), int(frame), FRAMES[tid], k)
            else:
                out[key] = TERRAIN[tid](int(mask), k)
        elif m := re.fullmatch(r"edge/rome\.(tufa|brick|travertine|earth)_(se|sw)/(v(\d)|top)", key):
            out[key] = FACES[m[1]](m[2], int(m[4] or 0), k, top=m[3] == "top")
        elif m := re.fullmatch(r"fx/(rome\.\w+)/f(\d+)", key):
            out[key] = fx(m[1], int(m[2]), FRAMES[m[1]], k)
        elif key.startswith("goods/"):
            out[key] = goods(key, k)
        else:
            raise KeyError(key)
    return out


TERRAIN_CATALOG = [
    {"id": "rome.grass_spring", "name": "Spring grass", "base": True, "variants": BASE_VARIANTS,
     "faces": ["rome.earth", "rome.tufa", "rome.brick"]},
    {"id": "rome.basalt_paving", "name": "Basalt road", "under": "rome.grass_spring", "edges": 16,
     "faces": ["rome.brick", "rome.travertine"]},
    {"id": "rome.travertine_paving", "name": "Travertine paving", "under": "rome.grass_spring", "edges": 16,
     "faces": ["rome.travertine", "rome.brick"]},
    {"id": "rome.brick_ground", "name": "Brick yard", "under": "rome.grass_spring", "edges": 16,
     "faces": ["rome.brick"]},
    {"id": "rome.packed_earth", "name": "Packed earth", "under": "rome.grass_spring", "edges": 16,
     "faces": ["rome.earth"]},
    {"id": "rome.tufa_rock", "name": "Tufa rock", "under": "rome.grass_spring", "edges": 16, "faces": ["rome.tufa"]},
    {"id": "rome.field_spring", "name": "Green wheat", "under": "rome.grass_spring", "edges": 16,
     "faces": ["rome.earth"]},
    {"id": "rome.vineyard_soil", "name": "Vineyard soil", "under": "rome.grass_spring", "edges": 16,
     "faces": ["rome.earth"]},
    {"id": "rome.river_tiber", "name": "Tiber", "under": "rome.grass_spring", "edges": 16, "fps": 3,
     "faces": ["rome.travertine", "rome.earth"]},
    {"id": "rome.mud_bank", "name": "Mud bank", "under": "rome.grass_spring", "edges": 16, "faces": ["rome.earth"]},
]
EDGES = ["rome.tufa", "rome.brick", "rome.travertine", "rome.earth"]
GOODS_CATALOG = [{"id": f"rome.{g}", "name": n, "sprite": f"goods/rome.{g}", "stack": 3} for g, n in zip(GOODS, (
    "Amphora of Baetican oil", "Amphora of wine", "Sack of grain", "Loaves of bread", "Marble block", "Bricks",
    "Bolt of cloth", "Basket of fish", "Water jug"))]
