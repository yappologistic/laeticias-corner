"""Small effect sprites, drawn directly in screen space at k pixels per design unit. Anchors are
the contact point: the bottom of a smoke puff, the centre of a ripple or sparkle, where a
raindrop lands. Shapes scale with k; lines and glints stay a pixel wide, so finer builds get
finer effects rather than enlarged ones."""

import math

import numpy as np

from pack import Sprite
from palette import LEAF, PLASTER, STONE, STRAW, GLOW, WATER, EARTH, _rgb
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


EFFECTS = {"smoke": smoke, "ripple": ripple, "sparkle": sparkle, "raindrop": raindrop, "leaf": leaf}


def build(frames: dict[str, int], k: int) -> dict[str, Sprite]:
    return {f"fx/{name}/f{f}": EFFECTS[name](f, n, k) for name, n in frames.items() for f in range(n)}
