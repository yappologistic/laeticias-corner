"""Small effect sprites, drawn directly in screen space at k pixels per design unit. Anchors are
the contact point: the bottom of a smoke puff, the centre of a ripple or sparkle, where a
raindrop lands. Shapes scale with k; lines and glints stay a pixel wide, so finer builds get
finer effects rather than enlarged ones."""

import math

import numpy as np

from pack import Sprite
from palette import BLOSSOM, EARTH, GLOW, INK, LEAF, PINE, PLASTER, POPPY, ROOF, SNOW, STONE, STRAW, WATER, _rgb
from render import dither


def _canvas(w, h):
    py, px = np.mgrid[0:h, 0:w]
    return px, py, np.zeros((h, w, 4), np.uint8)


def _set(rgba, mask, color, alpha=255):
    rgba[mask, :3] = _rgb(color)
    rgba[mask, 3] = alpha


# A puff is a few overlapping round lobes: (dx, dy) offsets in units of the puff radius.
SMOKE_LOBES = ((0.0, 0.0, 1.0), (-0.55, 0.25, 0.7), (0.5, 0.3, 0.65), (0.1, -0.45, 0.6))


def smoke(frame, frames, k):
    """A soft round puff that swells and thins out; the engine moves it upward."""
    t = frame / (frames - 1)
    r = (1.6 + 3.4 * t) * k
    w = h = 15 * k
    px, py, rgba = _canvas(w, h)
    cx, cy = 7.5 * k, h - 0.5 - r * 1.1
    inside = np.zeros(px.shape, np.float32)       # 1 deep inside a lobe, 0 at its edge
    for dx, dy, s in SMOKE_LOBES:
        d = np.hypot(px + 0.5 - cx - dx * r, py + 0.5 - cy - dy * r) / (r * s)
        inside = np.maximum(inside, 1 - d)
    # Lit from the upper left: light cream top, grey belly.
    lit = ((px + 0.5 - cx) * -0.6 + (py + 0.5 - cy) * -0.8) / r
    level = 1.2 + lit * 1.2 + inside * 0.6 - t * 0.5
    ramp = np.array([_rgb(c) for c in (STONE[3], STONE[4], PLASTER[3], PLASTER[4])], np.uint8)
    rgba[..., :3] = ramp[np.clip(dither(level, px, py, 0.55 / k), 0, 3).astype(np.int64)]
    # A soft rim one step fainter than the body; the whole puff fades and opens up with age.
    body = int(225 - 150 * t)
    alpha = np.where(inside > 0.22, body, np.where(inside > 0, body // 2, 0))
    holes = dither(np.full(px.shape, 1.9 - t * 1.1), px, py) < 1
    rgba[..., 3] = np.where(holes & (inside < 0.6), 0, alpha)
    return Sprite(rgba, 7 * k, h)


def ripple(frame, frames, k):
    t = frame / (frames - 1)
    r = (2.5 + 5.5 * t) * k
    w, h = 21 * k, 11 * k
    px, py, rgba = _canvas(w, h)
    d = np.hypot(px + 0.5 - 10.5 * k, (py + 0.5 - 5.5 * k) * 2)
    alpha = int(230 - 140 * t)
    if k > 1 and t > 0:  # a fainter second ring follows the first on fine grids
        inner = np.abs(d - r * 0.6) < 0.6
        _set(rgba, inner, WATER[4], alpha // 2)
    ring = np.abs(d - r) < 0.75
    _set(rgba, ring, WATER[5], alpha)
    _set(rgba, ring & (py + 0.5 > 5.5 * k), WATER[4], alpha)
    return Sprite(rgba, 10 * k, 5 * k)


def sparkle(frame, frames, k):
    size = (1, 2, 3, 1)[frame % 4] * k
    c = 3 * k
    px, py, rgba = _canvas(2 * c + 1, 2 * c + 1)
    dx, dy = np.abs(px - c), np.abs(py - c)
    star = ((dx == 0) & (dy <= size)) | ((dy == 0) & (dx <= size))
    _set(rgba, star, GLOW[1])
    _set(rgba, (dx + dy == 0) | (star & (dx + dy <= size - 2 * k)), GLOW[2])
    if size == 3 * k:
        _set(rgba, (dx == dy) & (dx >= 1) & (dx <= k), GLOW[1], 140)
    return Sprite(rgba, c, c)


def raindrop(frame, frames, k):
    """f0: the falling streak; f1..: the splash where it lands."""
    px, py, rgba = _canvas(9 * k, 7 * k)
    x0 = 4 * k
    if frame == 0:
        _set(rgba, (px == x0) & (py >= k) & (py < 5 * k), WATER[5], 170)
        _set(rgba, (px == x0) & (py >= 5 * k) & (py < 6 * k), PLASTER[4], 210)
        return Sprite(rgba, x0, 6 * k)
    r = frame * 1.4 * k
    d = np.hypot(px + 0.5 - 4.5 * k, (py + 0.5 - 5.5 * k) * 2)
    _set(rgba, np.abs(d - r) < 0.7, WATER[5], int(220 - 50 * frame))
    if frame == 1:  # droplets thrown up and out
        _set(rgba, (np.abs(px - x0) == k) & (py == 3 * k), WATER[5], 200)
        if k > 1:
            _set(rgba, (np.abs(px - x0) == 2 * k) & (py == 4 * k), WATER[5], 160)
    return Sprite(rgba, x0, 5 * k)


def leaf(frame, frames, k):
    a = frame / frames * math.pi
    c = 3 * k
    px, py, rgba = _canvas(2 * c + 1, 2 * c + 1)
    x, y = (px - c) / k, (py - c) / k
    u = x * math.cos(a) + y * math.sin(a)
    v = -x * math.sin(a) + y * math.cos(a)
    flat = 0.45 + 0.55 * abs(math.cos(a * 1.5))
    shape = (u / 2.8) ** 2 + (v / (1.5 * flat)) ** 2 <= 1
    _set(rgba, shape, LEAF[4])
    _set(rgba, shape & (v > 0.3), LEAF[3])
    # The midrib stays a pixel wide.
    _set(rgba, shape & (np.abs(v) < 0.5 / k) & (np.abs(u) < 2), STRAW[2])
    _set(rgba, (np.abs(u - 3.2) < 0.6) & (np.abs(v) < 0.6), EARTH[2])
    return Sprite(rgba, c, c)


# ---- batch 2: hand-drawn at the 64x32 density (2 px per design unit), scaled for others ----

FX_INKS = {"K": INK, "P": BLOSSOM[2], "p": BLOSSOM[3], "q": BLOSSOM[4], "W": SNOW[2], "w": SNOW[1],
           "b": SNOW[0], "R": POPPY[0], "r": POPPY[1], "D": ROOF[1], "G": LEAF[3], "g": LEAF[4],
           "B": EARTH[1], "S": STONE[4], "s": STONE[3], "C": PLASTER[4], "c": PLASTER[3], "Y": STRAW[2],
           "V": PINE[1], "v": LEAF[2], "e": EARTH[3], "O": GLOW[0], "o": ROOF[3], "x": STONE[2]}


def _stencil(rows, k, alpha=255, ox=None, oy=None):
    """Rows of FX_INKS letters drawn for k = 2; the anchor defaults to the bottom middle."""
    h, w = len(rows), len(rows[0])
    rgba = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                rgba[y, x, :3] = _rgb(FX_INKS[ch])
                rgba[y, x, 3] = alpha
    ox = w // 2 if ox is None else ox
    oy = h - 1 if oy is None else oy
    if k >= 2:
        f = k // 2
        return Sprite(rgba.repeat(f, 0).repeat(f, 1), ox * f, oy * f)
    return Sprite(rgba[::2, ::2].copy(), ox // 2, oy // 2)


HEART = (".PP.PP.",
         "PqpPPpP",
         "PpPPPPP",
         ".PPPPP.",
         "..PPP..",
         "...P...")
HEART_SMALL = ("P.P", "PPP", ".P.")


def heart(frame, frames, k):
    """A pink heart that pops, rises (the offset is in the sprite) and fades."""
    rows = HEART_SMALL if frame == 0 else HEART
    sp = _stencil(rows, k, alpha=(255, 255, 210, 120)[frame % 4])
    pad = np.zeros((sp.rgba.shape[0] + 3 * frame * max(1, k // 2),) + sp.rgba.shape[1:], np.uint8)
    pad[:sp.rgba.shape[0]] = sp.rgba
    return Sprite(pad, sp.ox, pad.shape[0] - 1)


PETALS = (("pP", "Pq"), (".P", "Pp"), ("PP",), ("P.", "pP"))


def petal(frame, frames, k):
    return _stencil(PETALS[frame % 4], k)


SNOWFLAKES = ((".w.", "wWw", ".w."), ("w.w", ".W.", "w.w"), (".b.", "bWb", ".b."), ("...", ".W.", "..."))


def snowflake(frame, frames, k):
    return _stencil(SNOWFLAKES[frame % 4], k, ox=1, oy=1)


MOTHS = (("c.c", "cCc", ".s."), ("...", "cCc", "csc"))


def moth(frame, frames, k):
    return _stencil(MOTHS[frame % 2], k, ox=1, oy=1, alpha=230)


def fish_jump(frame, frames, k):
    """A silver fish arcing out of the water and back in, with a splash at each end."""
    sc = max(1, k // 2) if k >= 2 else 1
    w, h = 18 * sc, 18 * sc
    px, py, rgba = _canvas(w, h)
    t = frame / (frames - 1)
    base = h - 2 * sc
    if 0 < frame < frames - 1:
        cx = (3 + 12 * t) * sc
        cy = base - 13 * sc * 4 * t * (1 - t)
        ang = math.atan2(-13 * 4 * (1 - 2 * t), 12)
        ca, sa = math.cos(ang), math.sin(ang)
        u = ((px + 0.5 - cx) * ca + (py + 0.5 - cy) * sa) / sc
        v = (-(px + 0.5 - cx) * sa + (py + 0.5 - cy) * ca) / sc
        body = (u / 3.2) ** 2 + (v / 1.2) ** 2 <= 1
        tail = (u < -2.6) & (u > -4.6) & (np.abs(v) < (-u - 2.4) * 0.8)
        _set(rgba, body | tail, STONE[3])
        _set(rgba, body & (v < -0.2), STONE[5])
        _set(rgba, body & (v > 0.5), STONE[2])
        _set(rgba, (np.abs(u - 2.0) < 0.5) & (np.abs(v + 0.2) < 0.5), INK)
    for sx, active in ((3 * sc, frame in (0, 1)), (15 * sc, frame in (frames - 2, frames - 1))):
        if active:
            d = np.hypot(px + 0.5 - sx, (py + 0.5 - base) * 2)
            r = (2.0 + 1.5 * (frame % 2)) * sc
            _set(rgba, np.abs(d - r) < 0.7, WATER[5], 220)
            _set(rgba, (np.abs(px - sx) == 2 * sc) & (py == base - 3 * sc), WATER[5], 200)
    return Sprite(rgba, 9 * sc, base)


def star_streak(frame, frames, k):
    """A white-to-transparent streak; the head (bright end) is at the right, anchored there."""
    sc = max(1, k // 2) if k >= 2 else 1
    w, h = 48 * sc, 3 * sc
    px, py, rgba = _canvas(w, h)
    t = (px + 0.5) / w
    core = np.abs(py + 0.5 - h / 2) < 0.5 * sc + t * 0.6 * sc
    _set(rgba, core, SNOW[2])
    rgba[..., 3] = np.where(core, (255 * t ** 1.5).astype(np.uint8), 0)
    rgba[core & (px >= w - 3 * sc), :3] = _rgb(GLOW[2])
    return Sprite(rgba, w - 1, h // 2)


APPLES = ((".Gg.", ".B..", "rrRR", "rrRR", "RRRD", ".DD."),
          ("..g.", ".B..", "rrRR", "RRRD", ".vv."))


def apple(frame, frames, k):
    return _stencil(APPLES[frame % 2], k)


def clear(frame, frames, k):
    """Brambles bursting into leaves and dust as wild land opens; particles fly out and fade."""
    sc = max(1, k // 2) if k >= 2 else 1
    w, h = 48 * sc, 32 * sc
    px, py, rgba = _canvas(w, h)
    t = (frame + 1) / frames
    rng = np.random.Generator(np.random.PCG64([81]))
    cx, cy = w / 2, h - 8 * sc
    # A dust cloud that swells and thins.
    d = np.hypot((px + 0.5 - cx) / (10 * sc * (0.4 + t)), (py + 0.5 - cy) / (4 * sc * (0.4 + t)))
    dust = (d < 1) & (dither(np.full(px.shape, 1.5 - t * 1.3), px, py) >= 1)
    _set(rgba, dust, EARTH[4], int(130 - 100 * t))
    for n in range(30):
        a = rng.uniform(-math.pi * 0.95, -0.05)
        speed = rng.uniform(12, 28) * sc
        x = cx + math.cos(a) * speed * t
        y = cy + math.sin(a) * speed * t + 20 * sc * t * t
        color = (PINE[1], LEAF[2], LEAF[3], EARTH[2], ROOF[1])[n % 5]
        size = 2 if n % 3 else 3
        m = (np.abs(px + 0.5 - x) < size * sc * 0.5 + 0.01) & (np.abs(py + 0.5 - y) < size * sc * 0.5 + 0.01)
        if frame < frames - 1 or n % 2:
            _set(rgba, m, color, 255 if t < 0.7 else 170)
    return Sprite(rgba, int(cx), int(cy))


def mist(frame, frames, k):
    """Soft white spray at a waterfall's foot: overlapping puffs that drift and shimmer."""
    sc = max(1, k // 2) if k >= 2 else 1
    w, h = 40 * sc, 16 * sc
    px, py, rgba = _canvas(w, h)
    t = frame / frames
    inside = np.zeros(px.shape, np.float32)
    for n in range(7):
        a = 2 * math.pi * (t + n / 7)
        cx = (6 + n * 4.6 + 1.2 * math.sin(a)) * sc
        cy = (10 - 2.5 * abs(math.sin(a * 0.5 + n))) * sc
        r = (4.0 + 1.2 * math.sin(a + n)) * sc
        inside = np.maximum(inside, 1 - np.hypot(px + 0.5 - cx, (py + 0.5 - cy) * 1.6) / r)
    body = inside > 0
    _set(rgba, body, SNOW[1])
    _set(rgba, inside > 0.45, SNOW[2])
    holes = dither(np.full(px.shape, 1.4), px + frame, py) < 1
    rgba[..., 3] = np.where(body & ~(holes & (inside < 0.3)), np.where(inside > 0.45, 170, 110), 0)
    return Sprite(rgba, w // 2, h - 2 * sc)


ZEDS = (("WWW", "..W", ".W.", "WWW"), ("WWWW", "..W.", ".W..", "WWWW"), ("WWWW", "..W.", ".W..", "WWWW"))


def zzz(frame, frames, k):
    """A small z drifting up and fading (the rise is in the sprite)."""
    sp = _stencil(ZEDS[frame % 3], k, alpha=(255, 230, 140)[frame % 3])
    f = max(1, k // 2) if k >= 2 else 1
    rise = (0, 3, 6)[frame % 3] * f
    pad = np.zeros((sp.rgba.shape[0] + rise + 2 * f, sp.rgba.shape[1] + 2 * f, 4), np.uint8)
    pad[:sp.rgba.shape[0], (frame % 3) * f:(frame % 3) * f + sp.rgba.shape[1]] = sp.rgba
    return Sprite(pad, sp.ox, pad.shape[0] - 1)


PRODUCE = (
    # cabbage
    ("....vGGv....", "..vGgggGGv..", ".vGggGggggv.", "vGgGgGgggGGv", "vGggGgggGgGv",
     ".vGgGgGgGgv.", "..vGGGGGGv..", "....vvvv...."),
    # a bunch of carrots
    ("..g.g.g.....", "...ggg.g....", "..gGgGg.....", "...oOoO.....", "...oOOo.....",
     "....oOo.....", "....oO......", ".....o......"),
    # pumpkin
    ("....BB......", "..oOoOoOo...", ".oOoOOoOOo..", "oOoOOoOOoOo.", "oOoOOoOOoOo.",
     ".oOoOOoOOo..", "..ooooooo..."),
    # tomatoes on the vine
    ("...vGv......", ".RRgRR......", "RrRRRrRR....", "RRRRRRRRR...", ".RRDRRrRR...",
     "..DD.RRRR...", ".....DDD...."),
)


def produce(frame, frames, k):
    """Frame k is the crop of veggie bed variant r<k>, for the harvest pop."""
    return _stencil(PRODUCE[frame % 4], k)


EFFECTS = {"smoke": smoke, "ripple": ripple, "sparkle": sparkle, "raindrop": raindrop, "leaf": leaf,
           "heart": heart, "petal": petal, "snowflake": snowflake, "moth": moth, "fish_jump": fish_jump,
           "star_streak": star_streak, "apple": apple, "clear": clear, "mist": mist, "zzz": zzz,
           "produce": produce}


def build(keys: list[str], cat: dict, k: int) -> dict[str, Sprite]:
    parsed = {key: (key.split("/")[1], int(key.split("/")[2][1:])) for key in keys}
    frames = {}
    for name, f in parsed.values():
        frames[name] = max(frames.get(name, 0), f + 1)
    return {key: EFFECTS[name](f, frames[name], k) for key, (name, f) in parsed.items()}
