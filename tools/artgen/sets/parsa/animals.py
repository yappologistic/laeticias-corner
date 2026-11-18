"""Pārsa's animals and wheeled movers (persepolis.md §3.6, §6.6): the beasts the delegations
bring and the city works with. One quadruped builder with proportions and markings as data;
like the critters they face +x, anchored at the ground under the body's middle. Generic farm
animals (sheep, goat, dog, ox, donkey, mule) belong to the shared world set (world-tech §1.1).
"""

import math
from dataclasses import dataclass

import numpy as np

from arch import ellipsoid, fill, rod, slab
from pack import Sprite
from render import render_base
from rig import BEAST_DUTY, CART_FRAMES, CRITTER_FRAMES, Body, Dress, Frame, draw, foot_cycle, pose, horse as rig_horse
from voxel import Model


@dataclass(frozen=True)
class Beast:
    length: float = 9.0          # body length (design units)
    height: float = 7.0          # withers
    girth: float = 1.6
    neck: float = 3.0            # neck length
    neck_up: float = 0.8         # how upright the neck is (0 level, 1 vertical)
    head: float = 1.0
    leg: float = 0.45
    coat: str = "cedar"
    belly: str | None = None
    mane: str | None = None
    horns: str = ""              # bull, ram, buffalo, oryx, zebu
    humps: int = 0
    hump_mat: str | None = None
    tail: str = "thin"           # thin, tied (Nisaean horse), tuft, bushy, long (lion)
    topknot: bool = False
    stripes_legs: bool = False   # the okapi
    face_mask: bool = False      # the oryx
    ears: str = "small"          # small, gold (Tištrya), round (lion), long (donkeys)
    lead: bool = False           # a lead rope from the neck (lions led by hand)
    dewlap: bool = False


SIZE = 2.5      # beasts are written in compact units; this brings a horse to about 44 px
REACH = 0.13    # a hoof sweeps this share of the body length either side of its hip
RUN = (1.35, 0.4)  # the trot: reach x 1.35, each hoof down 40 % of the cycle (diagonal pairs)
BIRD_REACH = 0.8   # walking birds: a foot swings this far either side (body units)


def stride(b: "Beast", anim: str = "move") -> float:
    """Ground one walk cycle covers, design units: 2 x reach over the duty factor."""
    if anim == "run":
        return 2 * REACH * RUN[0] * b.length * SIZE / RUN[1]
    return 2 * REACH * b.length * SIZE / BEAST_DUTY


def bird_feet(t: float, walking: bool):
    """Two small feet stepping (x offset, lift) per foot over a cycle; still when not walking.
    One cycle covers 4 x BIRD_REACH body units."""
    if not walking:
        return ((0.0, 0.0), (0.0, 0.0))
    (a, la), (b, lb) = foot_cycle(t), foot_cycle(t + 0.5)
    return ((a * BIRD_REACH, la * 0.5), (b * BIRD_REACH, lb * 0.5))


def _scaled(b: Beast) -> Beast:
    from dataclasses import replace
    return replace(b, length=b.length * SIZE, height=b.height * SIZE, girth=b.girth * SIZE * 1.15,
                   neck=b.neck * SIZE, head=b.head * SIZE, leg=b.leg * SIZE * 1.5)


