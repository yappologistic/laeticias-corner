"""Athens's flat sprites, evaluated per pixel like terrain.py: the summer ground (athens.md
§3.5), the faces under raised tiles (the Acropolis rock, squared wall masonry, earth banks;
world-tech.md §1.6), the set's effects and its carried goods."""

import math
import re

import numpy as np

import land
import terrain as home
from pack import Sprite
from palette import (ATTIC_ROCK, CINNABAR, CLAY, EARTH, GLOSS, GLOW, INK, LEAF, MARBLE, OLIVE, PLASTER, POROS, RUST,
                     STONE, STRAW, SUMMER, WATER)
from render import render_sprite
from sets.parsa.ground import _fx, _overlay
from voxel import Model, hash01

FRAMES = {"athens.altar_fire": 6, "athens.fire": 6, "athens.torch_flame": 6, "athens.altar_smoke": 6,
          "athens.marble_dust": 6, "athens.spout": 4, "athens.ripple": 4, "athens.sea_glint": 4, "athens.cicada": 4,
          "athens.sparks": 4}

TERRAIN_KEY = re.compile(r"terrain/(athens\.\w+)/(?:v(\d+)|m(\d+)(?:/v(\d+))?/f(\d+))")
DRY = [LEAF[1], OLIVE[1], SUMMER[0], SUMMER[1], SUMMER[2], SUMMER[3]]
ROCK = [INK, *ATTIC_ROCK]


def dry_grass(v, k):
    """The summer ground: gold-green grass burnt dry, darker tufts, grey thyme cushions, pale
    stones and bare earth showing in patches (four variants)."""
    g = home._grid(k)
    n = home._pnoise(g.u, g.v, 4, 1201 + v)
    fine = home._pnoise(g.u, g.v, 16, 1202 + v)
    lvl = 2.6 + (n - 0.5) * 1.6 + (fine - 0.5) * 0.8 + (hash01(g.px, g.py, 1203 + v) - 0.5) * 0.9
    rgb = home._paint(DRY, lvl, g.px, g.py, k=k)
    dx, dy, h, ok = home._scatter(g, 3, 1204 + v, 0.35)
    tuft = ok & (dx * dx + 3 * dy * dy < (0.8 + h) ** 2 * k * k)
    rgb = np.where(tuft[..., None], home._paint([LEAF[0], OLIVE[0], OLIVE[1], OLIVE[2]], 1.6 - dy / max(k, 1) * 0.6,
                                                 g.px, g.py, k=k), rgb)
    dx, dy, h, ok = home._scatter(g, 4, 1205 + v, 0.18)
    stone = ok & (dx * dx + 2.5 * dy * dy < (0.6 + h) ** 2 * k * k)
    rgb = np.where(stone[..., None], home._paint([STONE[2], POROS[2], POROS[3], MARBLE[4]], 2.0 - dy / max(k, 1) * 0.7,
                                                  g.px, g.py, k=k), rgb)
    earth = (n < 0.3) & (fine > 0.45)
    rgb = np.where(earth[..., None], home._paint([EARTH[1], EARTH[2], RUST[0], EARTH[3]], 2.0 + fine, g.px, g.py, k=k), rgb)
    return home._sprite(g, rgb, g.inside * 255)


