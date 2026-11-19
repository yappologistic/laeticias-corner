"""Falling and stepping water (art-smooth-land.md §4): where water drops to lower water, one
level of face at a time, as the engine stacks faces (`edge/world.fall_<se|sw>/...`):

- `top/f<k>`: the uppermost level: the flat water bends over the lip in a glassy roll, the
  sheet starting to tear into streaks below it; it reaches a few rows up over the upper tile.
- `f<k>`: any level between: a sheet of falling streaks over wet rock, thinner and broken where
  the rock shows through. It repeats every level down the face, so a shader can scroll it.
- `foot/f<k>`: the lowest level, where the sheet meets the pool in a white boil.
- `rapid/f<k>`: a drop of a single level: water tumbling white over stones, not a wall.

On the lower water tile: `terrain/world.river/plunge/m<mask>/f<k>` (foam spreading from each
edge with higher water beyond it, mask bits N 1, E 2, S 4, W 8 of those edges) and on a tile
whose flow leaves over a drop `terrain/world.river/rapids_<n|e>/f<k>` (white water speeding up
toward the edge; the engine mirrors them for w and s, as for `flow_*`).

Every field repeats along the edge every tile and down the face every level, and moves by a
whole number of periods over the loop, so falls join across a river's tiles, stack down a
cliff and loop with no step. Falls are colour-only (their foam and spray are translucent)."""

from __future__ import annotations

import numpy as np

import terrain as home
from land import face_grid, periodic
from palette import INK, PLASTER, SHALLOW, SNOW, STONE, WATER
from pack import Sprite
from voxel import hash01

# The frame fallback keeps the water's one loop (4 steps at 4 fps: ground cells cache once per
# step); the sheet moves one level down the face per loop. A shader scrolls the `mid` level by
# the catalog's `art.falls.speed_px_s` instead, the frames' pattern repeating every level.
FRAMES = 4
FPS = 4
LEVELS_PER_LOOP = 1
SHEET = [WATER[1], WATER[2], WATER[3], WATER[4], SHALLOW[4], WATER[5], SNOW[1], SNOW[2]]
FOAM = [SHALLOW[3], WATER[5], SNOW[1], SNOW[2], PLASTER[4]]
WET_ROCK = [INK, STONE[0], STONE[1], STONE[2]]


