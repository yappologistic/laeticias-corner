"""Pārsa's flat sprites, evaluated per pixel like terrain.py: ground tiles (persepolis.md §3.5),
the terrace's ashlar faces and merlon band (world-tech.md §1.6), the Kuh-e Raḥmat backdrop
strip and the set's effects."""

import math
import re

import numpy as np

import terrain as home
from pack import Sprite
from palette import (CINNABAR, EARTH, GLOW, HEMATITE, INK, LAPIS, LEAF, LIMESTONE, MUDBRICK, NAQSH,
                     PLASTER, SNOW, STONE, WATER, _rgb)
from render import dither
from validate import diamond
from voxel import hash01, value_noise

FRAMES = {"parsa.water_channel": 4, "parsa.incense": 6, "parsa.fire": 6, "parsa.torch_flame": 6,
          "parsa.chisel_dust": 6, "parsa.petals": 6, "parsa.spray": 4, "parsa.dust": 6, "parsa.sparks": 4}

TERRAIN_KEY = re.compile(r"terrain/(parsa\.\w+)/(?:v(\d+)|m(\d+)/f(\d+))")
SPRING = [LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]]
LIME = LIMESTONE[1:6]


def _overlay(mask, k, inset, radius, wobble, seed, paint):
    g = home._grid(k)
    f = home.shape_field(mask, g.u, g.v, inset, radius, wobble, seed, k)
    cover = g.inside & (f > 0)
    rgb = paint(g, f)
    return home._sprite(g, rgb, cover * 255)


def plain_grass(v, k):
    """The spring plain: the home lawn with its spring flowers, so both sets share one green."""
    return home.grass(v, k, "spring")


def field_barley(mask, k):
    """Rows of young barley, bright green over dark earth, running along u."""
    def paint(g, f):
        row = ((g.u * 1.0) % 2.0) < 1.15
        lvl = np.where(row, 2.6 + (home._pnoise(g.u, g.v, 8, 701) - 0.5) * 1.2, 1.2)
        rgb = home._paint(SPRING, lvl, g.px, g.py, k=k)
        soil = home._paint([INK, EARTH[0], EARTH[1], EARTH[2]], np.full_like(lvl, 2.0), g.px, g.py, k=k)
        return np.where(row[..., None], rgb, soil)
    return _overlay(mask, k, 1.0, 3.0, 0.5, 700, paint)


def garden_bed(mask, k):
    def paint(g, f):
        furrow = ((g.v * 0.8) % 2.0) < 0.6
        lvl = 2.0 + (home._pnoise(g.u, g.v, 6, 711) - 0.5) * 1.2 - furrow * 0.9 - np.clip(1.2 - f, 0, 1) * 0.8
        return home._paint([INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3]], lvl, g.px, g.py, k=k)
    return _overlay(mask, k, 1.4, 4.0, 0.5, 710, paint)


def packed_earth(mask, k):
    return home.path(mask, k)


def paving_stone(mask, k):
    """Large grey limestone slabs, fitted, with fine joints (terrace courts)."""
    def paint(g, f):
        u, v = g.u, g.v
        row = np.floor(v / 5.33)
        off = (row % 2) * 2.7
        col = np.floor((u + off) / 8.0)
        joint = ((v % 5.33) < 0.45) | (((u + off) % 8.0) < 0.45)
        h = hash01(row.astype(np.int64) % 3, col.astype(np.int64) % 2, 721)
        lvl = 2.8 + (h - 0.5) * 0.8 + (home._pnoise(u, v, 4, 722) - 0.5) * 0.6 - joint * 1.4 - np.clip(1.0 - f, 0, 1)
        return home._paint(LIME, lvl, g.px, g.py, band=0.4, k=k)
    return _overlay(mask, k, 0.6, 2.0, 0.2, 720, paint)


def paving_red(mask, k):
    """Floors plastered and painted dark red with hematite (inside porticoes and halls)."""
    def paint(g, f):
        lvl = 2.2 + (home._pnoise(g.u, g.v, 3, 731) - 0.5) * 0.7 - np.clip(0.8 - f, 0, 1) * 1.2
        crack = (np.abs(home._pnoise(g.u, g.v, 5, 732) - 0.5) < 0.012)
        lvl = lvl - crack * 0.8
        return home._paint([INK, *HEMATITE, CINNABAR[2]], lvl, g.px, g.py, band=0.4, k=k)
    return _overlay(mask, k, 0.5, 2.0, 0.2, 730, paint)