def quadruped(b: Beast, anim: str, frame: int, frames: int, k: int) -> Model:
    b = _scaled(b)
    L, H, g = b.length, b.height, b.girth
    m = Model.empty(-int(L) - 4, int(L) + int(b.neck) + 6, -int(g * 2) - 6, int(g * 2) + 6, 0,
                    int(H + b.neck + b.head * 4) + 4, k=k)
    bd = Body(m)
    ph = frame / frames
    run = anim == "run"
    gait = anim in ("move", "run")
    graze = anim in ("graze", "peck")
    bob = 0.125 * (1 - math.cos(4 * math.pi * ph)) if gait else 0.1 * (frame % 2)
    bz = H - g * 0.4 + bob
    # Barrel, a deep chest forward and rounded quarters behind, so the body is shaped, not a
    # sausage.
    bd.blob((0, 0, bz), (L * 0.42, g * 0.92, g * 1.05), b.coat, 0.05)
    bd.blob((L * 0.26, 0, bz - g * 0.05), (L * 0.24, g * 1.0, g * 1.22), b.coat, 0.15)
    bd.blob((-L * 0.3, 0, bz + g * 0.05), (L * 0.22, g * 1.02, g * 1.1), b.coat, 0.1)
    if b.belly:
        bd.put((((bd.X / (L * 0.48)) ** 2 + (bd.Y / (g * 0.9)) ** 2 + ((bd.Z - bz + g * 0.5) / (g * 0.7)) ** 2) <= 1)
               & (bd.Z < bz - g * 0.3), b.belly, 0.2)
    for i in range(b.humps):
        hx = (-0.15 + 0.35 * i) * L if b.humps == 2 else 0.0
        bd.blob((hx, 0, bz + g * 1.1), (L * 0.16, g * 0.7, g * 0.9), b.hump_mat or b.coat, 0.15)
    # Legs in a four-beat walk (left hind, left fore, right hind, right fore), each hoof planted
    # while it bears weight: forelegs fold at the knee as they lift, hind legs bend backward at
    # the hock; muscled above, slender cannons below, dark hooves.
    # A trot moves diagonal pairs together, reaching further, with a moment in the air.
    legs = ((0.36, 1, 0.0), (0.36, -1, 0.5), (-0.36, 1, 0.5), (-0.36, -1, 0.0)) if run else \
        ((0.36, 1, 0.25), (0.36, -1, 0.75), (-0.36, 1, 0.0), (-0.36, -1, 0.5))
    for lx, side, off in legs:
        a, up = foot_cycle(ph - off, RUN[1] if run else BEAST_DUTY) if gait else (0.0, 0.0)
        sw = a * L * REACH * (RUN[0] if run else 1.0)
        lift = up * H * (0.18 if run else 0.12)
        y = side * g * 0.55
        if lx > 0:      # foreleg: elbow, knee, hoof
            top = (lx * L, y, bz - g * 0.55)
            knee = (lx * L + sw * 0.4 + lift * 0.5, y, H * 0.36 + lift)
            foot = (lx * L + sw - lift * 0.7, y, 0.35 + lift * 0.9)
            bd.limb(top, knee, b.leg * 1.5, b.coat, -0.05, r2=b.leg * 0.95)
            bd.limb(knee, foot, b.leg * 0.85, b.coat, -0.2, r2=b.leg * 0.7)
        else:           # hind leg: stifle, hock bent back, hoof
            top = (lx * L + L * 0.04, y, bz - g * 0.35)
            hock = (lx * L - L * 0.07 + sw * 0.5, y, H * 0.3 + lift * 0.8)
            foot = (lx * L - L * 0.02 + sw - lift * 0.5, y, 0.35 + lift * 0.9)
            bd.limb(top, hock, b.leg * 1.75, b.coat, -0.05, r2=b.leg * 0.8)
            bd.limb(hock, foot, b.leg * 0.8, b.coat, -0.2, r2=b.leg * 0.7)
            knee = hock
        if b.stripes_legs:
            bd.put(((bd.X - knee[0]) ** 2 + (bd.Y - y) ** 2 < (b.leg * 1.4) ** 2) & (bd.Z < H * 0.6) &
                   ((bd.Z * 2.2) % 1.0 < 0.45), "white_paint", 0.3)
        bd.blob((foot[0] + 0.1, foot[1], foot[2] - 0.05), (b.leg * 1.0, b.leg * 0.9, 0.35), "ink" if b.coat != "white_paint" else "gold", 0.4)
    # Neck and head.
    n0 = (L * 0.42, 0, bz + g * 0.3)
    dip = H * 0.75 if graze else 0.0
    ang = math.radians(15 + 60 * b.neck_up)
    head = (n0[0] + b.neck * math.cos(ang) * (1.2 if graze else 1.0), 0, n0[2] + b.neck * math.sin(ang) - dip * (1 if graze else 0))
    if graze:
        head = (n0[0] + b.neck * 0.9, 0, max(b.head + 0.3, n0[2] - H * 0.8 + 0.4 * (frame % 2)))
    if b.humps and not graze:   # the camel's neck dips forward, then rises to the head
        mid = (n0[0] + b.neck * 0.65, 0, n0[2] - b.neck * 0.15)
        head = (mid[0] + b.neck * 0.25, 0, mid[2] + b.neck * 0.7)
        bd.limb(n0, mid, g * 0.55, b.coat, 0.1, r2=g * 0.38)
        bd.limb(mid, head, g * 0.38, b.coat, 0.15, r2=g * 0.32)
    else:                       # an arched neck, thick at the shoulder
        mid = ((n0[0] + head[0]) / 2 + 0.2 * g, 0, (n0[2] + head[2]) / 2 + 0.25 * g)
        bd.limb(n0, mid, g * 0.7, b.coat, 0.1, r2=g * 0.5)
        bd.limb(mid, head, g * 0.5, b.coat, 0.15, r2=g * 0.4)
    hz = head[2]
    snout = (head[0] + b.head * 1.3, 0, hz - b.head * 0.5)
    bd.limb(head, snout, b.head * 0.6, b.coat, 0.15, r2=b.head * 0.45)
    bd.points([(head[0] + b.head * 0.3, 0.45 * b.head + 0.2, hz + 0.2)], "ink")
    if b.face_mask:
        bd.limb(head, snout, b.head * 0.62, "ink", 0.3, r2=b.head * 0.3)
    if b.mane:
        bd.limb((n0[0] - 0.3, 0, n0[2] + g * 0.6), (head[0] - 0.4, 0, hz + b.head * 0.6), g * 0.35, b.mane, -0.1)
    if b.topknot:
        bd.blob((head[0], 0, hz + b.head * 1.0), (0.5, 0.5, 0.6), b.mane or "hair_black")
    ear = "gold" if b.ears == "gold" else b.coat
    for side in (1, -1):
        bd.limb((head[0] - 0.2, side * b.head * 0.4, hz + b.head * 0.5),
                (head[0] - 0.5, side * b.head * 0.7, hz + b.head * {"round": 1.0, "long": 2.4}.get(b.ears, 1.4)), 0.3, ear,
                0.2)
    if b.dewlap:
        bd.limb((n0[0] + 0.5, 0, n0[2] - g * 0.5), (head[0], 0, hz - b.head * 1.0), g * 0.3, b.coat, -0.2)
    for side in (1, -1):
        base = (head[0] - 0.1, side * b.head * 0.55, hz + b.head * 0.55)
        if b.horns in ("bull", "zebu"):
            bd.limb(base, (head[0] + 0.4, side * b.head * 1.3, hz + b.head * 1.4), 0.32, "cream", 0.3)
        elif b.horns == "buffalo":
            bd.limb(base, (head[0] - 0.8, side * b.head * 2.4, hz + b.head * 0.8), 0.42, "polished", 0.4)
        elif b.horns == "ram":
            pts = [(head[0] - 0.2 - 0.9 * math.sin(a), side * (b.head * 0.7 + 0.25 * a), hz + b.head * 0.4 + 0.9 * math.cos(a))
                   for a in np.linspace(0, 4.2, 9)]
            for p0, p1 in zip(pts, pts[1:]):
                bd.limb(p0, p1, 0.42, "cream", 0.2)
        elif b.horns == "oryx":
            bd.limb(base, (head[0] - 2.8, side * b.head * 0.6, hz + b.head * 3.6), 0.22, "polished", 0.4)
    # Tail.
    t0 = (-L * 0.5, 0, bz + g * 0.4)
    if b.tail == "tied":         # the Nisaean horse's tail knotted short, as on the reliefs
        bd.limb(t0, (-L * 0.6, 0, bz - g * 0.6), 0.5, b.mane or "hair_black")
        bd.blob((-L * 0.62, 0, bz - g * 0.9), (0.6, 0.6, 0.6), b.mane or "hair_black")
    elif b.tail == "long":
        sw = 0.6 * math.sin(2 * math.pi * ph)
        bd.limb(t0, (-L * 0.85, sw, bz - g * 0.2), 0.3, b.coat)
        bd.blob((-L * 0.88, sw, bz - g * 0.3), (0.5, 0.5, 0.55), "felt")
    elif b.tail == "bushy":
        bd.limb(t0, (-L * 0.62, 0, bz - g * 1.4), 0.6, b.mane or b.coat)
    else:
        bd.limb(t0, (-L * 0.58, 0, bz - g * 1.6), 0.28, b.coat)
        if b.tail == "tuft":
            bd.blob((-L * 0.6, 0, bz - g * 1.8), (0.4, 0.4, 0.6), "felt")
    if b.lead:
        bd.limb((n0[0], 0, n0[2] + 0.2), (n0[0] + 6.0, 2.0, n0[2] + 6.0), 0.2, "straw", 0.3)
    return m


