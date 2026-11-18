"""The animals, birds and boats of road and sea (docs/design/sets/world.md §5.2-5.3). Quadrupeds
use the shared builder of the Pārsa set (proportions and markings as data) with the loads and
breeds of the world: the grey donkey with its shoulder cross and panniers, the bay mule with a
pack saddle, Mediterranean and fat-tailed sheep (Herodotus 3.113), black and piebald goats, the
dun working ox, the herding dog, the gazelle. Birds are small voxel bodies, anchored at the
bottom of the body (the engine adds altitude). Boats lie along x with the bow toward +x, crews
baked in, sails bellying to the right of the screen. Like critters they face +x."""

import math
from dataclasses import replace

import numpy as np

from arch import ellipsoid, fill, revolve, rod, slab
from rig import CRITTER_FRAMES, Body, Dress, Frame, draw, pose
from sets.parsa.animals import SIZE, Beast, _render, quadruped
from voxel import Model

BEASTS = {
    "world.donkey": Beast(6.8, 5.4, 1.5, 2.0, 0.55, 1.0, coat="wood_grey", belly="cream", tail="tuft", ears="long"),
    "world.mule": Beast(7.9, 6.8, 1.5, 2.6, 0.6, 1.05, coat="cedar", belly="ochre", mane="hair_black", tail="tuft",
                        ears="long"),
    "world.sheep": Beast(5.6, 4.0, 1.8, 1.3, 0.4, 0.8, coat="wool", mane="wool", tail="bushy", leg=0.32),
    "world.goat": Beast(5.4, 4.4, 1.3, 1.6, 0.6, 0.8, coat="gloss", belly="gloss", horns="ram", tail="tuft", leg=0.3),
    "world.ox": Beast(9.2, 7.2, 2.1, 1.6, 0.2, 1.1, coat="wood_light", belly="cream", horns="bull", tail="tuft",
                      dewlap=True),
    "world.dog": Beast(5.6, 4.6, 0.95, 1.8, 0.6, 0.8, coat="wool", belly="cream", tail="bushy", leg=0.3),
    "world.gazelle": Beast(5.8, 5.6, 1.0, 2.4, 0.75, 0.75, coat="ochre", belly="cream", horns="oryx", tail="thin",
                           leg=0.24),
    # Woods of Thrace, Latium and the Apennines: a red deer stag, and a dark bristled boar.
    "world.deer": Beast(7.2, 6.8, 1.15, 2.6, 0.8, 0.85, coat="cedar", belly="cream", horns="antler", tail="thin",
                        leg=0.26),
    "world.boar": Beast(6.0, 4.8, 1.35, 1.2, 0.15, 1.1, coat="bark", belly="bark", mane="gloss", tail="thin",
                        leg=0.36),
}
VARIANT_COAT = {("world.goat", 1): replace(BEASTS["world.goat"], coat="cedar", belly="cream", mane="cream")}
FRAMES = CRITTER_FRAMES


def _beast(kind, variant):
    return VARIANT_COAT.get((kind, variant or 0), BEASTS[kind])


