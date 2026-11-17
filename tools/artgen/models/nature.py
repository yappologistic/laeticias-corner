"""Trees, shrubs, flowers, rocks and water plants (1x1 tile, `variant` layouts)."""

import math

import numpy as np

from render import SUN
from voxel import (Model, Rng, curve, cylinder, cylinder_normal, ellipsoid, ellipsoid_normal,
                   hash01, segment, value_noise)

C = 8.0  # centre of a 1x1 tile


def canopy(m: Model, clumps, material: str, seed: int, leafy=0.35, light_tone=0.7):
    """Union of noisy ellipsoid clumps; each clump keeps its own normals so it reads as a puff."""
    X, Y, Z = m.coords()
    for n, (cx, cy, cz, r) in enumerate(clumps):
        wob = (value_noise(X, Y, Z, 2.2, seed + n) - 0.5) * leafy * 2
        rz = r * 0.82
        mask = ellipsoid(X, Y, Z, cx, cy, cz, r, r, rz, wob)
        nrm = ellipsoid_normal(X, Y, Z, cx, cy, cz, r, r, rz)
        # Highlight cluster on the sun side of each clump, broken up by noise.
        sun_side = ((cx - X) * 0.45 + (Y - cy) * 0.3 + (Z - cz) * 0.85) / r
        speck = value_noise(X, Y, Z, 1.6, seed + 50 + n)
        tone = np.where((sun_side > 0.35) & (speck > 0.45), light_tone, 0.0) + (speck - 0.5) * 0.4
        m.put(mask, material, tone=tone, normal=nrm)


def trunk(m: Model, x, y, r, z1, material="bark", lean=(0.0, 0.0), flare=1.6, taper=0.0):
    X, Y, Z = m.coords()
    cx = x + lean[0] * Z / z1
    cy = y + lean[1] * Z / z1
    rr = r * (1 - taper * np.clip(Z / z1, 0, 1)) + flare * np.clip(1 - Z / 3.0, 0, 1) ** 2
    mask = ((X - cx) ** 2 + (Y - cy) ** 2 <= rr ** 2) & (Z >= 0) & (Z < z1)
    # Vertical bark grooves: noise stretched along the trunk.
    ang = np.arctan2(Y - cy, X - cx)
    bark = value_noise(np.cos(ang) * 4 + 10, np.sin(ang) * 4 + 10, Z * 0.25, 1.0, 11) - 0.5
    m.put(mask, material, tone=bark * 1.2, normal=cylinder_normal(X, Y, Z, cx, cy))


def roots(m: Model, rng: Rng, x, y, count, reach, r=1.1, material="bark"):
    """Short roots fanning out from the trunk base and diving into the ground."""
    X, Y, Z = m.coords()
    a0 = rng.uniform(0, 6.28)
    for k in range(count):
        a = a0 + k * 6.28 / count + rng.uniform(-0.4, 0.4)
        d = reach * rng.uniform(0.7, 1.1)
        p, q = (x, y, 2.2), (x + d * math.cos(a), y + d * math.sin(a), -0.6)
        m.put(segment(X, Y, Z, p, q, r) & (Z >= 0), material, tone=-0.2,
              normal=(X - x, Y - y, Z * 0 + 1.2))


# ---- leaf masses ----

def _sphere_points(n, rng: Rng):
    """n roughly even unit vectors (a jittered Fibonacci sphere)."""
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * k / n) + rng.g.uniform(-0.12, 0.12, n)
    theta = math.pi * (1 + 5 ** 0.5) * k + rng.uniform(0, 6.28) + rng.g.uniform(-0.3, 0.3, n)
    return np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], 1)


