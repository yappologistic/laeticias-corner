"""Voxel models: a material grid plus optional per-voxel normals and tone, with shape helpers.

Models are written in design units, 16 per tile edge, and sampled on a grid of `k` voxels per
design unit (k = 1 for 32x16 tiles, 2 for 64x32). z is up and one voxel tall projects to one
pixel. Shapes are boolean masks over voxel centres (in design units) so they compose with numpy
operators; the grid origin and shape are kept in voxels.
"""

from dataclasses import dataclass, field

import numpy as np

from palette import MAT
from spec import DESIGN_TILE


@dataclass
class Halo:
    """A soft additive light blob for the glow layer, at a point in design units."""
    x: float
    y: float
    z: float
    radius: float
    rgb: tuple[int, int, int]
    strength: float = 1.0


@dataclass
class Model:
    x0: int                              # grid origin, in voxels
    y0: int
    z0: int
    mat: np.ndarray                      # uint8 (nx, ny, nz), 0 = empty
    tone: np.ndarray                     # float32, ramp steps added to the lit level
    nrm: np.ndarray                      # float32 (nx, ny, nz, 3); zero = use the face normal
    halos: list[Halo] = field(default_factory=list)
    hover: bool = False                  # True when nothing rests on the ground (no contact AO)
    # Context voxels (a neighbour's joining arm): they occlude light but are never drawn.
    ghost: np.ndarray | None = None
    k: int = 1                           # voxels per design unit

    @classmethod
    def empty(cls, x0, x1, y0, y1, z0, z1, k=1) -> "Model":
        """An empty model over the box [x0,x1)x[y0,y1)x[z0,z1), given in design units."""
        shape = ((x1 - x0) * k, (y1 - y0) * k, (z1 - z0) * k)
        return cls(x0 * k, y0 * k, z0 * k, np.zeros(shape, np.uint8), np.zeros(shape, np.float32),
                   np.zeros(shape + (3,), np.float32), k=k)

    @property
    def fine(self) -> bool:
        """True when the grid can carry detail finer than a design unit (k >= 2). Shingle
        edges, hinges, mullions and the like are added only then: on the coarse grid they would
        be blocks, and the 32x16 atlas keeps its established look."""
        return self.k > 1

    def coords(self):
        """Voxel-centre coordinates in design units as broadcastable (nx,1,1), (1,ny,1), (1,1,nz)
        arrays."""
        nx, ny, nz = self.mat.shape
        X = ((np.arange(nx, dtype=np.float32) + self.x0 + 0.5) / self.k)[:, None, None]
        Y = ((np.arange(ny, dtype=np.float32) + self.y0 + 0.5) / self.k)[None, :, None]
        Z = ((np.arange(nz, dtype=np.float32) + self.z0 + 0.5) / self.k)[None, None, :]
        return X, Y, Z

    def window(self, cx, cy, cz, r):
        """Index slices of the voxels within a box of half-size r (or (rx, ry, rz)) around a
        point (design units), and their centre coordinates, so small shapes are evaluated
        locally instead of over the grid."""
        sl, axes = [], []
        k = self.k
        rs = np.broadcast_to(np.asarray(r, np.float64), (3,))
        for c, r, o, n in zip((cx, cy, cz), rs, (self.x0, self.y0, self.z0), self.mat.shape):
            a = max(int(np.floor((c - r) * k)) - o, 0)
            b = min(int(np.ceil((c + r) * k)) - o + 1, n)
            sl.append(slice(a, max(a, b)))
            axes.append((np.arange(a, max(a, b), dtype=np.float32) + o + 0.5) / k)
        X, Y, Z = axes
        return tuple(sl), X[:, None, None], Y[None, :, None], Z[None, None, :]

    def put(self, mask, material: str, tone=0.0, normal=None, only_empty=False, sl=None):
        """Set `mask` to `material`. With `sl` (from `window()`) the mask, tone and normal are
        shaped like that window instead of the whole grid."""
        mat, tn, nr = (self.mat, self.tone, self.nrm) if sl is None else \
            (self.mat[sl], self.tone[sl], self.nrm[sl])
        mask = np.broadcast_to(mask, mat.shape)
        if only_empty:
            mask = mask & (mat == 0)
        mat[mask] = MAT[material]
        tn[mask] = np.broadcast_to(np.asarray(tone, np.float32), mat.shape)[mask]
        if normal is None:
            nr[mask] = 0.0
        else:  # normalised only where it is stored
            n = np.stack([np.broadcast_to(c, mat.shape)[mask] for c in normal], axis=-1).astype(np.float32)
            n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
            nr[mask] = n

    def put_points(self, pts, material: str, tone=0.0, normal=None):
        """Set the voxels containing each point (N, 3) in design units; for thin stems and blades."""
        pts = np.asarray(pts, np.float32).reshape(-1, 3) * self.k
        i = np.floor(pts[:, 0]).astype(np.int64) - self.x0
        j = np.floor(pts[:, 1]).astype(np.int64) - self.y0
        k = np.floor(pts[:, 2]).astype(np.int64) - self.z0
        ok = (i >= 0) & (i < self.mat.shape[0]) & (j >= 0) & (j < self.mat.shape[1]) & \
            (k >= 0) & (k < self.mat.shape[2])
        i, j, k = i[ok], j[ok], k[ok]
        self.mat[i, j, k] = MAT[material]
        self.tone[i, j, k] = np.broadcast_to(np.asarray(tone, np.float32), ok.shape)[ok]
        self.nrm[i, j, k] = 0.0 if normal is None else np.asarray(normal, np.float32)

    def carve(self, mask):
        mask = np.broadcast_to(mask, self.mat.shape)
        self.mat[mask] = 0
        self.nrm[mask] = 0.0

    def rotated(self, turns: int, fw: int, fh: int) -> "Model":
        """The model turned `turns` x 90 degrees clockwise seen from above (N -> E -> S -> W)."""
        m = self
        for _ in range(turns % 4):
            hf = DESIGN_TILE * fh                 # design units, for the halos
            hv = hf * m.k                         # voxels, for the grid
            nx, ny, _nz = m.mat.shape
            rot = lambda a: np.ascontiguousarray(a.transpose(1, 0, *range(2, a.ndim))[::-1])
            nrm = rot(m.nrm)
            # A normal (nx, ny) turns like a direction: (x, y) -> (-y, x).
            nrm = np.stack([-nrm[..., 1], nrm[..., 0], nrm[..., 2]], axis=-1)
            m = Model(hv - m.y0 - ny, m.x0, m.z0, rot(m.mat), rot(m.tone), nrm,
                      [Halo(hf - h.y, h.x, h.z, h.radius, h.rgb, h.strength) for h in m.halos],
                      m.hover, None if m.ghost is None else rot(m.ghost), m.k)
            fw, fh = fh, fw
        return m


    def ghost_outside(self, x0, x1, y0, y1):
        """Mark everything outside [x0,x1)x[y0,y1) as context only."""
        X, Y, _Z = self.coords()
        inside = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
        self.ghost = np.broadcast_to(~inside, self.mat.shape) & (self.mat > 0)

    def visible(self) -> np.ndarray:
        return self.mat if self.ghost is None else np.where(self.ghost, 0, self.mat).astype(np.uint8)

    def density_normals(self, mask, radius=2):
        """Set normals of `mask` voxels from the gradient of the blurred solid field (radius in
        design units)."""
        radius *= self.k
        occ = box_blur(np.pad((self.mat > 0).astype(np.float32), radius + 1), radius)
        gx, gy, gz = np.gradient(occ)
        sl = (slice(radius + 1, -radius - 1),) * 3
        n = -np.stack([gx[sl], gy[sl], gz[sl]], axis=-1)
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
        mask = np.broadcast_to(mask, self.mat.shape)
        self.nrm[mask] = n[mask]