BEASTS = {
    "parsa.nisaean_horse": Beast(9.5, 8.5, 1.6, 3.6, 0.7, 1.1, coat="cedar", mane="hair_black", tail="tied", topknot=True),
    "parsa.bactrian_camel": Beast(10.5, 9.5, 2.0, 4.6, 0.35, 1.0, coat="wool", humps=2, hump_mat="felt", tail="tuft"),
    "parsa.dromedary": Beast(10.5, 10.0, 1.9, 5.0, 0.3, 1.0, coat="mudbrick", humps=1, tail="tuft"),
    "parsa.zebu": Beast(9.0, 7.5, 2.0, 1.8, 0.2, 1.1, coat="cream", humps=1, hump_mat="cream", horns="zebu",
                        dewlap=True, tail="tuft"),
    "parsa.bull": Beast(9.5, 7.5, 2.2, 1.8, 0.2, 1.2, coat="felt", horns="bull", tail="tuft"),
    "parsa.ram": Beast(6.0, 4.6, 1.8, 1.4, 0.4, 0.8, coat="wool", horns="ram", tail="bushy", mane="wool"),
    "parsa.lioness": Beast(8.5, 5.6, 1.6, 1.8, 0.4, 1.1, coat="wool", belly="cream", tail="long", ears="round",
                           lead=True),
    "parsa.lion_cub": Beast(4.6, 3.0, 1.0, 1.0, 0.5, 0.8, coat="wool", belly="cream", tail="long", ears="round"),
    "parsa.water_buffalo": Beast(10.0, 7.2, 2.3, 1.6, 0.15, 1.2, coat="polished", horns="buffalo", tail="tuft"),
    "parsa.oryx": Beast(8.0, 6.8, 1.4, 2.6, 0.6, 0.9, coat="cream", belly="white_paint", horns="oryx", face_mask=True,
                        tail="tuft"),
    "parsa.okapi": Beast(8.5, 7.5, 1.5, 3.4, 0.6, 1.0, coat="cedar", stripes_legs=True, tail="tuft"),
    "parsa.hound": Beast(6.0, 4.6, 1.0, 1.8, 0.6, 0.8, coat="wool", tail="thin", leg=0.32),
    # Tištrya, the rain star, as the Avesta's white horse with golden ears.
    "parsa.tishtrya": Beast(9.5, 8.5, 1.6, 3.6, 0.75, 1.1, coat="white_paint", mane="snow", tail="bushy", ears="gold"),
}


