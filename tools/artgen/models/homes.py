"""Buildings, modelled facing +y (the windmill faces +x so both of its rotations show the sails)."""

import math

import numpy as np

from palette import GLOW, _rgb
from voxel import (Halo, Model, box, cone, cylinder, cylinder_normal, ellipsoid, gable, hash01,
                   segment, slope_normal, value_noise)
from models.nature import canopy


class Facade:
    """Openings cut into one wall plane. `face` is '+x', '-x', '+y' or '-y'; `plane` is the
    wall's outer coordinate on that axis."""

    def __init__(self, m: Model, face: str, plane: float):
        self.m = m
        X, Y, Z = m.coords()
        sign = 1 if face[0] == "+" else -1
        if face[1] == "y":
            self.along, self.depth = X, (Y - plane) * sign
            self.left_is_low = sign > 0     # on +y faces, smaller x is further left on screen
        else:
            self.along, self.depth = Y, (X - plane) * sign
            self.left_is_low = sign < 0
        self.Z = Z

    def _rect(self, a0, a1, z0, z1):
        return (self.along >= a0) & (self.along < a1) & (self.Z >= z0) & (self.Z < z1)

    def layer(self, n):
        """Voxels n layers inside the wall surface (0 = outermost); negative n is outside."""
        return (self.depth < -n) & (self.depth > -n - 1)

    def window(self, a0, a1, z0, z1, glass="glass", frame="wood_light", cross=True, sill=True):
        m, Z = self.m, self.Z
        rect = self._rect(a0, a1, z0, z1)
        m.carve(rect & self.layer(0))
        lit_side = (self.along < a0 + 1.5) if self.left_is_low else (self.along >= a1 - 1.5)
        shine = lit_side & (Z >= z1 - 2)
        m.put(rect & self.layer(1), glass, tone=shine * 1.4 - (Z < z0 + 1) * 0.5)
        ring = self._rect(a0 - 1, a1 + 1, z0 - 1, z1 + 1) & ~rect & self.layer(0)
        m.put(ring, frame, tone=0.2)
        if cross:
            mid_a, mid_z = (a0 + a1) / 2, (z0 + z1) / 2
            bars = (np.abs(self.along - mid_a) < 0.5) | (np.abs(Z - mid_z) < 0.5)
            m.put(rect & self.layer(1) & bars, frame, tone=-0.2)
        if sill:
            m.put(self._rect(a0 - 1.5, a1 + 1.5, z0 - 1.6, z0 - 0.6) & (self.layer(0) | self.layer(-1)),
                  frame, tone=0.5)

    def door(self, a0, a1, z0, z1, material="wood", frame="wood_light", knob=True):
        m, Z = self.m, self.Z
        rect = self._rect(a0, a1, z0, z1)
        m.carve(rect & self.layer(0))
        planks = ((self.along - a0) % 2.0 < 0.5) * -0.7
        m.put(rect & self.layer(1), material, tone=planks + (Z > z1 - 1) * -0.8)
        m.put(self._rect(a0 - 1, a1 + 1, z0, z1 + 1) & ~rect & self.layer(0), frame, tone=0.1)
        if knob:
            kx = a1 - 1.5 if self.left_is_low else a0 + 1.5
            m.put(self._rect(kx - 0.5, kx + 0.5, (z0 + z1) / 2 - 0.5, (z0 + z1) / 2 + 0.5)
                  & self.layer(0), "metal", tone=1.5)

    def flower_box(self, a0, a1, z, seed):
        m = self.m
        m.put(self._rect(a0, a1, z - 1.5, z) & (self.layer(-1) | self.layer(-2)), "wood", tone=0.2)
        blooms = self._rect(a0, a1, z, z + 1.5) & (self.layer(-1) | self.layer(-2))
        pick = hash01(np.floor(self.along * 2).astype(np.int64), np.floor(self.Z).astype(np.int64), seed)
        m.put(blooms & (pick < 0.55), "grass", tone=0.3)
        m.put(blooms & (pick >= 0.55) & (pick < 0.8), "poppy", tone=0.6)
        m.put(blooms & (pick >= 0.8), "cream", tone=0.6)


