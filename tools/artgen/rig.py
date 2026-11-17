"""The generic walker rig: one posed voxel body for every person of every set.

A person is a `Dress` (data: body type, garments, colours, headgear, hair, beard, footwear,
jewellery, carried things) posed by one shared pose library (`POSES`, the names and frame
counts of world-tech.md §1.9), so hundreds of citizens animate alike and other sets reuse the
rig with dresses of their own. Like Laeticia (`models/resident.py`) parts are shapes in body
space: x forward, y to the person's left, z up from the soles; the anchor is the ground point
between the feet. `front` sprites face +x; `back` sprites are the model turned to face -y.

Sizes (64x32 tiles): adults stand 38-40 px to the top of the head (headgear adds), children
27 px. Everything a viewer must read at 1x is deliberately a little large: heads, headgear,
beards, sleeves and carried objects.
"""

import math
from dataclasses import dataclass, replace

import numpy as np

from pack import Sprite
from render import render_base
from voxel import Model

# ---- body types: (height to the crown of the head, head radii, shoulder half-width,
# hip half-width, stoop) in design units; 2 px per unit at 64x32 tiles ----
BODIES = {
    "man": (19.0, (1.55, 1.45, 1.75), 2.15, 1.55, 0.15),
    "woman": (18.2, (1.5, 1.4, 1.7), 1.8, 1.6, 0.1),
    "elder": (18.4, (1.55, 1.45, 1.75), 2.0, 1.55, 0.7),
    "child": (13.4, (1.45, 1.35, 1.6), 1.45, 1.1, 0.0),
    "king": (20.5, (1.6, 1.5, 1.8), 2.3, 1.7, 0.0),
}

# Frames of every pose (world-tech.md §1.9); `shoot` is a set addition (archery drill).
POSES = {"move": 6, "idle": 2, "carry": 6, "carry_idle": 2, "run": 6, "sit": 2, "lie": 2,
         "sleep": 2, "talk": 4, "gesture": 4, "bow": 4, "kneel": 2, "work_low": 4,
         "work_high": 4, "haul": 4, "stir": 4, "pour": 4, "write": 4, "play": 4, "throw": 4,
         "serve": 4, "guard": 2, "march": 6, "shoot": 4, "ride": 6}

LONG = {"court_robe", "long_tunic", "cloak_long", "striped_robe", "royal_robe"}


@dataclass(frozen=True)
class Dress:
    """What a person wears and carries. Materials are palette material names."""
    body: str = "man"
    skin: str = "skin_olive"
    hair: str = "hair_black"
    hair_style: str = "bunch"        # bunch (at the nape), short, long, braid, knot, curly, tied
    beard: str = "full"              # none, short, full, curled, square (royal, long and squared)
    garment: str = "court_robe"      # court_robe, royal_robe, tunic, long_tunic, cloak_long,
                                     # striped_robe, chiton, kilt, wrap, sleeveless
    colour: str = "cinnabar"
    trim: str | None = None          # hem and cuff border
    pattern: str = "plain"           # plain, dots, squares, stripes, fringe
    pattern_mat: str | None = None
    belt: str | None = None
    trousers: str | None = None
    coat: str | None = None          # the kandys, worn over the shoulders, sleeves empty
    cape: str | None = None          # short cloak, mantle or animal skin over the shoulders
    shawl: str | None = None         # women's shawl over the shoulders
    veil: str | None = None          # veil falling down the back from the head
    head: str = "none"               # see _headgear
    head_mat: str = "felt"
    head_trim: str | None = None
    feet: str = "shoes"              # shoes, boots, bare, pointed
    feet_mat: str = "leather"
    jewels: tuple = ()               # torque, bracelets, earrings, collar, necklace, amulet, seal
    worn: tuple = ()                 # quiver, gorytos, akinakes, bow_back, sword_belt, seal_cord
    hand_l: str | None = None        # held in the left hand (the side the camera sees)
    hand_r: str | None = None
    hold: str | None = None          # front (both hands at the chest), shoulder, head, pole,
                                     # lead (left arm forward), bowl_up (offering)
    mount: str | None = None         # rider on 'horse' or 'pony'


@dataclass
class Arm:
    elbow: tuple
    hand: tuple


@dataclass
class Pose:
    feet: tuple = ((0.15, 0.75, 0.0), (0.15, -0.75, 0.0))   # (x, y, lift)
    bob: float = 0.0
    crouch: float = 0.0              # hips lowered by bending the knees
    lean: float = 0.0                # extra forward lean of the shoulders
    bend: float = 0.0                # bow from the hips (radians)
    nod: float = 0.0
    left: Arm | None = None
    right: Arm | None = None
    kneel: bool = False
    sit: bool = False
    lying: bool = False
    hem: float = 0.0                 # robe hem drift with the stride
    tool: float = 0.0                # tool swing phase in [0, 1]
    phase: float = 0.0               # animation phase in [0, 1)
    held_up: bool = False            # goods held up (carry)
    mouth: bool = False              # hand before the mouth (the audience bow)


# ---------- body frame ----------

class Frame:
    """Joint positions of one body type, scaled from the adult template."""

    def __init__(self, dress: Dress):
        H, head_r, sw, hw, stoop = BODIES[dress.body]
        self.H, self.head_r, self.sw, self.hw, self.stoop = H, head_r, sw, hw, stoop
        f = H / 19.0
        self.f = f
        self.hip = 9.6 * f
        self.knee = 5.1 * f
        self.waist = 10.6 * f
        self.chest = 12.9 * f
        self.shoulder = 14.5 * f
        self.neck = 15.3 * f
        self.head = H - head_r[2]
        self.upper = 3.0 * f
        self.fore = 2.8 * f
        self.limb = 0.7 * max(f, 0.8)


def rest_arms(fr: Frame, swing=0.0, lift=0.0, out=0.35):
    sh = fr.shoulder
    e = 0.45
    return (Arm((0.05 + swing * 0.35, fr.sw + out * 0.6, sh - fr.upper * 0.95 + lift),
                (0.25 + swing, fr.sw + out * 0.4, sh - fr.upper - fr.fore * 0.95 + lift + e)),
            Arm((0.05 - swing * 0.35, -fr.sw - out * 0.6, sh - fr.upper * 0.95 + lift),
                (0.25 - swing, -fr.sw - out * 0.4, sh - fr.upper - fr.fore * 0.95 + lift + e)))


# ---------- the pose library ----------

def _walk(fr: Frame, frame, frames, stride=1.25, swing=1.3, bob=0.6, run=False):
    ph = 2 * math.pi * frame / frames
    s = math.sin(ph)
    st = stride * fr.f * (1.5 if run else 1.0)
    lift_a, lift_b = max(0.0, math.cos(ph)) * 0.8, max(0.0, -math.cos(ph)) * 0.8
    if run:
        lift_a, lift_b = lift_a * 2.2, lift_b * 2.2
    feet = ((0.15 + st * s, 0.75 * fr.f, lift_a), (0.15 - st * s, -0.75 * fr.f, lift_b))
    left, right = rest_arms(fr, swing=-swing * s * fr.f * (1.4 if run else 1.0))
    if run:
        left = Arm((left.elbow[0], left.elbow[1], left.elbow[2] + 1.0), (left.hand[0] + 0.4, left.hand[1], left.hand[2] + 2.2))
        right = Arm((right.elbow[0], right.elbow[1], right.elbow[2] + 1.0), (right.hand[0] + 0.4, right.hand[1], right.hand[2] + 2.2))
    return Pose(feet=feet, bob=bob * fr.f * abs(math.cos(ph)) * (1.5 if run else 1.0), left=left,
                right=right, hem=0.5 * s, lean=0.5 if run else 0.0, phase=frame / frames)


def _hands_front(fr: Frame, z=None, reach=1.9, gap=0.9, lift=0.0):
    z = (fr.chest - 0.6 * fr.f if z is None else z) + lift
    return (Arm((0.6 * fr.f, fr.sw + 0.2, fr.shoulder - fr.upper * 0.85 + lift * 0.5), (reach * fr.f, gap, z)),
            Arm((0.6 * fr.f, -fr.sw - 0.2, fr.shoulder - fr.upper * 0.85 + lift * 0.5), (reach * fr.f, -gap, z)))