def leaf_mass(m: Model, clumps, seed: int, materials=(("leaf", 1.0),), under="leaf",
              cluster=(2.8, 4.0), squash=0.9, level=-0.9):
    """A canopy built from clumps, each covered in small leaf clusters.

    `clumps` are (x, y, z, r). Every clump's surface is studded with clusters a few voxels
    across; each cluster shades as its own little puff (normal blended with the clump's), so
    the canopy reads as many lit tufts with dark crevices between them. Clusters on a clump's
    underside use `under`; the rest pick from weighted `materials`. `level` shifts the whole
    mass down the ramp so only sunlit tufts reach the lightest greens.
    """
    rng = Rng(seed)
    shape = m.mat.shape
    best = np.full(shape, -1.0, np.float32)
    second = np.full(shape, -1.0, np.float32)
    nrm = np.zeros(shape + (3,), np.float32)
    tone = np.zeros(shape, np.float32)
    own = np.zeros(shape, np.int8)
    names = [name for name, _w in materials] + [under]
    weights = np.cumsum([w for _n, w in materials]) / sum(w for _n, w in materials)

    def claim(sl, mask, score, n_vec, t, mat_idx):
        b, s2 = best[sl], second[sl]
        win = mask & (score > b)
        s2[win] = b[win]
        s2[mask & ~win & (score > s2)] = score[mask & ~win & (score > s2)]
        b[win] = score[win]
        nrm[sl][win] = n_vec[win]
        tone[sl][win] = np.broadcast_to(t, win.shape)[win]
        own[sl][win] = np.broadcast_to(np.asarray(mat_idx, np.int8), win.shape)[win]

    for cx, cy, cz, r in clumps:
        rz = r * squash
        sl, X, Y, Z = m.window(cx, cy, cz, r + 1)
        dx, dy, dz = (X - cx) / r, (Y - cy) / r, (Z - cz) / rz
        core = dx * dx + dy * dy + dz * dz <= 0.8 ** 2
        cn = np.stack(np.broadcast_arrays(dx / r, dy / r, dz / rz), -1)
        cn /= np.maximum(np.linalg.norm(cn, axis=-1, keepdims=True), 1e-6)
        under_side = cn[..., 2] < -0.35
        claim(sl, core, np.zeros(core.shape, np.float32), cn, level - 0.6 * under_side,
              np.where(under_side, len(names) - 1, 0).astype(np.int8))
        rc_mean = sum(cluster) / 2
        count = int(3.2 * (r / rc_mean) ** 2) + 4
        for p in _sphere_points(count, rng):
            if p[2] < -0.75:
                continue
            rc = rng.uniform(*cluster)
            px, py, pz = cx + p[0] * r * 0.8, cy + p[1] * r * 0.8, cz + p[2] * rz * 0.8
            sl, X, Y, Z = m.window(px, py, pz, rc + 1)
            d = np.sqrt((X - px) ** 2 + (Y - py) ** 2 + ((Z - pz) / 0.85) ** 2)
            blob = d <= rc
            if not blob.any():
                continue
            sn = np.stack(np.broadcast_arrays(X - px, Y - py, (Z - pz) / 0.85), -1) / np.maximum(d, 1e-3)[..., None]
            cn = np.array([p[0] / r, p[1] / r, p[2] / rz], np.float32)
            cn /= np.linalg.norm(cn)
            n_vec = 0.45 * cn + 0.55 * sn
            n_vec /= np.maximum(np.linalg.norm(n_vec, axis=-1, keepdims=True), 1e-6)
            # Lit tufts on the sun side get a highlight cluster; each cluster varies a little.
            sun = (sn * SUN).sum(-1)
            facing = float(cn @ SUN)
            t = (level + rng.uniform(-0.3, 0.3) + 0.9 * facing
                 + np.where((sun > 0.55) & (facing > 0.1), 0.9, 0.0) - 0.7 * (p[2] < -0.35))
            if p[2] < -0.35:
                idx = len(names) - 1
            else:
                idx = int(np.searchsorted(weights, rng.uniform(), side="right"))
                idx = min(idx, len(materials) - 1)
            claim(sl, blob, 1.0 - d / rc + 0.05, n_vec, t, idx)

    solid = best > -1
    # Crevices: where two clusters meet with nearly equal claim, the gap between them is dark.
    crevice = solid & (second > 0) & (best - second < 0.12)
    tone -= crevice * 0.8
    for i, name in enumerate(names):
        mask = solid & (own == i)
        if mask.any():
            m.put(mask, name, tone=tone, normal=(nrm[..., 0], nrm[..., 1], nrm[..., 2]))


def _branches(m: Model, base, clumps, r=1.2):
    X, Y, Z = m.coords()
    for cx, cy, cz, cr in clumps:
        m.put(segment(X, Y, Z, base, (cx, cy, cz - cr * 0.3), r), "bark", tone=-0.4)


# ---- broadleaf trees ----

# Per variant: crown radius, crown centre height, trunk lean (x, y), ring clumps, ring spread,
# crown squash and extra lobes (angle, distance, dz, radius) in units of the crown radius.
BROADLEAF = (
    dict(r=11.0, z=26, lean=(0.5, -0.5), ring=6, spread=0.95, lobes=()),
    dict(r=9.5, z=31, lean=(3.5, -2.5), ring=5, spread=0.8, lobes=((5.6, 0.9, 0.55, 0.6),)),
    dict(r=10.0, z=23, lean=(-1.0, 1.5), ring=7, spread=1.1, lobes=((5.5, 1.3, -0.2, 0.7),
                                                                   (2.36, 1.3, -0.1, 0.7))),
    dict(r=8.5, z=22, lean=(-2.0, -1.0), ring=4, spread=0.9, lobes=((2.4, 1.3, -0.3, 0.65),)),
)