def gable_roof(m: Model, x0, x1, y0, y1, z0, rise, material="roof", verge="wood",
               along_x=True, row=1.8, thick=2.5, thatch=False):
    """Shingled (or thatched) gable roof; returns the mask of voxels under it."""
    X, Y, Z = m.coords()
    roof = gable(X, Y, Z, x0, x1, y0, y1, z0, rise, along_x)
    under = gable(X, Y, Z, x0, x1, y0, y1, z0 - thick, rise, along_x)
    if along_x:
        across, along, half = np.abs(Y - (y0 + y1) / 2), X, (y1 - y0) / 2
    else:
        across, along, half = np.abs(X - (x0 + x1) / 2), Y, (x1 - x0) / 2
    rows = np.floor((half - across) / row)
    joint = ((along + rows * 1.5) % 3.0) < 0.6
    edge = ((half - across) % row) < 0.55
    if thatch:  # straw streaks running down the slope, a dark band at each course
        streak = value_noise(along * 1.6, across * 0.25, Z * 0.25, 1.0, 801) - 0.5
        tone = streak * 1.4 - 0.7 * (((half - across) % (row * 2)) < 0.6)
    else:
        tone = -0.9 * edge - 0.4 * joint + 0.35 * (rows % 2) + (value_noise(X, Y, Z, 3, 800) - 0.5) * 0.4
    shell = roof & ~gable(X, Y, Z, x0, x1, y0, y1, z0 + 0.01, rise - thick, along_x)
    ends = (along < (x0 if along_x else y0) + 1) | (along >= (x1 if along_x else y1) - 1)
    nrm = slope_normal(X, Y, Z, (x0 + x1) / 2, (y0 + y1) / 2, rise / half, along_x)
    m.put(shell, material, tone=tone - 0.6 * (across < 0.8), normal=nrm)
    m.put(shell & ends, verge, tone=-0.2)
    return under & ~roof


def siding(Z, period=2.0):
    return ((Z % period) < 0.5) * -0.7


def cottage(v, frame, frames):
    m = Model.empty(0, 32, 0, 32, 0, 40)
    X, Y, Z = m.coords()
    x0, x1, y0, y1 = 4, 28, 7, 25
    m.put(box(X, Y, Z, x0 - 1, x1 + 1, y0 - 1, y1 + 1, 0, 3), "stone",
          tone=-0.8 * (((X + Y) % 4) < 0.6) - 0.6 * ((Z % 1.5) < 0.4))
    eave, rise = 15.0, 14.0
    walls = box(X, Y, Z, x0, x1, y0, y1, 3, eave + rise)
    under = gable(X, Y, Z, x0, x1, y0 - 0.01, y1 + 0.01, eave, rise)
    m.put(walls & ((Z < eave) | under), "plaster",
          tone=(value_noise(X, Y, Z, 2.5, 810) - 0.5) * 0.6)
    # Timber frame: corner posts, sill and head beams, a few studs and braces.
    beam = (Z < 4) | ((Z >= eave - 1) & (Z < eave))
    corner = ((X < x0 + 1.5) | (X >= x1 - 1.5)) & ((Y < y0 + 1.5) | (Y >= y1 - 1.5))
    studs = ((np.abs(X - 16) < 0.75) & ((Y < y0 + 1) | (Y >= y1 - 1))) | \
        ((np.abs(Y - 16) < 0.75) & ((X < x0 + 1) | (X >= x1 - 1)) & (Z < eave))
    shell = walls & ~box(X, Y, Z, x0 + 1, x1 - 1, y0 + 1, y1 - 1, 0, 99)
    m.put(shell & (beam | corner | studs) & ((Z < eave) | under), "wood", tone=-0.3)
    brace = shell & (Z < eave) & (Z > 4) & (np.abs((X - x0 - 2) - (Z - 4) * 0.9) < 0.7) & (X < 11)
    m.put(brace, "wood", tone=-0.3)
    front = Facade(m, "+y", y1)
    front.door(13.5, 18.5, 3, 12)
    for a in (7, 21):
        front.window(a, a + 4, 7, 11)
        front.flower_box(a - 1, a + 5, 5.5, 820 + a)
    m.put(box(X, Y, Z, 12.5, 19.5, y1 + 1, y1 + 3.5, 0, 1.6), "stone", tone=0.4)
    back = Facade(m, "-y", y0)
    for a in (8, 20):
        back.window(a, a + 4, 7, 11)
    for face, plane in (("+x", x1), ("-x", x0)):
        side = Facade(m, face, plane)
        side.window(13, 19, 7, 11)
        side.window(14.5, 17.5, 18, 21, cross=False, sill=False)
    gable_roof(m, x0 - 2.5, x1 + 2.5, y0 - 3, y1 + 3, eave - 1, rise + 2.5)
    chim = box(X, Y, Z, 20, 24, 10, 14, 3, 35)
    m.put(chim, "stone", tone=-0.8 * ((Z % 2) < 0.5) - 0.5 * (((X + Y + np.floor(Z / 2) * 2) % 4) < 0.6))
    m.put(box(X, Y, Z, 19.5, 24.5, 9.5, 14.5, 35, 36.5), "stone", tone=0.5)
    m.carve(box(X, Y, Z, 21, 23, 11, 13, 34, 37))
    m.put(box(X, Y, Z, 21, 23, 11, 13, 33, 34), "ink")
    return m