def pose(name: str, frame: int, frames: int, fr: Frame, dress: Dress) -> Pose:
    t = frame / frames
    wave = math.sin(2 * math.pi * t)
    f = fr.f
    sh = fr.shoulder
    if name in ("move", "march", "carry"):
        p = _walk(fr, frame, frames, stride=1.45 if name == "march" else 1.25,
                  swing=0.35 if name == "march" else 1.3)
        if name == "march":
            p.bob *= 0.5
        if name == "carry":
            p.left, p.right = _hands_front(fr, z=sh + 1.2 * f, reach=1.2, gap=1.0)
            p.held_up = True
        return _hold(p, fr, dress)
    if name == "run":
        return _walk(fr, frame, frames, run=True)
    if name == "ride":
        p = Pose(sit=True, bob=0.5 * abs(wave) * f, phase=t)
        p.left, p.right = _hands_front(fr, z=fr.waist + 1.2 * f, reach=2.2, gap=0.8)
        return _hold(p, fr, dress, riding=True)
    if name in ("idle", "carry_idle", "guard"):
        breath = frame % 2
        p = Pose(bob=0.25 * breath * f, phase=t)
        p.left, p.right = rest_arms(fr, lift=0.2 * breath, out=0.25)
        if name == "carry_idle":
            p.left, p.right = _hands_front(fr, z=sh + 1.2 * f, reach=1.2, gap=1.0)
            p.held_up = True
        if name == "guard":   # spear planted in front, both hands on it
            p.left = Arm((0.8 * f, fr.sw + 0.1, sh - fr.upper * 0.8), (2.0 * f, 0.7, fr.chest - 0.4 * f))
            p.right = Arm((0.8 * f, -fr.sw - 0.1, sh - fr.upper * 0.8), (2.0 * f, 0.5, fr.waist + 0.6 * f))
            p.bob = 0.12 * breath * f
            return p
        return _hold(p, fr, dress)
    if name == "talk":
        p = Pose(phase=t, nod=0.15 * (frame % 2))
        p.left, p.right = rest_arms(fr, out=0.3)
        a = (0.0, 0.6, 1.0, 0.4)[frame % 4]
        p.left = Arm((0.7 * f, fr.sw + 0.5, sh - fr.upper * 0.8), ((1.6 + a) * f, fr.sw + 0.8, fr.chest - 0.5 * f + a * f))
        return _hold(p, fr, dress, keep_left=True)
    if name == "gesture":
        p = Pose(phase=t)
        p.left, p.right = rest_arms(fr)
        up = (0.3, 0.8, 1.0, 0.7)[frame % 4]
        p.left = Arm((0.9 * f, fr.sw + 0.6, sh + 0.3 * up * f), ((2.6 + 0.4 * up) * f, fr.sw + 1.0, sh + (0.6 + 1.6 * up) * f))
        return _hold(p, fr, dress, keep_left=True)
    if name == "bow":
        depth = (0.0, 0.35, 0.55, 0.35)[frame % 4]
        p = Pose(bend=depth, mouth=True, phase=t)
        p.left, p.right = rest_arms(fr)
        # Right hand raised before the mouth, palm in, as in the audience relief.
        p.right = Arm((1.0 * f, -0.9, sh - 1.2 * f), (1.8 * f, -0.1, fr.head - 0.6 * f))
        return _hold(p, fr, dress, keep_right=True)
    if name == "kneel":
        p = Pose(kneel=True, phase=t, bob=0.2 * (frame % 2) * f)
        p.left, p.right = _hands_front(fr, z=fr.knee * 0.4, reach=2.6, gap=1.0)
        return p
    if name == "work_low":     # hoe, dig, plant: tool from overhead down to the ground
        sw = (0.0, 0.35, 1.0, 0.6)[frame % 4]
        p = Pose(phase=t, tool=sw, lean=0.6 + 0.6 * sw, crouch=0.6 * sw * f)
        hz = sh + 1.2 * f - sw * (sh - 2.0 * f)
        p.left = Arm((0.9 * f, fr.sw + 0.2, sh - 1.5 * f), ((1.4 + sw * 1.2) * f, 0.6, hz))
        p.right = Arm((0.7 * f, -fr.sw - 0.2, sh - 1.8 * f), ((1.0 + sw * 1.0) * f, -0.3, hz - 1.4 * f))
        return p
    if name == "work_high":    # chisel and mallet, prune: striking at chest height
        sw = (0.0, 0.5, 1.0, 0.4)[frame % 4]
        p = Pose(phase=t, tool=sw, lean=0.3)
        p.left = Arm((1.0 * f, fr.sw, sh - 1.4 * f), (2.6 * f, 0.6, fr.chest + 0.2 * f))
        p.right = Arm((0.6 * f, -fr.sw - 0.3, sh - 0.5 * f + (1 - sw) * 1.2 * f),
                      ((1.6 + 0.9 * sw) * f, -0.4, sh + (1.6 - 2.0 * sw) * f))
        return p
    if name == "haul":         # leaning back on a rope, hand over hand
        sw = (0.0, 0.5, 1.0, 0.5)[frame % 4]
        p = Pose(phase=t, lean=-0.9, feet=((1.2 * f, 0.75 * f, 0.0), (-0.9 * f, -0.75 * f, 0.0)), crouch=0.7 * f,
                 tool=sw)
        p.left = Arm((1.2 * f, fr.sw, sh - 1.4 * f), ((2.8 - 0.6 * sw) * f, 0.4, fr.chest - 0.4 * f))
        p.right = Arm((0.9 * f, -fr.sw, sh - 1.6 * f), ((2.0 + 0.6 * sw) * f, -0.2, fr.chest - 0.8 * f))
        return p
    if name == "stir":         # grinding, kneading, dyeing: hands circling low in front
        a = 2 * math.pi * t
        p = Pose(phase=t, lean=0.9, crouch=0.8 * f, tool=t)
        hx, hy = (2.3 + 0.5 * math.cos(a)) * f, 0.5 * math.sin(a)
        p.left = Arm((1.0 * f, fr.sw, sh - 1.8 * f), (hx, hy + 0.5, fr.waist - 0.8 * f))
        p.right = Arm((1.0 * f, -fr.sw, sh - 1.8 * f), (hx, hy - 0.5, fr.waist - 0.8 * f))
        return p
    if name == "pour":
        tilt = (0.0, 0.4, 0.8, 0.8)[frame % 4]
        p = Pose(phase=t, tool=tilt, lean=0.4)
        p.left = Arm((0.9 * f, fr.sw + 0.3, sh - 1.4 * f), (2.4 * f, fr.sw * 0.5, fr.chest - 0.2 * f))
        p.right = Arm((0.8 * f, -fr.sw, sh - 1.6 * f), (2.0 * f, -0.2, fr.waist + 0.4 * f))
        return p
    if name == "write":        # tablet in the left hand, stylus moving in the right
        dx = (0.0, 0.3, 0.6, 0.3)[frame % 4]
        p = Pose(phase=t, nod=0.6, kneel=dress.body != "child")
        z = fr.chest - 1.5 * f if not p.kneel else fr.chest - 4.8 * f
        p.left = Arm((0.8 * f, fr.sw, sh - 1.6 * f - (3.3 * f if p.kneel else 0)), (2.0 * f, 0.6, z))
        p.right = Arm((0.8 * f, -fr.sw, sh - 1.6 * f - (3.3 * f if p.kneel else 0)), ((2.0 + dx * 0.4) * f, -0.1 + dx * 0.4, z + 0.5))
        return p
    if name == "play":
        p = Pose(phase=t, sit=False, nod=0.2 * (frame % 2))
        pl = 0.3 * math.sin(2 * math.pi * t)
        p.left = Arm((0.6 * f, fr.sw + 0.3, sh - 1.5 * f), (1.9 * f, 0.9, fr.chest + pl * f))
        p.right = Arm((0.7 * f, -fr.sw, sh - 1.7 * f), (1.8 * f, -0.4, fr.waist + 1.0 * f - pl * f))
        return p
    if name == "throw":        # seated hand work: weaving, spinning
        a = (0.0, 0.5, 1.0, 0.5)[frame % 4]
        p = Pose(phase=t, kneel=True, tool=a)
        z = fr.chest - 3.6 * f
        p.left = Arm((0.8 * f, fr.sw, z + 1.4 * f), ((2.4 + 0.4 * a) * f, 1.1, z + 1.0 * a))
        p.right = Arm((0.8 * f, -fr.sw, z + 1.4 * f), ((2.4 + 0.4 * (1 - a)) * f, -1.0, z + 1.0 * (1 - a)))
        return p
    if name == "serve":
        a = (0.0, 0.5, 1.0, 0.5)[frame % 4]
        p = Pose(phase=t, lean=0.3 * a)
        p.left, p.right = _hands_front(fr, z=fr.chest - 0.4 * f, reach=1.6 + 1.0 * a, gap=0.8)
        p.held_up = True
        return p
    if name == "sit":
        breath = frame % 2
        p = Pose(sit=True, bob=0.2 * breath * f, phase=t)
        p.left, p.right = _hands_front(fr, z=fr.waist - 3.5 * f, reach=2.4, gap=1.1)
        return _hold(p, fr, dress)
    if name in ("lie", "sleep"):
        p = Pose(lying=True, phase=t, bob=0.15 * (frame % 2) * f)
        p.left, p.right = rest_arms(fr)
        return p
    if name == "shoot":        # draw and loose: bow held out on the left, string drawn back
        d = (0.0, 0.6, 1.0, 0.1)[frame % 4]
        p = Pose(phase=t, tool=d)
        p.left = Arm((1.2 * f, fr.sw + 0.4, sh), (3.1 * f, fr.sw * 0.6, sh + 0.2 * f))
        p.right = Arm(((0.6 - 1.2 * d) * f, -fr.sw - 0.4, sh + 0.1), ((2.0 - 2.2 * d) * f, -0.2, sh + 0.4 * f))
        return p
    raise KeyError(name)


