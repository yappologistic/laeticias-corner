"""Trees, shrubs, flowers, rocks and water plants (1x1 tile, `variant` layouts)."""

import math

import numpy as np

from palette import MAT
from render import SUN
from voxel import (Model, Rng, box, cells3, curve, cylinder, cylinder_normal, ellipsoid, ellipsoid_normal,
                   hash01, segment, value_noise)

C = 8.0  # centre of a 1x1 tile


def canopy(m: Model, clumps, material: str, seed: int, leafy=0.35, light_tone=0.7):
    """Union of noisy ellipsoid clumps; each clump keeps its own normals so it reads as a puff."""
    X, Y, Z = m.coords()
    grown = np.zeros(m.mat.shape, bool)
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
        grown |= mask
    if m.fine:
        m.carve(grown & ~_leaves(m, grown & (m.mat == MAT[material]), m.nrm, m.tone, seed))


def trunk(m: Model, x, y, r, z1, material="bark", lean=(0.0, 0.0), flare=1.6, taper=0.0):
    sl, X, Y, Z = m.window(x + lean[0] / 2, y + lean[1] / 2, z1 / 2,
                           max(z1 / 2, r + flare + max(map(abs, lean))) + 1)
    cx = x + lean[0] * Z / z1
    cy = y + lean[1] * Z / z1
    rr = r * (1 - taper * np.clip(Z / z1, 0, 1)) + flare * np.clip(1 - Z / 3.0, 0, 1) ** 2
    mask = ((X - cx) ** 2 + (Y - cy) ** 2 <= rr ** 2) & (Z >= 0) & (Z < z1)
    # Vertical bark grooves: noise stretched along the trunk.
    ang = np.arctan2(Y - cy, X - cx)
    bark = value_noise(np.cos(ang) * 4 + 10, np.sin(ang) * 4 + 10, Z * 0.25, 1.0, 11) - 0.5
    tone = bark * 1.2
    if m.fine:  # narrow ridged plates between the grooves, catching light on their edges
        plates = value_noise(np.cos(ang) * 10 + 20, np.sin(ang) * 10 + 20, Z * 0.7, 1.0, 13)
        tone = tone + (plates > 0.62) * 0.8 - (plates < 0.3) * 0.7
    m.put(mask, material, tone=tone, normal=cylinder_normal(X, Y, Z, cx, cy), sl=sl)


def roots(m: Model, rng: Rng, x, y, count, reach, r=1.1, material="bark"):
    """Short roots fanning out from the trunk base and diving into the ground."""
    a0 = rng.uniform(0, 6.28)
    for k in range(count):
        a = a0 + k * 6.28 / count + rng.uniform(-0.4, 0.4)
        d = reach * rng.uniform(0.7, 1.1)
        p, q = (x, y, 2.2), (x + d * math.cos(a), y + d * math.sin(a), -0.6)
        sl, X, Y, Z = m.window(x, y, 1, reach * 1.1 + r + 2)
        m.put(segment(X, Y, Z, p, q, r) & (Z >= 0), material, tone=-0.2,
              normal=(X - x, Y - y, Z * 0 + 1.2), sl=sl)


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
    # Clusters stay small in pixels on finer grids, so a canopy carries more of them.
    cluster = tuple(c / m.k ** 0.5 for c in cluster)
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
            sn = np.stack(np.broadcast_arrays(X - px, Y - py, (Z - pz) / 0.85), -1)
            sn /= np.maximum(d, 1e-3)[..., None]
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
    # On finer grids the gaps are kept a pixel or two wide and a little deeper.
    crevice = solid & (second > 0) & (best - second < 0.12 * m.k)
    tone -= crevice * (0.8 + 0.4 * (m.k - 1))
    if m.fine:
        solid = _leaves(m, solid, nrm, tone, seed)
        # Limbs stay where they cross the foliage, glimpsed between the leaves.
        solid &= m.mat != MAT["bark"]
    for i, name in enumerate(names):
        mask = solid & (own == i)
        if mask.any():
            m.put(mask, name, tone=tone, normal=(nrm[..., 0], nrm[..., 1], nrm[..., 2]))


LEAF = 1.1  # leaf size in design units on fine grids