def toolshed(v, frame, frames):
    """Lean-to shed: braced door at the front, windows at the side and back, tools leaning on
    the other side, so every rotation shows something."""
    m = Model.empty(-2, 18, -2, 18, 0, 22)
    X, Y, Z = m.coords()
    x0, x1, y0, y1 = 2.5, 13.5, 3, 13
    low, high = 12.5, 16.5
    m.put(box(X, Y, Z, x0 - 0.5, x1 + 0.5, y0 - 0.5, y1 + 0.5, 0, 1.5), "stone",
          tone=-0.6 * (((X + Y) % 3) < 0.6))
    top = low + (high - low) * (Y - y0) / (y1 - y0)
    # Vertical boards: seams run up each wall, every board a slightly different tone.
    along = np.where((Y < y0 + 1) | (Y >= y1 - 1), X, Y)
    board = np.floor(along / 2.2)
    m.put(box(X, Y, Z, x0, x1, y0, y1, 1.5, 99) & (Z < top), "wood",
          tone=((along % 2.2) < 0.5) * -0.9 + (hash01(board.astype(np.int64), 860) - 0.5) * 0.6)
    corner = ((X < x0 + 1) | (X >= x1 - 1)) & ((Y < y0 + 1) | (Y >= y1 - 1))
    m.put(box(X, Y, Z, x0, x1, y0, y1, 1.5, 99) & (Z < top) & corner, "wood_light", tone=-0.2)
    front = Facade(m, "+y", y1)
    front.door(5.5, 10.5, 1.5, 11, material="wood_grey", frame="wood_light", knob=False)
    # Z brace and a latch on the door.
    a, z = front.along, Z
    brace = np.abs((a - 5.5) - (z - 2.5) * 5 / 7.5) < 0.6
    m.put(front._rect(5.5, 10.5, 2.5, 10) & front.layer(1) & brace, "wood_light", tone=-0.3)
    m.put(front._rect(9, 10, 6, 7) & front.layer(0), "metal", tone=1.2)
    Facade(m, "+x", x1).window(6, 10, 6, 9.5)
    Facade(m, "-y", y0).window(6.5, 9.5, 8, 10.5, cross=False, sill=False)
    rtop = low + (high - low) * (Y - y0) / (y1 - y0) + 0.5
    roof = (X >= x0 - 1.2) & (X < x1 + 1.2) & (Y >= y0 - 1.2) & (Y < y1 + 1.8) & \
        (Z >= rtop - 0.2) & (Z < rtop + 1.3)
    rows = np.floor(Y / 1.6)
    m.put(roof, "slate", tone=0.3 - 1.1 * ((Y % 1.6) < 0.5) - 0.5 * (((X + rows * 1.3) % 2.6) < 0.5)
          + 0.4 * (rows % 2), normal=(X * 0, -(high - low) / (y1 - y0) + X * 0, X * 0 + 1.0))
    m.put(roof & ((X < x0 - 0.2) | (X >= x1 + 0.2)), "wood_light", tone=-0.4)
    # A shovel and a rake leaning on the far side wall, a watering can by the door.
    m.put(segment(X, Y, Z, (x0 - 1.6, 5.0, 2.0), (x0 - 0.5, 6.0, 12.5), 0.5), "wood_light")
    m.put(box(X, Y, Z, x0 - 1.9, x0 - 1.1, 4.4, 6.0, 0, 2.6), "metal", tone=1.2)
    m.put(segment(X, Y, Z, (x0 - 1.4, 10.0, 0.5), (x0 - 0.5, 9.4, 12), 0.5), "wood_light")
    m.put(box(X, Y, Z, x0 - 1.4, x0 - 0.6, 7.6, 11.6, 11.5, 12.5), "metal", tone=0.4)
    can = (12.5, y1 + 2.2)
    m.put(cylinder(X, Y, Z, *can, 1.4, 0, 3), "metal", tone=0.6, normal=cylinder_normal(X, Y, Z, *can))
    m.put(segment(X, Y, Z, (11.3, y1 + 2.2, 1.5), (9.8, y1 + 2.4, 3.2), 0.45), "metal", tone=0.4)
    m.put(segment(X, Y, Z, (12.5, y1 + 1.2, 3.0), (12.5, y1 + 3.2, 3.0), 0.35), "metal", tone=0.2)
    return m


