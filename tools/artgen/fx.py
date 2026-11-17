"""Small effect sprites, drawn directly in screen space. Anchors are the contact point:
the bottom of a smoke puff, the centre of a ripple or sparkle, where a raindrop lands."""

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


def smoke(frame, frames):
    """A puff that swells and thins out; the engine moves it upward."""
    t = frame / (frames - 1)
    r = 2.0 + 3.2 * t
    w = h = 14
    px, py, rgba = _canvas(w, h)
    cx, cy = 7, h - 1 - r
    d = np.hypot(px + 0.5 - cx, (py + 0.5 - cy) * 1.1)
    lobes = d < r + 0.6 * np.sin(np.arctan2(py - cy, px - cx) * 3 + frame)
    lit = (px - cx) * -0.6 + (py - cy) * -0.8 > r * 0.15
    level = np.where(lit, 2.0, 1.0) - t * 0.6
    ramp = [STONE[3], STONE[4], PLASTER[3]]
    idx = np.clip(dither(level, px, py), 0, 2).astype(np.int64)
    rgba[..., :3] = np.array([_rgb(c) for c in ramp], np.uint8)[idx]
    alpha = int(210 - 150 * t)
    # Thin the puff out with an ordered pattern as it fades so it never looks like a disc.
    keep = dither(np.full(px.shape, 1.6 - t), px, py) >= 1
    rgba[..., 3] = np.where(lobes & keep, alpha, 0)
    return Sprite(rgba, 7, h)


def ripple(frame, frames):
    t = frame / (frames - 1)
    r = 2.5 + 5.5 * t
    w, h = 21, 11
    px, py, rgba = _canvas(w, h)
    d = np.hypot(px + 0.5 - 10.5, (py + 0.5 - 5.5) * 2)
    ring = np.abs(d - r) < 0.75
    _set(rgba, ring, WATER[5], int(230 - 140 * t))
    _set(rgba, ring & (py + 0.5 > 5.5), WATER[4], int(230 - 140 * t))
    return Sprite(rgba, 10, 5)


def sparkle(frame, frames):
    size = (1, 2, 3, 1)[frame % 4]
    px, py, rgba = _canvas(7, 7)
    dx, dy = np.abs(px - 3), np.abs(py - 3)
    star = ((dx == 0) & (dy <= size)) | ((dy == 0) & (dx <= size))
    _set(rgba, star, GLOW[1])
    _set(rgba, (dx + dy == 0) | (star & (dx + dy <= size - 2)), GLOW[2])
    if size == 3:
        _set(rgba, (dx == 1) & (dy == 1), GLOW[1], 140)
    return Sprite(rgba, 3, 3)


def raindrop(frame, frames):
    """f0: the falling streak; f1..: the splash where it lands."""
    px, py, rgba = _canvas(9, 7)
    if frame == 0:
        _set(rgba, (px == 4) & (py >= 1) & (py <= 4), WATER[5], 170)
        _set(rgba, (px == 4) & (py == 5), PLASTER[4], 210)
        return Sprite(rgba, 4, 6)
    r = frame * 1.4
    d = np.hypot(px + 0.5 - 4.5, (py + 0.5 - 5.5) * 2)
    _set(rgba, np.abs(d - r) < 0.7, WATER[5], int(220 - 50 * frame))
    if frame == 1:
        _set(rgba, (np.abs(px - 4) == 1) & (py == 3), WATER[5], 200)
    return Sprite(rgba, 4, 5)


def leaf(frame, frames):
    a = frame / frames * math.pi
    px, py, rgba = _canvas(7, 7)
    u = (px - 3) * math.cos(a) + (py - 3) * math.sin(a)
    v = -(px - 3) * math.sin(a) + (py - 3) * math.cos(a)
    flat = 0.45 + 0.55 * abs(math.cos(a * 1.5))
    shape = (u / 2.8) ** 2 + (v / (1.5 * flat)) ** 2 <= 1
    _set(rgba, shape, LEAF[4])
    _set(rgba, shape & (v > 0.3), LEAF[3])
    _set(rgba, shape & (np.abs(v) < 0.5) & (np.abs(u) < 2), STRAW[2])
    _set(rgba, (np.abs(u - 3.2) < 0.6) & (np.abs(v) < 0.6), EARTH[2])
    return Sprite(rgba, 3, 3)


EFFECTS = {"smoke": smoke, "ripple": ripple, "sparkle": sparkle, "raindrop": raindrop, "leaf": leaf}


def build(frames: dict[str, int]) -> dict[str, Sprite]:
    return {f"fx/{name}/f{f}": EFFECTS[name](f, n) for name, n in frames.items() for f in range(n)}