def _leaves(m: Model, solid, nrm, tone, seed, leaf=LEAF, period=None):
    """Individual leaves over a canopy: each lit on its sun side, with a dark notch where it
    overlaps the next, so tufts break into small shapes instead of smooth puffs. Notches on
    the outer skin are cut away, which frays the silhouette into leaf tips. Returns the solid
    mask that is left."""
    pad = np.pad(solid, 1)
    inner = pad[2:, 1:-1, 1:-1] & pad[:-2, 1:-1, 1:-1] & pad[1:-1, 2:, 1:-1] & \
        pad[1:-1, :-2, 1:-1] & pad[1:-1, 1:-1, 2:] & pad[1:-1, 1:-1, :-2]
    idx = np.nonzero(solid)
    X, Y, Z = m.coords()
    pts = np.stack([X[idx[0], 0, 0], Y[0, idx[1], 0], Z[0, 0, idx[2]]], 1)
    f1, f2, off, h = cells3(pts * (1.0, 1.0, 1.3), leaf, seed + 7, period=period)
    side = (off @ SUN) / (leaf * 0.5)
    lit = np.clip(nrm[idx] @ SUN, 0, 1)
    gap = (f2 - f1) < 0.18
    # Shadowed leaves keep a gentler version of the same marks, lifted off the darkest ink.
    t = side * (0.6 + 0.3 * lit) + (h - 0.5) * 0.5 + 1.1 * (1 - lit)
    tone[idx] += t - gap * (0.6 + 0.6 * (side < 0))
    keep = solid.copy()
    keep[idx] = ~(gap & ~inner[idx] & (h > 0.35))
    return keep


def _branches(m: Model, base, clumps, r=1.2):
    for cx, cy, cz, cr in clumps:
        q = np.array((cx, cy, cz - cr * 0.3))
        mid = (np.asarray(base) + q) / 2
        sl, X, Y, Z = m.window(*mid, np.linalg.norm(q - base) / 2 + r + 1)
        m.put(segment(X, Y, Z, base, q, r), "bark", tone=-0.4, sl=sl)


def _limbs(m: Model, rng: Rng, foot, top, trunk_h, clumps):
    """Tapering limbs leaving the trunk below the crown and forking up into its lowest clumps,
    so the branch structure shows under the canopy (fine grids only)."""
    for cx, cy, cz, cr in sorted(clumps, key=lambda c: c[2])[:3]:
        f = rng.uniform(0.4, 0.55)
        p = np.array([foot[0] + (top[0] - foot[0]) * f, foot[1] + (top[1] - foot[1]) * f,
                      trunk_h * f])
        q = np.array([cx, cy, cz - cr * 0.4])
        mid = (p + q) / 2 + (0, 0, rng.uniform(0.5, 2.0))
        sl, X, Y, Z = m.window(*((p + q) / 2), np.linalg.norm(q - p) / 2 + 2)
        m.put(segment(X, Y, Z, p, mid, 1.0) | segment(X, Y, Z, mid, q, 0.65), "bark",
              tone=-0.2, sl=sl)
        a = rng.uniform(0, 6.28)
        twig = mid + (q - mid) * 0.5
        tip = twig + (np.cos(a) * 2.5, np.sin(a) * 2.5, 2.5)
        sl, X, Y, Z = m.window(*twig, 4)
        m.put(segment(X, Y, Z, twig, tip, 0.45), "bark", tone=0.1, sl=sl)


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


def snow_caps(m: Model, seed: int, density=0.85, min_z=0.0, which=None, broad=0):
    """A pixel or two of snow on every upward-facing surface (of `which` materials), broken
    up a little column by column. With `broad` > 0 snow only settles where at least that many
    of the 8 neighbours in the layer are solid, so twigs stay dark and limbs carry it."""
    solid = m.mat > 0 if which is None else np.isin(m.mat, [MAT[w] for w in which])
    if broad:
        pad = np.pad(solid, ((1, 1), (1, 1), (0, 0)))
        near = sum(pad[1 + dx:pad.shape[0] - 1 + dx, 1 + dy:pad.shape[1] - 1 + dy]
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
        solid = solid & (near >= broad)
    covered = np.zeros_like(solid)
    covered[:, :, :-1] = m.mat[:, :, 1:] > 0
    X, Y, Z = m.coords()
    col = hash01(np.floor(X * m.k).astype(np.int64), np.floor(Y * m.k).astype(np.int64), seed)
    top = solid & ~covered & (Z > min_z) & (col < density)
    m.put(top, "snow", tone=0.3 * (col < density * 0.5), normal=(X * 0, Y * 0, Z * 0 + 1))
    if m.fine:  # thicker where it settled: the voxel under the cap too
        under = np.zeros_like(top)
        under[:, :, :-1] = top[:, :, 1:]
        m.put(under & solid & (col < density * 0.6), "snow", tone=-0.4, normal=(X * 0, Y * 0, Z * 0 + 1))


def _bare_crown(m: Model, seed: int, clumps, dry=None):
    """Winter: the crown as branches forking out to where the leaf clumps were, ending in a
    fan of pixel-wide twigs; `dry` is a material for a few leaves still clinging on."""
    rng = Rng(seed, 9)
    tips = []
    for cx, cy, cz, r in clumps:
        base = np.array((cx, cy, cz - r * 0.3))
        for _n in range(rng.integers(2, 4)):
            a = rng.uniform(0, 6.28)
            d = np.array((math.cos(a) * rng.uniform(0.5, 0.9), math.sin(a) * rng.uniform(0.5, 0.9),
                          rng.uniform(0.35, 0.9)))
            end = base + d * r * 0.8
            sl, X, Y, Z = m.window(*((base + end) / 2), r * 0.5 + 2)
            m.put(segment(X, Y, Z, base, end, 0.55), "bark", tone=0.0, sl=sl)
            for _t in range(rng.integers(2, 4)):
                b = rng.uniform(0, 6.28)
                tip = end + np.array((math.cos(b), math.sin(b), rng.uniform(0.4, 1.4))) * r * rng.uniform(0.3, 0.5)
                m.put_points(curve(end, tip, bend=(rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6))), "bark",
                             tone=0.4)
                tips.append(tip)
    if dry:
        for tip in tips[::3]:
            m.put_points([tip + (rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), rng.uniform(-0.6, 0.3))
                          for _n in range(3)], dry, tone=0.2)