def coop(v, frame, frames):
    m = Model.empty(0, 16, 0, 17, 0, 24)
    X, Y, Z = m.coords()
    x0, x1, y0, y1 = 3, 13, 3.5, 11.5
    for x in (x0 + 0.5, x1 - 1.5):
        for y in (y0 + 0.5, y1 - 1.5):
            m.put(box(X, Y, Z, x, x + 1, y, y + 1, 0, 4), "wood")
    walls = box(X, Y, Z, x0, x1, y0, y1, 4, 20)
    under = gable(X, Y, Z, x0 - 0.01, x1 + 0.01, y0, y1, 13, 5, along_x=False)
    m.put(walls & ((Z < 13) | under), "red_paint", tone=siding(Z))
    corners = ((X < x0 + 1) | (X >= x1 - 1)) & ((Y < y0 + 1) | (Y >= y1 - 1))
    m.put(walls & corners & (Z < 13), "cream", tone=-0.2)
    m.put(box(X, Y, Z, x0, x1, y0, y1, 4, 5), "cream", tone=-0.4)
    front = Facade(m, "+y", y1)
    m.carve(front._rect(6.5, 9.5, 5, 9.5) & front.layer(0))
    m.put(front._rect(6.5, 9.5, 5, 9.5) & front.layer(1), "ink")
    m.put(front._rect(5.5, 10.5, 9.5, 10.5) & front.layer(0), "cream")
    side = Facade(m, "+x", x1)
    side.window(6, 9, 7, 10, glass="glass", frame="cream", sill=False)
    gable_roof(m, x0 - 1, x1 + 1, y0 - 1, y1 + 1, 12.5, 6.0, material="straw", verge="straw",
               along_x=False, row=1.4, thick=2, thatch=True)
    ramp_z = lambda y: 5 - (y - y1) * 1.0
    ramp = (X >= 6.5) & (X < 9.5) & (Y >= y1) & (Y < y1 + 5) & (Z < ramp_z(Y)) & (Z >= ramp_z(Y) - 1)
    m.put(ramp, "wood_light", tone=-0.8 * ((Y % 1.6) < 0.4))
    return m