def _hold(p: Pose, fr: Frame, dress: Dress, keep_left=False, keep_right=False, riding=False):
    """Arms for what the dress says the person holds while walking or standing."""
    f, sh = fr.f, fr.shoulder
    if dress.hold == "front" or dress.hold == "bowl_up":
        z = fr.chest - 0.4 * f if dress.hold == "front" else sh + 0.4 * f
        left, right = _hands_front(fr, z=z, reach=1.9, gap=0.8)
        if not keep_left:
            p.left = left
        if not keep_right:
            p.right = right
    elif dress.hold == "shoulder" and not keep_left:
        p.left = Arm((0.2 * f, fr.sw + 0.6, sh + 0.4 * f), (0.3 * f, fr.sw + 0.3, sh + 2.0 * f))
    elif dress.hold == "head" and not keep_left:
        p.left = Arm((0.1 * f, fr.sw + 0.7, sh + 1.2 * f), (0.2 * f, 0.9, fr.H + 0.6 * f))
    elif dress.hold == "pole":
        if not keep_left:
            p.left = Arm((0.6 * f, fr.sw + 0.4, sh - 1.0 * f), (1.0 * f, fr.sw + 0.2, sh + 0.6 * f))
    elif dress.hold == "lead" and not keep_left:
        p.left = Arm((0.9 * f, fr.sw + 0.4, sh - 1.4 * f), (2.4 * f, fr.sw + 0.4, fr.waist + 0.6 * f))
    if dress.hand_l in ("spear", "staff", "lance", "crook") and not keep_left and dress.hold is None:
        p.left = Arm((0.6 * f, fr.sw + 0.3, sh - 1.6 * f), (1.6 * f, fr.sw * 0.6, fr.waist + 1.6 * f))
    if dress.hand_r in ("lotus",) and not keep_right and dress.hold is None:
        p.right = Arm((0.7 * f, -fr.sw - 0.2, sh - 1.6 * f), (1.8 * f, -0.8, fr.chest - 0.6 * f))
    return p


# ---------- drawing ----------

class Body:
    """A model plus the map from world voxels into body space: world = R @ body + t."""

    def __init__(self, m: Model, rot=None, shift=(0.0, 0.0, 0.0)):
        self.m = m
        self.R = np.eye(3, dtype=np.float32) if rot is None else np.asarray(rot, np.float32)
        self.t = np.asarray(shift, np.float32)
        X, Y, Z = m.coords()
        Xw, Yw, Zw = np.broadcast_arrays(X - self.t[0], Y - self.t[1], Z - self.t[2])
        R = self.R
        self.X = R[0, 0] * Xw + R[1, 0] * Yw + R[2, 0] * Zw
        self.Y = R[0, 1] * Xw + R[1, 1] * Yw + R[2, 1] * Zw
        self.Z = R[0, 2] * Xw + R[1, 2] * Yw + R[2, 2] * Zw

    def wn(self, n):
        if n is None:
            return None
        n = np.broadcast_arrays(*n)
        R = self.R
        return tuple(R[i, 0] * n[0] + R[i, 1] * n[1] + R[i, 2] * n[2] for i in range(3))

    def put(self, mask, material, tone=0.0, normal=None, only_empty=False):
        self.m.put(mask, material, tone=tone, normal=self.wn(normal), only_empty=only_empty)

    def blob(self, c, r, material, tone=0.0, only_empty=False):
        X, Y, Z = self.X, self.Y, self.Z
        mask = ((X - c[0]) / r[0]) ** 2 + ((Y - c[1]) / r[1]) ** 2 + ((Z - c[2]) / r[2]) ** 2 <= 1
        self.put(mask, material, tone, ((X - c[0]) / r[0] ** 2, (Y - c[1]) / r[1] ** 2, (Z - c[2]) / r[2] ** 2),
                 only_empty)
        return mask

    def limb(self, p, q, r, material, tone=0.0, only_empty=False, r2=None):
        X, Y, Z = self.X, self.Y, self.Z
        p, q = np.asarray(p, np.float32), np.asarray(q, np.float32)
        d = q - p
        dd = float(d @ d) or 1e-6
        t = np.clip(((X - p[0]) * d[0] + (Y - p[1]) * d[1] + (Z - p[2]) * d[2]) / dd, 0, 1)
        n = (X - p[0] - t * d[0], Y - p[1] - t * d[1], Z - p[2] - t * d[2])
        rr = r if r2 is None else r + (r2 - r) * t
        mask = n[0] ** 2 + n[1] ** 2 + n[2] ** 2 <= rr * rr
        self.put(mask, material, tone, n, only_empty)
        return mask

    def points(self, pts, material, tone=0.0):
        pts = np.asarray(pts, np.float32).reshape(-1, 3)
        self.m.put_points(pts @ self.R.T + self.t, material, tone=tone)


def _ik(hip, foot, l1, l2, forward=1.0):
    """Knee position for a two-bone leg from hip to foot, the knee bending forward."""
    hip, foot = np.asarray(hip, np.float32), np.asarray(foot, np.float32)
    d = foot - hip
    L = float(np.linalg.norm(d))
    L = min(L, l1 + l2 - 1e-3)
    a = (l1 * l1 - l2 * l2 + L * L) / (2 * L)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    u = d / (np.linalg.norm(d) + 1e-6)
    perp = np.array([1.0, 0.0, 0.0], np.float32) * forward
    perp = perp - u * float(perp @ u)
    perp /= np.linalg.norm(perp) + 1e-6
    return hip + u * a + perp * h


def draw(b: Body, d: Dress, p: Pose, fr: Frame):
    f = fr.f
    lift = p.bob - p.crouch
    if p.kneel:
        lift = -(fr.knee - 0.6 * f)
    if p.sit:
        lift = -(fr.hip - 0.6 * f) if not d.mount else 0.0
    long_dress = d.garment in LONG
    hip_z = fr.hip + lift
    # Upper-body transform: lean and bow tip the torso forward about the hips.
    lean = fr.stoop + p.lean

    def up(pt):
        x, y, z = pt
        z = z + lift
        rel = max(z - hip_z, 0.0)
        x = x + lean * 0.35 * rel / (fr.shoulder - fr.hip) * f
        if p.bend:
            c, s = math.cos(p.bend), math.sin(p.bend)
            x, z = x * c + (z - hip_z) * s, hip_z + (z - hip_z) * c - x * s
        return (x, y, z)

    _legs(b, d, p, fr, lift)
    _garment(b, d, p, fr, lift, up)
    _arms(b, d, p, fr, up)
    _head(b, d, p, fr, up)
    _worn(b, d, p, fr, up)
    _held(b, d, p, fr, up)


def _feet_pts(d: Dress, p: Pose, fr: Frame):
    f = fr.f
    if p.kneel:
        return [(-2.2 * f, 0.75 * f, 0.0), (-2.2 * f, -0.75 * f, 0.0)]
    if p.sit:
        return [(2.6 * f, 0.8 * f, 0.0), (2.6 * f, -0.8 * f, 0.0)]
    return [(x, y, z) for x, y, z in p.feet]


def _legs(b: Body, d: Dress, p: Pose, fr: Frame, lift):
    f = fr.f
    hip_z = fr.hip + lift
    feet = _feet_pts(d, p, fr)
    leg_mat = d.trousers or d.skin
    show = d.garment not in LONG or p.sit or p.kneel
    for (x, y, lz), side in zip(feet, (1, -1)):
        hip = (0.0, side * fr.hw * 0.55, hip_z)
        ankle = (x, y, 0.8 * f + lz)
        if p.kneel:
            knee = (1.4 * f, side * fr.hw * 0.6, 0.6 * f)
            ankle = (x + 0.6 * f, y, 0.6 * f)
        elif p.sit:
            knee = (2.4 * f, side * fr.hw * 0.6, hip_z + 0.2) if d.mount else (2.3 * f, side * fr.hw * 0.6, 4.8 * f)
            ankle = (x if not d.mount else 2.0 * f, y if not d.mount else side * 2.4 * f, 0.8 * f + (hip_z - 4.5 * f if d.mount else 0))
        else:
            knee = tuple(_ik(hip, ankle, fr.hip - fr.knee, fr.knee - 0.8 * f))
        if show:
            b.limb(hip, knee, fr.limb * 1.15, leg_mat, tone=-0.1)
            b.limb(knee, ankle, fr.limb * 0.95, leg_mat, tone=-0.2)
        # Feet.
        fx, fy, fz = ankle
        fz -= 0.8 * f
        mat = d.feet_mat if d.feet != "bare" else d.skin
        tone = -0.3 if d.feet != "bare" else 0.0
        if d.feet == "boots" and show:
            b.limb((fx, fy, fz + 0.6), (fx - 0.05, fy, fz + 2.2 * f), fr.limb * 1.05, d.feet_mat, tone=-0.2)
        b.blob((fx + 0.45 * f, fy, fz + 0.45), (0.95 * f, 0.55 * f, 0.55), mat, tone=tone)
        if d.feet == "pointed":
            b.limb((fx + 0.9 * f, fy, fz + 0.4), (fx + 1.6 * f, fy, fz + 0.8), 0.3, mat)
        if d.feet == "shoes":   # the three straps of the court shoe
            b.points([(fx + 0.5 * f, fy + 0.5 * f * np.sign(fy or 1), fz + 0.7)], "gold" if d.trim == "gold" else mat, 0.5)