def _broadleaf(p, v, frame, frames, k, seed, materials, under, level, scale=1.0, bare=False,
               dry=None, after=None):
    """`after(m, crown_clumps)` adds fruit or flowers once the leaves are in place."""
    rng = Rng(seed, v)
    R, zc = p["r"] * scale, p["z"] * scale
    m = Model.empty(-18, 34, -18, 34, 0, int(zc + R * 1.6) + 4, k=k)
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
    if m.fine:
        _limbs(m, Rng(seed, v, 7), (C, C), top, trunk_h, clumps[1:])
    # Sway: each clump drifts on its own phase, more the higher it sits (bare crowns less).
    t = 2 * math.pi * frame / max(frames, 1)
    swayed = []
    for n, (x, y, z, r) in enumerate(clumps):
        amp = 0.6 * float(np.clip((z - trunk_h) / R + 0.4, 0.2, 1.2)) * (0.5 if bare else 1.0)
        ph = (x - y) * 0.06 + n * 0.5        # a gust crossing the crown, each clump lagging a little
        swayed.append((x + amp * math.sin(t + ph), y - 0.5 * amp * math.sin(t + ph), z, r))
    swayed.sort(key=lambda c: c[2])
    if bare:
        _bare_crown(m, seed * 31 + v, swayed[1:], dry)
        snow_caps(m, seed + v, density=0.8, min_z=trunk_h * 0.4, broad=3)
        return m
    leaf_mass(m, swayed, seed * 31 + v, materials, under, level=level)
    if after:
        after(m, swayed)
    return m


# Leaf materials per season look: (weighted top materials, underside, level).
SUMMER = ((("leaf", 1.0),), "leaf_dark", -1.2)
AUTUMN = ((("autumn", 0.5), ("rust_leaf", 0.25), ("gold_leaf", 0.25)), "rust_leaf", -1.0)
RED_AUTUMN = ((("rust_leaf", 0.55), ("autumn", 0.45)), "rust_leaf", -1.0)
BLOOM = ((("blossom", 0.95), ("leaf_dark", 0.05)), "leaf_dark", -1.3)
WHITE_BLOOM = ((("cream", 0.75), ("blossom", 0.12), ("leaf", 0.13)), "leaf_dark", -1.1)


def oak(v, frame, frames, k, season=None):
    if season == "winter":
        return _broadleaf(BROADLEAF[v], v, frame, frames, k, 101, (), "", 0, bare=True, dry="autumn")
    mats, under, level = AUTUMN if season == "autumn" else SUMMER
    return _broadleaf(BROADLEAF[v], v, frame, frames, k, 101, mats, under, level=level)


def _fallen(m: Model, v, material, seed, rate=0.07, tone=2.0):
    """A few fallen petals or leaves on the ground under the crown, thicker near the trunk."""
    X, Y, Z = m.coords()
    rho = np.hypot(X - C - 2, Y - C + 1)
    cell = hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64), seed + v)
    petals = (cell < rate * np.clip(1.3 - rho / 12, 0, 1)) & (rho > 3) & (Z < 1)
    m.put(petals, material, tone=tone + (cell < 0.02), only_empty=True)