def _load(m, kind, variant, anim, frame, frames):
    """Panniers, pack saddles and the fat tail, on the beast's barrel (body centre at x 0)."""
    b = _beast(kind, variant)
    L, H, g = b.length * SIZE, b.height * SIZE, b.girth * SIZE * 1.15
    bob = 0.125 * (1 - math.cos(4 * math.pi * frame / frames)) if anim == "move" else 0.0
    bz = H - g * 0.4 + bob
    if kind == "world.donkey":
        # The dark shoulder cross, and on v1 two wicker panniers over a blanket.
        fill(m, (L * 0.15, L * 0.3, -g * 1.3, g * 1.3, bz, bz + g * 1.3), "ink",
             lambda X, Y, Z: (np.abs(X - L * 0.22) < 0.5) | ((np.abs(Y) < 0.6) & (X > -L * 0.4)), tone=0.2, only_solid=True)
        if variant == 1:
            slab(m, -L * 0.2, L * 0.15, -g * 1.1, g * 1.1, bz + g * 0.85, bz + g * 1.15, "cinnabar", tone=0.1)
            for s in (-1, 1):
                fill(m, (-L * 0.2, L * 0.12, s * g * 0.9 - 2.0, s * g * 0.9 + 2.0, bz - g * 0.9, bz + g * 0.9), "straw",
                     lambda X, Y, Z, s=s: np.abs(Y - s * (g * 1.0 + 1.2)) < 1.3,
                     tone=lambda X, Y, Z: -0.4 * (((X + Z) % 1.6) < 0.4) + 0.1)
    elif kind == "world.mule" and variant == 1:
        slab(m, -L * 0.22, L * 0.18, -g * 1.0, g * 1.0, bz + g * 0.85, bz + g * 1.4, "wood", tone=0.1)
        for s in (-1, 1):
            ellipsoid(m, (-L * 0.02, s * (g + 1.4), bz + g * 0.3), (L * 0.18, 1.4, g * 0.75), "linen", tone=0.1)
            rod(m, (-L * 0.2, s * (g + 1.4), bz + g * 0.3), (L * 0.15, s * (g + 1.4), bz + g * 0.3), 0.25, "straw")
        ellipsoid(m, (-L * 0.02, 0, bz + g * 2.0), (L * 0.16, g * 0.8, g * 0.6), "wool", tone=0.0)
    elif kind == "world.sheep" and variant == 1:
        ellipsoid(m, (-L * 0.52, 0, bz - g * 0.35), (L * 0.13, g * 0.8, g * 0.75), "wool", tone=0.15)


def dog_sleep(frame, k):
    """The herding dog asleep, curled on the ground, nose on its tail; it breathes."""
    m = Model.empty(-14, 14, -10, 10, 0, 10, k=k)
    bd = Body(m)
    br = 0.2 * (frame % 2)
    bd.blob((0, 0, 2.4 + br), (6.5, 3.6, 2.4 + br), "wool", 0.1)
    bd.blob((4.5, 2.4, 2.2), (2.4, 2.0, 1.8), "wool", 0.2)
    bd.limb((5.5, 3.0, 2.4), (8.0, 2.6, 1.6), 1.0, "cream", 0.2)
    bd.points([(7.2, 3.6, 2.6)], "ink")
    bd.limb((4.0, 2.8, 3.6), (3.4, 3.6, 4.6), 0.4, "wool", 0.2)
    bd.limb((-6.0, 0.0, 2.0), (-2.0, 4.0, 1.4), 1.2, "wool", 0.1)
    return m