def _broadleaf(v, frame, frames, seed, materials, under, level, scale=1.0):
    rng = Rng(seed, v)
    p = BROADLEAF[v]
    R, zc = p["r"] * scale, p["z"] * scale
    m = Model.empty(-18, 34, -18, 34, 0, int(zc + R * 1.6) + 4)
    lx, ly = p["lean"]
    top = (C + lx, C + ly)
    trunk_h = zc - R * 0.35
    trunk(m, C, C, 2.4 * scale, trunk_h, lean=(lx, ly), flare=2.0, taper=0.35)
    roots(m, rng, C, C, 5, 5.0)
    clumps = [(top[0], top[1], zc, R)]
    a0 = rng.uniform(0, 6.28)
    for n in range(p["ring"]):
        a = a0 + n * 6.28 / p["ring"] + rng.uniform(-0.35, 0.35)
        d = R * p["spread"] * rng.uniform(0.75, 1.0)
        clumps.append((top[0] + d * math.cos(a), top[1] + d * math.sin(a),
                       zc + R * rng.uniform(-0.45, 0.2), R * rng.uniform(0.55, 0.72)))
    for a, d, dz, r in p["lobes"]:
        clumps.append((top[0] + R * d * math.cos(a), top[1] + R * d * math.sin(a), zc + R * dz, R * r))
    for _n in range(2):
        a = rng.uniform(0, 6.28)
        clumps.append((top[0] + R * 0.35 * math.cos(a), top[1] + R * 0.35 * math.sin(a),
                       zc + R * rng.uniform(0.5, 0.7), R * rng.uniform(0.55, 0.65)))
    _branches(m, (top[0], top[1], trunk_h - 2), clumps[1:])
    # Sway: each clump drifts on its own phase, more the higher it sits.
    t = 2 * math.pi * frame / max(frames, 1)
    swayed = []
    for n, (x, y, z, r) in enumerate(clumps):
        amp = 0.6 * float(np.clip((z - trunk_h) / R + 0.4, 0.2, 1.2))
        ph = (x - y) * 0.06 + n * 0.5        # a gust crossing the crown, each clump lagging a little
        swayed.append((x + amp * math.sin(t + ph), y - 0.5 * amp * math.sin(t + ph), z, r))
    swayed.sort(key=lambda c: c[2])
    leaf_mass(m, swayed, seed * 31 + v, materials, under, level=level)
    return m


def oak(v, frame, frames):
    return _broadleaf(v, frame, frames, 101, (("leaf", 1.0),), "leaf_dark", level=-1.2)


def blossom(v, frame, frames):
    m = _broadleaf(v, frame, frames, 103, (("blossom", 0.95), ("leaf_dark", 0.05)), "leaf_dark",
                   level=-1.3, scale=0.92)
    # A few fallen petals on the ground under the crown, thicker near the trunk.
    X, Y, Z = m.coords()
    rho = np.hypot(X - C - 2, Y - C + 1)
    cell = hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64), 104 + v)
    petals = (cell < 0.07 * np.clip(1.3 - rho / 12, 0, 1)) & (rho > 3) & (Z < 1)
    m.put(petals, "blossom", tone=2.0 + (cell < 0.02), only_empty=True)
    return m


# ---- conifers ----

# Per variant: height, base radius, tiers, lean (x, y) at the top.
PINES = ((60, 11.5, 7, (0.0, 0.0)), (54, 10.0, 6, (1.5, -1.5)), (50, 12.5, 6, (-0.5, 0.5)),
         (63, 10.5, 8, (-1.0, -1.5)))