def gravel(mask, k):
    def paint(g, f):
        lvl = 2.6 + (hash01(g.px, g.py, 741) - 0.5) * 1.6 + (home._pnoise(g.u, g.v, 6, 742) - 0.5) * 0.6
        return home._paint([STONE[2], *MUDBRICK[1:5]], lvl - np.clip(1.0 - f, 0, 1), g.px, g.py, k=k)
    return _overlay(mask, k, 1.2, 4.0, 0.6, 740, paint)


def water_channel(mask, frame, frames, k):
    return home.water(mask, frame, frames, k)


def rough_ground(mask, k):
    """Stony rough ground with grey tufts: the bands separating satellites from the city."""
    def paint(g, f):
        lvl = 2.2 + (home._pnoise(g.u, g.v, 8, 751) - 0.5) * 1.4
        dx, dy, h, ok = home._scatter(g, 2, 752, 0.35)
        stone = ok & (dx * dx + 3 * dy * dy < (1.2 + h * 1.8) ** 2 * k * k)
        rgb = home._paint([EARTH[1], EARTH[2], MUDBRICK[1], MUDBRICK[2], MUDBRICK[3]], lvl, g.px, g.py, k=k)
        srgb = home._paint([STONE[1], STONE[2], STONE[3], STONE[4]], 2.0 - dy / max(k, 1) * 0.8, g.px, g.py, k=k)
        return np.where(stone[..., None], srgb, rgb)
    return _overlay(mask, k, 1.0, 4.0, 0.8, 750, paint)


TERRAIN = {"parsa.field_barley": field_barley, "parsa.garden_bed": garden_bed, "parsa.packed_earth": packed_earth,
           "parsa.paving_stone": paving_stone, "parsa.paving_red": paving_red, "parsa.gravel": gravel,
           "parsa.rough_ground": rough_ground}


# ---------------------------------------------------------------- terrace faces

ASHLAR = [INK, *LIMESTONE[:6]]


def _face_columns(k, side):
    """Screen columns of one level of face under a tile edge: x relative to the anchor (the
    tile's top vertex) and the first row of face below the ground diamond's lower edge."""
    want = diamond(32 * k)
    h, w = want.shape
    rows = np.arange(h)[:, None]
    bottom = np.where(want, rows, -1).max(axis=0)            # per diamond column
    xs = np.arange(w) - (16 * k - 1)                         # x of each diamond column
    keep = xs >= 0 if side == "se" else xs < 0
    return xs[keep], bottom[keep] + 1


def ashlar_face(side, v, k, top=False):
    """One level (16 px at 64x32) of the terrace face: fitted grey limestone in two courses of
    big blocks, joints skewed as in the polygonal-to-rectangular masonry of the terrace, a
    vertical joint at each tile edge so neighbouring variants always meet. `top` adds the kerb
    and the stepped-merlon parapet standing above the rim."""
    xs, first = _face_columns(k, side)
    band = 8 * k                                            # 16 px at 64x32
    above = 7 * k if top else 0
    H = 16 * k + above
    W = 16 * k
    rgba = np.zeros((H, W, 4), np.uint8)
    x0 = 0 if side == "se" else -16 * k
    shade = -0.9 if side == "se" else 0.0
    for x, f in zip(xs, first):
        col = x - x0
        if not 0 <= col < W:
            continue
        s = x if side == "se" else -x                       # distance along the face from the bottom vertex
        for d in range(band):
            y = f + d + above - 8 * k
            course = d // (4 * k)
            dd = d % (4 * k)
            skew = int((hash01(course, v, 801) - 0.5) * 6 * k * (dd / (4 * k)))
            seg_len = 16 * k
            a = (s + skew + course * 5 * k + v * 3 * k) % seg_len
            cut = int(hash01(course, v, 802) * 8 * k) + 4 * k
            joint = (dd == 0) or (a < 1) or (abs(a - cut) < 1) or (s == 0) or (s == 16 * k - 1)
            blk = int(a > cut)
            lvl = 3.0 + shade + (hash01(course, blk, v, 803) - 0.5) * 1.0 + (hash01(x, y, 804) - 0.5) * 0.35
            lvl -= 1.6 * joint
            lvl += 0.6 * (dd == 1)
            idx = int(np.clip(dither(np.array([lvl]), np.array([col]), np.array([y]))[0], 0, len(ASHLAR) - 1))
            if 0 <= y < H:
                rgba[y, col, :3] = _rgb(ASHLAR[idx])
                rgba[y, col, 3] = 255
        if top:
            # Kerb along the rim and stepped merlons rising above it.
            yr = f + above - 8 * k
            for d in range(-above, 2 * k):
                y = yr + d
                if not 0 <= y < H:
                    continue
                if d < 0:
                    u = (s % (6 * k)) / (6 * k)
                    tooth = (1 - abs(u - 0.5) * 2)
                    step = math.floor(tooth * 4) / 3.0
                    hgt = min(1.0, step) * above
                    if -d > hgt:
                        continue
                    lvl = 3.4 + shade + (0.6 if -d > hgt - k else 0.0)
                else:
                    lvl = 4.0 + shade
                idx = int(np.clip(round(lvl), 0, len(ASHLAR) - 1))
                rgba[y, col, :3] = _rgb(ASHLAR[idx])
                rgba[y, col, 3] = 255
    # Anchor: the tile's top vertex, which lies above the sprite (oy < 0) unless merlons rise.
    ox = -x0
    oy = above - 8 * k
    return Sprite(rgba, ox, oy)