def _bird(kind, anim, frame, frames, k):
    """Birds as small bodies with wings; flying anims flap or glide, `idle` stands or perches."""
    m = Model.empty(-22, 22, -22, 22, 0, 18, k=k)
    bd = Body(m)
    fly = anim == "move"
    t = frame / frames
    spec = {
        "world.gull": dict(size=1.0, body="white_paint", wing="stone", tip="ink", beak="yellow", legs="yellow", span=9.0),
        "world.stork": dict(size=1.3, body="white_paint", wing="white_paint", tip="ink", beak="cinnabar", legs="cinnabar",
                            span=12.0, neck=2.4, leg_len=4.5),
        "world.crane": dict(size=1.3, body="stone", wing="stone", tip="ink", beak="ink", legs="ink", span=12.0, neck=2.6,
                            cap="cinnabar"),
        "world.eagle": dict(size=1.4, body="cedar", wing="cedar", tip="ink", beak="yellow", legs="yellow", span=15.0,
                            head="ochre", glide=True),
        "world.swift": dict(size=0.6, body="ink", wing="ink", tip="ink", beak="ink", legs="ink", span=7.0, sickle=True),
        "world.raven": dict(size=1.0, body="gloss", wing="gloss", tip="gloss", beak="gloss", legs="gloss", span=10.0),
        # The tawny owl: round-headed, perching upright, out at night.
        "world.owl": dict(size=1.25, body="wood_grey", wing="cedar", tip="ink", beak="ochre", legs="ochre", span=10.0,
                          head="wood_light", head_r=1.5, glide=True, upright=True),
        "world.heron": dict(size=1.35, body="stone", wing="stone", tip="ink", beak="ochre", legs="ochre", span=13.0,
                            neck=2.8, leg_len=4.8, cap="ink"),
        "world.bat": dict(size=0.5, body="gloss", wing="felt", tip="gloss", beak="gloss", legs="gloss", span=7.0),
    }[kind]
    s = spec["size"]
    if spec.get("upright") and not fly:     # perched upright: the owl on a branch or a wall
        bd.blob((0, 0, 2.2 * s), (1.3 * s, 1.2 * s, 2.0 * s), spec["body"], 0.1)
        for side in (1, -1):
            bd.blob((-0.3 * s, side * 1.0 * s, 2.0 * s), (1.0 * s, 0.4 * s, 1.7 * s), spec["wing"], 0.0)
        bd.blob((0.2 * s, 0, 4.6 * s), (1.2 * s, 1.2 * s, 1.0 * s), spec["head"], 0.2)
        for side in (1, -1):
            bd.points([(1.2 * s, side * 0.5 * s, 4.8 * s)], "ink")
        bd.points([(1.4 * s, 0, 4.4 * s)], spec["beak"])
        return m
    z = 1.0 if fly else (spec.get("leg_len", 1.6) * s)
    bd.blob((0, 0, z + 1.2 * s), (2.6 * s, 1.1 * s, 1.1 * s), spec["body"], 0.1)
    hx = 2.6 * s
    neck = spec.get("neck", 0.0) * s
    if anim == "peck" and frame % 2:
        head = (hx + 0.8 * s, 0, max(0.6, z - 0.8 * s))
    else:
        head = (hx + (neck * 0.7 if fly else 0.4 * s), 0, z + 1.6 * s + (0 if fly else neck))
    if neck:
        bd.limb((hx * 0.8, 0, z + 1.4 * s), head, 0.45 * s, spec["body"], 0.1)
    hr = spec.get("head_r", 1.0)
    bd.blob(head, (0.9 * s * hr, 0.75 * s * hr, 0.75 * s * hr), spec.get("head", spec["body"]), 0.2)
    if spec.get("cap"):
        bd.blob((head[0], 0, head[2] + 0.5 * s), (0.4 * s, 0.4 * s, 0.25 * s), spec["cap"], 0.2)
    bl = 1.6 * s if kind in ("world.stork", "world.crane") else 0.9 * s
    bd.limb((head[0] + 0.6 * s, 0, head[2]), (head[0] + 0.6 * s + bl, 0, head[2] - 0.4 * s), 0.25 * s, spec["beak"], 0.2)
    bd.points([(head[0] + 0.3 * s, 0.6 * s, head[2] + 0.2 * s)], "ink")
    bd.limb((-2.4 * s, 0, z + 1.3 * s), (-4.0 * s, 0, z + 1.1 * s), 0.6 * s, spec["wing"], 0.0)
    if fly:
        if spec.get("glide"):
            a = 0.15 * math.sin(2 * math.pi * t)
        else:
            a = math.sin(2 * math.pi * t) * 0.9
        for side in (1, -1):
            span = spec["span"] * s / 1.2
            root = (0.2 * s, side * 0.9 * s, z + 1.5 * s)
            mid = (-0.4 * s - (1.5 * s if spec.get("sickle") else 0), side * span * 0.5, z + 1.5 * s + a * span * 0.4)
            tip = (-1.4 * s - (3.0 * s if spec.get("sickle") else 0), side * span, z + 1.5 * s + a * span * 0.7)
            bd.limb(root, mid, 0.55 * s, spec["wing"], 0.1)
            bd.limb(mid, tip, 0.4 * s, spec["tip"], 0.0)
        if spec.get("leg_len"):
            bd.limb((-2.0 * s, 0, z + 1.0 * s), (-5.5 * s, 0, z + 0.8 * s), 0.18 * s, spec["legs"], 0.1)
    else:
        for side in (1, -1):
            bd.limb((0.4 * s, side * 0.9 * s, z + 1.6 * s), (-2.6 * s, side * 0.9 * s, z + 1.3 * s), 0.55 * s, spec["wing"], 0.0)
            bd.limb((-1.6 * s, side * 0.95 * s, z + 1.3 * s), (-3.0 * s, side * 0.9 * s, z + 1.1 * s), 0.4 * s, spec["tip"], 0.0)
            bd.limb((0, side * 0.4 * s, z + 0.4 * s), (0, side * 0.4 * s, 0.0), 0.18 * s, spec["legs"], 0.1)
    return m


