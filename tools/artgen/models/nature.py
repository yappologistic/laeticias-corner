"""Trees, shrubs, flowers, rocks and water plants (1x1 tile, `variant` layouts)."""

import math

import numpy as np

from voxel import (Model, Rng, curve, cylinder, cylinder_normal, ellipsoid, ellipsoid_normal,
                   hash01, segment, value_noise)

C = 8.0  # centre of a 1x1 tile


def _sway(frame: int, frames: int, amount: float) -> float:
    return amount * math.sin(2 * math.pi * frame / max(frames, 1))


def canopy(m: Model, clumps, material: str, seed: int, shear, leafy=0.35, light_tone=0.7):
    """Union of noisy ellipsoid clumps; each clump keeps its own normals so it reads as a puff."""
    X, Y, Z = m.coords()
    for n, (cx, cy, cz, r) in enumerate(clumps):
        Xs = X - shear(Z)
        wob = (value_noise(Xs, Y, Z, 2.2, seed + n) - 0.5) * leafy * 2
        rz = r * 0.82
        mask = ellipsoid(Xs, Y, Z, cx, cy, cz, r, r, rz, wob)
        nrm = ellipsoid_normal(Xs, Y, Z, cx, cy, cz, r, r, rz)
        # Highlight cluster on the sun side of each clump, broken up by noise.
        sun_side = ((cx - Xs) * 0.45 + (Y - cy) * 0.3 + (Z - cz) * 0.85) / r
        speck = value_noise(Xs, Y, Z, 1.6, seed + 50 + n)
        tone = np.where((sun_side > 0.35) & (speck > 0.45), light_tone, 0.0) + (speck - 0.5) * 0.4
        m.put(mask, material, tone=tone, normal=nrm)


def trunk(m: Model, x, y, r, z1, material="bark", lean=(0.0, 0.0), flare=1.6):
    X, Y, Z = m.coords()
    cx = x + lean[0] * Z / z1
    cy = y + lean[1] * Z / z1
    rr = r + flare * np.clip(1 - Z / 3.0, 0, 1)
    mask = ((X - cx) ** 2 + (Y - cy) ** 2 <= rr ** 2) & (Z >= 0) & (Z < z1)
    bark = value_noise(X * 3, Y * 3, Z * 0.4, 1.0, 11) - 0.5
    m.put(mask, material, tone=bark * 0.8, normal=cylinder_normal(X, Y, Z, cx, cy))


def _round_tree(v, frame, frames, seed, material, size, inner=None):
    rng = Rng(seed, v)
    h = int(round(size * 40))
    m = Model.empty(-10, 26, -10, 26, 0, h + 4)
    trunk_h = rng.uniform(0.42, 0.5) * h
    lean = (rng.uniform(-1, 1), rng.uniform(-1, 1))
    trunk(m, C, C, 1.8 * size + 0.2, trunk_h + 4, lean=lean)
    X, Y, Z = m.coords()
    for a in (rng.uniform(0, 6.28), rng.uniform(0, 6.28)):
        p = (C + lean[0] * 0.7, C + lean[1] * 0.7, trunk_h - 4)
        q = (C + 6 * size * math.cos(a), C + 6 * size * math.sin(a), trunk_h + 3)
        m.put(segment(X, Y, Z, p, q, 1.0), "bark")
    sway = _sway(frame, frames, 0.9)
    shear = lambda Z: sway * np.clip((Z - trunk_h + 6) / 18, 0, 1)
    top = h - 9 * size
    clumps = [(C + lean[0], C + lean[1], top - 6 * size, 9.5 * size)]
    for n in range(rng.integers(6, 9)):
        a = n * 2.4 + rng.uniform(-0.4, 0.4)
        d = rng.uniform(4.5, 7) * size
        clumps.append((C + d * math.cos(a), C + d * math.sin(a),
                       top - 9 * size + rng.uniform(-2, 7) * size, rng.uniform(4.8, 6.6) * size))
    clumps.append((C - 1, C + 1, top + size, rng.uniform(5.5, 6.5) * size))
    clumps.sort(key=lambda c: c[2])
    if inner:
        canopy(m, [(x, y, z, r * 0.9) for x, y, z, r in clumps[:3]], inner, seed * 7 + v, shear)
        canopy(m, clumps[3:], material, seed * 13 + v, shear)
    else:
        canopy(m, clumps, material, seed * 13 + v, shear)
    return m


