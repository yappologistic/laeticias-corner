"""Voxel models: a material grid plus optional per-voxel normals and tone, with shape helpers.

World units are voxels, 16 per tile edge; z is up and one voxel tall projects to one pixel.
Shapes are boolean masks over voxel centres so they compose with numpy operators.
"""

from dataclasses import dataclass, field

import numpy as np

from palette import MAT

TILE = 16


@dataclass
class Halo:
    """A soft additive light blob for the glow layer, at a world point."""
    x: float
    y: float
    z: float
    radius: float
    rgb: tuple[int, int, int]
    strength: float = 1.0


@dataclass
class Model:
    x0: int
    y0: int
    z0: int
    mat: np.ndarray                      # uint8 (nx, ny, nz), 0 = empty
    tone: np.ndarray                     # float32, ramp steps added to the lit level
    nrm: np.ndarray                      # float32 (nx, ny, nz, 3); zero = use the face normal
    halos: list[Halo] = field(default_factory=list)
    hover: bool = False                  # True when nothing rests on the ground (no contact AO)
    # Context voxels (a neighbour's joining arm): they occlude light but are never drawn.
    ghost: np.ndarray | None = None

    @classmethod
    def empty(cls, x0, x1, y0, y1, z0, z1) -> "Model":
        shape = (x1 - x0, y1 - y0, z1 - z0)
        return cls(x0, y0, z0, np.zeros(shape, np.uint8), np.zeros(shape, np.float32),
                   np.zeros(shape + (3,), np.float32))

    @classmethod
    def for_footprint(cls, fw: int, fh: int, height: int, margin: int = 8, below: int = 0):
        return cls.empty(-margin, TILE * fw + margin, -margin, TILE * fh + margin, -below, height)

    def coords(self):
        """Voxel-centre world coordinates as broadcastable (nx,1,1), (1,ny,1), (1,1,nz) arrays."""
        nx, ny, nz = self.mat.shape
        X = (np.arange(nx, dtype=np.float32) + self.x0 + 0.5)[:, None, None]
        Y = (np.arange(ny, dtype=np.float32) + self.y0 + 0.5)[None, :, None]
        Z = (np.arange(nz, dtype=np.float32) + self.z0 + 0.5)[None, None, :]
        return X, Y, Z

    def put(self, mask, material: str, tone=0.0, normal=None, only_empty=False):
        mask = np.broadcast_to(mask, self.mat.shape)
        if only_empty:
            mask = mask & (self.mat == 0)
        self.mat[mask] = MAT[material]
        self.tone[mask] = np.broadcast_to(np.asarray(tone, np.float32), self.mat.shape)[mask]
        if normal is None:
            self.nrm[mask] = 0.0
        else:
            n = np.stack(np.broadcast_arrays(*normal), axis=-1).astype(np.float32)
            n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
            self.nrm[mask] = np.broadcast_to(n, self.mat.shape + (3,))[mask]

    def put_points(self, pts, material: str, tone=0.0, normal=None):
        """Set the voxels containing each world point (N, 3); for thin stems and blades."""
        pts = np.asarray(pts, np.float32).reshape(-1, 3)
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

    def add_tone(self, mask, amount):
        mask = np.broadcast_to(mask, self.mat.shape)
        self.tone += np.where(mask, np.asarray(amount, np.float32), 0.0)

    def rotated(self, k: int, fw: int, fh: int) -> "Model":
        """The model turned k x 90 degrees clockwise seen from above (N -> E -> S -> W)."""
        m = self
        for _ in range(k % 4):
            hf = TILE * fh
            nx, ny, _nz = m.mat.shape
            rot = lambda a: np.ascontiguousarray(a.transpose(1, 0, *range(2, a.ndim))[::-1])
            nrm = rot(m.nrm)
            # A normal (nx, ny) turns like a direction: (x, y) -> (-y, x).
            nrm = np.stack([-nrm[..., 1], nrm[..., 0], nrm[..., 2]], axis=-1)
            m = Model(hf - m.y0 - ny, m.x0, m.z0, rot(m.mat), rot(m.tone), nrm,
                      [Halo(hf - h.y, h.x, h.z, h.radius, h.rgb, h.strength) for h in m.halos],
                      m.hover, None if m.ghost is None else rot(m.ghost))
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
        """Set normals of `mask` voxels from the gradient of the blurred solid field."""
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