def _garment(b: Body, d: Dress, p: Pose, fr: Frame, lift, up):
    X, Y, Z = b.X, b.Y, b.Z
    f = fr.f
    hip_z = fr.hip + lift
    sh = fr.shoulder + lift
    waist = fr.waist + lift
    cx = lambda z: (fr.stoop + p.lean) * 0.35 * np.clip((z - hip_z) / (fr.shoulder - fr.hip), 0, None) * f
    # Torso (under every garment).
    tz = fr.chest + lift
    if p.bend:
        _bent_torso(b, d, p, fr, lift)
    else:
        ry, rx = fr.sw * 0.82, 1.25 * f
        torso = (((X - cx(Z)) / rx) ** 2 + (Y / ry) ** 2 + ((Z - tz) / (2.4 * f)) ** 2 <= 1) & (Z > waist - 1.5 * f)
        top_mat = d.skin if d.garment in ("wrap",) else d.colour
        b.put(torso, top_mat, tone=0.1, normal=((X - cx(Z)) / rx ** 2, Y / ry ** 2, (Z - tz) / (2.4 * f) ** 2))
        if d.garment == "sleeveless":
            pass
    # The lower garment.
    hem_z = {"court_robe": 0.25, "royal_robe": 0.15, "long_tunic": 0.35, "cloak_long": 0.4,
             "striped_robe": 0.3, "tunic": 4.6, "chiton": 5.0, "kilt": 4.8, "wrap": 4.2,
             "sleeveless": 5.0}.get(d.garment, 4.6) * f
    if p.kneel:
        hem_z = 0.5
    if p.sit and not d.mount:
        hem_z = max(hem_z - 4.5 * f, 0.3) if d.garment in LONG else 3.6 * f
    top_z = waist + (0.6 * f if d.garment in LONG else 0.2)
    if d.mount:
        top_z, hem_z = waist + 0.2, hip_z - 1.6 * f
    t = np.clip((Z - hem_z) / max(top_z - hem_z, 0.1), 0, 1)
    flare = {"court_robe": (3.7, 2.6), "royal_robe": (4.0, 2.8), "long_tunic": (2.4, 2.0),
             "cloak_long": (2.4, 2.1), "striped_robe": (2.4, 2.0)}.get(d.garment, (2.0, 1.75))
    wy = fr.hw * (1.05 + (flare[0] / 1.6 - 1.0) * (1 - t) ** 1.2) * (1.15 if p.kneel or p.sit else 1.0)
    wx = 1.35 * f * (1.0 + (flare[1] / 1.6 - 1.0) * (1 - t) ** 1.3) * (1.4 if p.kneel or p.sit else 1.0)
    drift = p.hem * f * (1 - t) ** 1.6
    ccx = 0.1 * f + drift + (1.2 * f if (p.kneel or p.sit) and not d.mount else 0)
    ang = np.arctan2(Y, X - ccx)
    rr = ((X - ccx) / wx) ** 2 + (Y / wy) ** 2
    skirt = (rr <= 1) & (Z >= hem_z) & (Z < top_z)
    if d.garment in ("court_robe", "royal_robe"):
        # The Persian robe is hitched up at the front, so its hem rises in a curve there, and
        # its pleats fall in fans at the sides.
        front_lift = 1.6 * f * np.clip(np.cos(ang), 0, 1) ** 2 * (0 if p.kneel or p.sit else 1)
        skirt &= Z >= hem_z + front_lift
    folds = np.cos(ang * 9 + 0.4)
    side = np.abs(np.sin(ang)) > 0.75
    tone = -0.6 * (folds > 0.6) * (1 - t * 0.6) + 0.25 * (folds < -0.7) - 0.25 * side * ((Z * 2.2) % 1.0 < 0.35)
    nrm = ((X - ccx) / wx ** 2, Y / wy ** 2, np.full_like(Z, 0.1))
    b.put(skirt, d.colour, tone, nrm)
    _pattern(b, d, skirt, X, Y, Z, ang)
    if d.garment == "striped_robe":
        b.put(skirt & ((Z * 1.6) % 1.0 < 0.35), d.pattern_mat or "linen", tone=0.2, normal=nrm)
    if d.trim:
        hem = skirt & (Z < hem_z + (0.8 if d.garment in LONG else 0.6) + (1.6 * f * np.clip(np.cos(ang), 0, 1) ** 2
                                                                          if d.garment in ("court_robe", "royal_robe") and not (p.kneel or p.sit) else 0))
        b.put(hem, d.trim, tone=0.3, normal=nrm)
    if d.pattern == "fringe":
        fr_ = (rr <= 1.08) & (Z >= hem_z - 0.6) & (Z < hem_z + 0.3) & ((np.floor(ang * 8) % 2) == 0)
        b.put(fr_, d.trim or d.colour, tone=-0.3)
    if d.belt:
        band = (rr <= 1.12) & (np.abs(Z - waist) < 0.45)
        band |= ((X - cx(Z)) / (1.4 * f)) ** 2 + (Y / (fr.sw * 0.86)) ** 2 <= 1
        band &= np.abs(Z - waist) < 0.45
        b.put(band, d.belt, tone=0.0)
    if d.garment == "wrap":
        b.put(skirt & (np.abs(ang) < 0.25), d.colour, tone=-0.6)
    # Over-garments.
    if d.coat:
        _kandys(b, d, p, fr, lift)
    if d.cape:
        cape = (((X - cx(Z) + 0.5 * f) / (1.7 * f)) ** 2 + (Y / (fr.sw * 1.15)) ** 2 <= 1) & \
            (Z > sh - 4.5 * f) & (Z < sh + 0.7 * f) & (X - cx(Z) < 0.9 * f)
        b.put(cape, d.cape, tone=-0.1 - 0.4 * ((np.arctan2(Y, X) * 3) % 1.0 < 0.2))
    if d.shawl:
        shawl = (((X - cx(Z)) / (1.6 * f)) ** 2 + (Y / (fr.sw * 1.08)) ** 2 <= 1) & \
            (Z > sh - 3.2 * f + 0.8 * np.clip(X, 0, None)) & (Z < sh + 0.6 * f)
        b.put(shawl, d.shawl, tone=0.1)


def _bent_torso(b, d, p, fr, lift):
    f = fr.f
    hip_z = fr.hip + lift
    c, s = math.cos(p.bend), math.sin(p.bend)
    top = (0.0 + (fr.shoulder - fr.hip) * s, 0.0, hip_z + (fr.shoulder - fr.hip) * c)
    b.limb((0.0, 0.0, hip_z + 0.6 * f), top, fr.sw * 0.8, d.colour, tone=0.1)


def _kandys(b, d, p, fr, lift):
    """The Median coat worn over the shoulders like a cape, its long sleeves hanging empty."""
    X, Y, Z = b.X, b.Y, b.Z
    f = fr.f
    sh = fr.shoulder + lift
    hem = 3.6 * f + lift if not p.sit else fr.hip + lift - 1.0
    back = (X < 0.4 * f) & (((X + 0.25 * f) / (1.65 * f)) ** 2 + (Y / (fr.sw * 1.08)) ** 2 <= 1 +
                            0.25 * np.clip((sh - Z) / (sh - hem), 0, 1)) & (Z > hem) & (Z < sh + 0.7 * f)
    hollow = (((X + 0.25 * f) / (1.35 * f)) ** 2 + (Y / (fr.sw * 0.85)) ** 2 <= 1) & (Z < sh - 0.4 * f)
    b.put(back & ~hollow, d.coat, tone=-0.15 - 0.35 * (np.abs(np.cos(Y * 2.4)) > 0.85))
    for side in (1, -1):   # the empty sleeves
        b.limb((-0.4 * f, side * (fr.sw + 0.35), sh - 0.2), (-0.9 * f, side * (fr.sw + 0.5), sh - 4.6 * f), 0.55 * f,
               d.coat, tone=-0.3)
    if d.trim:
        b.put(back & ~hollow & (Z < hem + 0.6), d.trim, tone=0.2)


def _pattern(b, d, mask, X, Y, Z, ang):
    if d.pattern == "dots":
        sel = mask & ((np.floor(Z * 1.25) + np.floor(ang * 5)) % 2 == 0) & ((Z * 1.25) % 1.0 < 0.45) & \
            ((ang * 5) % 1.0 < 0.4)
        b.put(sel, d.pattern_mat or "white_paint", tone=0.4)
    elif d.pattern == "squares":
        sel = mask & ((np.floor(Z * 0.9) + np.floor(ang * 4)) % 2 == 0) & ((Z * 0.9) % 1.0 < 0.55) & \
            ((ang * 4) % 1.0 < 0.5)
        b.put(sel, d.pattern_mat or "saffron", tone=0.2)
    elif d.pattern == "stripes":
        b.put(mask & ((ang * 6) % 1.0 < 0.3), d.pattern_mat or "linen", tone=0.2)