def oak(v, frame, frames):
    return _round_tree(v, frame, frames, 101, "leaf", (1.0, 0.92, 1.05, 0.96)[v])


def blossom(v, frame, frames):
    m = _round_tree(v, frame, frames, 103, "blossom", (0.86, 0.8, 0.9, 0.84)[v], inner="leaf")
    # Fallen petals around the trunk.
    X, Y, Z = m.coords()
    petals = (hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64), 104 + v) < 0.07) \
        & (np.hypot(X - C, Y - C) < 9) & (np.hypot(X - C, Y - C) > 2.5) & (Z < 1)
    m.put(petals, "blossom", tone=1.5, only_empty=True)
    return m


def pine(v, frame, frames):
    rng = Rng(102, v)
    h = rng.uniform(42, 50)
    m = Model.empty(-6, 22, -6, 22, 0, int(h) + 2)
    trunk(m, C, C, 1.5, 12, flare=1.2)
    X, Y, Z = m.coords()
    sway = _sway(frame, frames, 0.8)
    Xs = X - sway * np.clip((Z - 8) / 36, 0, 1)
    dx, dy = Xs - C, Y - C
    rho = np.sqrt(dx * dx + dy * dy) + 1e-3
    ang = np.arctan2(dy, dx)
    tiers = rng.integers(4, 6)
    for n in range(tiers):
        t = n / tiers
        z0 = 6 + t * (h - 12)
        r = 8.2 * (1 - t * 0.72) + rng.uniform(-0.5, 0.5)
        height = r * 1.25 + 5
        frac = np.clip((z0 + height - Z) / height, 0, 1)
        jag = 1 + 0.16 * np.sin(ang * 7 + n * 1.7 + v) + 0.08 * np.sin(ang * 13 + n)
        droop = np.clip(rho / r, 0, 1) ** 2 * 2.0
        mask = (rho <= r * frac * jag) & (Z >= z0 - droop) & (Z < z0 + height)
        nrm = (dx / rho * height, dy / rho * height, np.full_like(Z, r))
        speck = value_noise(Xs, Y, Z, 1.5, 300 + n + v * 10)
        sun = (-dx * 0.45 + dy * 0.3) / rho
        rim = rho / (r * jag + 1e-3)
        tone = np.where((sun > 0.1) & (speck > 0.45) & (Z > z0 + 1.5), 1.1, 0.0) \
            + (speck - 0.5) * 0.5 - ((Z < z0 + 1.6) & (rim > 0.55)) * 1.4
        m.put(mask, "leaf_dark", tone=tone, normal=nrm)
    return m


def _bush_shape(m: Model, rng: Rng, material: str, seed: int, size=1.0):
    clumps = []
    for n in range(rng.integers(4, 6)):
        a = n * 2.1 + rng.uniform(0, 1)
        d = rng.uniform(1.5, 4.0) * size
        r = rng.uniform(3.6, 5.0) * size
        clumps.append((C + d * math.cos(a), C + d * math.sin(a), r * 0.7 + rng.uniform(0, 2), r))
    clumps.append((C, C, 6.5 * size, 4.6 * size))
    clumps.sort(key=lambda c: c[2])
    canopy(m, clumps, material, seed, lambda Z: 0.0, leafy=0.45)


def bush(v, frame, frames):
    rng = Rng(104, v)
    m = Model.empty(-3, 19, -3, 19, 0, 15)
    _bush_shape(m, rng, "leaf", 400 + v, (0.95, 1.05, 0.85, 1.0)[v])
    return m