def _streaks(s, d, W, band, k, t, seed):
    """Brightness (0..1) of falling streaks: per column a pattern repeating every band down the
    face, moving down LEVELS_PER_LOOP bands per loop; columns drift sideways a little so streaks
    braid instead of running as rods."""
    col = np.floor(s).astype(np.int64) % W
    braid = 1.2 * k * np.sin(2 * np.pi * (d / band + hash01(col // 3, seed, 1)))
    c2 = np.floor(s + braid).astype(np.int64) % W
    phase = (d / band - LEVELS_PER_LOOP * t + hash01(c2, seed, 2)) % 1.0
    lengthy = 0.25 + 0.35 * hash01(c2, seed, 3)
    head = np.clip(1 - phase / lengthy, 0, 1)
    second = (d / (band / 2) - 2 * LEVELS_PER_LOOP * t + hash01(c2, seed, 4)) % 1.0
    return np.clip(head * 0.9 + (second < 0.18) * 0.5 * hash01(c2, seed, 5), 0, 1), c2


def _thickness(s, W, band, seed, v):
    """How full the sheet is along the edge (0 thin, the rock showing; 1 full), common to all
    levels so a fall's gaps run straight down."""
    return periodic(s, np.zeros_like(s), W, band, 2.2, seed, v)


def _sprite(rgb, alpha, H, W, ox, oy):
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Sprite(rgba, ox, oy)


def face(part: str, side: str, frame: int, k: int, ends: int = 3) -> Sprite:
    """One level of falling water: `part` is "top", "mid", "foot" or "rapid"; `ends` says where
    the falling water goes on beyond this tile along the edge (bit 1: past its s = 0 end, the
    outer corner; bit 2: past its far end). Where it does not, the sheet pulls in from the bank
    and wet rock stands beside it."""
    above = 4 * k if part in ("top", "rapid") else 0
    px, py, s, d, band, H, W, ox, oy = face_grid(side, k, above)
    band = float(band)
    t = frame / FRAMES
    shade = -0.6 if side == "se" else 0.0
    on = (d >= 0) & (d < band)
    dd = np.clip(d, 0, band - 1)
    seed = 12001
    thick = _thickness(s, W, band, seed, 0)
    lum, col = _streaks(s, dd, W, band, k, t, seed + 10)
    lvl = 1.5 + shade + lum * 3.1 + (thick - 0.5) * 0.9 + (hash01(px, py, seed + 20 + frame) - 0.5) * 0.4
    rgb = home._paint(SHEET, lvl, px, py, k=k)
    # Where the sheet thins the wet rock behind shows through for a moment, dark and glistening.
    gap = (thick < 0.2) & (lum < 0.25)
    rock = home._paint(WET_ROCK, 1.6 + shade + periodic(s, dd, W, band, 3.0, seed + 30) * 1.6, px, py, k=k)
    rgb = np.where(gap[..., None], rock, rgb)
    # The banks: a sheet that does not go on along the edge pulls in from that end, a wet stone
    # edge beside it and a pale curl of water along the sheet's side.
    for bit, dist in ((1, s), (2, W - s)):
        if ends & bit:
            continue
        inset = (2.0 + 1.0 * periodic(s * 0, dd, W, band, 2.0, seed + 31 + bit)) * k
        bank = dist < inset
        curl = (dist >= inset) & (dist < inset + 1)
        rgb = np.where(bank[..., None], home._paint(WET_ROCK, 1.8 + shade + (hash01(px // 2, py // 2, seed + 32) > 0.6)
                                                     + (dist > inset - 1.5) * 0.8, px, py, k=k), rgb)
        rgb = np.where((curl & ~bank)[..., None], home._paint(SHEET, np.full(s.shape, 5.0 + shade), px, py, k=k), rgb)
    alpha = on * 255.0
    if part in ("top", "rapid"):
        # The lip: a glassy roll of unbroken water at the top of the face, with a pale rim of
        # light where it bends, and slick acceleration lines on the upper tile above the edge.
        roll = on & (d < 2.5 * k)
        rgb = np.where(roll[..., None], home._paint(SHEET, 2.6 + shade + (d < k) * 2.0 - d / (3 * k), px, py, k=k), rgb)
        slick = (d < 0) & (d >= -above)
        lines = slick & (((np.floor(s / 2).astype(np.int64) + np.floor((d + 99) / 2 - 4 * t).astype(np.int64)) %
                          5) == 0) & (hash01(col, seed + 40) < 0.6)
        rgb = np.where(lines[..., None], home._paint(SHEET, np.full(s.shape, 4.0 + shade), px, py, k=k), rgb)
        alpha = np.where(lines, 150, alpha)
    if part == "rapid":
        # One level: the water tumbles over a step of stones, white and broken.
        stones = (periodic(s, dd, W, band, 2.8, seed + 50) > 0.62) & (dd > 3 * k)
        boil = (hash01(px // 2, (py - 4 * frame) // 2, seed + 51) < 0.45) & (dd > 2 * k)
        rgb = np.where(boil[..., None], home._paint(FOAM, 2.0 + hash01(px, py, seed + 52 + frame) * 2.5, px, py, k=k), rgb)
        srock = home._paint(WET_ROCK, 1.4 + shade + (periodic(s, dd, W, band, 6.0, seed + 53) > 0.5), px, py, k=k)
        rgb = np.where((stones & ~boil)[..., None], srock, rgb)
    if part in ("foot", "rapid"):
        # The boil where the sheet meets the pool: white water churning at the bottom rows.
        low = on & (d > band - 5 * k)
        churn = low & (hash01(px // 2, (py + 3 * frame) // 2, seed + 60) < 0.55 + 0.4 * (d > band - 2.5 * k))
        rgb = np.where(churn[..., None], home._paint(FOAM, 2.4 + hash01(px, py, seed + 61 + frame) * 2.0, px, py, k=k), rgb)
    return _sprite(rgb, alpha, H, W, ox, oy)


def plunge(mask: int, frame: int, k: int) -> Sprite:
    """Foam on the lower pool along each edge with higher water beyond it: a white band where
    the fall lands, broken foam drifting out and fading, rings spreading, on the loop."""
    g = home._grid(k)
    t = frame / FRAMES
    alpha = np.zeros(g.u.shape, np.float32)
    level = np.zeros(g.u.shape, np.float32)
    edges = [(1, g.v, g.u), (4, 16 - g.v, g.u), (8, g.u, g.v), (2, 16 - g.u, g.v)]
    for bit, dist, along in edges:
        if not mask & bit:
            continue
        wob = home._pnoise(along, along * 0, 4, 12101 + bit) - 0.5
        band = dist < 1.4 + wob * 0.8
        drift = (dist - 6.0 * t) % 6.0
        bits = (hash01(np.floor(along * 1.5).astype(np.int64) % 24, np.floor(dist - 6.0 * t).astype(np.int64) % 6, 12102 + bit)
                < 0.35 * np.clip(1 - dist / 7.0, 0, 1)) & (drift < 2.2)
        ring = np.abs(((dist + 3 * t * 4) % 4.0) - 2.0) < 0.18
        ring &= (dist < 5.5) & (home._pnoise(along, dist, 4, 12103 + bit) > 0.5)
        a = np.where(band, 0.95, np.where(bits, 0.7 * np.clip(1 - dist / 7.0, 0.2, 1), np.where(ring, 0.35, 0)))
        alpha = np.maximum(alpha, a)
        level = np.maximum(level, np.where(band, 3.2, np.where(bits, 2.4, np.where(ring, 1.8, 0))))
    rgb = home._paint(FOAM, level + (hash01(g.px, g.py, 12104 + frame) - 0.5) * 0.8, g.px, g.py, k=k)
    return home._sprite(g, rgb, (alpha * 255).astype(np.uint8) * g.inside)


def rapids(direction: str, frame: int, k: int) -> Sprite:
    """White water speeding up toward the edge a flow leaves over: streaks lengthening as they
    near it, standing waves, foam. `n` flows toward -y, `e` toward +x (mirrored for w, s)."""
    g = home._grid(k)
    t = frame / FRAMES
    along = (16 - g.v) if direction == "n" else g.u          # distance travelled toward the edge
    across = g.u if direction == "n" else g.v
    speed = 0.5 + along / 16.0
    phase = (along * 0.35 - 2 * t * 4 + hash01(np.floor(across * 1.5).astype(np.int64) % 24, 12201) * 4) % 1.0
    streak = (phase < 0.18 + 0.3 * along / 16) & (hash01(np.floor(across * 1.5).astype(np.int64) % 24, 12202) < 0.7)
    wave = (np.abs(((along + 1.3 * np.sin(across * 0.8)) % 4.0) - 2.0) < 0.35) & (along > 6)
    mid = np.clip(1 - np.abs(across - 8.0) / 7.0, 0, 1)
    a = np.where(streak, 0.75, np.where(wave, 0.55, 0.0)) * np.clip(speed - 0.4, 0, 1) * mid
    level = np.where(streak, 3.0, 2.2) + (hash01(g.px, g.py, 12203 + frame) - 0.5)
    rgb = home._paint(FOAM, level, g.px, g.py, k=k)
    return home._sprite(g, rgb, (a * 255).astype(np.uint8) * g.inside)
