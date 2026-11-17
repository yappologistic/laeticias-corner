"""Garden pieces: joining hedges and fences, beds, hive, scarecrow, well, lamp, seats, fire, bridge.

Rotatable pieces are modelled facing +y (towards the lower left of the screen).
"""

import math

import numpy as np

from palette import GLOW, MAT, _rgb
from voxel import (Halo, Model, Rng, box, cells3, curve, cylinder, cylinder_normal, ellipsoid,
                   ellipsoid_normal, gable, hash01, masonry, segment, slope_normal, value_noise)
from models.nature import C, _leaves, canopy, leaf_mass, snow_caps

N_BIT, E_BIT, S_BIT, W_BIT = 1, 2, 4, 8
ARMS = {N_BIT: (0, -1), E_BIT: (1, 0), S_BIT: (0, 1), W_BIT: (-1, 0)}


def _arm_region(X, Y, bit, half):
    """Voxels of the strip running from the tile centre out through edge `bit`, and beyond."""
    dx, dy = ARMS[bit]
    if dx:
        along = (X - C) * dx
        return (along >= 0) & (np.abs(Y - C) <= half), np.abs(Y - C)
    along = (Y - C) * dy
    return (along >= 0) & (np.abs(X - C) <= half), np.abs(X - C)


def _joined(mask: int, m: Model, part):
    """Build `part(across_distance, strip)` for the centre and each open arm, with the
    neighbours' arms as unseen context so light and leaves continue across the tile edge."""
    X, Y, Z = m.coords()
    centre = np.maximum(np.abs(X - C), np.abs(Y - C))
    part(centre, np.ones_like(centre, bool) & (centre < 8))
    for bit in ARMS:
        if mask & bit:
            strip, across = _arm_region(X, Y, bit, 8)
            part(across, strip)
    m.ghost_outside(0, 16, 0, 16)


def hedge(mask, frame, frames, k, season=None):
    m = Model.empty(-8, 24, -8, 24, 0, 16, k=k)
    X, Y, Z = m.coords()
    # Leaf texture repeats every tile so neighbouring hedges continue each other exactly.
    wob = (value_noise(X, Y, Z, 2.0, 700, period=8) - 0.5) * 1.3
    height, half = 13.0, 5.2

    def part(across, strip):
        prof = (np.clip(across, 0, None) / (half + wob * 0.6)) ** 3 + (Z / (height + wob)) ** 3
        m.put(strip & (prof <= 1) & (Z >= 0), "leaf")

    _joined(mask, m, part)
    solid = m.mat > 0
    m.density_normals(solid, radius=2)
    speck = value_noise(X, Y, Z, 1.6, 710, period=10)
    sun = m.nrm[..., 0] * -0.45 + m.nrm[..., 1] * 0.28 + m.nrm[..., 2] * 0.85
    # The speckle is kept fainter on fine grids, where the leaves already carry the texture.
    m.tone[solid] = (np.where((sun > 0.55) & (speck > 0.5), 0.7, 0.0) + (speck - 0.5) * 0.5 / k
                     - 0.4 * (Z < 2))[solid]
    if m.fine:  # clipped leaves, on a lattice that repeats every tile so joins stay seamless
        keep = _leaves(m, solid, m.nrm, m.tone, 711, leaf=16 / 12, period=12)
        m.carve(solid & ~keep)
        # Clipped hedges are smoother than free foliage: halve the leaf-by-leaf contrast.
        m.tone[keep] = 0.5 * m.tone[keep] + 0.5 * np.clip(m.tone[keep], -0.6, 0.6)
    if season == "winter":
        snow_caps(m, 730, density=0.8, min_z=7, broad=4)
    return m


def fence(mask, frame, frames, k):
    m = Model.empty(-8, 24, -8, 24, 0, 14, k=k)
    X, Y, Z = m.coords()
    grain = (value_noise(X * 2, Y * 2, Z * 0.3, 1.0, 720) - 0.5) * 0.8

    def part(across, strip):
        rails = ((Z >= 4) & (Z < 6)) | ((Z >= 8) & (Z < 10))
        m.put(strip & (across < 0.5 + 0.01) & rails & (np.maximum(np.abs(X - C), np.abs(Y - C)) >= 1),
              "wood_light", tone=grain)

    _joined(mask, m, part)
    post = (np.abs(X - C) < 1.01) & (np.abs(Y - C) < 1.01)
    m.put(post & (Z < 11), "wood", tone=grain)
    m.put((np.abs(X - C) < 0.6) & (np.abs(Y - C) < 0.6) & (Z >= 11) & (Z < 12), "wood", tone=0.5)
    return m


# ---------- 1x1 garden pieces ----------