def berry_bush(v, frame, frames):
    rng = Rng(105, v)
    m = Model.empty(-3, 19, -3, 19, 0, 15)
    _bush_shape(m, rng, "leaf_dark", 500 + v, (1.0, 0.92, 1.05, 0.95)[v])
    solid = m.mat > 0
    exposed = solid & ~np.pad(solid, 1)[1:-1, 1:-1, 2:] | solid & ~np.pad(solid, 1)[2:, 1:-1, 1:-1] \
        | solid & ~np.pad(solid, 1)[1:-1, 2:, 1:-1]
    X, Y, Z = m.coords()
    pick = hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64),
                  np.floor(Z).astype(np.int64), 510 + v) < 0.09
    berries = exposed & pick & (Z > 2)
    m.put(berries, "violet" if v == 2 else "poppy", tone=0.8)
    return m


def _blades(m: Model, rng: Rng, count, radius, h0, h1, materials, shear, spread=3.0, tip=1.0):
    for n in range(count):
        a, d = rng.uniform(0, 6.28), radius * math.sqrt(rng.uniform(0, 1))
        x, y = C + d * math.cos(a), C + d * math.sin(a)
        h = rng.uniform(h0, h1)
        out = rng.uniform(0.3, 1.0) * spread
        top = (x + out * math.cos(a), y + out * math.sin(a), h)
        pts = curve((x, y, 0.2), top, bend=(rng.uniform(-1, 1), rng.uniform(-1, 1)))
        pts[:, 0] += [shear(z) for z in pts[:, 2]]
        frac = pts[:, 2] / h
        m.put_points(pts, rng.choice(materials), tone=-0.8 + frac * (1.6 + tip))


def tall_grass(v, frame, frames):
    rng = Rng(106, v)
    m = Model.empty(-4, 20, -4, 20, 0, 18)
    sway = _sway(frame, frames, 1.0)
    shear = lambda z: sway * (z / 14) ** 1.5
    _blades(m, rng, 46, 6.0, 7, 14, ["grass", "grass", "leaf"], shear)
    if v in (1, 3):  # a few seed heads
        for n in range(5):
            a, d = rng.uniform(0, 6.28), rng.uniform(0, 5)
            x, y, h = C + d * math.cos(a), C + d * math.sin(a), rng.uniform(12, 15)
            pts = curve((x, y, 0.2), (x + 1, y, h))
            pts[:, 0] += [shear(z) for z in pts[:, 2]]
            m.put_points(pts, "grass", tone=0.5)
            m.put_points(pts[-4:], "straw", tone=0.5)
    return m


def _flower_patch(v, seed, head):
    rng = Rng(seed, v)
    m = Model.empty(-2, 18, -2, 18, 0, 14)
    _blades(m, rng, 14, 5.5, 2, 4.5, ["grass", "leaf"], lambda z: 0.0, spread=2.0, tip=0.3)
    X, Y, Z = m.coords()
    for n in range(rng.integers(7, 11)):
        a, d = rng.uniform(0, 6.28), 5.5 * math.sqrt(rng.uniform(0.05, 1))
        x, y = C + d * math.cos(a), C + d * math.sin(a)
        h = rng.uniform(3.5, 7.5)
        m.put_points(curve((x, y, 0.2), (x, y, h), bend=(rng.uniform(-0.6, 0.6), 0)), "grass")
        head(m, X, Y, Z, x, y, h, rng)
    return m


def _poppy(m, X, Y, Z, x, y, h, rng):
    cup = ellipsoid(X, Y, Z, x, y, h + 0.6, 1.3, 1.3, 0.9)
    m.put(cup, "poppy", normal=ellipsoid_normal(X, Y, Z, x, y, h, 1.3, 1.3, 1.3), tone=0.4)
    m.put_points([(x, y, h + 1.2)], "ink")


def _daisy(m, X, Y, Z, x, y, h, rng):
    petals = ellipsoid(X, Y, Z, x, y, h + 0.5, 1.6, 1.6, 0.6)
    m.put(petals, "cream", tone=0.6)
    m.put_points([(x, y, h + 1.0)], "yellow", tone=0.8)