def _arms(b: Body, d: Dress, p: Pose, fr: Frame, up):
    f = fr.f
    left, right = p.left, p.right
    if left is None or right is None:
        l0, r0 = rest_arms(fr)
        left, right = left or l0, right or r0
    sleeve = d.skin if d.garment in ("wrap", "sleeveless") else d.colour
    wide = d.garment in ("court_robe", "royal_robe")
    for arm, side in ((right, -1), (left, 1)):
        s = up((0.0, side * fr.sw, fr.shoulder))
        e = up(arm.elbow)
        h = up(arm.hand)
        b.blob(s, (0.85 * f, 0.8 * f, 0.85 * f), sleeve)
        b.limb(s, e, fr.limb * 1.05, sleeve)
        wrist = tuple(np.asarray(e) + (np.asarray(h) - np.asarray(e)) * 0.8)
        b.limb(e, wrist, fr.limb * 0.92, sleeve if d.garment not in ("chiton", "kilt") else d.skin, tone=0.1)
        if wide:
            # The court robe's wide sleeve hangs in a deep fold below the forearm.
            mid = tuple(np.asarray(e) * 0.5 + np.asarray(wrist) * 0.5)
            drop = (mid[0] - 0.3 * f, mid[1] + side * 0.35, mid[2] - 3.0 * f)
            b.limb(s, drop, 0.95 * f, d.colour, tone=-0.1)
            b.limb(drop, wrist, 0.85 * f, d.colour, tone=0.15)
            if d.trim:
                b.limb((drop[0], drop[1], drop[2] - 0.2), (drop[0] + 0.3, drop[1], drop[2] - 0.6), 0.55 * f, d.trim)
        if d.trim and d.garment not in ("wrap", "sleeveless", "chiton", "kilt"):
            b.limb(tuple(np.asarray(wrist) - (np.asarray(h) - np.asarray(e)) * 0.08), wrist, fr.limb * 0.98, d.trim,
                   tone=0.2)
        b.blob(h, (0.5 * f, 0.48 * f, 0.55 * f), d.skin)
        if "bracelets" in d.jewels:
            b.points([wrist], "gold", 0.6)


def _head(b: Body, d: Dress, p: Pose, fr: Frame, up):
    X, Y, Z = b.X, b.Y, b.Z
    f = fr.f
    rx, ry, rz = fr.head_r
    hx, hy, hz = up((0.15 * f + p.nod * 0.5, 0.0, fr.head))
    hz -= p.nod * 0.3
    # Neck.
    nb = up((0.05, 0.0, fr.shoulder - 0.2))
    b.limb(nb, (hx - 0.2, 0.0, hz - rz * 0.6), 0.65 * f, d.skin, tone=-0.3)
    b.blob((hx, hy, hz), (rx, ry, rz), d.skin)
    turn = 0.75                                    # the face turns toward the camera
    c, s = math.cos(turn), math.sin(turn)
    U = (X - hx) * c + (Y - hy) * s
    W = -(X - hx) * s + (Y - hy) * c

    def at(u, w, z):
        return (hx + u * c - w * s, hy + u * s + w * c, z)

    # Hair: a cap over the back and top; styles add volume.
    shell = ((X - hx + 0.1) / (rx + 0.2)) ** 2 + ((Y - hy) / (ry + 0.2)) ** 2 + ((Z - hz - 0.12) / (rz + 0.18)) ** 2 <= 1
    face = (U > -0.25 - 0.5 * np.clip(0.8 - (Z - hz), 0, 1.6)) & (Z - hz < 1.0 * f)
    hair = shell & ~face
    nrm = ((X - hx) / rx ** 2, (Y - hy) / ry ** 2, (Z - hz) / rz ** 2)
    if d.hair_style != "bald":
        b.put(hair, d.hair, tone=-0.3 * (((W * 2.2 + Z * 1.4) % 1.0) < 0.3), normal=nrm)
    if d.hair_style == "bunch":       # the Persian bunch of curls at the nape
        b.blob(at(-rx * 0.95, 0.0, hz - rz * 0.55), (0.95 * f, 1.25 * f, 0.9 * f), d.hair, tone=-0.1)
    elif d.hair_style in ("long", "braid"):
        b.limb(at(-rx * 0.8, 0.0, hz - 0.2), at(-rx * 1.05, 0.0, hz - rz - 2.5 * f), 0.7 * f, d.hair, tone=-0.2)
    elif d.hair_style == "knot":
        b.blob(at(-rx * 0.6, 0.0, hz + rz * 0.85), (0.7, 0.7, 0.6), d.hair)
    elif d.hair_style == "curly":
        b.blob((hx - 0.1, hy, hz + 0.4), (rx + 0.35, ry + 0.35, rz + 0.1), d.hair, tone=-0.2, only_empty=True)
    elif d.hair_style == "tied":
        b.blob(at(-rx * 1.0, 0.0, hz - 0.2), (0.7, 0.7, 0.75), d.hair)
    # Face: an eye and a brow on the camera side, a nose.
    fu = rx - 0.05
    b.points([at(fu, 0.55 * f, hz + 0.15 * f)], "hair_black")
    b.points([at(fu, -0.55 * f, hz + 0.15 * f)], "hair_black", tone=0.5)
    b.blob(at(fu + 0.25, 0.0, hz - 0.25 * f), (0.32, 0.3, 0.35), d.skin, tone=0.3)
    if d.beard != "none":
        long_ = {"short": 0.9, "full": 1.35, "curled": 1.6, "square": 2.4}[d.beard] * f
        beard = (U > -0.4) & (Z < hz - 0.25 * f) & (Z > hz - rz - long_ + 0.4) & \
            (((X - hx - 0.2) / (rx + 0.25)) ** 2 + ((Y - hy) / (ry + 0.1)) ** 2 <= 1.0 + 0.3 * (Z < hz - rz))
        if d.beard == "square":
            beard |= (U > 0.0) & (U < rx + 0.3) & (np.abs(W) < 0.95 * f) & (Z < hz - rz + 0.3) & (Z > hz - rz - long_ + 0.4)
        curls = ((Z * 2.6) % 1.0) < 0.35
        b.put(beard, d.hair, tone=-0.35 * curls + 0.15)
        if d.beard in ("curled", "square"):
            b.put(beard & curls & ((W * 3) % 1.0 < 0.4), "gold" if d.body == "king" else d.hair, tone=-0.6 if d.body != "king" else -1.6)
    else:
        b.points([at(fu + 0.05, 0.0, hz - 0.85 * f)], d.skin, tone=-1.2)
    if "earrings" in d.jewels:
        b.points([at(0.0, ry + 0.05, hz - 0.5 * f)], "gold", 0.6)
    _headgear(b, d, p, fr, (hx, hy, hz), at)
    if "torque" in d.jewels or "collar" in d.jewels or "necklace" in d.jewels:
        cxz = up((0.25, 0.0, fr.shoulder + 0.3))
        mat = "gold" if "necklace" not in d.jewels else "eblue"
        ring = (np.abs(np.hypot((X - cxz[0]) / 1.0, (Y - cxz[1]) / 1.1) - 1.0 * f) < 0.32) & (np.abs(Z - cxz[2]) < 0.35)
        b.put(ring, mat, tone=0.4)