def planter(v, frame, frames, k, stage=None):
    """Stages: g0 raked soil, g1 sprouts in rows, g2 leafy with no crop yet, g3 (and the plain
    key) ripe."""
    rng = Rng(130, v)
    m = Model.empty(0, 16, 0, 16, 0, 16, k=k)
    X, Y, Z = m.coords()
    frame_box = box(X, Y, Z, 1, 15, 1, 15, 0, 5)
    inner = box(X, Y, Z, 2.5, 13.5, 2.5, 13.5, 0, 5)
    plank = ((np.floor(Z) % 2.5) < 0.6) * -0.6
    m.put(frame_box & ~inner, "wood", tone=plank)
    # The rim caps the boards only: the bed stays open so the soil shows.
    m.put(box(X, Y, Z, 0.5, 15.5, 0.5, 15.5, 4.5, 5.5) & ~box(X, Y, Z, 2.5, 13.5, 2.5, 13.5, 0, 99),
          "wood_light", tone=0.3)
    m.put(inner & (Z < 4), "soil", tone=(hash01(np.floor(X).astype(np.int64),
                                                 np.floor(Y).astype(np.int64), 131) - 0.5))
    # A little marker stake in the front corner.
    m.put(box(X, Y, Z, 13.6, 14.3, 13.6, 14.3, 0, 8), "wood_light", tone=-0.2)
    m.put(box(X, Y, Z, 12.4, 15.2, 14.3, 14.8, 5.8, 8.2), "cream", tone=0.3)
    spots = [(5, 5), (11, 5), (5, 11), (11, 11)]
    if stage is not None and stage < 3:
        _young_bed(m, v, stage, rng, spots)
        return m
    if v == 0:      # cabbages
        for x, y in spots:
            r = rng.uniform(2.2, 2.7)
            canopy(m, [(x, y, 4 + r * 0.6, r)], "grass", 132 + x * 3 + y,
                   leafy=0.25, light_tone=0.6)
    elif v == 1:    # carrots: feathery tops and orange shoulders
        for row in (4.5, 8, 11.5):
            for x in (4, 6.5, 9, 11.5):
                m.put(ellipsoid(X, Y, Z, x, row, 4.2, 0.9, 0.9, 0.8), "orange", tone=0.4)
                for k in range(3):
                    a = k * 2.1 + x
                    m.put_points([(x + math.cos(a) * t, row + math.sin(a) * t, 4.5 + t * 1.6)
                                  for t in np.linspace(0, 1.6, 6)], "grass", tone=0.6)
    elif v == 2:    # pumpkins on a vine
        for x, y, r in ((5.5, 6, 3.0), (10.5, 10.5, 2.5)):
            ang = np.arctan2(Y - y, X - x)
            ribs = (np.cos(ang * 6) > 0.6) * -0.7
            m.put(ellipsoid(X, Y, Z, x, y, 4 + r * 0.7, r, r, r * 0.75), "orange", tone=ribs,
                  normal=ellipsoid_normal(X, Y, Z, x, y, 4 + r * 0.7, r, r, r * 0.75))
            m.put(cylinder(X, Y, Z, x, y, 0.6, 4 + r * 1.3, 4 + r * 1.3 + 1.5), "bark")
        canopy(m, [(11, 5, 5.5, 2.4), (5, 11.5, 5.5, 2.4)], "leaf", 133)
    else:           # tomato stakes
        for x, y in ((5.5, 8), (10.5, 8)):
            m.put(box(X, Y, Z, x - 0.5, x + 0.5, y - 0.5, y + 0.5, 4, 15), "wood_light")
            canopy(m, [(x, y, 7, 2.6), (x + 0.5, y - 0.5, 10.5, 2.3), (x - 0.3, y + 0.4, 13, 1.8)],
                   "leaf", 134 + int(x))
            for k in range(5):
                a, z = k * 2.4 + x, 6.5 + k * 1.4
                px, py = x + 2.2 * math.cos(a), y + 2.2 * math.sin(a)
                m.put(ellipsoid(X, Y, Z, px, py, z, 0.9, 0.9, 0.9), "poppy", tone=0.6)
    return m


ROWS = (4.6, 8.0, 11.4)       # the bed's planting rows (along x)


def _young_bed(m: Model, v, stage, rng: Rng, spots):
    X, Y, Z = m.coords()
    inner = box(X, Y, Z, 2.5, 13.5, 2.5, 13.5, 0, 5)
    # Raked ridges along the rows, a darker furrow between them.
    d = np.min([np.abs(Y - r) for r in ROWS], axis=0)
    ridge = inner & (Z < 4.0 + 0.6 * (d < 0.9)) & (Z >= 3.0)
    m.put(ridge, "soil", tone=0.5 * (d < 0.5) - 0.6 * (d > 1.3)
          + (hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), 135) - 0.5) * 0.6)
    if stage == 0:
        return
    if stage == 1:   # pairs of seed leaves in neat rows
        for row in ROWS:
            for x in np.arange(3.8, 13.0, 1.9):
                x += rng.uniform(-0.3, 0.3)
                m.put_points(curve((x, row, 4.4), (x, row, 5.4), bend=(0, 0)), "grass", tone=0.2)
                m.put_points([(x - 0.5, row, 5.6), (x + 0.5, row, 5.6), (x - 0.7, row + 0.2, 5.4),
                              (x + 0.7, row - 0.2, 5.4)], "grass", tone=1.0)
        return
    # Leafy: the plants are up, but nothing to pick yet.
    if v in (0, 2):
        for n, (x, y) in enumerate(spots):
            canopy(m, [(x, y, 5.2, 1.9 if v == 0 else 1.6)], "grass" if v == 0 else "leaf", 136 + n,
                   leafy=0.3, light_tone=0.6)
    elif v == 1:
        for row in ROWS:
            for x in (4, 6.5, 9, 11.5):
                for j in range(3):
                    a = j * 2.1 + x
                    m.put_points([(x + math.cos(a) * t, row + math.sin(a) * t, 4.5 + t * 1.3)
                                  for t in np.linspace(0, 1.3, 5)], "grass", tone=0.5)
    else:
        for x, y in ((5.5, 8), (10.5, 8)):
            m.put(box(X, Y, Z, x - 0.5, x + 0.5, y - 0.5, y + 0.5, 4, 15), "wood_light")
            canopy(m, [(x, y, 7, 2.0), (x + 0.4, y - 0.4, 9.5, 1.6)], "leaf", 137 + int(x))


def beehive(v, frame, frames, k):
    m = Model.empty(0, 16, 0, 16, 0, 22, k=k)
    X, Y, Z = m.coords()
    for x in (4, 11):
        for y in (4, 11):
            m.put(box(X, Y, Z, x, x + 1, y, y + 1, 0, 3), "wood")
    m.put(box(X, Y, Z, 3, 13, 3, 14.5, 3, 4), "wood_light")
    tiers = ((4, 9, "cream"), (9, 13.5, "straw"), (13.5, 17.5, "cream"))
    for z0, z1, mat in tiers:
        lip = (Z >= z1 - 0.8)
        m.put(box(X, Y, Z, 3.5, 12.5, 4, 13, z0, z1), mat, tone=-0.7 * (Z < z0 + 0.8) + 0.2 * lip)
    # Entrance slot and landing board on the front.
    m.carve(box(X, Y, Z, 6, 10, 12, 13, 4, 5.5))
    m.put(box(X, Y, Z, 6, 10, 11, 12, 4, 5.5), "ink")
    m.put(box(X, Y, Z, 5.5, 10.5, 13, 15, 4, 4.8), "wood_light", tone=0.4)
    # Roof with a little overhang.
    roof = gable(X, Y, Z, 2.5, 13.5, 3, 14, 17.5, 3.5, along_x=False)
    m.put(roof, "roof", tone=-0.8 * ((np.floor(Y) % 2) == 0),
          normal=slope_normal(X, Y, Z, 8, 8.5, 3.5 / 5.5, along_x=False))
    m.put(box(X, Y, Z, 2, 14, 2.5, 14.5, 17.5, 18.2), "wood", tone=-0.3)
    if m.fine:
        # Hand-hold notches on each box, and a flat stone on the roof to keep it down.
        for z0, z1, _mat in tiers:
            m.put(box(X, Y, Z, 6.5, 9.5, 12.9, 13.1, (z0 + z1) / 2 - 0.3, (z0 + z1) / 2 + 0.5), "wood", tone=-0.8)
            m.put(box(X, Y, Z, 12.4, 12.6, 7.0, 10.0, (z0 + z1) / 2 - 0.3, (z0 + z1) / 2 + 0.5), "wood", tone=-0.8)
        m.put(ellipsoid(X, Y, Z, 8.0, 8.2, 21.6, 2.4, 1.6, 0.9) & (Z > 20.8), "stone", tone=0.4,
              normal=ellipsoid_normal(X, Y, Z, 8.0, 8.2, 21.0, 2.4, 1.6, 1.5))
    # Lavender for the bees, growing at the hive's foot.
    rng = Rng(141, v)
    for k in range(5):
        x, y, h = 14.2 + rng.uniform(-0.8, 0.8), 9.5 + k * 1.2, rng.uniform(4, 6.5)
        m.put_points(curve((x, y, 0.2), (x + 0.3, y, h - 2)), "grass")
        for j in range(4):
            m.put_points([(x + 0.3, y, h - 2 + j * 0.7)], "violet", tone=0.3 + j * 0.25)
    return m