def _lavender(m, X, Y, Z, x, y, h, rng):
    for k in range(5):
        m.put_points([(x + rng.uniform(-0.5, 0.5), y + rng.uniform(-0.5, 0.5), h + k * 0.8)],
                     "violet", tone=0.2 + k * 0.25)


def flowers_red(v, frame, frames):
    return _flower_patch(v, 107, _poppy)


def flowers_white(v, frame, frames):
    return _flower_patch(v, 108, _daisy)


def flowers_violet(v, frame, frames):
    return _flower_patch(v, 109, _lavender)


def mushrooms(v, frame, frames):
    rng = Rng(110, v)
    m = Model.empty(-1, 17, -1, 17, 0, 12)
    X, Y, Z = m.coords()
    cap_mat = ("poppy", "wood_light", "poppy", "straw")[v]
    count = (3, 4, 2, 5)[v]
    for n in range(count):
        a, d = n * 2.4 + rng.uniform(0, 1), rng.uniform(0.5, 4.5)
        x, y = C + d * math.cos(a), C + d * math.sin(a)
        s = rng.uniform(0.7, 1.25) * (1.25 if n == 0 else 1.0)
        sh = 3.2 * s
        m.put(cylinder(X, Y, Z, x, y, 0.95 * s, 0, sh + 0.5), "cream",
              normal=cylinder_normal(X, Y, Z, x, y))
        rc = 2.6 * s
        cap = ellipsoid(X, Y, Z, x, y, sh, rc, rc, 2.2 * s) & (Z >= sh - 0.3)
        spots = (hash01(np.floor(X * 1.5).astype(np.int64), np.floor(Y * 1.5).astype(np.int64),
                        np.floor(Z).astype(np.int64), 111 + n) < 0.16) & (cap_mat == "poppy")
        m.put(cap, cap_mat, normal=ellipsoid_normal(X, Y, Z, x, y, sh - 0.6, rc, rc, 2.2 * s))
        m.put(cap & spots, "cream", tone=0.8, normal=ellipsoid_normal(X, Y, Z, x, y, sh - 0.6, rc, rc, 2.2 * s))
    return m


def rock(v, frame, frames):
    rng = Rng(112, v)
    m = Model.empty(-3, 19, -3, 19, 0, 11)
    X, Y, Z = m.coords()
    stones = [(C, C, 5.5, 4.8, 5.0)] if v != 3 else [(C - 1.5, C - 1, 4.2, 3.6, 4.0),
                                                       (C + 3.5, C + 3, 2.8, 2.6, 2.6)]
    for n, (x, y, rx, ry, rz) in enumerate(stones):
        rx *= rng.uniform(0.9, 1.15)
        ry *= rng.uniform(0.85, 1.1)
        rz *= rng.uniform(0.85, 1.25)
        wob = (value_noise(X, Y, Z, 3.0, 600 + v * 5 + n) - 0.5) * 0.5
        shape = ellipsoid(X, Y, Z, x, y, rz * 0.35, rx, ry, rz, wob) & (Z >= 0)
        nx, ny, nz = ellipsoid_normal(X, Y, Z, x, y, rz * 0.35, rx, ry, rz)
        # Chunky facets: snap a noisy normal to a few directions.
        fx = value_noise(X, Y, Z, 3.5, 610 + v) - 0.5
        fy = value_noise(X, Y, Z, 3.5, 620 + v) - 0.5
        norm = (nx * rx * rx + fx * 1.2, ny * ry * ry + fy * 1.2, nz * rz * rz * 1.2)
        crack = np.abs(value_noise(X, Y, Z, 2.5, 630 + v) - 0.5) < 0.03
        m.put(shape, "stone", normal=norm, tone=crack * -1.2)
        if v in (0, 2):
            moss = shape & (Z > rz * 0.75) & (value_noise(X, Y, Z, 2.0, 640 + v) > 0.45)
            m.put(moss, "grass", normal=norm, tone=-0.3)
    return m