def _headgear(b, d: Dress, p: Pose, fr: Frame, c, at):
    X, Y, Z = b.X, b.Y, b.Z
    hx, hy, hz = c
    rx, ry, rz = fr.head_r
    f = fr.f
    g, mat = d.head, d.head_mat
    rad = np.hypot((X - hx + 0.05) / (rx + 0.15), (Y - hy) / (ry + 0.15))
    top = hz + rz
    if g == "none":
        return
    if g in ("fluted_cap", "crown"):
        # Tall enough to read as the fluted felt tiara, not as hair; a dark band at its foot
        # parts it from the forehead.
        h = (3.4 if g == "fluted_cap" else 3.8) * f
        z0 = hz + rz * 0.35
        flare = 1.0 + 0.16 * np.clip((Z - z0) / h, 0, 1)
        cap = (rad <= flare) & (Z >= z0) & (Z < top + h - rz * 0.65)
        a = np.arctan2(Y - hy, X - hx)
        tone = 0.45 * (np.cos(a * 10) > 0.4) - 0.35
        b.put(cap, mat, tone, ((X - hx), (Y - hy), np.zeros_like(Z)))
        b.put(cap & (Z < z0 + 0.45), mat, tone=-1.4)
        if g == "crown":   # crenellated rim and a jewelled band
            crest = cap & (Z > top + h - rz * 0.65 - 0.9) & (np.cos(a * 6) < 0.0)
            b.m.mat[np.broadcast_to(crest, b.m.mat.shape)] = 0
            b.put(cap & (np.abs(Z - (z0 + 0.8)) < 0.35), "lapis", tone=0.5)
        if d.head_trim:
            b.put(cap & (Z < z0 + 0.5), d.head_trim, tone=0.3)
    elif g == "round_cap":
        cap = (((X - hx + 0.15) / (rx + 0.3)) ** 2 + ((Y - hy) / (ry + 0.3)) ** 2 + ((Z - hz - 0.5) / (rz + 0.25)) ** 2 <= 1) & \
            (Z > hz + 0.15 * f)
        flap = (X < hx - 0.2) & (((X - hx) / (rx + 0.35)) ** 2 + ((Y - hy) / (ry + 0.35)) ** 2 <= 1) & \
            (Z > hz - rz * 1.0) & (Z <= hz + 0.3)
        b.put(cap | flap, mat, tone=-0.1, normal=((X - hx) / rx ** 2, (Y - hy) / ry ** 2, (Z - hz) / rz ** 2))
        if d.head_trim:
            b.put(cap & (Z < hz + 0.6 * f), d.head_trim, tone=0.2)
    elif g in ("hood", "hood_mouth", "pointed_hood"):
        shell = ((X - hx + 0.1) / (rx + 0.35)) ** 2 + ((Y - hy) / (ry + 0.35)) ** 2 + ((Z - hz) / (rz + 0.3)) ** 2 <= 1
        U = (X - hx)
        open_face = (U > rx * 0.15) & (Z > hz - rz * (0.15 if g == "hood_mouth" else 0.8)) & (Z < hz + rz * 0.55)
        hood = shell & ~open_face
        # Flaps down the neck and cheeks.
        flaps = (np.hypot((X - hx + 0.3) / (rx + 0.2), (Y - hy) / (ry + 0.25)) <= 1) & (Z > hz - rz - 1.6 * f) & \
            (Z < hz - 0.2) & ~((X - hx) > rx * 0.3)
        b.put(hood | flaps, mat, tone=-0.1, normal=((X - hx) / rx ** 2, (Y - hy) / ry ** 2, (Z - hz) / rz ** 2))
        if g == "hood_mouth":
            mouth = (U > rx * 0.1) & (U < rx + 0.45) & (np.abs(Y - hy) < ry * 0.9) & (Z > hz - rz - 0.4) & (Z < hz - 0.2 * f)
            b.put(mouth, mat, tone=0.2)
        if g == "pointed_hood":
            h = 4.2 * f
            tf = np.clip((Z - (hz + rz * 0.4)) / h, 0, 1)
            spike = (np.hypot((X - hx + 0.2 + 0.6 * tf) / (rx * (1 - tf) + 0.1), (Y - hy) / (ry * (1 - tf) + 0.1)) <= 1) & \
                (Z > hz + rz * 0.4) & (Z < hz + rz * 0.4 + h)
            b.put(spike, mat, tone=0.1)
        else:   # a soft rounded crown, folded at the top
            b.put(shell & (Z > hz + rz * 0.8) & (X < hx + 0.3), mat, tone=0.3)
    elif g in ("fillet", "headband", "wreath"):
        band = (rad >= 0.9) & (rad <= 1.12) & (np.abs(Z - (hz + rz * 0.35)) < 0.45 * (1.3 if g == "wreath" else 1))
        b.put(band, mat, tone=0.2 - 0.5 * ((np.arctan2(Y - hy, X - hx) * 4) % 1.0 < 0.3) * (g != "headband"))
        if d.head_trim:   # a tassel or a ribbon end at the back
            b.limb((hx - rx, hy, hz + rz * 0.3), (hx - rx - 0.4, hy, hz - rz * 0.6), 0.35, d.head_trim)
    elif g in ("conical_tassel", "tall_cone", "felt_cap", "tight_cap"):
        h = {"conical_tassel": 2.8, "tall_cone": 4.4, "felt_cap": 1.4, "tight_cap": 0.7}[g] * f
        z0 = hz + rz * 0.3
        tf = np.clip((Z - z0) / h, 0, 1)
        r_top = 0.65 if g == "felt_cap" else (0.55 if g == "conical_tassel" else 0.15)
        if g == "tight_cap":
            r_top = 0.9
        cap = (rad <= 1.0 - (1 - r_top) * tf) & (Z >= z0) & (Z < z0 + h)
        if g == "tight_cap":
            cap = ((((X - hx + 0.1) / (rx + 0.22)) ** 2 + ((Y - hy) / (ry + 0.22)) ** 2 + ((Z - hz) / (rz + 0.2)) ** 2) <= 1) & \
                (Z > hz + 0.1)
        b.put(cap, mat, tone=0.2 * (np.cos(np.arctan2(Y - hy, X - hx) * 6) > 0.5) - 0.1)
        if g == "conical_tassel":
            b.limb((hx - rx * 0.6, hy, z0 + h * 0.8), (hx - rx - 0.6, hy, hz - rz * 0.6), 0.32, d.head_trim or mat)
    elif g in ("headcloth", "veil_crown"):
        cloth = (((X - hx + 0.15) / (rx + 0.3)) ** 2 + ((Y - hy) / (ry + 0.3)) ** 2 + ((Z - hz - 0.25) / (rz + 0.25)) ** 2 <= 1) & \
            ~((X - hx > rx * 0.25) & (Z < hz + rz * 0.5) & (Z > hz - rz))
        b.put(cloth & (Z > hz - rz * 0.4), mat, tone=0.1)
        if g == "veil_crown":
            z0 = hz + rz * 0.55
            crown = (rad <= 1.05) & (rad > 0.6) & (Z >= z0) & (Z < z0 + 1.3 * f)
            a = np.arctan2(Y - hy, X - hx)
            b.put(crown & ~((Z > z0 + 0.8 * f) & (np.cos(a * 8) < 0)), "gold", tone=0.3)
    if d.veil:   # down the back from the head to below the shoulders, never over the face
        veil = (X < hx - rx * 0.2) & (np.abs(Y - hy) < ry + 0.6 + 0.25 * np.clip(hz - Z, 0, 9)) & \
            (Z > fr.shoulder - 6.5 * f) & (Z < hz + rz * 0.9) & \
            (X > hx - rx - 0.9 - 0.06 * np.clip(hz - Z, 0, 9))
        b.put(veil, d.veil, tone=-0.2 * ((Y * 2.2) % 1.0 < 0.3))


def _worn(b: Body, d: Dress, p: Pose, fr: Frame, up):
    f = fr.f
    X, Y, Z = b.X, b.Y, b.Z
    for w in d.worn:
        if w in ("quiver", "bow_back"):
            # A quiver of arrows on the back with the bow across it.
            s = up((-1.5 * f, -0.4, fr.shoulder + 0.8))
            e = up((-1.5 * f, 0.6, fr.hip - 1.0 * f))
            b.limb(s, e, 0.55 * f, "leather", tone=0.1)
            b.points([(s[0], s[1] - 0.3, s[2] + 0.5), (s[0], s[1], s[2] + 0.7)], "gold", 0.4)
            if w == "bow_back":
                b.limb(up((-1.3 * f, 1.2, fr.shoulder + 1.0)), up((-1.4 * f, -1.2, fr.waist - 1.0)), 0.3, "cedar", 0.3)
        elif w == "gorytos":    # the bow case on the left hip
            s = up((0.0, fr.hw + 0.9, fr.waist))
            e = (s[0] - 1.4 * f, s[1] + 0.2, fr.knee + 0.4)
            b.limb(s, e, 0.75 * f, "leather", tone=0.2, r2=0.5 * f)
            b.points([s], "gold", 0.5)
        elif w == "akinakes":   # short straight sword on the right thigh
            s = up((0.3, -fr.hw - 0.5, fr.waist - 0.4))
            b.limb(s, (s[0] + 0.5 * f, s[1] - 0.2, fr.knee + 0.8 * f), 0.35, "leather")
            b.points([s], "gold", 0.6)
        elif w == "seal_cord":
            b.points([up((1.2 * f, fr.sw + 0.5, fr.waist - 0.6))], "eblue", 0.4)
        elif w == "sword_belt":
            s = up((0.5, fr.hw + 0.6, fr.waist - 0.2))
            b.limb(s, (s[0] - 1.0, s[1], fr.knee + 0.6), 0.32, "metal")


PROP_LEN = {"spear": 2.0, "lance": 1.75, "staff": 1.05, "crook": 1.0}


def _held(b: Body, d: Dress, p: Pose, fr: Frame, up):
    f = fr.f
    left, right = p.left, p.right
    if left is None or right is None:
        l0, r0 = rest_arms(fr)
        left, right = left or l0, right or r0
    hl, hr = up(left.hand), up(right.hand)
    for prop, hand, side in ((d.hand_l, hl, 1), (d.hand_r, hr, -1)):
        if prop:
            draw_prop(b, prop, hand, side, d, p, fr, hl, hr)
    if d.hold == "pole":
        _prop_pole(b, d, p, fr, up)