def scarecrow(v, frame, frames, k):
    m = Model.empty(-1, 17, 0, 16, 0, 34, k=k)
    X, Y, Z = m.coords()
    m.put(box(X, Y, Z, 7.5, 8.5, 7.5, 8.5, 0, 24), "wood")
    shirt = box(X, Y, Z, 5.5, 10.5, 6.6, 9.6, 11, 20)
    m.put(shirt, "red_paint", tone=0.0)
    m.put(box(X, Y, Z, 8.5, 10.5, 9.4, 9.8, 13, 15.5), "violet", tone=0.6)      # patch
    m.put(box(X, Y, Z, 5.5, 10.5, 6.5, 9.7, 10.5, 11.5), "wood", tone=-0.3)   # belt
    for sgn in (-1, 1):
        p, q = (8, 8, 18.5), (8 + sgn * 6.5, 8, 18.8)
        m.put(segment(X, Y, Z, p, q, 1.6), "red_paint", normal=(Y * 0 + 0, Y - 8, Z - 18.6))
        m.put(segment(X, Y, Z, q, (8 + sgn * 7.5, 8, 18.3), 1.2), "straw", tone=0.6)
    rng = Rng(140, v)
    for k in range(12):
        x, y = 8 + rng.uniform(-2.2, 2.2), 8 + rng.uniform(-1.2, 1.4)
        m.put_points([(x, y, z) for z in np.linspace(8.5, 11, 6)], "straw", tone=0.5)
    if m.fine:
        # Buttons down the shirt, straw poking out of the collar, a stitched patch on the hat.
        for z in (17.5, 15.5, 13.5):
            m.put_points([(8.0, 9.75, z)], "cream", tone=0.6)
        for a in np.linspace(0, 2 * math.pi, 9)[:-1]:
            m.put_points(curve((8 + 1.6 * math.cos(a), 8 + 1.4 * math.sin(a), 19.8),
                               (8 + 2.3 * math.cos(a), 8 + 2.0 * math.sin(a), 19.1), bend=(0, 0)), "straw", tone=0.6)
    head = ellipsoid(X, Y, Z, 8, 8, 21.8, 2.6, 2.4, 2.6)
    m.put(head, "cream", normal=ellipsoid_normal(X, Y, Z, 8, 8, 21.8, 2.6, 2.4, 2.6))
    for x in (7, 9):
        m.put_points([(x, 10.3, 22.4)], "ink")
    m.put_points([(7.5, 10.3, 20.8), (8.5, 10.3, 20.8)], "ink")
    m.put(cylinder(X, Y, Z, 8, 8, 3.8, 24.5, 25.3), "straw", tone=0.3)
    m.put(cylinder(X, Y, Z, 8, 8, 2.5, 25.3, 28.5), "straw", normal=cylinder_normal(X, Y, Z, 8, 8))
    m.put(cylinder(X, Y, Z, 8, 8, 2.6, 25.3, 26.3), "red_paint")
    if m.fine:
        m.put(box(X, Y, Z, 6.6, 8.4, 9.8, 10.7, 26.5, 27.9), "violet", tone=0.4)   # a patch on the hat
        m.put_points([(x, 10.35, 20.9 + 0.25 * math.sin(x * 4)) for x in np.linspace(6.9, 9.1, 7)], "ink", tone=0.8)
    # A crow perched on the hat, unimpressed.
    m.put(ellipsoid(X, Y, Z, 8.2, 8, 29.8, 1.7, 1.1, 1.2), "ink", tone=0.3)
    m.put(ellipsoid(X, Y, Z, 9.6, 8, 31.2, 0.9, 0.85, 0.85), "ink", tone=0.5)
    m.put(segment(X, Y, Z, (6.8, 8, 30.0), (5.6, 8, 31.0), 0.55), "ink")
    m.put_points([(10.5, 8, 31.1)], "yellow", tone=0.8)
    m.put_points([(9.9, 8.8, 31.5)], "cream", tone=1.0)
    return m


