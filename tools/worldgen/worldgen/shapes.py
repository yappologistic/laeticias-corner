"""Shapes a layout paints with: rectangles, polygons, polylines with width, ellipses, and their
unions and differences. Coordinates are plan tiles (c east, r south), inclusive rectangles.

Every shape answers two questions: its inclusive bounding box, and a boolean mask over any window.
`shifted` moves a shape, which is how a region's local coordinates become world coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import raster

Bounds = tuple[int, int, int, int]  # c0, r0, c1, r1 inclusive


class Shape:
    def bounds(self) -> Bounds:
        raise NotImplementedError

    def mask(self, c0: int, r0: int, w: int, h: int) -> np.ndarray:
        raise NotImplementedError

    def shifted(self, dc: int, dr: int) -> "Shape":
        raise NotImplementedError

    def __or__(self, other: "Shape") -> "Shape":
        return Union((self, as_shape(other)))

    def __sub__(self, other: "Shape") -> "Shape":
        return Minus(self, as_shape(other))

    def __and__(self, other: "Shape") -> "Shape":
        return Minus(self, Minus(self, as_shape(other)))

    def tiles(self) -> list[tuple[int, int]]:
        """Covered tiles in row-major order (r, then c)."""
        c0, r0, c1, r1 = self.bounds()
        m = self.mask(c0, r0, c1 - c0 + 1, r1 - r0 + 1)
        rr, cc = np.nonzero(m)
        return [(int(c) + c0, int(r) + r0) for r, c in zip(rr, cc)]


@dataclass(frozen=True)
class Rect(Shape):
    c0: int
    r0: int
    c1: int
    r1: int

    def __post_init__(self):
        if self.c1 < self.c0 or self.r1 < self.r0:
            raise ValueError(f"Rect{(self.c0, self.r0, self.c1, self.r1)}: c1 < c0 or r1 < r0")

    @property
    def w(self) -> int:
        return self.c1 - self.c0 + 1

    @property
    def h(self) -> int:
        return self.r1 - self.r0 + 1

    def bounds(self) -> Bounds:
        return (self.c0, self.r0, self.c1, self.r1)

    def mask(self, c0, r0, w, h):
        out = np.zeros((h, w), dtype=bool)
        a0, b0 = max(self.c0 - c0, 0), max(self.r0 - r0, 0)
        a1, b1 = min(self.c1 - c0 + 1, w), min(self.r1 - r0 + 1, h)
        if a1 > a0 and b1 > b0:
            out[b0:b1, a0:a1] = True
        return out

    def shifted(self, dc, dr):
        return Rect(self.c0 + dc, self.r0 + dr, self.c1 + dc, self.r1 + dr)

    def contains(self, c: int, r: int) -> bool:
        return self.c0 <= c <= self.c1 and self.r0 <= r <= self.r1


@dataclass(frozen=True)
class Poly(Shape):
    """Even-odd polygon; vertices are tiles (their centres), boundary tiles included."""

    points: tuple[tuple[int, int], ...]

    def __init__(self, points):
        object.__setattr__(self, "points", tuple((int(c), int(r)) for c, r in points))
        if len(self.points) < 3:
            raise ValueError("Poly needs at least three points")

    def bounds(self):
        cs = [p[0] for p in self.points]
        rs = [p[1] for p in self.points]
        return (min(cs), min(rs), max(cs), max(rs))

    def mask(self, c0, r0, w, h):
        return raster.poly_mask(list(self.points), c0, r0, w, h)

    def shifted(self, dc, dr):
        return Poly([(c + dc, r + dr) for c, r in self.points])


@dataclass(frozen=True)
class Line(Shape):
    """Tiles within width / 2 of a polyline through tile centres (see raster.line_mask)."""

    points: tuple[tuple[int, int], ...]
    width: int = 1

    def __init__(self, points, width: int = 1):
        object.__setattr__(self, "points", tuple((int(c), int(r)) for c, r in points))
        object.__setattr__(self, "width", int(width))
        if not self.points:
            raise ValueError("Line needs at least one point")
        if self.width < 1:
            raise ValueError("Line width must be at least 1")

    def bounds(self):
        m = self.width // 2 + 1
        cs = [p[0] for p in self.points]
        rs = [p[1] for p in self.points]
        return (min(cs) - m, min(rs) - m, max(cs) + m, max(rs) + m)

    def mask(self, c0, r0, w, h):
        return raster.line_mask(list(self.points), self.width, c0, r0, w, h)

    def shifted(self, dc, dr):
        return Line([(c + dc, r + dr) for c, r in self.points], self.width)

    def path(self) -> list[tuple[int, int]]:
        """The 4-connected centre walk."""
        return raster.path_tiles(list(self.points))


@dataclass(frozen=True)
class Ellipse(Shape):
    cc: int
    rc: int
    rx: float
    ry: float

    def bounds(self):
        return (int(self.cc - self.rx) - 1, int(self.rc - self.ry) - 1,
                int(self.cc + self.rx) + 1, int(self.rc + self.ry) + 1)

    def mask(self, c0, r0, w, h):
        return raster.ellipse_mask(self.cc, self.rc, self.rx, self.ry, c0, r0, w, h)

    def shifted(self, dc, dr):
        return Ellipse(self.cc + dc, self.rc + dr, self.rx, self.ry)


@dataclass(frozen=True)
class Union(Shape):
    parts: tuple[Shape, ...]

    def bounds(self):
        bs = [p.bounds() for p in self.parts]
        return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs),
                max(b[3] for b in bs))

    def mask(self, c0, r0, w, h):
        out = np.zeros((h, w), dtype=bool)
        for p in self.parts:
            out |= p.mask(c0, r0, w, h)
        return out

    def shifted(self, dc, dr):
        return Union(tuple(p.shifted(dc, dr) for p in self.parts))


@dataclass(frozen=True)
class Minus(Shape):
    a: Shape
    b: Shape

    def bounds(self):
        return self.a.bounds()

    def mask(self, c0, r0, w, h):
        return self.a.mask(c0, r0, w, h) & ~self.b.mask(c0, r0, w, h)

    def shifted(self, dc, dr):
        return Minus(self.a.shifted(dc, dr), self.b.shifted(dc, dr))


@dataclass(frozen=True, eq=False)
class Mask(Shape):
    """An explicit set of tiles: a boolean array whose [0, 0] is plan tile (c0, r0)."""

    c0: int
    r0: int
    array: np.ndarray

    def bounds(self):
        h, w = self.array.shape
        return (self.c0, self.r0, self.c0 + w - 1, self.r0 + h - 1)

    def mask(self, c0, r0, w, h):
        out = np.zeros((h, w), dtype=bool)
        ah, aw = self.array.shape
        i0, j0 = max(self.c0 - c0, 0), max(self.r0 - r0, 0)
        i1, j1 = min(self.c0 + aw - c0, w), min(self.r0 + ah - r0, h)
        if i1 > i0 and j1 > j0:
            out[j0:j1, i0:i1] = self.array[j0 + r0 - self.r0:j1 + r0 - self.r0,
                                           i0 + c0 - self.c0:i1 + c0 - self.c0]
        return out

    def shifted(self, dc, dr):
        return Mask(self.c0 + dc, self.r0 + dr, self.array)


def as_shape(x) -> Shape:
    """A Shape, or a 4-tuple (c0, r0, c1, r1) read as an inclusive Rect."""
    if isinstance(x, Shape):
        return x
    if isinstance(x, (tuple, list)) and len(x) == 4:
        return Rect(*(int(v) for v in x))
    raise TypeError(f"not a shape: {x!r}")