def blossom(v, frame, frames, k, season=None):
    """The plain look is the spring bloom; summer is in leaf, autumn red-orange, winter bare."""
    if season == "winter":
        return _broadleaf(BROADLEAF[v], v, frame, frames, k, 103, (), "", 0, scale=0.92, bare=True)
    mats, under, level = {None: BLOOM, "summer": SUMMER, "autumn": RED_AUTUMN}[season]
    m = _broadleaf(BROADLEAF[v], v, frame, frames, k, 103, mats, under, level=level, scale=0.92)
    if season is None:
        _fallen(m, v, "blossom", 104)
    elif season == "autumn":
        _fallen(m, v, "rust_leaf", 104, rate=0.05, tone=0.8)
    return m


# Apple trees: smaller and rounder than the oak, with a low, spreading crown.
APPLE = (
    dict(r=8.0, z=17, lean=(1.0, -0.5), ring=6, spread=0.95, lobes=((0.8, 1.1, -0.25, 0.6),)),
    dict(r=7.5, z=16, lean=(-1.2, 0.8), ring=5, spread=1.05, lobes=((3.9, 1.1, -0.2, 0.62),)),
)


def _apples(seed):
    """Red apples hung on the outside of the crown, a voxel cluster each."""
    def add(m: Model, clumps):
        solid = m.mat > 0
        pad = np.pad(solid, 1)
        exposed = solid & ~(pad[2:, 1:-1, 1:-1] & pad[1:-1, 2:, 1:-1] & pad[1:-1, 1:-1, 2:])
        X, Y, Z = m.coords()
        pick = hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64),
                      np.floor(Z).astype(np.int64), seed) < 0.035
        seeds = exposed & pick & (Z > 9)
        grown = seeds.copy()
        for axis in range(3):
            grown |= np.roll(seeds, 1, axis) | np.roll(seeds, -1, axis)
        m.put(grown, "poppy", tone=0.7 + seeds * 0.8, normal=(X * 0, Y * 0, Z * 0 + 1))
    return add


def apple_tree(v, frame, frames, k, season=None):
    """Plain look: summer green with red apples; spring in white blossom; autumn orange with
    apples; winter bare grey-brown."""
    p = APPLE[v]
    if season == "winter":
        return _broadleaf(p, v, frame, frames, k, 107, (), "", 0, bare=True)
    mats, under, level = {None: SUMMER, "spring": WHITE_BLOOM, "autumn": AUTUMN}[season]
    after = None if season == "spring" else _apples(170 + v)
    m = _broadleaf(p, v, frame, frames, k, 107, mats, under, level=level, after=after)
    if season == "spring":
        _fallen(m, v, "cream", 171, rate=0.05, tone=1.5)
    elif season == "autumn":
        _fallen(m, v, "poppy", 172, rate=0.02, tone=0.8)
    return m


# ---- conifers ----

# Per variant: height, base radius, tiers, lean (x, y) at the top.
PINES = ((60, 11.5, 7, (0.0, 0.0)), (54, 10.0, 6, (1.5, -1.5)), (50, 12.5, 6, (-0.5, 0.5)),
         (63, 10.5, 8, (-1.0, -1.5)))


def pine(v, frame, frames, k, season=None):
    rng = Rng(102, v)
    h, r0, tiers, (lx, ly) = PINES[v]
    m = Model.empty(-10, 26, -10, 26, 0, h + 3, k=k)
    trunk(m, C, C, 1.7, h * 0.4, flare=1.6, taper=0.3)
    roots(m, rng, C, C, 4, 4.0, r=0.9)
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
        # Each tier is evaluated only in a box around it.
        sl, X, Y, Z = m.window(C + sx, C + sy, z0 + height / 2 - 2, max(r * 1.45 + 2, height / 2 + 3))
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
        tips = (sun > 0.1) & (speck > 0.55) & (Z > z0 + 1.5) & (rim > 0.6)
        hem = (Z < z0 - droop + 1.8) & (rim > 0.4)
        tone = (0.7 * np.clip((rim - 0.45) * 2.5, 0, 1) - 0.3 + tips * 0.8
                + (speck - 0.5) * 0.3 + (jag - 1) * 1.2 - hem * 1.8)
        if m.fine:
            # Needle sprays: streaks running out and down from the axis, so each tier reads
            # as layered branch tips; the hem frays where a streak ends.
            spray = value_noise(ang * rho * 1.8, (rho - Z * 0.6) * 0.45, np.full_like(Z, n * 7.0),
                                1.0, 330 + v)
            tone = tone + (spray - 0.5) * 1.3 + 0.3
            mask = mask & ~(hem & (spray < 0.38))
        m.put(mask, "leaf_dark", tone=tone, normal=nrm, sl=sl)
    if season == "winter":   # snow lying along every tier
        snow_caps(m, 120 + v, density=0.85, min_z=12, broad=3)
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