def draw_prop(b: Body, prop, hand, side, d: Dress, p: Pose, fr: Frame, hl, hr):
    f = fr.f
    x, y, z = hand
    if prop in ("spear", "lance", "staff", "crook"):
        L = PROP_LEN[prop] * fr.H
        lo = max(0.15, z - (0.45 if prop != "staff" else 0.9) * fr.H * 0.5)
        b.limb((x, y, lo), (x + 0.05, y, lo + L), 0.3, "cedar", tone=0.2)
        if prop == "staff":
            b.blob((x + 0.05, y, lo + L + 0.3), (0.45, 0.45, 0.45), "gold", 0.4)
        if prop in ("spear", "lance"):
            b.limb((x + 0.05, y, lo + L), (x + 0.05, y, lo + L + 1.6 * f), 0.42, "metal", tone=0.6, r2=0.05)
        if prop == "spear":   # the silver or gold pomegranate butt of the guard's spear
            b.blob((x, y, lo + 0.2), (0.6, 0.6, 0.65), "gold", tone=0.4)
        if prop == "crook":
            b.limb((x + 0.05, y, lo + L), (x + 0.8 * f, y, lo + L + 0.6), 0.3, "cedar")
    elif prop == "lotus":
        b.limb((x, y, z), (x + 0.3, y, z + 1.6 * f), 0.18, "malachite")
        b.blob((x + 0.35, y, z + 2.0 * f), (0.5, 0.5, 0.55), "white_paint", tone=0.4)
    elif prop in ("tablet", "tablet_wax"):
        b.blob((x + 0.4, y, z + 0.3), (0.75 * f, 0.55 * f, 0.25), "mudbrick", tone=0.3)
    elif prop == "stylus":
        b.limb((x, y, z), (x + 0.6, y, z + 0.9), 0.16, "cedar")
    elif prop == "scroll":
        b.limb((x + 0.3, y - 0.6, z + 0.2), (x + 0.3, y + 0.6, z + 0.2), 0.42, "linen", tone=0.3)
    elif prop == "basket_tablets":
        b.blob((x + 0.7, y, z - 0.6), (1.1 * f, 0.9 * f, 0.8 * f), "straw", tone=0.1)
        b.points([(x + 0.7, y, z + 0.2)], "mudbrick", 0.4)
    elif prop in ("bowl", "phial", "cup"):
        cx = (hl[0] + hr[0]) / 2 if d.hold in ("front", "bowl_up") else x
        cy = (hl[1] + hr[1]) / 2 if d.hold in ("front", "bowl_up") else y
        b.blob((cx + 0.6, cy, z + 0.6), (1.5 * f, 1.5 * f, 0.6 * f), "gold" if prop != "bowl" else "bronze", tone=0.4)
    elif prop in ("pitcher", "jar", "wineskin", "amphora"):
        cx, cy = ((hl[0] + hr[0]) / 2, (hl[1] + hr[1]) / 2) if d.hold == "front" else (x, y)
        cz = z
        if d.hold == "shoulder":
            cx, cy, cz = x - 0.3, y + 0.2, z + 0.9 * f
        if d.hold == "head":
            cx, cy, cz = fr.head_r[0] * 0.2, 0.0, fr.H + 0.9 * f
        mat = {"pitcher": "gold", "jar": "mudbrick", "wineskin": "leather", "amphora": "mudbrick"}[prop]
        b.blob((cx + 0.4, cy, cz + 0.6), (1.3 * f, 1.2 * f, 1.6 * f), mat, tone=0.2)
        b.limb((cx + 0.4, cy, cz + 1.9 * f), (cx + 0.4, cy, cz + 2.6 * f), 0.5 * f, mat, tone=0.4)
    elif prop in ("cloth", "garment"):
        cx, cy = (hl[0] + hr[0]) / 2, (hl[1] + hr[1]) / 2
        b.blob((cx + 0.5, cy, z + 0.4), (1.5 * f, 1.9 * f, 0.9 * f), d.pattern_mat or "purple", tone=0.2)
        b.blob((cx + 0.5, cy, z + 1.2 * f), (1.4 * f, 1.8 * f, 0.25), "saffron", tone=0.3)
    elif prop == "armlets":
        cx, cy = (hl[0] + hr[0]) / 2, (hl[1] + hr[1]) / 2
        for dy in (-0.6, 0.6):
            ring = (np.abs(np.hypot(b.X - cx - 0.4, b.Z - z - 0.9) - 0.75 * f) < 0.28) & (np.abs(b.Y - cy - dy) < 0.3)
            b.put(ring, "gold", tone=0.5)
    elif prop in ("shield_round", "shield_eight"):
        sx, sy, sz = x + 0.5, y + side * 0.8, z
        rr = 1.7 * f
        if prop == "shield_round":
            mask = (np.hypot(b.X - sx, b.Z - sz) < rr) & (np.abs(b.Y - sy) < 0.35)
        else:
            mask = ((np.hypot(b.X - sx, b.Z - sz - 0.9 * f) < rr * 0.7) | (np.hypot(b.X - sx, b.Z - sz + 0.9 * f) < rr * 0.7)) & \
                (np.abs(b.Y - sy) < 0.35)
        b.put(mask, "cedar" if prop == "shield_eight" else "bronze", tone=0.2)
    elif prop == "bow":
        b.limb((x, y, z - 2.6 * f), (x + 0.4, y, z), 0.25, "cedar", 0.3)
        b.limb((x + 0.4, y, z), (x, y, z + 2.6 * f), 0.25, "cedar", 0.3)
        sx_ = hr[0] if d.hand_r is None else x - 0.6
        b.limb((x - 0.1, y, z - 2.5 * f), (sx_, hr[1], hr[2]), 0.1, "linen", 0.6)
        b.limb((sx_, hr[1], hr[2]), (x - 0.1, y, z + 2.5 * f), 0.1, "linen", 0.6)
    elif prop in ("mallet", "hoe", "spade", "sickle", "adze", "chisel", "hammer", "pruning_knife", "ladle"):
        _tool(b, prop, hl, hr, p, fr)
    elif prop == "barsom":     # the magus's bundle of twigs
        b.limb((x, y, z - 0.4), (x + 1.0 * f, y, z + 2.4 * f), 0.4, "wood", 0.3)
        b.points([(x + 1.0 * f, y + 0.2, z + 2.6 * f), (x + 1.1 * f, y - 0.2, z + 2.5 * f)], "malachite", 0.3)
    elif prop == "parasol":
        top = (x + 0.6, y, fr.H + 7.5 * f)
        b.limb((x, y, z - 1.0), top, 0.28, "gold", 0.2)
        X, Y, Z = b.X, b.Y, b.Z
        rel = np.hypot(X - top[0] - 2.0 * f, Y - top[1])
        canopy = (rel < 4.4 * f) & (np.abs(Z - (top[2] - 0.8 * (rel / (4.4 * f)) ** 2 * 2.0 * f)) < 0.45)
        b.put(canopy, "purple", tone=0.3 - 0.5 * ((np.arctan2(Y - top[1], X - top[0] - 2.0 * f) * 4) % 1.0 < 0.15))
        b.put(canopy & (rel > 3.9 * f), "gold", tone=0.4)
        b.blob((top[0] + 2.0 * f, top[1], top[2] + 0.3), (0.45, 0.45, 0.6), "gold", 0.4)
    elif prop == "flywhisk":
        b.limb((x, y, z), (x + 0.4, y, z + 2.5 * f), 0.2, "gold")
        b.limb((x + 0.4, y, z + 2.5 * f), (x + 0.9, y, z + 3.8 * f), 0.45, "linen", r2=0.15)
    elif prop == "harp":       # an angular harp held upright against the chest
        b.limb((x + 0.3, y - 0.5, z - 1.4 * f), (x + 0.3, y - 0.5, z + 2.8 * f), 0.42, "cedar", 0.2)
        b.limb((x + 0.3, y - 0.5, z - 1.4 * f), (x + 2.6 * f, y - 0.5, z - 1.2 * f), 0.36, "cedar", 0.3)
        for i in range(4):
            u = 0.5 + i * 0.5
            b.limb((x + 0.3 + u * f, y - 0.5, z - 1.2 * f), (x + 0.3, y - 0.5, z + (2.4 - i * 0.5) * f), 0.1, "linen", 0.6)
    elif prop == "pipes":
        b.limb((x, y, z), (x + 2.4 * f, y + 0.3, z + 1.6 * f), 0.2, "cedar", 0.3)
        b.limb((x, y - 0.4, z), (x + 2.4 * f, y - 0.6, z + 1.4 * f), 0.2, "cedar", 0.3)
    elif prop == "drum":
        ring = (np.hypot(b.X - x - 0.6, b.Z - z - 0.5) < 1.6 * f) & (np.abs(b.Y - y - 0.6) < 0.4)
        b.put(ring, "linen", tone=0.3)
    elif prop == "tusk":
        b.limb((hl[0] + 0.2, hl[1], hl[2]), (hr[0] + 1.5 * f, hr[1] - 1.5, hr[2] + 2.0 * f), 0.45 * f, "white_paint", 0.3, r2=0.2)
    elif prop in ("axe", "axes"):
        b.limb((x, y, z - 0.5), (x + 0.3, y, z + 3.0 * f), 0.22, "cedar")
        b.blob((x + 0.7, y, z + 2.7 * f), (0.6, 0.25, 0.5), "metal", 0.5)
    elif prop == "sword":
        b.limb((x, y, z), (x + 0.3, y, z + 2.5 * f), 0.25, "metal", 0.4)
    elif prop == "rings":
        b.put((np.abs(np.hypot(b.X - x - 0.5, b.Z - z - 0.5) - 0.8 * f) < 0.3) & (np.abs(b.Y - y) < 0.35), "gold", 0.5)
    elif prop == "ingot":      # an ox-hide-shaped copper ingot
        b.blob((x + 0.5, y, z + 0.6), (1.2 * f, 0.4, 0.8 * f), "orange", 0.2)
    elif prop in ("kid_goat", "cub"):      # a kid for the king's table; a lion cub (Elamites)
        mat = "wool" if prop == "kid_goat" else "saffron"
        cx, cy = ((hl[0] + hr[0]) / 2, (hl[1] + hr[1]) / 2) if d.hold == "front" else (x, y)
        b.blob((cx + 0.6, cy, z + 0.5), (1.4 * f, 0.7 * f, 0.8 * f), mat, 0.2)
        b.blob((cx + 1.8 * f, cy, z + 1.1 * f), (0.6 * f, 0.5 * f, 0.55 * f), mat, 0.3)
    elif prop == "dish":
        b.blob((x + 0.5, (hl[1] + hr[1]) / 2, z + 0.4), (1.3 * f, 1.3 * f, 0.3), "bronze", 0.4)
        b.blob((x + 0.5, (hl[1] + hr[1]) / 2, z + 0.9), (0.8 * f, 0.8 * f, 0.5), "orange", 0.3)
    elif prop == "spindle":
        b.limb((x, y, z - 1.8 * f), (x, y, z + 0.4), 0.15, "wood")
        b.blob((x, y, z - 1.6 * f), (0.4, 0.4, 0.25), "wool", 0.3)
    elif prop == "rope":
        b.limb((hl[0], hl[1], hl[2]), (hl[0] + 4.0 * f, 0.0, hl[2] - 1.0), 0.25, "straw", 0.3)
    elif prop == "torch":
        b.limb((x, y, z - 0.5), (x + 0.3, y, z + 2.6 * f), 0.3, "wood")
        b.blob((x + 0.35, y, z + 3.2 * f), (0.6, 0.6, 0.9), "fire", 0.4)
    elif prop == "seal":
        b.points([(x + 0.3, y, z + 0.2)], "eblue", 0.5)
    elif prop == "sack":
        b.blob((x - 0.6, y + 0.5, z + 1.0 * f), (1.2 * f, 1.0 * f, 1.4 * f), "straw", 0.1)
    elif prop == "brick_mould":
        b.blob((x + 0.8, (hl[1] + hr[1]) / 2, z - 0.5), (1.2 * f, 1.0 * f, 0.4 * f), "wood_light", 0.2)
    elif prop == "lotus_bud":
        b.blob((x + 0.2, y, z + 0.8), (0.35, 0.35, 0.5), "malachite", 0.3)
    else:
        raise KeyError(f"rig: no prop {prop!r}")


