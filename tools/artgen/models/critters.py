"""Visitors, modelled around the origin facing +x; the anchor is the ground contact point.

`front` sprites face +x (down-right); `back` sprites face -y (up-right), i.e. the model turned
three quarter-turns clockwise. The engine mirrors these for the other two directions.
"""

import math

import numpy as np

from pack import Sprite
from palette import GLOW, INK, PLASTER, ROOF, STONE, STRAW, WATER, _rgb
from render import render_base
from palette import MAT
from voxel import Model, ellipsoid, ellipsoid_normal, segment


S = 1.35  # critters are modelled at life-ish size and enlarged so they read at 1x


def _model(k, x0, x1, y0, y1, z0, z1) -> Model:
    return Model.empty(*(int(math.floor(v * S)) if v < 0 else int(math.ceil(v * S))
                         for v in (x0, x1, y0, y1, z0, z1)), k=k)


def _put_points(m, pts, material, **kw):
    m.put_points(np.asarray(pts, np.float32) * S, material, **kw)


def _blob(m, X, Y, Z, c, r, material, tone=0.0):
    m.put(ellipsoid(X, Y, Z, *c, *r), material, tone=tone, normal=ellipsoid_normal(X, Y, Z, *c, *r))


def duck(anim, frame, frames, k):
    m = _model(k, -6, 7, -4, 5, 0, 10)
    X, Y, Z = (a / S for a in m.coords())
    moving = anim == "move"
    bob = 0.5 * math.sin(2 * math.pi * frame / frames) if moving else 0.0
    dip = (not moving) and frame % 2 == 1
    _blob(m, X, Y, Z, (0, 0, 2.6 + bob), (3.6, 2.4, 2.2), "cream")
    m.put(segment(X, Y, Z, (-2.5, 0, 3.5 + bob), (-4.3, 0, 5.0 + bob), 1.0), "cream", tone=-0.4)
    wing = ellipsoid(X, Y, Z, -0.6, 0, 3.4 + bob, 2.6, 2.5, 1.4) & (np.abs(Y) > 1.6)
    if m.fine:  # overlapping flight feathers: a darker line along each, tips towards the tail
        feather = ((X - (Z - bob) * 0.6) % 0.9) < 0.3
        m.put(wing, "cream", tone=-0.5 - feather * 0.8 - (X < -2.2) * 0.5)
        m.put(segment(X, Y, Z, (-3.6, 0, 4.4 + bob), (-4.9, 0, 5.9 + bob), 0.55), "cream", tone=-0.6)
    else:
        m.put(wing, "cream", tone=-0.8)
    hz = (4.6 if dip else 6.2) + bob
    hx = 3.4 if dip else 2.6
    m.put(segment(X, Y, Z, (1.8, 0, 3.5 + bob), (hx, 0, hz), 1.0), "cream")
    _blob(m, X, Y, Z, (hx, 0, hz), (1.6, 1.4, 1.5), "cream", tone=0.3)
    m.put(ellipsoid(X, Y, Z, hx + 1.9, 0, hz - 0.4, 1.0, 0.7, 0.45), "orange", tone=0.8)
    _put_points(m, [(hx + 0.6, 1.2, hz + 0.3)], "ink")
    if m.fine:  # a nostril, a pale lower mandible and a glint in the eye
        _put_points(m, [(hx + 2.1, 0.45, hz - 0.2)], "ember")
        m.put(ellipsoid(X, Y, Z, hx + 1.7, 0, hz - 0.75, 0.8, 0.55, 0.2), "orange", tone=-0.3)
        _put_points(m, [(hx + 0.75, 1.25, hz + 0.6)], "cream", tone=2)
    m.carve(Z < 0.6)  # sits in the water
    return m