def bush(v, frame, frames, k, season=None):
    rng = Rng(104, v)
    m = Model.empty(-3, 19, -3, 19, 0, 15, k=k)
    _bush_shape(m, rng, "leaf", 400 + v, (0.95, 1.05, 0.85, 1.0)[v])
    if season == "winter":
        snow_caps(m, 410 + v, density=0.8, min_z=5, broad=4)
    return m


def berry_bush(v, frame, frames, k, season=None):
    rng = Rng(105, v)
    m = Model.empty(-3, 19, -3, 19, 0, 15, k=k)
    _bush_shape(m, rng, "leaf_dark", 500 + v, (1.0, 0.92, 1.05, 0.95)[v])
    solid = m.mat > 0
    exposed = solid & ~np.pad(solid, 1)[1:-1, 1:-1, 2:] | solid & ~np.pad(solid, 1)[2:, 1:-1, 1:-1] \
        | solid & ~np.pad(solid, 1)[1:-1, 2:, 1:-1]
    X, Y, Z = m.coords()
    pick = hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64),
                  np.floor(Z).astype(np.int64), 510 + v) < 0.09
    berries = exposed & pick & (Z > 2)
    m.put(berries, "violet" if v == 2 else "poppy", tone=0.8)
    if season == "winter":
        snow_caps(m, 520 + v, density=0.8, min_z=5, broad=4)
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


def tall_grass(v, frame, frames, k):
    rng = Rng(106, v)
    m = Model.empty(-4, 20, -4, 20, 0, 18, k=k)
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


def _flower_patch(v, k, seed, head, season=None):
    """In winter the same plants stand dried: straw stems bent over, brown seed heads."""
    rng = Rng(seed, v)
    m = Model.empty(-2, 18, -2, 18, 0, 14, k=k)
    winter = season == "winter"
    _blades(m, rng, 14, 5.5, 2, 4.5, ["straw", "soil"] if winter else ["grass", "leaf"], spread=2.0, tip=0.3)
    X, Y, Z = m.coords()
    for n in range(rng.integers(7, 11)):
        a, d = rng.uniform(0, 6.28), 5.5 * math.sqrt(rng.uniform(0.05, 1))
        x, y = C + d * math.cos(a), C + d * math.sin(a)
        h = rng.uniform(3.5, 7.5)
        if winter:
            droop = rng.uniform(0.8, 2.0)
            tip = (x + droop * math.cos(a), y + droop * math.sin(a), h * 0.8)
            m.put_points(curve((x, y, 0.2), tip, bend=(droop * 0.5, 0)), "straw", tone=-0.3)
            m.put(ellipsoid(X, Y, Z, *tip, 0.7, 0.7, 0.6), "bark", tone=0.3,
                  normal=ellipsoid_normal(X, Y, Z, *tip, 0.7, 0.7, 0.6))
            continue
        m.put_points(curve((x, y, 0.2), (x, y, h), bend=(rng.uniform(-0.6, 0.6), 0)), "grass")
        head(m, X, Y, Z, x, y, h, rng)
    if winter:
        snow_caps(m, seed + v, density=0.5)
    return m


def _petal_angle(X, Y, x, y, count, phase):
    """Angular position within a petal: 0 at a petal's middle, 1 at the gap between two."""
    a = (np.arctan2(Y - y, X - x) * count / (2 * np.pi) + phase) % 1.0
    return np.abs(a - 0.5) * 2


def _leaf_pair(m, x, y, h, rng):
    """Two small leaves on a stem (fine grids)."""
    a = rng.uniform(0, 6.28)
    for side in (0, math.pi):
        z = h * rng.uniform(0.3, 0.55)
        tip = (x + 1.3 * math.cos(a + side), y + 1.3 * math.sin(a + side), z + 0.8)
        m.put_points(curve((x, y, z), tip, bend=(0, 0)), "leaf", tone=0.4)