def box_blur(a, r):
    """Mean over a (2r+1)^3 box, same shape, via cumulative sums."""
    for axis in range(3):
        c = np.cumsum(np.pad(a, [(r + 1, r) if ax == axis else (0, 0) for ax in range(3)]),
                      axis=axis, dtype=np.float32)
        n = a.shape[axis]
        a = (np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
             - np.take(c, np.arange(0, n), axis=axis)) / (2 * r + 1)
    return a


# ---- shapes (all return boolean masks over voxel centres) ----

def box(X, Y, Z, x0, x1, y0, y1, z0, z1):
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1) & (Z >= z0) & (Z < z1)


def ellipsoid(X, Y, Z, cx, cy, cz, rx, ry, rz, wobble=None):
    d = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 + ((Z - cz) / rz) ** 2
    return d <= (1.0 if wobble is None else 1.0 + wobble)


def ellipsoid_normal(X, Y, Z, cx, cy, cz, rx, ry, rz):
    return ((X - cx) / rx ** 2, (Y - cy) / ry ** 2, (Z - cz) / rz ** 2)


def cylinder(X, Y, Z, cx, cy, r, z0, z1):
    return ((X - cx) ** 2 + (Y - cy) ** 2 <= r * r) & (Z >= z0) & (Z < z1)