def well(v, frame, frames, k):
    m = Model.empty(0, 16, 0, 16, 0, 27, k=k)
    X, Y, Z = m.coords()
    rho = np.hypot(X - C, Y - C)
    ring = (rho <= 6.2) & (rho > 4.0) & (Z < 7)
    course = (np.floor(Z / 2.0) % 2)
    seam = np.cos(np.arctan2(Y - C, X - C) * 7 + course * 0.45) > 0.85
    m.put(ring, "stone", tone=-0.9 * seam - 0.8 * ((Z % 2.0) < 0.5),
          normal=cylinder_normal(X, Y, Z, C, C))
    m.put((rho <= 6.6) & (rho > 3.6) & (Z >= 7) & (Z < 8), "stone", tone=0.6)
    m.put((rho <= 4.0) & (Z < 4), "water", tone=-0.6)
    for x in (2.2, 13.8):
        m.put(box(X, Y, Z, x - 1, x + 1, C - 1, C + 1, 6, 20), "wood")
    m.put(box(X, Y, Z, 2.2, 13.8, C - 0.5, C + 0.5, 15.5, 16.5), "wood_light")
    if m.fine:
        # A pixel of rope wound on the axle and hanging to a hooped bucket with a bail handle.
        m.put(cylinder(X, Y, Z, C, C, 0.25, 11.5, 15.5), "straw", tone=0.4)
        m.put(box(X, Y, Z, C - 1.6, C + 1.6, C - 0.7, C + 0.7, 15.2, 16.8) &
              ((X % 0.5) < 0.25), "straw", tone=-0.3)
        m.put(cylinder(X, Y, Z, C, C, 1.5, 8.5, 11.5) & ~cylinder(X, Y, Z, C, C, 1.0, 9.0, 12),
              "wood", normal=cylinder_normal(X, Y, Z, C, C),
              tone=(np.cos(np.arctan2(Y - C, X - C) * 6) > 0.7) * -0.6)
        m.put(cylinder(X, Y, Z, C, C, 1.6, 8.5, 11.5) & ((np.abs(Z - 9.0) < 0.25) | (np.abs(Z - 11.0) < 0.25)),
              "metal", tone=0.3, normal=cylinder_normal(X, Y, Z, C, C))
        m.put(cylinder(X, Y, Z, C, C, 0.9, 9.0, 10.5), "water", tone=0.6)
        m.put_points(curve((C - 1.5, C, 11.5), (C + 1.5, C, 11.5), bend=(0, 0)) + [0, 0, 0], "metal")
        handle = [(C + 1.5 * math.cos(t), C, 11.5 + 1.0 * math.sin(t)) for t in np.linspace(0, math.pi, 12)]
        m.put_points(handle, "metal", tone=0.4)
    else:
        m.put(box(X, Y, Z, C - 0.3, C + 0.3, C - 0.3, C + 0.3, 11, 15.5), "ink")
        m.put(cylinder(X, Y, Z, C, C, 1.5, 8.5, 11.5), "wood", normal=cylinder_normal(X, Y, Z, C, C),
              tone=-0.8 * ((Z > 9.5) & (Z < 10.2)))
    roof = gable(X, Y, Z, -0.5, 16.5, 2.5, 13.5, 19.5, 6.5)
    course = np.floor((19.5 + 6.5 - Z) / 1.7)
    rows = (course % 2) == 0
    tone = -0.7 * rows
    if m.fine:  # each shingle its own shade, a pixel joint between them, a lit lower lip
        tile = np.floor((X + course * 1.1) / 2.2)
        tone = tone + (hash01(course.astype(np.int64), tile.astype(np.int64), 162) - 0.5) * 0.7 \
            - (((X + course * 1.1) % 2.2) < 0.5) * 0.5 + (((19.5 + 6.5 - Z) % 1.7) > 1.3) * 0.4
    m.put(roof, "roof", tone=tone, normal=slope_normal(X, Y, Z, 8, 8, 6.5 / 5.5))
    m.put(roof & ((X < 0.5) | (X > 15.5)), "wood", tone=-0.3)
    m.put(box(X, Y, Z, -0.8, 16.8, C - 0.6, C + 0.6, 25.4, 26.6), "wood", tone=0.2)   # ridge beam
    if m.fine:
        moss = roof & (value_noise(X, Y, Z, 1.4, 163) > 0.8)
        m.put(moss, "grass", tone=-0.4, normal=slope_normal(X, Y, Z, 8, 8, 6.5 / 5.5))
    # A crank on the axle and moss in the stones' shady joints.
    m.put(segment(X, Y, Z, (14.0, C, 16), (15.4, C, 16), 0.45), "metal", tone=0.4)
    m.put(segment(X, Y, Z, (15.4, C, 16), (15.4, C, 13.2), 0.45), "metal", tone=0.4)
    m.put(segment(X, Y, Z, (15.4, C, 13.2), (15.4, C + 1.6, 13.2), 0.5), "wood_light")
    moss = ring & (Z > 2) & (value_noise(X, Y, Z, 1.8, 160) > 0.66)
    m.put(moss, "grass", tone=-0.2, normal=cylinder_normal(X, Y, Z, C, C))
    return m


def lamp(v, frame, frames, k):
    m = Model.empty(1, 15, 1, 15, 0, 36, k=k)
    X, Y, Z = m.coords()
    cyl = cylinder_normal(X, Y, Z, C, C)
    # Stepped stone plinth, then a slim post with collars.
    m.put(box(X, Y, Z, C - 3, C + 3, C - 3, C + 3, 0, 2), "stone", tone=0.2 - 0.6 * (Z < 0.8))
    m.put(box(X, Y, Z, C - 2, C + 2, C - 2, C + 2, 2, 3.5), "stone", tone=0.5)
    m.put(cylinder(X, Y, Z, C, C, 1.3, 3.5, 6), "metal", normal=cyl)
    m.put(cylinder(X, Y, Z, C, C, 0.8, 6, 22), "metal", normal=cyl)
    m.put(cylinder(X, Y, Z, C, C, 1.4, 20.5, 22), "metal", normal=cyl, tone=0.3)
    # Lantern: a tray, glowing panes inside a four-post cage, a pyramid cap and a finial.
    m.put(box(X, Y, Z, C - 2.6, C + 2.6, C - 2.6, C + 2.6, 22, 23), "metal", tone=0.2)
    pane = box(X, Y, Z, C - 2, C + 2, C - 2, C + 2, 23, 28.5)
    m.put(pane, "lamp", tone=(Z > 26) * 0.6)
    if m.fine:  # leaded panes: a pixel of came across the middle of each face
        lead = (np.abs(X - C) < 0.25) | (np.abs(Y - C) < 0.25) | (np.abs(Z - 25.8) < 0.25)
        m.put(pane & lead & ((np.abs(X - C) > 1.5) | (np.abs(Y - C) > 1.5)), "metal", tone=0.2)
    posts = (np.abs(np.abs(X - C) - 2.1) < 0.6) & (np.abs(np.abs(Y - C) - 2.1) < 0.6)
    m.put(box(X, Y, Z, C - 2.7, C + 2.7, C - 2.7, C + 2.7, 23, 28.5) & posts, "metal")
    m.put(box(X, Y, Z, C - 2.8, C + 2.8, C - 2.8, C + 2.8, 28.5, 29.3), "metal", tone=0.4)
    cap = np.maximum(np.abs(X - C), np.abs(Y - C)) <= 2.8 - (Z - 29.3) * 0.85
    on_x = np.abs(X - C) > np.abs(Y - C)          # which of the four pyramid faces
    m.put(cap & (Z >= 29.3) & (Z < 32.5), "metal",
          normal=(np.where(on_x, X - C, 0), np.where(on_x, 0, Y - C), Z * 0 + 2.0))
    m.put(ellipsoid(X, Y, Z, C, C, 33.3, 0.9, 0.9, 0.9), "metal", tone=0.8)
    m.halos.append(Halo(C, C, 25.5, 20, _rgb(GLOW[1]), 1.0))
    m.halos.append(Halo(C, C, 0, 17, _rgb(GLOW[0]), 0.45))   # a pool of light on the ground
    return m