def hen(anim, frame, frames, k):
    m = _model(k, -5, 6, -4, 5, 0, 11)
    X, Y, Z = (a / S for a in m.coords())
    moving = anim == "move"
    step = math.sin(2 * math.pi * frame / frames) if moving else 0.0
    peck = (not moving) and frame % 2 == 1
    bob = abs(step) * 0.5
    for side, phase in ((-0.9, 1), (0.9, -1)):
        lift = max(0.0, step * phase) * 1.2
        m.put(segment(X, Y, Z, (0.2, side, 3), (0.2 + step * phase * 0.8, side, lift), 0.5), "orange")
    # A brown hen with a pale breast and a dark tail, so she never reads as a small ginger cat.
    _blob(m, X, Y, Z, (0, 0, 4.4 + bob), (3.0, 2.2, 2.4), "wood_light", tone=-0.2)
    m.put(ellipsoid(X, Y, Z, 1.6, 0, 4.2 + bob, 1.5, 1.8, 1.6), "straw", tone=0.6)
    if m.fine:
        # Tail feathers fanned in strips, scalloped feathers over the wing.
        tail = ellipsoid(X, Y, Z, -2.6, 0, 6.2 + bob, 1.4, 1.2, 1.9)
        m.put(tail, "wood", tone=0.2 - (((Z - bob) % 0.8) < 0.3) * 0.9 + (X < -3.3) * 0.5)
        wing = ellipsoid(X, Y, Z, -0.4, 0, 4.8 + bob, 2.0, 2.4, 1.3) & (np.abs(Y) > 1.5)
        scallop = (((X * 1.4 + np.sin(Z * 4.0) * 0.3) % 1.0) < 0.3)
        m.put(wing, "wood", tone=0.6 - scallop * 0.9)
        body = (m.mat == MAT["wood_light"]) & (np.abs(Y) > 1.2)
        m.tone[body] -= np.broadcast_to(((X * 1.6 + Z * 0.8) % 1.0) < 0.25, body.shape)[body] * 0.7
    else:
        m.put(ellipsoid(X, Y, Z, -2.6, 0, 6.2 + bob, 1.4, 1.2, 1.9), "wood", tone=0.2)
        m.put(ellipsoid(X, Y, Z, -0.4, 0, 4.8 + bob, 2.0, 2.4, 1.3) & (np.abs(Y) > 1.5), "wood", tone=0.6)
    hx, hz = (3.6, 3.6 + bob) if peck else (2.4, 7.0 + bob)
    _blob(m, X, Y, Z, (hx, 0, hz), (1.4, 1.2, 1.4), "wood_light", tone=0.2)
    m.put(ellipsoid(X, Y, Z, hx - 0.1, 0, hz + 1.5, 1.2, 0.55, 0.9), "poppy", tone=1.0)
    m.put(ellipsoid(X, Y, Z, hx + 1.2, 0, hz - 0.9, 0.5, 0.5, 0.7), "poppy", tone=0.8)
    m.put(ellipsoid(X, Y, Z, hx + 1.6, 0, hz, 0.8, 0.5, 0.4), "yellow", tone=0.6)
    _put_points(m, [(hx + 0.4, 1.1, hz + 0.3)], "ink")
    return m