def cylinder_normal(X, Y, Z, cx, cy):
    return (X - cx, Y - cy, Z * 0.0)


def cone(X, Y, Z, cx, cy, r, z0, z1):
    """Cone with base radius r at z0 narrowing to a point at z1."""
    frac = np.clip((z1 - Z) / (z1 - z0), 0, 1)
    return ((X - cx) ** 2 + (Y - cy) ** 2 <= (r * frac) ** 2) & (Z >= z0) & (Z < z1)


def segment(X, Y, Z, p, q, r):
    """Capsule of radius r around the segment p-q (sticks, posts at an angle, rails)."""
    p, q = np.asarray(p, np.float32), np.asarray(q, np.float32)
    d = q - p
    t = np.clip(((X - p[0]) * d[0] + (Y - p[1]) * d[1] + (Z - p[2]) * d[2]) / float(d @ d), 0, 1)
    return (X - p[0] - t * d[0]) ** 2 + (Y - p[1] - t * d[1]) ** 2 + (Z - p[2] - t * d[2]) ** 2 <= r * r


def gable(X, Y, Z, x0, x1, y0, y1, z0, rise, along_x=True):
    """Gable roof prism over [x0,x1)x[y0,y1) from z0; the ridge runs along x (or y)."""
    if along_x:
        half = (y1 - y0) / 2
        h = z0 + rise * (1 - np.abs(Y - (y0 + half)) / half)
    else:
        half = (x1 - x0) / 2
        h = z0 + rise * (1 - np.abs(X - (x0 + half)) / half)
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1) & (Z >= z0) & (Z < h)


def slope_normal(X, Y, Z, cx, cy, pitch, along_x=True):
    """Normals of a pitched roof plane, so voxel staircases shade as one smooth slope."""
    zero = Z * 0 + X * 0 + Y * 0
    if along_x:
        return (zero, np.sign(Y - cy) * pitch + zero, zero + 1.0)
    return (np.sign(X - cx) * pitch + zero, zero, zero + 1.0)


def masonry(m: "Model", along, Z, course, block, seed):
    """Fine-grid coursed stone: staggered blocks of slightly different tones with pixel-wide
    mortar joints and a lit top edge. `along` runs along the wall (X + Y serves every face of
    a box)."""
    row = np.floor(Z / course)
    a = along + (row % 2) * block * 0.5
    col = np.floor(a / block)
    j = 0.5 / m.k
    joint = ((Z % course) < j) | ((a % block) < j)
    top = (Z % course) >= course - j
    return -1.1 * joint + top * 0.5 + (hash01(row.astype(np.int64), col.astype(np.int64), seed) - 0.5) * 0.9


# ---- deterministic noise ----