def _poppy(m, X, Y, Z, x, y, h, rng):
    cup = ellipsoid(X, Y, Z, x, y, h + 0.6, 1.3, 1.3, 0.9)
    nrm = ellipsoid_normal(X, Y, Z, x, y, h, 1.3, 1.3, 1.3)
    if m.fine:  # four crinkled petals with dark folds round a black boss
        r = 1.6
        cup = ellipsoid(X, Y, Z, x, y, h + 0.7, r, r, 1.0) & ~ellipsoid(X, Y, Z, x, y, h + 1.4, r - 0.5,
                                                                        r - 0.5, 0.8)
        fold = _petal_angle(X, Y, x, y, 4, rng.uniform(0, 1)) > 0.8
        m.put(cup, "poppy", normal=nrm, tone=0.5 - fold * 0.9)
        m.put(ellipsoid(X, Y, Z, x, y, h + 1.0, 0.5, 0.5, 0.4), "ink", tone=0.5)
        _leaf_pair(m, x, y, h, rng)
        return
    m.put(cup, "poppy", normal=nrm, tone=0.4)
    m.put_points([(x, y, h + 1.2)], "ink")


def _daisy(m, X, Y, Z, x, y, h, rng):
    petals = ellipsoid(X, Y, Z, x, y, h + 0.5, 1.6, 1.6, 0.6)
    if m.fine:  # separate petals round a domed yellow centre
        petals &= _petal_angle(X, Y, x, y, 8, rng.uniform(0, 1)) < 0.7
        m.put(petals, "cream", tone=0.7 - (np.hypot(X - x, Y - y) > 1.2) * 0.3)
        m.put(ellipsoid(X, Y, Z, x, y, h + 0.8, 0.6, 0.6, 0.45), "yellow", tone=0.6,
              normal=(X - x, Y - y, Z - h))
        _leaf_pair(m, x, y, h, rng)
        return
    m.put(petals, "cream", tone=0.6)
    m.put_points([(x, y, h + 1.0)], "yellow", tone=0.8)


def _lavender(m, X, Y, Z, x, y, h, rng):
    # Fine grids carry twice the florets, in pairs round the spike.
    for k in range(5 * m.k):
        m.put_points([(x + rng.uniform(-0.5, 0.5), y + rng.uniform(-0.5, 0.5), h + k * (0.8 / m.k))],
                     "violet", tone=0.2 + k * (0.25 / m.k))


def flowers_red(v, frame, frames, k, season=None):
    return _flower_patch(v, k, 107, _poppy, season)


def flowers_white(v, frame, frames, k, season=None):
    return _flower_patch(v, k, 108, _daisy, season)


def flowers_violet(v, frame, frames, k, season=None):
    return _flower_patch(v, k, 109, _lavender, season)


# Per variant: cap material and the cluster as (dx, dy, scale); the first is the biggest.
MUSHROOMS = (
    ("poppy", ((0.0, 0.0, 1.25), (3.6, 2.2, 0.7), (-2.6, 3.0, 0.5))),
    ("bark", ((0.5, -0.5, 1.15), (-3.0, 1.6, 0.85), (3.0, 3.2, 0.6), (-0.4, 4.2, 0.42))),
    ("poppy", ((-1.0, 0.0, 0.9), (2.6, 1.2, 0.72))),
    ("yellow", ((0.0, 0.0, 1.0), (2.9, -1.4, 0.8), (-2.7, 1.8, 0.7), (1.6, 3.6, 0.55),
                (-1.2, -3.2, 0.5))),
)


def mushrooms(v, frame, frames, k):
    m = Model.empty(-1, 17, -1, 17, 0, 12, k=k)
    X, Y, Z = m.coords()
    cap_mat, cluster = MUSHROOMS[v]
    for n, (dx, dy, sc) in enumerate(cluster):
        x, y = C + dx, C + dy
        top, rs = 1.5 + 3.6 * sc, 0.55 + 0.45 * sc
        # Stem with a slight bulge at the foot, then a domed cap with a pale gill rim.
        m.put(cylinder(X, Y, Z, x, y, rs + 0.3 * (Z < 1.2), 0, top + 0.5), "cream",
              normal=cylinder_normal(X, Y, Z, x, y), tone=0.2)
        rc, rz = 2.4 * sc + 0.3, 1.8 * sc + 0.3
        cap = ellipsoid(X, Y, Z, x, y, top, rc, rc, rz) & (Z >= top - 0.2)
        nrm = ellipsoid_normal(X, Y, Z, x, y, top - 0.6, rc, rc, rz)
        m.put(cap, cap_mat, normal=nrm, tone=0.6 if cap_mat == "bark" else 0.0)
        rim = cap & (Z < top + 0.6) & (np.hypot(X - x, Y - y) > rc - 1.0)
        m.put(rim, "cream", tone=-0.6, normal=nrm)
        if cap_mat == "poppy":
            spots = (hash01(np.floor(X * 1.4).astype(np.int64), np.floor(Y * 1.4).astype(np.int64),
                            np.floor(Z * 1.4).astype(np.int64), 111 + n) < 0.14) & (Z > top + 0.6)
            m.put(cap & spots, "cream", tone=0.9, normal=nrm)
    return m