def bench(v, frame, frames, k):
    m = Model.empty(0, 16, 0, 16, 0, 14, k=k)
    X, Y, Z = m.coords()
    for x in (2.5, 12.5):
        for y in (6, 10):
            m.put(box(X, Y, Z, x, x + 1, y, y + 1, 0, 5), "metal")
        m.put(box(X, Y, Z, x, x + 1, 5, 6, 0, 12), "metal")
        m.put(box(X, Y, Z, x - 0.3, x + 1.3, 5, 11.5, 7.5, 8.3), "wood")
    seat = box(X, Y, Z, 1.5, 14.5, 6, 11.5, 5, 6)
    if m.fine:  # real gaps between the slats, grain along them and a screw at each support
        seat &= (Y % 1.4) >= 0.5
        grain = (value_noise(X * 0.3, Y * 4, Z, 1.0, 255) - 0.5) * 0.8
        m.put(seat, "wood_light", tone=grain + ((Y % 1.4) >= 1.15) * -0.5)
        for x in (3.0, 13.0):
            m.put(seat & (np.abs(X - x) < 0.25) & (Z >= 5.5), "metal", tone=0.5)
    else:
        m.put(seat, "wood_light", tone=(np.floor(Y) % 2 == 0) * -0.7)
    for z in (7, 9.5):
        back = box(X, Y, Z, 1.5, 14.5, 5.2, 6.2, z, z + 1.6)
        m.put(back, "wood_light", tone=0.2 - ((Z - z) < 0.5 / k) * 0.6 * m.fine)
    # Someone left their book.
    m.put(box(X, Y, Z, 9, 12.5, 7.2, 10.2, 6, 7.0), "poppy", tone=0.3)
    m.put(box(X, Y, Z, 9.2, 12.3, 10.0, 10.2, 6.1, 6.8), "cream", tone=0.6)
    return m


def picnic_table(v, frame, frames, k):
    m = Model.empty(0, 32, 0, 16, 0, 12, k=k)
    X, Y, Z = m.coords()
    slats = (np.floor(Y / 2.0) % 2 == 0) * -0.5 - ((Y % 2.0) < 0.35) * 0.8
    top = box(X, Y, Z, 2, 30, 4, 12, 9, 10.2)
    if m.fine:  # gaps between the boards, and grain along them
        top &= (Y % 2.0) >= 0.5
        slats = slats + (value_noise(X * 0.3, Y * 4, Z, 1.0, 275) - 0.5) * 0.8
    m.put(top, "wood_light", tone=slats)
    for y0 in (0.8, 12.2):
        m.put(box(X, Y, Z, 3, 29, y0, y0 + 3, 5, 6), "wood_light", tone=((Y % 1.5) < 0.3) * -0.6)
    for x in (7, 25):
        for a, b in (((x, 1.5, 0), (x, 7.5, 9.5)), ((x, 14.5, 0), (x, 8.5, 9.5))):
            m.put(segment(X, Y, Z, a, b, 0.75), "wood")
        m.put(box(X, Y, Z, x - 0.6, x + 0.6, 0.5, 15.5, 4.2, 5), "wood")
    # A check runner draped across the middle and a picnic basket.
    sq = 1.4 / k ** 0.5  # smaller checks on finer grids
    check = ((np.floor(X / sq) + np.floor(Y / sq)) % 2) == 0
    cloth = box(X, Y, Z, 12, 20, 3.6, 12.4, 10.2, 10.7) | \
        (box(X, Y, Z, 12, 20, 3.2, 12.8, 8.0, 10.7) & ((Y < 3.7) | (Y >= 12.3)))
    m.put(cloth & check, "red_paint", tone=0.6)
    m.put(cloth & ~check, "cream", tone=0.3)
    m.put(box(X, Y, Z, 22, 25.5, 6, 9, 10.2, 12.6), "straw", tone=((X % 1.2) < 0.4) * -0.6)
    m.put(segment(X, Y, Z, (22.6, 7.5, 12.6), (23.75, 7.5, 14.4), 0.4) |
          segment(X, Y, Z, (23.75, 7.5, 14.4), (24.9, 7.5, 12.6), 0.4), "wood", tone=0.3)
    return m


def campfire(v, frame, frames, k):
    m = Model.empty(0, 16, 0, 16, 0, 16, k=k)
    X, Y, Z = m.coords()
    for k in range(9):
        a = k * 2 * math.pi / 9 + 0.2
        x, y = C + 5.2 * math.cos(a), C + 5.2 * math.sin(a)
        r = 1.5 + 0.35 * math.sin(k * 3.1)
        m.put(ellipsoid(X, Y, Z, x, y, 0.6, r, r, r * 0.8) & (Z >= 0), "stone",
              normal=ellipsoid_normal(X, Y, Z, x, y, 0.4, r, r, r))
    m.put((np.hypot(X - C, Y - C) < 4.2) & (Z < 0.8), "ember",
          tone=(hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64), 150) - 0.5) * 2)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        p = (C + 4.2 * math.cos(a), C + 4.2 * math.sin(a), 0.8)
        m.put(segment(X, Y, Z, p, (C, C, 6.0), 0.9), "bark")
    t = frame / frames * 2 * math.pi
    flick = value_noise(X * 0.9, Y * 0.9, Z - frame * 2.3, 2.2, 151 + frame % 2)
    for k in range(3):
        a = k * 2.1 + t * 0.5
        cx, cy = C + 1.2 * math.cos(a), C + 1.2 * math.sin(a)
        h = 7.5 + 2.2 * math.sin(t + k * 2.0) + (k == 0) * 2
        frac = np.clip(1 - (Z - 1) / h, 0, 1)
        r = 2.6 * frac ** 0.7 * (0.75 + 0.5 * flick)
        tongue = ((X - cx) ** 2 + (Y - cy) ** 2 <= r * r) & (Z >= 1) & (Z < 1 + h)
        core = (X - cx) ** 2 + (Y - cy) ** 2 <= (r * 0.45) ** 2
        m.put(tongue, "fire", tone=frac * 2.6 - 1.6 + core * 1.2 + (flick - 0.5))
    # Spare firewood stacked by the ring, cut ends showing.
    for x, z in ((13.4, 0.75), (14.9, 0.75), (14.15, 2.0)):
        log = (np.hypot(X - x, Z - z) <= 0.75) & (Y >= 10.5) & (Y < 15.5)
        m.put(log, "bark", normal=(X - x, Y * 0, Z - z))
        m.put(log & (Y >= 15), "wood_light", tone=0.4 - 0.8 * (np.hypot(X - x, Z - z) < 0.3))
    m.halos.append(Halo(C, C, 4, 18, _rgb(GLOW[0]), 0.9 + 0.1 * math.sin(t * 2)))
    return m