def pine(v, frame, frames):
    rng = Rng(102, v)
    h, r0, tiers, (lx, ly) = PINES[v]
    m = Model.empty(-10, 26, -10, 26, 0, h + 3)
    trunk(m, C, C, 1.7, h * 0.4, flare=1.6, taper=0.3)
    roots(m, rng, C, C, 4, 4.0, r=0.9)
    X, Y, Z = m.coords()
    t = 2 * math.pi * frame / max(frames, 1)
    # Tiers are steep skirts, each starting wider than the one above reaches at that height,
    # so every tier's drooping hem stands out from the one below it.
    spacing = (h - 17) / tiers
    for n in range(tiers):
        f = n / tiers
        z0 = 13 + n * spacing + rng.uniform(-0.6, 0.6)
        r = r0 * (1 - f * 0.8) + rng.uniform(-0.5, 0.5)
        height = h - z0 if n == tiers - 1 else spacing * 2.3
        # Each tier sways on its own phase; the axis leans with height.
        sx = lx * z0 / h + (0.25 + 0.6 * f) * math.sin(t + n * 1.3)
        sy = ly * z0 / h
        dx, dy = X - C - sx, Y - C - sy
        rho = np.sqrt(dx * dx + dy * dy) + 1e-3
        ang = np.arctan2(dy, dx)
        frac = np.clip((z0 + height - Z) / height, 0, 1)
        # Branch tips: a ragged rim of drooping points around the tier.
        phase = rng.uniform(0, 6.28)
        jag = 1 + 0.38 * np.maximum(np.sin(ang * 6 + phase), 0) ** 3 - 0.1 * np.sin(ang * 4 + phase * 2)
        reach = r * jag
        droop = (rho / reach) ** 2 * 4.0
        mask = (rho <= reach * frac ** 1.35) & (Z >= z0 - droop) & (Z < z0 + height)
        nrm = (dx / rho * height, dy / rho * height, np.full_like(Z, r * 0.9))
        speck = value_noise(X, Y, Z, 1.4, 300 + n + v * 10)
        sun = (-dx * 0.45 + dy * 0.3) / rho
        rim = rho / (reach + 1e-3)
        # The outer skirt catches the light, branch tips glint on the sun side, and a dark hem
        # runs along the underside of each drooping tier.
        tips = (sun > 0.1) & (speck > 0.45) & (Z > z0 + 1.5) & (rim > 0.55)
        hem = (Z < z0 - droop + 1.8) & (rim > 0.4)
        tone = (0.7 * np.clip((rim - 0.45) * 2.5, 0, 1) - 0.3 + tips * 0.8
                + (speck - 0.5) * 0.3 + (jag - 1) * 1.2 - hem * 1.8)
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
    canopy(m, clumps, material, seed, leafy=0.45)


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


def _bend(pts, t, sway, h, phase):
    """Sway one stem: its tip swings most, each stem on its own phase."""
    lean = sway * math.sin(t + phase) * np.clip(pts[:, 2] / h, 0, 1) ** 1.5
    pts[:, 0] += lean
    pts[:, 1] -= 0.4 * lean
    return pts


def _gust_phase(rng: Rng, x, y):
    """Phase of a gust crossing the patch, with a little lag per stem."""
    return (x - y) * 0.18 + rng.uniform(0, 1.5)


def _blades(m: Model, rng: Rng, count, radius, h0, h1, materials, t=0.0, sway=0.0, spread=3.0,
            tip=1.0):
    for n in range(count):
        a, d = rng.uniform(0, 6.28), radius * math.sqrt(rng.uniform(0, 1))
        x, y = C + d * math.cos(a), C + d * math.sin(a)
        h = rng.uniform(h0, h1)
        out = rng.uniform(0.3, 1.0) * spread
        top = (x + out * math.cos(a), y + out * math.sin(a), h)
        pts = curve((x, y, 0.2), top, bend=(rng.uniform(-1, 1), rng.uniform(-1, 1)))
        pts = _bend(pts, t, sway * rng.uniform(0.6, 1.2), h, _gust_phase(rng, x, y))
        frac = pts[:, 2] / h
        m.put_points(pts, rng.choice(materials), tone=-0.8 + frac * (1.6 + tip))


def tall_grass(v, frame, frames):
    rng = Rng(106, v)
    m = Model.empty(-4, 20, -4, 20, 0, 18)
    t = 2 * math.pi * frame / max(frames, 1)
    _blades(m, rng, 46, 6.0, 7, 14, ["grass", "grass", "leaf"], t, 1.3)
    if v in (1, 3):  # a few seed heads
        for n in range(5):
            a, d = rng.uniform(0, 6.28), rng.uniform(0, 5)
            x, y, h = C + d * math.cos(a), C + d * math.sin(a), rng.uniform(12, 15)
            pts = _bend(curve((x, y, 0.2), (x + 1, y, h)), t, 1.6, h, _gust_phase(rng, x, y))
            m.put_points(pts, "grass", tone=0.5)
            m.put_points(pts[-4:], "straw", tone=0.5)
    return m


def _flower_patch(v, seed, head):
    rng = Rng(seed, v)
    m = Model.empty(-2, 18, -2, 18, 0, 14)
    _blades(m, rng, 14, 5.5, 2, 4.5, ["grass", "leaf"], spread=2.0, tip=0.3)
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
    t = 2 * math.pi * frame / max(frames, 1)
    _blades(m, rng, 18, 4.5, 9, 17, ["leaf_dark", "grass"], t, 1.3, spread=2.5)
    for n in range(rng.integers(3, 6)):
        a, d = rng.uniform(0, 6.28), rng.uniform(0, 3.5)
        x, y, h = C + d * math.cos(a), C + d * math.sin(a), rng.uniform(13, 19)
        pts = curve((x, y, 0.2), (x + rng.uniform(-1, 1), y, h))
        pts = _bend(pts, t, 1.1, h, _gust_phase(rng, x, y))
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