def hash01(*ints) -> np.ndarray:
    """Integer lattice hash -> float in [0, 1); vectorised and platform independent."""
    h = np.array(2166136261, np.uint32)
    with np.errstate(over="ignore"):  # wrapping uint32 arithmetic is the point
        for v in ints:
            h = (h ^ np.asarray(v).astype(np.int64).astype(np.uint32)) * np.uint32(16777619)
            h ^= h >> np.uint32(13)
            h = h * np.uint32(0x5BD1E995)
            h ^= h >> np.uint32(15)
    return (h & np.uint32(0xFFFFFF)).astype(np.float32) / np.float32(0x1000000)


def value_noise(x, y, z, scale, seed, period=None):
    """Smooth 3D value noise in [0, 1). With `period` (in lattice cells) it tiles in x and y."""
    x, y, z = (np.asarray(v, np.float32) / scale for v in (x, y, z))
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - xi, y - yi, z - zi
    sx, sy, sz = (f * f * (3 - 2 * f) for f in (fx, fy, fz))
    xi, yi, zi = xi.astype(np.int64), yi.astype(np.int64), zi.astype(np.int64)

    def h(dx, dy, dz):
        a, b = xi + dx, yi + dy
        if period:
            a, b = a % period, b % period
        return hash01(a, b, zi + dz, seed)

    lerp = lambda a, b, t: a + (b - a) * t
    x00 = lerp(h(0, 0, 0), h(1, 0, 0), sx)
    x10 = lerp(h(0, 1, 0), h(1, 1, 0), sx)
    x01 = lerp(h(0, 0, 1), h(1, 0, 1), sx)
    x11 = lerp(h(0, 1, 1), h(1, 1, 1), sx)
    return lerp(lerp(x00, x10, sy), lerp(x01, x11, sy), sz)


def cells3(pts, cell, seed, jitter=0.9, period=None):
    """3D Voronoi cells over points (N, 3): distance to the nearest and second nearest centre,
    the offset (N, 3) from the nearest centre and its hash. Leaves, pebbles, shingles. With
    `period` (cells) the pattern repeats along x and y, for pieces that join across tiles."""
    q = np.asarray(pts, np.float32) / cell
    base = np.floor(q).astype(np.int64)
    f1 = np.full(len(q), 1e9, np.float32)
    f2 = np.full(len(q), 1e9, np.float32)
    off = np.zeros(q.shape, np.float32)
    h = np.zeros(len(q), np.float32)
    for d in np.ndindex(3, 3, 3):
        c = base + np.array(d) - 1
        w = c if period is None else np.stack([c[:, 0] % period, c[:, 1] % period, c[:, 2]], 1)
        centre = c + 0.5 + (np.stack([hash01(w[:, 0], w[:, 1], w[:, 2], seed, a) for a in range(3)], 1)
                            - 0.5) * jitter
        o = (q - centre) * cell
        dist = np.sqrt((o * o).sum(1))
        nearer = dist < f1
        f2 = np.where(nearer, f1, np.minimum(f2, dist))
        f1 = np.where(nearer, dist, f1)
        off[nearer] = o[nearer]
        h = np.where(nearer, hash01(w[:, 0], w[:, 1], w[:, 2], seed, 9), h)
    return f1, f2, off, h


class Rng:
    """Seeded generator for model parameters (numpy's PCG64 is stable across platforms)."""

    def __init__(self, *seed):
        self.g = np.random.Generator(np.random.PCG64(list(seed)))

    def uniform(self, a=0.0, b=1.0) -> float:
        return float(self.g.uniform(a, b))

    def integers(self, a, b) -> int:
        return int(self.g.integers(a, b))

    def choice(self, seq):
        return seq[self.integers(0, len(seq))]


def curve(p0, p1, bend=(0.0, 0.0), n=None):
    """Points along a quadratic curve from p0 to p1, bowed sideways by `bend` at its middle."""
    p0, p1 = np.asarray(p0, np.float32), np.asarray(p1, np.float32)
    n = n or int(np.ceil(np.linalg.norm(p1 - p0) * 3)) + 2
    t = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    mid = (p0 + p1) / 2 + np.array([bend[0], bend[1], 0], np.float32)
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * p1