# ---------------------------------------------------------------- backdrop

def kuh_rahmat(v, night, k):
    """A segment of the Kuh-e Raḥmat strip behind the east world edge: bare grey-brown rock,
    spring snow streaks high up, paler with height (aerial perspective). Segments join: the
    ridge height at both ends is the same for every variant."""
    W, Hmax = 256 * k, 192 * k
    H = Hmax + 128 * k
    py, px = np.mgrid[0:H, 0:W]
    base_y = Hmax + px / 2.0                    # the edge line, sloping down to the right
    t = px / W
    end = 0.72 * Hmax
    zeros = np.zeros_like(px, dtype=float)
    mid = (value_noise(px / k + v * 977.0, zeros, zeros, 60.0, 811) - 0.5) * 0.5 * Hmax
    ridge = end + mid * np.sin(np.pi * t) + 0.2 * Hmax * np.sin(np.pi * t) ** 2 + \
        (value_noise(px / k, zeros, zeros, 9.0, 813 + v) - 0.5) * 0.06 * Hmax * np.sin(np.pi * t)
    ridge = np.minimum(ridge, Hmax - 2)
    height = base_y - py                        # pixels above the edge line
    inside = (height >= 0) & (height < ridge)
    rel = np.clip(height / Hmax, 0, 1)          # absolute height decides snow, not the local ridge
    top = np.clip(height / np.maximum(ridge, 1), 0, 1)
    # Erosion gullies run down the slope (stretched vertically), spurs between them catch the
    # light from the upper left; bare grey-brown rock grows paler with height.
    gully = value_noise(px / k * 2.2 + py / k * 0.35, py / k * 0.22, zeros, 7.0, 815)
    spur = value_noise(px / k * 0.8, py / k * 0.5, zeros, 26.0, 817)
    lvl = 1.8 + rel * 1.5 + (spur - 0.5) * 1.4 + (gully - 0.5) * 1.6 - (gully < 0.3) * 0.8
    rock = [NAQSH[0], STONE[1], NAQSH[1], STONE[2], NAQSH[2], STONE[3], PLASTER[1]]
    snow = (rel > 0.7) & (gully > 0.74 - (rel - 0.7) * 1.4) & (top > 0.6)
    rgb = home._paint(rock, lvl, px, py, k=k)
    rgb = np.where(snow[..., None], home._paint([SNOW[0], SNOW[1], SNOW[2]], 1.0 + spur * 1.4, px, py, k=k), rgb)
    if night:
        rgb = home._paint([INK, STONE[0], LAPIS[0], STONE[1], STONE[2]], 0.6 + rel * 1.4 + (gully - 0.5) + snow * 1.6,
                          px, py, k=k)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = inside * 255
    return Sprite(rgba, 0, Hmax)


# ---------------------------------------------------------------- effects

