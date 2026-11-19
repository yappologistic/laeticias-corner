"""Water inside items, drawn to the falls' standard (falls.py): a basin's surface and a spout's
falling stream, for fountains, street basins and springs in every set.

- A surface is darker where it is deep and lighter over the shallow rim, with a thin bright line
  where it touches the stone; rings spread from where streams land and move outward over the
  item's frames (one loop), with a white boil at each landing point; a few sparse glints.
- A stream leaves its spout as a glassy rod (lit on the side toward the sun, which is up and to
  the left: -x, -y), swells a little as it falls, its streaks scrolling downward one loop per
  cycle, and breaks into drops just above the boil.

Everything is the `water` material (a water ramp, so the shader path's water page marks it and
gives it depth; `datapages.write_water_page`), white water at its lightest step. Lengths are
design units; `frame / frames` is the loop's phase."""

from __future__ import annotations

import math

import numpy as np

from arch import fill
from voxel import hash01


def surface(m, box, z, frame, frames, sources=(), shape=None, seed=0, depth_units=3.0, rings=True, boil=True):
    """The top of the water in a basin `box` (x0, x1, y0, y1) at height `z` (the layer below z),
    over whatever `shape(X, Y)` allows (default: the whole box). `sources`: (x, y) where streams
    land, or where a spring wells up (`boil` False: rings without white water). `depth_units`:
    how far in from the rim the water reaches full depth."""
    x0, x1, y0, y1 = box
    t = (frame % max(frames, 1)) / max(frames, 1)

    def mask(X, Y, Z):
        ok = np.ones(np.broadcast(X, Y, Z).shape, bool)
        return ok if shape is None else ok & shape(X, Y)

    def tone(X, Y, Z):
        X, Y = np.broadcast_arrays(X, Y)[0], np.broadcast_arrays(X, Y)[1]
        if shape is None:
            rim = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Y - y0, y1 - Y))
        else:   # distance to the edge of the shape, by probing outward (cheap: a few rings)
            rim = np.full(X.shape, depth_units, np.float32)
            for r in np.linspace(0.5, depth_units, 6):
                for a in np.linspace(0, 2 * math.pi, 12, endpoint=False):
                    out = ~shape(X + r * math.cos(a), Y + r * math.sin(a))
                    rim = np.where(out & (r < rim), r, rim)
        deep = np.clip(rim / depth_units, 0, 1)
        out = 0.2 - 1.25 * deep ** 0.7                       # shallow rim lighter, deep middle darker
        out = out + 0.9 * (rim < 0.55)                       # the contact line on the stone
        for sx, sy in sources:
            d = np.hypot(X - sx, Y - sy)
            if rings:
                ph = d / 1.6 - t
                ring = (np.abs((ph % 1.0) - 0.5) < 0.12) & (d > 0.9) & (d < 7.0)
                out = out + ring * 0.75 * np.clip(1.2 - d / 7.0, 0, 1)
            white = d < 0.9 + 0.35 * hash01(np.floor(X * 3).astype(np.int64), np.floor(Y * 3).astype(np.int64),
                                           int(frame), seed + 1)
            out = np.where(white & boil, 1.8, out)
        glint = hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), int(frame), seed + 2) < 0.012
        return np.where(glint & (deep > 0.4), 1.4, out)

    fill(m, (x0, x1, y0, y1, z - 1.0, z), "water", mask, tone=tone, normal=(0.0, 0.0, 1.0))


def stream(m, lip, reach, land_z, frame, frames, r=0.45, seed=0):
    """A spout's stream from `lip` (x, y, z) leaving horizontally along `reach` (dx, dy: where it
    lands, relative to the lip) and falling to `land_z`. Returns the landing point (x, y)."""
    x0, y0, z0 = lip
    dx, dy = reach
    fall = max(z0 - land_z, 0.5)
    t = (frame % max(frames, 1)) / max(frames, 1)
    n = max(int(fall * 6), 8)
    s = np.linspace(0.0, 1.0, n)
    # A parabola: horizontal speed constant, the fall growing with the square of time.
    px, py, pz = x0 + dx * s, y0 + dy * s, z0 - fall * s * s
    lo = (min(px.min(), x0) - 2 * r - 0.5, max(px.max(), x0) + 2 * r + 0.5,
          min(py.min(), y0) - 2 * r - 0.5, max(py.max(), y0) + 2 * r + 0.5, land_z, z0 + r + 0.5)

    def nearest(X, Y, Z):
        best = np.full(np.broadcast(X, Y, Z).shape, 1e9, np.float32)
        along = np.zeros(best.shape, np.float32)
        for i in range(n):
            d = np.sqrt((X - px[i]) ** 2 + (Y - py[i]) ** 2 + (Z - pz[i]) ** 2)
            closer = d < best
            best = np.where(closer, d, best)
            along = np.where(closer, s[i], along)
        return best, along

    def mask(X, Y, Z):
        d, a = nearest(X, Y, Z)
        rad = r * (0.75 + 0.45 * a)                           # thin at the lip, fuller below
        body = d < rad
        # Near the foot the stream breaks into drops that slide down with the loop.
        drops = (a > 0.82) & (((Z - land_z) / 0.9 + t * 3.0) % 1.0 < 0.55)
        return body & ((a <= 0.82) | drops)

    def tone(X, Y, Z):
        d, a = nearest(X, Y, Z)
        streak = (((z0 - Z) / 1.1 - t * 2.0) % 1.0) < 0.35     # streaks travelling down
        braid = hash01(np.floor((X + Y) * 2).astype(np.int64), np.floor((z0 - Z) / 1.1 - t * 2.0).astype(np.int64),
                       seed + 3) < 0.4
        lit = (X - np.interp(a, s, px)) + (Y - np.interp(a, s, py)) < -0.1    # the side toward the sun
        out = 0.4 + 0.7 * lit + 0.5 * (streak & braid)
        return np.where(a < 0.08, 1.2, out)                    # the glassy roll at the lip

    fill(m, lo, "water", mask, tone=tone)
    return x0 + dx, y0 + dy
