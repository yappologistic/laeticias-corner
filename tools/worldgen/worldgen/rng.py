"""Deterministic random streams and noise keyed by strings (Python's hash() is never used).

Streams are SplitMix64 seeded by a 64-bit FNV-1a hash of their key parts, so a stream depends only
on its key: editing one region never shifts the random choices of another. Noise and per-tile
draws are pure functions of world coordinates and a key, for the same reason.
"""

from __future__ import annotations

import numpy as np

MASK = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15


def _mix(z: int) -> int:
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    return z ^ (z >> 31)


def hash64(*parts: object) -> int:
    """Stable 64-bit hash of the parts' text (FNV-1a, then a SplitMix64 finaliser)."""
    h = 0xCBF29CE484222325
    for byte in "\x1f".join(str(p) for p in parts).encode():
        h = ((h ^ byte) * 0x100000001B3) & MASK
    return _mix(h)


class Stream:
    """SplitMix64 stream."""

    def __init__(self, seed: int):
        self.state = seed & MASK

    def next64(self) -> int:
        self.state = (self.state + GOLDEN) & MASK
        return _mix(self.state)

    def uniform(self) -> float:
        return (self.next64() >> 11) * (1.0 / (1 << 53))

    def randint(self, lo: int, hi: int) -> int:
        """Uniform integer in [lo, hi]."""
        return lo + self.next64() % (hi - lo + 1)

    def chance(self, p: float) -> bool:
        return self.uniform() < p

    def weighted(self, weights: dict[str, float]) -> str:
        """One key of `weights`, chosen in proportion to its weight (keys in insertion order)."""
        total = sum(weights.values())
        x = self.uniform() * total
        for key, w in weights.items():
            x -= w
            if x < 0:
                return key
        return next(reversed(weights))


def stream(*parts: object) -> Stream:
    return Stream(hash64(*parts))


# --- vectorised hashing and noise over coordinate arrays -------------------------------------

_U = np.uint64


def hash_grid(c: np.ndarray, r: np.ndarray, seed: int) -> np.ndarray:
    """uint64 hash per (c, r) integer pair; numpy wraps on overflow, which is what we want."""
    with np.errstate(over="ignore"):
        h = c.astype(np.int64).astype(_U) * _U(0x9E3779B97F4A7C15)
        h ^= r.astype(np.int64).astype(_U) * _U(0xC2B2AE3D27D4EB4F)
        h ^= _U(seed & MASK)
        h ^= h >> _U(30)
        h *= _U(0xBF58476D1CE4E5B9)
        h ^= h >> _U(27)
        h *= _U(0x94D049BB133111EB)
        h ^= h >> _U(31)
    return h


def hash01(c: np.ndarray, r: np.ndarray, seed: int) -> np.ndarray:
    """Uniform [0, 1) per integer (c, r)."""
    return (hash_grid(c, r, seed) >> _U(11)).astype(np.float64) * (1.0 / (1 << 53))


def value_noise(c: np.ndarray, r: np.ndarray, scale: float, seed: int) -> np.ndarray:
    """Smooth value noise in [0, 1] at float coordinates, lattice spacing `scale` tiles."""
    x = np.asarray(c, dtype=np.float64) / scale
    y = np.asarray(r, dtype=np.float64) / scale
    x0 = np.floor(x)
    y0 = np.floor(y)
    fx = x - x0
    fy = y - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    xi = x0.astype(np.int64)
    yi = y0.astype(np.int64)
    v00 = hash01(xi, yi, seed)
    v10 = hash01(xi + 1, yi, seed)
    v01 = hash01(xi, yi + 1, seed)
    v11 = hash01(xi + 1, yi + 1, seed)
    top = v00 + (v10 - v00) * fx
    bottom = v01 + (v11 - v01) * fx
    return top + (bottom - top) * fy


def fbm(c: np.ndarray, r: np.ndarray, scale: float, seed: int, octaves: int = 4,
        gain: float = 0.5) -> np.ndarray:
    """Fractal sum of value noise, normalised to [0, 1]."""
    total = np.zeros(np.broadcast(c, r).shape)
    amp = 1.0
    norm = 0.0
    for o in range(octaves):
        total += amp * value_noise(c, r, scale / (2 ** o), _mix(seed + o))
        norm += amp
        amp *= gain
    return total / norm


def grid_coords(c0: int, r0: int, w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Plan coordinate arrays (C, R) of shape (h, w) for a window."""
    r, c = np.mgrid[r0:r0 + h, c0:c0 + w]
    return c, r