def cat(anim, frame, frames, k):
    m = _model(k, -7, 8, -4, 5, 0, 12)
    X, Y, Z = (a / S for a in m.coords())
    moving = anim == "move"
    t = 2 * math.pi * frame / frames
    # Tabby stripes; on fine grids narrower, bent with the body and a pixel or two wide.
    if m.fine:
        stripes = (((X * 1.5 + np.abs(Y) * 0.6 + Z * 0.3) % 1.6) < 0.45) * -0.9
    else:
        stripes = ((np.floor(X * 0.9) % 2) == 0) * -0.6
    if moving:
        for x0, side, ph in ((2.6, 1, 0), (2.6, -1, math.pi), (-2.4, 1, math.pi), (-2.4, -1, 0)):
            sw = math.sin(t + ph)
            m.put(segment(X, Y, Z, (x0, side * 0.9, 3.5), (x0 + sw * 1.2, side * 0.9, 0.3), 0.6),
                  "ginger", tone=-0.3)
        _blob(m, X, Y, Z, (0, 0, 4.0), (4.0, 1.7, 1.7), "ginger", tone=stripes)
        head = (4.3, 0, 5.6)
        tail = [(-3.6, 0, 4.4), (-5.6, 0, 6.5 + 0.6 * math.sin(t)), (-6.0, 0, 8.6)]
    else:
        # Sitting: haunches down, chest up, tail curled around and flicking.
        m.put(segment(X, Y, Z, (1.6, 0.8, 3.5), (1.9, 0.8, 0.3), 0.6), "ginger", tone=-0.2)
        m.put(segment(X, Y, Z, (1.6, -0.8, 3.5), (1.9, -0.8, 0.3), 0.6), "ginger", tone=-0.2)
        _blob(m, X, Y, Z, (-0.8, 0, 2.6), (2.6, 2.0, 2.2), "ginger", tone=stripes)
        _blob(m, X, Y, Z, (0.6, 0, 4.8), (1.7, 1.6, 2.4), "ginger", tone=stripes)
        head = (1.3, 0, 7.6)
        flick = 1.0 if frame % 2 else 0.0
        tail = [(-3.0, 0, 1.0), (-1.5, 2.2, 0.6), (1.0 + flick, 2.4, 0.8 + flick)]
    for a, b in zip(tail, tail[1:]):
        m.put(segment(X, Y, Z, a, b, 0.65), "ginger", tone=-0.2)
    hx, hy, hz = head
    _blob(m, X, Y, Z, head, (1.9, 1.8, 1.6), "ginger", tone=0.3)
    for side in (-1, 1):
        m.put(segment(X, Y, Z, (hx - 0.3, side * 1.0, hz + 1.0), (hx - 0.4, side * 1.1, hz + 2.4), 0.55),
              "ginger", tone=0.2)
        if m.fine:  # pink inside the ear
            _put_points(m, [(hx + 0.05, side * 1.0, hz + 1.6), (hx + 0.05, side * 1.0, hz + 1.9)],
                        "blossom", tone=0.6)
    if m.fine:
        # A cream muzzle and bib, green eyes with dark pupils, a darker tail tip.
        m.put(ellipsoid(X, Y, Z, hx + 1.3, 0, hz - 0.6, 0.8, 1.0, 0.7), "cream", tone=0.3)
        m.put(ellipsoid(X, Y, Z, head[0] - 1.2, 0, hz - 2.2, 1.2, 1.1, 1.4) & (X > head[0] - 1.0),
              "cream", tone=0.2)
        for ey in (1.2, 0.4):
            _put_points(m, [(hx + 1.0, ey, hz + 0.3)], "leaf", tone=2.0)
            _put_points(m, [(hx + 1.0, ey, hz + 0.1)], "ink")
        m.put(segment(X, Y, Z, tail[-2], tail[-1], 0.7) & (np.hypot(*(np.broadcast_arrays(
            X - tail[-1][0], Z - tail[-1][2]))) < 1.0), "ginger", tone=-1.2)
    else:
        _put_points(m, [(hx + 1.0, 1.2, hz + 0.3), (hx + 1.6, 0.4, hz + 0.3)], "ink")
    _put_points(m, [(hx + 1.9, 0, hz - 0.5)], "blossom", tone=1)
    return m


# ---- tiny flyers: hand-drawn at pixel scale, where voxels would only make blobs ----
# Rows top to bottom; the anchor is the bottom-middle of the drawing (the engine adds altitude).
# Each set of drawings is made for one pixel density (pixels per design unit); a build uses the
# densest set that divides its own and enlarges it by the remaining whole factor. On the
# coarse set `back` reuses the `front` drawings; the fine set shows the upper side of the wings
# from behind and the paler underside, head first, from the front.

FLYER_INKS = {"K": (INK, 255), "O": (GLOW[0], 255), "o": (ROOF[3], 255), "R": (ROOF[2], 255),
              "Y": (STRAW[2], 255), "y": (STRAW[3], 255), "W": (PLASTER[4], 255),
              "w": (WATER[5], 200), "g": (STONE[2], 255), "1": (GLOW[2], 255), "2": (GLOW[1], 150),
              "3": (GLOW[0], 60)}