def _tool(b: Body, prop, hl, hr, p: Pose, fr: Frame):
    """Two-handed or striking tools along the line of the hands."""
    f = fr.f
    a, c = np.asarray(hr, np.float32), np.asarray(hl, np.float32)
    if prop in ("hoe", "spade"):
        d = c - a
        d = d / (np.linalg.norm(d) + 1e-6)
        end = a + d * 5.8 * f
        b.limb(tuple(a - d * 0.8), tuple(end), 0.25, "cedar")
        head = end + (np.array([0.7, 0.0, -0.9], np.float32) if prop == "hoe" else d * 0.9)
        b.limb(tuple(end), tuple(head), 0.45 if prop == "hoe" else 0.6, "metal", 0.4)
    elif prop in ("mallet", "hammer"):
        b.limb(tuple(a), tuple(a + (0.4, 0.0, 1.6 * f)), 0.22, "cedar")
        b.blob(tuple(a + (0.4, 0.0, 1.9 * f)), (0.75, 0.6, 0.6), "wood_light" if prop == "mallet" else "metal", 0.3)
    elif prop == "chisel":
        b.limb(tuple(c), tuple(c + (0.9, 0.0, -0.4)), 0.2, "metal", 0.6)
    elif prop in ("sickle", "pruning_knife"):
        b.limb(tuple(a), tuple(a + (0.8, 0.0, 0.8)), 0.2, "metal", 0.5)
    elif prop == "adze":
        b.limb(tuple(a), tuple(a + (0.3, 0.0, 2.0 * f)), 0.22, "cedar")
        b.limb(tuple(a + (0.3, 0.0, 2.0 * f)), tuple(a + (1.2, 0.0, 1.8 * f)), 0.3, "metal", 0.5)
    elif prop == "ladle":
        b.limb(tuple(a), tuple(a + (1.8 * f, 0.0, -0.8)), 0.18, "bronze")
        b.blob(tuple(a + (2.0 * f, 0.0, -1.0)), (0.5, 0.5, 0.35), "bronze", 0.4)


def _prop_pole(b: Body, d: Dress, p: Pose, fr: Frame, up):
    """A shoulder pole with a basket hanging from each end (the Indians' gold dust)."""
    f = fr.f
    s = up((-0.2, 0.0, fr.shoulder + 0.6))
    a, c = (s[0] + 3.2 * f, s[1], s[2]), (s[0] - 3.2 * f, s[1], s[2])
    b.limb(a, c, 0.28, "cedar", 0.2)
    for e in (a, c):
        b.limb(e, (e[0], e[1], e[2] - 3.0 * f), 0.1, "straw")
        b.blob((e[0], e[1], e[2] - 3.6 * f), (1.0 * f, 1.0 * f, 0.8 * f), "straw", 0.1)
        b.blob((e[0], e[1], e[2] - 3.0 * f), (0.7 * f, 0.7 * f, 0.3), "gold", 0.5)


# ---------- mounts ----------

HORSE = 2.3     # a horse about 44 px at the withers under a 40 px rider (world.md toy scale)

def horse(b: Body, phase: float, coat="cedar", mane="hair_black", trappings="cinnabar", f=1.0, pony=False):
    """A horse under a rider (rider's body space: the saddle at the origin's hips). The tail
    is tied in a knot and the forelock bunched in a topknot, as on the reliefs."""
    s = 0.78 if pony else 1.0
    g = s * f * HORSE
    H = 8.6 * g                     # withers above the ground (the rider's soles are lifted)
    gait = math.sin(2 * math.pi * phase)
    b.blob((0.3 * g, 0.0, H - 0.6 * g), (4.2 * g, 1.5 * g, 1.7 * g), coat, 0.1)
    for lx, side, ph in ((3.0, 1, 0.0), (3.0, -1, 0.5), (-2.6, 1, 0.5), (-2.6, -1, 0.0)):
        sw = math.sin(2 * math.pi * (phase + ph)) * 1.0 * g
        top = (lx * g, side * 0.8 * g, H - 1.6 * g)
        foot = (lx * g + sw, side * 0.8 * g, 0.4 + max(0.0, -math.cos(2 * math.pi * (phase + ph))) * 0.8)
        b.limb(top, foot, 0.45 * g, coat, -0.2)
        b.blob((foot[0] + 0.15, foot[1], 0.35), (0.45 * g, 0.4 * g, 0.4), "ink", 0.3)
    neck0 = (3.4 * g, 0.0, H + 0.2 * g)
    head = (5.6 * g, 0.0, H + 2.6 * g + 0.2 * gait)
    b.limb(neck0, head, 1.0 * g, coat, 0.1, r2=0.7 * g)
    b.limb(head, (6.9 * g, 0.0, H + 1.6 * g + 0.2 * gait), 0.6 * g, coat, 0.2)
    b.limb((3.0 * g, 0.0, H + 1.0 * g), (5.3 * g, 0.0, H + 3.3 * g), 0.45 * g, mane, -0.1)
    b.blob((5.6 * g, 0.0, H + 3.6 * g), (0.5 * g, 0.5 * g, 0.55 * g), mane, 0.0)        # topknot
    b.limb((-4.0 * g, 0.0, H - 0.2 * g), (-4.8 * g, 0.0, H - 2.4 * g), 0.55 * g, mane, -0.1)   # tied tail
    b.blob((-4.9 * g, 0.0, H - 2.6 * g), (0.6 * g, 0.6 * g, 0.6 * g), mane, 0.0)
    b.blob((0.1 * g, 0.0, H + 0.9 * g), (1.7 * g, 1.7 * g, 0.5 * g), trappings, 0.2)   # saddle cloth
    return H + 0.9 * g


# ---------- entry points ----------

FACING = ("front", "back")


def person_model(dress: Dress, anim: str, frame: int, k: int) -> Model:
    frames = POSES[anim]
    fr = Frame(dress)
    p = pose(anim, frame, frames, fr, dress)
    tall = fr.H * (2.2 if dress.hand_l in ("spear", "lance") or dress.hand_r in ("spear", "lance") else 1.0)
    tall = max(tall, fr.H + (9.0 if dress.hand_l == "parasol" or dress.hand_r == "parasol" else 6.5))
    if dress.mount:
        tall += 24.0
    reach = 26 if dress.mount else 9
    m = Model.empty(-reach, reach + 2, -8, 8, 0, int(math.ceil(tall)) + 2, k=k)
    if dress.mount:
        b0 = Body(m)
        seat = horse(b0, p.phase, pony=dress.mount == "pony", f=1.0)
        b = Body(m, shift=(0.0, 0.0, seat - (fr.hip - 0.6 * fr.f) - 0.1))
        draw(b, dress, p, fr)
        return m
    if p.lying:
        a = math.radians(90)
        rot = np.array([[math.cos(a), 0, -math.sin(a)], [0, 1, 0], [math.sin(a), 0, math.cos(a)]])
        m2 = Model.empty(-14, 12, -8, 8, 0, 8, k=k)
        b = Body(m2, rot, shift=-rot @ np.asarray((0.0, 0.0, fr.hip)) + (0, 0, 1.2))
        draw(b, dress, p, fr)
        return m2
    draw(Body(m), dress, p, fr)
    return m


def person_sprite(dress: Dress, anim: str, facing: str, frame: int, k: int) -> Sprite:
    m = person_model(dress, anim, frame, k)
    if facing == "back":
        m = m.rotated(3, 0, 0)
    rgba, _glow, ox, oy = render_base(m)
    return Sprite(rgba, ox, oy)


def carry_point(dress: Dress, anim: str, frame: int, facing: str, k: int) -> list[int]:
    """Pixel offset from the anchor to the bottom centre of carried goods (world-tech §1.10):
    above the hands held at shoulder height."""
    fr = Frame(dress)
    p = pose(anim, frame, POSES[anim], fr, dress)
    hl, hr = p.left.hand, p.right.hand
    x, y, z = (hl[0] + hr[0]) / 2 + 0.4, (hl[1] + hr[1]) / 2, max(hl[2], hr[2]) + 0.6 + p.bob
    if facing == "back":     # turned to face -y: (x, y) -> (y, -x)
        x, y = y, -x
    return [int(round((x - y) * k)), int(round(((x + y) / 2 - z) * k))]


def variant(dress: Dress, **changes) -> Dress:
    return replace(dress, **changes)
