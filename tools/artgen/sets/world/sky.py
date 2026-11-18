"""The world's sky and screen-space sprites (docs/design/sets/world.md §6): backdrop strips
behind the north and east world edges, soft weather sprites, effects and the paper map's ink
markers.

Backdrop segments are drawn for the east edge (their base line slopes down to the right, like
`parsa.kuh_rahmat`); the engine mirrors a segment for the north edge, anchored at its right
end. Strips meant only for the north edge are lit from the upper right so that, mirrored,
their light comes from the upper left like everything else; strips used on both edges are lit
from straight above."""

import math

import numpy as np

import terrain as home
from pack import Sprite
from palette import (BASALT, EARTH, GLOW, HAZE, INK, LEAF, OLIVE, PINE, PLASTER, ROOF, SAND, SEA, SEPIA, SHALLOW,
                     SNOW, STEPPE, STONE, STRAW, _rgb)
from render import BAYER4, dither
from sets.parsa.ground import _fx
from voxel import hash01, value_noise

FX_FRAMES = {"world.whitecap": 6, "world.wake": 6, "world.dolphin": 6, "world.dust_puff": 6, "world.chaff": 6,
             "world.lightning": 4, "world.puddle": 4, "world.fire": 6, "world.shimmer": 6, "world.spray": 6,
             "world.fish_shoal": 4}


def _paint(ramp, level, px, py, k, band=0.55):
    return home._paint(ramp, level, px, py, band=band, k=k)


# ---------------------------------------------------------------- backdrops

# Per strip: (light: -1 upper left, 0 above, +1 upper right; far ramp, mid ramp, near ramp,
# snow ramp or None, ridge heights as shares of the strip height).
BACK = {
    "world.bd_far_hills": dict(light=0, far=HAZE[2:], mid=HAZE[0:4], near=[HAZE[0], STONE[1], HAZE[1], HAZE[2]],
                               snow=None, heights=(0.62, 0.45, 0.26), wood=None),
    "world.bd_alps": dict(light=1, far=[HAZE[2], HAZE[3], SNOW[0], SNOW[1], SNOW[2]],
                          mid=[HAZE[0], HAZE[1], STONE[2], HAZE[2], STONE[3]],
                          near=[PINE[0], PINE[1], LEAF[1], OLIVE[1], LEAF[2], OLIVE[2]],
                          snow=[HAZE[3], SNOW[0], SNOW[1], SNOW[2]], heights=(0.95, 0.55, 0.3), wood=True),
    "world.bd_pindos": dict(light=1, far=[HAZE[2], HAZE[3], HAZE[4], SNOW[1]],
                            mid=[STONE[1], HAZE[1], STONE[2], STONE[3], HAZE[3], STONE[4]],
                            near=[STONE[1], OLIVE[0], OLIVE[1], STONE[2], OLIVE[2], STONE[3]],
                            snow=[STONE[3], SNOW[0], SNOW[1]], heights=(0.8, 0.6, 0.32), wood=None),
    "world.bd_pontic": dict(light=1, far=[HAZE[3], SNOW[0], SNOW[1], SNOW[2]],
                            mid=[PINE[0], HAZE[0], PINE[1], HAZE[1], PINE[2]],
                            near=[PINE[0], PINE[1], LEAF[0], PINE[2], LEAF[1], LEAF[2]],
                            snow=None, heights=(0.9, 0.58, 0.34), wood=True, cloud=True),
    "world.bd_plateau": dict(light=0, far=[HAZE[2], HAZE[3], HAZE[4], SNOW[1], SNOW[2]],
                             mid=[EARTH[1], STEPPE[1], HAZE[1], STEPPE[2], SAND[2], STEPPE[3]],
                             near=[EARTH[0], EARTH[1], STEPPE[0], EARTH[2], STEPPE[2], SAND[3]],
                             snow=[HAZE[3], SNOW[0], SNOW[1], SNOW[2]], heights=(0.75, 0.42, 0.24), wood=None,
                             cone=True),
}