_BUTTERFLY_1 = {
    "open": ("K.K...K.K",
             ".K.....K.",
             "KOOK.KOOK",
             "KWROKORWK",
             ".KOOKOOK.",
             ".KYYKYYK.",
             "..KYKYK..",
             "...K.K..."),
    "half": ("..K...K..",
             "...K.K...",
             "..KOKOK..",
             ".KWOKOWK.",
             ".KROKORK.",
             "..KYKYK..",
             "..KYKYK..",
             "...K.K..."),
    "shut": ("...K.K...",
             "....K....",
             "...KOK...",
             "...KOK...",
             "...KRK...",
             "...KYK...",
             "...KYK...",
             "....K...."),
}
_BEE_1 = {
    "up":   ("...wW...",
             "..wWw...",
             ".KYYKYKK",
             "KYyKYyKK",
             ".KKKKKK."),
    "down": ("........",
             "........",
             ".KYYKYKK",
             "KYyKYyKK",
             "wwKKKKw."),
}
_FIREFLY_1 = {
    2: (".33333.",
        "3322233",
        "3221223",
        "3212123",
        "3221223",
        "3322233",
        ".3KgK3."),
    1: (".......",
        "..333..",
        ".32223.",
        ".32123.",
        ".32223.",
        "..333..",
        "..KgK.."),
    0: (".......",
        ".......",
        ".......",
        "...3...",
        "..323..",
        "...3...",
        "..KgK.."),
}

_BUTTERFLY_2_BACK = {
    "open": (".....K...K.....",
             "......K.K......",
             ".KKK...K...KKK.",
             "KWKOK.KKK.KOKWK",
             "KKOOOKKKKKOOOKK",
             "KOOoOOKKKOOoOOK",
             ".KOOOOKKKOOOOK.",
             "..KKRRKKKRRKK..",
             ".KRRoOKKKOoRRK.",
             ".KRoOK.K.KOoRK.",
             "..KKK..K..KKK..",
             "..............."),
    "half": (".....K...K.....",
             "......K.K......",
             "....K..K..K....",
             "...KWK.K.KWK...",
             "...KOOKKKOOK...",
             "...KOoKKKoOK...",
             "....KOKKKOK....",
             "....KRKKKRK....",
             "....KRKKKRK....",
             ".....KK.KK.....",
             ".......K.......",
             "..............."),
    "shut": (".....K...K.....",
             "......K.K......",
             ".......K.......",
             "......KWK......",
             "......KOK......",
             "......KoK......",
             "......KOK......",
             "......KRK......",
             "......KRK......",
             ".......K.......",
             "...............",
             "..............."),
}
_BUTTERFLY_2_FRONT = {
    "open": ("...............",
             ".KKK.......KKK.",
             "KyyyK.....KyyyK",
             "KyKyyK...KyyKyK",
             "KyyyOOK.KOOyyyK",
             ".KyyOOKKKOOyyK.",
             "..KKKKKKKKKKK..",
             ".KYYOKKKKKOYYK.",
             ".KYOOK.K.KOOYK.",
             "..KKK.KKK.KKK..",
             "......K.K......",
             ".....K...K....."),
    "half": ("...............",
             "....K.....K....",
             "...KyK...KyK...",
             "...KyyK.KyyK...",
             "...KyOKKKOyK...",
             "....KOKKKOK....",
             "....KYKKKYK....",
             "....KYKKKYK....",
             ".....KKKKK.....",
             "......KKK......",
             "......K.K......",
             ".....K...K....."),
    "shut": ("...............",
             "...............",
             "...............",
             "......KyK......",
             "......KyK......",
             "......KOK......",
             "......KOK......",
             "......KYK......",
             "......KKK......",
             ".......K.......",
             "......K.K......",
             ".....K...K....."),
}
_BEE_2_FRONT = {
    "up":   ("....ww.ww....",
             "...wWw.wWw...",
             "....ww.ww....",
             "..KKYYKKYK...",
             ".KYyKYyKYyKK.",
             "KYyyKYyKYyKgK",
             ".KYYKYYKYKKK.",
             "..KKKKKKKK...",
             "...K..K..K..."),
    "down": (".............",
             ".............",
             ".............",
             "..KKYYKKYK...",
             ".KYyKYyKYyKK.",
             "KYyyKYyKYyKgK",
             ".KYYKYYKYKKK.",
             "wwKKKKKKKKww.",
             ".wwK..K..Kw.."),
}
_BEE_2_BACK = {
    "up":   (".ww.......ww.",
             "wWww.....wwWw",
             ".www.KKK.www.",
             "....KYYYK....",
             "...KKKKKKK...",
             "...KYyYyYK...",
             "...KKKKKKK...",
             "....KYyYK....",
             ".....KKK....."),
    "down": (".............",
             ".............",
             ".....KKK.....",
             "....KYYYK....",
             "...KKKKKKK...",
             "wwwKYyYyYKwww",
             ".wwKKKKKKKww.",
             "....KYyYK....",
             ".....KKK....."),
}
_GLOW_2 = {
    2: ("...33333...",
        "..3333333..",
        ".333222333.",
        ".332212233.",
        ".332111233.",
        ".332212233.",
        ".333222333.",
        "..3333333..",
        "...33333..."),
    1: ("...........",
        "....333....",
        "...33333...",
        "..3322233..",
        "..3321233..",
        "..3322233..",
        "...33333...",
        "....333....",
        "..........."),
    0: ("...........",
        "...........",
        "...........",
        "....333....",
        "....323....",
        "....333....",
        "...........",
        "...........",
        "..........."),
}
# The fine firefly: its glowing tail over a small dark body, head first or wings first.
_FIREFLY_2 = {face: {n: rows + body for n, rows in _GLOW_2.items()}
              for face, body in (("front", ("....KKgK...", ".....K.K...")),
                                 ("back", ("...gKKKg...", "....K.K....")))}