def bridge(v, frame, frames, k):
    m = Model.empty(0, 16, 0, 16, -1, 13, k=k)
    X, Y, Z = m.coords()
    arch = 1.2 + 2.8 * np.sin(np.pi * np.clip(X, 0, 16) / 16)
    plank = (np.floor(X / 2.0) % 2 == 0) * -0.4 - ((X % 2.0) < 0.4) * 0.9
    m.put((Y >= 3) & (Y < 13) & (Z < arch) & (Z >= arch - 1.6), "wood_light", tone=plank)
    for y in (3, 12):
        m.put((Y >= y) & (Y < y + 1) & (Z < arch - 1.6) & (Z >= arch - 3), "wood")
        for x in (1, 8, 15):
            top = 1.2 + 2.8 * math.sin(math.pi * x / 16)
            m.put(box(X, Y, Z, x - 0.5, x + 0.5, y, y + 1, top - 2, top + 5.5), "wood")
        m.put((Y >= y) & (Y < y + 1) & (Z >= arch + 4.5) & (Z < arch + 5.5), "wood_light", tone=0.3)
    return m


# ---------- batch 2 ----------

def stone_wall(mask, frame, frames, k):
    """A knee-high dry-stone wall of grey and ochre stones with moss along the top; joins like
    the fence. Stones come from a tile-periodic cell pattern so lengths continue seamlessly."""
    m = Model.empty(-8, 24, -8, 24, 0, 10, k=k)
    X, Y, Z = m.coords()
    height, half = 7.5, 2.9

    def part(across, strip):
        batter = half - 0.12 * Z                     # leaning in a little towards the top
        cap = Z < height - 1.4 * (np.clip(across, 0, None) / half) ** 2
        m.put(strip & (np.clip(across, 0, None) <= batter) & cap & (Z >= 0), "stone")

    _joined(mask, m, part)
    solid = m.mat > 0
    idx = np.nonzero(solid)
    pts = np.stack([X[idx[0], 0, 0], Y[0, idx[1], 0], Z[0, 0, idx[2]]], 1)
    # Flat stones: cells stretched along the wall, one course every couple of units.
    f1, f2, off, h = cells3(pts * (0.75, 0.75, 1.3), 3.0, 740, jitter=0.7, period=4)
    joint = (f2 - f1) < 0.3
    lit_edge = (off[:, 2] > 0.6)
    tone = np.zeros(m.mat.shape, np.float32)
    tone[idx] = 0.5 + (h - 0.5) * 1.0 - joint * 1.9 + lit_edge * 0.5
    ochre = np.zeros(m.mat.shape, bool)
    ochre[idx] = (h > 0.84) & ~joint
    m.density_normals(solid, radius=1)
    m.tone[solid] = tone[solid]
    m.mat[ochre] = MAT["wood_light"]
    # Moss in the cap and the shady joints.
    covered = np.zeros_like(solid)
    covered[:, :, :-1] = solid[:, :, 1:]
    moss_n = value_noise(X, Y, Z, 1.6, 741, period=10)
    m.put(solid & ~covered & (Z > height - 2.2) & (moss_n > 0.5), "grass", tone=-1.1 + (moss_n > 0.68) * 0.6)
    m.ghost_outside(0, 16, 0, 16)
    return m


def arbor(v, frame, frames, k):
    """A white-painted rose arch; the opening faces +x (walk through along x)."""
    m = Model.empty(0, 16, -1, 17, 0, 30, k=k)
    X, Y, Z = m.coords()
    top = 20.0
    for y in (2.0, 14.0):
        for x in (6.2, 9.8):
            m.put(box(X, Y, Z, x - 0.6, x + 0.6, y - 0.6, y + 0.6, 0, top), "white_paint")
        # Trellis between the pair of posts.
        lattice = (np.abs(((Z + (X - 6.2) * 1.0) % 2.4) - 1.2) < 0.25) | (np.abs(((Z - (X - 6.2)) % 2.4) - 1.2) < 0.25)
        m.put(box(X, Y, Z, 6.2, 9.8, y - 0.25, y + 0.25, 1.5, top) & lattice, "white_paint", tone=-0.3)
    # The arch: two curved beams over the path, slats across.
    rho = np.hypot(Y - 8.0, Z - top)
    for x in (6.2, 9.8):
        m.put((np.abs(rho - 6.0) < 0.6) & (Z >= top) & (np.abs(X - x) < 0.6), "white_paint", tone=0.3)
    ang = np.arctan2(Z - top, Y - 8.0)
    slats = (np.abs(rho - 6.0) < 0.5) & (Z >= top) & (np.abs(X - 8.0) < 2.4) & ((ang * 7 % 1.0) < 0.3)
    m.put(slats, "white_paint", tone=-0.2)
    # Roses climbing both sides and over the top.
    clumps = []
    rng = Rng(150, v)
    for y in (2.0, 14.0):
        for z in (4.0, 9.0, 14.0, 19.0):
            clumps.append((8.0 + rng.uniform(-1.6, 1.6), y + rng.uniform(-0.6, 0.6), z, rng.uniform(1.8, 2.6)))
    for a in np.linspace(0.35, math.pi - 0.35, 5):
        clumps.append((8.0 + rng.uniform(-1.2, 1.2), 8.0 + 6.0 * math.cos(a), top + 6.0 * math.sin(a), 2.2))
    leaf_mass(m, clumps, 151, (("leaf", 0.6), ("blossom", 0.4)), "leaf_dark", cluster=(1.6, 2.4), level=-0.6)
    return m


