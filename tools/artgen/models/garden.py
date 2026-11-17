"""Garden pieces: joining hedges and fences, beds, hive, scarecrow, well, lamp, seats, fire, bridge.

Rotatable pieces are modelled facing +y (towards the lower left of the screen).
"""

import math

import numpy as np

from palette import GLOW, _rgb
from voxel import (Halo, Model, Rng, box, curve, cylinder, cylinder_normal, ellipsoid,
                   ellipsoid_normal, gable, hash01, segment, slope_normal, value_noise)
from models.nature import C, canopy

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


def hedge(mask, frame, frames):
    m = Model.empty(-8, 24, -8, 24, 0, 16)
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
    m.tone[solid] = (np.where((sun > 0.55) & (speck > 0.5), 0.7, 0.0) + (speck - 0.5) * 0.5
                     - 0.4 * (Z < 2))[solid]
    return m


def fence(mask, frame, frames):
    m = Model.empty(-8, 24, -8, 24, 0, 14)
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

def planter(v, frame, frames):
    rng = Rng(130, v)
    m = Model.empty(0, 16, 0, 16, 0, 16)
    X, Y, Z = m.coords()
    frame_box = box(X, Y, Z, 1, 15, 1, 15, 0, 5)
    inner = box(X, Y, Z, 2.5, 13.5, 2.5, 13.5, 0, 5)
    plank = ((np.floor(Z) % 2.5) < 0.6) * -0.6
    m.put(frame_box & ~inner, "wood", tone=plank)
    m.put(box(X, Y, Z, 0.5, 15.5, 0.5, 15.5, 4.5, 5.5) & ~inner, "wood_light", tone=0.3)
    m.put(inner & (Z < 4), "soil", tone=(hash01(np.floor(X).astype(np.int64),
                                                 np.floor(Y).astype(np.int64), 131) - 0.5))
    # A little marker stake in the front corner.
    m.put(box(X, Y, Z, 13.6, 14.3, 13.6, 14.3, 0, 8), "wood_light", tone=-0.2)
    m.put(box(X, Y, Z, 12.4, 15.2, 14.3, 14.8, 5.8, 8.2), "cream", tone=0.3)
    spots = [(5, 5), (11, 5), (5, 11), (11, 11)]
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


def beehive(v, frame, frames):
    m = Model.empty(0, 16, 0, 16, 0, 22)
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
    # Lavender for the bees, growing at the hive's foot.
    rng = Rng(141, v)
    for k in range(5):
        x, y, h = 14.2 + rng.uniform(-0.8, 0.8), 9.5 + k * 1.2, rng.uniform(4, 6.5)
        m.put_points(curve((x, y, 0.2), (x + 0.3, y, h - 2)), "grass")
        for j in range(4):
            m.put_points([(x + 0.3, y, h - 2 + j * 0.7)], "violet", tone=0.3 + j * 0.25)
    return m


def scarecrow(v, frame, frames):
    m = Model.empty(-1, 17, 0, 16, 0, 34)
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
    head = ellipsoid(X, Y, Z, 8, 8, 21.8, 2.6, 2.4, 2.6)
    m.put(head, "cream", normal=ellipsoid_normal(X, Y, Z, 8, 8, 21.8, 2.6, 2.4, 2.6))
    for x in (7, 9):
        m.put_points([(x, 10.3, 22.4)], "ink")
    m.put_points([(7.5, 10.3, 20.8), (8.5, 10.3, 20.8)], "ink")
    m.put(cylinder(X, Y, Z, 8, 8, 3.8, 24.5, 25.3), "straw", tone=0.3)
    m.put(cylinder(X, Y, Z, 8, 8, 2.5, 25.3, 28.5), "straw", normal=cylinder_normal(X, Y, Z, 8, 8))
    m.put(cylinder(X, Y, Z, 8, 8, 2.6, 25.3, 26.3), "red_paint")
    # A crow perched on the hat, unimpressed.
    m.put(ellipsoid(X, Y, Z, 8.2, 8, 29.8, 1.7, 1.1, 1.2), "ink", tone=0.3)
    m.put(ellipsoid(X, Y, Z, 9.6, 8, 31.2, 0.9, 0.85, 0.85), "ink", tone=0.5)
    m.put(segment(X, Y, Z, (6.8, 8, 30.0), (5.6, 8, 31.0), 0.55), "ink")
    m.put_points([(10.5, 8, 31.1)], "yellow", tone=0.8)
    m.put_points([(9.9, 8.8, 31.5)], "cream", tone=1.0)
    return m