def hoopoe(anim, frame, frames, k):
    """A hoopoe: pinkish-buff with barred black-and-white wings and a fanned crest, probing."""
    m = Model.empty(-6, 8, -4, 4, 0, 9, k=k)
    bd = Body(m, rot=np.eye(3) / 1.5)
    peck = anim == "peck" and frame % 2 == 1
    t = frame / frames
    hop = 0.15 * (1 - math.cos(4 * math.pi * t)) if anim == "move" else 0.0
    bd.blob((0, 0, 1.8 + hop), (1.5, 0.8, 0.9), "saffron", 0.2)
    bd.put((np.abs(bd.Y) > 0.4) & (((bd.X + 2) * 2.5) % 1.0 < 0.5) & ((bd.X / 1.6) ** 2 + (bd.Y / 0.9) ** 2 +
           ((bd.Z - 1.9 - hop) / 0.8) ** 2 <= 1) & (bd.X < 0.5), "ink", 0.0)
    hz = 3.0 + hop - (1.5 if peck else 0)
    bd.blob((1.4, 0, hz), (0.6, 0.55, 0.6), "saffron", 0.3)
    bd.limb((1.7, 0, hz - 0.1), (3.2, 0, hz - 0.8 - (0.4 if peck else 0)), 0.15, "ink")
    for i, a in enumerate(np.linspace(-0.9, 0.6, 5)):
        bd.limb((1.2, 0, hz + 0.3), (1.2 - 1.3 * math.sin(a), 0, hz + 0.3 + 1.2 * math.cos(a)), 0.18,
                "saffron" if i % 2 else "orange", 0.3)
    bd.limb((-1.3, 0, 1.9 + hop), (-2.8, 0, 1.6 + hop), 0.3, "ink")
    for y, (fx, fz) in zip((0.3, -0.3), bird_feet(t, anim == "move")):
        bd.limb((0.2, y, 1.0 + hop), (0.2 + fx, y, 0.1 + fz), 0.12, "felt")
    return m