def bird_feeder(v, frame, frames, k):
    """A wooden post with a little roofed tray of seed."""
    m = Model.empty(2, 14, 2, 14, 0, 26, k=k)
    X, Y, Z = m.coords()
    m.put(box(X, Y, Z, C - 0.8, C + 0.8, C - 0.8, C + 0.8, 0, 16), "wood",
          tone=((value_noise(X * 3, Y * 3, Z * 0.4, 1.0, 160) - 0.5) * 0.8))
    for a in range(4):   # little feet bracing the post
        dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[a]
        m.put(segment(X, Y, Z, (C + dx * 0.6, C + dy * 0.6, 2.4), (C + dx * 2.6, C + dy * 2.6, 0.2), 0.45), "wood")
    tray = box(X, Y, Z, C - 3.2, C + 3.2, C - 3.2, C + 3.2, 16, 17.2)
    m.put(tray, "wood_light", tone=0.2)
    m.put(box(X, Y, Z, C - 3.2, C + 3.2, C - 3.2, C + 3.2, 17.2, 17.9) & ~box(X, Y, Z, C - 2.6, C + 2.6, C - 2.6, C + 2.6, 0, 99),
          "wood_light", tone=-0.2)
    seed = box(X, Y, Z, C - 2.6, C + 2.6, C - 2.6, C + 2.6, 17.2, 17.7)
    m.put(seed, "straw", tone=(hash01(np.floor(X * 4).astype(np.int64), np.floor(Y * 4).astype(np.int64), 161) - 0.5) * 2)
    for x in (C - 2.7, C + 2.7):
        m.put(box(X, Y, Z, x - 0.35, x + 0.35, C - 0.35, C + 0.35, 17.2, 20.5), "wood")
    roof = gable(X, Y, Z, C - 4.0, C + 4.0, C - 4.0, C + 4.0, 20.3, 3.2)
    m.put(roof, "roof", tone=-0.7 * ((np.floor((23.5 - Z) / 1.0) % 2) == 0),
          normal=slope_normal(X, Y, Z, C, C, 3.2 / 4.0))
    return m


def hay_bale(v, frame, frames, k):
    """r0 a round golden bale lying on its side, r1 a square bale tied with twine; loose straw
    at the foot."""
    m = Model.empty(-1, 17, -1, 17, 0, 13, k=k)
    X, Y, Z = m.coords()
    if v == 0:
        r, cz = 5.6, 5.6
        rho = np.hypot(X - C, Z - cz)
        bale = (rho <= r) & (np.abs(Y - C) <= 4.8)
        ang = np.arctan2(Z - cz, X - C)
        streak = value_noise(ang * 6, Y * 0.6, rho * 0.3, 1.0, 165) - 0.5
        m.put(bale, "straw", tone=streak * 1.4, normal=(X - C, Y * 0, Z - cz))
        # The flat ends show the rolled spiral.
        ends = bale & (np.abs(Y - C) > 4.3)
        spiral = ((rho + ang / (2 * math.pi) * 1.1) % 1.1) < 0.35
        m.put(ends, "straw", tone=0.4 - spiral * 1.0 - (rho < 1.0) * 0.8, normal=(X * 0, np.sign(Y - C), Z * 0))
    else:
        bale = box(X, Y, Z, 2.0, 14.0, 4.5, 11.5, 0, 6.5)
        streak = value_noise(X * 0.4, Y * 2.0, Z * 2.0, 1.0, 166) - 0.5
        m.put(bale, "straw", tone=streak * 1.2 + (Z > 6.0) * 0.5)
        for x in (5.0, 11.0):   # two twine bands
            m.put(bale & (np.abs(X - x) < 0.3), "wood", tone=0.6)
        m.carve(bale & (Z > 6.0) & (hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), 167) < 0.2))
    rng = Rng(168, v)
    for _n in range(14):   # loose straw scattered round the foot
        a, d = rng.uniform(0, 6.28), rng.uniform(5.5, 7.8)
        x, y = C + d * math.cos(a), C + d * math.sin(a)
        b = rng.uniform(0, 6.28)
        m.put_points(curve((x, y, 0.2), (x + 1.4 * math.cos(b), y + 1.4 * math.sin(b), 0.3), bend=(0, 0)), "straw",
                     tone=rng.uniform(0, 1.2))
    return m


def hammock(v, frame, frames, k):
    """Two posts and a striped canvas hammock along x. The canvas sags to 8 units (16 px at
    64x32) at the middle, where the `lie` slot puts Laeticia."""
    m = Model.empty(0, 32, 0, 16, 0, 16, k=k)
    X, Y, Z = m.coords()
    for x in (1.8, 30.2):
        m.put(box(X, Y, Z, x - 0.9, x + 0.9, C - 0.9, C + 0.9, 0, 14.5), "wood",
              tone=((value_noise(X * 3, Y * 3, Z * 0.4, 1.0, 170) - 0.5) * 0.8))
        m.put(box(X, Y, Z, x - 1.1, x + 1.1, C - 1.1, C + 1.1, 14.5, 15.2), "wood", tone=0.4)
        for dy in (-1, 1):   # a guy brace into the ground
            m.put(segment(X, Y, Z, (x, C, 8.0), (x - np.sign(x - 16) * 3.0, C + dy * 3.0, 0.2), 0.4), "wood",
                  tone=-0.2)
    # Ropes from the post tops to the canvas ends, then the canvas hanging in a curve.
    sag = lambda x: 8.0 + 4.6 * ((x - 16.0) / 11.0) ** 2
    for x0, x1 in ((2.6, 6.0), (29.4, 26.0)):
        m.put_points(curve((x0, C, 13.8), (x1, C, sag(x1) + 0.2), bend=(0, 0)), "straw", tone=0.2)
    on = (X > 5.0) & (X < 27.0)
    across = (Y - C) / 2.8
    surf = sag(X) + 1.6 * across ** 2
    canvas = on & (np.abs(across) <= 1.0) & (np.abs(Z - surf) < 0.45)
    stripe = (np.floor((Y - C + 2.8) / 1.12) % 2) == 0
    m.put(canvas & stripe, "cream", tone=0.3, normal=(X * 0, -across, Z * 0 + 1))
    m.put(canvas & ~stripe, "green_paint", tone=-0.6, normal=(X * 0, -across, Z * 0 + 1))
    m.put(on & (np.abs(across) <= 1.08) & (np.abs(across) > 0.92) & (np.abs(Z - surf) < 0.6), "wood_light", tone=0.3)
    return m