# density -> flyer -> facing -> pose -> rows
FLYER_ART = {
    1: {"butterfly": {"front": _BUTTERFLY_1, "back": _BUTTERFLY_1},
        "bee": {"front": _BEE_1, "back": _BEE_1},
        "firefly": {"front": _FIREFLY_1, "back": _FIREFLY_1}},
    2: {"butterfly": {"front": _BUTTERFLY_2_FRONT, "back": _BUTTERFLY_2_BACK},
        "bee": {"front": _BEE_2_FRONT, "back": _BEE_2_BACK},
        "firefly": _FIREFLY_2},
}
BUTTERFLY_FRAMES = {"move": ("open", "half", "shut", "half"), "idle": ("open", "half")}


def _stencil(rows, scale) -> Sprite:
    h, w = len(rows), len(rows[0])
    rgba = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                color, alpha = FLYER_INKS[ch]
                rgba[y, x, :3] = _rgb(color)
                rgba[y, x, 3] = alpha
    rgba = rgba.repeat(scale, 0).repeat(scale, 1)
    return Sprite(rgba, w // 2 * scale, h * scale - 1)


def _flyer_pose(cid, kind, frame):
    if cid == "butterfly":
        poses = BUTTERFLY_FRAMES[kind]
        return poses[frame % len(poses)]
    if cid == "bee":
        return "up" if frame % 2 == 0 else "down"
    # Fireflies are emissive at night, so the glow is part of the sprite: a white-hot core in
    # a warm halo that pulses with the frames.
    pulse = (2, 1, 0, 1) if kind == "move" else (2, 1)
    return pulse[frame % len(pulse)]


def flyer(cid, kind, facing, frame, k) -> Sprite:
    density = max(d for d in FLYER_ART if k % d == 0)
    rows = FLYER_ART[density][cid][facing][_flyer_pose(cid, kind, frame)]
    return _stencil(rows, k // density)


MODELS = {"duck": duck, "hen": hen, "cat": cat}


def sprite(cid: str, anim: str, frame: int, frames: int, k: int) -> Sprite:
    kind, facing = anim.split("_")
    if cid not in MODELS:
        return flyer(cid, kind, facing, frame, k)
    model = MODELS[cid](kind, frame, frames, k)
    if facing == "back":
        model = model.rotated(3, 0, 0)
    rgba, _glow, ox, oy = render_base(model)
    return Sprite(rgba, ox, oy)