def _fx(points, size, k):
    """Draw [(x, y, rgb, r)] marks (px, anchor at the ground point) into a small sprite."""
    W, H = size
    rgba = np.zeros((H * k, W * k, 4), np.uint8)
    ox, oy = W * k // 2, H * k - 1
    for x, y, col, r in points:
        cx, cy = ox + x * k, oy + y * k
        rr = max(1, int(round(r * k)))
        for yy in range(int(cy) - rr + 1, int(cy) + rr):
            for xx in range(int(cx) - rr + 1, int(cx) + rr):
                if 0 <= xx < W * k and 0 <= yy < H * k and (xx - cx) ** 2 + (yy - cy) ** 2 < rr * rr:
                    rgba[yy, xx, :3] = _rgb(col)
                    rgba[yy, xx, 3] = 255
    return Sprite(rgba, ox, oy)


def fx(fid, f, n, k):
    rng = np.random.Generator(np.random.PCG64([sum(map(ord, fid)), 3]))
    pts = []
    t = f / n
    if fid == "parsa.incense":          # a thin blue-grey thread of smoke curling upward
        for i in range(14):
            h = ((i / 14) + t) % 1.0
            pts.append((math.sin(h * 7 + 1.3) * (1 + h * 4), -h * 26, (STONE[3], STONE[4], PLASTER[2])[i % 3],
                        0.6 + h * 1.1))
        return _fx(pts, (16, 30), k)
    if fid in ("parsa.fire", "parsa.torch_flame"):
        s = 1.0 if fid == "parsa.fire" else 0.6
        for i in range(10):
            h = rng.uniform(0, 1)
            a = rng.uniform(-1, 1)
            ph = (h + t) % 1.0
            col = (GLOW[2], GLOW[1], GLOW[0], CINNABAR[3])[min(3, int(ph * 4))]
            pts.append((a * (1 - ph) * 3 * s, -ph * 10 * s, col, (1.6 - ph) * s))
        return _fx(pts, (12, 14), k)
    if fid in ("parsa.chisel_dust", "parsa.dust"):
        col = (PLASTER[3], PLASTER[2]) if fid == "parsa.chisel_dust" else (MUDBRICK[3], MUDBRICK[2])
        for i in range(10):
            x0, y0 = rng.uniform(-6, 6), rng.uniform(-6, 0)
            pts.append((x0 + t * rng.uniform(-3, 3), y0 - t * 6, col[i % 2], 0.6))
        return _fx(pts, (20, 16), k)
    if fid == "parsa.petals":
        for i in range(6):
            x0, y0 = rng.uniform(-8, 8), rng.uniform(-14, -6)
            pts.append((x0 + math.sin(t * 6.28 + i) * 2, y0 + t * 10, ("#f6c9c8", "#fbf5e4")[i % 2], 0.6))
        return _fx(pts, (22, 20), k)
    if fid == "parsa.spray":
        for i in range(8):
            a = rng.uniform(-1, 1)
            ph = (rng.uniform(0, 1) + t) % 1.0
            pts.append((a * ph * 6, -4 * ph * (1 - ph) * 8, (WATER[4], WATER[5])[i % 2], 0.6))
        return _fx(pts, (16, 12), k)
    if fid == "parsa.sparks":
        for i in range(6):
            a = rng.uniform(-1, 1)
            ph = (rng.uniform(0, 1) + t) % 1.0
            pts.append((a * ph * 5, -3 * ph + ph * ph * 4, (GLOW[2], GLOW[1])[i % 2], 0.5))
        return _fx(pts, (14, 10), k)
    raise KeyError(fid)


# ---------------------------------------------------------------- dispatch

def build(keys, cat, k):
    out = {}
    for key in keys:
        if m := TERRAIN_KEY.fullmatch(key):
            tid, var, mask, frame = m.groups()
            if var is not None:
                out[key] = plain_grass(int(var), k)
            elif tid == "parsa.water_channel":
                out[key] = water_channel(int(mask), int(frame), FRAMES[tid], k)
            else:
                out[key] = TERRAIN[tid](int(mask), k)
        elif m := re.fullmatch(r"edge/parsa\.ashlar_(se|sw)/(v(\d)|top)", key):
            out[key] = ashlar_face(m[1], int(m[3] or 0), k, top=m[2] == "top")
        elif m := re.fullmatch(r"backdrop/parsa\.kuh_rahmat/(day|night)/v(\d)", key):
            out[key] = kuh_rahmat(int(m[2]), m[1] == "night", k)
        elif m := re.fullmatch(r"fx/(parsa\.\w+)/f(\d+)", key):
            out[key] = fx(m[1], int(m[2]), FRAMES[m[1]], k)
        else:
            raise KeyError(key)
    return out