def well(v, frame, frames):
    m = Model.empty(0, 16, 0, 16, 0, 27)
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
    m.put(box(X, Y, Z, C - 0.3, C + 0.3, C - 0.3, C + 0.3, 11, 15.5), "ink")
    m.put(cylinder(X, Y, Z, C, C, 1.5, 8.5, 11.5), "wood", normal=cylinder_normal(X, Y, Z, C, C),
          tone=-0.8 * ((Z > 9.5) & (Z < 10.2)))
    roof = gable(X, Y, Z, -0.5, 16.5, 2.5, 13.5, 19.5, 6.5)
    rows = (np.floor((19.5 + 6.5 - Z) / 1.7) % 2) == 0
    m.put(roof, "roof", tone=-0.7 * rows, normal=slope_normal(X, Y, Z, 8, 8, 6.5 / 5.5))
    m.put(roof & ((X < 0.5) | (X > 15.5)), "wood", tone=-0.3)
    # A crank on the axle and moss in the stones' shady joints.
    m.put(segment(X, Y, Z, (14.0, C, 16), (15.4, C, 16), 0.45), "metal", tone=0.4)
    m.put(segment(X, Y, Z, (15.4, C, 16), (15.4, C, 13.2), 0.45), "metal", tone=0.4)
    m.put(segment(X, Y, Z, (15.4, C, 13.2), (15.4, C + 1.6, 13.2), 0.5), "wood_light")
    moss = ring & (Z > 2) & (value_noise(X, Y, Z, 1.8, 160) > 0.66)
    m.put(moss, "grass", tone=-0.2, normal=cylinder_normal(X, Y, Z, C, C))
    return m


def lamp(v, frame, frames):
    m = Model.empty(1, 15, 1, 15, 0, 36)
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


def bench(v, frame, frames):
    m = Model.empty(0, 16, 0, 16, 0, 14)
    X, Y, Z = m.coords()
    for x in (2.5, 12.5):
        for y in (6, 10):
            m.put(box(X, Y, Z, x, x + 1, y, y + 1, 0, 5), "metal")
        m.put(box(X, Y, Z, x, x + 1, 5, 6, 0, 12), "metal")
        m.put(box(X, Y, Z, x - 0.3, x + 1.3, 5, 11.5, 7.5, 8.3), "wood")
    slats = (np.floor(Y) % 2 == 0) * -0.7
    m.put(box(X, Y, Z, 1.5, 14.5, 6, 11.5, 5, 6), "wood_light", tone=slats)
    for z in (7, 9.5):
        m.put(box(X, Y, Z, 1.5, 14.5, 5.2, 6.2, z, z + 1.6), "wood_light", tone=0.2)
    # Someone left their book.
    m.put(box(X, Y, Z, 9, 12.5, 7.2, 10.2, 6, 7.0), "poppy", tone=0.3)
    m.put(box(X, Y, Z, 9.2, 12.3, 10.0, 10.2, 6.1, 6.8), "cream", tone=0.6)
    return m


def picnic_table(v, frame, frames):
    m = Model.empty(0, 32, 0, 16, 0, 12)
    X, Y, Z = m.coords()
    slats = (np.floor(Y / 2.0) % 2 == 0) * -0.5 - ((Y % 2.0) < 0.35) * 0.8
    m.put(box(X, Y, Z, 2, 30, 4, 12, 9, 10.2), "wood_light", tone=slats)
    for y0 in (0.8, 12.2):
        m.put(box(X, Y, Z, 3, 29, y0, y0 + 3, 5, 6), "wood_light", tone=((Y % 1.5) < 0.3) * -0.6)
    for x in (7, 25):
        for a, b in (((x, 1.5, 0), (x, 7.5, 9.5)), ((x, 14.5, 0), (x, 8.5, 9.5))):
            m.put(segment(X, Y, Z, a, b, 0.75), "wood")
        m.put(box(X, Y, Z, x - 0.6, x + 0.6, 0.5, 15.5, 4.2, 5), "wood")
    # A check runner draped across the middle and a picnic basket.
    check = ((np.floor(X / 1.4) + np.floor(Y / 1.4)) % 2) == 0
    cloth = box(X, Y, Z, 12, 20, 3.6, 12.4, 10.2, 10.7) | \
        (box(X, Y, Z, 12, 20, 3.2, 12.8, 8.0, 10.7) & ((Y < 3.7) | (Y >= 12.3)))
    m.put(cloth & check, "red_paint", tone=0.6)
    m.put(cloth & ~check, "cream", tone=0.3)
    m.put(box(X, Y, Z, 22, 25.5, 6, 9, 10.2, 12.6), "straw", tone=((X % 1.2) < 0.4) * -0.6)
    m.put(segment(X, Y, Z, (22.6, 7.5, 12.6), (23.75, 7.5, 14.4), 0.4) |
          segment(X, Y, Z, (23.75, 7.5, 14.4), (24.9, 7.5, 12.6), 0.4), "wood", tone=0.3)
    return m


def campfire(v, frame, frames):
    m = Model.empty(0, 16, 0, 16, 0, 16)
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


def bridge(v, frame, frames):
    m = Model.empty(0, 16, 0, 16, -1, 13)
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