BIRDS = {"world.gull", "world.stork", "world.crane", "world.eagle", "world.swift", "world.raven", "world.owl",
         "world.heron", "world.bat"}


def dolphin(frame, frames, k):
    """A dolphin breaking the surface: the body rolls along an arc out of the water and back,
    only what is above the surface drawn (the grid starts at the water line)."""
    m = Model.empty(-14, 14, -6, 6, 0, 12, k=k)
    m.hover = True
    bd = Body(m)
    t = frame / frames
    pts = []
    for i in range(9):          # nose (i = 0) to tail, the arc travelling forward with t
        u = t * 1.6 - 0.3 - i * 0.11
        pts.append((9.0 - i * 2.2, 0.0, 6.5 * math.sin(math.pi * min(max(u, 0.0), 1.0)) - 2.5))
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        r = 1.5 - abs(i - 2.5) * 0.22
        bd.limb(a, b, max(r, 0.45), "granite", 0.1)
        bd.limb((a[0], 0, a[2] - r * 0.5), (b[0], 0, b[2] - r * 0.5), max(r * 0.6, 0.3), "cream", 0.1)
    fin = pts[3]
    bd.limb(fin, (fin[0] - 1.4, 0, fin[2] + 2.2), 0.45, "granite", 0.0)
    tail = pts[-1]
    for side in (1, -1):
        bd.limb(tail, (tail[0] - 1.2, side * 1.8, tail[2] + 0.3), 0.4, "granite", 0.0)
    return m


# ---------------------------------------------------------------- boats

CREW = Dress(garment="exomis", colour="wool", beard="full", hair_style="short", head="felt_cap", head_mat="felt",
             feet="bare", skin="skin_olive")
CREW_EAST = Dress(garment="wrap", colour="linen", beard="full", hair="hair_black", hair_style="short", head="headcloth",
                  head_mat="cream", feet="bare", skin="skin_olive")


def _crew(m, x, y, z, dress, anim, frame, hold=None):
    d = replace(dress, hand_l=hold) if hold else dress
    fr = Frame(d)
    if anim in ("row", "haul"):
        p = pose("haul", frame % 4, 4, fr, d)
    else:
        p = pose("idle", frame % 2, 2, fr, d)
    # Crews at about two thirds of a walker's size, so a six-metre boat holds its two men.
    draw(Body(m, rot=np.eye(3) / CREW_SCALE, shift=(x, y, z)), d, p, fr)


CREW_SCALE = 0.62


def _hull(m, L, beam, depth, mat, top=None, rise=1.6, round_=0.7):
    """A boat's hull along x, bow at +x: its half-beam falls off toward both ends, the sheer
    rises toward bow and stern, a strake of `top` colour along the gunwale."""
    def half(X):
        tt = np.clip((X + L / 2) / L, 0, 1)
        return beam * np.clip(np.sin(np.pi * tt), 0, 1) ** round_ + 0.25

    def sheer(X):
        return depth + rise * ((X / (L / 2)) ** 2)
    fill(m, (-L / 2 - 1, L / 2 + 1, -beam - 1, beam + 1, 0.0, depth + rise + 1), mat,
         lambda X, Y, Z: (np.abs(Y) < half(X)) & (Z > depth * 0.4 * (Y / beam) ** 2) & (Z < sheer(X)),
         tone=lambda X, Y, Z: -0.35 * ((Z % 1.5) < 0.35) + 0.1)
    if top:
        fill(m, (-L / 2 - 1, L / 2 + 1, -beam - 1, beam + 1, 0.0, depth + rise + 1), top,
             lambda X, Y, Z: (np.abs(Y) < half(X)) & (Z < sheer(X)) & (Z > sheer(X) - 0.8), tone=0.2, only_solid=True)
    fill(m, (-L / 2 + 2, L / 2 - 2, -beam, beam, depth - 1.0, depth - 0.4), "wood_light",
         lambda X, Y, Z: np.abs(Y) < half(X) - 0.8, tone=0.1)
    return half


