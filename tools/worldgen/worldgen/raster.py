"""Exact integer rasterisation of polygons and polylines onto the tile grid.

All coordinates are plan tiles (c east, r south). A tile is the unit square [c, c+1) x [r, r+1);
"inside" always means its centre (c + 0.5, r + 0.5) is inside.
"""

from __future__ import annotations

import math

import numpy as np


def poly_mask(points: list[tuple[float, float]], c0: int, r0: int, w: int, h: int) -> np.ndarray:
    """Even-odd fill of a polygon given by its vertices (tile coordinates of vertex points).

    Vertices name tiles, so a vertex (c, r) stands for the point (c + 0.5, r + 0.5): a polygon
    through tile centres covers the tiles it names on its axis-aligned edges.
    """
    out = np.zeros((h, w), dtype=bool)
    n = len(points)
    if n < 3 or w <= 0 or h <= 0:
        return out
    px = np.array([p[0] for p in points], dtype=np.float64) + 0.5
    py = np.array([p[1] for p in points], dtype=np.float64) + 0.5
    qx = np.roll(px, -1)
    qy = np.roll(py, -1)
    cx = np.arange(c0, c0 + w, dtype=np.float64) + 0.5
    for j in range(h):
        y = r0 + j + 0.5
        # Edges straddling the scanline (half-open in y so shared vertices count once).
        lo = np.minimum(py, qy)
        hi = np.maximum(py, qy)
        # Centres on the boundary count as inside, so edges through tile centres include their
        # tiles: horizontal edges lying on this scanline, and every edge touching it.
        flat = (py == y) & (qy == y)
        for k in np.nonzero(flat)[0]:
            a, b = sorted((px[k], qx[k]))
            out[j] |= (cx >= a) & (cx <= b)
        touch = (lo <= y) & (y <= hi) & ~flat
        if touch.any():
            xt = px[touch] + (y - py[touch]) * (qx[touch] - px[touch]) / (qy[touch] - py[touch])
            out[j] |= np.isin(cx, xt)
        sel = (lo <= y) & (y < hi)
        if not sel.any():
            continue
        xs = px[sel] + (y - py[sel]) * (qx[sel] - px[sel]) / (qy[sel] - py[sel])
        xs.sort()
        crossings = np.searchsorted(xs, cx, side="right")
        out[j] |= crossings % 2 == 1
    return out


def _seg_dist2(cx: np.ndarray, cy: np.ndarray, a: tuple[float, float],
               b: tuple[float, float]) -> np.ndarray:
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    ll = dx * dx + dy * dy
    if ll == 0:
        return (cx - ax) ** 2 + (cy - ay) ** 2
    t = np.clip(((cx - ax) * dx + (cy - ay) * dy) / ll, 0.0, 1.0)
    return (cx - (ax + t * dx)) ** 2 + (cy - (ay + t * dy)) ** 2


def path_tiles(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """4-connected walk through tile centres along a polyline (no repeats of consecutive tiles).

    Each segment steps one tile at a time, choosing the axis that keeps closest to the exact line,
    so straight runs are exact and diagonals become even staircases.
    """
    out: list[tuple[int, int]] = []
    for i in range(len(points) - 1):
        (c, r), (c1, r1) = points[i], points[i + 1]
        dc, dr = c1 - c, r1 - r
        sc = 1 if dc > 0 else -1
        sr = 1 if dr > 0 else -1
        n = abs(dc) + abs(dr)
        if not out or out[-1] != (c, r):
            out.append((c, r))
        ic = ir = 0
        for _ in range(n):
            # Error of stepping in c vs in r relative to the ideal line, by cross product.
            if ic == abs(dc):
                ir += 1
            elif ir == abs(dr):
                ic += 1
            elif abs((ic + 1) * abs(dr) - ir * abs(dc)) <= abs(ic * abs(dr) - (ir + 1) * abs(dc)):
                ic += 1
            else:
                ir += 1
            out.append((c + sc * ic, r + sr * ir))
    if len(points) == 1:
        out.append(tuple(points[0]))
    return out


def line_mask(points: list[tuple[int, int]], width: int, c0: int, r0: int, w: int,
              h: int) -> np.ndarray:
    """Tiles within width / 2 of the polyline, always including a 4-connected centre walk.

    Odd widths centre on the tiles named by the points; even widths centre on their south-east
    corners, so a width-2 line along row r covers rows r and r + 1 (straight runs are exact).
    """
    out = np.zeros((h, w), dtype=bool)
    if w <= 0 or h <= 0:
        return out
    off = 0.5 if width % 2 == 1 else 1.0
    half = width / 2.0
    half2 = half ** 2
    pts = [(p[0] + off, p[1] + off) for p in points]
    if len(pts) == 1:
        pts = pts * 2
    for a, b in zip(pts, pts[1:]):
        # Only the segment's bounding box (grown by the half width) can be inside.
        i0 = max(int(math.floor(min(a[0], b[0]) - half)) - c0 - 1, 0)
        i1 = min(int(math.ceil(max(a[0], b[0]) + half)) - c0 + 1, w)
        j0 = max(int(math.floor(min(a[1], b[1]) - half)) - r0 - 1, 0)
        j1 = min(int(math.ceil(max(a[1], b[1]) + half)) - r0 + 1, h)
        if i1 <= i0 or j1 <= j0:
            continue
        r, c = np.mgrid[r0 + j0:r0 + j1, c0 + i0:c0 + i1]
        out[j0:j1, i0:i1] |= _seg_dist2(c + 0.5, r + 0.5, a, b) < half2 - 1e-9
    for (tc, tr) in path_tiles([tuple(p) for p in points]):
        if c0 <= tc < c0 + w and r0 <= tr < r0 + h:
            out[tr - r0, tc - c0] = True
    return out


def ellipse_mask(cc: float, rc: float, rx: float, ry: float, c0: int, r0: int, w: int,
                 h: int) -> np.ndarray:
    r, c = np.mgrid[r0:r0 + h, c0:c0 + w]
    return ((c + 0.5 - (cc + 0.5)) / rx) ** 2 + ((r + 0.5 - (rc + 0.5)) / ry) ** 2 <= 1.0
