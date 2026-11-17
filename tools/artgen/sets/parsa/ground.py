"""Pārsa's flat sprites, evaluated per pixel like terrain.py: ground tiles (persepolis.md §3.5),
the terrace's ashlar faces and merlon band (world-tech.md §1.6), the Kuh-e Raḥmat backdrop
strip and the set's effects."""

import math
import re

import numpy as np

import terrain as home
from pack import Sprite
from palette import (CINNABAR, EARTH, GLOW, HEMATITE, INK, LAPIS, LEAF, LIMESTONE, MUDBRICK, NAQSH, PINE,
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
    """A planted bed of the paradise: rows of herbs and spring flowers (tulips, lilies,
    roses) over dark watered soil, the rows running along v."""
    def paint(g, f):
        row = ((g.v * 0.5) % 2.0) < 1.25
        n = home._pnoise(g.u, g.v, 8, 712)
        leaf = row & (hash01(g.px, g.py, 713) < 0.78)
        lvl = 2.4 + (n - 0.5) * 1.4 + (hash01(g.px // 2, g.py, 714) - 0.5) * 0.8
        green = home._paint(SPRING, lvl, g.px, g.py, k=k)
        soil = home._paint([INK, EARTH[0], EARTH[1], EARTH[2]], 1.8 + (n - 0.5) - np.clip(1.2 - f, 0, 1) * 0.8,
                           g.px, g.py, k=k)
        rgb = np.where(leaf[..., None], green, soil)
        bloom = row & (hash01(g.px // 2, g.py // 2, 715) < 0.07)
        colour = hash01(g.px // 2, g.py // 2, 716)
        petals = np.where((colour < 0.4)[..., None], np.array(_rgb(CINNABAR[2]), np.uint8),
                          np.where((colour < 0.7)[..., None], np.array(_rgb(PLASTER[4]), np.uint8),
                                   np.array(_rgb("#e597a6"), np.uint8)))
        return np.where(bloom[..., None], petals, rgb)
    return _overlay(mask, k, 1.4, 4.0, 0.5, 710, paint)


def packed_earth(mask, k):
    return home.path(mask, k)


def paving_stone(mask, k):
    """The terrace courts: big fitted slabs of warm grey limestone in courses two to a tile
    edge, lengths alternating, each slab its own tone, hairline joints with a lit edge, the
    odd cracked or stained slab, and soft lighter patches where feet have polished them."""
    def paint(g, f):
        u, v = g.u, g.v
        row = np.floor(v / 8.0)
        off = (row % 2) * 6.0
        a = (u + off) % 16.0
        cut = np.where(row % 2 == 0, 10.0, 6.0)
        col = (a >= cut).astype(np.int64)
        su = np.where(col == 0, a, a - cut)
        joint = ((v % 8.0) < 0.42) | (su < 0.42)
        lip = ((v % 8.0) > 0.42) & ((v % 8.0) < 0.95) | ((su > 0.42) & (su < 0.95))
        h = hash01(row.astype(np.int64) % 2, col, 721)
        crack = (h > 0.82) & (np.abs((su - (v % 8.0) * 0.9) - 2.5) < 0.25)
        worn = home._pnoise(u, v, 2, 723)
        lvl = (3.0 + (h - 0.5) * 1.1 + (home._pnoise(u, v, 8, 722) - 0.5) * 0.45 + (worn > 0.62) * 0.35
               - joint * 1.3 + lip * 0.3 - crack * 0.9 - np.clip(1.0 - f, 0, 1))
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


ROCK = [INK, LIMESTONE[1], LIMESTONE[2], NAQSH[1], LIMESTONE[3], LIMESTONE[4], LIMESTONE[5]]
EARTH_FACE = [INK, EARTH[0], EARTH[1], EARTH[2], MUDBRICK[1], MUDBRICK[2], MUDBRICK[3]]
SHRUB = [LEAF[0], LEAF[1], LEAF[2], LEAF[3]]


def _face_grid(side, k, above):
    """Pixel grid of one level of face: for each pixel its distance along the face from the
    bottom vertex `s` (px), its row inside the band `d` (0 at the rim) and whether it is on
    the face; plus the sprite size and anchor."""
    xs, first = _face_columns(k, side)
    band = 8 * k
    H, W = 16 * k + above, 16 * k
    x0 = 0 if side == "se" else -16 * k
    py, px = np.mgrid[0:H, 0:W]
    s = np.zeros((H, W)); d = np.full((H, W), -999.0)
    for x, f in zip(xs, first):
        col = x - x0
        if 0 <= col < W:
            s[:, col] = x if side == "se" else -x
            d[:, col] = py[:, col] - (f + above - 8 * k)
    return px, py, s, d, band, H, W, -x0, above - 8 * k


def _periodic(s, d, W, band, scale, seed, v=0):
    """Smooth noise repeating every face width along s and every band down d, so faces stack
    and join; variants differ only away from the tile edges."""
    a = np.sin(2 * np.pi * s / W)
    b = np.cos(2 * np.pi * s / W)
    c = np.sin(2 * np.pi * d / band)
    e = np.cos(2 * np.pi * d / band)
    n = value_noise(a * scale + 7, b * scale + 3, (c + 2 * e) * scale * 0.7, 1.0, seed)
    if v:
        win = np.sin(np.pi * np.clip(s / W, 0, 1))
        n = n * (1 - win) + value_noise(s / 3.0 + v * 31, d / 3.0, e * 3, 1.0, seed + v) * win
    return n


def rock_face(side, v, k, top=False):
    """One level of the mountain's own rock (Kuh-e Raḥmat, the quarry, the slope): warm grey
    limestone in strata, each bed with a lit lip and a shadowed undercut, vertical joints and
    cracks, weathered pits, a tuft of shrub on a ledge here and there. `top` is the rim band:
    broken rock with grass and wormwood tufts above."""
    above = 6 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = _face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    on = d >= (-above if top else 0)
    on &= d < band
    n = _periodic(s, d, W, band, 1.3, 831, v)
    bed = (d + (n - 0.5) * 2.5 * k) % (4 * k)
    lip = bed < 1.2
    under = (bed > 4 * k - 1.6)
    crack = (np.abs(((s + n * 4 * k) % (W / 2)) - W / 4) < 0.6) & (_periodic(s, d, W, band, 2.0, 833, v) > 0.55)
    pit = hash01(px, py, 835 + v) < 0.04
    lvl = 3.0 + shade + (n - 0.5) * 1.0 + lip * 1.3 - under * 1.4 - crack * 1.4 - pit * 0.7 + (bed / (4 * k)) * 0.5
    rgb = home._paint(ROCK, lvl, px, py, k=k)
    shrub = lip & (_periodic(s, d, W, band, 3.0, 837, v) > 0.8) & (hash01(s.astype(np.int64) // 3, d.astype(np.int64) // 8, 838 + v) < 0.25) & on
    shrub_px = np.zeros_like(shrub)
    for dy in range(1, 3 * k):
        shrub_px |= np.roll(shrub, -dy, axis=0) & (hash01(px, py - dy, 839) < 0.7)
    rgb = np.where(shrub_px[..., None], home._paint(SHRUB, 2.0 + shade + (hash01(px, py, 841) - 0.3), px, py, k=k), rgb)
    alpha = on.copy()
    if top:
        rim = (d < 0) & (d >= -above)
        tuft = rim & (np.abs(d) < 2 + 3 * (_periodic(s, d * 0, W, band, 4.0, 843, v) > 0.6) * (hash01(px, 0, 845) < 0.6))
        alpha = (on & (d >= 0)) | tuft
        rgb = np.where(tuft[..., None], home._paint(SPRING, 2.4 + shade + (hash01(px, py, 847) - 0.5), px, py, k=k), rgb)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha * 255
    return Sprite(rgba, ox, oy)


def earth_face(side, v, k, top=False):
    """One level of an earth bank (field and garden terraces, road cuttings): packed brown
    earth in faint layers, pebbles and roots, a grassy lip on the rim band."""
    above = 5 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = _face_grid(side, k, above)
    shade = -0.9 if side == "se" else 0.0
    on = (d >= 0) & (d < band)
    n = _periodic(s, d, W, band, 1.6, 851, v)
    layer = (d + n * 2 * k) % (3 * k) < 1
    pebble = (hash01(px // 2, py // 2, 853 + v) < 0.015)
    root = (np.abs(((s * 0.7 + d) % (W / 2)) - 3) < 0.5) & (d < band * 0.4) & (_periodic(s, d, W, band, 2.5, 855, v) > 0.6)
    lvl = 3.0 + shade + (n - 0.5) * 1.4 - layer * 0.5 + pebble * 1.2 - root * 1.2
    rgb = home._paint(EARTH_FACE, lvl, px, py, k=k)
    rgb = np.where(pebble[..., None] & on[..., None], home._paint([STONE[1], STONE[2], STONE[3]], 1.2 + shade, px, py, k=k), rgb)
    alpha = on.copy()
    if top:
        tall = hash01(px, 0, 857 + v) * above * (hash01(px // 3, 0, 861 + v) < 0.6)
        lip = (d < 2 * k) & (d >= -tall - 1)
        alpha = alpha | lip
        rgb = np.where(lip[..., None], home._paint(SPRING, 2.6 + shade + (hash01(px, py, 859) - 0.5), px, py, k=k), rgb)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha * 255
    return Sprite(rgba, ox, oy)


# ---------------------------------------------------------------- backdrop

MOUNTAIN = LIMESTONE
FAR = [STONE[1], STONE[2], STONE[3], SNOW[0], SNOW[1]]
SCRUB = [LEAF[0], PINE[0], LEAF[1], EARTH[1]]


def kuh_rahmat(v, night, k):
    """A segment of the Kuh-e Raḥmat strip behind the east world edge: a bare limestone
    mountain of warm grey-brown rock. Spurs lit from the upper left alternate with shadowed
    gullies; beds of rock run across them as broken ledges, each with a lit lip; scree fans
    spread pale at the gully mouths, dark scrub dots the lower slopes, spring snow lies in the
    high gullies, and the higher Zagros shows pale and blue behind. Segments join: the ridge
    at both ends and every texture near the ends are common to all variants."""
    W, Hmax = 256 * k, 192 * k
    H = Hmax + 128 * k
    pyi, pxi = np.mgrid[0:H, 0:W]
    py, px = pyi.astype(float), pxi.astype(float)
    base_y = Hmax + px / 2.0                    # the edge line, sloping down to the right
    t = px / W
    win = np.sin(np.pi * t)                     # 0 at both ends: variant terms fade out there
    z0 = np.zeros_like(px)

    def per(x, y, scale, seed):
        """Noise periodic across the segment width (seamless between any variants)."""
        a = 2 * np.pi * x / W
        return value_noise(np.sin(a) * W / (2 * np.pi * scale) + 50, np.cos(a) * W / (2 * np.pi * scale) + 50,
                           y / scale, 1.0, seed)

    def mix(x, y, scale, seed):
        return per(x, y, scale, seed) * (1 - win) + value_noise(x / scale + v * 97.0, y / scale, z0, 1.0, seed + v) * win
    end = 0.7 * Hmax
    ridge = end + (mix(px, z0, 40.0 * k, 811) - 0.5) * 0.5 * Hmax * win + 0.18 * Hmax * win ** 2 + \
        (mix(px, z0, 6.0 * k, 813) - 0.5) * 0.07 * Hmax
    ridge = np.minimum(ridge, Hmax - 2)
    far = 0.86 * Hmax + (mix(px, z0, 28.0 * k, 815) - 0.5) * 0.22 * Hmax
    height = base_y - py
    inside = (height >= 0) & (height < ridge)
    behind = (height >= ridge) & (height < np.maximum(far, ridge))
    rel = np.clip(height / Hmax, 0, 1)
    top = np.clip(height / np.maximum(ridge, 1), 0, 1)
    # Spurs and gullies: a ridged profile across x that leans a little with height; its
    # slope against the light from the upper left gives lit and shaded flanks.
    xs = px + height * 0.6
    depth = np.clip(1.15 - top, 0.2, 1.0)                 # gullies cut deeper low down
    prof = mix(xs, z0, 30.0 * k, 817) + 0.35 * mix(xs, z0, 9.0 * k, 819) * depth
    dprof = mix(xs + 2 * k, z0, 30.0 * k, 817) + 0.35 * mix(xs + 2 * k, z0, 9.0 * k, 819) * depth - prof
    gully = (prof < 0.5) & (depth > 0.35)
    lit = np.clip(-dprof * 14.0, -1.0, 1.0) * depth
    # Beds of rock: ledges at intervals of height, bent a little by the spurs, broken.
    bed = (height + prof * 6 * k) % (10 * k)
    unbroken = mix(px, height, 7.0 * k, 821) > 0.33
    ledge = (bed < 1.0) & unbroken
    under = (bed >= 1.0) & (bed < 3.0) & unbroken
    grain = mix(px, height, 2.0 * k, 823) - 0.5
    lvl = 2.5 + rel * 1.6 + lit * 1.7 - gully * 1.1 + ledge * 1.3 - under * 1.0 + grain * 0.7 + \
        (mix(px, height, 22.0 * k, 824) - 0.5) * 1.0
    # Scree fans at the gully mouths, low down: paler, finely speckled.
    fan = gully & (rel < 0.28) & (mix(px, z0, 9.0 * k, 825) > 0.45)
    lvl = np.where(fan, 4.6 + (hash01(pxi, pyi, 827) - 0.5) * 1.6 + lit * 0.4, lvl)
    rgb = home._paint(MOUNTAIN, lvl, pxi, pyi, k=k)
    scrub = (rel < 0.4) & ~fan & ~ledge & (hash01(pxi // 2, pyi // 2, 829 + v) < 0.018) \
        & (mix(px, height, 14.0 * k, 831) > 0.45)
    rgb = np.where(scrub[..., None], home._paint(SCRUB, 1.4 + lit * 0.5, pxi, pyi, k=k), rgb)
    snow = (rel > 0.6) & (top > 0.7) & ((prof < 0.55) | (top > 0.93)) & \
        (mix(px, height, 4.0 * k, 833) > 0.7 - (rel - 0.6) * 1.2)
    rgb = np.where(snow[..., None], home._paint([STONE[3], SNOW[0], SNOW[1], SNOW[2]], 1.2 + lit * 0.8 + ledge, pxi, pyi, k=k), rgb)
    # The higher range behind: pale, cool, snow on its crest.
    frel = np.clip((height - ridge) / np.maximum(far - ridge, 1), 0, 1)
    far_lvl = 1.2 + frel * 1.8 + (mix(xs, z0, 7.0 * k, 835) - 0.5) * 1.4
    rgb = np.where(behind[..., None], home._paint(FAR, far_lvl, pxi, pyi, k=k), rgb)
    if night:
        nl = 0.6 + rel * 1.2 + lit * 0.5 + ledge * 0.4 + snow * 1.6 - gully * 0.4
        rgb = home._paint([INK, STONE[0], LAPIS[0], STONE[1], STONE[2]], np.where(behind, 1.0 + frel, nl), pxi, pyi, k=k)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = (inside | behind) * 255
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
        elif m := re.fullmatch(r"edge/parsa\.(ashlar|rock|earth)_(se|sw)/(v(\d)|top)", key):
            face = {"ashlar": ashlar_face, "rock": rock_face, "earth": earth_face}[m[1]]
            out[key] = face(m[2], int(m[4] or 0), k, top=m[3] == "top")
        elif m := re.fullmatch(r"backdrop/parsa\.kuh_rahmat/(day|night)/v(\d)", key):
            out[key] = kuh_rahmat(int(m[2]), m[1] == "night", k)
        elif m := re.fullmatch(r"fx/(parsa\.\w+)/f(\d+)", key):
            out[key] = fx(m[1], int(m[2]), FRAMES[m[1]], k)
        else:
            raise KeyError(key)
    return out