WALKING_BIRDS = {"parsa.hoopoe": 1.5}   # walking birds: body scale (strides)
CRITTERS = {**{k_: None for k_ in BEASTS}, "parsa.hoopoe": hoopoe}


# ---------------------------------------------------------------- carts

def _wheel(bd: Body, cx, cz, r, side_y, turn, mat="cedar"):
    X, Y, Z = bd.X, bd.Y, bd.Z
    d = np.hypot(X - cx, Z - cz)
    a = np.arctan2(Z - cz, X - cx) + turn
    rim = (np.abs(d - r) < 0.45) & (np.abs(Y - side_y) < 0.45)
    spokes = (d < r) & (np.abs(Y - side_y) < 0.35) & (np.abs(np.sin(a * 3)) < 0.12)
    hub = (d < 0.6) & (np.abs(Y - side_y) < 0.6)
    bd.put(rim | spokes | hub, mat, 0.2)


def _driver(m, x, y, dress, frame, k, seated=False, anim="move", cycle=None, frames=CART_FRAMES):
    fr = Frame(dress)
    p = pose(anim, frame, frames, fr, dress, cycle) if anim == "move" else pose(anim, frame % 2, 2, fr, dress)
    b = Body(m, shift=(x, y, 0.0))
    draw(b, dress, p, fr)


DRIVER = Dress(garment="tunic", colour="wool", belt="leather", beard="short", head="felt_cap", head_mat="felt",
               feet="bare", hair_style="short", hand_l="staff")


CART_OX = (Beast(8.5, 6.6, 2.0, 1.6, 0.2, 1.1, coat="cream", horns="bull", tail="tuft"),
           Beast(8.5, 6.6, 2.0, 1.6, 0.2, 1.1, coat="felt", horns="bull", tail="tuft"))
SLEDGE_OX = Beast(8.0, 6.2, 1.8, 1.6, 0.2, 1.1, coat="felt", horns="bull", tail="tuft")


def _rollers(x0: float, span: float, t: float, n: int = 3):
    """Rollers under a sledge: they slip back as it moves and are carried round to the front."""
    return [x0 + (i * span / n + span / n * (1 - t)) % span for i in range(n)]


def cart_stride(kind) -> float:
    """Ground one cycle of a cart's `move` covers, design units (its team's walk)."""
    return {"parsa.p_cart": stride(CART_OX[0]), "parsa.p_sledge": stride(SLEDGE_OX)}.get(kind, rig_stride())


def rig_stride() -> float:
    from rig import HORSE_STRIDE
    return HORSE_STRIDE