def greenhouse(v, frame, frames):
    m = Model.empty(0, 32, 0, 32, 0, 26)
    X, Y, Z = m.coords()
    x0, x1, y0, y1 = 3, 29, 5, 27
    m.put(box(X, Y, Z, x0, x1, y0, y1, 0, 3), "stone", tone=-0.7 * (((X + Y) % 3) < 0.5))
    eave, rise = 13.0, 8.0
    body = box(X, Y, Z, x0, x1, y0, y1, 3, eave + rise) & \
        gable(X, Y, Z, x0, x1, y0 - 0.01, y1 + 0.01, eave, rise) | box(X, Y, Z, x0, x1, y0, y1, 3, eave)
    shell = body & ~box(X, Y, Z, x0 + 1, x1 - 1, y0 + 1, y1 - 1, 0, 99)
    m.put(shell, "glass_warm", tone=(((X - Y) % 7) < 1.2) * 1.0 - 0.5 * (Z < 6))
    roof_glass = gable(X, Y, Z, x0 - 0.5, x1 + 0.5, y0 - 1.5, y1 + 1.5, eave, rise + 1.3) & \
        ~gable(X, Y, Z, x0 - 0.5, x1 + 0.5, y0 - 1.5, y1 + 1.5, eave + 0.01, rise + 1.3 - 1.5)
    across = np.abs(Y - 16)
    m.put(roof_glass, "glass_cool", tone=0.6 + (((X + across) % 6) < 1.0) * 0.8)
    on_end = (X < x0 + 1) | (X >= x1 - 1)
    corner = on_end & ((Y < y0 + 1) | (Y >= y1 - 1))
    mullion = np.where(on_end, ((Y - y0 + 2.75) % 5.5) < 1.0, ((X - x0 + 2.2) % 4.33) < 1.0) | \
        corner | (Z < 4) | ((Z >= eave - 1) & (Z < eave)) | (np.abs(Z - 8.5) < 0.5)
    m.put(shell & mullion, "cream", tone=0.2)
    m.put(roof_glass & ((X - x0) % 4.33 < 1.0), "cream", tone=0.3)
    m.put(roof_glass & (across < 1.0), "cream", tone=0.5)
    # Plants pressed against the glass and a door at the front gable end.
    canopy(m, [(x, y, 4.5, 2.4) for x, y in ((7, y1 - 2), (12, y1 - 2), (20, y1 - 2), (25, y1 - 2),
                                              (x1 - 2, 10), (x1 - 2, 16), (x1 - 2, 22))],
           "leaf", 830)
    front = Facade(m, "+y", y1)
    front.door(14, 18, 3, 11, material="glass_cool", frame="cream", knob=False)
    return m