def backdrop(bid, v, k):
    """One segment of a strip, 16 edge tiles long and at most 256 px tall at 64 x 32: three
    ranges one behind the other, the nearer darker and more detailed, the farther paler in the
    haze. Ridges and textures near both ends are common to every look, so looks join."""
    st = BACK[bid]
    W, Hmax = 256 * k, 128 * k
    H = Hmax + 128 * k
    pyi, pxi = np.mgrid[0:H, 0:W]
    py, px = pyi.astype(float), pxi.astype(float)
    height = Hmax + px / 2.0 - py
    t = px / W
    win = np.sin(np.pi * t)
    z0 = np.zeros_like(px)
    seed0 = sum(map(ord, bid))

    def per(x, y, scale, seed):
        a = 2 * np.pi * x / W
        return value_noise(np.sin(a) * W / (2 * np.pi * scale) + 50, np.cos(a) * W / (2 * np.pi * scale) + 50,
                           y / scale, 1.0, seed)

    def mix(x, y, scale, seed):
        return per(x, y, scale, seed) * (1 - win) + value_noise(x / scale + v * 97.0, y / scale, z0, 1.0, seed + v) * win

    rgb = np.zeros((H, W, 3), np.uint8)
    alpha = np.zeros((H, W), bool)
    light = st["light"]
    for layer, (share, ramp) in enumerate(zip(st["heights"], (st["far"], st["mid"], st["near"]))):
        seed = seed0 + 31 * layer
        base = share * Hmax
        amp = (0.32, 0.28, 0.22)[layer]
        if st.get("cone") and layer == 0:
            cone = np.clip(1 - np.abs(px - W * (0.35 + 0.3 * (v % 2))) / (W * 0.16), 0, 1)
            ridge = base * 0.55 + Hmax * 0.42 * cone ** 1.4 * win + (mix(px, z0, 9 * k, seed) - 0.5) * 0.05 * Hmax
        else:
            ridge = base + (mix(px, z0, (60, 34, 20)[layer] * k, seed) - 0.5) * amp * 2 * Hmax * win \
                + (mix(px, z0, (14, 8, 5)[layer] * k, seed + 1) - 0.5) * 0.08 * Hmax
        ridge = np.clip(ridge, 4 * k, Hmax - 2)
        inside = (height >= 0) & (height < ridge)
        # Spurs and gullies: the profile's slope against the light gives lit and shaded flanks.
        xs = px + height * 0.5
        prof = mix(xs, z0, (26, 16, 9)[layer] * k, seed + 2)
        dprof = mix(xs + 2 * k, z0, (26, 16, 9)[layer] * k, seed + 2) - prof
        lit = np.clip((-dprof if light <= 0 else dprof) * 14.0, -1, 1) * (0.6 if light == 0 else 1.0)
        top = np.clip(height / np.maximum(ridge, 1), 0, 1)
        lvl = 1.4 + top * 1.2 + lit * 1.1 + (mix(px, height, 4 * k, seed + 3) - 0.5) * 0.6
        if light == 0:      # lit from above: the upper slopes brighter
            lvl = lvl + (top > 0.85) * 0.5
        col = _paint(ramp, lvl, pxi, pyi, k)
        if st.get("wood") and layer == 2:
            tree = (hash01(pxi // 2, pyi // 2, seed + 4 + v) < 0.25) & (top < 0.9) & (mix(px, height, 10 * k, seed + 5) > 0.4)
            col = np.where(tree[..., None], _paint([PINE[0], PINE[1], LEAF[1]], 1.0 + lit, pxi, pyi, k), col)
        if st["snow"] is not None and layer <= 1:
            snowline = 0.62 if layer == 0 else 0.8
            sn = (top > snowline) & ((prof < 0.55) | (top > snowline + 0.15)) & \
                (mix(px, height, 3 * k, seed + 6) > 0.62 - (top - snowline) * 1.6)
            col = np.where(sn[..., None], _paint(st["snow"], 1.4 + lit + top, pxi, pyi, k), col)
        if layer == 0 and st.get("cloud"):
            band = (height > ridge * 0.7) & (height < ridge * 0.95) & (mix(px, height, 12 * k, seed + 7) > 0.45)
            col = np.where(band[..., None], _paint([HAZE[3], HAZE[4], SNOW[1], SNOW[2]], 1.6 + top, pxi, pyi, k), col)
        rgb = np.where(inside[..., None], col, rgb)
        alpha |= inside
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha * 255
    return Sprite(rgba, 0, Hmax)


# ---------------------------------------------------------------- weather

WEATHER_SIZE = {"cloud_shadow": (192, 96), "fog": (384, 48), "dust": (256, 96), "seam_mist": (512, 96),
                "seam_haze": (384, 64), "squall": (128, 192), "heat_shimmer": (256, 32)}


def _soft(alpha, px, py, steps=4):
    """Quantise a 0..1 alpha into a few levels with the ordered dither, so soft sprites keep
    the pixel look."""
    q = np.floor(alpha * steps + BAYER4[py % 4, px % 4] * 0.999) / steps
    return np.clip(q, 0, 1)


def weather(kind, v, k):
    """Soft low-alpha sprites the engine lays over the ground (living-world.md §6.1)."""
    w, h = (s * k // 2 for s in WEATHER_SIZE[kind])
    py, px = np.mgrid[0:h, 0:w]
    x, y = (px + 0.5) / w, (py + 0.5) / h
    seed = sum(map(ord, kind)) * 7 + v * 131
    n = value_noise(px / (24.0 * k / 2), py / (12.0 * k / 2), np.zeros_like(x), 1.0, seed)
    fine = value_noise(px / (7.0 * k / 2), py / (4.0 * k / 2), np.zeros_like(x), 1.0, seed + 1)
    ex = np.clip(1 - ((x - 0.5) * 2) ** 2, 0, 1)
    ey = np.clip(1 - ((y - 0.5) * 2) ** 2, 0, 1)
    rgb = np.zeros((h, w, 3), np.uint8)
    if kind == "cloud_shadow":
        lobes = sum(np.clip(1 - np.hypot((x - cx) / rx, (y - cy) / ry), 0, 1) for cx, cy, rx, ry in
                    [(0.5 + 0.18 * math.cos(a + v), 0.5 + 0.2 * math.sin(a * 1.3 + v), 0.3, 0.38)
                     for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)])
        a = np.clip(lobes * 0.9 + (n - 0.5) * 0.6, 0, 1) * 0.42
        rgb[:] = _rgb(INK)
    elif kind in ("fog", "seam_mist", "seam_haze", "heat_shimmer"):
        streak = value_noise(px / (40.0 * k / 2), py / (3.0 * k / 2), np.zeros_like(x), 1.0, seed + 2)
        body = ex ** 0.6 * ey ** (1.2 if kind != "heat_shimmer" else 3.0)
        dens = {"fog": 0.5, "seam_mist": 0.62, "seam_haze": 0.3, "heat_shimmer": 0.22}[kind]
        a = np.clip(body * (0.55 + 0.6 * (streak - 0.5) + 0.4 * (n - 0.5)), 0, 1) * dens
        if kind == "heat_shimmer":
            wave = np.abs(np.sin(px / (6.0 * k / 2) + py * 1.3 + v * 2.0)) < 0.25
            a = a * wave * 2.2
        ramp = {"fog": [SNOW[1], SNOW[2], PLASTER[4]], "seam_mist": [STRAW[3], SAND[4], SAND[5], PLASTER[4]],
                "seam_haze": [SAND[3], SAND[4], SAND[5]], "heat_shimmer": [SAND[5], PLASTER[4]]}[kind]
        rgb[:] = _paint(ramp, 1.0 + fine * len(ramp) * 0.6, px, py, k)
    elif kind == "dust":
        streak = value_noise(px / (30.0 * k / 2), py / (5.0 * k / 2), np.zeros_like(x), 1.0, seed + 3)
        a = np.clip(ex * ey ** 0.8 * (0.5 + 0.8 * (streak - 0.5) + 0.5 * (n - 0.5)), 0, 1) * 0.5
        rgb[:] = _paint([EARTH[2], SAND[1], SAND[2], SAND[3]], 1.0 + fine * 2.5, px, py, k)
    elif kind == "squall":
        base = np.clip(1 - np.abs(y - 0.14) / 0.12, 0, 1) * ex ** 0.5
        cloud = np.clip(base + (n - 0.5) * 0.5, 0, 1)
        rain = (y > 0.12) & (value_noise(px / (2.0 * k / 2) + py * 0.18, py * 0, np.zeros_like(x), 1.0, seed + 4) > 0.55)
        curtain = rain * ex ** 0.8 * np.clip(1 - (y - 0.12) / 0.88, 0, 1) ** 0.5 * (0.5 + 0.6 * n)
        a = np.clip(np.maximum(cloud * 0.75, curtain * 0.55), 0, 1)
        rgb[:] = _paint([INK, STONE[0], STONE[1], STONE[2]], 1.0 + fine * 2 + (y > 0.2), px, py, k)
    else:
        raise KeyError(kind)
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = (_soft(a, px, py) * 255).astype(np.uint8)
    return Sprite(rgba, w // 2, h // 2)


# ---------------------------------------------------------------- markers

def _ink(canvas, shape, level):
    canvas[shape] = np.maximum(canvas[shape], level)


def marker(icon, k):
    """A small sepia ink drawing for the paper overview map (24 x 24 at 64 x 32), anchored at
    its centre: line work in dark ink, a paler wash inside."""
    s = 12 * k
    py, px = np.mgrid[0:s, 0:s]
    x, y = (px + 0.5) / (k / 2) - 12, (py + 0.5) / (k / 2) - 12       # design px around the centre
    c = np.zeros((s, s), np.int64)          # 0 empty, 1 wash, 2 mid, 3 line
    line = lambda m: _ink(c, m, 3)
    wash = lambda m: _ink(c, m, 1)

    def rect(x0, x1, y0, y1, w=1.0):
        inside = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        edge = inside & ((x < x0 + w) | (x > x1 - w) | (y < y0 + w) | (y > y1 - w))
        wash(inside)
        line(edge)

    if icon == "home":          # the cottage: a pitched roof, a chimney, a door
        rect(-6, 6, -1, 8)
        roof = (y >= -8) & (y <= -1) & (np.abs(x) <= (y + 9) * 1.0)
        wash(roof)
        line(roof & ((np.abs(x) > (y + 9) - 1.4) | (y > -2)))
        rect(3.5, 5.5, -9, -4)
        rect(-1.5, 1.5, 3, 8, 0.9)
    elif icon == "rome":        # a dome over a portico and a column beside it
        d = np.hypot(x + 1, (y + 1) * 1.3)
        wash((d < 6.5) & (y < -1))
        line((np.abs(d - 6.5) < 0.9) & (y < -1))
        rect(-8, 6, -1, 2)
        for cx in (-6, -3, 0, 3):
            line((np.abs(x - cx) < 0.6) & (y > 2) & (y < 8))
        rect(-8.5, 6.5, 8, 9.5)
        line((np.abs(x - 9) < 0.8) & (y > -9) & (y < 9.5))
        rect(7.5, 10.5, -10, -8.5)
    elif icon == "athens":      # the rock and a temple on it
        rock = (y > 2) & (np.abs(x) < 10 - (y - 2) * -0.4) & (y < 9)
        wash(rock)
        line(rock & ((y < 3) | (np.abs(x) > 9 - (y - 2) * -0.4)))
        roof = (y > -8) & (y <= -4) & (np.abs(x) <= (y + 8) * 1.8)
        wash(roof)
        line(roof & ((np.abs(x) > (y + 8) * 1.8 - 1.4) | (y > -5)))
        for cx in (-6, -3, 0, 3, 6):
            line((np.abs(x - cx) < 0.6) & (y > -4) & (y < 2))
        line((y > 1.2) & (y < 2.4) & (np.abs(x) < 8))
    elif icon == "parsa":       # a double stairway and two columns with their capitals
        for sgn in (-1, 1):
            st = (y > 2) & (y < 9) & (sgn * x > 0) & (sgn * x < 9) & ((sgn * x) > (y - 2) * 0.0) & \
                 (y > 9 - (9 - sgn * x) * 0.8)
            wash(st)
            line(st & ((np.floor(y) % 2) == 0))
        for cx in (-4, 4):
            line((np.abs(x - cx) < 0.7) & (y > -6) & (y < 2))
            rect(cx - 2.5, cx + 2.5, -9, -6, 0.9)
        line((y > -10) & (y < -8.8) & (np.abs(x) < 8))
    elif icon == "town":        # a small drawn tower with a crenellated top
        rect(-4, 4, -5, 8)
        cren = (y > -9) & (y < -5) & (np.abs(x) < 5) & ((np.floor(x + 5) % 3) < 1.6)
        line(cren)
        rect(-1, 1, 2, 8, 0.8)
        line((np.abs(x) < 0.6) & (y > -3) & (y < -1))
    elif icon == "town_unseen":     # an open dot
        d = np.hypot(x, y)
        line((d > 3.2) & (d < 5.0))
    elif icon == "port":        # an anchor
        line((np.abs(x) < 0.8) & (y > -8) & (y < 7))
        d = np.hypot(x, y + 9)
        line((d > 1.2) & (d < 2.6))
        line((np.abs(y + 4) < 0.7) & (np.abs(x) < 5))
        arc = np.hypot(x, y - 1)
        line((np.abs(arc - 7.5) < 0.9) & (y > 2))
    elif icon == "pass":        # two peaks with a path between them
        for cx, hgt in ((-5, 9), (5, 11)):
            pk = (y < 7) & (y > 7 - hgt + np.abs(x - cx) * 1.3)
            wash(pk)
            line(pk & (y < 7 - hgt + np.abs(x - cx) * 1.3 + 1.4))
        line((np.abs(x - (y - 7) * 0.2) < 0.7) & (y > 0) & (y < 9) & ((np.floor(y) % 2) == 0))
        line((y > 7) & (y < 8.4) & (np.abs(x) < 11))
    elif icon == "shrine":      # a small stele on a stepped base with an offering bowl
        rect(-3, 3, -7, 4)
        top = (y > -10) & (y <= -7) & (np.abs(x) <= (y + 10) * 1.2)
        wash(top)
        line(top & ((np.abs(x) > (y + 10) * 1.2 - 1.2) | (y > -7.8)))
        rect(-6, 6, 4, 7)
        rect(-8, 8, 7, 9.5)
    else:
        raise KeyError(icon)
    ramp = np.array([(0, 0, 0)] + [_rgb(cc) for cc in (SEPIA[2], SEPIA[1], SEPIA[0])], np.uint8)
    rgba = np.zeros((s, s, 4), np.uint8)
    rgba[..., :3] = ramp[c]
    rgba[..., 3] = np.where(c == 0, 0, np.where(c == 1, 110, 255)).astype(np.uint8)
    return Sprite(rgba, s // 2, s // 2)


# ---------------------------------------------------------------- effects

def fx(fid, f, n, k):
    rng = np.random.Generator(np.random.PCG64([sum(map(ord, fid)), 7]))
    t = f / n
    pts = []
    if fid == "world.whitecap":         # a crest forms, breaks white and dissolves
        grow = math.sin(math.pi * t)
        for i in range(9):
            x = (i - 4) * 1.4 * (0.6 + 0.6 * grow)
            y = -abs(x) * 0.15 - grow * 1.2 * (1 - abs(i - 4) / 5)
            if rng.uniform() < 0.5 + grow * 0.5:
                pts.append((x, y, (SHALLOW[4], SNOW[2], PLASTER[4])[i % 3], 0.6 + 0.3 * grow))
        return _fx(pts, (18, 8), k)
    if fid == "world.wake":             # V-shaped ripples spreading behind a hull
        for arm in (-1, 1):
            for i in range(10):
                s = i / 9
                x = -s * 14 - t * 3
                y = arm * s * 5 * (0.6 + 0.4 * t) - 2
                if (i + f) % 3 != 0:
                    pts.append((x, y, (SHALLOW[3], SHALLOW[4], PLASTER[4])[i % 3], 0.5))
        return _fx(pts, (36, 14), k)
    if fid == "world.dolphin":          # a grey dolphin arcing out and back in, a splash
        ph = t * math.pi
        cx, cy = -8 + 16 * t, -8 * math.sin(ph)
        if 0 < f < n - 1:
            ang = math.cos(ph) * 0.9
            for i in range(9):
                s = (i - 4) / 4
                x = cx + s * 4.5 * math.cos(ang)
                y = cy - s * 4.5 * math.sin(ang) - (1 - s * s) * 1.4
                pts.append((x, y, (BASALT[3], BASALT[4], STONE[2])[1 if i < 6 else 0], 1.1 - abs(s) * 0.5))
            pts.append((cx - 0.5, cy - 2.4, BASALT[3], 0.6))      # dorsal fin
            pts.append((cx + 1.0, cy + 0.2, STONE[3], 0.5))       # pale belly
        sx = -8 if f <= 1 else 8 if f >= n - 2 else None
        if sx is not None:
            for i in range(7):
                a = rng.uniform(-1.2, 1.2)
                pts.append((sx + a * 3, -abs(a) * 2.5 - rng.uniform(0, 2), (SHALLOW[4], PLASTER[4])[i % 2], 0.5))
        return _fx(pts, (30, 14), k)
    if fid == "world.dust_puff":        # dust kicked up by hooves and wheels
        for i in range(10):
            a = rng.uniform(0, 2 * math.pi)
            r = (1 + 5 * t) * rng.uniform(0.4, 1.0)
            if rng.uniform() < 1 - t * 0.6:
                pts.append((math.cos(a) * r, -abs(math.sin(a)) * r * 0.7 - t * 2, (SAND[1], SAND[2], SAND[3])[i % 3],
                            1.2 + t * 1.2))
        return _fx(pts, (18, 12), k)
    if fid == "world.chaff":            # chaff blown off the threshing floor
        for i in range(12):
            x0, y0 = rng.uniform(-6, 2), rng.uniform(-10, -2)
            pts.append((x0 + t * 8 + math.sin(t * 6 + i) * 1.2, y0 + t * 3, (STRAW[2], STRAW[3], SAND[4])[i % 3], 0.5))
        return _fx(pts, (22, 14), k)
    if fid == "world.lightning":        # a jagged bolt: flash, strike, branch, fade
        if f == 3:
            return _fx([(0, -1, SNOW[1], 0.5)], (24, 60), k)
        x, y = rng.uniform(-3, 3), -58.0
        col = (PLASTER[4], SNOW[2], GLOW[2])[f % 3]
        while y < 0:
            nx, ny = x + rng.uniform(-3.5, 3.5), y + rng.uniform(3, 6)
            for s in np.linspace(0, 1, 6):
                pts.append((x + (nx - x) * s, min(0, y + (ny - y) * s), col, 0.7 if f == 1 else 0.5))
            if f >= 1 and rng.uniform() < 0.25:
                bx, by = nx, ny
                for j in range(3):
                    bx2, by2 = bx + rng.uniform(-4, 4), by + rng.uniform(2, 4)
                    for s in np.linspace(0, 1, 4):
                        pts.append((bx + (bx2 - bx) * s, min(0, by + (by2 - by) * s), SNOW[1], 0.4))
                    bx, by = bx2, by2
            x, y = nx, ny
        return _fx(pts, (24, 60), k)
    if fid == "world.puddle":           # a muddy rain puddle on earth, growing over 4 frames
        g = (f + 1) / n
        for i in range(40):
            a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.uniform()) * 6 * g
            pts.append((math.cos(a) * r * 1.6, math.sin(a) * r * 0.6 - 3, (SEA[3], SEA[4], SHALLOW[1])[i % 3], 1.2 * g + 0.4))
        pts.append((-2 * g, -3.5, SHALLOW[3], 0.6 * g + 0.2))
        return _fx(pts, (26, 10), k)
    if fid == "world.fire":             # the beacon's flames: big tongues and sparks
        for i in range(16):
            h, a = rng.uniform(0, 1), rng.uniform(-1, 1)
            ph = (h + t) % 1.0
            col = (GLOW[2], GLOW[1], GLOW[0], ROOF[2])[min(3, int(ph * 4))]
            pts.append((a * (1 - ph) * 4.5, -ph * 16, col, (2.2 - ph * 1.6)))
        return _fx(pts, (20, 22), k)
    if fid == "world.shimmer":          # golden motes in the seam mist
        for i in range(8):
            x, y = rng.uniform(-10, 10), rng.uniform(-14, -1)
            on = math.sin(2 * math.pi * (t + rng.uniform(0, 1))) > 0.2
            if on:
                pts.append((x + math.sin(t * 6.28 + i) * 1.0, y - t * 2, (STRAW[3], GLOW[2], PLASTER[4])[i % 3], 0.5))
        pts.append((0, -1, STRAW[3], 0.4))
        return _fx(pts, (24, 18), k)
    if fid == "world.spray":            # surf thrown up against a cliff or a mole
        for i in range(16):
            a = rng.uniform(-1, 1)
            ph = (rng.uniform(0, 0.3) + t) % 1.0
            up = math.sin(math.pi * min(1.0, t * 1.4)) * 12
            pts.append((a * (2 + ph * 6), -up * (1 - abs(a) * 0.4) * rng.uniform(0.5, 1.0), (SHALLOW[4], SNOW[2], PLASTER[4])[i % 3],
                        0.6 + 0.6 * (1 - t)))
        return _fx(pts, (22, 18), k)
    if fid == "world.fish_shoal":       # a dark shifting patch with silver glints
        for i in range(30):
            a = rng.uniform(0, 2 * math.pi) + t * 1.5
            r = math.sqrt(rng.uniform()) * 7
            pts.append((math.cos(a) * r * 1.5, math.sin(a) * r * 0.5 - 4, (SEA[0], SEA[1])[i % 2], 0.7))
        for i in range(5):
            a = rng.uniform(0, 2 * math.pi) + t * 2.0
            pts.append((math.cos(a) * 6, math.sin(a) * 2 - 4, (SNOW[2], SHALLOW[4])[i % 2], 0.4))
        return _fx(pts, (26, 10), k)
    raise KeyError(fid)