def rock_limestone(mask, k, look=0):
    """The Acropolis and hill limestone: blue-grey bedrock with rusty stains, cracks and pits,
    tufts of dry grass in the joints."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 6, 1211)
        crack = np.abs(home._pnoise(g.u, g.v, 5, 1212) - 0.5) < 0.02
        lvl = 3.2 + (n - 0.5) * 0.9 - crack * 1.1 - np.clip(1.0 - f, 0, 1) * 0.8 + (hash01(g.px, g.py, 1213) - 0.5) * 0.7
        rgb = home._paint(ROCK, lvl, g.px, g.py, k=k)
        stain = (home._pnoise(g.u, g.v, 3, 1214) > 0.8) & (hash01(g.px, g.py, 1215) < 0.5)
        return np.where(stain[..., None], home._paint([RUST[0], RUST[1], CLAY[2]], 1.4 + n, g.px, g.py, k=k), rgb)
    return _overlay(mask, k, 0.8, 3.0, 0.7, 1210, paint, look)


def marble_paving(mask, k):
    """Marble paving of temple platforms and courts: big slabs, each its own warm tone, fine
    joints with a lit edge, the odd darker slab, polish where feet pass."""
    def paint(g, f):
        u, v = g.u, g.v
        row = np.floor(v / 8.0)
        a = (u + (row % 2) * 8.0) % 16.0
        joint = ((v % 8.0) < 0.42) | (a < 0.42)
        h = hash01(row.astype(np.int64) % 2, (a >= 8).astype(np.int64), 1221)
        lvl = 4.2 + (h - 0.5) * 0.9 + (home._pnoise(u, v, 8, 1222) - 0.5) * 0.4 - joint * 1.4 - np.clip(1 - f, 0, 1)
        return home._paint(MARBLE, lvl, g.px, g.py, band=0.4, k=k)
    return _overlay(mask, k, 0.6, 2.0, 0.2, 1220, paint)


def gravel(mask, k, look=0):
    """The Panathenaic Way and the Agora: trodden gravel, grey and buff pebbles, dust."""
    def paint(g, f):
        lvl = 2.8 + (hash01(g.px, g.py, 1231) - 0.5) * 1.8 + (home._pnoise(g.u, g.v, 6, 1232) - 0.5) * 0.7
        return home._paint([STONE[2], POROS[1], POROS[2], STONE[3], POROS[3], MARBLE[4]], lvl - np.clip(1 - f, 0, 1),
                           g.px, g.py, k=k)
    return _overlay(mask, k, 1.0, 4.0, 0.6, 1230, paint, look)


def packed_earth(mask, k, look=0):
    return home.path(mask, k, look=look)


def field_stubble(mask, k):
    """A barley field after the harvest: rows of gold stubble over pale dry earth."""
    def paint(g, f):
        row = ((g.u * 1.0) % 2.0) < 1.1
        lvl = np.where(row, 3.0 + (home._pnoise(g.u, g.v, 8, 1241) - 0.5) * 1.2 + (hash01(g.px, g.py, 1242) - 0.5),
                       1.6)
        stub = home._paint([STRAW[0], STRAW[1], STRAW[2], STRAW[3]], lvl - 0.8, g.px, g.py, k=k)
        soil = home._paint([EARTH[1], EARTH[2], EARTH[3], EARTH[4]], np.full_like(lvl, 2.2), g.px, g.py, k=k)
        return np.where(row[..., None], stub, soil)
    return _overlay(mask, k, 1.0, 3.0, 0.5, 1240, paint)


def olive_soil(mask, k, look=0):
    """The red-brown ploughed earth under the olive groves, clods and fallen leaves."""
    def paint(g, f):
        n = home._pnoise(g.u, g.v, 8, 1251)
        lvl = 2.4 + (n - 0.5) * 1.2 + (hash01(g.px, g.py, 1252) - 0.5) * 1.0 - np.clip(1 - f, 0, 1)
        rgb = home._paint([EARTH[0], RUST[0], EARTH[2], RUST[1], CLAY[2]], lvl, g.px, g.py, k=k)
        leaf = hash01(g.px, g.py, 1253) < 0.02
        return np.where(leaf[..., None], home._paint(OLIVE, np.full_like(lvl, 3.0), g.px, g.py, k=k), rgb)
    return _overlay(mask, k, 1.0, 4.0, 0.7, 1250, paint, look)


def riverbed(mask, k, look=0):
    """The Ilissos in summer: a bed of pale stones and sand with a thin stream of water."""
    def paint(g, f):
        lvl = 3.0 + (hash01(g.px // 2, g.py // 2, 1261) - 0.5) * 1.6
        rgb = home._paint([STONE[1], STONE[2], POROS[2], STONE[4], MARBLE[4]], lvl, g.px, g.py, k=k)
        stream = f > 2.4
        water = home._paint(WATER[1:5], 2.0 + (home._pnoise(g.u, g.v, 8, 1262) - 0.5) * 1.6, g.px, g.py, k=k)
        return np.where(stream[..., None], water, rgb)
    return _overlay(mask, k, 1.0, 4.0, 0.8, 1260, paint, look)


# Natural overlays with interior looks (terrain.SHIFTS): a field of them has no one-tile rhythm.
INTERIOR = {"athens.rock_limestone": 4, "athens.packed_earth": 4, "athens.gravel": 4, "athens.olive_soil": 4,
            "athens.riverbed": 4}
TERRAIN = {"athens.rock_limestone": rock_limestone, "athens.marble_paving": marble_paving, "athens.gravel": gravel,
           "athens.packed_earth": packed_earth, "athens.field_stubble": field_stubble, "athens.olive_soil": olive_soil,
           "athens.riverbed": riverbed}


# ---------------------------------------------------------------- faces

def _face_sprite(rgb, alpha, H, W, ox, oy):
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha * 255
    return Sprite(rgba, ox, oy)


def ashlar_face(side, v, k, top=False):
    """One level of squared wall masonry (the Kimonian wall on the Acropolis, terrace walls):
    isodomic courses of poros and limestone blocks, each its own tone, a joint at every tile
    edge so variants meet; the top band is a plain coping course."""
    above = 3 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = land.face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    on = (d >= (-above if top else 0)) & (d < band)
    course = np.floor(d / (4 * k)).astype(np.int64)
    off = np.where(course % 2 == 0, 0, W // 2)
    a = (s + off) % W
    cut = W // 2
    joint = ((d % (4 * k)) < 1) | (a < 1) | (np.abs(a - cut) < 1)
    blk = (a >= cut).astype(np.int64)
    lvl = 3.2 + shade + (hash01(course, blk, v, 1311) - 0.5) * 1.0 + (hash01(px, py, 1312) - 0.5) * 0.35 - 1.5 * joint
    lvl = lvl + 0.5 * ((d % (4 * k)) == 1)
    lvl = np.where(d < 0, 4.0 + shade, lvl)
    rgb = home._paint([INK, *POROS, MARBLE[4]], lvl, px, py, k=k)
    return _face_sprite(rgb, on, H, W, ox, oy)


FACES = {"ashlar": ashlar_face}
# The natural faces (land.py): the Acropolis rock, the hills' limestone and earth banks.
NATURAL = {
    "limestone": land.Stone("rock", tuple(ROCK), tuple(DRY), 1301, stain=(RUST[0], ATTIC_ROCK[1], ATTIC_ROCK[2]),
                            shrub=(OLIVE[0], OLIVE[1], LEAF[2], OLIVE[2]), cell=6),
    "earth": land.Stone("earth", (INK, EARTH[0], EARTH[1], CLAY[0], EARTH[2], CLAY[1], EARTH[3]), tuple(DRY), 1321,
                        stones=(ATTIC_ROCK[1], ATTIC_ROCK[2], ATTIC_ROCK[3], ATTIC_ROCK[4]), cell=3),
}


# ---------------------------------------------------------------- effects

def fx(fid, f, n, k):
    rng = np.random.Generator(np.random.PCG64([sum(map(ord, fid)), 3]))
    pts = []
    t = f / n
    if fid in ("athens.altar_fire", "athens.fire", "athens.torch_flame"):
        s = {"athens.altar_fire": 1.4, "athens.fire": 1.0, "athens.torch_flame": 0.6}[fid]
        for i in range(12):
            h, a = rng.uniform(0, 1), rng.uniform(-1, 1)
            ph = (h + t) % 1.0
            col = (GLOW[2], GLOW[1], GLOW[0], CINNABAR[3])[min(3, int(ph * 4))]
            pts.append((a * (1 - ph) * 3 * s, -ph * 10 * s, col, (1.6 - ph) * s))
        return _fx(pts, (16, 18), k)
    if fid == "athens.altar_smoke":     # thick grey-brown smoke of burnt fat rising and leaning
        for i in range(16):
            h = ((i / 16) + t) % 1.0
            pts.append((h * h * 8 + math.sin(h * 6 + 1) * 1.5, -h * 34, (STONE[2], STONE[3], PLASTER[1])[i % 3],
                        1.0 + h * 2.4))
        return _fx(pts, (28, 40), k)
    if fid == "athens.marble_dust":
        for i in range(12):
            x0, y0 = rng.uniform(-7, 7), rng.uniform(-6, 0)
            pts.append((x0 + t * rng.uniform(-3, 3), y0 - t * 7, (MARBLE[5], MARBLE[4], PLASTER[3])[i % 3], 0.6))
        return _fx(pts, (22, 18), k)
    if fid == "athens.spout":           # water arching from a lion's mouth into the basin
        for i in range(8):
            ph = ((i / 8) + t) % 1.0
            pts.append((ph * 5, -6 + 7 * ph * ph, (WATER[4], WATER[5], PLASTER[4])[i % 3], 0.6))
        return _fx(pts, (14, 12), k)
    if fid == "athens.ripple":
        r = 2 + 6 * t
        for a in np.linspace(0, 2 * math.pi, 18, endpoint=False):
            pts.append((math.cos(a) * r, math.sin(a) * r * 0.5 - 2, WATER[5], 0.5))
        return _fx(pts, (20, 10), k)
    if fid == "athens.sea_glint":       # sun glitter on the sea: sparks appearing and fading
        for i in range(7):
            x, y = rng.uniform(-14, 14), rng.uniform(-8, 0)
            on = math.sin((t + rng.uniform(0, 1)) * 2 * math.pi) > 0.3
            if on:
                pts.append((x, y, (PLASTER[4], WATER[5])[i % 2], 0.6))
        pts.append((0, 0, WATER[4], 0.4))
        return _fx(pts, (32, 12), k)
    if fid == "athens.cicada":          # a cicada on a trunk, wings quivering
        w = 0.6 + 0.4 * (f % 2)
        pts = [(0, -2, GLOSS[2], 0.8), (0, -3, OLIVE[1], 0.6), (w, -2, PLASTER[3], 0.5), (-w, -2, PLASTER[3], 0.5)]
        return _fx(pts, (6, 6), k)
    if fid == "athens.sparks":
        for i in range(6):
            a, ph = rng.uniform(-1, 1), (rng.uniform(0, 1) + t) % 1.0
            pts.append((a * ph * 5, -3 * ph + ph * ph * 4, (GLOW[2], GLOW[1])[i % 2], 0.5))
        return _fx(pts, (14, 10), k)
    raise KeyError(fid)


# ---------------------------------------------------------------- goods

def _goods_model(name, k, n=1):
    from greek import vase
    from arch import ellipsoid, slab
    m = Model.empty(-12, 12, -12, 12, 0, 16, k=k)
    offs = [(0.0, 0.0), (0.0, 5.0), (5.0, 2.5)][:n]
    for i, (ox, oy) in enumerate(offs):
        if name == "goods_hydria":
            vase(m, ox, oy, 0.0, 6.0, "hydria", figure="redfigure")
        elif name == "goods_prize_amphora":     # the Panathenaic prize amphora, black-figure Athena
            vase(m, ox, oy, 0.0, 7.0, "amphora", figure="blackfigure")
        elif name == "goods_redfigure":
            vase(m, ox, oy, 0.0, 5.0, ("krater", "amphora", "lekythos")[i % 3], figure="redfigure")
        elif name == "goods_kanoun":
            ellipsoid(m, (ox, oy, 1.0), (3.0, 3.0, 1.0), "gold", tone=0.3)
            ellipsoid(m, (ox, oy, 1.8), (2.0, 2.0, 0.6), "straw", tone=0.2)
        elif name == "goods_charcoal":
            ellipsoid(m, (ox, oy, 2.0), (2.8, 2.2, 2.0), "straw", tone=-0.2)
            ellipsoid(m, (ox, oy, 3.6), (2.0, 1.6, 0.8), "ink", tone=0.3)
        elif name == "goods_shield":
            for j in range(1 if n == 1 else 2):
                slab(m, ox - 0.5 + j, ox + 0.5 + j, oy - 3.4, oy + 3.4, 0.0, 6.8, "bronze_cast", tone=0.3)
                ellipsoid(m, (ox + j + 0.6, oy, 3.4), (0.4, 1.6, 1.6), "cinnabar", tone=0.2)
        elif name == "goods_peplos":            # Athena's new robe, saffron with woven purple
            slab(m, ox - 3.0, ox + 3.0, oy - 2.0, oy + 2.0, 0.0, 2.4, "saffron", tone=0.2)
            slab(m, ox - 3.0, ox + 3.0, oy - 2.0, oy + 2.0, 2.4, 2.9, "purple", tone=0.2)
        else:
            raise KeyError(name)
    return m


def goods(key, k):
    m_ = re.fullmatch(r"goods/athens\.(\w+?)(?:/s(\d))?", key)
    model = _goods_model(m_[1], k, int(m_[2] or 1))
    return render_sprite(model)


# ---------------------------------------------------------------- dispatch

def build(keys, cat, k):
    out = {}
    for key in keys:
        if m := TERRAIN_KEY.fullmatch(key):
            tid, var, mask, look, frame = m.groups()
            if var is not None:
                out[key] = dry_grass(int(var), k)
            else:
                out[key] = TERRAIN[tid](int(mask), k, *(() if look is None else (int(look),)))
        elif m := re.fullmatch(r"edge/athens\.(limestone|ashlar|earth)_(se|sw)/(?:w(\d)/)?(v(\d)|top)", key):
            if m[1] in NATURAL:
                out[key] = land.face(NATURAL[m[1]], m[2], int(m[5] or 0), k, top=m[4] == "top",
                                     wedge=None if m[3] is None else int(m[3]))
            else:
                out[key] = FACES[m[1]](m[2], int(m[5] or 0), k, top=m[4] == "top")
        elif m := re.fullmatch(r"fx/(athens\.\w+)/f(\d+)", key):
            out[key] = fx(m[1], int(m[2]), FRAMES[m[1]], k)
        elif key.startswith("goods/"):
            out[key] = goods(key, k)
        else:
            raise KeyError(key)
    return out