def barn(v, frame, frames):
    m = Model.empty(0, 48, 0, 32, 0, 44)
    X, Y, Z = m.coords()
    x0, x1, y0, y1 = 3, 45, 4, 28
    m.put(box(X, Y, Z, x0 - 0.5, x1 + 0.5, y0 - 0.5, y1 + 0.5, 0, 2), "stone", tone=-0.6 * ((X % 3) < 0.5))
    eave, yc, half = 18.0, 16.0, 12.0
    across = np.abs(Y - yc)
    # Gambrel profile: steep lower slope to a knee, shallow upper slope to the ridge.
    knee_a, knee_z, ridge = 7.0, 29.0, 36.0
    prof = np.where(across > knee_a, eave + (knee_z - eave) * (half - across) / (half - knee_a),
                    knee_z + (ridge - knee_z) * (knee_a - across) / knee_a)
    walls = box(X, Y, Z, x0, x1, y0, y1, 2, 99) & (Z < prof)
    m.put(walls, "red_paint", tone=((X % 2.5) < 0.5) * -0.7 + ((Y % 2.5) < 0.5) * -0.7)
    trim = ((X < x0 + 1) | (X >= x1 - 1)) & ((Y < y0 + 1) | (Y >= y1 - 1))
    m.put(walls & trim, "cream", tone=-0.2)
    m.put(walls & (Z >= prof - 1) & ((X < x0 + 1) | (X >= x1 - 1)), "cream", tone=-0.2)
    # Big doors on the +x gable with white X bracing, hayloft door above.
    end = Facade(m, "+x", x1)
    rect = end._rect(10, 22, 2, 15)
    m.carve(rect & end.layer(0))
    a = end.along
    leaf = np.where(a < 16, a - 10, a - 16)          # two door leaves, each braced with an X
    rise_ = (Z - 2) * 6 / 13
    brace = (np.abs(leaf - rise_) < 0.75) | (np.abs((6 - leaf) - rise_) < 0.75) \
        | (leaf < 0.9) | (leaf > 5.1) | (Z >= 14) | (Z < 3)
    m.put(rect & end.layer(1), "red_paint", tone=((a % 2) < 0.5) * -0.6 - 0.4)
    m.put(rect & end.layer(1) & brace, "cream")
    m.put(end._rect(9, 23, 15, 16) & (end.layer(0) | end.layer(-1)), "cream", tone=0.3)
    m.put(end._rect(15, 17, 18, 19.5) & (end.layer(-1) | end.layer(-2)), "metal")
    m.put(end._rect(15.2, 16.8, 16.5, 18) & end.layer(-1), "lamp")
    loft = end._rect(13.5, 18.5, 21, 26)
    m.carve(loft & end.layer(0))
    m.put(loft & end.layer(1), "straw", tone=0.3)
    m.put(end._rect(12.5, 19.5, 20, 27) & ~loft & end.layer(0), "cream")
    for e in (Facade(m, "-x", x0),):
        e.window(14, 18, 20, 24, frame="cream")
    for face, plane in (("+y", y1), ("-y", y0)):
        f = Facade(m, face, plane)
        for a0 in (9, 33):
            f.window(a0, a0 + 4, 7, 11, frame="cream")
        f.door(20, 25, 2, 12, material="red_paint", frame="cream")
    # Roof shingles following the gambrel.
    roof_top = np.where(across > knee_a, eave + (knee_z - eave) * (half + 2 - across) / (half - knee_a),
                        knee_z + 0.9 + (ridge + 1 - knee_z) * (knee_a - across) / knee_a)
    roof = (X >= x0 - 1.5) & (X < x1 + 1.5) & (across < half + 2) & (Z < roof_top) & (Z >= roof_top - 2.2)
    # Courses are spaced by height, so they stay evenly spaced on screen on the steep lower
    # slope and the shallow upper one, lit or in shade.
    course = np.floor(Z / 2.4)
    pitch = np.where(across > knee_a, (knee_z - eave) / (half - knee_a), (ridge - knee_z) / knee_a)
    zero = X * 0 + Z * 0
    roof_n = (zero, np.sign(Y - yc) * pitch + zero, zero + 1.0)
    m.put(roof, "slate", normal=roof_n, tone=-1.3 * ((Z % 2.4) < 0.7) + 0.5 * ((Z % 2.4) > 1.7)
          - 0.6 * (((X + course * 1.5) % 3) < 0.6) - 0.5 * (across < 0.8)
          + (value_noise(X, Y, Z, 2.5, 850) - 0.5) * 0.25)
    m.put(roof & ((X < x0 - 0.5) | (X >= x1 + 0.5)), "cream", tone=-0.3)
    m.halos.append(Halo(x1 + 1.5, 16, 17.5, 12, _rgb(GLOW[1]), 0.8))
    return m


