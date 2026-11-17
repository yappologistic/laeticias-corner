"""Laeticia, the resident: one voxel figure posed per frame.

Like the critters she faces +x (`front`) and is turned three quarters for `back`; the anchor is
the ground contact point between her boots. Seated poses (`sit`, `read`) are anchored at the seat
contact under her hips, so the engine lifts her by the seat's `perch`; `lie` is anchored where
her hips rest in the hammock, `sleep` on the ground under her hips (the bedroll is part of it).

Every part is a shape evaluated in body space: (x forward, y to her left, z up from the soles,
or from the seat when seated). A pose may tip the whole body (lying down), so the voxel centres
are mapped into body space once and normals are turned back into the world. Proportions are
about four and a half heads, a little stooped; at 64x32 tiles she stands 43 px tall.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from voxel import Model, box, ellipsoid, hash01, segment

# ---- body measurements (design units) ----
WAIST = 9.6            # standing waist height
HEM = 2.0              # standing skirt hem
SEAT_WAIST = 3.3       # waist above the seat when seated
SHOULDER = (0.1, 2.1, 14.7)
HEAD = (0.55, 0.0, 18.2)
HEAD_R = (2.05, 1.95, 2.25)
FACE_TURN = 0.55       # radians towards her left (the camera) from straight ahead


@dataclass
class Arm:
    elbow: tuple
    hand: tuple


@dataclass
class Pose:
    """Everything that moves. Positions are in body space (design units)."""
    lift: float = 0.0                  # whole upper body up (breath, bob), in units
    lean: float = 0.3                  # stoop: forward shift at the shoulders
    nod: float = 0.0                   # head forward and down
    left: Arm = None                   # her left arm, on the camera side when facing +x
    right: Arm = None
    feet: tuple = ((0.2, 0.9), (0.2, -0.9))    # (x, y) of each boot on the ground
    toe_lift: tuple = (0.0, 0.0)       # heel raised, per foot
    hem: tuple = (0.0, 0.0)            # skirt hem drift (x, y)
    bag_swing: float = 0.0             # satchel swing along x
    sit: str = ""                      # "" standing, "chair" on a seat, "ground" knees up
    lying: bool = False                # a slimmer skirt and no satchel (hammock, bedroll)
    shoulders_up: float = 0.0          # shrug (stretch)
    face_turn: float = FACE_TURN
    props: list = field(default_factory=list)

    @property
    def seated(self) -> bool:
        return bool(self.sit)


def rest_arms(swing=0.0, lift=0.0):
    """Arms hanging, swinging `swing` units forward (left) and back (right)."""
    sx, sy, sz = SHOULDER
    return (Arm((sx + 0.2 + swing * 0.4, sy + 0.45, sz - 3.2 + lift), (sx + 0.5 + swing, sy + 0.35, sz - 6.1 + lift)),
            Arm((sx + 0.2 - swing * 0.4, -sy - 0.45, sz - 3.2 + lift), (sx + 0.5 - swing, -sy - 0.35, sz - 6.1 + lift)))


class Figure:
    """A model plus the map from world voxels into body space: world = R @ body + t."""

    def __init__(self, m: Model, rot=np.eye(3), shift=(0.0, 0.0, 0.0)):
        self.m = m
        self.R = np.asarray(rot, np.float32)
        self.t = np.asarray(shift, np.float32)
        X, Y, Z = m.coords()
        Xw, Yw, Zw = np.broadcast_arrays(X - self.t[0], Y - self.t[1], Z - self.t[2])
        R = self.R
        self.X = R[0, 0] * Xw + R[1, 0] * Yw + R[2, 0] * Zw
        self.Y = R[0, 1] * Xw + R[1, 1] * Yw + R[2, 1] * Zw
        self.Z = R[0, 2] * Xw + R[1, 2] * Yw + R[2, 2] * Zw

    def world_normal(self, n):
        if n is None:
            return None
        n = np.broadcast_arrays(*n)
        R = self.R
        return tuple(R[i, 0] * n[0] + R[i, 1] * n[1] + R[i, 2] * n[2] for i in range(3))

    def put(self, mask, material, tone=0.0, normal=None, only_empty=False):
        self.m.put(mask, material, tone=tone, normal=self.world_normal(normal), only_empty=only_empty)

    def blob(self, c, r, material, tone=0.0, only_empty=False):
        X, Y, Z = self.X, self.Y, self.Z
        mask = ellipsoid(X, Y, Z, *c, *r)
        n = ((X - c[0]) / r[0] ** 2, (Y - c[1]) / r[1] ** 2, (Z - c[2]) / r[2] ** 2)
        self.put(mask, material, tone, n, only_empty)
        return mask

    def limb(self, p, q, r, material, tone=0.0):
        """A capsule whose normals point away from its axis, so sleeves shade round."""
        X, Y, Z = self.X, self.Y, self.Z
        p, q = np.asarray(p, np.float32), np.asarray(q, np.float32)
        d = q - p
        t = np.clip(((X - p[0]) * d[0] + (Y - p[1]) * d[1] + (Z - p[2]) * d[2]) / float(d @ d), 0, 1)
        n = (X - p[0] - t * d[0], Y - p[1] - t * d[1], Z - p[2] - t * d[2])
        mask = n[0] ** 2 + n[1] ** 2 + n[2] ** 2 <= r * r
        self.put(mask, material, tone, n)
        return mask

    def points(self, pts, material, tone=0.0):
        pts = np.asarray(pts, np.float32).reshape(-1, 3)
        self.m.put_points(pts @ self.R.T + self.t, material, tone=tone)


# ---- body parts ----

def _boots(f: Figure, p: Pose):
    z = -4.6 if p.sit == "chair" else 0.0
    for (x, y), lift in zip(p.feet, p.toe_lift):
        zz = z + lift * 0.5
        f.blob((x + 0.45, y, zz + 0.62), (1.05, 0.62, 0.68), "leather", tone=-0.3)
        f.blob((x + 0.85, y, zz + 0.9), (0.6, 0.55, 0.45), "leather", tone=0.4)
        # A pale sole edge.
        sole = (np.abs(f.Z - (zz + 0.15)) < 0.25) & ellipsoid(f.X, f.Y, f.Z, x + 0.45, y, zz + 0.6, 1.1, 0.66, 0.9)
        f.put(sole, "linen", tone=-0.8)


KNEE = (2.6, 3.7)      # (x, z) of the knees when sitting on the ground


def _legs(f: Figure, p: Pose):
    """Stockinged shins: they show below the hem in a stride, or when seated."""
    if p.sit == "chair":
        for (x, y) in p.feet:
            f.limb((0.6, y * 0.95, 1.1), (x - 0.1, y, 1.5), 0.95, "skirt")
            f.limb((x - 0.1, y, 1.3), (x + 0.1, y, -4.0), 0.55, "leather", tone=-0.6)
    elif p.sit == "ground":
        for (x, y) in p.feet:
            f.limb((0.4, y * 0.95, 1.0), (KNEE[0], y * 0.9, KNEE[1]), 0.95, "skirt")
            f.limb((KNEE[0], y * 0.9, KNEE[1]), (x + 0.1, y, 0.9), 0.55, "leather", tone=-0.6)
    else:
        for (x, y), lift in zip(p.feet, p.toe_lift):
            f.limb((x * 0.4, y * 0.8, 4.5), (x + 0.05, y, 1.0 + lift * 0.5), 0.5, "leather", tone=-0.6)


def _skirt(f: Figure, p: Pose):
    X, Y, Z = f.X, f.Y, f.Z
    waist = (SEAT_WAIST if p.seated else WAIST) + p.lift * 0.5
    folds = np.cos(Y * 2.6 + 0.5)
    if p.sit == "chair":
        # Over the seat, across the lap and falling from the knees.
        hip = ellipsoid(X, Y, Z, 0.1, 0, 1.4, 2.35, 2.45, 2.2) & (Z >= 0)
        lap = (np.abs(Y) <= 2.25 - 0.25 * (Z < 0.8)) & (X >= -0.5) & (X <= 3.3 + 0.2 * (Z < 1.2)) & \
            (Z >= 0.15) & (Z < 2.35 - 0.35 * np.clip(X - 2.6, 0, 1))
        drop = (np.abs(Y) <= 2.15 + 0.15 * np.clip(1.8 - Z, 0, 4) / 4) & (X >= 2.5) & \
            (X <= 3.75 + 0.18 * np.clip(1.5 - Z, 0, 4)) & (Z >= -2.3 + 0.25 * np.sin(Y * 2.1)) & (Z < 2.0)
        body = hip | lap | drop
        front = drop & ~lap
        top = lap & ~drop
        apron = body & (np.abs(Y - 0.3) < 1.2) & (((X > 3.3) & drop & (Z > -1.2)) | (lap & (Z > 1.95)))
    elif p.sit == "ground":
        # Draped over the raised knees down to the ankles.
        kx, kz = KNEE
        prof = np.where(X < kx, 2.2 + (kz + 0.6 - 2.2) * np.clip(X / kx, 0, 1),
                        kz + 0.6 - (kz + 0.6 - 0.9) * np.clip((X - kx) / 1.8, 0, 1))
        hip = ellipsoid(X, Y, Z, 0.0, 0, 1.4, 2.4, 2.5, 2.3) & (Z >= 0)
        tent = (np.abs(Y) <= 2.25 + 0.2 * np.clip(kx - X, 0, 2) / 2) & (X >= -0.4) & (X <= kx + 1.9) & \
            (Z >= 0.2) & (Z < prof)
        body = hip | tent
        front = tent & (X > kx)
        top = tent & (X <= kx)
        apron = tent & (np.abs(Y - 0.2) < 1.5) & (Z > prof - 0.7)
    if p.seated:
        tone = -0.55 * (folds > 0.7) + 0.25 * (folds < -0.8)
        nrm = (np.where(front, 1.0, X * 0.15), Y * 0.25, np.where(top, 1.0, 0.25))
        f.put(body, "skirt", tone, nrm)
        f.put(apron, "linen", tone=0.6 - 0.5 * (np.abs(Y - 0.3) > 0.95), normal=nrm)
        return
    hem = HEM
    t = np.clip((Z - hem) / (waist - hem), 0, 1)
    flare = 0.55 if p.lying else 1.0        # lying down, the skirt falls flat along the legs
    rx = 1.85 + (3.0 - 1.85) * flare * (1 - t ** 0.75)
    ry = 2.1 + (3.2 - 2.1) * flare * (1 - t ** 0.75)
    drift = (1 - t) ** 1.6
    cx = 0.05 + p.hem[0] * drift
    cy = p.hem[1] * drift
    ang = np.arctan2(Y - cy, X - cx)
    rr = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2
    wavy = hem + 0.28 * np.sin(ang * 3 + 0.8) + 0.18 * np.sin(ang * 5 + p.hem[0] * 2)
    body = (rr <= 1) & (Z >= wavy) & (Z < waist)
    # Soft vertical folds, deeper towards the hem.
    folds = np.cos(ang * 6 + 0.6 + p.hem[0] * 0.8)
    tone = (-0.7 * (folds > 0.72) + 0.3 * (folds < -0.85)) * (1 - t * 0.8) - 0.5 * (Z < wavy + 0.5)
    nrm = ((X - cx) / rx ** 2, (Y - cy) / ry ** 2, np.full_like(Z, 0.12))
    f.put(body, "skirt", tone, nrm)
    # A linen apron over the front with a pocket on her left, and its waistband all round.
    apron = (rr <= 1.13) & (rr > 0.6) & (np.abs(ang - 0.25) < 0.5) & (Z >= 4.6) & (Z < waist)
    pocket = (ang > 0.25) & (ang < 0.7) & (Z > 5.2) & (Z < 7.0)
    pocket_edge = pocket & ((Z > 6.65) | (np.abs(ang - 0.25) < 0.08) | (np.abs(ang - 0.7) < 0.08))
    f.put(apron, "linen", tone=0.6 - 0.5 * (np.abs(ang - 0.25) > 0.4) - 0.7 * (apron & pocket_edge)
          - 0.35 * (np.cos(ang * 9) > 0.85), normal=nrm)
    band = (rr <= 1.12) & (Z >= waist - 0.4) & (Z < waist)
    f.put(band, "linen", tone=-0.7, normal=nrm)
    # The apron strings tied in a small bow at the back.
    f.blob((-1.95, 0.35, waist - 0.6), (0.4, 0.55, 0.4), "linen", tone=0.3)
    f.blob((-1.95, -0.35, waist - 0.6), (0.4, 0.55, 0.4), "linen", tone=0.3)
    f.limb((-1.9, 0.2, waist - 0.9), (-2.1, 0.45, waist - 2.3), 0.22, "linen")


def _torso(f: Figure, p: Pose):
    waist = (SEAT_WAIST if p.seated else WAIST) + p.lift * 0.5
    dz = waist - WAIST + p.lift * 0.5
    lean = p.lean
    cz = 12.5 + dz
    X, Y, Z = f.X, f.Y, f.Z
    cx = 0.1 + lean * 0.5 * np.clip((Z - waist) / 5, 0, 1)
    body = ellipsoid(X - cx + 0.1, Y, Z, 0.1, 0, cz, 1.75, 2.15, 3.3) & (Z >= waist - 0.9)
    # A cardigan, open at the front over a cream blouse; ribbed hem and cuffs are lighter.
    n = ((X - cx) / 1.75 ** 2, Y / 2.15 ** 2, (Z - cz) / 3.3 ** 2)
    rib = (Z < waist - 0.1)
    f.put(body, "cardigan", tone=-0.35 * rib + 0.35 * ((Z - waist) % 1.0 < 0.25) * rib, normal=n)
    blouse = body & (X > cx + 0.6) & (np.abs(Y) < 0.25 + 0.3 * np.clip(Z - (cz + 0.9), 0, 4)) & (Z > cz + 0.4)
    f.put(blouse, "linen", tone=0.5, normal=n)
    # Two buttons down the cardigan's edge and a collar at the neck.
    top = 0.1 + lean * 0.5          # the body's centre line at the shoulders
    for bz in (cz - 1.6, cz - 0.4):
        f.points([(top - 0.15 + 1.75, 0.45, bz)], "wood", tone=0.6)
    neck_z = cz + 2.9 + p.shoulders_up * 0.2
    f.limb((top + 0.15, 0, neck_z - 0.4), (top + 0.35, 0, neck_z + 1.0), 0.72, "skin", tone=-0.4)
    f.put(ellipsoid(X, Y, Z, top + 0.3, 0, neck_z - 0.25, 1.15, 1.25, 0.5) & ~body, "linen", tone=-0.2)


def _arm(f: Figure, p: Pose, arm: Arm, side: int, dz: float):
    sx, sy, sz = SHOULDER
    s = (sx + p.lean * 0.5, side * sy, sz + dz + p.shoulders_up)
    e, h = np.asarray(arm.elbow, np.float32), np.asarray(arm.hand, np.float32)
    e = e + (0, 0, dz)
    h = h + (0, 0, dz)
    wrist = e + (h - e) * 0.78
    f.blob(s, (0.95, 0.85, 0.95), "cardigan")
    f.limb(s, e, 0.74, "cardigan")
    f.limb(e, wrist, 0.66, "cardigan", tone=0.1)
    f.limb(wrist - (h - e) * 0.08, wrist, 0.7, "cardigan", tone=0.45)   # a ribbed cuff
    f.blob(tuple(h), (0.58, 0.55, 0.62), "skin")


def _satchel(f: Figure, p: Pose, dz: float):
    """A leather satchel on her left hip, its strap across her chest from the right shoulder."""
    waist = WAIST + dz
    bx = 0.2 + p.bag_swing
    strap = [(0.15 + p.lean * 0.4 + 0.1 * t, -1.5 + 3.9 * t, waist + 5.2 - 5.6 * t) for t in np.linspace(0, 1, 40)]
    pts = []
    for x, y, z in strap:
        # Pushed out to sit on the cardigan's surface.
        rx2 = 1.95 ** 2 * max(0.0, 1 - (y / 2.4) ** 2 - ((z - 12.5 - dz) / 3.6) ** 2)
        pts.append((x + math.sqrt(rx2) + 0.05, y, z))
    f.points(pts, "leather", tone=0.2)
    X, Y, Z = f.X, f.Y, f.Z
    cz = waist - 1.6
    bag = (np.abs(X - bx) <= 1.35) & (np.abs(Y - 2.75) <= 0.5) & (Z >= cz - 1.2) & (Z <= cz + 1.1)
    bag &= ((np.abs(X - bx) - 0.95).clip(0) ** 2 + (np.clip(cz - 0.7 - Z, 0, None)) ** 2) <= 0.35 ** 2
    f.put(bag, "leather", tone=0.3, normal=(X * 0, Y * 0 + 1, Z * 0 + 0.3))
    flap = bag & (Z > cz + 0.05) | ((np.abs(X - bx) <= 1.2) & (np.abs(Y - 3.3) < 0.25) & (Z > cz - 0.3) & (Z <= cz + 1.1))
    f.put(flap, "leather", tone=-0.4, normal=(X * 0, Y * 0 + 1, Z * 0 + 0.6))
    f.points([(bx, 3.5, cz - 0.15)], "yellow", tone=0.8)


def _head(f: Figure, p: Pose, dz: float):
    hx, hy, hz = HEAD
    hx += p.lean * 1.1 + p.nod * 0.6
    hz += dz + p.shoulders_up * 0.4 - p.nod * 0.35
    rx, ry, rz = HEAD_R
    X, Y, Z = f.X, f.Y, f.Z
    # The face turns a little towards the camera (her left), so it reads in the 3/4 view.
    c, s = math.cos(p.face_turn), math.sin(p.face_turn)
    U = (X - hx) * c + Y * s            # head-local: u out of the face, w to her left
    W = -(X - hx) * s + Y * c
    def at(u, w, z):
        return (hx + u * c - w * s, u * s + w * c, z)
    f.blob((hx, hy, hz), (rx, ry, rz), "skin")
    # Grey hair swept back into a bun: everything but the face, a soft hairline at the brow.
    shell = ellipsoid(X, Y, Z, hx - 0.08, 0, hz + 0.12, rx + 0.18, ry + 0.2, rz + 0.18)
    face = (U > -0.2 - 0.5 * np.clip(0.9 - (Z - hz), 0, 1.6)) & \
        (Z - hz < 1.25 + 0.2 * (np.abs(W) < 0.7) - 0.4 * (np.abs(W) > 1.4))
    hair = shell & ~face
    strands = ((W * 1.6 + U * 0.4 + np.sin(Z * 2.2) * 0.25) % 1.0) < 0.3
    n = ((X - hx) / rx ** 2, Y / ry ** 2, (Z - hz) / rz ** 2)
    f.put(hair, "hair", tone=-0.3 * strands, normal=n)
    bun = at(-1.55, 0.0, hz + 1.7)
    f.blob(bun, (1.2, 1.15, 1.1), "hair", tone=0.1)
    swirl = np.abs(np.sin(np.arctan2(Z - bun[2], W) * 2 + U * 2)) < 0.25
    f.put(ellipsoid(X, Y, Z, *bun, 1.25, 1.2, 1.15) & swirl, "hair", tone=-0.7)
    f.limb(at(-1.95, -1.2, bun[2] + 0.5), at(-1.25, 1.2, bun[2] + 0.9), 0.18, "wood", tone=0.5)
    # Face: eyes behind round glasses (a dark rim over the pair, a glint on each lens), a nose,
    # pink cheeks and a small mouth.
    fu = rx - 0.1
    ez = hz + 0.1
    for ew in (0.75, -0.75):
        f.points([at(fu, ew, ez)], "ink")
        rim = [at(fu + 0.12, ew + 0.55 * math.cos(a), ez + 0.45 * math.sin(a))
               for a in np.linspace(0.3, math.pi - 0.3, 7)]
        f.points(rim, "leather", tone=0.3)
        f.points([at(fu + 0.1, ew + 0.32, ez + 0.22)], "snow", tone=1.0)
    f.points([at(fu + 0.15, 0.0, ez + 0.3)], "leather", tone=-0.5)
    f.points([at(0.5, 1.95, ez + 0.2), at(1.1, 1.92, ez + 0.25)], "ink", tone=0.5)   # temple arm
    f.blob(at(fu + 0.35, 0.0, hz - 0.4), (0.42, 0.4, 0.42), "skin", tone=0.4)
    f.points([at(fu - 0.05, 1.2, hz - 0.65), at(fu - 0.05, -1.2, hz - 0.65)], "blossom", tone=1.0)
    f.points([at(fu + 0.05, 0.25, hz - 1.15), at(fu + 0.05, -0.25, hz - 1.15)], "skin", tone=-2.4)


def figure(f: Figure, p: Pose):
    dz = (SEAT_WAIST - WAIST if p.seated else 0.0) + p.lift * 0.5
    left, right = p.left, p.right
    if left is None or right is None:
        l0, r0 = rest_arms()
        left, right = left or l0, right or r0
    _legs(f, p)
    _boots(f, p)
    _skirt(f, p)
    _torso(f, p)
    if not (p.seated or p.lying):
        _satchel(f, p, dz)
    _arm(f, p, right, -1, dz)
    _arm(f, p, left, 1, dz)
    _head(f, p, dz)
    for prop in p.props:
        prop(f, dz)


# ---- props (drawn in standing body space; `dz` lowers them with a seated body) ----

def _book(open_at=(2.5, 0.0, 11.4), tilt=0.5, turning=False, cover="red_paint"):
    """Her sketchbook held open: two pages in a shallow V, the cover showing underneath."""
    def draw(f: Figure, dz):
        x, y, z = open_at
        z += dz
        X, Y, Z = f.X, f.Y, f.Z
        for side in (1, -1):
            # Each half rises from the spine towards the outer edge.
            w = (Y - y) * side
            surf = z + 0.25 + w * tilt
            page = (w >= 0) & (w < 1.7) & (np.abs(X - x) < 1.25) & (np.abs(Z - surf) < 0.3)
            f.put(page, "linen", tone=0.8 - 0.6 * (w < 0.35), normal=(X * 0 - 0.3, -side * tilt + X * 0, X * 0 + 1))
            f.put((w >= 0) & (w < 1.85) & (np.abs(X - x) < 1.35) & (np.abs(Z - surf + 0.45) < 0.25),
                  cover, tone=-0.2)
        if turning:  # a page standing up mid-turn
            f.put((np.abs(Y - y - 0.15) < 0.25) & (np.abs(X - x) < 1.15) & (Z > z + 0.3) & (Z < z + 2.0),
                  "linen", tone=0.6)
        f.points([(x + 0.3, y + 0.8, z + 0.6), (x - 0.3, y + 1.1, z + 0.75)], "leaf", tone=0.5)  # a sketch
    return draw


def _can(hand, tilt, drops=0):
    """A green watering can held by its handle at `hand`, its rose tipped down by `tilt`
    radians; `drops` > 0 shows a spray at that phase."""
    def draw(f: Figure, dz):
        hx, hy, hz = hand
        hz += dz
        c, s = math.cos(tilt), math.sin(tilt)

        def at(u, w, v):  # can-local: u forward, w to her left, v up; turned about the hand
            return (hx + u * c + v * s, hy + w, hz - u * s + v * c)
        body0, body1 = at(0.4, 0, -1.9), at(0.4, 0, -0.5)
        f.limb(body0, body1, 1.05, "green_paint", tone=0.2)
        f.limb(at(0.4, 0, -0.45), at(0.4, 0, -0.35), 0.75, "green_paint", tone=0.7)
        spout0, spout1 = at(1.2, 0, -1.6), at(3.2, 0, -0.1)
        f.limb(spout0, spout1, 0.26, "green_paint", tone=0.4)
        f.blob(at(3.45, 0, 0.0), (0.42, 0.42, 0.42), "metal", tone=1.0)
        f.points([at(u, 0, 0.35 - 0.25 * (u - 0.4) ** 2) for u in np.linspace(-0.6, 1.3, 9)], "green_paint", tone=-0.2)
        if drops:
            rose = np.array(at(3.6, 0, -0.1))
            rng = np.random.Generator(np.random.PCG64([71, drops]))
            pts = []
            for n in range(14):
                d = rng.uniform(0.2, 1.0)
                spread = rng.uniform(-0.7, 0.7)
                fall = (d + drops * 0.33) % 1.0
                pts.append(rose + (0.6 + 1.6 * fall, spread * (0.4 + fall), -0.3 - 6.5 * fall ** 1.4))
            f.points(pts, "water", tone=1.6)
    return draw


def _basket(at_=(0.7, 3.35, 8.7)):
    """A wicker basket on her left hip, a harvest peeping out."""
    def draw(f: Figure, dz):
        x, y, z = at_
        z += dz
        X, Y, Z = f.X, f.Y, f.Z
        tub = ellipsoid(X, Y, Z, x, y, z, 1.75, 1.05, 1.1) & (Z < z + 0.55) & \
            ~ellipsoid(X, Y, Z, x, y, z + 0.4, 1.35, 0.7, 0.9)
        weave = ((np.floor((Z - z) * 2.2) + np.floor((X - x) * 1.4)) % 2) == 0
        f.put(tub, "straw", tone=-0.4 * weave - 0.2, normal=((X - x) / 3, (Y - y), (Z - z) / 1.2))
        f.put(tub & (Z > z + 0.25), "straw", tone=0.5)
        for dx, dy, mat in ((-0.6, 0.1, "orange"), (0.2, -0.1, "poppy"), (0.8, 0.15, "grass")):
            f.blob((x + dx, y + dy, z + 0.75), (0.55, 0.5, 0.45), mat, tone=0.4)
        f.points([(x - 0.6, y + 0.1, z + 1.3), (x - 0.75, y + 0.15, z + 1.6)], "grass", tone=0.6)
        f.points([(x + 1.6 * math.cos(a), y, z + 0.5 + 1.5 * math.sin(a)) for a in np.linspace(0, math.pi, 13)],
                 "straw", tone=0.2)
    return draw


def _pebble(at_):
    def draw(f: Figure, dz):
        x, y, z = at_
        f.blob((x, y, z + dz), (0.4, 0.4, 0.35), "stone", tone=0.6)
    return draw


def _grain(phase):
    """Grain thrown from the hand in a widening arc, falling."""
    def draw(f: Figure, dz):
        rng = np.random.Generator(np.random.PCG64([72]))
        pts = []
        for n in range(16):
            a = rng.uniform(-0.6, 0.9)
            d = rng.uniform(0.6, 1.0) * (1.5 + 3.5 * phase)
            arc = 1.6 * math.sin(math.pi * min(1.0, phase * 1.2)) - 6.5 * phase ** 2
            pts.append((2.8 + d * math.cos(a), 3.6 + d * math.sin(a), 11.4 + dz + arc * rng.uniform(0.7, 1.3)))
        f.points(pts, "yellow", tone=0.8)
    return draw


def _pencil(hand):
    def draw(f: Figure, dz):
        x, y, z = hand
        f.points([(x + 0.25 * t, y - 0.1 * t, z + dz + 0.25 + 0.55 * t) for t in np.linspace(0, 1, 4)], "yellow", tone=0.5)
    return draw


# ---- animations: each returns the pose for one frame ----

def _arms(left, right):
    return Arm(*left), Arm(*right)


def _umbrella(hand):
    """A red and cream umbrella held up over her head."""
    def draw(f: Figure, dz):
        X, Y, Z = f.X, f.Y, f.Z
        top = (0.4, 0.4, 26.0 + dz)
        f.limb(hand, top, 0.18, "wood", tone=0.3)
        rel = np.stack(np.broadcast_arrays(X - top[0], Y - top[1], Z - top[2] + 1.6), -1)
        rho = np.hypot(rel[..., 0], rel[..., 1])
        canopy = (rho < 4.8) & (np.abs(rel[..., 2] - 1.6 * (1 - (rho / 4.8) ** 2)) < 0.35 + 0.15 * (rho < 1))
        panel = (np.floor((np.arctan2(rel[..., 1], rel[..., 0]) + math.pi) / (math.pi / 4)) % 2) == 0
        n = (rel[..., 0] * 0.4, rel[..., 1] * 0.4, np.ones_like(rho) * 2.0)
        f.put(canopy & panel, "red_paint", tone=0.5 - 0.6 * (rho > 4.2), normal=n)
        f.put(canopy & ~panel, "cream", tone=0.4 - 0.6 * (rho > 4.2), normal=n)
        f.blob((top[0], top[1], top[2] + 0.2), (0.3, 0.3, 0.4), "wood", tone=0.6)
    return draw


def _walk(frame, frames, carry=False, umbrella=False):
    ph = 2 * math.pi * frame / frames
    s = math.sin(ph)
    feet = ((0.3 + 1.4 * s, 0.85), (0.3 - 1.4 * s, -0.85))
    toe = (max(0.0, -s) * 0.7, max(0.0, s) * 0.7)
    lift = 1.0 * (1 - abs(s)) ** 2
    left, right = rest_arms(swing=-1.5 * s)
    props = []
    if carry:
        left = Arm((0.2, 3.15, 11.0), (1.0, 3.25, 9.5))
        props.append(_basket((0.7, 3.4, 8.8 + lift * 0.5)))
    if umbrella:
        hand = (1.3, 1.9, 14.6 + lift * 0.5)
        left = Arm((0.8, 3.1, 12.6), hand)
        props.append(_umbrella(hand))
    return Pose(lift=lift, left=left, right=right, feet=feet, toe_lift=toe,
                hem=(0.3 * s, 0.0), bag_swing=0.35 * math.sin(ph - 0.9), props=props)


def _idle(frame, frames):
    breath = frame % 2
    left, right = rest_arms(lift=0.25 * breath)
    return Pose(lift=0.5 * breath, left=left, right=right)


CHAIR_FEET = ((3.3, 0.95), (3.4, -0.95))


def _sit(frame, frames):
    breath = frame % 2
    left, right = _arms(((0.7, 2.5, 10.9 + 0.2 * breath), (2.1, 0.9, 9.3)),
                        ((0.7, -2.5, 10.9 + 0.2 * breath), (2.2, -0.6, 9.3)))
    return Pose(sit="chair", lift=0.5 * breath, left=left, right=right, feet=CHAIR_FEET)


def _read(frame, frames):
    left, right = _arms(((0.9, 2.4, 10.4), (2.3, 1.3, 11.1)), ((0.9, -2.4, 10.4), (2.3, -1.3, 11.1)))
    return Pose(sit="chair", nod=0.9, left=left, right=right, feet=CHAIR_FEET,
                props=[_book((2.6, 0.0, 11.3), turning=frame % 2 == 1)])


def _sketch(frame, frames):
    pencil = (3.0, -0.2 + 0.5 * (frame % 2), 11.1 + 0.15 * (frame % 2))
    left, right = _arms(((1.2, 2.5, 11.0), (2.8, 1.6, 10.6)), ((1.3, -2.2, 11.3), pencil))
    return Pose(sit="ground", nod=1.0, left=left, right=right, feet=((4.0, 0.9), (4.1, -0.9)),
                props=[_book((2.9, 0.4, 10.4), tilt=0.15), _pencil(pencil)])


def _warm(frame, frames):
    rub = frame % 2
    y = 0.75 - 0.2 * rub
    left, right = _arms(((1.2, 2.4, 12.0), (2.9, y, 11.4 + 0.2 * rub)),
                        ((1.2, -2.4, 12.0), (2.9, -y, 11.4 + 0.2 * rub)))
    return Pose(lean=0.6, nod=0.3, left=left, right=right)


def _stretch(frame, frames):
    poses = (
        dict(arms=(((0.3, 2.6, 11.5), (0.6, 2.5, 8.6)), ((0.3, -2.6, 11.5), (0.6, -2.5, 8.6))),
             up=0.0, lift=0.0, lean=0.3),
        dict(arms=(((0.2, 3.7, 15.2), (0.4, 5.0, 16.8)), ((0.2, -3.7, 15.2), (0.4, -5.0, 16.8))),
             up=0.2, lift=0.5, lean=0.1),
        dict(arms=(((0.0, 2.5, 18.2), (-0.1, 1.5, 21.0)), ((0.0, -2.5, 18.2), (-0.1, -1.5, 21.0))),
             up=0.5, lift=1.5, lean=-0.4),
        dict(arms=(((0.2, 3.5, 13.8), (0.5, 4.3, 12.5)), ((0.2, -3.5, 13.8), (0.5, -4.3, 12.5))),
             up=0.1, lift=0.5, lean=0.2),
    )[frame % 4]
    left, right = _arms(*poses["arms"])
    toes = 0.8 if frame % 4 == 2 else 0.0
    return Pose(lift=poses["lift"], lean=poses["lean"], shoulders_up=poses["up"], left=left,
                right=right, toe_lift=(toes, toes), nod=-0.4 if frame % 4 == 2 else 0.0)


def _wave(frame, frames):
    w = math.sin(2 * math.pi * frame / frames)
    left = Arm((0.4, 3.5, 16.0), (0.6, 3.8 + 1.0 * w, 19.8 - 0.3 * abs(w)))
    _l, right = rest_arms()
    return Pose(left=left, right=right, nod=-0.2)


def _toss(frame, frames):
    hand = ((-1.3, 2.6, 9.6), (1.0, 2.5, 9.0), (2.4, 2.3, 11.9))[frame % 3]
    elbow = ((-0.4, 2.7, 11.6), (0.5, 2.7, 11.4), (1.2, 2.5, 12.6))[frame % 3]
    _l, right = rest_arms()
    pebble = (hand[0] + 0.5, hand[1], hand[2]) if frame % 3 < 2 else (3.8, 2.2, 13.6)
    return Pose(left=Arm(elbow, hand), right=right, lean=0.5 if frame % 3 == 1 else 0.3,
                props=[_pebble(pebble)])


def _water(frame, frames):
    tilt = (0.1, 0.45, 0.7, 0.7)[frame % 4]
    hand = (1.9, 3.3, 10.4)
    left = Arm((0.6, 3.1, 11.8), hand)
    right = Arm((0.6, -2.5, 11.5), (1.4, -1.6, 10.2))
    return Pose(left=left, right=right, lean=0.5, nod=0.4,
                props=[_can(hand, tilt, drops=frame % 4 - 1 if frame % 4 >= 2 else 0)])


def _scatter(frame, frames):
    hand = ((1.3, 2.35, 6.9), (1.9, 3.1, 10.0), (2.6, 3.9, 11.3), (1.8, 3.4, 9.8))[frame % 4]
    elbow = ((0.6, 2.9, 10.4), (0.7, 3.2, 11.6), (1.1, 3.5, 12.6), (0.6, 3.2, 11.5))[frame % 4]
    _l, right = rest_arms()
    props = [_grain((0.0, 0.0, 0.35, 0.8)[frame % 4])] if frame % 4 >= 2 else []
    return Pose(left=Arm(elbow, hand), right=right, lean=0.5, props=props)


def _lie(frame, frames):
    breath = frame % 2
    left, right = _arms(((1.1, 2.5, 12.6), (2.6, 1.2, 13.6)), ((1.1, -2.5, 12.6), (2.6, -1.2, 13.6)))
    return Pose(lying=True, lift=0.4 * breath, nod=0.8, left=left, right=right,
                props=[_book((3.1, 0.0, 13.9), tilt=0.35, turning=False)])


def _sleep(frame, frames):
    left, right = rest_arms()
    return Pose(lying=True, lift=0.0, left=left, right=right)


ANIMS = {"move": _walk, "carry": lambda f, n: _walk(f, n, carry=True),
         "umbrella": lambda f, n: _walk(f, n, umbrella=True), "idle": _idle, "sit": _sit,
         "read": _read, "sketch": _sketch, "warm": _warm, "stretch": _stretch, "wave": _wave,
         "toss": _toss, "water": _water, "scatter": _scatter, "lie": _lie, "sleep": _sleep}

# Lying poses tip the body back about the hips: (angle from upright, hip height above anchor).
LYING = {"lie": (math.radians(72), 0.0), "sleep": (math.radians(90), 0.9)}
HIP = (-1.6, 0.0, 8.8)   # body point under the hips that rests on the hammock or bedroll


def _bedroll(m: Model, breath: int):
    """Her bedroll (a rolled pillow and a mat) and a patchwork blanket over her (world space)."""
    X, Y, Z = m.coords()
    mat = (X > -12.5) & (X < 10.5) & (np.abs(Y) < 2.9) & (Z < 0.8)
    m.put(mat, "straw", tone=-0.5 - 0.4 * ((X % 2.0) < 0.4) - 0.5 * (np.abs(Y) > 2.6))
    m.put((np.hypot(Z - 1.1, X + 11.0) < 1.15) & (np.abs(Y) < 2.4), "linen", tone=0.2,
          normal=(X + 11.0, Y * 0, Z - 1.1))
    top = 4.0 + 0.5 * breath * np.clip(1 - np.abs(X + 2.5) / 4, 0, 1) - 0.12 * np.clip(X - 2, 0, 9)
    blanket = (X > -6.5) & (X < 9.6) & (np.abs(Y) < 2.75 - 0.25 * (Z < 1.0)) & (Z >= 0.75) & \
        (Z < top + 0.6 * np.cos(Y * 0.55) - 0.6)
    patch = np.floor((X + 6.5) / 2.6).astype(np.int64) * 7 + np.floor((Y + 3) / 2.0).astype(np.int64)
    pick = hash01(patch, 73)
    for lo, hi, material, tone in ((0.0, 0.3, "poppy", 0.0), (0.3, 0.55, "cream", 0.2),
                                   (0.55, 0.75, "violet", 0.5), (0.75, 1.0, "grass", 0.0)):
        sel = blanket & (pick >= lo) & (pick < hi)
        seam = ((X + 6.5) % 2.6 < 0.3) | ((Y + 3) % 2.0 < 0.3)
        m.put(sel, material, tone=tone - 0.6 * seam, normal=(X * 0, Y * 0.4, Z * 0 + 1))
    m.put(blanket & (X < -5.8), "linen", tone=0.5)   # a turned-back edge


def model(anim: str, frame: int, frames: int, k: int) -> Model:
    pose = ANIMS[anim](frame, frames)
    if anim in LYING:
        a, hip_z = LYING[anim]
        # Body z (up) tips towards -x; body x (forward) towards +z.
        rot = np.array([[math.cos(a), 0, -math.sin(a)], [0, 1, 0], [math.sin(a), 0, math.cos(a)]])
        shift = -rot @ np.asarray(HIP) + (0, 0, hip_z)
        m = Model.empty(-15, 12, -5, 5, -3 if anim == "lie" else 0, 12, k=k)
        m.hover = anim == "lie"
        figure(Figure(m, rot, shift), pose)
        if anim == "sleep":
            _bedroll(m, frame % 2)
        return m
    m = Model.empty(-6, 10, -7, 9, -6 if pose.sit == "chair" else 0, 29, k=k)
    m.hover = pose.sit == "chair"
    figure(Figure(m), pose)
    return m