def cart_model(kind, variant, anim, frame, k, frames=CART_FRAMES):
    """Carts with their teams and drivers baked in (world-tech.md §1.9), at toy scale: an ox
    about as tall as a man at the shoulder, wheels as tall as his waist."""
    turn = frame / frames * (math.pi / 3) if anim == "move" else 0.0
    m = Model.empty(-44, 40, -14, 14, 0, 46, k=k)
    team = "move" if anim == "move" else "idle"
    tf, tn = (frame, frames) if team == "move" else (frame % 2, 2)
    if kind == "parsa.p_cart":
        # A two-wheeled cart with spoked wheels behind an ox, its driver walking beside.
        ox = CART_OX[variant]
        m = _merge(m, quadruped(ox, team, tf, tn, k), 16.0, 0.0)
        bd = Body(m)
        slab(m, -34, -10, -7, 7, 9.0, 10.5, "wood_light", tone=0.2)
        for y in (-7.4, 7.4):
            slab(m, -34, -10, y - 0.5, y + 0.5, 10.5, 15.0, "wood", tone=0.1)
        rod(m, (-10, 0, 10.0), (8.0, 0, 12.0), 0.7, "wood")
        for y in (-8.4, 8.4):
            _wheel(bd, -22, 8.0, 7.6, y, turn)
        if variant == 0:
            for i, (x, y) in enumerate(((-29, -3), (-23, 3), (-17, -2))):
                ellipsoid(m, (x, y, 14.0), (3.4, 2.8, 3.6), "straw", tone=0.1 * i)
        else:
            slab(m, -30, -14, -5, 5, 10.5, 18.0, "limestone", tone=0.3)
        _driver(m, 14.0, 11.0, DRIVER, frame, k, anim="move" if anim == "move" else "idle", cycle=stride(ox),
                frames=frames)
    elif kind == "parsa.p_sledge":
        # Two oxen yoked to a wooden sledge carrying a column drum, rollers under it.
        for y in (-5.5, 5.5):
            m = _merge(m, quadruped(SLEDGE_OX, team, tf, tn, k), 16.0, y)
        rod(m, (12.0, -7, 13.0), (12.0, 7, 13.0), 0.9, "wood")
        rod(m, (12.0, 0, 12.0), (-12.0, 0, 4.0), 0.9, "wood")
        slab(m, -40, -12, -8, 8, 2.0, 4.5, "wood_light", tone=0.2)
        for x in _rollers(-38.0, 27.0, frame / frames if anim == "move" else 0.0):
            rod(m, (x, -9, 1.2), (x, 9, 1.2), 1.2, "wood")
        rod(m, (-34, 0, 9.5), (-18, 0, 9.5), 5.0, "limestone", tone=0.3)
        _driver(m, 10.0, 12.0, DRIVER, frame, k, anim="move" if anim == "move" else "idle",
                cycle=stride(SLEDGE_OX), frames=frames)
    else:
        # The two-horse chariot of the Lydian (and Libyan) gift: light box, big spoked wheels.
        for y in (-4.5, 4.5):
            mo = Model.empty(-22, 22, -9, 9, 0, 36, k=k)
            rig_horse(Body(mo), frame / frames, coat="cedar" if variant == 0 else "wool",
                      trappings="cinnabar")
            m = _merge(m, mo, 16.0, y)
        bd = Body(m)
        rod(m, (6.0, 0, 15.0), (-12.0, 0, 10.0), 0.8, "cedar")
        slab(m, -22, -10, -6.0, 6.0, 8.0, 9.5, "cedar", tone=0.2)
        fill(m, (-22, -10, -6, 6, 9.5, 18.0), "lapis" if variant == 0 else "cinnabar",
             lambda X, Y, Z: (np.abs(Y) > 5.0) | (X > -11.2), tone=0.2)
        for y in (-7.0, 7.0):
            _wheel(bd, -16, 8.0, 7.8, y, turn, "cedar")
    return m


def _merge(dst: Model, src: Model, dx: float, dy: float) -> Model:
    """Copy src's voxels into dst shifted by (dx, dy) design units (whole voxels)."""
    k = dst.k
    ox, oy = int(round(dx * k)), int(round(dy * k))
    sx0, sy0, sz0 = src.x0 + ox - dst.x0, src.y0 + oy - dst.y0, src.z0 - dst.z0
    nx, ny, nz = src.mat.shape
    a = [(max(0, -o), min(n, N - o)) for o, n, N in zip((sx0, sy0, sz0), (nx, ny, nz), dst.mat.shape)]
    (i0, i1), (j0, j1), (l0, l1) = a
    sl_s = (slice(i0, i1), slice(j0, j1), slice(l0, l1))
    sl_d = (slice(i0 + sx0, i1 + sx0), slice(j0 + sy0, j1 + sy0), slice(l0 + sz0, l1 + sz0))
    on = src.mat[sl_s] > 0
    dst.mat[sl_d][on] = src.mat[sl_s][on]
    dst.tone[sl_d][on] = src.tone[sl_s][on]
    dst.nrm[sl_d][on] = src.nrm[sl_s][on]
    return dst


CARTS = {"parsa.p_cart", "parsa.p_sledge", "parsa.chariot"}


def _render(m: Model, facing: str) -> Sprite:
    if facing == "back":
        m = m.rotated(3, 0, 0)
    rgba, _g, ox, oy = render_base(m)
    return Sprite(rgba, ox, oy)


def sprite(kind, variant, anim, facing, frame, k, frames=None):
    """`frames`: the cycle's length where the set's page budget sets it."""
    if kind in CARTS:
        return _render(cart_model(kind, variant or 0, anim, frame, k, frames or CART_FRAMES), facing)
    frames = frames or CRITTER_FRAMES[anim]
    if kind == "parsa.hoopoe":
        return _render(hoopoe(anim, frame, frames, k), facing)
    return _render(quadruped(BEASTS[kind], anim, frame, frames, k), facing)