def fountain(v, frame, frames, k):
    """A round stone basin with a two-tier spout; the falling water and the rings animate."""
    m = Model.empty(0, 32, 0, 32, 0, 24, k=k)
    X, Y, Z = m.coords()
    cx = cy = 16.0
    rho = np.hypot(X - cx, Y - cy)
    ang = np.arctan2(Y - cy, X - cx)
    t = frame / frames
    rim = (rho <= 13.0) & (rho > 11.0) & (Z < 5.0)
    course = masonry(m, ang * 12.0, Z, 1.6, 3.0, 175) if m.fine else -0.6 * ((Z % 2) < 0.5)
    m.put(rim, "stone", tone=course, normal=(X - cx, Y - cy, Z * 0))
    m.put((rho <= 13.4) & (rho > 10.7) & (Z >= 5.0) & (Z < 6.0), "stone", tone=0.6)
    # The pool: rings spreading from the spout and from where the streams land.
    pool = (rho <= 11.0) & (Z < 3.6)
    ripple = (np.abs(((rho - t * 3.0) % 3.0) - 1.5) < 0.35) & (rho > 2.0)
    m.put(pool, "water", tone=0.6 * ripple - 0.4 * (rho > 10.0) + 0.2)
    # Pedestal and two bowls.
    m.put((rho <= 1.6) & (Z < 10.5), "stone", normal=(X - cx, Y - cy, Z * 0), tone=0.2)
    for z0, r, depth in ((10.5, 6.0, 1.6), (16.0, 3.4, 1.2)):
        bowl = (rho <= r) & (Z >= z0) & (Z < z0 + depth) & (rho >= (r - 1.4) * np.clip((Z - z0) / depth, 0, 1) ** 0.5)
        m.put(bowl, "stone", tone=0.3 + 0.5 * (Z > z0 + depth - 0.6), normal=(X - cx, Y - cy, (Z - z0) * 2))
        m.put((rho < r - 0.6) & (Z >= z0 + depth - 0.6) & (Z < z0 + depth - 0.1), "water", tone=0.8)
        # Water spilling over the lip in thin sheets, broken into dashes that move down.
        sheet = (np.abs(rho - (r + 0.4)) < 0.4) & (Z < z0 + depth) & (Z > (3.6 if r > 5 else 11.6)) & \
            (np.cos(ang * (9 if r > 5 else 6)) > 0.2)
        dash = ((Z / 1.6 + t * 4) % 1.0) < 0.6
        m.put(sheet & dash, "water", tone=1.6)
        m.put(sheet & ~dash, "water", tone=0.6)
    m.put((rho <= 0.8) & (Z >= 10.5) & (Z < 16.0), "stone", tone=0.1)
    # The spout jet and its crown of drops.
    m.put((rho <= 0.5) & (Z >= 17.2) & (Z < 20.5), "water", tone=1.8)
    drops = [(cx + 1.4 * math.cos(a), cy + 1.4 * math.sin(a), 20.0 - ((t * 4 + n * 0.37) % 1.0) * 3.0)
             for n, a in enumerate(np.linspace(0, 2 * math.pi, 9)[:-1])]
    m.put_points(drops, "water", tone=2.0)
    moss = rim & (Z < 2.5) & (value_noise(X, Y, Z, 1.6, 176) > 0.62)
    m.put(moss, "grass", tone=-0.3, normal=(X - cx, Y - cy, Z * 0))
    return m


def rowboat(v, frame, frames, k):
    """A small wooden rowing boat along x, faded blue outside, two oars shipped inside, its
    painter rope trailing to the bank side."""
    m = Model.empty(0, 32, 0, 16, 0, 9, k=k)
    X, Y, Z = m.coords()
    L, B = 13.5, 5.2                      # half length, half beam
    u = (X - 16.0) / L
    half = B * np.sqrt(np.clip(1 - np.abs(u) ** 2.4, 0, 1)) * (1 - 0.25 * (u > 0) * u)
    keel = 0.2 + 1.8 * np.abs(u) ** 2.0
    gunwale = 4.6 + 1.4 * np.abs(u) ** 2.2
    hull = (np.abs(Y - C) <= half * np.clip((Z + 0.6) / 4.0, 0.45, 1.0)) & (Z >= keel - 0.4) & (Z < gunwale) & (np.abs(u) <= 1)
    inside = (np.abs(Y - C) <= half * np.clip((Z + 0.6) / 4.0, 0.45, 1.0) - 0.7) & (Z >= keel + 0.7)
    shell = hull & ~inside
    planks = ((Z * 1.0) % 1.4) < 0.3
    m.put(shell, "blue_paint", tone=-0.7 * planks + (value_noise(X, Y, Z, 1.4, 180) > 0.66) * 0.8,
          normal=(X * 0, (Y - C), Z * 0 + 0.3))
    m.put(shell & (Z > gunwale - 0.7), "wood_light", tone=0.3)
    m.put(hull & inside & (Z < keel + 1.3), "wood", tone=-0.6 * ((Y % 1.3) < 0.3))
    for x in (11.0, 20.0):   # thwarts
        m.put(box(X, Y, Z, x - 1.0, x + 1.0, 0, 16, 3.0, 3.7) & hull, "wood_light", tone=0.1)
    for dy in (-1.6, 1.6):   # oars shipped along the thwarts, blades towards the stern
        m.put(segment(X, Y, Z, (7.0, C + dy, 4.0), (24.0, C + dy * 0.8, 4.4), 0.35), "wood_light", tone=0.4)
        m.put(box(X, Y, Z, 5.0, 8.0, C + dy - 0.6, C + dy + 0.6, 3.9, 4.3), "wood_light", tone=0.2)
    # The painter: a rope from the bow ring down into the water.
    m.put_points(curve((29.3, C, 5.4), (31.8, C + 3.0, 0.3), bend=(0.6, 0)), "straw", tone=0.1)
    m.put((np.hypot(X - 16, (Y - C) * 2.2) > 14.2) & (np.hypot(X - 16, (Y - C) * 2.2) < 15.0) & (Z < 0.8),
          "water", tone=1.4)   # a waterline ripple round the hull
    return m