def _sail(m, x, h, w, anim, t, cloth="linen", z0=None):
    """A square sail on a yard, bellying toward +x under way, hanging when slack."""
    z0 = z0 if z0 is not None else h * 0.35
    rod(m, (x, 0.0, 2.0), (x, 0.0, h + 1.0), 0.45, "wood")
    rod(m, (x, -w, h), (x, w, h), 0.35, "wood")
    belly = (2.6 + 0.4 * math.sin(2 * math.pi * t)) if anim == "move" else 0.5
    fill(m, (x - 1.0, x + 4.0, -w, w, z0, h), cloth,
         lambda X, Y, Z: np.abs(X - (x + belly * np.clip(1 - (Y / w) ** 2, 0, 1) *
                                     np.clip(1 - ((Z - (z0 + h) / 2) / ((h - z0) / 2)) ** 2, 0, 1))) < 0.4,
         tone=lambda X, Y, Z: 0.25 * ((Y % 3.0) < 0.4) - 0.05)


def ship_model(kind, anim, frame, k):
    t = frame / 4
    if kind == "world.fishing_boat":
        # An open boat of about 6 m, a short mast with a small square sail, two pairs of oars,
        # eyes painted at the bow, a crew of two.
        m = Model.empty(-20, 20, -16, 16, 0, 34, k=k)
        L = 28.0
        _hull(m, L, 3.6, 3.4, "wood", top="eblue")
        for s in (1, -1):
            ellipsoid(m, (L / 2 - 2.4, s * 2.2, 4.4), (0.6, 0.3, 0.5), "white_paint", tone=0.3)
            ellipsoid(m, (L / 2 - 2.2, s * 2.3, 4.4), (0.3, 0.2, 0.3), "ink", tone=0.0)
        fill(m, (-6, 2, -2.5, 2.5, 2.8, 4.0), "wood_grey", lambda X, Y, Z: ((X + Y) % 1.4) < 0.4, tone=0.1)
        if anim in ("move", "slack"):
            _sail(m, 2.0, 22.0, 6.0, anim, t, z0=8.0)
            _crew(m, -9.0, 0.0, 2.6, CREW, "idle", frame)
            rod(m, (-L / 2 + 2, 2.0, 4.0), (-L / 2 - 3, 3.2, 0.0), 0.4, "wood")       # steering oar
        else:
            rod(m, (-10.0, 0.0, 4.6), (10.0, 0.4, 4.8), 0.4, "wood")                   # mast lowered
            ellipsoid(m, (0.0, 0.3, 5.3), (7.0, 0.9, 0.6), "linen", tone=0.1)
        if anim == "row":
            sw = math.sin(t * 2 * math.pi) * 2.2
            for x in (-3.0, 5.0):
                for s in (1, -1):
                    rod(m, (x, s * 3.4, 4.4), (x - sw, s * 10.0, 0.3), 0.22, "wood_light")
            _crew(m, -1.0, 0.0, 2.6, CREW, "row", frame)
            _crew(m, 7.0, 0.0, 2.6, CREW, "row", frame + 1)
        elif anim == "idle":
            _crew(m, -4.0, 0.0, 2.6, CREW, "idle", frame, hold="net")
            rod(m, (L / 2 - 1, 0.0, 4.5), (L / 2 + 6, 0.0, 0.5), 0.15, "straw")       # the mooring line
        else:
            _crew(m, 7.0, 0.0, 2.6, CREW, "idle", frame + 1)
        return m
    if kind == "world.quffa":
        # A round boat of hide over a willow frame (Herodotus 1.194), paddled, laden with sacks.
        m = Model.empty(-14, 14, -14, 14, 0, 26, k=k)
        fill(m, (-8, 8, -8, 8, 0.0, 4.5), "hide",
             lambda X, Y, Z: (np.hypot(X, Y) < 7.0 + Z * 0.15) & (np.hypot(X, Y) > 6.2 + Z * 0.15 - (Z < 1.0) * 8),
             tone=lambda X, Y, Z: -0.4 * (((np.arctan2(Y, X) * 8) % 1.0) < 0.15) + 0.1 * (Z > 3.8))
        revolve(m, 0, 0, 4.0, 4.8, lambda tt: 7.6, "wood_light", tone=0.2)
        for i, (x, y) in enumerate(((-3.0, -3.0), (-0.5, -4.2), (2.0, -2.5), (1.0, 0.5), (3.5, 0.0))):
            ellipsoid(m, (x, y, 2.6 + (i == 3) * 2.2), (1.6, 1.3, 1.5), ("straw", "linen")[i % 2], tone=0.1 * i)
        sw = math.sin(t * 2 * math.pi) * 2.0 if anim == "move" else 0.0
        _crew(m, -4.5, 3.0, 1.0, CREW_EAST, "idle", frame)
        rod(m, (-3.0, 4.5, 9.0), (-6.0 + sw, 9.0, 0.0), 0.25, "wood")
        return m
    if kind == "world.reed_boat":
        # Bundled reeds bound into a boat with upturned ends, a bitumen-dark waterline, a poler
        # and a load of dates or reeds.
        m = Model.empty(-22, 22, -10, 10, 0, 34, k=k)
        L = 30.0

        def body(X, Y, Z):
            u = X / (L / 2)
            half = 3.2 * np.sqrt(np.clip(1 - u ** 4, 0, 1)) + 0.3
            curl = 2.0 + 5.0 * np.clip(np.abs(u) - 0.7, 0, 1) ** 1.3 * 4
            return (np.abs(Y) < half) & (Z < curl) & (Z > 0.3 * (Y / 3.2) ** 2)
        fill(m, (-L / 2 - 1, L / 2 + 1, -4, 4, 0.0, 9.0), "straw", body,
             tone=lambda X, Y, Z: -0.5 * ((X % 2.2) < 0.35) + 0.15 * ((Y % 1.0) < 0.3))
        fill(m, (-L / 2 - 1, L / 2 + 1, -4, 4, 0.0, 1.0), "pitch", body, tone=0.0, only_solid=True)
        for i in range(4):
            ellipsoid(m, (-6.0 + i * 3.4, (-1) ** i * 0.8, 3.0), (1.5, 1.3, 1.3), "straw" if i % 2 else "orange", tone=0.1)
        _crew(m, 8.0, 0.0, 1.8, CREW_EAST, "idle", frame)
        lean = math.sin(t * 2 * math.pi) * 2.5 if anim == "move" else 0.0
        rod(m, (9.0, 1.4, 16.0), (6.0 - lean, 3.0, -2.0), 0.25, "wood")
        return m
    if kind == "world.kelek":
        # A raft of logs on inflated skins (Assyrian reliefs), a steersman at the sweep.
        m = Model.empty(-22, 22, -12, 12, 0, 28, k=k)
        for x in np.arange(-12.0, 13.0, 4.0):
            for y in np.arange(-6.0, 7.0, 4.0):
                ellipsoid(m, (x, y, 1.2), (1.8, 1.4, 1.2), "hide", tone=0.1)
        for y in np.arange(-7.0, 7.5, 1.6):
            rod(m, (-14.0, y, 2.8), (14.0, y, 2.8), 0.75, "wood", tone=0.1)
        for x in (-12.0, 12.0):
            rod(m, (x, -7.5, 3.6), (x, 7.5, 3.6), 0.5, "wood_light")
        for i in range(3):
            ellipsoid(m, (-3.0 + i * 3.5, 0.0, 4.6), (1.6, 1.4, 1.2), "linen", tone=0.1 * i)
        _crew(m, -10.0, 0.0, 3.2, CREW_EAST, "idle", frame)
        sw = math.sin(t * 2 * math.pi) * 1.5 if anim == "move" else 0.0
        rod(m, (-11.0, 1.0, 8.0), (-18.0, 2.0 + sw, 0.5), 0.3, "wood")
        return m
    # world.phoenician: a round-hulled merchantman, high stem and stern, a horse-head prow, a
    # square sail, two steering oars, a crew on deck and a cargo of jars.
    m = Model.empty(-40, 44, -24, 24, 0, 66, k=k)
    L = 62.0
    _hull(m, L, 9.0, 7.0, "wood", top="cinnabar", rise=3.0, round_=0.45)
    rod(m, (L / 2 - 2, 0, 8.0), (L / 2 + 3, 0, 15.0), 0.9, "wood")
    ellipsoid(m, (L / 2 + 3.6, 0, 16.0), (1.6, 0.9, 1.2), "wood", tone=0.2)          # the horse head
    rod(m, (L / 2 + 3.0, 0, 16.6), (L / 2 + 2.0, 0, 18.0), 0.4, "wood")
    rod(m, (-L / 2 + 2, 0, 8.0), (-L / 2 - 2, 0, 17.0), 0.9, "wood")
    rod(m, (-L / 2 - 2, 0, 17.0), (-L / 2 + 1, 0, 19.0), 0.6, "wood")
    for s in (1, -1):
        rod(m, (-L / 2 + 6, s * 7.0, 9.0), (-L / 2 - 1, s * 9.0, 0.0), 0.6, "wood")
    from greek import vase
    for i in range(8):
        vase(m, -14.0 + (i % 4) * 5.0, -3.0 + (i // 4) * 6.0, 6.4, 4.0, "transport", figure="plain")
    if anim in ("move", "slack"):
        _sail(m, 4.0, 50.0, 16.0, anim, t, cloth="cream", z0=18.0)
        for i, x in enumerate((-22.0, 18.0)):
            _crew(m, x, (-1) ** i * 2.0, 6.0, CREW, "idle", frame + i)
    else:
        rod(m, (4.0, 0.0, 6.0), (4.0, 0.0, 36.0), 0.6, "wood")
        rod(m, (4.0, -12.0, 34.0), (4.0, 12.0, 34.0), 1.0, "cream", tone=0.1)
        for i, x in enumerate((-22.0, 18.0)):
            _crew(m, x, (-1) ** i * 2.0, 6.0, CREW, "haul" if anim == "row" else "idle", frame + i)
    if anim == "row":
        sw = math.sin(t * 2 * math.pi) * 3.0
        for x in np.arange(-16.0, 20.0, 6.0):
            for s in (1, -1):
                rod(m, (x, s * 8.6, 7.6), (x - sw, s * 18.0, 0.3), 0.25, "wood_light")
    if anim == "idle":
        rod(m, (L / 2, 0.0, 8.0), (L / 2 + 10, 0.0, 0.5), 0.2, "straw")
    return m


SHIPS = {"world.fishing_boat", "world.quffa", "world.reed_boat", "world.kelek", "world.phoenician"}
KINDS = set(BEASTS) | BIRDS | SHIPS | {"world.dolphin"}


def sprite(kind, variant, anim, facing, frame, k):
    if kind in SHIPS:
        return _render(ship_model(kind, anim, frame, k), facing)
    n = FRAMES[anim]
    if kind == "world.dolphin":
        return _render(dolphin(frame, n, k), facing)
    if kind in BIRDS:
        return _render(_bird(kind, anim, frame, n, k), facing)
    if kind == "world.dog" and anim == "sleep":
        return _render(dog_sleep(frame, k), facing)
    if anim == "run":       # the dog's run: a trot, diagonal pairs together
        return _render(quadruped(BEASTS[kind], "run", frame, n, k), facing)
    m = quadruped(_beast(kind, variant), anim, frame, n, k)
    _load(m, kind, variant, anim, frame, n)
    return _render(m, facing)