def rock(v, frame, frames, k):
    rng = Rng(112, v)
    m = Model.empty(-3, 19, -3, 19, 0, 11, k=k)
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
    if v in (1, 3):  # a few daisies tucked against the stone
        for a in (0.5, 1.15, 1.9):
            fx, fy = C + 6.3 * math.cos(a), C + 6.3 * math.sin(a)
            h = 1.8 + rng.uniform(0, 1.5)
            m.put_points(curve((fx, fy, 0.2), (fx, fy, h)), "grass")
            petals = ((0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6))
            m.put_points([(fx + dx, fy + dy, h + 0.5) for dx, dy in petals], "cream", tone=0.6)
            m.put_points([(fx, fy, h + 0.6)], "yellow", tone=0.8)
    return m


def stump(v, frame, frames, k):
    rng = Rng(113, v)
    m = Model.empty(-3, 19, -3, 19, 0, 14, k=k)
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
    if v == 0:  # an axe left in the stump
        m.put(box(X, Y, Z, C - 0.2, C + 2.6, C - 0.5, C + 0.5, h - 1.6, h + 1.4), "metal", tone=0.8)
        handle = segment(X, Y, Z, (C + 1.2, C, h + 0.6), (C + 5.5, C - 2.2, h + 5.5), 0.6)
        m.put(handle, "wood", tone=0.6)
    if v == 1:
        moss = (m.mat > 0) & (Z > 1) & (Z < h - 1) & (value_noise(X, Y, Z, 2, 650) > 0.55)
        m.put(moss, "grass", tone=-0.2)
        m.put(cylinder(X, Y, Z, C + 4.8, C + 1.5, 0.6, 0, 2.5), "cream")
        m.put(ellipsoid(X, Y, Z, C + 4.8, C + 1.5, 2.6, 1.6, 1.6, 1.0) & (Z > 2.2), "wood_light",
              normal=(X - C - 4.8, Y - C - 1.5, Z - 1.6))
    return m


def reeds(v, frame, frames, k):
    rng = Rng(114, v)
    m = Model.empty(-4, 20, -4, 20, 0, 22, k=k)
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


def lily_pads(v, frame, frames, k):
    rng = Rng(115, v)
    m = Model.empty(-2, 18, -2, 18, 0, 4, k=k)
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


# ---- batch 2 ----

def sunflowers(v, frame, frames, k, season=None):
    """Three or four tall stems, big yellow faces turned south-east (towards +x +y)."""
    rng = Rng(190, v)
    m = Model.empty(-4, 20, -4, 20, 0, 30, k=k)
    X, Y, Z = m.coords()
    n = 3 + (v % 2)
    face_n = np.array((0.62, 0.62, 0.48) if season != "winter" else (0.5, 0.5, -0.7))
    face_n /= np.linalg.norm(face_n)
    for i in range(n):
        a = i * 2.4 + rng.uniform(0, 1.2) + v
        d = rng.uniform(1.0, 4.0)
        x, y = C + d * math.cos(a), C + d * math.sin(a)
        h = rng.uniform(17, 24)
        top = (x + rng.uniform(-0.6, 0.6), y + rng.uniform(-0.6, 0.6), h)
        sl, Xs, Ys, Zs = m.window(x, y, h / 2, (2, 2, h / 2 + 1))
        m.put(segment(Xs, Ys, Zs, (x, y, 0), top, 0.45), "straw" if season == "winter" else "grass", tone=-0.2,
              sl=sl)
        for z, side in ((h * 0.35, 1), (h * 0.55, -1), (h * 0.75, 1)):   # broad leaves up the stem
            b = a + side * 1.6
            c = (x + 1.6 * math.cos(b), y + 1.6 * math.sin(b), z)
            sl, Xs, Ys, Zs = m.window(*c, 2.2)
            m.put(ellipsoid(Xs, Ys, Zs, *c, 1.7, 1.7, 0.45), "bark" if season == "winter" else "leaf",
                  tone=0.3 - 0.5 * (Zs < z), sl=sl,
                  normal=(Xs - x, Ys - y, Zs * 0 + 2.0))
        # The head: a disc facing the sun's side of the garden, petals round a seed centre.
        cx, cy, cz = top[0] + face_n[0] * 0.6, top[1] + face_n[1] * 0.6, h + 0.6
        sl, Xs, Ys, Zs = m.window(cx, cy, cz, 4.0)
        rel = np.stack(np.broadcast_arrays(Xs - cx, Ys - cy, Zs - cz), -1)
        depth = rel @ face_n
        radial = np.sqrt(np.maximum((rel ** 2).sum(-1) - depth ** 2, 0))
        disc = (np.abs(depth) < 0.55) & (radial < 3.3)
        ref = np.cross(face_n, (0, 0, 1))
        ang = np.arctan2(rel @ np.cross(face_n, ref), rel @ ref)
        petal = disc & (radial > 1.6) & ((np.cos(ang * 13) > -0.2) | (radial < 2.2))
        centre = disc & (radial <= 1.6)
        seeds = (hash01(np.floor(Xs * 3).astype(np.int64), np.floor(Ys * 3).astype(np.int64),
                        np.floor(Zs * 3).astype(np.int64), 191) - 0.5)
        nrm = tuple(np.broadcast_to(c, Xs.shape * 0 + depth.shape) for c in face_n)
        if season == "winter":   # dried: the petals gone, the seed head dark and bowed
            m.put(centre | (disc & (radial < 2.2)), "bark", tone=-0.2 + seeds, normal=nrm, sl=sl)
            continue
        m.put(petal, "yellow", tone=0.4 - 0.6 * (radial > 2.9), normal=nrm, sl=sl)
        m.put(centre, "bark", tone=0.4 + seeds - 0.5 * (radial > 1.2), normal=nrm, sl=sl)
        m.put((depth < -0.4) & (depth > -1.0) & (radial < 1.6), "grass", tone=-0.4, sl=sl)
    return m