def stump(v, frame, frames):
    rng = Rng(113, v)
    m = Model.empty(-3, 19, -3, 19, 0, 9)
    X, Y, Z = m.coords()
    r, h = 4.3, 5.5 + v
    trunk(m, C, C, r, h, flare=1.4)
    rho = np.hypot(X - C, Y - C)
    top = (rho <= r + 0.2) & (Z >= h - 1) & (Z < h)
    m.put(top, "wood_light", tone=-0.9 * (np.sin(rho * 2.1) > 0.5) - 1.2 * (rho > r - 0.8))
    for k in range(4):
        a = k * 1.6 + rng.uniform(0, 0.8)
        m.put(segment(X, Y, Z, (C, C, 1.5), (C + 7 * math.cos(a), C + 7 * math.sin(a), 0.3), 1.0),
              "bark")
    if v == 1:
        moss = (m.mat > 0) & (Z > 1) & (Z < h - 1) & (value_noise(X, Y, Z, 2, 650) > 0.55)
        m.put(moss, "grass", tone=-0.2)
        m.put(cylinder(X, Y, Z, C + 4.8, C + 1.5, 0.6, 0, 2.5), "cream")
        m.put(ellipsoid(X, Y, Z, C + 4.8, C + 1.5, 2.6, 1.6, 1.6, 1.0) & (Z > 2.2), "wood_light",
              normal=(X - C - 4.8, Y - C - 1.5, Z - 1.6))
    return m


def reeds(v, frame, frames):
    rng = Rng(114, v)
    m = Model.empty(-4, 20, -4, 20, 0, 22)
    sway = _sway(frame, frames, 1.0)
    shear = lambda z: sway * (z / 18) ** 1.5
    _blades(m, rng, 18, 4.5, 9, 17, ["leaf_dark", "grass"], shear, spread=2.5)
    for n in range(rng.integers(3, 6)):
        a, d = rng.uniform(0, 6.28), rng.uniform(0, 3.5)
        x, y, h = C + d * math.cos(a), C + d * math.sin(a), rng.uniform(13, 19)
        pts = curve((x, y, 0.2), (x + rng.uniform(-1, 1), y, h))
        pts[:, 0] += [shear(z) for z in pts[:, 2]]
        m.put_points(pts, "leaf_dark", tone=0.3)
        head = pts[(pts[:, 2] > h - 5) & (pts[:, 2] < h - 1.5)]
        m.put_points(head, "bark", tone=1.2)
        m.put_points(head + [0.6, 0, 0], "bark", tone=0.4)
    return m


def lily_pads(v, frame, frames):
    rng = Rng(115, v)
    m = Model.empty(-2, 18, -2, 18, 0, 4)
    X, Y, Z = m.coords()
    for n in range(rng.integers(2, 5)):
        a, d = n * 2.3 + rng.uniform(0, 1), rng.uniform(0, 4.5)
        x, y, r = C + d * math.cos(a), C + d * math.sin(a), rng.uniform(2.3, 3.8)
        ang = np.arctan2(Y - y, X - x)
        notch = np.abs(((ang - rng.uniform(0, 6.28)) + np.pi) % (2 * np.pi) - np.pi) < 0.35
        pad = (np.hypot(X - x, Y - y) <= r) & (Z < 1) & ~notch
        rim = np.hypot(X - x, Y - y) > r - 0.8
        m.put(pad, "leaf", tone=0.6 - rim * 1.0 + (hash01(n, 116) - 0.5))
    if v in (1, 3):
        x, y = C + rng.uniform(-2, 2), C + rng.uniform(-2, 2)
        m.put(ellipsoid(X, Y, Z, x, y, 1.0, 1.8, 1.8, 1.4) & (Z >= 1), "blossom", tone=0.8,
              normal=(X - x, Y - y, Z))
        m.put_points([(x, y, 2.2)], "yellow", tone=1)
    return m