def windmill(v, frame, frames):
    m = Model.empty(-12, 44, -12, 44, 0, 70)
    X, Y, Z = m.coords()
    cx = cy = 16.0
    r = 10.5 - Z * 0.07
    rho = np.hypot(X - cx, Y - cy)
    ang = np.arctan2(Y - cy, X - cx)
    tower = (rho <= r) & (Z < 44)
    m.put(tower & (Z < 8), "stone", normal=cylinder_normal(X, Y, Z, cx, cy),
          tone=-0.8 * ((Z % 2) < 0.5) - 0.6 * (np.cos(ang * 9 + np.floor(Z / 2) * 0.6) > 0.85))
    m.put(tower & (Z >= 8), "plaster", normal=cylinder_normal(X, Y, Z, cx, cy),
          tone=(value_noise(X, Y, Z, 2.5, 840) - 0.5) * 0.5)
    m.put(tower & (np.abs(Z - 8.5) < 0.7), "wood", normal=cylinder_normal(X, Y, Z, cx, cy))
    # Door, windows (two levels) and a balcony rail on the front.
    front = Facade(m, "+x", cx + 10.0)
    door = front._rect(13.5, 18.5, 0, 9)
    m.carve(door & (front.depth > -1.2))
    m.put(door & (front.depth > -2.2) & (front.depth <= -1.2), "wood", tone=((Y % 2) < 0.5) * -0.7)
    m.put(front._rect(12.5, 19.5, 0, 10) & ~door & tower & (front.depth > -1.5), "wood_light")
    for z0, d in ((19, 1.4), (31, 2.2)):
        win = front._rect(14.5, 17.5, z0, z0 + 4) & (front.depth > -d - 2.5) & (front.depth < -d + 1)
        m.carve(win & (front.depth > -d - 1))
        m.put(win & (front.depth <= -d - 1), "glass")
    side = Facade(m, "+y", cy + 9.0)
    win = side._rect(14.5, 17.5, 24, 28) & (side.depth > -3) & (side.depth < 1)
    m.carve(win & (side.depth > -2))
    m.put(win & (side.depth <= -2), "glass")
    # Cap roof.
    capz = 43.0
    cap = cone(X, Y, Z, cx, cy, 9.8, capz, capz + 14)
    m.put(cap, "roof", normal=(X - cx, Y - cy, np.full_like(Z, 7.0)),
          tone=-0.8 * ((np.floor(Z) % 2) == 0) - 0.4 * (np.cos(ang * 12) > 0.8))
    m.put((rho <= 10.2) & (Z >= capz - 0.5) & (Z < capz + 0.8), "wood", tone=0.2)
    # Hub and four sails turning in the y-z plane in front of the tower.
    hx, hz = cx + 11.5, capz + 1.0
    m.put(segment(X, Y, Z, (cx + 6, cy, hz), (hx + 1.0, cy, hz), 1.3), "wood")
    turn = frame / frames * (math.pi / 2)
    for k in range(4):
        a = turn + k * math.pi / 2
        dy, dz = math.cos(a), math.sin(a)
        tip = (hx, cy + dy * 25, hz + dz * 25)
        m.put(segment(X, Y, Z, (hx, cy, hz), tip, 0.9), "wood")
        # Sail cloth on the trailing side of each spar, with lattice lines.
        s = (Y - cy) * dy + (Z - hz) * dz           # distance along the spar
        w = -(Y - cy) * dz + (Z - hz) * dy          # distance across it
        cloth = (np.abs(X - hx) < 0.6) & (s > 5) & (s < 24.5) & (w > 0.8) & (w < 7.2)
        lattice = ((s % 4.0) < 0.8) | (w > 6.4)
        m.put(cloth & ~lattice, "cream", tone=0.4 - (w < 1.8) * 0.6)
        m.put(cloth & lattice, "wood_light", tone=-0.2)
    m.put(ellipsoid(X, Y, Z, hx + 0.8, cy, hz, 1.6, 1.8, 1.8), "wood", tone=0.3)
    return m