def log_pile(v, frame, frames, k):
    """Split logs stacked three, two and one along y, pale cut ends, a little moss on top."""
    m = Model.empty(-1, 17, -1, 17, 0, 12, k=k)
    X, Y, Z = m.coords()
    rng = Rng(195, v)
    r = 1.9
    for row, count in ((0, 3), (1, 2), (2, 1)):
        for i in range(count):
            x = C + (i - (count - 1) / 2) * 2 * r * 0.98 + rng.uniform(-0.2, 0.2)
            z = r + row * r * 1.72
            y0, y1 = 2.6 + rng.uniform(-0.8, 0.6), 13.4 + rng.uniform(-0.6, 0.8)
            rho = np.hypot(X - x, Z - z)
            log = (rho <= r) & (Y >= y0) & (Y < y1)
            bark = (value_noise(np.arctan2(Z - z, X - x) * 4, Y * 0.5, rho, 1.0, 196 + i) - 0.5) * 1.4
            m.put(log, "bark", tone=bark, normal=(X - x, Y * 0, Z - z))
            ends = log & ((Y >= y1 - 0.5) | (Y < y0 + 0.5))
            rings = (np.sin(rho * 5.5) > 0.6) * -0.6
            m.put(ends, "wood_light", tone=0.5 + rings - (rho > r - 0.45) * 1.4,
                  normal=(X * 0, np.where(Y > C, 1.0, -1.0) + X * 0, Z * 0))
            if row == 2 or (row == 1 and i == 0):
                moss = log & (Z > z + r * 0.5) & (value_noise(X, Y, Z, 1.5, 197) > 0.5) & ~ends
                m.put(moss, "grass", tone=-0.2)
    return m


def stepping_stones(v, frame, frames, k):
    """Three or four flat grey stones sitting in the water, a dark wet rim at the waterline."""
    rng = Rng(198, v)
    m = Model.empty(-1, 17, -1, 17, 0, 3, k=k)
    X, Y, Z = m.coords()
    n = 3 + (v % 2)
    for i in range(n):
        t = (i + 0.5) / n
        x = 2.5 + 11.0 * t + rng.uniform(-1.0, 1.0)
        y = 13.5 - 11.0 * t + rng.uniform(-1.0, 1.0)
        rx, ry = rng.uniform(1.8, 2.6), rng.uniform(1.6, 2.3)
        wob = (value_noise(X, Y, Z, 1.6, 199 + i + v * 7) - 0.5) * 0.5
        top = 1.3 + rng.uniform(0, 0.5)
        stone = (((X - x) / rx) ** 2 + ((Y - y) / ry) ** 2 <= 1 + wob) & (Z < top - 0.6 * ((X - x) ** 2 / rx ** 2 + (Y - y) ** 2 / ry ** 2))
        m.put(stone, "stone", tone=-0.4 - (Z < 0.6) * 1.4 + wob, normal=(X - x, Y - y, Z * 0 + 2.5))
        lap = (((X - x) / (rx + 0.6)) ** 2 + ((Y - y) / (ry + 0.6)) ** 2 <= 1) & ~stone & (Z < 0.5)
        m.put(lap, "water", tone=1.4)
    return m
